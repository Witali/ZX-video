// Compare the pinned upstream Ayumi against the allocation-only local patch.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { patchAyumi } from './patch-ayumi.mjs';

const original = fs.readFileSync(process.argv[2] || '.tmp/baseline-ayumi.js', 'utf8');
const candidate = fs.readFileSync(process.argv[3] || 'web/vendor/ayumi.js', 'utf8');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
assert.equal(sha(original), 'bd189a818201aa57e9185d3c5bd809ead8cd6ac6a0a9b9ee8df17d0ef483326d');
assert.equal(candidate, patchAyumi(original), 'Checked-in patch must reproduce from pinned source');

const exercise = `
function configureChip(chip, ym, rate) {
  chip.configure(ym,1773400,rate);
  for(var i=0;i<3;i++)chip.setPan(i,[.1,.5,.9][i],true);
}
function play(chip,count,capture) {
  var output=capture?new Float64Array(count*2):null;
  for(var n=0;n<count;n++) {
    if((n&1023)===0) {
      var block=n>>>10;
      chip.setNoise([0,1,7,31][block&3]);
      chip.setEnvelope([0,1,2,255,4095,65535][block%6]);
      chip.setEnvelopeShape(block&15);
      for(var c=0;c<3;c++) {
        chip.setTone(c,[0,1,2,13,127,1024,4095][(block+c)%7]);
        chip.setVolume(c,(block*7+c*5)&15);
        chip.setMixer(c,(block>>>c)&1,(block>>>(c+1))&1,(block>>>(c+2))&1);
      }
    }
    // configure changes clocks/DAC without clearing the existing filter history.
    if(n===100000)configureChip(chip,!ym,rate===44100?48000:44100);
    chip.process();chip.removeDC();
    if(output){output[n*2]=chip.left;output[n*2+1]=chip.right;}
  }
  return output;
}
function snapshot(chip) {
  var scalar={};
  for(var name of ['noisePeriod','noiseCounter','noise','envelopeCounter','envelopePeriod',
    'envelopeShape','envelopeSegment','envelope','step','x','left','right','dcIndex','firIndex'])scalar[name]=chip[name];
  scalar.channels=chip.channels;
  scalar.dcSums=[chip.dcFilterLeft.sum,chip.dcFilterRight.sum];
  return {scalar,arrays:[chip.firLeft,chip.firRight,chip.interpolatorLeft.c,chip.interpolatorLeft.y,
    chip.interpolatorRight.c,chip.interpolatorRight.y,chip.dcFilterLeft.delay,chip.dcFilterRight.delay]};
}`;

function run(source, ym, rate, samples) {
  const context = vm.createContext({ ym, rate, samples });
  vm.runInContext(source + '\n' + exercise, context);
  vm.runInContext('var chip=new Ayumi();configureChip(chip,ym,rate);var pcm=play(chip,samples,true);var state=snapshot(chip)', context);
  return { context, pcm: context.pcm, state: context.state };
}

const cases = [];
for (const ym of [false, true]) for (const rate of [44100, 48000]) {
  const before = run(original, ym, rate, 262144);
  const after = run(candidate, ym, rate, 262144);
  const beforeBytes = Buffer.from(before.pcm.buffer);
  assert(beforeBytes.equals(Buffer.from(after.pcm.buffer)), 'Every Float64 stereo sample must match bit-for-bit');
  assert.equal(JSON.stringify(after.state.scalar), JSON.stringify(before.state.scalar));
  for (let i = 0; i < before.state.arrays.length; i++) {
    assert(Buffer.from(before.state.arrays[i].buffer).equals(Buffer.from(after.state.arrays[i].buffer)));
  }
  vm.runInContext(`
    if(chip.firViewsLeft.length!==23||chip.firViewsRight.length!==23)throw Error('View count');
    for(var i=0;i<23;i++){
      var offset=192-i*8;
      if(chip.firViewsLeft[i].buffer!==chip.firLeft.buffer||chip.firViewsRight[i].buffer!==chip.firRight.buffer
        ||chip.firViewsLeft[i].byteOffset!==offset*8||chip.firViewsRight[i].byteOffset!==offset*8)throw Error('View alias');
    }`, after.context);
  cases.push({ chip: ym ? 'YM' : 'AY', initialSampleRate: rate, stereoFrames: 262144, pcmFloat64Sha256: sha(beforeBytes) });
}

function allocationProbe(source) {
  const context = vm.createContext({ ym: false, rate: 44100 });
  vm.runInContext(source + '\n' + exercise, context);
  vm.runInContext(`var chip=new Ayumi();configureChip(chip,ym,rate);
    var calls=0,subarray=Float64Array.prototype.subarray;
    Float64Array.prototype.subarray=function(){calls++;return subarray.apply(this,arguments)};
    play(chip,1000,false);`, context);
  return context.calls;
}
const allocations = [allocationProbe(original), allocationProbe(candidate)];
assert.deepEqual(allocations, [2000, 0]);
const report = { scope: 'Bit-exact Ayumi differential: AY/YM, 44.1/48 kHz, all 16 shapes, tone/noise/mixer/volume changes and live reconfiguration; not physical-chip accuracy.',
  baselineSha256: sha(original), candidateSha256: sha(candidate), cases, internalStateExact: true,
  per1000SamplesSubarrayCalls: { before: allocations[0], after: allocations[1] } };
console.log(JSON.stringify(report, null, 2));
if (process.argv[4]) fs.writeFileSync(process.argv[4], JSON.stringify(report, null, 2) + '\n');
