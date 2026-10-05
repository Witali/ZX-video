# Round 14: four-sample vectors fail the quality gate

2026-10-04. Conditional experiment from [NEXT_TARGET](../../NEXT_TARGET.md),
on the same complete 186880-sample, 8-kHz PCM8 control recording. Compare
PVQ4x1024 against the selected round13 PVQ3x1024, whose sound and stored
bytes equal round12. Exact Speex remains a separate format and implementation.

## Method and storage

Extend the assembly generator to four residuals per vector, preserving
the round13 removal of dead history writes and pointer increments. Four
10-bit indices occupy five bytes and now represent sixteen samples. Retrain
1024 four-byte vectors with the prior seeded teacher-forced K-means method
(seed 1977, 24 iterations), then encode with the actual reconstructed
half-predictor. Reject any candidate vector whose output would overflow PCM8.
Training clips 48 residual components; decoded output clips zero samples.
The cache validates source, settings, NumPy version and dictionary hash;
saved data can also be verified independently without retraining.
Fresh training and a cache reuse run produce identical stored-data and
PCM8 hashes; both archived timestamp streams pass an independent full
deadline check.

The first script launch failed before training because importing the old
codec research helper also imported unavailable OpenCV/PDM dependencies.
Copying its NumPy K-means helper into this focused script removed that
unrelated dependency; no decoder measurement came from the failed launch.

Stored payload 58400 + dictionary 4096 + header 32 = **62528 bytes**, or
**2.98874:1 versus PCM8**. This is 18446 fewer bytes than round13's 80974.
Input uses four banks (0,1,3,4), with twelve resident bank-padding bytes
not serialized. Table RAM remains 4614 bytes: the fourth residual occupies
the previously unused byte of each expanded dictionary row. State is one
byte and reserved stack 256; input storage is additional to the table budget.

## Timing and checks

Full unpaced execution costs **12953218 T / 69.3130 T per sample**, compared
with round13's 15651480 / 83.7515: **2698262 fewer T**. Steady sixteen-sample
work is `(355 + 3*142 + 8*26 + 4*30)/16 = 69.3125 T/sample`. Group start,
other vector starts, interior samples and vector ends retain round13's
355/142/26/30-T paths; longer vectors amortize index and bank handling.
These costs include parsing, OUT, bank checks and loop control, but no ULA.
Unpaced code is 299 bytes (round13: 360); paced code is 910 (935). Code-size
comparisons include this recording's different whole-group/tail shape.

All 186880 native PCM8 samples equal the independent scalar recurrence.
Every one of 186879 output intervals is exactly 437/438 T, including all
three bank switches. First/last OUT remain 499/81760061 T. Total paced CPU
is 81760098 T; the extra 36 T versus round13 occur after the last OUT as
the complete-group counter exits, not as an output deadline error.
Thirty-three short lengths (1..33) cover every tail position and group
transition. Input/code/table immutability and write guards pass. A separate
instruction audit covers startup and the first bank switch: 3023 executed
instructions / 27624 T match the instruction timing model. Index-half
operations count the four-T prefix and four-T base register instruction.

Rebuilding round13 after generalizing the generator preserves its stored
bytes, PCM8, timing, binary hashes and all 25 short-length checks; the
historical round12 option still reproduces its archived binary hash.

## Decision

Raw source SNR is **19.8552 dB**, down **3.6550 dB** from 23.5102. Speed and
storage targets pass, but the predeclared maximum one-dB loss fails.
**Reject this four-sample candidate and retain round13.** This waveform
metric is not a listening score; no subjective listening assessment is
claimed. The result does not rule out a better PC-side encoder or dictionary.

All timing is nominal 3.5-MHz CPU evidence. ULA contention, physical DAC,
disk delivery and hardware remain unverified; no release TRD is produced.

Reproduce with `pvq_four.py`; its complete checks write a listening preview
to `build/speex-port/pvq-r14/preview.wav`. The source PCM8 hash is checked
before training. [Report](report.json), [assembly](decoder.s),
[image](player.ihx), [timestamps](out-times.u64.gz),
[stored audio](audio.pvq.gz), [experiment script](../../pvq_four.py).
