# Chip-model noise colour fitting at 50 Hz

Completed 2026-10-04, baseline `4ab6d7f`. The user requested an accurate online
description/simulation and an implemented fit of noise frequency colour to
The Entertainer. The current optional `--profile music` now searches the
actual Ayumi output. All sound states remain **20 ms**, with persistent tone
channels and the same detected noise events/routes. Default `legacy` stays
byte-identical; `--profile music --noise-fit heuristic` retains tracked50.

## Listen and inspect

- [Independently bootable listening disk](../../../ZX-music-Entertainer-AY-noise-colour-test.trd)
- [Normal Fuse recording, two complete repeats](evidence/release/fuse-preview.wav)
- [Original / previous tracked AY / fitted AY comparison](evidence/comparison/comparison-original-old-new.wav)
- [Complete spectrogram](evidence/comparison/spectrogram-full.png),
  [busy phrase](evidence/comparison/spectrogram-12-16s.png),
  [noise spectrum and periods](evidence/comparison/noise-colour.png)
- [Every fitted noise state](evidence/release/noise-fit.json.gz),
  [channel/state audit](evidence/comparison/noise-audit.json),
  [complete execution proof](evidence/release/verification.json)

The comparison WAV's three sections start at 0, 32.12 and 64.24 seconds.
The unchanged source is the public-domain keyboard performance by IE; see
[provenance](../../../audiobook-beeper/experiments/ima-3bit-entertainer/source.json).
Requested 31.128 s retains 1556 complete states /31.12 s. Source SHA-256 is
`08dc5241de419edf9693ad20797389cb735d9b6fc06bfb6936568bb707f13077`.

## Documented digital model

