import assert from 'node:assert/strict';
import { LOWPASS_CUTOFFS, rcCoefficients } from '../audio-filter.js';
let cases=0;
for (const rate of [44100,48000]) for (const hz of LOWPASS_CUTOFFS) {
  const {feedforward:[a],feedback:[,b]}=rcCoefficients(hz,rate),p=-b;
  assert(p>0&&p<1,'Stable positive pole');
  const magnitude=f=>a/Math.hypot(1-p*Math.cos(2*Math.PI*f/rate),p*Math.sin(2*Math.PI*f/rate));
  assert(Math.abs(magnitude(0)-1)<1e-12,'Unity DC gain');
  assert(Math.abs(magnitude(hz)-Math.SQRT1_2)<1e-12,'Preset is exactly -3 dB');
  let previous=1;
  for(let i=1;i<=256;i++) {const m=magnitude(i*rate/512);assert(m<=previous+1e-12);previous=m;}
  let sum=0,impulse=a;
  for(let i=0;i<256;i++){assert(impulse>=0);sum+=impulse;impulse*=p;}
  assert(Math.abs(sum-1)<1e-12,'Passive exponential response');cases++;
}
assert.throws(()=>rcCoefficients(22050,44100),RangeError);
console.log(`RC low-pass: ${cases} sample-rate/preset cases pass DC, -3 dB, monotonic response and stability.`);
