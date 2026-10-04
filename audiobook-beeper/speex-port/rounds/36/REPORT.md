# Round 36: exact direct cosine lookup with a complete fallback

2026-10-04. Continue from round35 on unchanged complete mode-3 speech.
The packed cosine helper reads an anchor and accumulates up to fifteen
nibble deltas per call. Observe the complete input first: **46720 calls,
5475 unique angles, all multiples of four**. Margin averaging can produce
other residues, so an aligned-only implementation would be incorrect.

Store exact cos_int(4*i) words for the folded positive half, i=0..3217:
**6436 bytes**. For an aligned angle x, its word's byte offset is x/2.
Retain the old fold/sign convention at 12868 and 25736. For all remaining
angles, evaluate the original rounded integer polynomial. No angle is
rounded to the lookup grid and no PCM precision changes.

A preliminary host-only packing inspection covered block sizes 4/8/16.
Of 805 sixteen-angle blocks, 46 span more than four bits, up to 21 units;
plain nibble offsets would therefore need exception handling. No such
native candidate was implemented. The measured common alignment supports
one direct-table candidate with a full arithmetic fallback instead. The
inspection is reproduced in the checker and saved with its evidence.

## Exact polynomial and instruction costs

The fallback uses the same expression as the prior table generator:

```text
P13(a,b) = (a*b + 4096) >> 13
x2 = P13(x,x)
cos_int(x) = 8192 + P13(x2, -4096 + P13(x2, 340 + P13(-10,x2)))
```

All intermediate P13 results fit signed16 for folded x in 0..12868. The
new helper multiplies signed16 operands with the existing exact multiplier,
adds the rounding constant across both words and extracts bits 13..28.
Its full signed32 product plus 4096 is safe for all signed16 operands.
It returns the low signed16 word; cosine's domain requires no truncation
beyond that representation. The two old contiguous cosine scratch bytes
hold x2, and the fold sign is saved on the real stack across either path.

Input is HL=0..25736, output signed16 DE. Preserve IX/IY, all alternate
registers and caller SP. Ordinary AF/BC/DE/HL, the two cosine scratch bytes
and the multiplier sign scratch are clobbered. The path is nonreentrant,
as before. The nested fallback calls stay inside the guarded stack reserve.

For the old helper, let n=folded_x mod 16 and p=floor(n/2). Cost is
356 T when p=0, otherwise 346+117*p T, plus 68 T for odd n and 61 T for
the upper half. The new aligned path costs **177 T below 12868, 237 T at
or above it**, versus 356..1294 T over the old helper's full domain.

A P13 call body costs M(a,b)+132+c T, where M is the already verified
signed-word multiplication cost and c is one when the low product word
plus 4096 carries. The full unaligned cosine costs 324/384 T for lower/
upper-half setup and combination, plus its four P13 bodies. Every formula
is checked against actual execution for every legal angle.

The fallback is deliberately exact and slower: complete helper costs now
range **177..3771 T**. Across all angles, savings range from -3248 to +872 T;
only aligned inputs are guaranteed faster. This is not a universal per-call
speedup. The full random-packet fixture exercises two residue-2 inputs
among 20480 cosine calls; it still improves by 9414811 T, with exact output.

| Measurement | Round35 | Selected round36 |
| --- | ---: | ---: |
| Speech cosine T | 30846551 | 9544980 |
| Complete speech T | 1588097042 | 1566795471 |
| T/sample | 8497.9508 | 8383.9655 |
| First complete frame T | 1067580 | 1051240 |
| Code bytes | 8891 | 8889 |
| Useful static table bytes | 12658 | 10788 |

Select **21301571 T / 1.3413% less complete CPU**, with **69.0566% less
cosine CPU** on speech. Both observed angle sequences match. The weighted
isolated cost formulas equal the function profiles and entire saving.
Every OUT advances by exactly the accumulated cosine savings before its
40-sample subframe. Profiling preserves every OUT timestamp in both images.

