# Round 10: approximate eight-bit feedback, rejected

2026-10-04. On round 09, quantize the signed synthesis-feedback multiplier
down to a multiple of 256. Read only the two upper-nibble product tables.
Retain original output quantization, excitation, LPC and table preparation.
This is explicitly an approximate decoder, not a bit-exact Speex result.

Complete speech: **2201671482 T** versus 2510789186 (-309117704),
**11781.204 T/sample**, 1.1404x faster. Code 6572 (-52), state 1039,
table arena still 16384 bytes. First-frame instruction audit: 1596831 T
versus 1861567 (-264736), all instructions match Zilog timings. 960 random
filter samples and final states match an independent scalar approximation.
Full-stream guards pass; 150751 of 186880 PCM8 samples differ from exact.

Raw PCM8 SNR against exact decoding is 15.492 dB. Against original speech,
exact/approximate SNR is 6.500/6.096 dB. Both use the same 79-sample lag,
selected on the first 32000 source samples against exact decoding only.
The initial 40-sample alignment omitted encoder lookahead and was corrected;
do not compare that initial negative SNR with these aligned results. These
are waveform metrics, not a perceptual quality score. Approximation reaches
the PCM8 rails 14 times. Listening WAVs are reproducible under
`build/speex-port/pure-r10-approx/` (source, exact, approximate).

**Reject for selection:** speed still misses the nominal real-time budget
by 26.929x and introduces an additional error. Further precision reduction
alone cannot remove the excitation/LPC cost. Keep the candidate reproducible
as a failed experiment; retain round 09 as the exact implementation.
ULA/hardware and additional signal/capacity verification were not attempted
after this full-speech rejection.

Run `build.py --skip-host --variant pure-r10-approx` and `check_approx.py`.
See [report](report.json), [checks/quality](checks.json),
[independent model](../../check_approx.py), [transform](../../followup_opt.py).
