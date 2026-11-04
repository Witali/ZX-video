// Headless characterization of the real WebGL vertex producer. A separate
// browser fixture verifies actual GPU pixels, bank copies and context recovery.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';

const source = fs.readFileSync('web/vendor/zx-dream.js', 'utf8');
const context = vm.createContext({});
vm.runInContext(source, context);
const prototype = vm.runInContext('WebGLRenderer.prototype', context);
let comparedVertices = 0, uploadedBytes = 0, cases = 0;
function check(layer, flash, semicolors, addresses) {
  const data = Uint8Array.from({ length: 6912 }, (_, a) => (a * 73 + (a >>> 3) * 19) & 255);
  const dirty = new Uint8Array(6144);
  for (const address of addresses) dirty[address] = 1;
  const calls = [];
  const gl = {
    ARRAY_BUFFER: 34962, TRIANGLES: 4,
    bufferSubData: (target, offset, view) => calls.push(['upload', target, offset, Array.from(view)]),
    drawArrays: (...args) => calls.push(['draw', ...args]),
    flush: () => calls.push(['flush']),
    finish: () => assert.fail('Playback must not synchronously wait for the GPU'),
    bufferData: () => assert.fail('Bank storage must not be reallocated on redraw')
  };
  const renderer = Object.create(prototype);
  renderer._glBuffer = new Float32Array(6144 * 24).fill(NaN);
  renderer._layer0Ctx = layer ? null : gl;
  renderer._layer1Ctx = layer ? gl : null;
  renderer._presentationChanged = false;
  renderer.drawData(layer, data, dirty, flash, semicolors);
  assert(dirty.every(value => value === 0), 'Every supplied dirty byte must be consumed');
  if (!addresses.length) {
    assert.deepEqual(calls, []);
    assert.equal(renderer._presentationChanged, false);
    return;
  }
  const expected = [];
  for (const address of [...addresses].sort((a, b) => a - b)) {
    const x = address % 32;
    // Decode the three interleaved scanline fields independently of drawData.
    const y = (address >>> 11) * 64 + ((address >>> 5) & 7) * 8 + ((address >>> 8) & 7);
    let attr = data[6144 + Math.floor(y / 8) * 32 + x];
    attr = (attr & (flash ? 255 : 127)) | (semicolors ? 0 : 64);
    if (attr & 128) attr = (attr & 64) | ((attr & 7) << 3) | ((attr >>> 3) & 7);
    const sx = data[address];
    expected.push(x, y, sx, attr, x + 1, y, sx + 1, attr,
      x + 1, y + 1, sx + 1, attr + 1, x, y, sx, attr,
      x, y + 1, sx, attr + 1, x + 1, y + 1, sx + 1, attr + 1);
  }
  assert.deepEqual(calls, [['upload', gl.ARRAY_BUFFER, 0, expected],
    ['draw', gl.TRIANGLES, 0, addresses.length * 6], ['flush']]);
  assert.equal(renderer._presentationChanged, true);
  comparedVertices += addresses.length * 6;
  uploadedBytes += expected.length * 4;
  cases++;
}
for (const layer of [0, 1]) for (const flash of [false, true]) for (const semicolors of [false, true]) {
  check(layer, flash, semicolors, Array.from({ length: 6144 }, (_, a) => a));
  check(layer, flash, semicolors, [0, 31, 32, 255, 256, 511, 2047, 2048, 6143]);
  check(layer, flash, semicolors, []);
}
const report = { scope: 'WebGL vertex production and API calls; browser GPU checks are separate',
  nonemptyCases: cases, emptyCases: 8, banks: [5, 7], flashAndSemicolorCombinations: 4,
  comparedVertices, uploadedBytes, exactVertices: true, perRedrawGpuBufferAllocations: 0,
  perDirtyByteTemporaryArrays: 0, playbackFinishCalls: 0,
  coreSha256: createHash('sha256').update(source).digest('hex') };
console.log(JSON.stringify(report, null, 2));
if (process.argv[2]) fs.writeFileSync(process.argv[2], JSON.stringify(report, null, 2) + '\n');
