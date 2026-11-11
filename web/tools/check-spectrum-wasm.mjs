// Real-ROM Expedition 33 cold boot, keyboard, two stereo excerpts and 50 Hz.
// Advance virtual wall time in the normal clock's 4-ms wakes. Time the CPU,
// disk, AY, and display snapshots together with a headless renderer.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import vm from 'node:vm';
import { createWasmCpu } from '../wasm-cpu.js';

const root = resolve(process.argv[2] || '.tmp/web-site');
const output = process.argv[3];
const pairs = Number(process.argv[4] || 5);
const hash = data => createHash('sha256').update(data).digest('hex');
const read = path => readFile(resolve(root, path));
const [ayumi, zxDream, binary, disk, font] = await Promise.all([
  read('vendor/ayumi.js'), read('vendor/zx-dream.js'), read('vendor/spectrum-z80.wasm'),
  read('disks/Expedition-33-Demo.trd'), read('vendor/roms/48.rom')
]);
const loadRom = name => read(`vendor/roms/${name}`);

async function run(backend) {
  let now = 0, wake;
  const context = vm.createContext({
    console, performance: { now: () => now },
    setInterval: callback => { wake = callback; return 1; },
    clearInterval: () => { wake = null; },
    ZXContext: { debugMode: false }
  });
  vm.runInContext(ayumi.toString(), context);
  vm.runInContext(zxDream.toString(), context);
  context.loadServerFile = loadRom;
  context.diskBytes = disk;
  context.wasm = backend === 'js' ? null : await createWasmCpu(loadRom,
    { binary, fast: backend !== 'wasm-tick', audio: backend !== 'wasm-js-ay' });
  vm.runInContext(`
    var h = { bus: new ZX_Bus(), clock: new ZX_Clock(), cpu: wasm || new ZX_Z80(),
      keyboard: new ZX_Keyboard(), disk: new ZX_BetaDisk(), paging: new ZX_Port7FFD(), fe: new ZX_PortFE(),
      drives: Array.from({length:4}, () => new ZX_Floppy()), psg: wasm?.audio || new ZX_PSG(), display: new ZX_Display() };
    var frames = [], ayWrites = [], packets = [], firstSound = null, ready;
    var visible, menu, screenMilestones = [];
    // Capture exactly what the selected screen bank passes to the renderer.
    NullRenderer = function () {
      this.set_threading = () => {};
      this.drawData = (layer, data, dirty) => {
        frames.push(h.clock.get_tstates());
        visible = data;
        dirty.fill(0);
      };
      this.displayLayer = this.drawBorder = () => {};
    };
    h.cpu.connect(h.bus);
    h.clock.connect(h.bus, h.cpu);
    if (wasm) h.display.set_screen_source(wasm.screen);
    else {
      var rom = new ZX_ROM();
      rom.connect(h.bus);
      new ZX_RAM().connect(h.bus);
      ready = rom.get_ready$();
    }
    [h.keyboard, h.fe, h.paging].forEach(device => device.connect(h.bus));
    h.display.connect(h.bus, h.clock);
    h.disk.connect(h.bus, h.clock, h.drives);
    if (!wasm?.audio) h.psg.connect(h.bus, h.clock);
    h.bus.opt('TSTATES_PER_INTRQ', 70908);
    h.bus.opt('INTRQ_PERIOD', 20);
    h.bus.opt('EXTENDED_MEMORY', 0);
    h.bus.opt('SEMICOLORS', true);
    if (!wasm?.audio) h.psg.applySettings(true, .35, 1, 0, 0, 1773400, 512, .7);
    h.bus.on_io_write((port, value) => ayWrites.push(value), { mask: 65535, value: 0xbffd });
    h.psg.get_onDataReady().subscribe(packet => {
      packets.push(packet);
      if (firstSound === null && packet.left.some(sample => Math.abs(sample) > .0001))
        firstSound = packet.tstates ?? h.clock.get_tstates();
    });
    function start() { h.drives[0].insertTRD(diskBytes); h.bus.reset(2); h.clock.run(); }
    function key(row, bit, down) { h.keyboard.switchKeys([{index:row, bit}], down); }
    function menuSnapshot() { menu = visible.slice(); }
    function sampleScreen() { screenMilestones.push(visible.slice()); }
  `, context);
  await context.ready;
  const advance = milliseconds => {
    const end = now + milliseconds;
    while (now < end) { now += 4; wake(); }
  };
  const start = performance.now();
  context.start();
  advance(20_000);
  context.sampleScreen();
  advance(20_000);
  context.sampleScreen();
  advance(20_000);
  context.sampleScreen();
  const coldWrites = context.ayWrites.length;
  const excerpts = [];
  for (const [bit, name] of ['Lumiere', 'Alicia'].entries()) {
    context.key(7, 0, true); advance(400);
    context.key(7, 0, false); advance(100);
    context.menuSnapshot();
    const firstPacket = context.packets.length;
    context.key(3, bit, true); advance(100);
    context.key(3, bit, false); advance(3000);
    excerpts.push({ name, firstPacket, endPacket: context.packets.length });
  }
  context.h.clock.stop();
  const wallMs = performance.now() - start;

  assert(coldWrites > 100, `${backend}: TR-DOS did not start AY music automatically`);
  assert(context.firstSound !== null && context.firstSound < 60 * 3545400, `${backend}: no boot audio`);
  for (const [column, character] of [...'EXPEDITION 33 DEMO'].entries()) {
    for (let row = 0; row < 8; row++) {
      const offset = (row << 8) + 32 + 7 + column;
      assert.equal(context.menu[offset], font[0x3c00 + character.charCodeAt(0) * 8 + row],
        `${backend}: Space did not reveal the demo menu`);
    }
  }
  const screens = Array.from(context.screenMilestones, hash);
  assert.equal(new Set(screens).size, screens.length, `${backend}: slideshow is static`);
  const frames = Array.from(context.frames);
  const maxFrameError = frames.reduce((max, time, index) =>
    Math.max(max, Math.abs(time - frames[0] - index * 70908)), 0);
  assert(frames.length >= Math.floor(now / 20) && maxFrameError <= (backend === 'js' ? 24 : 1),
    `${backend}: ${frames.length} frames, up to ${maxFrameError} T from the native phase`);
  const pcm = createHash('sha256');
  for (const [index, packet] of context.packets.entries()) {
    if (context.wasm?.audio)
      assert.equal(packet.tstates, Math.ceil((index + 1) * 512 * 3545400 / 44100), 'WASM audio block deadline');
    pcm.update(Buffer.from(packet.left.buffer));
    pcm.update(Buffer.from(packet.right.buffer));
  }
  for (const excerpt of excerpts) {
    let left = 0, right = 0, count = 0;
    for (const packet of context.packets.slice(excerpt.firstPacket, excerpt.endPacket)) {
      for (let i = 0; i < packet.sampleCount; i++) {
        left += packet.left[i] ** 2;
        right += packet.right[i] ** 2;
        count++;
      }
    }
    assert(count > 44_100 * 3 && left > .01 && right > .01, `${backend}: missing stereo samples`);
    excerpt.samples = count;
    excerpt.rms = [Math.sqrt(left / count), Math.sqrt(right / count)];
  }
  return {
    backend, wallMs, emulatedMs: now, diskSha256: hash(disk),
    identity: {
      firstSoundT: context.firstSound, coldWrites, aySha256: hash(Buffer.from(context.ayWrites)),
      frames: frames.length, frameHz: (frames.length - 1) * 3545400 / (frames.at(-1) - frames[0]),
      maxFrameErrorT: maxFrameError, pcmPackets: context.packets.length, pcmSha256: pcm.digest('hex'),
      menuSha256: hash(context.menu), screens, excerpts
    }
  };
}

