# Locating the remaining reconstruction error

Measured 2026-10-03 using both complete saved Fuse timelines. These host
diagnostics preserve the original prepared 8-kHz reference, filter, phase
and gain. They do not execute a new disk or satisfy the 20-dB goal.

| Successive stage, compared with original uniform clock | Older full excerpt | Initial full prefix |
|---|---:|---:|
| Compensated PCM8 on actual sample boundaries | 25.25390 dB | 28.95125 dB |
| IMA PCM16 on those boundaries | 22.58842 dB | 25.07499 dB |
| Actual six-bit midpoint levels | 21.49069 dB | 20.58585 dB |
| Actual PDM port waveform | 18.99410 dB | 15.80350 dB |

Filtered source RMS is 0.19283 vs 0.09629: the initial prefix is much quieter
relative to its peak. Its PDM error relative to the six-bit levels scores
17.17643 dB, compared with 22.39884 dB for the older excerpt. Fitting an
output gain only raises the initial prefix's total to 15.86391 dB; gain
correction is not the missing four dB. That fitted score is diagnostic only.

## Rejected greedy pulse-area steering

The measured source packets have 96 distinct hold vectors. A host search
choosing any of 64 levels to minimize each packet's mean pulse-area error
scores 12.08682 dB on the initial prefix, worse than the current player.
Additional first-order error feedback with coefficients 0.5 and 1 gives
11.87138 and 10.67521 dB. The IMA restriction was deliberately absent, so
adding a codec cannot validate this failed method. This is a greedy search,
not an optimal bound on what another waveform-aware encoder can achieve.
Reject it: accurate packet means alone do not ensure low filtered error.

## Nonlinear amplitude maps

Keep 64 table rows but make levels denser near silence. All targets remain
integer multiples of 1/128, include exact zero audio, and retain wide peaks.
Three symmetric palettes use different central densities; a duplicated
zero row preserves the 64-row layout. The PCM-byte-to-row map is still a
single lookup and all output instruction paths would retain 423 native T
per ordinary sample. Tables remain host proposals until actual execution.

| Palette | Older full excerpt | Initial prefix | Required resident bytes |
|---|---:|---:|---:|
| Existing linear | 18.99410 dB | 15.80350 dB | 14336 |
| Weak companding | 19.36783 dB | 16.54155 dB | 14336 |
| Medium companding | 19.33124 dB | 16.56011 dB | 14080 |
| Strong companding | 19.23206 dB | 16.56071 dB | 14336 |

All palettes fit the counted code-pattern and reachable-state bounds. The
medium map leaves 256 extra resident bytes, but no variant reaches 20 dB
even on the old timeline. Changing the row map also changes which accesses
use contended memory, so these scores are not new disk measurements.

## Rejected robust-word cost

For the medium palette, enumerate 10320 words formed from its existing
120 first-half and 86 second-half patterns. Minimize forced error-history
energy plus a penalty for pulse-area variance under measured ULA hold
variation, retaining the existing 16 reachable feedback states. Covariance
weights 0/4/16/64 give 15.78310/15.82289/16.20488/16.35899 dB on the prefix.
All are worse than the medium palette's original 16.56011 dB. No extra
pattern, RAM or instruction cost was proposed; the cost function failed to
predict the desired waveform improvement. Do not sweep more weights here.

Decision: keep the existing delivered player. The next useful encoder
experiment must score the filtered waveform over time, rather than only
PCM16 error, a packet's mean area or an internal error-state norm. It can
still produce ordinary IMA bytes for the unchanged live decoder. A real
candidate must then be recalibrated and checked over both complete loops.

## Reproduction

```powershell
python audiobook-beeper/probe_reconstruction_error.py --input audiobook-beeper/experiments/ima-direct-locked --input audiobook-beeper/experiments/audio-converter --output build/reconstruction-error --ffmpeg <ffmpeg.exe>
python audiobook-beeper/probe_packet_area.py --input audiobook-beeper/experiments/audio-converter --output build/packet-area --ffmpeg <ffmpeg.exe>
python audiobook-beeper/probe_companded_packets.py --input audiobook-beeper/experiments/audio-converter --output build/companded-prefix --ffmpeg <ffmpeg.exe>
python audiobook-beeper/probe_companded_packets.py --input audiobook-beeper/experiments/ima-direct-locked --output build/companded-original --ffmpeg <ffmpeg.exe>
python audiobook-beeper/probe_robust_packets.py --input audiobook-beeper/experiments/audio-converter --output build/robust-packets --palette medium --ffmpeg <ffmpeg.exe>
```

[Saved reports and producer snapshots](experiments/reconstruction-error/manifest.json).
Both linear baselines reproduce the prior accepted first-loop scores exactly.
The old native player remains 423 T/sample; no physical hardware is measured.
