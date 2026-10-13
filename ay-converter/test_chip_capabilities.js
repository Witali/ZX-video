/* Independent AY invariants checked against GI data-manual sections 3.3..3.7.
 * Register names in that manual are octal: R10=decimal 8, R15=decimal 13.
 * Timing below uses the model's clock/8 internal step and paired AY DAC codes.
 */
'use strict';
const assert=require('assert');
const {createChip,setRegisters,AY_DAC_TABLE,YM_DAC_TABLE}=require('./render_ym2149');
const chip=createChip();
assert.strictEqual(new Set(AY_DAC_TABLE).size,16);
assert.deepStrictEqual(chip.dacTable,AY_DAC_TABLE);
assert.notDeepStrictEqual(AY_DAC_TABLE,YM_DAC_TABLE);
function expected(shape,step) {
  const c=(shape>>3)&1,a=(shape>>2)&1,alt=(shape>>1)&1,hold=shape&1;
  const cycle=Math.floor(step/16),position=step%16;
  if(cycle && !c)return 0;
  if(cycle && hold)return (a^alt)?15:0;
  const rising=a^(alt&&(cycle&1));
  return rising?position:15-position;
}
let shapes=0,states=0;
for(let shape=0;shape<16;shape++)for(const period of [1,2,257,65535]) {
  const test=createChip();test.setEnvelope(period);test.setEnvelopeShape(shape);
  // Large divisors are checked at counter boundaries, without 8 million loops.
  for(let step=0;step<64;step++) {
    assert.strictEqual(test.dacTable[test.envelope],AY_DAC_TABLE[expected(shape,step)*2+1]);
    states++;
    for(let pair=0;pair<2;pair++) {
      test.envelopeCounter=period-1;test.updateEnvelope();
    }
  }
  shapes++;
}
const phase=createChip();phase.setEnvelope(10);phase.setEnvelopeShape(14);
for(let i=0;i<127;i++)phase.updateEnvelope();
const before=[phase.envelopeCounter,phase.envelopeSegment,phase.envelope];
phase.setEnvelope(11);
assert.deepStrictEqual([phase.envelopeCounter,phase.envelopeSegment,phase.envelope],before);
phase.setEnvelopeShape(14);
assert.deepStrictEqual([phase.envelopeCounter,phase.envelopeSegment,phase.envelope],[0,0,0]);
for(const toneDisabled of [0,1])for(const noiseDisabled of [0,1]) {
  const test=createChip();test.setEnvelopeShape(9);test.setMixer(0,toneDisabled,noiseDisabled,1);
  test.updateTone=()=>0;test.updateNoise=()=>0;test.updateEnvelope=()=>31;
  test.updateMixer();assert.strictEqual(test.left+test.right,toneDisabled&noiseDisabled);
}
const registers=Uint8Array.from([255,15,1,0,1,0,31,63,16,0,0,255,255,14]);
setRegisters(phase,registers);
assert.strictEqual(phase.envelopePeriod,65535);assert.strictEqual(phase.envelopeShape,14);
registers[13]=255;phase.envelopeCounter=123;setRegisters(phase,registers);
assert.strictEqual(phase.envelopeCounter,123);
registers[13]=14;setRegisters(phase,registers);assert.strictEqual(phase.envelopeCounter,0);
console.log(JSON.stringify({complete:true,chip:'AY-3-8910/8912',distinct_dac_levels:16,
  envelope_shape_period_cases:shapes,envelope_step_checks:states,shared_envelope:true,
  period_write_preserves_phase:true,shape_write_restarts:true,sentinel_not_sent_to_chip:true,
  envelope_only_boolean_gate_valid:true,manual_register_notation:'octal',
  analogue_circuit_measured:false}));
