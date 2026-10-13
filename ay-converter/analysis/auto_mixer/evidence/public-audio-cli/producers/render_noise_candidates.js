/* Continuous Ayumi renders used to measure the colour of each R6 choice.
 * The tones, mixer routing and shared volumes are exactly the input stream.
 * No phase/counter reset occurs at a frame boundary or noise-event boundary.
 */
'use strict';
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const {render} = require('./render_ym2149');

function candidates(input, output, sampleRate=44100, delta=0) {
  if (![-2,-1,0].includes(delta)) throw new Error('Invalid volume delta');
  const registers = zlib.gunzipSync(fs.readFileSync(input));
  if (!registers.length || registers.length%11) throw new Error('Invalid registers');
  for (let period=1; period<=31; period++) {
    const candidate = Buffer.from(registers);
    for (let tick=0; tick<candidate.length/11; tick++) {
      if (candidate[tick*11+6]) {
        candidate[tick*11+6] = period;
        for (let channel=0; channel<3; channel++) {
          if (!(candidate[tick*11+7] & (1 << (channel+3)))) {
            candidate[tick*11+8+channel] = Math.max(1,candidate[tick*11+8+channel]+delta);
          }
        }
      }
    }
    const samples = render(candidate, 50, {sampleRate});
    fs.writeFileSync(path.join(output, `noise-${period}.f32`), Buffer.from(samples.buffer));
  }
}
module.exports = {candidates};
if (require.main === module) {
  const [input, output, delta='0'] = process.argv.slice(2);
  if (!output) throw new Error('Usage: node render_noise_candidates.js registers.gz output-directory');
  if (delta === 'baseline') {
    const samples = render(zlib.gunzipSync(fs.readFileSync(input)),50);
    fs.writeFileSync(path.join(output,'baseline.f32'),Buffer.from(samples.buffer));
  } else {
    candidates(input, output, 44100, Number(delta));
  }
}
