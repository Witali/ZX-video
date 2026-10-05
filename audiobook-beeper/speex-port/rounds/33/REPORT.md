# Round 33: sign-specific Q14 combination without double negation

2026-10-04. Continue from round32 on unchanged complete mode-3 speech.
Dispatch once on the coefficient sign and duplicate the short Q14 body.
Prepare its magnitude once, restore the high product's final sign, then
add the floor of a nonnegative fraction or subtract its ceiling. This
removes the negative-coefficient/negative-high double negation and the
sign scratch store/reload. The public signed and unsigned products stay
unchanged; the entire generated filter unit matches round32 byte for byte
as assembly text. No new table or state allocation is needed.

## Exact arithmetic and carries

Keep the upstream expression and its intentional high-part wrap:

```text
hi = int16(b >> 14)
lo = b & 16383
H = a*hi
P = abs(a)*lo
Q = floor(P/16384)
result = H+Q                  if a >= 0
result = H-Q-(P%16384 != 0)    if a < 0
```

Input HL is signed16 a; DE points to little-endian signed32 b. Return
signed32 HL:DE. Preserve IX/IY, all alternate registers and caller SP.
Only qcoef/qarg/qtemp (ten bytes) and the reserved real stack may be
written. The old sign slot remains allocated for compatibility but is no
longer read or written. Ordinary AF/BC/DE/HL are clobbered; the scratch
implementation remains nonreentrant.

P is below 2^29 and Q fits nonnegative signed16. In the positive body,
add Q to H's low word and increment its high word only on carry. In the
negative body, preserve the low product word DE while extracting Q into
HL, then form R=(D&63)|E. ADD A,255 sets carry exactly when R is nonzero;
use that carry as the rounding borrow in SBC HL,BC. A second upper-word
SBC propagates the low borrow. Intervening LD and EX preserve carry.
Zero, -32768, exact/non-exact fractions and high truncation are all exact.

## Instruction accounting and comparison

Both versions call the same unsigned helper twice: U(abs(hi),abs(a)) and
U(lo,abs(a)). Reuse its round32 instruction formula and prior exhaustive
proof. The complete wrapper costs below include coefficient normalization,
argument copy/extraction, scratch, calls, sign handling, combination and RET.

| Coefficient / high sign | Round32 wrapper | Round33 wrapper | Saving |
| --- | ---: | ---: | ---: |
| Nonnegative / nonnegative | 572 T | 494 or 495 T | 78 or 77 T |
| Nonnegative / negative | 685 T | 607 or 608 T | 78 or 77 T |
| Negative / nonnegative | 683 exact, 680 fractional | 650 T | 33 or 30 T |
| Negative / negative | 796 exact, 793 fractional | 585 T | 211 or 208 T |

The positive one-T variation is the low-word carry branch. These exhaust
all coefficient/high/remainder/carry cases: nominal Q14 cost improves by
**at least 30 T for every input** relative to round32, independent of the
unchanged helper costs. This is an instruction-count claim, not a physical
Spectrum timing guarantee.

Reuse the authenticated round32 operand archive. Every one of 93440 calls
receives the same pair; 84220 unique pairs are executed on both binaries.
Weighted isolated costs match the archived/current Q14 profiles and the
entire complete-stream delta. Profiling the new binary preserves every
uninstrumented OUT timestamp. All observed calls improve: 30557 save 30 T,
47 save 33 T, 2500 save 77 T, 20390 save 78 T, 35853 save 208 T and 4093
save 211 T.

| Measurement | Round32 | Selected round33 |
| --- | ---: | ---: |
| Q14 T | 167108120 | 156085892 |
| Complete speech T | 1630001442 | 1618979214 |
| T/sample | 8722.1824 | 8663.2021 |
| First complete frame T | 1090996 | 1081400 |
| Code bytes | 9038 | 9046 |

Select the **11022228 T / 0.6762%** complete saving. All other full fixtures
improve: silence -191760 T, impulses -191897 T, low tone -191544 T, high
tone -163833 T, noise -191764 T, level jumps -191452 T, six-bank capacity
-47125020 T, random packets -4808708 T and all-pitch input -1208777 T.
The initial arithmetic probe was followed by full domain and stream checks;
no failed candidate, revert or interrupted verification occurred.

## Verification and memory

Execute **1343488 Q14 cases**: every signed16 coefficient against 12
signed32 boundaries, every 14-bit fraction against 32 coefficient/high
pairs, and 32768 random signed32 inputs. All eight sign/carry/rounding
classes occur. Full signed32 results, exact instruction formulas, register
contracts, unchanged input and narrowly guarded writes all pass. Savings
are exactly one of 30/33/77/78/208/211 T throughout the domain.

Independently instruction-step 374 boundary pairs per binary: 53937
baseline and 49241 new instructions match the timing table. The unchanged
unsigned helper/filter source identity allows reuse of round32's 1179648
unsigned word cases and round31's exhaustive unsigned8x16 core proof.

Standard **1074400** plus all-pitch **20480 complete PCM16/PCM8 samples**
pass, totalling **1094880 exact samples**. Generic arithmetic, control
paths, table construction/cache, full-frame and cached-silence instruction
audits, protected playback memory and fresh default image identity pass.

Code is 9046 bytes at 8000..A355, +8 bytes. State remains 1041 bytes at
B000..B410, stack reserve BF00..BFFF. Tables remain 16010 useful bytes
within a 16384-byte arena; code/state/input are additional RAM. Compressed
payload is unchanged at 23360 bytes, 8:1 against mono 8-kHz PCM8. Every
playback code write remains forbidden. Binary SHA-256:
`b74f241d3902cb049cd0f168b83172dc944c5be1e57367d42d9fc89ccd21ccce`.

23.36 seconds of audio needs 462.565 nominal CPU seconds, **19.8016x**
the 437.5-T/sample real-time budget. Output remains unpaced. ULA, disk and
physical hardware are unverified. The real-time objective remains active.

## Next candidate and target

The below-8500 intermediate target remains unmet; another 30499214 T must
be saved to reach 8500 T/sample on the same speech. Inspection of the
current generated coefficient builder finds **64 adjacent EXX/EXX pairs**
inside one changed-page path. Each pair restores the original register
selection without changing flags or memory, wasting 8 nominal T. Removing
only those pairs predicts **512 T per changed page**, or **22882304 T**
using the saved 44692-page count. This would reach about 8540.76 T/sample,
still short of 8500. The next candidate is not implemented or executed.

Restrict cancellation to that builder, check every signed16 coefficient
and table entry, preserve cached-page behavior and real SP, then reconcile
the predicted saving with complete measured playback. Do not count this
estimate as achieved or repeat unrelated parameter searches.

Reproduce with saved fixtures and round32 image/report/operand evidence:

```text
build.py --skip-host --variant pure-r33
verify.py --native-only --restore-fixture --variant pure-r33
check_q14_sign.py
check_round.py --variant pure-r33
check_unpaced.py --variant pure-r33 --previous pure-r32 --check-default
report_round.py --variant pure-r33 --previous pure-r32 --round 33
```

[Measurements](report.json), [standard checks](checks.json),
[Q14 domain, instructions and full cost reconciliation](q14-sign-checks.json),
[unpaced/default checks](unpaced-checks.json),
[reused input operands](../32/observed-q14-operands.i16i32.gz),
[generator](../../q14_product.py), [checker](../../check_q14_sign.py).
