// Reuse the existing real-ROM/TRD/AY workload, changing only the CPU/clock core.
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const before=process.argv[2]||'.tmp/baseline-zx-dream.js';
const after=process.argv[3]||'web/vendor/zx-dream.js';
const site=process.argv[4]||'.tmp/web-site';
const mode=process.argv[6]||'machine';
assert(['machine','movie'].includes(mode));
const worker=fileURLToPath(new URL('./bench-emulation.mjs',import.meta.url));
const ayumi=fileURLToPath(new URL('../vendor/ayumi.js',import.meta.url));
const rows=[];let identity;
for(let pair=0;pair<5;pair++)for(const name of pair&1?['after','before']:['before','after']){
  const run=spawnSync(process.execPath,[worker,'--worker',mode,ayumi,site,name==='before'?before:after],{encoding:'utf8',maxBuffer:2*1024*1024});
  assert.equal(run.status,0,run.stderr);const value=JSON.parse(run.stdout);
  identity??=value.identity;assert.deepEqual(value.identity,identity);
  rows.push({pair,name,elapsedMs:value.elapsedMs,cpuMs:value.cpuMs});
  process.stderr.write(`Machine ${pair+1}/5 ${name}: ${value.elapsedMs.toFixed(1)} ms\n`);
}
const median=v=>v.sort((a,b)=>a-b)[Math.floor(v.length/2)];
const beforeMs=median(rows.filter(r=>r.name==='before').map(r=>r.elapsedMs));
const afterMs=median(rows.filter(r=>r.name==='after').map(r=>r.elapsedMs));
const sha=path=>createHash('sha256').update(fs.readFileSync(path)).digest('hex');
const report={scope:`${mode==='movie'?'60-second cold video-disk':'66.2-second cold music'} real-ROM/TRD/CPU/AY workload with NullRenderer; setup/parsing and final PCM/RAM hashes excluded. No GPU or physical-machine claim.`,
  mode,emulatedSeconds:mode==='movie'?60:66.2,node:process.version,baselineSha256:sha(before),candidateSha256:sha(after),identity,rows,
  summary:{beforeMs,afterMs,reductionPercent:100*(1-afterMs/beforeMs)},allExact:true};
fs.writeFileSync(process.argv[5]||'.tmp/cpu-machine-benchmark.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report.summary,null,2));
