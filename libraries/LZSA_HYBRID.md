# Fixed resident LZSA2 hybrid profiles

Completed 2026-10-20 after the independent [short-copy](WIDE_SHORT_EXPERIMENT.md)
and [hybrid-handler](WIDE_HYBRID_EXPERIMENT.md) experiments. The optional
[lzsa.hybrid.build](lzsa/src/lzsa/hybrid.py) API exports fixed, measured raw
LZSA2 decoders. Existing Fast/Wide/Shared defaults retain their exact bytes
and labels. Compatible data does not need recompression.

## Choose an implementation

Same frozen 21-real-block corpus, 323,940 decoded bytes. These are complete
deterministic instruction counts, excluding IRQ/ULA/WAIT/physical disk/ROM.
Service counts all code, the 512-byte table, embedded offset state, alignment
and the six-byte maximum caller stack. The two offset bytes are already in
code and count once; extra state/scratch/internal buffers are zero. Input
and decoded output/history are separate, as authorized.

| Builder profile | Aligned service B | Real CPU T | CPU-time reduction vs old Expanded |
| --- | ---: | ---: | ---: |
| Original Shared | 3,452 | 15,869,483 | -1.571497% |
| Original Expanded | 7,004 | 15,623,953 | baseline |
| `compact-base` | 3,452 | 15,822,353 | -1.269845% |
| `balanced-base` | 4,499 | 15,683,583 | -0.381658% |
| `fast-base` | 5,500 | 15,643,493 | -0.125064% |
| `compact` | **4,999** | **15,048,469** | **3.683344%** |
| `balanced` | **6,500** | **14,983,119** | **4.101612%** |
| `fast` (default of this new builder) | **9,500** | **14,944,429** | **4.349245%** |

The compact point saves 2,005 B and 575,484 T against the previous fastest
Expanded. The fast point saves 679,524 T for 2,496 additional service bytes.
Against pass-baseline Fast (17,765,094 T), their total gains are 15.291926%
and 15.877569%, including the earlier Wide benefit. Do not attribute that
earlier benefit to this follow-up. Corpus gains are not universal bounds.

```python
from lzsa.hybrid import build
from lzsa.export import export

export("build/lzsa", *build(profile="compact", core=0x8000))
```

The function-linked [complete variant table](DECODER_VARIANTS.md) also retains
direct [wide.build](lzsa/src/lzsa/wide.py) calls with explicit `short_lengths`
and `repeat_lengths`. Shared plus new2..8/repeat4..8 uses 4,228 B /
15,188,829 T. Expanded new3..8 uses 9,524 B /14,999,606 T with no slower
cases versus old Expanded. Full new2..8 uses 9,748 B /14,975,960 T aligned,
but at 9003h needs 10,001 B and is rejected. The fixed fast hybrid fits at
arbitrary table alignment: at most 9,755 intrinsic B; actual IRQ is additional.

## Algorithm and exact CPU accounting

For each XYZ/MMM body, all four literal LL forms remain available. An offline
bounded selector chooses one through four body copies and the fallthrough
LL member of each group. Every other shared member pays one 10-T JP. Three-
byte JP-only bodies can split without adding bytes. The package embeds fixed
selector constants; it never reads benchmark reports or profiles user data
at runtime. Rankings came from this corpus; another workload can rank them
differently. No token, cold case or valid short word escape is omitted.

Known new-offset lengths2..8 reuse the negative offset already in BC before
making BC the copy count. The complete copy path changes 21n+76 ->16n+80 T,
saving 5n-4 T. Known repeated lengths4..8 load the retained offset and copy
with n LDIs: 21n+49 ->16n+65 T, saving 5n-16 T. Repeated lengths2/3 keep their
old paths because those kernels would lose time. MMM7 keeps the original
nibble/byte/word decoder, including legally short escaped word lengths.
For every case the independent model is exactly:

