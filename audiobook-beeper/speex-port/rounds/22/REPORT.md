# Round 22: exact zero-feedback state copy

2026-10-04. Continue from round20 on the unchanged 186880-sample mode-3
speech. Round21 observed 3340 zero feedback samples and selected this
shortcut; the rejected pitch/history guards are not introduced.

For y=0, every coefficient product is zero, so the next filter state is
exactly the following nine old 32-bit words followed by a zero word. Copy
36 bytes forward with LDIR; source is four bytes ahead of destination,
making the overlap safe. This identity also holds for arbitrary nonzero
old history. The next nonzero feedback refreshes all four cached product
offsets. Reuse A=H after negation for the zero test and remove the unread
asm_n store and its two-byte allocation. Generated assembly documents the
register contract, overlapping copy and untouched cached offsets.

## Instruction timing and full result

The previous feedback block costs 4138 T: dead store 16, split CALL/body
176, ten product loads/CALLs/bodies 2920, and memory updates 1026. Its
products and additions are constant-time. The new nonzero path replaces
the store with OR L (4) and JP Z (10): **4136 T**, delta **-2 T**.

The zero handler costs 833 T: three register loads 30, LDIR 751
(35*21+16), zero word load 10, two word stores 32, and return jump 10.
With the 14-T test it costs **847 T**, delta **-3291 T**. Every instruction
matches the independent timing table on both paths and both variants.
4650 arbitrary-history/coefficient cases per variant pass an independent
signed-product/modulo32 model, including 1548 zero cases. Write guards
and SP/IX/IY preservation pass.

Full speech **1973053274 -> 1961694254 T**, delta **-11359020 T**, exactly
`3340*3291 + (186880-3340)*2` saved. Mean **10497.0797 T/sample**; the
intermediate below-10500 target is achieved. All **1074400 PCM16/PCM8
samples** remain exact across speech, signals, six-bank capacity and 512
random packets. Arithmetic, tables/cache, controls, memory guards, full
first-frame and cached-silence instruction audits pass. A fresh default
build matches SHA-256
`437162b560c4e8ce8794325000d075e08b5ce9a4703640d17e49beca59fde549`.

## Decision and next scope

Select **pure-r22**. Code 6923 bytes (+24), state 1039 (-2), stack reserve
256. Tables remain 16010 useful bytes in a 16384-byte arena. Stored speech
remains 23360 bytes, 8:1 versus PCM8. Output is consecutive with no pacing.
23.36 seconds of sound costs 560.484 nominal CPU seconds, still **23.9933x**
the 437.5-T/sample real-time budget. The broader throughput goal is unmet;
ULA, disk and physical hardware remain unverified.

Next proposed milestone: below 10000 T/sample on this same complete input,
with exact output and unchanged table budget. First count an inline
coefficient-product loop using register-held nibble offsets, including
register saves and setup. Only implement it if the complete cost is lower.
This is a prospective target, not an achieved measurement or a guarantee
that exact Speex can reach real time on a 3.5-MHz Z80.

Reproduce: `build.py --skip-host --variant pure-r22`,
`check_zero_feedback.py --variant pure-r22 --previous pure-r20`,
`check_round.py --variant pure-r22`, and
`check_unpaced.py --variant pure-r22 --previous pure-r20 --check-default`.
Archive with `report_round.py --variant pure-r22 --previous pure-r20 --round 22`.
[Measurements](report.json), [full checks](checks.json),
[feedback checks](zero-feedback-checks.json), [unpaced checks](unpaced-checks.json),
[transform](../../followup_opt.py), [checker](../../check_zero_feedback.py).
