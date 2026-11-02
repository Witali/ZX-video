// Compare/re-render the authenticated native AY transaction trace using the
// website's pinned Ayumi engine, ABC panning, DC removal and 20 kHz RC filter.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';
import {rcCoefficients} from '../../web/audio-filter.js';
const trace=JSON.parse(fs.readFileSync(process.argv[2]));
const capture=JSON.parse(fs.readFileSync(process.argv[3]));
const output=process.argv[4];fs.mkdirSync(output,{recursive:true});
const rate=44100,cpuHz=3546900,field=70908;
const source=fs.readFileSync(new URL('../../web/vendor/ayumi.js',import.meta.url),'utf8');
const c=vm.createContext({});vm.runInContext(source,c);
const chip=vm.runInContext('new Ayumi()',c);chip.configure(false,1773400,rate);
for(const [channel,pan] of [[0,.1],[1,.5],[2,.9]])chip.setPan(channel,pan,false);
const regs=new Uint8Array(14);
function write(reg,value){
 regs[reg]=value;
 if(reg<=5){let ch=reg>>1;chip.setTone(ch,regs[ch*2]|regs[ch*2+1]<<8);}
 else if(reg===6)chip.setNoise(value);
 else if(reg===7)for(let ch=0;ch<3;ch++){chip.channels[ch].tOff=(value>>ch)&1;chip.channels[ch].nOff=(value>>(ch+3))&1;}
 else if(reg<=10){let ch=reg-8;chip.setVolume(ch,value&15);chip.channels[ch].eOn=!!(value&16);}
 else if(reg<=12)chip.setEnvelope(regs[11]|regs[12]<<8);
 else chip.setEnvelopeShape(value);
}
const mute=[[8,0],[9,0],[10,0],[13,0],[7,63],[6,31],[11,255],[12,255],
 [0,0],[1,0],[2,0],[3,0],[4,0],[5,0]];
for(const [reg,value] of mute)write(reg,value);
const prefix=capture.track_starts[0][0]*field;
const events=trace.writes.filter(r=>r[0]<trace.end_tstates).map(([t,r,v])=>[t+prefix,r,v]);
for(const start of trace.starts.slice(0,2))for(const [r,v] of mute)events.push([prefix+start,r,v,-1]);
events.sort((a,b)=>a[0]-b[0]||(a[3]||0)-(b[3]||0));
const completeFields=capture.track_starts[2][0];
const count=Math.floor(completeFields*field/cpuHz*rate);
const pcm=Buffer.alloc(count*4),alpha=rcCoefficients(20000,rate).feedforward[0];
let event=0,left=0,right=0,peak=0,clipped=0;
for(let sample=0;sample<count;sample++){
 const t=sample*cpuHz/rate;
 while(event<events.length&&events[event][0]<=t){write(events[event][1],events[event][2]);event++;}
 chip.process();chip.removeDC();
 left=alpha*chip.left*.7+(1-alpha)*left;right=alpha*chip.right*.7+(1-alpha)*right;
 peak=Math.max(peak,Math.abs(left),Math.abs(right));if(Math.abs(left)>=1||Math.abs(right)>=1)clipped++;
 pcm.writeInt16LE(Math.max(-32768,Math.min(32767,Math.round(left*32767))),sample*4);
 pcm.writeInt16LE(Math.max(-32768,Math.min(32767,Math.round(right*32767))),sample*4+2);
 if(sample%(rate*30)===0)console.log(`Ayumi ${sample/rate}s`);
}
if(clipped)throw Error('Unexpected clipping');
const header=Buffer.alloc(44);header.write('RIFF');header.writeUInt32LE(36+pcm.length,4);header.write('WAVEfmt ',8);
header.writeUInt32LE(16,16);header.writeUInt16LE(1,20);header.writeUInt16LE(2,22);header.writeUInt32LE(rate,24);
header.writeUInt32LE(rate*4,28);header.writeUInt16LE(4,32);header.writeUInt16LE(16,34);header.write('data',36);header.writeUInt32LE(pcm.length,40);
fs.writeFileSync(path.join(output,'ayumi.wav'),Buffer.concat([header,pcm]));
const chunks=Array.from({length:completeFields},(_,f)=>{let offset=Math.floor(f*field/cpuHz*rate);return[f,offset,Math.floor((f+1)*field/cpuHz*rate)-offset];});
const metadata={sample_rate:rate,channels:2,audio_samples:count,chunks,source:'Pinned website Ayumi + ABC panning + DC removal + 20 kHz RC; native Fuse AY transactions unchanged.',
 source_trace_sha256:trace.trace_sha256,ayumi_sha256:crypto.createHash('sha256').update(source).digest('hex'),
 peak,clipped_samples:clipped,register_writes:events.length,wav_sha256:crypto.createHash('sha256').update(header).update(pcm).digest('hex')};
fs.writeFileSync(path.join(output,'decoded.json'),JSON.stringify(metadata)+'\n');
console.log(JSON.stringify({...metadata,chunks:undefined},null,2));
