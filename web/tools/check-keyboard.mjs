// Read actual Spectrum keyboard ports after browser-adapter input transitions.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
globalThis.window=new EventTarget();
globalThis.document=new EventTarget();document.hidden=false;
const {SpectrumPlayer}=await import('../emulator.js');
const c=vm.createContext({console});
vm.runInContext(fs.readFileSync('web/vendor/zx-dream.js','utf8'),c);
vm.runInContext(`
var bus=new ZX_Bus(),keyboard=new ZX_Keyboard();keyboard.connect(bus);
`,c);
const surface=new EventTarget();surface.focus=()=>{};
const player=new SpectrumPlayer(surface);player.hw={keyboard:vm.runInContext('keyboard',c)};
function key(code,pressed=true){
  const event=new Event(pressed?'keydown':'keyup',{cancelable:true});event.code=code;
  surface.dispatchEvent(event);return event.defaultPrevented;
}
const row=address=>vm.runInContext(`bus.io_read(${address})&31`,c);
const idle=()=>{for(let r=0;r<8;r++)assert.equal(row(((255^(1<<r))<<8)|254),31);};
idle();
for(const [arrow,address,mask] of [['ArrowLeft',0xf7fe,16],['ArrowDown',0xeffe,16],['ArrowUp',0xeffe,8],['ArrowRight',0xeffe,4]]){
  assert(key(arrow));assert.equal(row(0xfefe),30);assert.equal(row(address),31^mask);
  key(arrow,false);idle();
}
key('ArrowLeft');key('ArrowUp');key('ArrowLeft',false);
assert.equal(row(0xfefe),30);assert.equal(row(0xeffe),23);
key('ShiftLeft');key('ShiftRight');key('ArrowUp',false);key('ShiftLeft',false);
assert.equal(row(0xfefe),30);key('ShiftRight',false);idle();
key('Digit5');key('ArrowLeft');key('ArrowLeft',false);
assert.equal(row(0xf7fe),15);assert.equal(row(0xfefe),31);key('Digit5',false);idle();
key('ArrowDown');key('ArrowDown');key('ArrowDown',false);idle();
key('ArrowRight');surface.dispatchEvent(new Event('blur'));idle();
key('AltLeft');key('AltRight');key('AltLeft',false);assert.equal(row(0x7ffe),29);
window.dispatchEvent(new Event('blur'));idle();
assert.equal(key('Tab'),false);
await player.tap('ArrowUp');idle();
console.log('Keyboard ports pass: four cursor chords, shared holds, repeat, blur, aliases and touch release.');
