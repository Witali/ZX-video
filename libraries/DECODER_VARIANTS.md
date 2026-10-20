# Decoder variants, function links and baseline comparisons

Updated 2026-10-20. These are selectable decoder implementations of
forward ZX0 v2 and raw LZSA2; switching implementations does not require
recompressing a valid compatible block. The table covers the named measured
selection points, including the smallest retained valid decoders.

## Reading the measurements

- **CPU T** is the complete real-corpus deterministic instruction count.
- **Delta vs pass** compares with Fast at `f5a0362c`; LZSA2 includes `fast_jumps=True`.
- **Delta vs original** compares with the project's pre-policy adapted Fast:
  all optional tuning flags off, with the same ABI and input data.
- Both deltas are `100 * (candidate_T / reference_T - 1)`: **negative is faster**.
  They measure CPU-time change, not the reciprocal throughput percentage.
- **Service B** includes code, state, tables, alignment and required caller/private
  stack. Embedded state counts once. Compressed input and output/history are separate.
  Ordinary/resident totals exclude the application's IRQ code and extra stack.
- ZX0 uses 364 real blocks; LZSA2 uses 21. Compare variants within one codec/mode;
  these different corpora do not establish which format wins on a common workload.
- IRQ execution, ULA contention, physical disk/ROM latency and player publication
  deadlines are outside these CPU totals. Directed/slice regressions remain in
  [FRONTIER.md](FRONTIER.md) and the linked complete native evidence.

Original means the retained pre-policy project implementation; no timing claim
for an unmodified upstream executable is implied. ZX0 Standard and LZSA2 Small
are additional size-oriented choices, not substituted for the Fast baselines.

| Codec / mode | Original Fast CPU T | Pass baseline CPU T |
| --- | ---: | ---: |
| zx0 / block | 156,012,520 | 156,012,520 |
| zx0 / coroutine | 180,610,040 | 180,610,040 |
| lzsa2 / block | 17,767,606 | 17,765,094 |
| lzsa2 / coroutine | 19,412,006 | 19,407,004 |
| lzsa2 / guarded-call | 23,966,776 | 23,961,774 |
| lzsa2 / guarded-direct | 21,761,090 | 21,756,088 |

## Shared placement arguments

Import the module named in a linked call. The source link targets its actual
`build` function; the visible call includes all variant-selection arguments.
Use these common placements to reproduce the table instead of relying on a
coroutine's smaller legacy core reservation. Addresses are examples requiring
a disjoint application layout. Changing placement can change alignment cost.

```python
SMALL = dict(core=0x8000, core_limit=0x8400)
WIDE = dict(core=0x8000, core_limit=0xb000)
GUARDED = dict(core=0xa000, core_limit=0xbc00,
               prefix=0x7000, prefix_limit=0x7400,
               stack=0x7be0, output_base=0xc000)
```

## Resident complete-block decoders

