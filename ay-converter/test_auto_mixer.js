/* Independent tone -> mixed -> noise fixture with an unseen LFSR phase. */
'use strict';
const fs = require('fs');
const {createChip,setRegisters} = require('./render_ym2149');
const chip = createChip();
chip.noise = 0x15abc;
const audio = new Float32Array(120*882);
for (let tick=0; tick<120; tick++) {
  const mixer = tick<40 ? 0x38 : tick<80 ? 0x30 : 0x31;
  setRegisters(chip,Uint8Array.from([251,0,0,2,0,3,19,mixer,11,0,0]));
  for (let i=tick*882; i<(tick+1)*882; i++) {
    chip.process(); chip.removeDC(); audio[i]=(chip.left+chip.right)/3;
  }
}
fs.writeFileSync(process.argv[2],Buffer.from(audio.buffer));
