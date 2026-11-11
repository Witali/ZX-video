// Exercise beeper/sample ties, packet phase across uneven wakes, cold reset
// with a partial packet, and AY port reads on both CPU paths.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const binary = await readFile(new URL('../vendor/spectrum-z80.wasm', import.meta.url));
const cpuHz = 70908 * 50, sampleHz = 44100, block = 512;

async function machine(program) {
  let core, origin = 0, limit;
  const writes = [], packets = [];
  const { instance } = await WebAssembly.instantiate(binary, { spectrum: {
    in_port: () => 0xfe,
    out_port(port, value, time) { writes.push({ port, value, time: origin + time }); },
    trdos() {},
    dispatch: () => limit,
    audio_block(left, right, count, time) {
      const samples = pointer => new Float32Array(core.memory.buffer, pointer, count).slice();
      packets.push({ left: samples(left), right: samples(right), time });
    }
  } });
  core = instance.exports;
  new Uint8Array(core.memory.buffer).set(program, core.rom_ptr() + 2 * 0x4000);
  core.native_audio(true);
  core.reset(0);
  return { core, writes, packets, run(tstates, fast) {
    const wakes = [97, 3933, 13017, 527];
    for (let wake = 0; tstates > 0; wake++) {
      limit = Math.min(tstates, wakes[wake % wakes.length]);
      core.set_ticks(0);
      assert.equal(core.run(limit, fast), limit);
      origin += limit;
      tstates -= limit;
    }
  } };
}

function checkBeeper(writes, packets, origin) {
  let write = 0, sample = 0, value = 0, ties = 0;
  for (const packet of packets) {
    assert.equal(packet.left.length, block);
    assert.deepEqual(packet.left, packet.right);
    for (const actual of packet.left) {
      const deadline = origin + Math.ceil(++sample * cpuHz / sampleHz);
      while (write < writes.length && writes[write].time <= deadline) {
        const event = writes[write++];
        assert.equal(event.port, 0xfe);
        value = event.value & 16 ? Math.fround(.35) : 0;
        if (event.time === deadline) ties++;
      }
      assert.equal(actual, value, `Beeper sample ${sample} at T=${deadline}`);
    }
    assert.equal(packet.time, origin + Math.ceil(sample * cpuHz / sampleHz));
  }
  assert.equal(packets.length, 2);
  assert(ties > 0, 'At least one OUT must share a sample deadline');
}

for (const fast of [false, true]) {
  // LD BC,00FE; LD A,10; loop: OUT (C),A; XOR 10; JP loop.
  const beeper = await machine([0x01, 0xfe, 0, 0x3e, 0x10, 0xed, 0x79, 0xee, 0x10, 0xc3, 5, 0]);
  const duration = 96013; // two packets and part of a third
  beeper.run(duration, fast);
  checkBeeper(beeper.writes, beeper.packets, 0);
  beeper.core.reset(0);
  beeper.writes.length = beeper.packets.length = 0;
  beeper.run(duration, fast);
  checkBeeper(beeper.writes, beeper.packets, duration);

  // AY fine/coarse register mask combined with the other devices' bus value.
  const readback = await machine([
    0x01, 0xfd, 0xff, 0x3e, 1, 0xed, 0x79,
    0x01, 0xfd, 0xbf, 0x3e, 0xff, 0xed, 0x79,
    0x01, 0xfd, 0xff, 0xed, 0x78, 0x32, 0x00, 0x40, 0x76
  ]);
  readback.run(800, fast);
  assert.equal(readback.core.read(0x4000), 0x0e);
}
console.log('WASM audio matches exact beeper strobes, reset phase and AY readback on both CPU paths.');