All complete fixtures improve: silence -326800 T, impulses -356570 T,
low tone -324968 T, high tone -355661 T, noise -373974 T, level jumps
-341456 T, six-bank capacity -80311100 T, random packets -9414811 T,
and all-pitch input -2327169 T. No native failure, reverted candidate or
interrupted verification occurred. The preliminary packing work was a
host-only inspection, not another decoder implementation.

## Verification and memory

- All **25737 legal angles on both binaries**, including 6435 aligned and
  19302 unaligned inputs: exact prior/upstream polynomial values, exact
  instruction formulas, preserved registers/SP and narrowly guarded writes.
- **720896 P13 cases**: every signed16 word against eleven constants,
  including both extrema, signs, zero and rounding/carry boundaries.
  Verify the low16 rounded result, exact cost and register/write contracts.
- Independent instruction stepping of **82 boundary/residue cases per
  binary**: 8544 old and 22421 new instructions all match the timing table.
- Standard **1074400** plus all-pitch **20480 complete PCM16/PCM8 samples**
  pass, totalling **1094880 exact samples**. This includes full execution
  of the fallback on random packets. Generic arithmetic, table/cache and
  control checks, complete-frame/cached-silence instruction audits,
  protected playback memory and fresh default identity pass.

Code is 8889 bytes at 8000..A2B8, two bytes smaller. State remains 1041
bytes at B000..B410; stack reserve remains BF00..BFFF. Replace the old
8050-byte packed table and 256-byte pair-sum table with 6436 exact word
bytes at 4000..5923, saving **1870 bytes**. Useful tables are now **14140
bytes** (10788 static + 3352 dynamic) within the same 16384-byte arena.
Code/state/input require additional RAM. Existing table addresses outside
the replaced cosine region, payload and all playback code guards stay intact.
Payload is 23360 bytes, 8:1 against mono 8-kHz PCM8. Binary SHA-256:
`5b34ecca4931423b3366c3a8d9a5a32cec8c8456778e4312f6705f5927844e9b`.

23.36 seconds of audio needs 447.656 nominal CPU seconds, **19.1633x**
the 437.5-T/sample real-time budget. The below-8500 intermediate milestone
stays met, but the overall real-time goal remains active. Output is unpaced;
ULA, disk and physical hardware are unverified.

## Next candidate

The next intermediate target is below 8000 T/sample on the same complete
speech, another 4.58% reduction. It is unachieved; this individual candidate
is not assumed to deliver that entire saving.

The LPC generator has twenty adjacent `call mulq14 / call neg32` sites,
executed 93440 times on this speech. The separate neg32 costs 67 T plus
17 T for its call. Investigate a private Q14 entry returning the negated
result directly, retaining the ordinary entry's contract. This may remove
the separate negation, but the full combined cost must include changed sign
branches and exact floor/ceiling handling. Do not simply negate the signed16
coefficient: -32768 and the high-part truncation require their current exact
semantics. Reuse the archived Q14 operands and all domain/stream gates.
No combined path is implemented and no net saving is yet measured.

Reproduce with saved fixtures and the round35 image/report/OUT trace:

```text
build.py --skip-host --variant pure-r36
verify.py --native-only --restore-fixture --variant pure-r36
check_direct_cosine.py
check_round.py --variant pure-r36
check_unpaced.py --variant pure-r36 --previous pure-r35 --check-default
report_round.py --variant pure-r36 --previous pure-r35 --round 36
```

The completed check_round run used --skip-speech to reuse the verified
speech measurement; every other full fixture was executed normally.

[Measurements](report.json), [standard checks](checks.json),
[angle/P13 domains, packing inspection and cost proofs](direct-cosine-checks.json),
[observed speech angles](observed-cosine-angles.u16.gz),
[unpaced/default checks](unpaced-checks.json),
[generator](../../direct_cosine.py), [checker](../../check_direct_cosine.py).
