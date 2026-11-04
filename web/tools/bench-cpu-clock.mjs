import fs from 'node:fs';
import vm from 'node:vm';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {performance} from 'node:perf_hooks';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const sha=data=>createHash('sha256').update(data).digest('hex');
if(process.argv[2]==='--worker'){
  const core=fs.readFileSync(process.argv[3],'utf8');
  const work=fs.readFileSync(new URL('./cpu-clock-workload.js',import.meta.url),'utf8');
  const output={};
  for(const kind of ['alu','copy','indexed','flow']){
    let now=0,callback;
    const context=vm.createContext({performance:{now:()=>now},setInterval:fn=>{callback=fn;return 1;},clearInterval:()=>{}});
    vm.runInContext(core+'\n'+work,context);context.kind=kind;
    vm.runInContext('var h=cpuClockWorkload(kind);h.clock.run();',context);
    const advance=ms=>{const end=now+ms;while(now<end){now+=4;callback();}};
    advance(1000);const start=performance.now();advance(20000);const ms=performance.now()-start;
    const memory=vm.runInContext('var b=h.bus;Uint8Array.from({length:65536},(_,a)=>b.mem_read(a))',context);
    output[kind]={ms,state:vm.runInContext('h.cpu.get_state()',context),t:context.h.clock.get_tstates(),
      ram:sha(memory),interrupts:JSON.parse(JSON.stringify(context.h.interrupts))};
  }
  console.log(JSON.stringify(output));
}else{
  const before=process.argv[2]||'.tmp/baseline-zx-dream.js',after=process.argv[3]||'web/vendor/zx-dream.js';
  const rows=[],identities={};
  for(let pair=0;pair<5;pair++)for(const name of pair&1?['after','before']:['before','after']){
    const run=spawnSync(process.execPath,[fileURLToPath(import.meta.url),'--worker',name==='before'?before:after],{encoding:'utf8'});
    assert.equal(run.status,0,run.stderr);
    for(const[kind,{ms,...identity}]of Object.entries(JSON.parse(run.stdout))){
      identities[kind]??=identity;assert.deepEqual(identity,identities[kind]);rows.push({pair,name,kind,ms});
    }
    process.stderr.write(`CPU clock ${pair+1}/5 ${name} complete\n`);
  }
  const median=v=>v.sort((a,b)=>a-b)[Math.floor(v.length/2)];
  const summary=Object.keys(identities).map(kind=>{
    const times=name=>rows.filter(r=>r.kind===kind&&r.name===name).map(r=>r.ms);
    const beforeMs=median(times('before')),afterMs=median(times('after'));
    return{kind,beforeMs,afterMs,reductionPercent:100*(1-afterMs/beforeMs)};
  });
  const compact=Object.fromEntries(Object.entries(identities).map(([kind,value])=>[kind,{...value,
    interrupts:{count:value.interrupts.length,sha256:sha(JSON.stringify(value.interrupts))}}]));
  const report={scope:'Actual Z80, banked RAM, bus and 50-Hz clock; 1s warmup and 20s timed machine time per kernel. No audio/video or physical-machine claim.',node:process.version,
    baselineSha256:sha(fs.readFileSync(before)),candidateSha256:sha(fs.readFileSync(after)),identities:compact,rows,summary,allExact:true};
  fs.writeFileSync(process.argv[4]||'.tmp/cpu-clock-benchmark.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(summary,null,2));
}
