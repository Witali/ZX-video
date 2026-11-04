// Differential scheduling, bus and instruction-boundary tests. The reference
// disables only run_until, retaining the old clock's instruction-step path.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const source=fs.readFileSync('web/vendor/zx-dream.js','utf8');
const reference=process.argv[3]?fs.readFileSync(process.argv[3],'utf8'):source;
const digest=value=>createHash('sha256').update(value).digest('hex');
function run(sliced, cadence, frequency=false, debug=false) {
  const c=vm.createContext({});
  vm.runInContext(sliced?source:reference,c);
  c.cadence=cadence;c.frequency=frequency;c.debug=debug;c.sliced=sliced;
  return vm.runInContext(`(function(){
    var now=0,callback,trace=[],reads=0,writes=0,slices=0;
    performance={now:()=>now};setInterval=fn=>{callback=fn;return 1;};clearInterval=()=>{};
    var bus=new ZX_Bus(),cpu=new ZX_Z80(),clock=new ZX_Clock(),memory=new Uint8Array(65536);
    // OUT/IN, indexed loads/bit operations, self-contained LDIR and a jump.
    memory.set([0x31,0x00,0xff,0xfb,0x01,0xfe,0x00,0x3e,0x41,0xed,0x79,0xed,0x78,
      0xdd,0x21,0x00,0xa0,0xdd,0x77,0x03,0xdd,0xcb,0x03,0x06,
      0x21,0x00,0xa0,0x11,0x00,0xb0,0x01,0x10,0x00,0xed,0xb0,0xc3,0x04,0x80],0x8000);
    memory.set([0xfb,0xc9],0x38);memory.set([0xed,0x45],0x66);
    bus.on_instruction_read(a=>{trace.push(['M1',clock.get_tstates(),a]);return memory[a];});
    bus.on_mem_read(a=>memory[a]);bus.on_mem_write((a,v)=>memory[a]=v);
    bus.on_io_read(a=>{reads++;var t=clock.get_tstates();trace.push(['IN',t,a,clock.get_ms()]);return (a^t)&255;});
    bus.on_io_write((a,v)=>{
      writes++;trace.push(['OUT',clock.get_tstates(),a,v]);
      // A new I/O command may create a deadline BEFORE the existing slice end.
      if(writes<80){var n=writes;clock.setTimeout(()=>{trace.push(['IO-event',clock.get_tstates(),n]);memory[0xc000+n]=n;},[0,1,3,7,19][n%5]/3545.4);}
      if(frequency&&writes===5)bus.opt('TSTATES_PER_INTRQ',72000);
      if(frequency&&writes===30)bus.opt('TSTATES_PER_INTRQ',70908);
    });
    cpu.connect(bus);clock.connect(bus,cpu);bus.opt('TSTATES_PER_INTRQ',70908);bus.opt('INTRQ_PERIOD',20);
    if(!sliced)cpu.run_until=undefined;
    else {var advance=cpu.run_until;cpu.run_until=function(...args){slices++;advance(...args);};}
    bus.on_var_write((n,v)=>trace.push(['IRQ',clock.get_tstates(),v]),'intrq');
    var state=cpu.get_state();Object.assign(state,{pc:0x8000,sp:0xff00,imf:2,iff:0});cpu.set_state(state);
    var recurring,count=0;
    recurring=clock.setInterval(()=>{trace.push(['timer',clock.get_tstates(),++count]);if(count===3){recurring.cancelled=true;clock.setTimeout(()=>trace.push(['nested',clock.get_tstates()]),0);}},.013,0);
    var cancelled=clock.setTimeout(()=>{throw Error('Cancelled task ran');},.02);cancelled.cancelled=true;
    clock.setTimeout(()=>bus.var_write('nmirq',1),.117);
    // Regression: this floating timestamp is infinitesimally AFTER integer T.
    clock.setTimeout(()=>trace.push(['fraction',clock.get_tstates()]),129998.00000000001/3545.4);
    if(debug)clock.runDebug(()=>trace.length>1000,()=>trace.push(['break',clock.get_tstates()]));
    else clock.run();
    var index=0;
    while(now<120){now=Math.min(120,now+cadence[index++%cadence.length]);callback();}
    if(!debug){var before=clock.get_tstates();clock.stop();now+=2000;clock.run();if(clock.get_tstates()!==before)throw Error('Pause advanced CPU');now+=4;callback();}
    clock.stop();
    return {cpu:cpu.get_state(),t:clock.get_tstates(),memory:Array.from(memory),trace,reads,writes,slices};
  })()`,c,{timeout:10000});
}
const cases=[];
for(const [name,cadence,frequency,debug]of [
  ['regular',[4],false,false],['irregular',[1,7,3,29,4,2],false,false],
  ['catch-up',[4,4,90],false,false],['frequency change',[4],true,false],['debug step path',[4],false,true]
]){
  const a=JSON.parse(JSON.stringify(run(false,cadence,frequency,debug)));
  const b=JSON.parse(JSON.stringify(run(true,cadence,frequency,debug)));
  const slices=b.slices;delete a.slices;delete b.slices;
  assert.deepEqual(b,a,name);
  if(debug)assert.equal(slices,0);else assert(slices>0);
  cases.push({name,t:b.t,busFetches:b.trace.filter(e=>e[0]==='M1').length,ioReads:b.reads,ioWrites:b.writes,
    slices,traceSha256:digest(JSON.stringify(b.trace)),memorySha256:digest(Uint8Array.from(b.memory))});
}
const report={scope:'Real Z80 instructions, bus timestamps, dynamic I/O deadlines, IRQ/NMI, cancellation, frequency changes, pause, debug and fractional deadlines; differential against instruction-step scheduling.',
  coreSha256:digest(source),referenceSha256:digest(reference),cases,allExact:true};
console.log(JSON.stringify(report,null,2));
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
