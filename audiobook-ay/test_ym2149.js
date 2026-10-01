'use strict';
const assert = require('assert/strict');
const {createChip,setRegisters,render,YM_DAC_TABLE,AY_DAC_TABLE} = require('./render_ym2149');

// Independent tone-counter period check before anti-alias and DC filters.
const tone = createChip();
tone.setTone(0, 111);
let previous=0, transitions=[];
for (let tick=1; tick<=111*20; tick++) {
  const value=tone.updateTone(0);
  if (value!==previous) transitions.push(tick);
  previous=value;
}
assert.equal(transitions.length,20);
for (let i=1; i<transitions.length; i++) assert.equal(transitions[i]-transitions[i-1],111);

// One LFSR must feed every enabled channel; verify independent tap recurrence.
const chip = createChip();
chip.setNoise(1);
for (let c=0;c<3;c++) { chip.setMixer(c,1,0,0); chip.setVolume(c,15); }
chip.setPan(0,0,false); chip.setPan(1,1,false); chip.setPan(2,.5,false); chip.setVolume(2,0);
let lfsr=1;
const values=new Set();
for(let i=1;i<=8192;i++) {
  if (!(i%2)) lfsr=(lfsr>>>1)|(((lfsr^(lfsr>>>3))&1)<<16);
  chip.updateMixer();
  assert.equal(chip.noise,lfsr);
  assert.equal(chip.left,chip.right);
  assert.equal(chip.left,lfsr&1);
  values.add(chip.left);
}
assert.equal(values.size,2);

// Mixer is Boolean (tone | disabled) & (shared noise | disabled), not addition.
const mixer=createChip();
mixer.updateEnvelope=()=>0;
for(let c=1;c<3;c++) mixer.setVolume(c,0);
mixer.setPan(0,0,false); mixer.setVolume(0,15);
for(const t of [0,1]) for(const n of [0,1]) for(const td of [0,1]) for(const nd of [0,1]) {
  mixer.updateTone=()=>t; mixer.updateNoise=()=>n; mixer.setMixer(0,td,nd,0); mixer.updateMixer();
  assert.equal(mixer.left,(t|td)&(n|nd));
}
assert.notEqual(YM_DAC_TABLE[15],AY_DAC_TABLE[15]);

const silent=Buffer.from([111,0,222,0,55,0,1,0x38,0,0,0]);
assert.ok(render(Buffer.concat(Array(3).fill(silent)),100).every(x=>x===0));
const active=Buffer.from(silent); active[8]=10;
const output=render(Buffer.concat(Array(101).fill(active)),100);
assert.equal(output.length,44541); // No rounding drift at 100 Hz.
assert.ok(output.some(x=>Math.abs(x)>.001));
assert.throws(()=>setRegisters(createChip(),Buffer.alloc(10)));
assert.throws(()=>render(Buffer.alloc(12),100));
console.log('YM2149: period, shared noise taps, all 16 mixer cases, DAC model, silence and sample counts pass.');
