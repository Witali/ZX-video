# Round 32: shared coefficient magnitude in exact Q14 products

2026-10-04. Continue from round31 on the unchanged complete mode-3 speech.
The two signed16 products inside MULT16_32_Q14 normalize the same coefficient
independently. Prepare its unsigned magnitude once and use the existing
byte/word partial-product method through a new unsigned entry. Restore the
coefficient sign after combining the high and fractional products. The
public signed multiplier and its standalone contract remain unchanged.

## Exact arithmetic and register contract

Input is signed16 a in HL and a pointer to signed32 b in DE. Return signed32
HL:DE. Preserve IX/IY, all alternate registers and the caller's SP; clobber
ordinary AF/BC/DE/HL and the declared scratch. The path remains nonreentrant.
Reuse the unused s8_sign byte for the coefficient sign: the current signed8
implementation keeps its sign in C. A generator assertion checks that the
slot has no other references. No additional state or tables are allocated.

Retain the upstream expression, including its intentional high truncation:

```text
hi = int16(b >> 14)
lo = b & 16383
result = a*hi + floor(a*lo / 16384)
```

Let c=abs(a), P=c*lo and H=c*hi. For nonnegative a, return
H+floor(P/16384). For negative a, return -H-ceil(P/16384).
Before discarding the low 14 product bits, distinguish a zero remainder
from a nonzero remainder. Separate tails compute ordinary negation or
-sum-1 with an initial borrow. This also handles zero, -32768, signed32
extrema and high-part wrap at bits 29/30/31 exactly. P is below 2^29;
its shifted value is nonnegative and fits signed16, allowing zero extension.

## Instruction accounting

Reuse round31's independently audited U8 cost. For unsigned U(x,y), including
RET: zero x costs 50 T, otherwise zero y costs 60 T. Nonzero inputs use
35 T entry, 20/34/35 T dispatch (first byte / swapped second byte / two words),
then 46 T plus the nonzero U8 product for the byte path, or 114 T plus the
low general and high nonzero U8 products for the word path, and 10 T RET.
The underlying U8 code is unchanged from its exhaustive round31 domain test.

Old Q14 costs 491 T plus signed M(hi,a)+M(lo,a). New Q14 costs
U(abs(hi),c)+U(lo,c) plus the following complete wrapper costs, including
CALLs, sign normalization, argument copy/extraction, scratch, combination
and final return:

| Coefficient | High part | Wrapper, exact fraction | Wrapper, nonzero remainder |
| --- | --- | ---: | ---: |
| Nonnegative | Nonnegative | 572 T | 572 T |
| Nonnegative | Negative | 685 T | 685 T |
| Negative | Nonnegative | 683 T | 680 T |
| Negative | Negative | 796 T | 793 T |

Observe all 93440 Q14 calls, 84220 unique pairs. Both binaries receive the
same inputs; reconstruct all 186880 signed operands from the archived
round31 trace exactly. Execute every unique Q14 pair in isolation on both
binaries. Weighted instruction formulas equal the profiled function totals;
their difference equals the entire playback saving. The baseline profiled
run also preserves every saved OUT timestamp.

| Measurement | Round31 | Selected round32 |
| --- | ---: | ---: |
| Q14 T | 172467335 | 167108120 |
| Complete speech T | 1635360657 | 1630001442 |
| T/sample | 8750.8597 | 8722.1824 |
| First complete frame T | 1094940 | 1090996 |
| Code bytes | 8859 | 9038 |

Select the measured **5359215 T / 0.3277%** complete saving. This is an
average improvement: **40193 individual speech calls regress**. In the
isolated domain, savings range from -194 to +143 T. In particular, the
negative-coefficient/negative-high path first negates H and later negates
the combined result. The report does not claim universal per-call speedup.
Every complete checked fixture is nevertheless faster, including silence
(-92400 T), six-bank capacity (-22707300 T), random packets (-2354241 T)
and all-pitch input (-589143 T). No other candidate was implemented or
reverted in this round.

## Verification and memory

- 1343488 exact Q14 cases: every signed16 coefficient against 12 signed32
  boundaries; every 14-bit fraction against 32 coefficient/high pairs;
  32768 random signed32 cases. Check full signed32 result and exact cost.
- 1179648 unsigned16 products: every word in both orders against nine
  zero/byte/word/extreme fixed values. Check all 32 result bits and cost.
- Independently step 374 Q14 boundary pairs per binary: 54005 baseline and
  53937 selected instructions, each matching the Z80 timing table.
- Guard input, code and all memory writes. New Q14 can write only ten
  scratch bytes, its existing sign byte and the reserved stack. Check
  IX/IY, alternate AF/BC/DE/HL and SP after every isolated execution.
- Standard 1074400 plus all-pitch 20480 **complete PCM16/PCM8 samples**
  pass, for **1094880 exact samples**. Generic primitives, control paths,
  coefficient/table caches, full-frame and cached-silence instruction
  audits and fresh default image identity also pass.

Code is 9038 bytes at 8000..A34D, +179 bytes. State stays 1041 bytes at
B000..B410; reserved stack is BF00..BFFF. Tables remain 16010 useful bytes
within a 16384-byte arena (12658 static and 3352 useful dynamic bytes).
Code/state/input are additional RAM. Payload remains 23360 bytes, 8:1
against mono 8-kHz PCM8. Playback code is immutable. Selected binary SHA-256:
`19582a1aff55a679abe762f4485a6a1d24f4791cdd572043222dd397b0579415`.

23.36 seconds of audio needs 465.715 nominal CPU seconds, still **19.9364x**
the 437.5-T/sample average real-time budget. Output is deliberately unpaced.
ULA contention, disk and physical hardware are outside this measurement.
The average real-time goal remains active and unmet.

## Next measurable target

Adopt **below 8500 T/sample** on the same complete 186880-sample speech as
the next intermediate target, retaining exact PCM16/PCM8 and the table
budget. It needs more than 41521442 T additional saving (about 2.55%);
this is a target, not a measured or guaranteed result. Individual streams
must still be reported separately and all correctness/memory gates retained.

First investigate avoiding the double sign reversal for a negative
coefficient and negative high part, observed 39946 times. Combine a positive
high product with a subtracted, correctly rounded fraction instead. Compare
all sign combinations and full setup/dispatch costs; zero and remainder
boundaries remain mandatory. This small change alone is not expected to
close the entire 8500-T gap. Subsequent work should revisit the larger
feedback/preparation costs using current measurements, rather than assuming
that accumulated small gains will deliver real-time Speex.

Reproduce with the saved fixtures and round31 image/report/OUT trace:

```text
build.py --skip-host --variant pure-r32
check_q14_product.py
check_round.py --variant pure-r32
check_unpaced.py --variant pure-r32 --previous pure-r31 --check-default
report_round.py --variant pure-r32 --previous pure-r31 --round 32
```

[Measurements](report.json), [standard checks](checks.json),
[Q14 domains, instruction costs and full trace](q14-product-checks.json),
[observed Q14 operands](observed-q14-operands.i16i32.gz),
[unpaced/default checks](unpaced-checks.json),
[generator](../../q14_product.py), [checker](../../check_q14_product.py).
