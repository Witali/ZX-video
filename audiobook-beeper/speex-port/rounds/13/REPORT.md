# Round 13: meet the bit-identical <=84-T target

2026-10-04. Baseline round12, unchanged stored PVQ3x1024 data, dictionary
and 186880-sample waveform. Retain IXH history only after the third sample;
remove the final INC L because the next vector reloads its address.
Pacing is regenerated to preserve the output schedule exactly.

Complete unpaced CPU: **15651480 T**, down from 16897348 T by **1245868 T**;
**83.7515 T/sample**, meeting the <=84 target. Each full vector saves
two 8-T IXH writes plus one 4-T INC L: 20 T/3 samples. The recording contains
62293 complete vectors and a final sample: 62293*20+8 = 1245868 T.
Steady work is 83.75 T/sample; the startup/tail difference remains included
in the complete measurement. Average decoder time falls 7.373%.

Unpaced slot costs are 355 T at a new group (was 363), 142 at other new
vectors (150), 26 at the middle sample (34), and 30 at a vector end (34).
Tables remain 4614 bytes, state 1, stack reserve 256. Unpaced code 360 bytes
(was 387). The paced image and its size are recorded in report.json.
The historical generator option still rebuilds the round12 image identically.

All 186880 PCM8 bytes and every stored byte retain their round12 hashes.
All 186879 output intervals stay 437/438 T, including all bank transitions
and the four-sample tail. First/last OUT and total paced CPU time are also
unchanged. Twenty-five additional lengths (1..25) cover all short tail
shapes, whole groups and a partial third group. Memory guards pass; the
instruction audit includes startup and the first bank switch.

Select this exact waveform optimization. Storage remains 80974 bytes,
compression 2.3079:1 versus PCM8 and raw source SNR 23.510 dB. Less decoder
work means more available slot time; playback remains 8 kHz. ULA contention
and physical hardware remain unverified, as for the baseline.

Reproduce with `pvq_improve.py`. [Report](report.json), [assembly](decoder.s),
[image](player.ihx), [timestamps](out-times.u64.gz),
[generator/verifier](../../pvq_improve.py).
