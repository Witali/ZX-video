# Item 06: real-time decision and selected delivery

2026-10-04. All six authorized worklist items are complete. Select the exact
`pure-r4` assembly decoder and make it the default build/verification target.
A fresh offline build reproduces the verified image hash exactly. Earlier
variants and reports remain available; no approximate audio is substituted.

| Measure | Original assembly | Selected assembly |
| --- | ---: | ---: |
| Complete speech CPU T | 4536172045 | 2759257254 |
| Mean T/sample | 24273.181 | 14764.861 |
| CPU seconds for 23.36 s speech, at 3.5 MHz | 1296.049 | 788.359 |
| Code bytes | 10122 | 6152 |
| State bytes | 1885 | 1356 |
| Useful table bytes | 12658 | 16010 |
| Aligned table arena | 12800 | 16384 |

The reduction is **1776914791 T / 39.17%**, or **1.644x faster**. Samples are
bit-identical, so the compressed stream remains 23360 bytes and its 8:1 ratio
against PCM8 is unchanged. The 256-byte stack reserve and compressed input
are additional to the table/code/state figures.

**Real-time decision: FAIL.** The 8-kHz budget is 437.5 T/sample or 70000
T per 160-sample frame. The measured average is still **33.748x** that budget.
The synthesis phase including coefficient preparation alone costs 9231.900
T/sample; LPC costs 1700.391, and all remaining work 3832.571. Even eliminating
LPC and all remaining work would leave this synthesis implementation far
outside the budget. This is evidence about these implementations, not a
proof that every conceivable Speex decoder is impossible on a Z80.

Actual OUT intervals are 5473..889303 T. All 186879 outputs following the first
miss deadlines anchored at that first output; maximum accumulated lateness
is 2676721156.5 T. A one-frame or two-frame buffer cannot resolve the sustained
deficit. Uniform 8-kHz scheduling is consequently not added or claimed.
ULA contention, ROM/disk delays and physical hardware are excluded. Since
nominal CPU time already fails, extra contention cannot produce a pass.

The next useful experiment would change synthesis and must report audio
quality separately: a few table-driven oscillators plus noise, or a short
periodic waveform with controlled updates. The previously estimated
four-oscillator kernel costs 388 T/sample before noise, parameter extraction,
table updates and pacing; it leaves too little margin to claim a decoder.
A three-oscillator kernel leaves more room, but intelligibility and timbre
must be tested on the same speech. Deriving its parameters directly from
Speex remains work; preparing them offline would change the stored format
and require a new compression-ratio measurement. Neither alternative was
implemented as part of this exact-decoder worklist.

Deliver [current assembly/image/map](../04/), the
[full verification](../05/REPORT.md), [machine-readable decision](report.json)
and the completed [TODO](../../TODO.md). Keep separate focused commits for
each item. No playback release or TRD is produced.
