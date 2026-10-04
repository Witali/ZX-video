# Round 37: fuse the LPC Q14 product and its caller's negation

2026-10-04. Continue from selected round36 on unchanged complete mode-3
speech. Twenty LPC call sites invoke mulq14 then neg32, 93440 times over
186880 samples. Add one private _q14_negated entry and replace each pair
with one call. Keep the ordinary Q14 entry and unsigned multiplier intact.

## Exact arithmetic and contracts

For signed16 a and signed32 b, retain the upstream decomposition:

```text
hi = int16(b >> 14)       # intentional signed16 truncation, including wrap
lo = b & 16383
old_result = a*hi + floor(a*lo / 16384)
new_result = -old_result
```

Split on the coefficient sign once. For a>=0, compute -a*hi and subtract
floor(a*lo/16384). For a<0, compute |a|*hi and add ceil(|a|*lo/16384).
Do not negate a signed16 coefficient as a shortcut: -32768 and fractional
rounding require these separate cases. The unsigned magnitude 32768 is
valid. The low product retains all fourteen remainder bits; ADD A,255
sets carry exactly for a nonzero remainder, and ADC includes that carry
in the ceiling. Propagate low-word carry or borrow into the upper word.

Input HL=signed16 coefficient, DE=pointer to little-endian signed32
argument; return signed32 HL:DE. Preserve IX/IY, all alternate registers
and caller SP. Ordinary AF/BC/DE/HL and the existing ten-byte Q14 scratch
are clobbered. No sign scratch or new state is needed. The helper remains
nonreentrant; caller behavior and scratch ownership are unchanged.

## Instruction-table accounting

Let U(x,y) be the already verified unsigned16 multiplication cost,
c=abs(a), and C the low-word overflow when adding ceil(c*lo/16384) to c*hi.
Every body cost below includes RET and excludes its caller's initial CALL.
The old column includes the subsequent CALL neg32 (17+67 = 84 T).

| Coefficient / high word | Old Q14 + negate wrapper | New wrapper |
| --- | ---: | ---: |
| a>=0, hi>=0 | 578 + old low carry | 603 |
| a>=0, hi<0 | 691 + old low carry | 548 |
| a<0, hi>=0 | 734 | 549 + C |
| a<0, hi<0 | 669 | 652 + C |

Add U(abs(hi),c)+U(lo,c) to either column. The common initial CALL costs
17 T on both sides and cancels. New wrapper components are dispatch 18,
argument preparation 213, fractional product preparation/extraction 153,
and coefficient normalization 0/24 T. For nonnegative a, high-sign work
costs 66/121 T for negative/nonnegative hi, and the subtract-floor tail
98 T. For negative a, high-sign work costs 145/42 T, and the add-ceiling
tail 99+C T. Independent instruction stepping verifies these sums.

Observed isolated savings range **-25..185 T**. The positive-coefficient,
nonnegative-high path regresses by 24/25 T; **6773 speech calls regress**.
The complete speech still improves by **8467830 T / 0.54046%**. Select on
full-stream evidence; this is not a guarantee that every call is faster.

An initial handwritten cost estimate missed five-T branch differences;
the preliminary boundary check rejected that estimate. The corrected
formula above passes all cases and independent instruction audits. No
native arithmetic or PCM failure occurred and no candidate was reverted.

| Measurement | Round36 | Selected round37 |
| --- | ---: | ---: |
| Q14 plus caller negate / fused body T | 163934852 | 155467022 |
| Complete speech T | 1566795471 | 1558327641 |
| T/sample | 8383.9655 | 8338.6539 |
| First complete frame T | 1051240 | 1043840 |
| Code bytes | 8889 | 9042 |

The entire saving equals the weighted isolated-call costs. Every operand
matches the authenticated round32 trace. Every OUT timestamp advances by
exactly the accumulated saving of the twenty calls before its 40-sample
subframe. Both profiled runs preserve every uninstrumented OUT timestamp.

All complete fixtures improve: silence -148080 T, impulses -148014 T,
low tone -147998 T, high tone -175374 T, noise -147971 T, level jumps
-148088 T, six-bank capacity -36390660 T, random packets -3699803 T,
and all-pitch input -928687 T. Sample counts and payload bytes are unchanged.

## Verification and memory

- **1343488 negative-Q14 cases**: every signed16 coefficient against twelve
  signed32 boundary arguments; every fourteen-bit fraction against 32
  coefficient/high-word pairs; 32768 deterministic random signed32 cases.
  Check exact result, rounding, cycle formulas, preserved registers/input,
  and narrowly guarded writes. Measured body costs span 649..2232 T.
- **374 actual caller-sequence cases per binary**, with 54851 old and 50136
  new instructions checked against the Z80 timing table. Also audit 374
  ordinary Q14 boundary cases per binary; its original result is retained.
- **1094880 complete PCM16/PCM8 samples**: 1074400 standard speech/signal/
  capacity/random samples plus 20480 all-pitch samples. Full content,
  paging, code/input guards, table/cache checks and a fresh default-build
  identity pass. First-frame and cached-silence instruction audits pass.
- The retained decoder prefix and complete filter assembly sources match
  round36. Reuse earlier exhaustive unsigned-product and cosine proofs;
  relocation is additionally covered by the complete new-image checks.

Code grows by 153 bytes to **9042** at 8000..A351: the 213-byte private
helper replaces sixty caller bytes. State stays **1041** at B000..B410,
stack reserve BF00..BFFF, and useful tables **14140** in the same 16384-byte
arena. Code/state/input are additional RAM. The 23360-byte payload remains
8:1 against mono 8-kHz PCM8. Playback code is write-protected. Binary SHA-256:
`0d5d89d71c04a7c08796c6dc843b3f06d9c1b6d40db76f2196781af79bdfb2a6`.

23.36 seconds of speech needs **445.236 nominal CPU seconds**, still
**19.0598x** the average 437.5-T/sample budget. Output remains unpaced.
ULA, disk and physical hardware timing are unverified. The below-8000
intermediate target and the overall real-time goal remain unmet.

## Next candidate

The private helper copies all four argument bytes through LDIR, then
reloads the high word. Only the low word must survive for the fractional
product. Inspect direct reads that save the low word and retain the high
word in registers. Instruction-table estimate: 119 ->74 T for that region,
45 T per call, excluding the unchanged coefficient store. This is not yet
implemented or measured; retain rounding, pointer boundaries, register
contracts and full-stream checks. Do not change the ordinary public entry.

Reproduce with saved fixtures and the round36 build/report/OUT trace:

```text
build.py --skip-host --variant pure-r37
verify.py --native-only --restore-fixture --variant pure-r37
check_q14_negated.py
check_round.py --variant pure-r37
check_unpaced.py --variant pure-r37 --previous pure-r36 --check-default
report_round.py --variant pure-r37 --previous pure-r36 --round 37
```

The completed check_round run used --skip-speech, reusing the already
verified speech run while executing every other full fixture normally.

[Measurements](report.json), [standard checks](checks.json),
[Q14 domains, caller audits and cost/OUT proof](q14-negated-checks.json),
[unpaced/default checks](unpaced-checks.json),
[generator](../../q14_negated.py), [checker](../../check_q14_negated.py).