const results = [];
const reference = await run('wasm-tick');
const js = await run('js');
let jsAyIdentity;
for (const key of ['coldWrites', 'aySha256', 'frames', 'pcmPackets', 'menuSha256', 'screens'])
  assert.deepEqual(js.identity[key], reference.identity[key], `JavaScript workload differs in ${key}`);
for (let pair = 0; pair < pairs; pair++) {
  for (const backend of pair % 2 ? ['wasm', 'wasm-js-ay'] : ['wasm-js-ay', 'wasm']) {
    const result = await run(backend);
    if (backend === 'wasm') assert.deepEqual(result.identity, reference.identity,
      'Fused WASM must match its independent T-by-T execution');
    else {
      jsAyIdentity ??= result.identity;
      assert.deepEqual(result.identity, jsAyIdentity, 'JavaScript AY workload changed between pairs');
      for (const key of ['coldWrites', 'aySha256', 'frames', 'pcmPackets', 'menuSha256', 'screens', 'pcmSha256']) {
        assert.deepEqual(result.identity[key], reference.identity[key],
          `JavaScript and WASM must perform the same work (${key})`);
      }
    }
    results.push({ pair: pair + 1, backend, wallMs: result.wallMs });
    console.error(`${backend} ${pair + 1}/${pairs}: ${result.wallMs.toFixed(1)} ms`);
  }
}
const median = backend => results.filter(run => run.backend === backend).map(run => run.wallMs)
  .sort((a, b) => a - b)[Math.floor(pairs / 2)];
const jsAyMs = median('wasm-js-ay'), wasmMs = median('wasm');
const report = {
  scope: '67.2 s, real ROM/TRD/AY, deterministic clock, headless display, no physical audio or GPU timing',
  node: process.version, jsSha256: hash(zxDream), wasmSha256: hash(binary),
  emulatedMs: reference.emulatedMs, diskSha256: reference.diskSha256,
  medians: { jsAyMs, wasmMs, reductionPercent: 100 * (1 - wasmMs / jsAyMs) },
  jsIdentity: js.identity, jsAyIdentity, wasmIdentity: reference.identity, perTickWasmMs: reference.wallMs, results
};
if (output) await writeFile(output, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ ...report.medians, identity: reference.identity }, null, 2));