```text
hybrid_T = old_Expanded_T - sum(short_kernel_savings) + 10 * shared_body_hits
```

Forward LDI order preserves overlapping distance-1/2 history. BC becomes zero
after each short kernel. Input HL is saved/restored on the existing caller
stack; A/AF' reservoir ownership, the original offset store and exact EOF
behavior are retained. No new self-modifying operand or IRQ masking is added.

## Verified scope and regressions

Every fixed profile passes 95 corpus plus 580 directed cases, including all
256 token values in both nibble phases, all 64 offset-nibble forms, word
literal lengths1/2 and single-nibble EOF. Protected replays verify exact
data/input/EOF/registers, IRQ and relocation to 9103h. Each case reconciles
the instruction model above, not just the real-corpus sum.

All real blocks improve over old Expanded in the three short-kernel hybrids.
The fast hybrid has four directed regressions, each +4 T: token-e0/e1 in
both empty/full phases. It has no slower case versus old Shared. Compact
and balanced have 208/83 slower cases across the full 675-case suite versus
Expanded (58/16 non-real corpus and 150/67 directed), maximum196/14 T,
and four/two versus Shared, maximum4 T. The base profiles retain
their separate +10-T directed counterexamples. Full per-case lists remain
in the native reports and selector evidence.

Call generated `start` with HL=input, DE=output and the caller stack. Main
AF/AF'/BC/DE/HL are clobbered; IX/IY and alternate pairs are preserved at
EOF. Code/offset state must be writable and nonreentrant; input/history
must remain readable and output must not wrap. Caller validates allocation.
IRQ preserves all live main/alternate registers, including temporary HL'
during dispatch. Plain stack peaks at six bytes; the diagnostic IRQ uses
six extra stack bytes plus thirteen code bytes. Fast at 9103h plus that
IRQ totals 9,772 B, below the 10,000-B service cap.

These new options are resident-only. Quota/guard-hook combinations reject
until separately qualified; ordinary/guarded coroutines keep their previous
verified implementations. Actual producer buffers/workspace, disk delivery
and movie deadlines are not qualified by this raw decoder proof.

## Evidence and reproduction

- [Fixed selectors and every regression](evidence/wide_hybrid_experiment_selectors.json).
- [Complete hybrid native evidence](evidence/wide_hybrid/wide_hybrid_experiment_short.json.gz).
- [Complete base-profile evidence](evidence/wide_hybrid/wide_hybrid_experiment.json.gz).
- [Public API/wheel authentication](evidence/hybrid_public_verification.json).
- [Independent experiments](WIDE_HYBRID_EXPERIMENT.md) retain native commands,
  dominated points and the saved original source hashes.

The public verifier binds all accepted public calls/exports to frozen native
bytes, checks all 31 legacy layouts and the isolated package, and authenticates
current sources separately. It does not relabel old native runs as new ones.

```powershell
python -m unittest discover -s libraries/tests -v
python -m pip wheel --no-deps --no-build-isolation --wheel-dir .tmp/hybrid-wheels libraries/lzsa
python libraries/tests/verify_hybrid_public.py --wheel .tmp/hybrid-wheels/zxvideo_lzsa-0.1.0-py3-none-any.whl --output libraries/evidence/hybrid_public_verification.json
python libraries/tests/document_decoder_variants.py
```

The verifier consumes worktree-local `.tmp/hybrid-library-tests.log` (61 tests),
`.tmp/hybrid-toolkit-tests.log` (24 selected integration tests) and
`.tmp/hybrid-wheel.log`. The selected toolkit modules are `test_row_lzsa`,
`test_bank_local_zx0`, `test_banked_zx0`, `test_streaming_lzsa2`,
`test_streaming_zx0_input`, `test_token_boundary_zx0`, `test_inplace_zx0_native`
and `test_zx0_speed`. The earlier 67-test run remains its historical evidence;
it is not relabeled as this selection.
