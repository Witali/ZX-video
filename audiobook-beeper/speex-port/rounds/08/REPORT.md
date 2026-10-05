# Round 08: unroll table construction and retain unchanged pages

2026-10-04. Same complete speech and fixed-point reference as round 07.
Unroll each 16-entry construction loop, preserving signed top-nibble wrap.
Compare/cache coefficients individually; rebuild only changed pages. Initial
construction is forced even when a coefficient is zero. Retain the cheap
whole-set comparison for unchanged subframes.

Full speech: **2527353474 T**, delta **-157151780 T**; **13523.938 T/sample**,
1.06218x faster than round 07. Code 6657 bytes (+513), state 1359 (+3).
Tables remain 16010 useful bytes / 16384 reserved. Select the change.

All speech, signal/capacity PCM16/PCM8, 12800 products, 40960 entries and
excitation primitives pass. Ten single-coefficient update checks verify
other pages remain byte-identical; unchanged preparation costs 976 T,
single-page changes 14799..15627 T including return. The first complete
frame instruction audit is 1882463 T versus 1952616 T (-70153 T), every
instruction matching the independent timing table. Changing only symbol
visibility to expose the cache check leaves the image hash unchanged.

Neither nominal real time nor ULA/hardware playback is claimed.
Reproduce with `build.py --skip-host --variant pure-r8` and
`check_round.py --variant pure-r8`. See [report](report.json),
[checks](checks.json), [assembly](decoder.s), and [transform](../../followup_opt.py).
