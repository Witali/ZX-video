// Fuse instruction vectors plus modern interrupted-repeat flag rules.
import fs from 'node:fs';import vm from 'node:vm';import crypto from 'node:crypto';import {join} from 'node:path';
const fixtures=process.argv[2]||'.tmp/fuse-test-source/z80/tests';
const expectedHashes={'tests.in':'9f36e866f22e72ff1f8bf2100bf70ffbf58edd97b453500aab60acf1f403ebbb','tests.expected':'15a6946f4addcf97e137b5bdd1d5fdb08124ff91f1b169f36a8bf4afe4bab6e4'};
for(const [name,hash]of Object.entries(expectedHashes))if(crypto.createHash('sha256').update(fs.readFileSync(join(fixtures,name),'utf8').replace(/\r/g,'')).digest('hex')!==hash)throw new Error('Unrecognized Fuse vectors');
const c=vm.createContext({console});vm.runInContext(fs.readFileSync('web/vendor/zx-dream.js','utf8'),c);
function parse(file,expected){
 const lines=fs.readFileSync(file,'utf8').replace(/\r/g,'').split('\n');const cases=[];let i=0;
 while(i<lines.length){while(!lines[i]?.trim()&&i<lines.length)i++;if(i===lines.length)break;
 const name=lines[i++].trim();const events=[];if(expected)while(/^\s+\d+\s+(MR|MW|MC|PR|PW|PC)\b/.test(lines[i]))events.push(lines[i++].trim().split(/\s+/));
 const regs=lines[i++].trim().split(/\s+/).map(n=>parseInt(n,16));const misc=lines[i++].trim().split(/\s+/);const mem=[];
 while(i<lines.length&&lines[i].trim()&&lines[i].trim()!=='-1'){mem.push(lines[i++].trim().split(/\s+/).map(n=>parseInt(n,16)));}if(lines[i]?.trim()==='-1')i++;
 cases.push({name,regs,misc,mem,events});}return cases;
}
const adjusted=[];
function modernRepeat(t,e){
 if(!['edb2_1','edb3_1','edb9_2','edbb_1'].includes(t.name))return;
 const old=e.regs[0],pc=e.regs[11],b=e.regs[1]>>>8;let f=(old&255&~0x28)|((pc>>>8)&0x28);
 // Banks' hardware-observed flags during the extra five repeat T-states.
 // https://github.com/hoglet67/Z80Decoder/wiki/Undocumented-Flags
 if(t.name!=='edb9_2'){
  const parity=v=>{let n=0;for(let i=0;i<8;i++)n^=(v>>>i)&1;return n^1;};
  const carry=f&1,negative=f&2;
  const v=carry?(b+(negative?-1:1))&255:b;
  f^=(parity(v&7)^1)<<2;
  if(carry)f=(f&~16)|(((b&15)===(negative?0:15))?16:0);
 }
 e.regs[0]=(old&0xff00)|f;adjusted.push({name:t.name,legacyAF:old,hardwareAF:e.regs[0]});
}
const input=parse(join(fixtures,'tests.in'),false),expected=parse(join(fixtures,'tests.expected'),true);const exp=new Map(expected.map(t=>[t.name,t]));
const names=['af','bc','de','hl','af_','bc_','de_','hl_','ix','iy','sp','pc','memptr'];const failures=[];let checked=0;
for(const t of input){const e=exp.get(t.name);modernRepeat(t,e);const memory=new Uint8Array(65536);for(const row of t.mem){let a=row[0];for(const v of row.slice(1,-1))memory[a++&65535]=v;}
 c.memory=memory;c.io=[];c.portReads=e.events.filter(x=>x[1]==='PR').map(x=>({a:parseInt(x[2],16),v:parseInt(x[3],16)}));
 vm.runInContext(`var bus=new ZX_Bus(),cpu=new ZX_Z80();bus.on_instruction_read(a=>memory[a]);bus.on_mem_read(a=>memory[a]);bus.on_mem_write((a,v)=>memory[a]=v);bus.on_io_read(a=>{var v=portReads.length?portReads.shift().v:255;io.push({type:"PR",address:a,value:v});return v;});bus.on_io_write((a,v)=>io.push({type:"PW",address:a,value:v}));cpu.connect(bus);`,c);
 const initial=Object.fromEntries(names.map((n,i)=>[n,t.regs[i]]));Object.assign(initial,{i:parseInt(t.misc[0],16),r:parseInt(t.misc[1],16),iff:(+t.misc[2]<<1)|+t.misc[3],imf:[0,2,3][+t.misc[4]],memptr:t.regs[12],prefix_dd:false,prefix_fd:false,prefix_ed:false,prefix_cb:false});c.initial=initial;c.limit=+t.misc[6];vm.runInContext('cpu.set_state(initial);cpu.set_tstates(0);do{cpu.process();var s=cpu.get_state();}while(cpu.get_tstates()<limit||s.prefix_dd||s.prefix_fd||s.prefix_ed||s.prefix_cb);',c);
 const got=vm.runInContext('cpu.get_state()',c),diff=[];for(const [i,n]of names.entries())if(got[n]!==e.regs[i])diff.push({field:n,got:got[n],expected:e.regs[i]});
 for(const row of e.mem){let a=row[0];for(const v of row.slice(1,-1)){if(memory[a&65535]!==v)diff.push({field:'memory',address:a,got:memory[a&65535],expected:v});a++;}}
 const expectedIo=e.events.filter(x=>x[1]==="PR"||x[1]==="PW").map(x=>({type:x[1],address:parseInt(x[2],16),value:parseInt(x[3],16)}));if(JSON.stringify(c.io)!==JSON.stringify(expectedIo))diff.push({field:"ports",got:c.io,expected:expectedIo});got.imf=got.imf<2?0:got.imf;for(const [field,value]of Object.entries({i:parseInt(e.misc[0],16),r:parseInt(e.misc[1],16),iff:(+e.misc[2]<<1)|+e.misc[3],imf:[0,2,3][+e.misc[4]]}))if(got[field]!==value)diff.push({field,got:got[field],expected:value});const cycles=vm.runInContext('cpu.get_tstates()',c);if(cycles!==+e.misc[6])diff.push({field:'tstates',got:cycles,expected:+e.misc[6]});
 if(diff.length)failures.push({name:t.name,diff});checked++;
}
const report={scope:'1356 Fuse vectors: registers, MEMPTR, R/I/IFF/IM, changed RAM, port addresses/data and instruction T-states. Four legacy repeat-flag expectations updated from independent hardware rules. Not exhaustive hardware or mid-cycle contention proof.',fixtureRevision:'67d72235610a9821c780499a0c10d89512656127',checked,passed:checked-failures.length,modernRepeatExpectations:adjusted,failures};fs.writeFileSync(process.argv[3]||'.tmp/fuse-opcodes.json',JSON.stringify(report,null,2));console.log(JSON.stringify({checked,passed:report.passed,failed:failures.length,first:failures.slice(0,20)},null,2));


if(failures.length)process.exitCode=1;
