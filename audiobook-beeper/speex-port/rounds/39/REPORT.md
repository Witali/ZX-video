# Round 39: omit zero top-nibble partials in synthesis

2026-10-04. Continue from selected round38 on unchanged complete mode-3
speech. Before building, classify exact reference PCM through the real
feedback operand n=(-y)&65535: **3340 zero, 58289 nonzero values below
4096, and 125251 general values**. The zero-top class is frequent enough
to justify one sample-level dispatch and a specialized ten-tap kernel.

## Exact kernel and instruction costs

Keep the existing n=0 state-copy path. For other values, LD A,H / AND F0 /
JP Z selects the new path only when 1<=n<=4095. Such a value's signed top
nibble is zero, so that partial contributes zero to every coefficient
product. Omit its offset preparation and all ten corresponding additions.
All other signed words retain the original four-part product.

The three remaining nibble tables and state recurrence remain unchanged:

```text
state[k] = (signed16(n)*coefficient[k] + old_state[k+1]) & 0xffffffff
state[9] = (signed16(n)*coefficient[9]) & 0xffffffff
```

Ordinary AF/BC/DE/HL and IXL/IXH/IYL are scratch. The new path leaves IYH
untouched. Preserve all alternate registers, including the sample cursor,
and restore the real SP before emission. IRQ stays disabled while POP
reads coefficient tables through SP; no CALL/PUSH/RET occurs in that span.
Dropping the zero addition can alter flags, but each next state update's
ADD starts a fresh carry chain; final emission resets flags with XOR.
The full filter continues to preserve caller IX/IY and SP.

| Feedback class | Round38 T | Round39 T | Saving |
| --- | ---: | ---: | ---: |
| n=0 | 847 | 847 | 0 |
| 1<=n<=4095 | 3603 | 2950 | 653 |
| All other 16-bit words | 3603 | 3624 | -21 |

Each removed partial costs 65 T, ten times per sample. Offset preparation
costs 34 T. New dispatch costs 4+7+10=21 T on either nonzero branch; the
specialized kernel's final JP costs 10 T. Its saving is therefore
**10*65+34-21-10 = 653 T**. General nonzero values pay 21 T; zero values
skip dispatch entirely. This is deliberately not a per-sample speedup for
all inputs. Isolated measurements and instruction stepping match every path.

Complete speech saving is **58289*653 - 125251*21 = 35432446 T**, exactly
**2.27990% less CPU**. The full feedback profile changes from 664123600 to
628691154 T, with class counts matching the source inspection. Every OUT
delta equals cumulative per-sample savings, including individual negative
deltas on the general path. Both profiles preserve all uninstrumented OUT
moments. The complete decoder.s source is unchanged.

| Measurement | Round38 | Selected round39 |
| --- | ---: | ---: |
| Complete speech T | 1554122841 | 1518690395 |
| T/sample | 8316.1539 | 8126.5539 |
| First complete frame T | 1040240 | 1018120 |
| Code bytes | 9044 | 9625 |

All full-fixture costs also equal predictions from their exact feedback
classes. Savings: impulses 642399 T, low tone 39624 T, high tone 53104 T,
noise 290352 T, level jumps 690813 T, random packets 17711405 T, and
all-pitch input 4507069 T. Silence and six-bank capacity are unchanged;
none of these complete fixtures regress. Arbitrary other input can regress
if it seldom uses the specialized path.

The first build failed in Python variant wiring because a mechanical tuple
edit added an extra argument; the attempted verification then had no image.
Correct the wrapper before building the first native candidate. No native
arithmetic/PCM failure, reverted native candidate or interrupted test occurred.

## Verification and memory

- Both binaries pass **196608 isolated feedback cases**: all 65536 words
  against three coefficient arrays and 515 cyclic arbitrary histories,
  including zero, extrema and randomized state. Compare with independent
  signed multiplication and modulo-2^32 recurrence. Only the forty history
  bytes are writable; code, tables, scratch and stack writes are forbidden.
  Real SP and all alternate registers are preserved.
- **36 instruction audits per binary** cover zero, nibble/byte transitions,
  4095/4096, signs and extrema. All 19011 old and 16680 new instructions
  match the timing table, including prefixed index-half operations and
  periods with SP inside the table.
- Both versions pass **128 complete arbitrary-state filter calls**, 5120
  samples each, with exact PCM16/PCM8, final history, caller IX/IY/SP and
  protected code. Previous table-generation proofs remain applicable.
- The selected image passes **1094880 complete-stream PCM16/PCM8 samples**:
  1074400 standard speech/signal/capacity/random plus 20480 all-pitch.
  Full paging/control/cache checks, arithmetic helpers, first-frame and
  cached-silence instruction audits and fresh default identity pass.

Code grows **581 bytes**: six dispatch bytes plus a 575-byte specialized
kernel, to **9625 bytes** at 8000..A598. State remains **1041** at B000..B410,
stack BF00..BFFF, useful tables **14140** in the same 16384-byte arena.
Code/state/input require additional RAM. No table rebuild work changes.
The 23360-byte payload remains 8:1 against mono 8-kHz PCM8. Every playback
code write remains forbidden. Binary SHA-256:
`fe98f33f2068c7d9ab7b6c0e93185708a62fa3f1848a9d733d31bb2d61c3af4d`.

23.36 seconds of speech needs **433.912 nominal CPU seconds**, still
**18.5750x** the average 437.5-T/sample budget. The below-8000 intermediate
target needs another 1.56% reduction. Neither that target nor the overall
real-time objective is achieved. Output remains unpaced; ULA, disk and
physical hardware timing are unverified.

## Next candidate

Inspect the two upper partials for small signed feedback. For n in 1..255,
both are zero. For signed n in -256..-1, their sum is -256*coefficient.
A specialized low-byte kernel could omit both and, for negative n, add one
cached correction per tap. First measure both populations and compare total
cost including dispatch, any correction-table preparation on changed LPC
pages, code size and table RAM. Select one candidate only if the full cost
looks favorable; retain general and n=0 behavior. This is not implemented
and no additional saving is measured.

Reproduce with saved fixtures and the round38 build/report/OUT trace:

```text
build.py --skip-host --variant pure-r39
verify.py --native-only --restore-fixture --variant pure-r39
check_top_zero_feedback.py
check_round.py --variant pure-r39
check_unpaced.py --variant pure-r39 --previous pure-r38 --check-default
check_top_zero_feedback.py --reconcile-fixtures
report_round.py --variant pure-r39 --previous pure-r38 --round 39
```

The completed check_round run used --skip-speech to reuse the verified
speech measurement; every other full fixture was executed normally.

[Measurements](report.json), [standard checks](checks.json),
[feedback domains, input inspection and all timing proofs](top-zero-checks.json),
[unpaced/default checks](unpaced-checks.json),
[generator](../../top_zero_feedback.py), [checker](../../check_top_zero_feedback.py).
