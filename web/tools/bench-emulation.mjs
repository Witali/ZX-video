// Host benchmark only. Both variants execute the same complete emulated work.
// Run after the normal site build; pass the authenticated unpatched Ayumi file.
import fs from 'node:fs';
import vm from 'node:vm';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { performance } from 'node:perf_hooks';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { patchAyumi } from './patch-ayumi.mjs';

const sha = data => createHash('sha256').update(data).digest('hex');
const worker = process.argv[2] === '--worker';
if (worker) {
  const [kind, ayumiPath, siteRoot] = process.argv.slice(3);
  const timers = new Map();
  let now = 0, timerId = 0;
  const context = vm.createContext({ console, performance: { now: () => now },
    setInterval: fn => { timers.set(++timerId, fn); return timerId; },
    clearInterval: id => timers.delete(id), ZXContext: { debugMode: false },
    loadServerFile: async name => new Uint8Array(fs.readFileSync(resolve(siteRoot, 'vendor/roms', name))) });
  vm.runInContext(fs.readFileSync(ayumiPath, 'utf8'), context);
  if (kind === 'psg') {
    vm.runInContext(`var chip=new Ayumi();chip.configure(false,1773400,44100);
      for(var c=0;c<3;c++){chip.setPan(c,[.1,.5,.9][c],true);chip.setTone(c,65+c*120);
      chip.setVolume(c,12-c);chip.setMixer(c,0,0,c===2);}chip.setNoise(11);chip.setEnvelope(54);chip.setEnvelopeShape(14);
      function advanceChip(count){for(var i=0;i<count;i++){chip.process();chip.removeDC();}}
      advanceChip(100000);`, context);
  } else {
    // Optional core path lets CPU experiments reuse this exact real-machine workload.
    vm.runInContext(fs.readFileSync(resolve(process.argv[6] || siteRoot + '/vendor/zx-dream.js'), 'utf8'), context);
    // Upstream common.js declares its own XHR loader; replace it only in this
    // Node harness, after evaluation, with the same authenticated local ROMs.
    context.loadServerFile = async name => new Uint8Array(fs.readFileSync(resolve(siteRoot, 'vendor/roms', name)));
    vm.runInContext(`var h={bus:new ZX_Bus(),cpu:new ZX_Z80(),clock:new ZX_Clock(),rom:new ZX_ROM(),
      ram:new ZX_RAM(),fe:new ZX_PortFE(),paging:new ZX_Port7FFD(),keyboard:new ZX_Keyboard(),
      display:new ZX_Display(),disk:new ZX_BetaDisk(),drives:Array.from({length:4},()=>new ZX_Floppy()),psg:new ZX_PSG()};
      h.cpu.connect(h.bus);h.clock.connect(h.bus,h.cpu);
      [h.rom,h.ram,h.fe,h.paging,h.keyboard].forEach(d=>d.connect(h.bus));
      h.display.connect(h.bus,h.clock);h.disk.connect(h.bus,h.clock,h.drives);h.psg.connect(h.bus,h.clock);
      h.bus.opt('TSTATES_PER_INTRQ',70908);h.bus.opt('INTRQ_PERIOD',20);h.bus.opt('EXTENDED_MEMORY',0);
      h.psg.applySettings(true,.35,1,0,0,1773400,512,.7);
      var packets=[];h.psg.get_onDataReady().subscribe(p=>packets.push([p.left,p.right]));`, context);
    await vm.runInContext('h.rom.get_ready$()', context);
    context.diskImage = new Uint8Array(fs.readFileSync(resolve(siteRoot,
      kind === 'movie' ? 'disks/ZX-video-refined_part02.trd' : 'disks/ZX-Music-Menu.trd')));
  }
  const cpuStart = process.cpuUsage(), start = performance.now();
  if (kind === 'psg') {
    vm.runInContext('advanceChip(3000000)', context);
  } else {
    vm.runInContext('h.drives[0].insertTRD(diskImage);h.bus.reset(2);h.clock.run()', context);
    function advance(ms) { const until = now + ms; while (now < until) { now += 4; for (const fn of [...timers.values()]) fn(); } }
    advance(60000);
    for (const bit of kind === 'movie' ? [] : [0, 1]) {
      vm.runInContext(`h.keyboard.switchKeys([{index:3,bit:${bit}}],true)`, context);advance(100);
      vm.runInContext(`h.keyboard.switchKeys([{index:3,bit:${bit}}],false)`, context);advance(3000);
    }
    vm.runInContext('h.clock.stop()', context);
  }
  const elapsedMs = performance.now() - start, cpu = process.cpuUsage(cpuStart);
  // Hash output after timing, rather than spending most of the benchmark in
  // a per-sample diagnostics callback, which the initial profiler exposed.
  let identity;
  if (kind === 'psg') {
    identity = vm.runInContext('({left:chip.left,right:chip.right,x:chip.x,noise:chip.noise,firIndex:chip.firIndex})', context);
  } else {
    const pcmHash = createHash('sha256');
    for (const packet of context.packets) for (const channel of packet) pcmHash.update(Buffer.from(channel.buffer));
    const memory = vm.runInContext('Uint8Array.from({length:65536},(_,a)=>h.bus.mem_read(a))', context);
    identity = { pcmSha256: pcmHash.digest('hex'), packets: context.packets.length,
      memorySha256: sha(memory), cpu: vm.runInContext('h.cpu.get_state()', context),
      clockTstates: vm.runInContext('h.clock.get_tstates()', context),
      disk: vm.runInContext('h.disk.get_state()', context), psg: vm.runInContext('h.psg.getState()', context) };
  }
  console.log(JSON.stringify({ kind, elapsedMs, cpuMs: (cpu.user + cpu.system) / 1000, identity }));
} else {
  const originalPath = resolve(process.argv[2] || '.tmp/baseline-ayumi.js');
  const original = fs.readFileSync(originalPath, 'utf8');
  assert.equal(sha(original), 'bd189a818201aa57e9185d3c5bd809ead8cd6ac6a0a9b9ee8df17d0ef483326d');
  const candidatePath = resolve('.tmp/benchmark-ayumi.js');
  fs.writeFileSync(candidatePath, patchAyumi(original));
  const siteRoot = resolve(process.argv[3] || '.tmp/web-site');
  const pairs = Number(process.argv[4] || 5), results = [], identities = {};
  for (const kind of ['psg', 'machine']) {
    let expected;
    for (let pair = 0; pair < pairs; pair++) for (const variant of pair & 1 ? ['after', 'before'] : ['before', 'after']) {
      const run = spawnSync(process.execPath, [new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1'),
        '--worker', kind, variant === 'before' ? originalPath : candidatePath, siteRoot], { encoding: 'utf8', maxBuffer: 1024 * 1024 });
      if (run.status !== 0) throw new Error(run.stderr || run.stdout);
      const value = JSON.parse(run.stdout);
      expected ??= value.identity;
      assert.deepEqual(value.identity, expected, 'Benchmark variants must execute identical work');
      identities[kind] = expected;
      results.push({ kind, pair, variant, elapsedMs: value.elapsedMs, cpuMs: value.cpuMs });
      process.stderr.write(`${kind} ${pair + 1}/${pairs} ${variant}: ${value.elapsedMs.toFixed(1)} ms\n`);
    }
  }
  const median = values => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
  const summary = ['psg', 'machine'].map(kind => {
    const select = variant => results.filter(r => r.kind === kind && r.variant === variant).map(r => r.elapsedMs);
    const before = select('before'), after = select('after');
    return { kind, beforeMs: median(before), afterMs: median(after), reductionPercent: 100 * (1 - median(after) / median(before)) };
  });
  const report = { scope: 'Node/V8 host timing, not browser GPU or physical-machine qualification. PSG: 3M stereo frames after 100k warmup. Machine: cold real-ROM/TRD boot plus both 3.1s songs, AY and NullRenderer display events, 66.2 emulated seconds. Setup/parsing and post-run hashes excluded.',
    node: process.version, baselineAyumiSha256: sha(original), candidateAyumiSha256: sha(patchAyumi(original)),
    coreSha256: sha(fs.readFileSync(resolve(siteRoot, 'vendor/zx-dream.js'))),
    diskSha256: sha(fs.readFileSync(resolve(siteRoot, 'disks/ZX-Music-Menu.trd'))),
    alternatingFreshProcessPairs: pairs, allComparedOutputsExact: true, identities, results, summary };
  fs.writeFileSync(process.argv[5] || '.tmp/emulation-benchmark.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(summary, null, 2));
}
