# Optional Fast ZX0 multi-byte literal prefix

2026-10-19, baseline `674a1fc8`; the active ten-percent goal remains based on
`f5a0362c`. This is a measured intermediate component improvement, not completion
of that goal or movie/player qualification. Existing data and defaults stay exact.

`zx0.block.build(literal_prefix=True)` restores one upstream Fast LDI on the
entry where gamma decoding proves BC>=2. It shares the remaining LDIR with the
BC=1 entry. N>=2 copy cost is 16+21(N-1)-5 = **21N-10 T**, versus **21N-5 T**:
save exactly 5 T per multi-byte literal run, for two added resident code bytes.
The one-byte entry skips LDI, avoiding an erroneous 65,536-byte remaining copy.

`zx0.resumable.build(literal_prefix=True)` retains quota-before-output semantics.
Separate long/short checks share the success tail: long success first does LDI
with scratch AF while AF' holds the reservoir; EX AF,AF' restores it before the
remaining nonzero LDIR. A slow path restores live AF before saving the suspended
decoder. No extra success jump is introduced. One extra high/low target patch
costs **13+13=26 T on each begin/slice_until call**, even an already-ready return.
The option adds 24 hot bytes and six cold bytes, no extra state, buffer or stack.
Output cursors and token overshoot at every return remain identical.

## Same-feature complete native results

All 417 inputs include 364 authenticated real blocks /2,965,011 output bytes.
There are 113,897 real multi-byte literal runs and 11,584 real 256-byte demands.
Counts exclude IRQ/ULA/ROM/disk; IRQ replays are separate correctness checks.

| Profile | Real before T | Real after T | Delta T | Total code/state bytes |
| --- | ---: | ---: | ---: | ---: |
| Resident Fast | 156,012,520 | 155,443,035 | -569,485 | 207 ->209 |
| Resident +branch_tuned | 153,706,279 | 153,136,794 | -569,485 | 193 ->195 |
| Coroutine, 256-byte demands | 180,610,040 | 180,341,739 | -268,301 | 401 ->431 |
| Coroutine +branch_tuned | 178,657,995 | 178,389,694 | -268,301 | 388 ->418 |

Every block satisfies the independently decoded formula
`delta = -5 * multi_byte_literal_runs + 26 * coroutine_requests` (resident
has no synchronization term). Tuned incremental gains are 0.370502% resident
and 0.150176% coroutine; cumulative gains versus the goal baseline are only
1.843266% /1.229359%. The existing Mega real total 146,421,546 T remains faster
at 673 bytes; it is unchanged and its earlier gain does not count as new work.

No resident block slows. Each coroutine profile has 55 slower blocks,
including real-1-0 (+617 T) and real-3-116 (+17 T). Of 12,542 demand slices,
3,731 are slower, including 2,783 real slices; maximum increase is 26 T.
These are real timing regressions, preserved in the report. For frequent
requests on a stream with few multi-byte literals, leave the option disabled.
Full-demand gains cannot be substituted for the measured 256-byte workload.

## Use and memory reservations

```python
from zx0.block import build
regions, labels, metadata = build(literal_prefix=True, branch_tuned=True)
```

```powershell
python -m zx0 build --variant fast-block --literal-prefix --branch-tuned --core 0x8000 --core-limit 0x8400 --output build/zx0-prefix
python -m zx0 build --variant fast --literal-prefix --branch-tuned --core 0x8000 --core-limit 0x8400 --output build/zx0-prefix-coroutine
```

Only Fast resident/coroutine profiles support the flag. Reserve code regions
explicitly: the untuned coroutine exceeds the old default hot reservation;
the tuned variant fits with only one byte remaining. No reservation is silently
enlarged. Existing resident/coroutine ABI, writable offset, nonwrapping output,
source/history lifetime and IRQ register preservation requirements still apply.
Generated comments and metadata describe the prefix, minimum count and sync cost.

## Verification and reproduction

All 1,668 complete profile comparisons replay before/after and candidate
relocation at 9103h plus IRQ execution: 6,672 native runs. The protected resident
harness checks exact source/EOF, every output write and unchanged stack/ABI;
coroutine comparisons require identical output cursors at every return.
An independently written runner additionally checks 28 relocated case/profiles
with initial/repeated zero demands, repeated targets, byte-by-byte demands,
caller-clobbered registers and forced IRQ immediately before the shared deferred
EX AF,AF'. All 28 forced checkpoints restore working/alternate AF and continuation.
Demand sizes 2/3/17/whole-block also preserve return cursors.

All 28 library tests pass; 31 historical byte/address/label profiles and six
upstream assembly resources remain exact. Independently installed ZX0/LZSA
wheels match package sources/resources, avoid converter imports and export exact
ORG/DB regions. The earlier test expectation included the IRQ bootstrap's 26 T
only on one side; it was corrected to compare plain CPU on both sides and keep
IRQ correctness separate. No production bug was hidden by that test correction.
No new guarded-input, movie, physical disk or publication qualification is claimed.

Use `z80==1.2.0`, the existing authenticated fixtures, and TMP/TEMP inside the
worktree. [Full native data](evidence/ten_percent_literal_prefix.json),
[independent review](evidence/literal_prefix_independent_review.json), and
[authenticated sources/tests/wheels](evidence/literal_prefix_verification.json)
retain the result at this source checkpoint; later combined options need their
own comparison rather than rewriting historical artifacts.

```powershell
python libraries/tests/measure_literal_prefix.py --output libraries/evidence/ten_percent_literal_prefix.json
python libraries/tests/review_literal_prefix.py --output libraries/evidence/literal_prefix_independent_review.json
python -m unittest discover -s libraries/tests -v
python libraries/tests/verify_literal_prefix.py --directory .tmp --output libraries/evidence/literal_prefix_verification.json
```

The verifier also consumes the saved 28-test log, `.tmp/literal-prefix-wheels/`
and `.tmp/literal-prefix-smoke-{zx0,lzsa}/report.json` from the isolated pip
wheel/install/smoke checks. Their full names and hashes are retained in the
verification JSON. Use [the instruction desk reference](Z80_TIMINGS.md) when
evaluating a later change to these paths.