The [General Instrument register description](https://cpctech.cpcwiki.de/docs/ay38912/psgspec.htm)
describes the five-bit noise divider, mixer gates and shared channel volumes.
[MAME's implementation](https://github.com/mamedev/mame/blob/master/src/devices/sound/ay8910.h)
records a hardware-verified 17-bit shift register, bit-0 XOR bit-3 feedback
into bit 16, with bit 0 as output. Its nonzero sequence repeats after 131071
steps. For the fitted periods N=1..31, its step rate is chip_clock/(16*N).
At 1773450 Hz that spans about 110841..3576 steps/s. It changes noise colour,
not the pitch of a sinusoidal oscillator; there is no arbitrary EQ curve.

[Ayumi](https://github.com/true-grue/ayumi) provides a precise digital chip
simulation. Its [C source](https://github.com/true-grue/ayumi/blob/master/ayumi.c)
implements the shift register, tone counters, Boolean mixer, measured DAC
tables and resampling. The local unmodified JS port remains pinned to
`alexanderk23/ayumi-js` commit `3a1fb9120cc2c5ef8f538af59b46701e4c2305bb`.
It mixes `(tone OR tone_disabled) AND (noise OR noise_disabled)` before the
channel DAC. Thus occupied-channel noise depends on the note, and changing
its volume also changes that tone. A sinc-only noise envelope misses this.

These are primary digital-model sources, accessed 2026-10-04. Board loading,
analogue filters and AY/YM DAC differences prevent a universal exact analogue
prediction. The selected renderer is YM2149; Fuse supplies a separate check
of the actual player output. No physical hardware measurement is claimed.
We only search N=1..31. In the file, N=0 denotes a disabled noise event; initial
and inter-event LFSR phase is not assumed identical across emulators/hardware.

## Implemented bounded search

`noise_colour.py` refines the already tracked register stream after excerpt
clipping. `render_noise_candidates.js` renders all 31 periods with three
shared-volume choices: unchanged, minus one, minus two steps. This bounded
attenuation limits damage to the carrier's tone while correcting excessive
estimated noise. No candidate mutes the carrier. All other registers remain
the input stream's values. This is a 93-candidate search, not an exhaustive
search over arbitrary arrangements or independent tone/noise amplitudes.

Every candidate simulates the entire sequence with continuous phase/counters,
actual tone/noise gates, YM DAC and filters. **Render at 44100 Hz**: Ayumi's
interpolator requires sample_rate > chip_clock/64. A new wrapper guard rejects
unsupported rates. A zero-phase 127-tap Hann/sinc filter, cutoff 10584 Hz,
then downsamples both baseline and candidates identically to 22050 Hz.

The fit uses 512/2048/8192-sample Hann windows, 20-ms hops and 50..8000-Hz
bins. A narrow approximately 50-Hz power average reduces sensitivity to
individual random peaks; it is not a broad musical-band pooling. One global
source/model RMS gain is fixed from the previous stream. Equal weights on
the three log-magnitude errors use a common source-relative -60-dB floor.
A dynamic program penalizes R6 jumps by .15 dB per octave and shared-volume
jumps by .15 dB per register step, restarting at each gap in detected noise.
It does not change the 20-ms output grid or move attacks.

Choosing between continuous candidate streams changes the final LFSR history.
Therefore the chosen complete stream is rendered again, then run in Fuse;
candidate cost alone is never accepted as quality proof. The independent
comparisons below use **unpooled** STFT bins, one global RMS normalization,
no local gain, no pitch fitting and no dynamic time warp.

For this excerpt, R6 changes on 301 of 415 noisy states. Shared volume drops
two steps on 411 states and one on four. All 289 component lifetimes, tone
periods, mixer bits, base tone volumes, noise presence/routes and volumes of
the other two channels remain exact. The 1141 states without noise retain
every register byte. Noise still occupies 398 tone+noise states and 17
noise-only states. No active tone is disabled or moved.

## Measured benefit and limits

[Four valid full-length host ablations](evidence/host/results.json) isolate
the contributions. These use identical source/register inputs and actual
44100-Hz chip rendering; the independent evaluator downsamples with FFmpeg.

| Host variant | Log-magnitude MAE, 512 | 2048 | 8192 |
| --- | ---: | ---: | ---: |
| Previous tracked50 | 10.88844 | 9.78226 | 7.91031 |
| Fitted level only, old R6 | 10.57118 | 9.15174 | 7.28674 |
| Fitted R6 only, old level | 10.90216 | 9.81086 | 7.95262 |
| **Joint fit** | **10.56307** | **9.15825** | **7.27228** |

Most benefit comes from the shared-level correction. Period fitting adds a
small improvement at short/long windows relative to level-only, with a
.00652-dB medium-window regression. Changing only R6 worsens log error.
Do not attribute the whole gain to noise colour or claim a universal better
timbre. The joint version has slightly higher magnitude cosine than level-only
at all three scales. Select it as a modest measured joint improvement that
implements the requested chip-aware colour search.

The actual cold Fuse comparison uses the preceding tracked50 disk, not the
older original legacy disk. A fixed known clock mapping, 50*70908/3546900,
applies to both recordings; the normal WAV retains physical timing. Complete
raw-time scores are also saved in [the comparison](evidence/comparison/fuse-spectrogram.json).

| Window | First-loop log MAE, old -> new | First-loop magnitude cosine, old -> new |
| --- | ---: | ---: |
| 512 | 9.77503 -> 9.56216 | .82651 -> .82813 |
| 2048 | 9.45849 -> 9.06411 | .81248 -> .81512 |
| 8192 | 8.12608 -> 7.65117 | .80224 -> .80732 |

Second-loop log errors likewise improve: 9.64893/9.46516/8.11674 ->
9.42575/9.08434/7.65949. Cosine and spectral convergence improve at every
scale in both loops; raw-time comparisons agree. On the same 415 noisy
states, first-loop errors fall 10.03907/9.78933/8.71878 ->
8.98038/8.62440/7.89888, roughly **9–12%**. These are errors in the entire
mixed signal during detected-noise states, not an isolated true-noise stem.

Fine onset F1 is mixed: .64662 -> .67742 in loop one, .63396 -> .62857 in loop
two. Semitone-pooled cosine falls slightly in both loops, and second-loop
loudness correlation falls .97242 -> .97101. No musical or listening acceptance
is inferred. Visual inspection of complete/busy-phrase spectrograms and the
noise-floor plot shows less excess broadband energy, with remaining missing
polyphony and spectral valleys that one noise divider cannot reproduce.

## Verification and history

All **19 tests pass**. New checks cover the full 131071-state noise cycle,
65536 one bits, all 31 clock divisors, all 16 Boolean mixer truth cases,
invalid-rate rejection, anti-alias suppression without timing shift, channel
invariants, no-noise bypass and temporal smoothing. A synthetic period-23 /
volume-11 reference with an unseen LFSR phase recovers median period 23 /
volume 11. This tests a digital-model fixture, not source separation.

The entire disk cold-boots through two Fuse loops: **34232 exact register
writes /3112 fields**, zero missing or duplicate fields, 67 startup reads,
no runtime disk reads, loading-message display/hiding verified. Startup is
10.677687 s; normal recording 62.226236 s. Player bytes are identical to the
previous disk: **974 ->974 T ordinary work, delta 0 T**, unchanged special
paths 992/1091/1079 T, and 17116 resident bytes. Deterministic instruction
counts exclude ULA, HALT/IRQ, ROM and disk latency; Fuse checks real writes.

The complete default CLI still reproduces the original TRD, AY9/register
streams and original/model WAVs byte for byte. All 177 retained previous
image hashes are unchanged. Final disk SHA-256:
`a7d36854c41ca7f408619ffb32f6218aeb28324c397cdf30ff131e4d6f6a8691`.
See [the completion audit](evidence/completion.json).

Early drafts used an invalid 22050-Hz Ayumi configuration and an aliased RMS
calibration. They are explicitly rejected, including apparently passing
tests whose reference also used that bad rate. Their sources, measurements,
failed checks and execution summaries remain in
[discarded evidence](evidence/discarded/README.md). Only the valid-rate final
release and the four controls above support this milestone's quality claims.

## Reproduce

Use the standalone dependencies, FFmpeg, Node.js and Fuse; Matplotlib is
needed only for figures. Set `OPENBLAS_NUM_THREADS=1`.

```powershell
python -m unittest discover -s ay-converter -p "test_*.py" -v
python ay-converter/convert_audio.py audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --output build/noise-release --duration 31.128 --title "THE ENTERTAINER" --profile music --ffmpeg FFMPEG --node NODE --fuse FUSE
python ay-converter/analysis/noise_colour/compare_host.py --input audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --baseline ay-converter/analysis/tracked50/evidence/release --candidate build/noise-release --output build/noise-host --ffmpeg FFMPEG --node NODE
python ay-converter/analysis/music50/compare_fuse.py --input audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --baseline ay-converter/analysis/tracked50/evidence/release --candidate build/noise-release --output build/noise-figures --ffmpeg FFMPEG
python ay-converter/analysis/noise_colour/inspect_noise.py --input audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --baseline ay-converter/analysis/tracked50/evidence/release --candidate build/noise-release --output build/noise-figures --ffmpeg FFMPEG
```
