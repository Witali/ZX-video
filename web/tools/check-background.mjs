// Exercise the actual app's visibility transitions, independently of a tab UI.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const source = fs.readFileSync('web/app.js', 'utf8').replace(/^import .*;\r?\n/gm, '');
async function fixture(saved, blocked = false) {
  const fields = new Map();
  function element(id) {
    if (!fields.has(id)) fields.set(id, { value: ({renderer:'webgl',lowpass:'20000',scope:'root',category:'all'})[id] || '',
      checked: true, dataset:{}, classList:{toggle(){}}, handlers:{},
      addEventListener(name, fn) {this.handlers[name] = fn;}, setAttribute(){}, append(){}, replaceChildren(){} });
    return fields.get(id);
  }
  const writes = new Map();
  const document = {hidden:false, handlers:{}, getElementById:element, querySelectorAll:()=>[],
    createElement:()=>element(Symbol()), addEventListener(name,fn){this.handlers[name]=fn;}};
  class Player {
    calls=[]; running=false;
    setRenderer(){} setLowpassCutoff(){} setPlayInBackground(v){this.background=v;} async enableAudio(){} async initialize(){}
    mount(){this.running=true;} pause(value){this.calls.push(value);this.running=!value;}
  }
  const context = vm.createContext({document, SpectrumPlayer:Player, keepPhysicalPixelScale(){},
    LOWPASS_CUTOFFS:[5000,10000,15000,20000], URL, Uint8Array, console,
    location:{href:'http://localhost/'}, history:{replaceState(){}},
    localStorage:{getItem(key){if(blocked)throw Error('blocked');return key==='zx-video.play-in-background'?saved:null;},
      setItem(key,value){if(blocked)throw Error('blocked');writes.set(key,value);}},
    fetch:async()=>({ok:true,json:async()=>({images:[]})})});
  const app = await vm.runInContext(`(async()=>{${source}\nreturn {load, player, state:()=>({paused,visibilityPaused})};})()`, context);
  const disk={name:'test.trd',bytes:655360}; const bytes=new Uint8Array(655360);bytes[0x8e7]=0x10;
  return {app,fields,writes,document,load:()=>app.load(true,disk,bytes),
    hidden(value){document.hidden=value;document.handlers.visibilitychange();},
    setting(value){element('play-in-background').checked=value;element('play-in-background').handlers.change();},
    pause(){element('pause').handlers.click();}};
}
const enabled=await fixture(); assert(enabled.fields.get('play-in-background').checked);
await enabled.load(); enabled.hidden(true); enabled.hidden(false);
assert.equal(enabled.app.player.running,true);assert.deepEqual(enabled.app.player.calls,[]);
enabled.setting(false); enabled.hidden(true);assert.equal(enabled.app.player.running,false);
enabled.hidden(false);assert.equal(enabled.app.player.running,true);
enabled.pause();enabled.hidden(true);enabled.hidden(false);assert.equal(enabled.app.player.running,false,'Manual pause must survive tab switching');
enabled.pause();enabled.hidden(true);enabled.setting(true);assert.equal(enabled.app.player.running,true);
assert.equal(enabled.writes.get('zx-video.play-in-background'),'true');
const disabled=await fixture('false');assert.equal(disabled.fields.get('play-in-background').checked,false);
disabled.hidden(true);await disabled.load();assert.equal(disabled.app.player.running,false,'Hidden async boot must honor opt-out');
disabled.hidden(false);assert.equal(disabled.app.player.running,true);
const blocked=await fixture(null,true);await blocked.load();blocked.hidden(true);assert.equal(blocked.app.player.running,true);
blocked.setting(false);assert.equal(blocked.app.player.running,false,'In-memory preference works without storage');
const html=fs.readFileSync('web/index.html','utf8');assert.match(html,/id="play-in-background" type="checkbox" checked/);
let Processor;
const worklet=vm.createContext({sampleRate:44100,AudioWorkletProcessor:class{
  constructor(){this.port={onmessage:null,postMessage:data=>wakes.push(data)};}
},registerProcessor(name,klass){Processor=klass;}});
const wakes=[];
vm.runInContext(fs.readFileSync('web/audio-worklet.js','utf8'),worklet);
const processor=new Processor();
const quantum=()=>processor.process([],[[new Float32Array(128),new Float32Array(128)]]);
for(let i=0;i<40;i++)quantum();assert.equal(wakes.length,0);
processor.port.onmessage({data:{background:true}});
for(let i=0;i<40;i++)quantum();assert.equal(wakes.length,Math.floor(40*128/441));
processor.port.onmessage({data:{background:false}});const before=wakes.length;
for(let i=0;i<40;i++)quantum();assert.equal(wakes.length,before);
const report={cases:['default on','hidden and visible without audio restart','opt-out automatic pause/resume',
  'manual pause preserved','enable while hidden','saved opt-out','hidden async disk load','blocked storage default and toggle',
  'audio heartbeat only when enabled, including an empty audio queue'],
  passed:true,appSha256:crypto.createHash('sha256').update(fs.readFileSync('web/app.js')).digest('hex'),
  scope:'Actual application visibility policy with a player double; real clock cadence is checked separately.'};
console.log(JSON.stringify(report,null,2));if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
