// Real display/clock code with a recording renderer and deterministic monitor.
// Native snapshots must follow ULA fields; browser vsync only presents them.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const source=fs.readFileSync('web/vendor/zx-dream.js','utf8');
function run(hz,cadence=[4],hidden=false,rebind=false){
  const context=vm.createContext({});vm.runInContext(source,context);
  Object.assign(context,{hz,cadence,hidden,rebind});
  return JSON.parse(JSON.stringify(vm.runInContext(`(function(){
    var now=0,hostTick,rafId=0,pending=new Map(),maxPending=0,frames=[],presented=[],irq=[],forced=0;
    var field=0,inField=false,force=false,rebound=false,staleIgnored=true,current=null,lastColor=[0,0,0,255];
    performance={now:()=>now};setInterval=fn=>{hostTick=fn;return 1;};clearInterval=()=>{};
    requestAnimationFrame=fn=>{pending.set(++rafId,fn);maxPending=Math.max(maxPending,pending.size);return rafId;};
    cancelAnimationFrame=id=>pending.delete(id);
    var bus=new ZX_Bus(),clock=new ZX_Clock(),cpuT=0;
    var cpu={get_tstates:()=>cpuT,set_tstates:t=>{cpuT=t;},process:()=>{
      cpuT+=4;
      // Writes after capture must never leak into that completed frame.
      if(field){bus.mem_write(field&1?0xc000:0x4000,238);bus.var_write('port_fe_value',(field+3)&7);}
    }};
    clock.connect(bus,cpu);bus.opt('TSTATES_PER_INTRQ',70908);bus.opt('INTRQ_PERIOD',20);
    bus.on_var_write((name,value)=>{if(!value)return;field++;inField=true;irq.push(clock.get_tstates());
      bus.var_write('port_7ffd_value',field&1?15:0);
      bus.mem_write(field&1?0xc000:0x4000,field&255);bus.var_write('port_fe_value',field&7);
    },'intrq');
    NullRenderer=function(){
      var banks=[];
      this.set_threading=()=>{};this.bind=()=>{};
      this.drawData=(layer,data,dirty)=>{
        var item={t:clock.get_tstates(),host:now,layer,value:data[0],field,force};
        banks[layer]=item;dirty.fill(0);
        if(inField)frames.push(item);else if(force)forced++;
      };
      this.displayLayer=layer=>{current={...banks[layer],presentHost:now,border:lastColor};presented.push(current);};
      this.copyLayerToScreen=this.displayLayer;
      this.drawBorder=color=>{lastColor=Array.from(color);if(current)current.border=lastColor;};
    };
    var display=new ZX_Display();display.connect(bus,clock);bus.opt('SEMICOLORS',true);
    bus.on_var_write((name,value)=>{if(value)inField=false;},'intrq');
    bus.opt('RENDERING_PARAMS',{scale:1,scaleType:1,rendererType:0,renderOnAnimationFrame:true});
    display.bind([]);clock.run();
    var tickIndex=0,nextTick=cadence[0],vsync=1,period=1000/hz;
    for(now=0;now<=1000;now+=.25){
      if(now>=nextTick){hostTick();nextTick+=cadence[++tickIndex%cadence.length];}
      if(rebind&&!rebound&&now>=550){
        rebound=true;var stale=[...pending.values()][0],before=presented.length;
        display.bind([]);force=true;display.force_redraw();force=false;
        if(presented.length!==before+1)throw Error('Forced redraw must present immediately');
        before=presented.length;if(stale)stale();staleIgnored=presented.length===before;
      }
      if(now>=vsync*period){
        vsync++;
        if(!hidden||now<300||now>=800){var tasks=[...pending.values()];pending.clear();tasks.forEach(fn=>fn(now));}
      }
    }
    now=1000;while(clock.get_tstates()<3545400)hostTick();
    var tasks=[...pending.values()];pending.clear();tasks.forEach(fn=>fn(now));clock.stop();
    return{hz,frames,presented,irq,maxPending,forced,staleIgnored};
  })()`,context,{timeout:10000})));
}
const cases=[];
for(const [hz,cadence,hidden,rebind]of [
  [50,[4],false,false],[60,[4],false,false],[75,[4],false,false],[120,[4],false,false],
  [40,[4],false,false],[60,[1,7,3,29,64,2,17],false,false],[60,[4],true,false],[60,[4],false,true]
]){
  const value=run(hz,cadence,hidden,rebind);
  assert.equal(value.frames.length,50,'Exactly fifty native captures per emulated second');
  assert.deepEqual(value.frames.map(frame=>frame.t),value.irq,'Capture on IRQ, without phase delay');
  assert(value.maxPending<=1,'Never accumulate animation callbacks');
  assert(value.staleIgnored,'Old renderer generation must not present');
  for(const frame of value.frames)assert.equal(frame.value,frame.field&255,'Native capture precedes later CPU writes');
  for(const frame of value.presented){
    if(frame.force)continue;
    assert.equal(frame.value,frame.field&255,'Present the completed native bank');
    const color=frame.field&7;
    assert.deepEqual(frame.border,[color&2?191:0,color&4?191:0,color&1?191:0,255],'Border belongs to the captured field');
  }
  if(!hidden&&!rebind&&cadence.length===1&&hz>=50)assert.equal(value.presented.length,50);
  cases.push({monitorHz:hz,cadence,hidden,rebind,nativeFrames:value.frames.length,
    presentations:value.presented.length,maxQueuedAnimationCallbacks:value.maxPending,
    forcedRedraws:value.forced,staleCallbackIgnored:value.staleIgnored,
    capturePhaseErrorTstates:0,maxPresentationDelayMs:Math.max(...value.presented.filter(f=>!f.force).map(f=>f.presentHost-f.host))});
}
const report={scope:'Actual shared clock and display with a four-T CPU and recording renderer; monitor/vsync simulation, not physical scanout or raster-level ULA qualification.',
  coreSha256:createHash('sha256').update(source).digest('hex'),cases,passed:true};
// Changing from a queued presentation to synchronous mode must retain the
// captured border even if the port has not been written again.
const switchContext=vm.createContext({});vm.runInContext(source,switchContext);
const switched=vm.runInContext(`(function(){var color=null;requestAnimationFrame=()=>1;cancelAnimationFrame=()=>{};
  NullRenderer=function(){this.bind=()=>{};this.set_threading=()=>{};this.drawData=()=>{};this.displayLayer=()=>{};this.drawBorder=v=>{color=Array.from(v);};};
  var b=new ZX_Bus(),d=new ZX_Display();d.connect(b,{setInterval:()=>{}});b.opt('SEMICOLORS',true);
  b.opt('RENDERING_PARAMS',{scale:1,scaleType:1,rendererType:0,renderOnAnimationFrame:true});d.bind([]);
  b.var_write('port_fe_value',1);b.var_write('intrq',1);
  b.opt('RENDERING_PARAMS',{scale:1,scaleType:1,rendererType:0,renderOnAnimationFrame:false});b.var_write('intrq',1);
  return color;})()`,switchContext);
assert.deepEqual(Array.from(switched),[0,0,191,255]);
report.pendingBorderSurvivesPresentationModeChange=true;
console.log(JSON.stringify(report,null,2));
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
