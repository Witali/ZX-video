# Round 23: inline products and table reads through SP

2026-10-04. Continue from exact round22 on the unchanged 186880-sample
mode-3 speech. Compare two inline synthesis candidates, counting setup,
register preservation and complete port output. No pacing is introduced.

| Candidate | Complete speech T | T/sample | Delta versus round22 |
| --- | ---: | ---: | ---: |
| Round22 baseline | 1961694254 | 10497.080 | 0 |
| Register offsets, ordinary byte reads | 1885485770 | 10089.286 | -76208484 |
| Register offsets, initial table reads via POP | 1863554410 | 9971.931 | -98139844 |

Select **pure-r23-pop**, using **5.003% fewer T** than round22. The proposed
below-10000 intermediate milestone is met. Complete real-time decoding
remains unachieved: average cost is **22.793x** the 437.5-T/sample budget.
23.36 seconds of sound takes 532.444 nominal CPU seconds. ULA, disk and
physical hardware are not included.

## Register layout and arithmetic

After coefficient preparation, keep the excitation cursor in alternate HL.
Read the next word through it and transfer that word via the real stack.
Clip preserves this cursor. The four nibble offsets live in IXL/IXH/IYL/IYH;
each inline product reads an offset through A into ordinary L. DD/FD-prefixed
LD L,index-half would instead address an index half, so it is not used.
The target uses Z80 index-half operations; SDAS rejects their mnemonics,
so generated .db pairs retain explicit mnemonic/timing comments. Their
register-only timing is 4 T for the prefix plus 4 T for the LD operation;
the emulator and independent prefix timing calculation agree.

Products remain in BC:DE. Add each next history word through HL using
ADD HL,DE and ADC HL,BC, then store both words. This retains all 32-bit
wrap and carry semantics without moving the product's high word to HL.
The first partial product is four contiguous bytes. Temporarily set SP to
its address and use POP DE / POP BC. Other partials retain byte additions,
including the known-zero low bytes. Restore the saved real SP before
output or any subsequent CALL/PUSH/RET. IRQ stays disabled as before.
All caller IX/IY values are saved/restored around the complete filter call.

## Exact instruction accounting

The nonzero feedback block falls from **4136 to 3723 T** with ordinary reads,
or **3603 T** with POP. The zero path remains **847 T**. All totals include
the zero test and stop immediately before the shared output block.

- Splitting offsets: 176 -> 129 T, saving 47.
- Ten inline products: 292 -> 273 T each with ordinary reads, saving 190.
- Nine history additions: 110 -> 90 T; last store 36 -> 40 T, net saving 176.
- POP replaces each first-part read's 40 T with 26 T. Ten such savings minus
  the 20-T SP restore save another 120 T per nonzero sample.
- Cursor fetching saves 3 T on every sample. Whole-call overhead grows by
  33 T, or 53 T with the saved-SP store, once per 40 samples.

There are 183540 nonzero feedback samples, 3340 zero samples and 4672
filter calls. Complete savings exactly equal
`183540*413 + 186880*3 - 4672*33 = 76208484 T` and
`183540*533 + 186880*3 - 4672*53 = 98139844 T`.

## Verification and memory

Both candidates match the full speech, first-frame instruction audit,
**7719 arbitrary-history/product cases per variant**, and **128 complete
filter calls / 5120 extra samples per variant**. These independent integer
checks include signed16 coefficient extremes, arbitrary 32-bit history,
clipping, modulo32 carries and zero/nonzero feedback. The direct block
preserves the real SP and alternate cursor; full calls preserve SP/IX/IY.
Code and table write guards cover the borrowed-stack path.

Only selected pure-r23-pop is run through the complete fixture suite:
**1074400 exact PCM16/PCM8 samples**, including signals, six-bank capacity
and 512 random packets. Arithmetic, all table entries/products, cache
changes, invalid-input controls and cached-silence instruction audit pass.
The playback verifier now forbids every code write for these inline
variants; the retained standalone self-modifying helpers remain available
only to primitive checks. A fresh default build matches SHA-256
`1b6ca1a367f1cbf30888bd154a1d76ff7321ef76761a86a0cc10e5007746a727`.

Selected code is **7411 bytes** (+488), state **1041** (+2), stack reserve
256. Tables remain 16010 useful bytes inside the 16384-byte arena. Stored
speech remains 23360 bytes / 8:1 versus PCM8. Ordinary-read inline code is
7443 bytes with 1039 state bytes; keep it as a slower comparison, not default.

Next investigate the coefficient-table recurrence. Its repeated 32-bit
subtractions cost 42 T; adding a pre-negated step would cost 34 T, but the
negation/setup and signed upper-nibble transition must be included before
selecting it. This is not yet a measured optimization.

Reproduce both builds with `build.py --skip-host --variant pure-r23` and
`--variant pure-r23-pop`; retain round22 for comparison. Run
`check_inline_products.py`, `check_round.py --variant pure-r23-pop`, and
`check_unpaced.py --variant pure-r23-pop --previous pure-r22 --check-default`.
Archive with `report_round.py --variant pure-r23-pop --previous pure-r22 --round 23`.
[Measurements](report.json), [full checks](checks.json),
[inline/contract checks](inline-checks.json), [unpaced checks](unpaced-checks.json),
[ordinary-read candidate](../23-register/report.json),
[transform](../../followup_opt.py), [checker](../../check_inline_products.py).
