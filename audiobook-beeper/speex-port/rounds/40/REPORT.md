# Round 40: exact small signed feedback with subtractive state updates

2026-10-04. Continue from round39 on unchanged complete mode-3 speech.
Inspect actual n=(-y)&65535 values: 3340 zero, 17835 small positive,
18461 small negative, 40454 other top-zero, 106750 general and forty -256
words. Select two low-byte kernels, reaching **7960.218 T/sample** and
meeting the **below-8000 intermediate target** on this complete input.

## Representation choice and exact arithmetic

For n=1..255, the two upper nibble products are zero. For signed n=-255..-1,
use the positive byte magnitude m=-n and fuse the sign into the history
update: state[k]=old_state[k+1]-m*coefficient[k], modulo 2^32. The final
state has no successor, so negate its complete product in registers.
The -256 boundary retains the general kernel; its magnitude is not a byte.
All other signed words and the existing n=0 behavior remain exact.

The proposed cached negative correction would need ten extra three-byte
adds (about 630 T/sample) plus preparation when LPC pages change. Fusing
subtraction instead adds **9*8+54 = 126 T/sample** to the low-byte kernel,
plus magnitude normalization, and needs no correction table or preparation.
No cached-correction native candidate was built. Keep table allocation and
all coefficient preparation unchanged.

Both short kernels use only IXL/IXH for two nibble offsets. IY is untouched.
Preserve the real SP and every alternate register, including the sample
cursor. Ordinary registers and IX halves are scratch. IRQ stays disabled
while POP reads tables through SP; no CALL/PUSH/RET occurs before restoration.
The full filter retains caller IX/IY/SP. Each subtractive state update clears
carry before low-word SBC and propagates its borrow through LD to upper SBC.

## Cost accounting and measured results

| Feedback value | Round39 T | Round40 T | Saving |
| --- | ---: | ---: | ---: |
| 0 | 847 | 847 | 0 |
| 1..255 | 2950 | 2284 | 666 |
| -255..-1 | 3624 | 2440 | 1184 |
| 256..4095 | 2950 | 2968 | -18 |
| -256 | 3624 | 3660 | -36 |
| All other signed16 values | 3624 | 3642 | -18 |

The existing round39 dispatch stays. Both new class tests cost 18 T. The
positive path removes ten 65-T partials and 34-T offset setup, less its new
18-T dispatch: **650+34-18=666 T saved**. The negative path removes two
such groups, saving 1368 T. Costs are two 18-T checks, 12-T byte normalization,
10-T final JP and 126 T for fused subtraction/final negation:
**1368-18-18-12-10-126=1184 T saved**. The -256 fallback pays both checks.

The final 32-bit negation costs 54 T. Intermediate bytes use LD A,0 / SBC
so the borrow remains valid. Only the final byte can use SBC A,A / SUB,
because its outgoing borrow is discarded. Every instruction and path cost
is checked independently against the timing table.

Full speech saving is exactly:

```text
17835*666 + 18461*1184 - (40454+106750)*18 - 40*36 = 31084822 T
```

Select **2.04682% less complete CPU**, with unchanged exact PCM. Feedback
profile costs 628691154 ->597606332 T. Every class count matches the input
inspection; every OUT delta equals the cumulative per-sample prediction.
Both profiles preserve all uninstrumented OUT timestamps. decoder.s is
unchanged at source level.

| Measurement | Round39 | Selected round40 |
| --- | ---: | ---: |
| Complete speech T | 1518690395 | 1487605573 |
| T/sample | 8126.5539 | 7960.2182 |
| First complete frame T | 1018120 | 961246 |
| Code bytes | 9625 | 10527 |

Full fixtures have explicit tradeoffs. Impulses save 1506162 T, noise 10368 T,
level jumps 916158 T, random packets 14199916 T and all-pitch input 3158290 T.
Silence and six-bank capacity are unchanged. **Low tone regresses by 34212 T
(0.1535%), high tone by 33010 T (0.1398%)** because short values are rare.
Every full-fixture delta matches its class prediction. Select for the complete
speech target and substantial random/all-pitch gains; do not claim a universal
speedup or hide the tone regressions. The previous variant remains selectable.

