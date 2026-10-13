/* Continuous chip candidates for one shared noise carrier per 20-ms state.
 * Routing comes from the persistent tracker; the search changes its mode,
 * R6 and shared volume. Other channels keep their tonal parameters. */
'use strict';
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const {render} = require('./render_ym2149');

function candidate(seed, tones, route, mode, period, delta) {
  if (!['noise','mixed'].includes(mode) || period<1 || period>31) throw new Error('Invalid candidate');
  const result = Buffer.from(tones);
  for (let t=0; t<route.carriers.length; t++) {
    if (!route.eligible[t]) continue;
    const c = route.carriers[t], offset = t*11;
    result[offset+6] = period;
    result[offset+7] &= ~(1 << (c+3));
    if (mode==='noise') result[offset+7] |= 1 << c;
    result[offset+8+c] = Math.min(15,Math.max(1,route.levels[t]+delta));
  }
  return result;
}
module.exports = {candidate};
if (require.main===module) {
  const [seedFile,toneFile,routeFile,output,mode,deltaText] = process.argv.slice(2);
  const seed = zlib.gunzipSync(fs.readFileSync(seedFile));
  const tones = zlib.gunzipSync(fs.readFileSync(toneFile));
  const route = JSON.parse(fs.readFileSync(routeFile));
  if (seed.length!==tones.length || seed.length!==route.carriers.length*11) throw new Error('State length mismatch');
  for (let period=1; period<=31; period++) {
    const registers = candidate(seed,tones,route,mode,period,Number(deltaText));
    const audio = render(registers,50);
    fs.writeFileSync(path.join(output,`candidate-${period}.f32`),Buffer.from(audio.buffer));
  }
}
