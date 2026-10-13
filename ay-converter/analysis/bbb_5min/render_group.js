/* Task-local scheduling of independent complete candidate renders.
 * Each period starts the same canonical chip model and renders the entire
 * stream. Parallel execution does not reset phase within a candidate. */
'use strict';
const fs = require('fs'), path = require('path'), zlib = require('zlib');
const [core, kind, firstText, lastText, ...args] = process.argv.slice(2);
const {render} = require(path.join(core, 'render_ym2149.js'));
const {candidate} = require(path.join(core, 'render_mixer_candidates.js'));
const first = Number(firstText), last = Number(lastText);
if (!(first >= 1 && last <= 31 && first <= last)) throw new Error('Invalid range');
let seed, tones, route, output, mode, delta;
if (kind === 'noise') {
  const [input, directory, deltaText] = args;
  seed = zlib.gunzipSync(fs.readFileSync(input));
  output = directory; delta = Number(deltaText);
  if (![-2,-1,0].includes(delta)) throw new Error('Invalid noise delta');
} else if (kind === 'mixer') {
  const [input, toneFile, routeFile, directory, modeText, deltaText] = args;
  seed = zlib.gunzipSync(fs.readFileSync(input));
  tones = zlib.gunzipSync(fs.readFileSync(toneFile));
  route = JSON.parse(fs.readFileSync(routeFile));
  output = directory; mode = modeText; delta = Number(deltaText);
} else throw new Error('Invalid kind');
for (let period = first; period <= last; period++) {
  let registers;
  if (kind === 'mixer') registers = candidate(seed, tones, route, mode, period, delta);
  else {
    registers = Buffer.from(seed);
    for (let tick=0; tick<registers.length/11; tick++) {
      const o=tick*11;
      if (!registers[o+6]) continue;
      registers[o+6]=period;
      for (let c=0; c<3; c++)
        if (!(registers[o+7] & (1 << (c+3))))
          registers[o+8+c]=Math.max(1, registers[o+8+c]+delta);
    }
  }
  const audio=render(registers,50);
  fs.writeFileSync(path.join(output,`${kind === 'noise' ? 'noise' : 'candidate'}-${period}.f32`),Buffer.from(audio.buffer));
}
