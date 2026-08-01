"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");

const htmlPath = path.join(__dirname, "ay-speech-tap-generator.html");
const html = fs.readFileSync(htmlPath, "utf8");
const match = html.match(/<script>([\s\S]*?)<\/script>/);
assert(match, "inline script was not found");

global.window = {};
global.requestAnimationFrame = callback => setImmediate(callback);
new Function(match[1])();
const core = global.window.AySpeechTapCore;
assert(core, "core API was not exported");

const states = Array.from({ length: 100 }, (_, index) => ({
  periods: [400 + index, 100 + index, 40 + index],
  volumes: [15, 10, 7],
  noise: index % 31 + 1,
  mixer: index % 3 ? 0x38 : 0x18
}));

const tap = core.buildTap(states, "TESTVOICE");
const blocks = core.parseTapeBlocks(tap);
assert.strictEqual(blocks.length, 4, "TAP must contain BASIC and CODE header/data pairs");
assert.strictEqual(blocks[0][0], 0x00, "BASIC header flag");
assert.strictEqual(blocks[0][1], 0x00, "BASIC file type");
assert.strictEqual(blocks[1][0], 0xFF, "BASIC data flag");
assert(blocks[1].includes(0xB0), "BASIC numeric constants must use VAL strings");
assert.strictEqual(blocks[2][0], 0x00, "CODE header flag");
assert.strictEqual(blocks[2][1], 0x03, "CODE file type");
assert.strictEqual(blocks[3][0], 0xFF, "CODE data flag");

const basicAutostart = blocks[0][14] | (blocks[0][15] << 8);
assert.strictEqual(basicAutostart, 10, "BASIC must autostart at line 10");

const codeLength = blocks[2][12] | (blocks[2][13] << 8);
const loadAddress = blocks[2][14] | (blocks[2][15] << 8);
assert.strictEqual(loadAddress, core.LOAD_ADDRESS, "CODE load address");
assert.strictEqual(codeLength, blocks[3].length - 2, "CODE header length");

const packed = core.encodeStates(states);
const codePayload = blocks[3].subarray(1, blocks[3].length - 1);
assert.deepStrictEqual(
  Array.from(codePayload.subarray(codePayload.length - packed.length)),
  Array.from(packed),
  "packed AY states must end the CODE block"
);

assert(core.maxFrameCount() > 5000, "single TAP should hold about 100 seconds at 50 Hz");

(async () => {
  const sampleRate = 8000;
  const samples = new Float32Array(sampleRate / 5);
  for (let i = 0; i < samples.length; i++) {
    const time = i / sampleRate;
    samples[i] = 0.45 * Math.sin(2 * Math.PI * 120 * time)
      + 0.18 * Math.sin(2 * Math.PI * 480 * time)
      + 0.12 * Math.sin(2 * Math.PI * 1440 * time);
  }
  const analyzed = await core.analyzeSamples(samples, () => {});
  assert.strictEqual(analyzed.length, 10, "20 ms analysis frames");
  assert(analyzed.some(state => state.volumes.some(volume => volume > 0)), "synthetic voice must produce audible states");
  core.parseTapeBlocks(core.buildTap(analyzed, "SYNTHETIC"));
  console.log(`AY speech TAP generator OK: ${tap.length} bytes, ${core.maxFrameCount()} max frames`);
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
