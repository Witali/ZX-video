// Read-only full-volume comparison with the project's saved Fuse screen identities.
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import { resolve, join } from 'node:path';
import assert from 'node:assert/strict';
const dataRoot = resolve(process.argv[2] || '.');
const part = Number(process.argv[3] || 2);
const limit = Number(process.argv[4] || 700) * 1000;
const stem = `ZX-video-refined_part${String(part).padStart(2, '0')}`;
const evidence = join(dataRoot, 'toolkit/refined_four_evidence');
const json = name => JSON.parse(gunzipSync(fs.readFileSync(join(evidence, name))));
const metadata = json(`${stem}.json.gz`);
const expected = json(`work-${stem}-screens.json.gz`);
const timers = new Map();
let now = 0, id = 0;
const c = vm.createContext({ console, ZXContext: { debugMode: false },
  Date: class extends Date { static now() { return now; } },
  setInterval: fn => { timers.set(++id, fn); return id; }, clearInterval: id => timers.delete(id) });
for (const name of ['ayumi.js', 'zx-dream.js']) vm.runInContext(fs.readFileSync(`web/vendor/${name}`, 'utf8'), c);
c.loadServerFile = async name => new Uint8Array(fs.readFileSync(`web/vendor/roms/${name}`));
vm.runInContext(`
var h={bus:new ZX_Bus(),cpu:new ZX_Z80(),clock:new ZX_Clock(),rom:new ZX_ROM(),ram:new ZX_RAM(),fe:new ZX_PortFE(),paging:new ZX_Port7FFD(),keyboard:new ZX_Keyboard(),disk:new ZX_BetaDisk(),drives:Array.from({length:4},()=>new ZX_Floppy())};
h.cpu.connect(h.bus);h.clock.connect(h.bus,h.cpu);
[h.rom,h.ram,h.fe,h.paging,h.keyboard].forEach(d=>d.connect(h.bus));
h.disk.connect(h.bus,h.clock,h.drives);
h.bus.opt('TSTATES_PER_INTRQ',70908);h.bus.opt('INTRQ_PERIOD',20);h.bus.opt('EXTENDED_MEMORY',0);
var shadow=Array.from({length:8},()=>new Uint8Array(16384));
h.bus.on_mem_write((a,v)=>{if(a>=0x4000){var bank=a<0x8000?5:a<0xc000?2:h.bus.var_read('port_7ffd_value')&7;shadow[bank][a&0x3fff]=v;}});
`, c);
await vm.runInContext('h.rom.get_ready$()', c);
const screenErrors = [], frames = new Set(), publications = [];
c.labels = metadata.player_labels;
c.ready = metadata.native_ready_pcs;
c.capture = (frame, bytes) => {
  if (frames.has(frame)) return;
  frames.add(frame);
  const hash = crypto.createHash('sha256').update(Uint8Array.from(bytes)).digest('hex');
  if (hash !== expected.screen_sha256[frame]) screenErrors.push({ frame, hash, expected: expected.screen_sha256[frame] });
};
c.publish = () => publications.push(vm.runInContext('h.clock.get_tstates()', c));
vm.runInContext(`
h.bus.on_instruction_read(a=>{if(ready.includes(a)){
var frame=h.bus.mem_read(labels.published)|(h.bus.mem_read(labels.published+1)<<8);
var bank=h.bus.var_read('port_7ffd_value')&8?5:7;
capture(frame,Array.from(shadow[bank].slice(0,6912)));}});
h.bus.on_io_write((a,v)=>{if((a&0x8002)===0&&h.cpu.get_state().pc===labels.publish_out+2)publish();});
`, c);
c.image = new Uint8Array(fs.readFileSync(join(dataRoot, `${stem}.trd`)));
assert.equal(crypto.createHash('sha256').update(c.image).digest('hex'), expected.trd_sha256);
vm.runInContext('h.drives[0].insertTRD(image);h.bus.reset(2);h.clock.run()', c);
let published = 0;
while (now < limit && published < metadata.frames) {
  const end = now + 1000;
  while (now < end) { now += 4; for (const fn of [...timers.values()]) fn(); }
  published = vm.runInContext('h.bus.mem_read(labels.published)|(h.bus.mem_read(labels.published+1)<<8)', c);
}
const state = vm.runInContext('({pc:h.cpu.get_state().pc,ayTicks:h.bus.mem_read(labels.audio_ticks_played)|(h.bus.mem_read(labels.audio_ticks_played+1)<<8),disk:h.disk.get_state()})', c);
const deltas = publications.map((t,i) => t - publications[0] - i * 5 * 70908);
const report = { scope: 'Complete screen-byte comparison; instruction-boundary publication callbacks, not physical hardware certification',
  part, diskSha256: expected.trd_sha256, framesExpected: metadata.frames, screensCompared: frames.size,
  published, publicationCallbacks: publications.length, screenErrors,
  emulatedSeconds: now / 1000, playbackSeconds: (publications.at(-1) - publications[0]) / 3545400,
  lateCallbacksBeyond64T: deltas.filter(t => t > 64).length,
  maximumCallbackDeviationT: Math.max(...deltas), ...state };
console.log(JSON.stringify(report, null, 2));
if (process.argv[5]) fs.writeFileSync(process.argv[5], JSON.stringify(report, null, 2) + '\n');
assert.equal(published, metadata.frames, 'Every frame must finish');
assert.equal(frames.size, metadata.frames, 'Every full screen must be compared');
assert.equal(publications.length, metadata.frames, 'Every publication OUT must be observed');
assert.equal(screenErrors.length, 0, 'Screen identities must match Fuse');
