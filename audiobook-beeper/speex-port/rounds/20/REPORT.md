# Round 20: register-held innovation table construction

2026-10-04. Continue from exact round19 on the unchanged 186880-sample
Speex mode-3 speech. Rebuild the same two cached 132-entry signed24 tables
when frame gain changes. The initial -65 entry and energy arithmetic stay
unchanged; optimize only the recurrence and stores.

Ordinary HL/C hold the low word/high byte of the current value, DE the
integer step and B the counter. Alternate HL/DE hold remainder/fraction
scaled by sixteen, with alternate BC as the output cursor. Their 16-bit
addition's carry is precisely the old overflow of the 12-bit remainder.
EXX preserves this carry for ADC HL,DE; its carry then increments C. The
remaining low four bits stay zero. Three stores transfer L/H/C through A
to alternate (BC), preserving the same little-endian signed24 layout.

## Exact timing

The old loop costs **352 T/entry**, including counter and JP. The new loop
costs **137 T**, except **132 T** on its final DJNZ. Stores consume 75 T,
fraction/value update 49 T, DJNZ 13/8 T. Thus loop cost is 46464 -> 18079 T.
Register setup grows from 20 to 216 T: net saving **28189 T per table**.

All 64 energy settings show that identical saving, including setup. The
independently audited last-energy builder call costs **48218 -> 20029 T**,
4967 -> 3268 instructions. Actual loop boundaries confirm 131*137+132 T.
Every one of **8448 table entries per variant** matches signed floor
`(shape*energy)//4096`; exact state/table/stack write guards and preserved
SP/IX/IY pass. Both ordinary and alternate general register sets are clobbered,
as documented in the generated assembly; existing callers allow this.

Complete speech **2017535516 -> 1973053274 T**, delta **-44482242**,
equal to 1578 table builds * 28189 T. The count agrees with the prior complete
profile; gain selection and cache logic are unchanged. Mean **10557.8621
T/sample**. First-frame audit: 1610399 -> **1554021 T**, delta -56378,
exactly two builds. All **1074400 PCM16/PCM8 samples** remain exact across
speech, signals, complete six-bank capacity and 512 random packets. Existing
arithmetic, tables/products, cache changes, controls, write guards, stack
and cached-silence audits pass. A fresh default build matches.

## Decision

Select **pure-r20** as the exact default. Code **6899 bytes** (-15), state
1041, stack reserve 256. Table payload remains 16010 useful bytes in its
16384-byte arena; stream storage remains 23360 bytes / 8:1 versus PCM8.
Rounds19/20 save 69150402 T together, with no waveform or format change.
Samples are emitted consecutively without added pacing. Average CPU still
exceeds the real-time budget **24.1323x**; the active goal is unmet.
ULA, disk and physical hardware remain outside these CPU measurements.

Reproduce: `build.py --skip-host`, `check_round.py --variant pure-r20`,
`check_innovation_registers.py`, and
`check_unpaced.py --variant pure-r20 --previous pure-r19 --check-default`.
Archive with `report_round.py --variant pure-r20 --previous pure-r19 --round 20`.
[Report](report.json), [full checks](checks.json),
[innovation checks](innovation-checks.json), [unpaced checks](unpaced-checks.json),
[transform](../../followup_opt.py), [builder checker](../../check_innovation_registers.py).
