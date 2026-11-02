// Verify shared-device time independently of host callback cadence and wall-clock edits.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';

const source = fs.readFileSync('web/vendor/zx-dream.js', 'utf8');
function run(cadence, jumpWallClock = false, pause = false) {
  let hostMs = 0, wallMs = 0, callback;
  const context = vm.createContext({ console, performance: { now: () => hostMs },
    Date: class extends Date { static now() { return wallMs; } },
    setInterval: fn => { callback = fn; return 1; }, clearInterval: () => {} });
  vm.runInContext(source, context);
  vm.runInContext(`
    var bus=new ZX_Bus(),clock=new ZX_Clock(),cpuT=0;
    // Four-T NOP bus isolates scheduling from instruction correctness.
    var cpu={get_tstates:()=>cpuT,set_tstates:t=>{cpuT=t;},process:()=>{cpuT+=4;}};
    clock.connect(bus,cpu);bus.opt('TSTATES_PER_INTRQ',70908);bus.opt('INTRQ_PERIOD',20);
    var events=[],counts={ula:0,disk:0,audio:0};
    function record(device){counts[device]++;events.push([device,clock.get_tstates()]);}
    bus.on_var_write((name,value)=>{if(value)record('ula');},'intrq');
    clock.setInterval(()=>record('disk'),200/6250,0); // 300 rpm, MFM byte cadence.
    clock.setInterval(()=>record('audio'),1000/44100,0);
    clock.run();
  `, context);
  const total = 1000, hz = 3545400;
  let step = 0, pausedAt = 0;
  while (hostMs - pausedAt < total) {
    hostMs = Math.min(total + pausedAt, hostMs + cadence[step++ % cadence.length]);
    wallMs = jumpWallClock ? (step & 1 ? 3600000 : -7200000) : hostMs;
    callback();
    if (pause && !pausedAt && hostMs >= 400) {
      vm.runInContext('clock.stop()', context);
      const before = vm.runInContext('clock.get_tstates()', context);
      hostMs += 2000; wallMs += 2000; pausedAt = 2000;
      assert.equal(vm.runInContext('clock.get_tstates()', context), before);
      vm.runInContext('clock.run()', context);
    }
  }
  // Drain bounded catch-up slices without advancing real time.
  let callbacks = 0;
  while (vm.runInContext('clock.get_tstates()', context) < hz && callbacks++ < 100) callback();
  const result = vm.runInContext('({t:clock.get_tstates(),counts,events})', context);
  assert.equal(result.t, hz, 'One second of active host time must run one machine second');
  assert(callbacks < 100, 'Catch-up debt must remain drainable');
  return JSON.parse(JSON.stringify(result));
}
const baseline = run([4]);
const cases = [
  ['irregular callbacks', run([1, 7, 3, 29, 64, 2, 17])],
  ['long host stall', run([4, 4, 4, 700])],
  ['wall-clock jumps', run([4], true)],
  ['pause and resume', run([4], false, true)],
];
for (const [name, result] of cases) assert.deepEqual(result, baseline, name);
const report = { scope: 'Shared clock scheduling with a four-T NOP CPU; not full-machine timing qualification',
  cases: ['regular callbacks', ...cases.map(([name]) => name)],
  machineTstates: baseline.t, events: baseline.counts,
  identicalDeviceEventTimelines: true,
  coreSha256: crypto.createHash('sha256').update(source).digest('hex') };
console.log(JSON.stringify(report, null, 2));
if (process.argv[2]) fs.writeFileSync(process.argv[2], JSON.stringify(report, null, 2) + '\n');