| Variant | Service B | CPU T | Delta vs pass | Delta vs original | Builder call / source |
| --- | ---: | ---: | ---: | ---: | --- |
| ZX0 Standard (minimum) | 74 | 201,490,104 | +29.1500% | +29.1500% | [zx0.block.build(**SMALL, variant='standard')](zx0/src/zx0/block.py#L7) |
| ZX0 Turbo | 130 | 160,653,056 | +2.9745% | +2.9745% | [zx0.block.build(**SMALL, variant='turbo')](zx0/src/zx0/block.py#L7) |
| ZX0 Fast (original and pass baseline) | 211 | 156,012,520 | 0.0000% | 0.0000% | [zx0.block.build(**SMALL, variant='fast')](zx0/src/zx0/block.py#L7) |
| ZX0 Mega (original) | 677 | 146,422,274 | -6.1471% | -6.1471% | [zx0.block.build(**SMALL, variant='mega')](zx0/src/zx0/block.py#L7) |
| ZX0 Fast tuned | 197 | 153,706,279 | -1.4782% | -1.4782% | [zx0.block.build(**SMALL, branch_tuned=True)](zx0/src/zx0/block.py#L7) |
| ZX0 Fast tuned +prefix +tail | 202 | 152,776,831 | -2.0740% | -2.0740% | [zx0.block.build(**SMALL, branch_tuned=True, literal_prefix=True, inline_tail_refill=True)](zx0/src/zx0/block.py#L7) |
| ZX0 Mega tuned | 674 | 145,701,295 | -6.6092% | -6.6092% | [zx0.block.build(**SMALL, variant='mega', mega_tuned=True, fast_jumps=True)](zx0/src/zx0/block.py#L7) |
| ZX0 Maximum 31 | 4,454 | 141,618,798 | -9.2260% | -9.2260% | [zx0.maximum.build(prefix_cap=31)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum 63 | 5,990 | 140,680,558 | -9.8274% | -9.8274% | [zx0.maximum.build(prefix_cap=63)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum 127 | 7,526 | 140,193,198 | -10.1398% | -10.1398% | [zx0.maximum.build(prefix_cap=127)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum 227 | 9,966 | 140,170,198 | -10.1545% | -10.1545% | [zx0.maximum.build(prefix_cap=227)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum 228 | 9,990 | 140,169,968 | -10.1547% | -10.1547% | [zx0.maximum.build(prefix_cap=228)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum shared 31 | 2,810 | 141,342,108 | -9.4034% | -9.4034% | [zx0.maximum.build(prefix_cap=31, shared_prefixes=True)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum shared 63 | 3,578 | 140,403,868 | -10.0047% | -10.0047% | [zx0.maximum.build(prefix_cap=63, shared_prefixes=True)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum shared 127 | 5,114 | 139,916,508 | -10.3171% | -10.3171% | [zx0.maximum.build(prefix_cap=127, shared_prefixes=True)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum shared 227 | 7,554 | 139,893,048 | -10.3322% | -10.3322% | [zx0.maximum.build(prefix_cap=227, shared_prefixes=True)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum shared 228 | 7,578 | 139,892,818 | -10.3323% | -10.3323% | [zx0.maximum.build(prefix_cap=228, shared_prefixes=True)](zx0/src/zx0/maximum.py#L20) |
| LZSA2 Fast (original) | 222 | 17,767,606 | +0.0141% | 0.0000% | [lzsa.block.build(**SMALL, fast_jumps=False)](lzsa/src/lzsa/block.py#L5) |
| LZSA2 Fast (pass baseline) | 223 | 17,765,094 | 0.0000% | -0.0141% | [lzsa.block.build(**SMALL, fast_jumps=True)](lzsa/src/lzsa/block.py#L5) |
| LZSA2 Small (minimum) | 145 | 20,423,546 | +14.9645% | +14.9482% | [lzsa.block.build(**SMALL, variant='small')](lzsa/src/lzsa/block.py#L5) |
| LZSA2 Fast compact branches | 222 | 17,724,654 | -0.2276% | -0.2417% | [lzsa.block.build(**SMALL, fast_jumps=True, compact_branches=True)](lzsa/src/lzsa/block.py#L5) |
| LZSA2 Fast tuned +prefill | 228 | 17,635,500 | -0.7295% | -0.7435% | [lzsa.block.build(**SMALL, fast_jumps=True, branch_tuned=True, nibble_prefill=True)](lzsa/src/lzsa/block.py#L5) |
| LZSA2 Wide shared | 3,452 | 15,869,483 | -10.6704% | -10.6831% | [lzsa.block.build(**WIDE, variant='wide-shared')](lzsa/src/lzsa/block.py#L5) |
| LZSA2 Wide expanded | 7,004 | 15,623,953 | -12.0525% | -12.0650% | [lzsa.block.build(**WIDE, variant='wide')](lzsa/src/lzsa/block.py#L5) |
| LZSA2 Hybrid compact-base | 3,452 | 15,822,353 | -10.9357% | -10.9483% | [lzsa.hybrid.build(**WIDE, profile='compact-base')](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid balanced-base | 4,499 | 15,683,583 | -11.7169% | -11.7293% | [lzsa.hybrid.build(**WIDE, profile='balanced-base')](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid fast-base | 5,500 | 15,643,493 | -11.9425% | -11.9550% | [lzsa.hybrid.build(**WIDE, profile='fast-base')](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid compact | 4,999 | 15,048,469 | -15.2919% | -15.3039% | [lzsa.hybrid.build(**WIDE, profile='compact')](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid balanced | 6,500 | 14,983,119 | -15.6598% | -15.6717% | [lzsa.hybrid.build(**WIDE, profile='balanced')](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid fast | 9,500 | 14,944,429 | -15.8776% | -15.8895% | [lzsa.hybrid.build(**WIDE, profile='fast')](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Wide shared +short | 4,138 | 15,221,490 | -14.3180% | -14.3301% | [lzsa.wide.build(**WIDE, shared_literals=True, short_lengths=[2, 3, 4, 5, 6, 7, 8], repeat_lengths=[])](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Wide shared +short +repeat | 4,228 | 15,188,829 | -14.5018% | -14.5139% | [lzsa.wide.build(**WIDE, shared_literals=True, short_lengths=[2, 3, 4, 5, 6, 7, 8], repeat_lengths=[4, 5, 6, 7, 8])](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Wide expanded +short 3..8 | 9,524 | 14,999,606 | -15.5670% | -15.5789% | [lzsa.wide.build(**WIDE, shared_literals=False, short_lengths=[3, 4, 5, 6, 7, 8], repeat_lengths=[])](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Wide expanded +short 2..8 | 9,748 | 14,975,960 | -15.7001% | -15.7120% | [lzsa.wide.build(**WIDE, shared_literals=False, short_lengths=[2, 3, 4, 5, 6, 7, 8], repeat_lengths=[])](lzsa/src/lzsa/wide.py#L16) |

## Ordinary output-demand coroutines

Measured with 256-byte output demands and unchanged publication cursors.

| Variant | Service B | CPU T | Delta vs pass | Delta vs original | Builder call / source |
| --- | ---: | ---: | ---: | ---: | --- |
| ZX0 Fast (original and pass baseline) | 417 | 180,610,040 | 0.0000% | 0.0000% | [zx0.resumable.build(**SMALL)](zx0/src/zx0/resumable.py#L21) |
| ZX0 tuned +tail | 407 | 178,298,032 | -1.2801% | -1.2801% | [zx0.resumable.build(**SMALL, branch_tuned=True, inline_tail_refill=True)](zx0/src/zx0/resumable.py#L21) |
| ZX0 tuned +prefix +tail | 437 | 178,029,731 | -1.4287% | -1.4287% | [zx0.resumable.build(**SMALL, branch_tuned=True, literal_prefix=True, inline_tail_refill=True)](zx0/src/zx0/resumable.py#L21) |
| ZX0 Maximum coroutine 31 | 4,901 | 167,431,057 | -7.2969% | -7.2969% | [zx0.maximum_coroutine.build(prefix_cap=31)](zx0/src/zx0/maximum_coroutine.py#L6) |
| ZX0 Maximum coroutine 63 | 6,437 | 166,492,817 | -7.8164% | -7.8164% | [zx0.maximum_coroutine.build(prefix_cap=63)](zx0/src/zx0/maximum_coroutine.py#L6) |
| ZX0 Maximum coroutine 127 | 7,973 | 166,005,457 | -8.0863% | -8.0863% | [zx0.maximum_coroutine.build(prefix_cap=127)](zx0/src/zx0/maximum_coroutine.py#L6) |
| LZSA2 Fast (original) | 402 | 19,412,006 | +0.0258% | 0.0000% | [lzsa.resumable.build(**SMALL, fast_jumps=False)](lzsa/src/lzsa/resumable.py#L15) |
| LZSA2 Fast (pass baseline) | 404 | 19,407,004 | 0.0000% | -0.0258% | [lzsa.resumable.build(**SMALL, fast_jumps=True)](lzsa/src/lzsa/resumable.py#L15) |
| LZSA2 Fast compact_branches +prefill +sync | 402 | 19,252,552 | -0.7959% | -0.8214% | [lzsa.resumable.build(**SMALL, fast_jumps=True, nibble_prefill=True, compact_sync=True, compact_branches=True)](lzsa/src/lzsa/resumable.py#L15) |
| LZSA2 Fast branch_tuned +prefill +sync | 404 | 19,242,382 | -0.8483% | -0.8738% | [lzsa.resumable.build(**SMALL, fast_jumps=True, nibble_prefill=True, compact_sync=True, branch_tuned=True)](lzsa/src/lzsa/resumable.py#L15) |
| LZSA2 Wide shared | 3,633 | 17,511,393 | -9.7677% | -9.7909% | [lzsa.wide_coroutine.build(**WIDE, shared_literals=True)](lzsa/src/lzsa/wide_coroutine.py#L16) |
| LZSA2 Wide expanded | 7,185 | 17,265,863 | -11.0328% | -11.0558% | [lzsa.wide_coroutine.build(**WIDE, shared_literals=False)](lzsa/src/lzsa/wide_coroutine.py#L16) |

## Guarded-input LZSA2

Service is **consumer / full aligned reference**. The consumer includes the
guard patcher. The full reference additionally includes the retained supplier,
256-byte carry, I/O code/state, 1,280-byte mock workspace, required stacks and
the tested IRQ. Carry is specific to that supplier, not every possible supplier.
CPU columns compare decoder work only, using the same original 63-case supplier
harness and its 21 real blocks; producer CPU and sector delivery are separate.

| Variant | Service B | CPU T | Delta vs pass | Delta vs original | Builder call / source |
| --- | ---: | ---: | ---: | ---: | --- |
| LZSA2 Wide expanded call | 7,344 / 9,881 | 21,822,661 | -8.9272% | -8.9462% | [lzsa.wide_coroutine.build(**GUARDED, streaming=True, direct_header=False, shared_literals=False)](lzsa/src/lzsa/wide_coroutine.py#L16) |
| LZSA2 Wide expanded direct | 7,336 / 9,870 | 19,616,975 | -9.8323% | -9.8530% | [lzsa.wide_coroutine.build(**GUARDED, streaming=True, direct_header=True, shared_literals=False)](lzsa/src/lzsa/wide_coroutine.py#L16) |
| LZSA2 Wide shared call | 3,792 / 6,329 | 22,068,191 | -7.9025% | -7.9217% | [lzsa.wide_coroutine.build(**GUARDED, streaming=True, direct_header=False, shared_literals=True)](lzsa/src/lzsa/wide_coroutine.py#L16) |
| LZSA2 Wide shared direct | 3,784 / 6,318 | 19,862,505 | -8.7037% | -8.7247% | [lzsa.wide_coroutine.build(**GUARDED, streaming=True, direct_header=True, shared_literals=True)](lzsa/src/lzsa/wide_coroutine.py#L16) |

## Selection and runtime contracts

- Smallest resident decoders: **ZX0 Standard 74 B** (68 code +6 stack),
  **LZSA2 Small 145 B** (137 code +8 stack). Both are slower than Fast.
- Fastest measured resident choices: **ZX0 Maximum shared 228, 7,578 B** and
  **LZSA2 Hybrid fast, 9,500 B**. Shared 127 uses 5,114 B and is faster
  than the original unshared 228. Shared suffixes support resident calls only.
- LZSA2 Hybrid compact uses 4,999 B and reduces CPU time by 3.683344%
  versus the old 7,004-B Expanded. Hybrid fast saves 4.349245%; retain
  its four directed +4-T regressions and the smaller profiles' full lists.
- Useful intermediate choices include Mega tuned 674 B and Wide shared 3,452 B.
- Maximum ZX0 coroutine requires Spectrum-style undocumented `CP IXH/IXL`.
  Caller IX is restored on every return; IRQ must preserve live IX and AF/AF'.
- Wide figures assume an aligned core. Arbitrary alignment adds up to 255 B.
  A full guarded reference can therefore exceed 10,000 B after relocation.
- Original unshared Maximum 228 has only 10 service bytes left. The 13-byte/six-stack-byte
  IRQ example makes 10,009 B; use 227 (9,985 B with that IRQ) or reserve the
  actual handler through `irq_code_bytes` / `irq_stack_bytes`. The verified
  minimal `EI; RETI` handler makes 228 total 9,995 B.

Resident calls use HL=input, DE=output and the caller stack. Ordinary coroutines
configure `input_pointer`, `block_end`, `slice_target` and call generated `begin`,
then `slice_until`. Guarded callers additionally publish input frontiers and
call the embedded `update_guards` only while suspended. Keep required source/
history readable and respect the linked function's writable-code/IRQ contract.
The Python `build` functions are generators returning `(regions, labels, metadata)`;
the generated labels are the Z80 runtime entry points.

```python
import zx0.block
from zx0.export import export

profile = zx0.block.build(**SMALL, branch_tuned=True,
                          literal_prefix=True, inline_tail_refill=True)
export("build/zx0", *profile)
```

For LZSA2 use `lzsa.export.export`. Existing CLI selectors remain documented in
[ZX0 README](zx0/README.md) and [LZSA2 README](lzsa/README.md); no new mode key
or runtime format switch is introduced by this table.

## Implementation files

The tables above link public selection functions. For the Z80 instruction
emitters behind a dispatcher, use these implementation functions:

| Decoder family | Implementation function / file |
| --- | --- |
| ZX0 Standard / Turbo / Mega | [zx0.codec.emit_decoder](zx0/src/zx0/codec.py#L66) |
| ZX0 Fast | [zx0.resumable.emit_fast](zx0/src/zx0/resumable.py#L138) |
| ZX0 Maximum resident | [zx0.maximum.build](zx0/src/zx0/maximum.py#L20) |
| ZX0 shared-prefix layout | [zx0._shared_prefixes.transform](zx0/src/zx0/_shared_prefixes.py#L26) |
| ZX0 Maximum coroutine | [zx0.maximum_coroutine.build](zx0/src/zx0/maximum_coroutine.py#L6) |
| LZSA2 Small | [lzsa.compact.build](lzsa/src/lzsa/compact.py#L13) |
| LZSA2 Fast and its coroutine | [lzsa.resumable.build](lzsa/src/lzsa/resumable.py#L15) |
| LZSA2 Wide resident | [lzsa.wide.build](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 fixed resident hybrids | [lzsa.hybrid.build](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 known new-offset short copy | [lzsa._wide_kernels.emit_new_offset_short](lzsa/src/lzsa/_wide_kernels.py#L9) |
| LZSA2 known repeat-offset short copy | [lzsa._wide_kernels.emit_repeat_short](lzsa/src/lzsa/_wide_kernels.py#L25) |
| LZSA2 Wide ordinary / guarded coroutine | [lzsa.wide_coroutine.build](lzsa/src/lzsa/wide_coroutine.py#L16) |

## Evidence and reproduction

[Shared Maximum native proof](evidence/shared_zero_prefix_native.json.gz),
[shared-prefix contracts](ZX0_SHARED_PREFIXES.md),
[Hybrid API/wheel/native binding](evidence/hybrid_public_verification.json),
[hybrid contracts and directed regressions](LZSA_HYBRID.md),
[previous full native integration](evidence/frontier_completed_profiles_verification.json),
[original ZX0 counts](evidence/trick_23.json), [original LZSA2 and jump pass](evidence/fast_jumps.json),
[Small counts](evidence/trick_29.json), [guarded native replay](evidence/wide_guarded_native.json.gz),
[authenticated original guarded recordings](evidence/fast_jumps_verification.json).

[Table/API/export validation](evidence/decoder_variants_verification.json) records
exact calls, source-function lines, memory arithmetic, both timing references
and source/evidence hashes. It reuses complete saved native timings and verifies
the current public calls and ORG/DB exports; it is not a new benchmark or release.
Rebuild the table and its validation with:

```powershell
python libraries/tests/document_decoder_variants.py
```
