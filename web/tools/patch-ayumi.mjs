// Allocation-only optimization of the pinned Ayumi FIR ring. Arithmetic and
// sample/oscillator clocks remain byte-for-byte source-equivalent.
export function patchAyumi(source) {
  const constructor = /  this\.firIndex = 0;\r?\n/;
  const process = /  var firOffset = FIR_SIZE - this\.firIndex \* DECIMATE_FACTOR;\r?\n  var firLeft = this\.firLeft\.subarray\(firOffset\);\r?\n  var firRight = this\.firRight\.subarray\(firOffset\);/;
  if ((source.match(new RegExp(constructor.source, 'g')) || []).length !== 1
      || (source.match(new RegExp(process.source, 'g')) || []).length !== 1) {
    throw new Error('Pinned Ayumi FIR-view anchors changed');
  }
  source = source.replace(constructor, `$&
  // Each ring position uses the same two aliasing views on every cycle.
  // Retain all 192 FIR taps and their original floating-point operation order.
  this.firViewsLeft = [];
  this.firViewsRight = [];
  for (var index = 0; index < FIR_SIZE / DECIMATE_FACTOR - 1; index++) {
    var offset = FIR_SIZE - index * DECIMATE_FACTOR;
    this.firViewsLeft.push(this.firLeft.subarray(offset));
    this.firViewsRight.push(this.firRight.subarray(offset));
  }
`);
  return source.replace(process, `  var firLeft = this.firViewsLeft[this.firIndex];
  var firRight = this.firViewsRight[this.firIndex];`);
}
