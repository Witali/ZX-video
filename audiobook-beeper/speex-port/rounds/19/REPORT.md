# Round 19: replace the signed24 seven-bit shift

2026-10-04. Same complete Speex mode-3 speech, starting from round18-signed.
The rounded excitation sum in L:D:E previously used seven SRA/RR/RR steps
followed by sign extension: 7*24+16 = **184 T**. Save its sign in A, shift
the three bytes left once, take the upper two bytes as DE and sign-extend
from A into HL. This takes **52 T**, saving exactly **132 T/sample**.
It discards the same seven low bits and keeps arithmetic floor semantics;
the preceding +64 rounding and the following symmetric clip stay unchanged.

Complete speech **2042203676 -> 2017535516 T**, delta **-24668160**, exactly
186880*132. Mean **10795.8878 T/sample**, still **24.6763x** the average
real-time budget. First-frame instruction audit **1631519 -> 1610399 T**,
delta -21120 = 160*132. No output pacing is introduced.

The isolated actual assembly block passes **396800 signed24 cases**, covering
all low words for six important high bytes and every high byte at rounding,
byte and word boundaries. All cost exactly 52 T; a ten-instruction audit
matches the timing table. The full **1074400 PCM16/PCM8 samples** remain
exact, including speech, signals, six-bank capacity and random packets.
Existing arithmetic, coefficient/innovation tables, caches, controls, memory
guards, stack checks and cached-silence instruction audit also pass.

Code **6914 bytes** (-33), state 1041, stack reserve 256. Tables remain
16010 useful bytes in their 16-KiB arena. Select as the next exact baseline;
ULA, disk and physical hardware remain unmeasured. The throughput goal is
still unmet. Next test register-held innovation-table state and a scaled
fraction whose carry represents the 12-bit remainder overflow.

Reproduce: `build.py --skip-host --variant pure-r19`, `check_exc_shift.py`,
`check_round.py --variant pure-r19`, and
`check_unpaced.py --variant pure-r19 --previous pure-r18-signed`.
[Report](report.json), [full checks](checks.json), [shift checks](shift-checks.json),
[unpaced checks](unpaced-checks.json), [transform](../../followup_opt.py).
