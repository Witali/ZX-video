// Deterministic integration smoke: real ROM, TRD sectors, Z80 and AY synthesis.
// It measures emulated progress, not physical-disk or browser audio accuracy.
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
const root = resolve(process.argv[2] || '.tmp/web-site');
const timers = new Map();
let now = 0, timerId = 0;
const context = vm.createContext({ console, performance: { now: () => now },
  Date: class extends Date { static now() { return now; } },
  setInterval: fn => { timers.set(++timerId, fn); return timerId; },
  clearInterval: id => timers.delete(id),
  loadServerFile: async name => new Uint8Array(await readFile(resolve(root, 'vendor/roms', name))),
  ZXContext: { debugMode: false } });
for (const name of ['ayumi.js', 'zx-dream.js']) vm.runInContext(await readFile(resolve(root, 'vendor', name), 'utf8'), context);
context.loadServerFile = async name => new Uint8Array(await readFile(resolve(root, 'vendor/roms', name)));
vm.runInContext(`
var h = { bus: new ZX_Bus(), cpu: new ZX_Z80(), clock: new ZX_Clock(), rom: new ZX_ROM(),
ram: new ZX_RAM(), fe: new ZX_PortFE(), paging: new ZX_Port7FFD(), keyboard: new ZX_Keyboard(),
disk: new ZX_BetaDisk(), drives: [new ZX_Floppy(), new ZX_Floppy(), new ZX_Floppy(), new ZX_Floppy()], psg: new ZX_PSG() };
h.cpu.connect(h.bus); h.clock.connect(h.bus,h.cpu);
[h.rom,h.ram,h.fe,h.paging,h.keyboard].forEach(d => d.connect(h.bus));
h.disk.connect(h.bus,h.clock,h.drives); h.psg.connect(h.bus,h.clock);
h.bus.opt('TSTATES_PER_INTRQ',70908); h.bus.opt('INTRQ_PERIOD',20);
h.bus.opt('EXTENDED_MEMORY',0);
h.psg.applySettings(true,0.35,1,0,0,1773400,512,0.7);
var audio = { packets: 0, nonzero: 0, peak: 0 };
var ayDataWrites = 0;
h.bus.on_io_write(function () { ayDataWrites++; }, { mask: 0xffff, value: 0xbffd });
var songAudio=null;
h.psg.get_onDataReady().subscribe(p => { audio.packets++; for (var i=0;i<p.sampleCount;i++) {
var left=p.left[i],right=p.right[i],a=Math.abs(left)+Math.abs(right);
if(a>0.0001)audio.nonzero++; audio.peak=Math.max(audio.peak,a);
if(songAudio){songAudio.samples++;songAudio.leftEnergy+=left*left;songAudio.rightEnergy+=right*right;
songAudio.leftPeak=Math.max(songAudio.leftPeak,Math.abs(left));songAudio.rightPeak=Math.max(songAudio.rightPeak,Math.abs(right));}
} });
`, context);
await vm.runInContext('h.rom.get_ready$()', context);
function advance(ms) { const until = now + ms; while (now < until) { now += 4; for (const fn of [...timers.values()]) fn(); } }
const music = new Uint8Array(await readFile(resolve(root, 'disks/ZX-Music-Menu.trd')));
context.image = music;
vm.runInContext('h.drives[0].insertTRD(image); h.bus.reset(2); h.clock.run()', context);
advance(60000);
const screen = vm.runInContext('Array.from({length:6912},(_,i)=>h.bus.mem_read(0x4000+i))', context);
assert(screen.slice(0, 6144).some(v => v !== 0), 'Boot must write screen pixels');
assert(screen.slice(6144).some(v => v !== 0), 'Boot must set screen attributes');
// The menu renders ROM glyphs: identify its title pixels, not a generic ROM prompt.
const rom = await readFile(resolve(root, 'vendor/roms/48.rom'));
let matching = 0;
for (const [column, character] of [...'SPECTRUM MUSIC'].entries()) {
  const x = 6 + column;
  let equal = true;
  for (let row = 0; row < 8; row++) {
    const y = 8 + row;
    const address = ((y & 0xc0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2) | x;
    if (screen[address] !== rom[0x3c00 + character.charCodeAt(0) * 8 + row]) equal = false;
  }
  if (equal) matching++;
}
assert.equal(matching, 'SPECTRUM MUSIC'.length, 'Music-menu title must reach the screen');
const autoplay = vm.runInContext('({ ayDataWrites, nonzeroSamples: audio.nonzero })', context);
assert(autoplay.ayDataWrites > 100, 'Cold boot must play AY music before any keyboard input');
assert(autoplay.nonzeroSamples > 100, 'Autoplay must produce actual sound');
const excerpts=[];
for(const [name,bit] of [['Lumiere',0],['Alicia',1]]) {
  vm.runInContext('songAudio={samples:0,leftEnergy:0,rightEnergy:0,leftPeak:0,rightPeak:0}',context);
  vm.runInContext(`h.keyboard.switchKeys([{index:3,bit:${bit}}],true)`,context);advance(100);
  vm.runInContext(`h.keyboard.switchKeys([{index:3,bit:${bit}}],false)`,context);advance(3000);
  const stats=vm.runInContext('songAudio',context);
  assert(stats.leftEnergy>0.01&&stats.rightEnergy>0.01,`${name} must have nonzero audio in both channels`);
  assert(stats.leftPeak<1&&stats.rightPeak<1,`${name} must not clip`);
  excerpts.push({name,samples:stats.samples,leftRms:Math.sqrt(stats.leftEnergy/stats.samples),
    rightRms:Math.sqrt(stats.rightEnergy/stats.samples),leftPeak:stats.leftPeak,rightPeak:stats.rightPeak});
}
const audio = vm.runInContext('audio', context);
assert(audio.nonzero > 100, 'The menu must produce actual nonzero AY/beeper samples');
const memory = vm.runInContext('Array.from({length:65536},(_,i)=>h.bus.mem_read(i))', context);
const pc = vm.runInContext('h.cpu.get_state().pc', context);
context.image = new Uint8Array(await readFile(resolve(root, 'disks/ZX-video-refined_part02.trd')));
vm.runInContext('h.clock.stop(); h.drives[0].insertTRD(image)', context);
assert.deepEqual(vm.runInContext('Array.from({length:65536},(_,i)=>h.bus.mem_read(i))', context), memory, 'Swap must preserve the mapped RAM and ROM');
assert.equal(vm.runInContext('h.cpu.get_state().pc', context), pc, 'Swap must preserve PC');
const report = { scope: 'Deterministic upstream-core smoke, not full release timing', musicTitleGlyphs: matching,
  emulatedMilliseconds: now, autoplayBeforeInput: autoplay, audio: { ...audio }, songExcerpts:excerpts,
  coreSha256:createHash('sha256').update(await readFile(resolve(root,'vendor/zx-dream.js'))).digest('hex'),
  diskSha256:createHash('sha256').update(music).digest('hex'),swapPreservedMemoryAndPC: true };
console.log(JSON.stringify(report, null, 2));
if (process.argv[3]) await writeFile(process.argv[3], JSON.stringify(report, null, 2) + '\n');
