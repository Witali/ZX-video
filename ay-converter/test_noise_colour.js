/* Check the vendored digital model against documented chip invariants and
 * make a synthetic fixture with a different LFSR phase from the fit bank. */
'use strict';
const assert = require('assert');
const fs = require('fs');
const {createChip,setRegisters} = require('./render_ym2149');
const chip = createChip();
assert.throws(() => createChip(1773450,22050),/sampleRate/);
chip.setNoise(1);
const seen = new Set();
let ones = 0;
for (let i=0; i<131071; i++) {
  assert(!seen.has(chip.noise));
  seen.add(chip.noise);
  ones += chip.noise&1;
  chip.updateNoise(); chip.updateNoise();
}
assert.strictEqual(chip.noise,1);
assert.strictEqual(ones,65536);
for (let p=1; p<=31; p++) {
  const test = createChip(); test.setNoise(p);
  for (let i=1; i<2*p; i++) { test.updateNoise(); assert.strictEqual(test.noise,1); }
  test.updateNoise(); assert.strictEqual(test.noise,65536);
  test.setNoise(7);
  assert.strictEqual(test.noise,65536); // Writing R6 must not reseed the LFSR.
}
for (let tone=0; tone<=1; tone++) for (let noise=0; noise<=1; noise++) {
  for (let td=0; td<=1; td++) for (let nd=0; nd<=1; nd++) {
    const test = createChip();
    test.setVolume(0,15); test.setMixer(0,td,nd,0);
    test.updateTone = () => tone; test.updateNoise = () => noise;
    test.updateMixer();
    assert.strictEqual(test.left+test.right,(tone|td)&(noise|nd));
  }
}
if (process.argv[2]) {
  const target = createChip(1773450,44100);
  target.noise = 0x15abc; // Held-out phase; no fitted reset or copied PCM.
  const row = Uint8Array.from([0,1,0,2,0,3,23,0x37,0,0,0]);
  // A noise-only channel at volume 11. Other generators continue silently.
  row[8] = 11; row[7] = 0x37;
  setRegisters(target,row);
  const out = new Float32Array(882*100);
  for (let i=0; i<out.length; i++) {
    target.process(); target.removeDC(); out[i]=(target.left+target.right)/3;
  }
  fs.writeFileSync(process.argv[2],Buffer.from(out.buffer));
}
console.log(JSON.stringify({lfsr_states:seen.size,ones,period_divisors_checked:31,mixer_truth_cases:16,pass:true}));
