/* Run the user's existing LPC2 codec core headlessly, without changing its DSP. */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');
const zlib = require('zlib');

const [sourcePath, pcmPath, outputPath] = process.argv.slice(2);
if (!outputPath) throw new Error('Usage: node lpc2_bridge.js index.html input.f32 output-directory');
const html = fs.readFileSync(sourcePath, 'utf8');
function section(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  if (a < 0 || b <= a) throw new Error(`LPC source layout changed: ${start}`);
  return html.slice(a, b);
}
const code = `const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const tick=async()=>{}; function progress(){} function status(){}
` + section('function levelInfo(', 'function dbfs(')
  + section('function waveformStats(', 'function outputBalanceLine(')
  + section('const LPC_CHIRP=', 'function splitForBlocks(');
const context = {};
vm.runInNewContext(code + '\nglobalThis.api={normalizeInput,processDecodedOutput,encodeLPC2,packLPC2,unpackLPC2,synthLPC2,decodeLpc2FrameLsf,lsfToLpc,qLpcGain,qLpc2Pitch};', context, {timeout:5000});
const api = context.api;
const input = fs.readFileSync(pcmPath);
if (input.length % 4) throw new Error('Truncated float PCM');
const samples = new Float32Array(input.buffer.slice(input.byteOffset, input.byteOffset + input.byteLength));
const config = {frameMs:20, windowMs:32, pre:.85, voicing:.38, repeat:.05, pitchSmooth:.65};
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
async function main() {
  const normalized = api.normalizeInput(samples, 'peak', -1, 18);
  const encoded = await api.encodeLPC2(normalized.samples, 8000, config);
  const packed = api.packLPC2(encoded.meta, encoded.frames, encoded.analysis);
  const decoded = api.unpackLPC2(packed.buffer);
  const repacked = api.packLPC2(decoded.meta, decoded.frames);
  if (!Buffer.from(packed.buffer).equals(Buffer.from(repacked.buffer))) throw new Error('LPC2 bitstream round trip failed');
  const pcm = await api.synthLPC2(decoded.meta, decoded.frames, .35);
  const processed = api.processDecodedOutput(pcm, 8000, 'dcblock', 4, 70);
  if (processed.samples.length !== samples.length || !Array.from(processed.samples).every(Number.isFinite)) {
    throw new Error('Invalid LPC2 reconstructed samples');
  }
  fs.writeFileSync(path.join(outputPath, 'reference.lp2'), Buffer.from(packed.buffer));
  fs.writeFileSync(path.join(outputPath, 'lpc2-reference.f32'), Buffer.from(processed.samples.buffer));
  fs.writeFileSync(path.join(outputPath, 'lpc2-core.js.gz'), zlib.gzipSync(code));
  const frames = decoded.frames.map(frame => ({
    mode:frame.mode, energy:frame.energy, gain:api.qLpcGain(frame.energy),
    pitch_hz:frame.mode === 1 || frame.mode === 2 ? 8000 / api.qLpc2Pitch(frame.pitch,8000) : 0,
    coefficients:Array.from(api.lsfToLpc(api.decodeLpc2FrameLsf(frame)))
  }));
  fs.writeFileSync(path.join(outputPath, 'lpc2-analysis.json'), JSON.stringify({
    source:sourcePath, source_sha256:sha(Buffer.from(html)), extracted_core_sha256:sha(Buffer.from(code)),
    input_pcm_sha256:sha(input), config, normalization_gain:normalized.gain,
    postfilter:.35, brightness_db:4, highpass_hz:70,
    bitstream_roundtrip:true, stats:decoded.stats, meta:decoded.meta, frames
  }, null, 2) + '\n');
  console.log(JSON.stringify({lpc2_bytes:packed.buffer.byteLength, frames:frames.length, stats:decoded.stats}));
}
main().catch(error => { console.error(error); process.exitCode=1; });
