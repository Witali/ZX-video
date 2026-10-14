# Sea-foam main song through YM3812

Completed2026-10-14 in `.worktree/ym3812-sea-foam`, branch
`codex/ym3812-sea-foam`, from main `13819086`. The user requests a YM3812
track of the song from "In the Blue Sea, in the White Foam".

The user subsequently prefers the original audition and reports recurring
electronic "beep/blam" sounds. The [complete source/output audit and proposed
improvements](BEEP_ANALYSIS.md) identifies rapid peak switching and synthesized
lines on diffuse source regions. Use [the original version](evidence/ym3812-preview.wav)
as the next fitting baseline; the purity experiment below remains historical.

The earlier user request to reduce added high harmonics and use mainly
sines is complete. **[Latest pure-sine audition](overtones-evidence/ym3812-preview.wav)**
and **[before/after comparison, revised starts91 s](overtones-evidence/before-after.wav)**
retain the same90-second song and50-Hz targets. See [the measured changes,
all six trials and explicit selection limits](OVERTONES.md). The initial
version and its evidence remain below.

- **[Complete90-second YM3812 audition](evidence/ym3812-preview.wav)**
- **[Source0..90 s, silence90..91 s, YM381291..181 s](evidence/source-versus-ym3812.wav)**
- [VGM commands](evidence/ym3812.vgm), [compressed VGZ](evidence/ym3812.vgz)
- [Full spectrogram](evidence/spectrogram-full.png)
- [Worst-error detail35.44..38.44 s](evidence/spectrogram-detail.png)
- [Same-target abrupt control](evidence/abrupt.wav)
- [Measurements/provenance](evidence/report.json), [independent verification](evidence/verification.json)

## Source and synthesis

Reuse the archived main song [133.6,223.6) seconds of the authenticated
cartoon, without the later reprise. Original stereo44.1-kHz PCM16 SHA256:
`bf2218324c29575d3360d67d995012db43d27f5deb6aed9721aa9809d1c49190`.
[Original source/cut evidence](../../../audiobook-beeper/experiments/sea-foam-song/README.md).
Prepare mono by0.5L+0.5R and FFmpeg resampling to22050-Hz PCM16. Keep all
1,984,500 samples; do not reuse the limited8-kHz beeper preparation or add
normalization, compression or fades. The prepared reference is retained.

The existing spectral fitter analyzes all4500 fields continuously. Nine
sine-carrier voices use real FNUM/BLOCK, multipliers1/2, quantized0.75-dB TL
and key-on/off. Each voice has the same attenuated modulator as the earlier
experiment. These are nine moving partials, not nine fixed frequency bands.
Source PCM supplies targets only; the output comes entirely from YM3812
register/wait streams rendered by pinned ymfm-py0.2.0. There are no chunk
resets, PCM commands or source mixed into the chip output.

Reuse the previously selected eight-step raised-cosine, nominal2-ms TL
transitions and ordered split-frequency writes. Keep a same-target abrupt
export as the control. Actual serial slots are45.35 microseconds apart;
the smoothed burst completes in at most3.900227 ms. Every target is reached
before the next exact20-ms field boundary. Native rate3579545/72 Hz, fixed
20-Hz AC coupling and8-kHz129-tap fractional resampling are unchanged.

One fixed playback gain3.031479042166069 applies to both full outputs. It
is the lower of whole-song RMS matching and the common0.95 peak limit;
no per-frame gain adjustment is made. The smoothed saved WAV has3,969,000
mono44.1-kHz PCM16 samples, peak0.902472 and no clipping.

## Measured result and limits

| Measure | Abrupt control | Selected smooth preset |
| --- | ---: | ---: |
| Magnitude cosine512 |0.949826 |0.950017 |
| Magnitude cosine2048 |0.855534 |0.854519 |
| Magnitude cosine8192 |0.798895 |0.798115 |
|20-ms level MAE,dB |1.372615 |1.379574 |
| Combined log/level objective,dB |9.416898 |9.444631 |
| Immediate register-effect squared sum |66.074976 |12.499952 |
| Largest immediate effect |0.362005 |0.080579 |
| Register writes |116,526 |242,868 |
| VGM bytes |479,750 |992,252 |
| VGZ bytes |170,538 |369,327 |

The smooth preset reduces measured immediate write-effect energy81.0822%
and the largest effect77.7409%. This same-state counterfactual also includes
legitimate pitch/envelope changes; it does not establish inaudible clicks.
There is a small medium/long-spectrum and level tradeoff. This task reuses
the preset accepted for audition in the earlier experiment; no new search
or global spectral superiority is claimed.

Common-scale figures preserve much of the low-frequency partial structure.
Sparse voices lose diffuse and upper harmonic detail: output/source power
is0.635405 in2..4 kHz and0.197385 in4..8 kHz. Below50-Hz output power is
0.024779%. The result remains a listening trial, not a transparent music
encoding or physical-chip qualification. VGM players may apply different
output gain/filtering. Native Spectrum players and release disks are unchanged.

## Complete verification and reproduction

Eight existing independent chip/export tests pass. Both90-second streams
pass all4500 field endpoints, all nine channel states and real write spacing.
Each has4,474,431 native samples and3,969,000 output samples. A chip-state
counterfactual pass and a separate verifier replay every native/output sample;
saved PCM and re-exported commands match exactly, with zero native/output
clipping. The verifier recreates source preparation byte for byte, checks
all181 seconds of comparison segments, and authenticates all artifact and
producer hashes plus the pinned native core. No partial run is accepted.

The single bounded fit/build/measurement takes112.549 seconds on this host;
verification and unit-test time are separate. No real-time Z80, floppy or
physical-chip delivery has been measured for these commands. No player hot
path changes or instruction timing deltas apply.

On Windows with NumPy/Pillow and FFmpeg, from the worktree root:

```powershell
python -m pip install --no-deps --target .tmp/dependencies/ymfm ymfm-py==0.2.0
$env:PYTHONPATH=(Resolve-Path .tmp/dependencies/ymfm).Path
$env:OPENBLAS_NUM_THREADS='1'
python ay-converter/analysis/ym3812_sea_foam/run.py --song audiobook-beeper/experiments/sea-foam-song/evidence/original-song.wav --ffmpeg ffmpeg --output .tmp/new-ym3812-song
python -m unittest discover -s ay-converter -p test_experimental_ym3812.py -v 2> .tmp/song-tests.log
python ay-converter/analysis/ym3812_sea_foam/verify.py --evidence .tmp/new-ym3812-song --tests .tmp/song-tests.log --song audiobook-beeper/experiments/sea-foam-song/evidence/original-song.wav --ffmpeg ffmpeg
```

Use a fresh output directory and hydrate the original song through Git LFS.
FFmpeg version is recorded; another version can change reference resampling
bytes. The generic30-second historical CLI remains unchanged. This wrapper
uses its already duration-independent fitter/exporter for the full song.
