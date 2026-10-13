/* Real register/wait command audition through vendored Ayumi, no source PCM. */
'use strict';
const fs=require('fs'), zlib=require('zlib'), api=require('./render_ym2149.js');
function render(data) {
  if(data.toString('ascii',0,4)!=='AYE1' || data.readUInt32LE(4)!==44100 || (data.length-16)%6) throw Error('invalid AYE1 stream');
  const samples=data.readUInt32LE(8), chip=api.createChip(1773450,44100,false), state=new Uint8Array(14);
  state[0]=state[2]=state[4]=1;state[7]=63;
  const out=new Float32Array(samples); let event=16, previous=-1, writes=0, sum=0, maximum=0;
  // Instantaneous DAC before/after a command at the SAME current gates and
  // envelope phase. No clock advance or ordinary square edge is counted.
  function dac() {
    let total=0;
    for(const ch of chip.channels) {
      const gate=(ch.tone|ch.tOff)&((chip.noise&1)|ch.nOff);
      total+=chip.dacTable[gate ? (ch.eOn ? chip.envelope : ch.volume*2+1) : 0];
    }
    return total/3;
  }
  function apply(reg,value) {
    state[reg]=value;
    if(reg<6) { const ch=reg>>1;chip.setTone(ch,state[2*ch]|state[2*ch+1]<<8); }
    else if(reg===6) chip.setNoise(value);
    else if(reg===7) for(let ch=0;ch<3;ch++) chip.setMixer(ch,(value>>ch)&1,(value>>(ch+3))&1,(state[8+ch]>>4)&1);
    else if(reg<11) {const ch=reg-8;chip.setVolume(ch,value&15);chip.setMixer(ch,(state[7]>>ch)&1,(state[7]>>(ch+3))&1,(value>>4)&1);}
    else if(reg<13) chip.setEnvelope(state[11]|state[12]<<8);
    else if(reg===13) chip.setEnvelopeShape(value);
    else throw Error('invalid register');
  }
  for(let i=0;i<samples;i++) {
    if(event<data.length && data.readUInt32LE(event)<i) throw Error('unsorted events');
    while(event<data.length && data.readUInt32LE(event)===i) {
      if(i<=previous) throw Error('zero bus spacing');
      const before=dac();apply(data[event+4],data[event+5]);const delta=dac()-before;
      sum+=delta*delta;maximum=Math.max(maximum,Math.abs(delta)); writes++;previous=i;event+=6;
    }
    chip.process();chip.removeDC();out[i]=(chip.left+chip.right)/3;
  }
  if(event!==data.length || !out.every(Number.isFinite)) throw Error('invalid end/output');
  return {out,diagnostic:{writes,instant_dac_step_squared_sum:sum,instant_dac_step_max:maximum,
    limitations:'Same-state DAC changes only; not future pitch transients or perceptual click audibility. One44.1-kHz-sample spacing approximates21.99us register writes at22.68us. Not Fuse or native Z80 qualification.'}};
}
module.exports={render};
if(require.main===module) {
  const [input,output,report]=process.argv.slice(2);const result=render(zlib.gunzipSync(fs.readFileSync(input)));
  fs.writeFileSync(output,Buffer.from(result.out.buffer));fs.writeFileSync(report,JSON.stringify(result.diagnostic,null,2)+'\n');
}