## Failures resolved and verification

A wrong Python executable path initially prevented file creation. A generator
assertion then rejected an overly strict comment match before assembly;
fix both before the first native build. That first native candidate failed
at sample 100: PCM16 -61 instead of -69. Its final negate used SBC A,A / SUB
on intermediate bytes, which can lose the borrow. Replace those intermediate
steps with LD A,0 / SBC, keep the shortened operation only on the final byte,
and add the dedicated exhaustive borrow-domain test below. The corrected
candidate passes every test; no failed native result is selected.

- Both binaries pass **196608 feedback cases**: all 65536 words against
  three coefficient arrays and 515 arbitrary histories. Only forty history
  bytes are writable; real SP and all alternate registers are preserved.
- **54 feedback instruction audits per binary**, 26220 old and 21729 new
  instructions, include signs, -257/-256/-255 and 255/256 boundaries. Every
  instruction matches the timing table, including borrowed-table SP periods.
- **327680 standalone negate cases**: every low word against five high
  words, covering signed/unsigned extremes and all intermediate borrow
  boundaries. All memory writes are forbidden, SP points inside the table,
  and HL, indexes and alternates stay intact. Forty instruction audits
  (480 instructions) all confirm the exact 54-T body.
- Both binaries pass **128 complete arbitrary-state filter calls**, 5120
  samples each, with exact final history, PCM16/PCM8 and caller IX/IY/SP.
- Selected **1094880 complete-stream PCM16/PCM8 samples** pass: 1074400
  standard speech/signal/capacity/random plus 20480 all-pitch. Full cache,
  paging, code/input guards, generic arithmetic and first-frame/cached-silence
  instruction audits pass. Fresh default identity matches. Every fixture
  cost is reconciled, including regressions.

Code grows **902 bytes** to **10527** at 8000..A91E. State remains **1041**
at B000..B410, stack BF00..BFFF. Useful tables stay **14140** in the same
16384-byte arena; code/state/input require additional RAM. Coefficient
preparation stays 49703 T in its audit. The payload remains 23360 bytes,
8:1 against mono 8-kHz PCM8. Every playback code write remains forbidden.
Binary SHA-256:
`f49f43048e862c274148efb279905dd5f4308e1f16f1573f5af3dcc7c1320f24`.

23.36 seconds of speech needs **425.030 nominal CPU seconds**, still
**18.1948x** the average 437.5-T/sample budget. Meeting below 8000 does not
complete the real-time goal. Output stays unpaced. ULA, disk and physical
hardware timing are unverified.

## Next candidate

Inspect the same magnitude/subtraction approach for negative 12-bit feedback.
For -4095..-256, a positive magnitude fits three partials; a dedicated kernel
could omit the signed top partial while subtracting from history. Count
eligible samples, include the new dispatch and normalization, and preserve
-4096/general fallbacks and the existing small-value kernels. The current
code leaves 1761 bytes before state, so account for the added kernel. This
is unimplemented and unmeasured. The next intermediate target is below
7800 T/sample; the original average real-time objective remains active.

Reproduce with saved fixtures and the round39 build/report/OUT trace:

```text
build.py --skip-host --variant pure-r40
verify.py --native-only --restore-fixture --variant pure-r40
check_small_feedback.py
check_round.py --variant pure-r40
check_unpaced.py --variant pure-r40 --previous pure-r39 --check-default
check_small_feedback.py --reconcile-fixtures
report_round.py --variant pure-r40 --previous pure-r39 --round 40
```

The completed check_round run used --skip-speech to reuse the verified
speech measurement; every other full fixture was executed normally.

[Measurements](report.json), [standard checks](checks.json),
[feedback/borrow domains, inspection and cost proofs](small-feedback-checks.json),
[unpaced/default checks](unpaced-checks.json),
[generator](../../small_feedback.py), [checker](../../check_small_feedback.py).
