/* Register-only AY/YM rendering through the unmodified, vendored Ayumi core. */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const zlib = require('zlib');
const crypto = require('crypto');

const corePath = path.join(__dirname, 'vendor', 'ayumi-js', 'ayumi.js');
const core = fs.readFileSync(corePath, 'utf8');
const context = {};
vm.runInNewContext(core+'\nglobalThis.chipApi={Ayumi,YM_DAC_TABLE,AY_DAC_TABLE};', context);
const {Ayumi, YM_DAC_TABLE, AY_DAC_TABLE} = context.chipApi;

function createChip(clock = 1773450, sampleRate = 44100, isYM = process.env.ZX_SOUND_CHIP==='YM2149') {
  // Ayumi's interpolator requires one internal step or less per oversample.
  // The JS port omits the validity return present in the original C API.
  if (!Number.isFinite(clock) || !Number.isFinite(sampleRate) || clock<=0 || sampleRate<=clock/64) {
    throw new Error('Ayumi requires sampleRate > clock/64; render at 44100 Hz then low-pass resample');
  }
  const chip = new Ayumi();
  chip.configure(isYM, clock, sampleRate);
  for (let channel=0; channel<3; channel++) {
    chip.setPan(channel, .5, false);
    chip.setMixer(channel, 1, 1, 0);
    chip.setVolume(channel, 0);
  }
  return chip;
}

function setRegisters(chip, registers) {
  if (![11,14].includes(registers.length)) throw new Error('Expected R0..R10 or R0..R13');
  for (let channel=0; channel<3; channel++) {
    if (registers[channel*2+1] > 15 || registers[8+channel] > (registers.length===14 ? 31 : 15)) {
      throw new Error('Only 12-bit tone periods and fixed 4-bit volumes are supported');
    }
    chip.setTone(channel, registers[channel*2] | (registers[channel*2+1]<<8));
    chip.setVolume(channel, registers[8+channel]&15);
    chip.setMixer(channel, (registers[7]>>channel)&1, (registers[7]>>(channel+3))&1, (registers[8+channel]>>4)&1);
  }
  if (registers[6] > 31) throw new Error('Invalid shared noise period');
  chip.setNoise(registers[6]);
  if (registers.length===14) {
    chip.setEnvelope(registers[11] | (registers[12]<<8));
    if (registers[13] !== 255) {
      if (registers[13]>15) throw new Error('Invalid envelope shape');
      chip.setEnvelopeShape(registers[13]);
    }
  }
}

function render(registers, fps, {clock=1773450, sampleRate=44100, isYM=process.env.ZX_SOUND_CHIP==='YM2149', registerBytes=11}={}) {
  if (![11,14].includes(registerBytes) || !registers.length || registers.length%registerBytes || !Number.isFinite(fps) || fps<=0 || fps>sampleRate) {
    throw new Error('Invalid register stream or update rate');
  }
  const count = registers.length/registerBytes, chip = createChip(clock, sampleRate, isYM);
  const out = new Float32Array(Math.round(count*sampleRate/fps));
  for (let frame=0; frame<count; frame++) {
    // Preserve tone/noise phase and counters across all register updates.
    setRegisters(chip, registers.subarray(frame*registerBytes, frame*registerBytes+registerBytes));
    const start = Math.round(frame*sampleRate/fps), end = Math.round((frame+1)*sampleRate/fps);
    for (let i=start; i<end; i++) {
      chip.process(); chip.removeDC();
      // Equal mono sum of the three chip outputs; fixed headroom, no compressor.
      out[i] = (chip.left+chip.right)/3;
    }
  }
  if (!out.every(Number.isFinite)) throw new Error('Nonfinite chip output');
  return out;
}

module.exports = {createChip,setRegisters,render,YM_DAC_TABLE,AY_DAC_TABLE};
if (require.main === module) {
  const [input, output, fpsText, reportPath, widthText, chipText] = process.argv.slice(2);
  if (!reportPath) throw new Error('Usage: node render_ym2149.js registers.gz output.f32 fps report.json');
  const registers = zlib.gunzipSync(fs.readFileSync(input)), fps = Number(fpsText);
  const registerBytes = widthText ? Number(widthText) : 11;
  const chipType=chipText || (process.env.ZX_SOUND_CHIP==='YM2149'?'YM':'AY');
  if (!['AY','YM'].includes(chipType)) throw new Error('Chip must be AY or YM');
  const samples = render(registers, fps, {registerBytes,isYM:chipType==='YM'});
  fs.writeFileSync(output, Buffer.from(samples.buffer));
  const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
  fs.writeFileSync(reportPath, JSON.stringify({chip:chipType==='AY'?'AY-3-8910/8912':'YM2149',
    dac_curve:chipType, distinct_envelope_levels:chipType==='AY'?16:32, clock_hz:1773450, sample_rate:44100,
    update_rate_hz:fps, frames:registers.length/registerBytes, register_bytes_per_state:registerBytes, samples:samples.length,
    channels:3, shared_noise_generators:1, mixing:'equal mono sum; chip Boolean tone/noise mixer',
    envelope_enabled:registerBytes===14, envelope_restart:'R13=255 skips the write and preserves phase',
    high_rate_pcm_volume_output:false, dc_filter:'Ayumi 1024-sample DC filter',
    scheduling:'ideal atomic register update; not a Z80 bus-timing or analogue circuit simulation',
    source:'https://github.com/alexanderk23/ayumi-js/tree/3a1fb9120cc2c5ef8f538af59b46701e4c2305bb',
    core_sha256:sha(Buffer.from(core)), registers_sha256:sha(registers),
    output_pcm_sha256:sha(Buffer.from(samples.buffer))}, null, 2)+'\n');
}
