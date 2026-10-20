# Shared ZX0 Maximum prefixes and cloned continuations

Completed 2026-10-20 after the [selective-sharing screen](SHARED_PREFIX_SCREEN.md).
The optional resident [maximum.build](zx0/src/zx0/maximum.py#L20) argument
`shared_prefixes=True` makes the measured Maximum profiles smaller and faster.
All existing default profiles remain byte/label exact. Forward ZX0 v2 data,
the resident ABI and the source/history requirements stay unchanged.

## Results

Same 417 main cases, including the same 364 real blocks; CPU excludes IRQ
execution, WAIT/ULA contention, physical disk/ROM and movie publication.
Service includes every emitted code/embedded-state byte and the four-byte
maximum caller/source stack. Tables, padding, scratch and internal buffers
are zero. Input and output/history are separate, as authorized.

| Cap | Original service B | Shared service B | Original real CPU T | Shared real CPU T | CPU delta T |
| --- | ---: | ---: | ---: | ---: | ---: |
| 31 | 4,454 | 2,810 | 141,618,798 | 141,342,108 | -276,690 |
| 63 | 5,990 | 3,578 | 140,680,558 | 140,403,868 | -276,690 |
| 127 | 7,526 | 5,114 | 140,193,198 | 139,916,508 | -276,690 |
| 227 | 9,966 | 7,554 | 140,170,198 | 139,893,048 | -277,150 |
| 228 | 9,990 | 7,578 | 140,169,968 | 139,892,818 | -277,150 |

The fastest cap228 saves 2,412 service bytes and 277,150 real T (about
0.198%) against the previous fastest cap228. Shared cap127 is also faster
than that previous maximum while using 4,876 fewer bytes. The last 2,464 B
from shared127 to shared228 save only 23,690 T. No tested complete block
slows against its same-cap original. This finite frontier does not prove
global optimality or another 10% beyond the stronger existing Mega.

## Why sharing costs no extra jump

The [layout transform](zx0/src/zx0/_shared_prefixes.py) keeps original small
LDIR tails in place. Each phase/family shares one descending LDI chain with
entry labels for the proven prefix lengths. After that chain it clones the
original LDIR/command continuation up to an existing unconditional JP.
Every local label in the clone is remapped. References to the one mutable
negative-offset word still target the original operand.

Originally a prefix performs setup, P LDIs and a 10-T JP to its tail. The
shared layout performs setup, that same 10-T JP to the shared entry, P LDIs
and the cloned tail. There is no new return jump. Reuse phases1/3/5 invert
their existing JP condition and fall through into a cloned literal header;
both JP outcomes remain 10 T. Phase7 retains its original branch pair.

Four literal >=4 entries can target the shared suffix directly, eliminating
one JP. Caps227/228 also eliminate the old intermediate word-prefix JP.
LDI remains 16 T; the positive LDIR tail remains 21N-5 T. Per block the
independently observed difference is exactly:

```text
shared_T - original_same_cap_T =
    -10 * original_literal4_entries
    -10 * original_word_joins_eliminated_at_caps_227_228
```

Original small-copy instructions, gamma shifts, forward overlap semantics,
input consumption and caller/alternate-register ownership are retained.
No state or temporary buffer is introduced by continuation cloning.

## Use and limits

```python
from zx0.maximum import build
from zx0.export import export

export("build/zx0-shared", *build(prefix_cap=127, shared_prefixes=True,
       irq_code_bytes=13, irq_stack_bytes=6))
```

```powershell
python -m zx0 build --variant maximum --shared-prefixes --prefix-cap 228 --output build/zx0-shared
```

The generated entry remains `dzx0_mega`: HL=input, DE=output, caller stack;
AF/BC/DE/HL clobbered, IX and alternate registers preserved. Keep complete
valid source/history resident, output nonwrapping and code writable and
nonreentrant. The caller validates allocations. Actual application IRQ code,
state and extra stack must be declared/counted. The tested 13-byte handler
and six stack bytes make shared228 total 7,597 B, well below 10,000 B.

This transformation is resident-only. Quota hooks and the CLI coroutine
combination explicitly reject it. Existing Maximum coroutines retain their
separately verified implementations. No streaming, physical-disk or player
release qualification follows from this resident proof.

## Verification and reproduction

All five caps pass 417 main and 56 high-word cases, each with a protected
baseline/candidate replay, IRQ replay and relocation: 2,365 candidate
comparisons /9,460 native runs. High-word counts include 32,767/32,768/49,151,
new/reused offsets and distance-1/2 overlapping history. Every output byte,
source cursor, EOF, patched write, caller/alternate register and stack bound
is checked; every CPU delta matches the independent JP-count formula.
Plain stack is at most four bytes, diagnostic-IRQ stack at most ten.

- [Main native proof](evidence/shared_zero_prefix_native.json.gz).
- [High-word native proof](evidence/shared_zero_prefix_high_word.json.gz).
- [Public/wheel authentication](evidence/shared_zero_prefix_verification.json).
- [Frozen test prototype](tests/shared_zero_prefix_profile.py),
  [native reproducer](tests/measure_shared_zero_prefix.py),
  [integration verifier](tests/verify_shared_zero_prefix.py).

```powershell
python libraries/tests/measure_shared_zero_prefix.py --output libraries/evidence/shared_zero_prefix_native.json.gz
python libraries/tests/measure_shared_zero_prefix.py --high-word --output libraries/evidence/shared_zero_prefix_high_word.json.gz
python -m unittest discover -s libraries/tests -v
python -m pip wheel --no-deps --no-build-isolation --wheel-dir .tmp/shared-prefix-wheels libraries/zx0
python libraries/tests/verify_shared_zero_prefix.py --wheel .tmp/shared-prefix-wheels/zxvideo_zx0-0.1.0-py3-none-any.whl --output libraries/evidence/shared_zero_prefix_verification.json
```

Use the pinned native dependency and worktree-local TMP/TEMP. The verifier
consumes `.tmp/shared-prefix-library-tests.log`, checks all 31 legacy layouts,
binds public regions to both complete native reports and builds/exports all
five profiles from an isolated installed wheel without toolkit/native imports.
