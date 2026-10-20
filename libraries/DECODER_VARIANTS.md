# Decoder variants, function links and baseline comparisons

Updated 2026-10-20. These are selectable decoder implementations of
forward ZX0 v2 and raw LZSA2; switching implementations does not require
recompressing a valid compatible block. The table covers the named measured
selection points, including the smallest retained valid decoders.

## Reading the measurements

- **CPU T** measures complete entry-through-return work on the frozen real corpus.
  Guarded tables additionally show **total CPU** for producer+decoder, including
  initialization and guard updates; their historical decoder-only column is explicit.
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

All required Z80 initialization belongs in benchmark totals. F00 includes44 T
of setup per block and28 T of EOF restoration/RET; its external initializer is0 T.
The512-byte static dispatch table is emitted in the library image. Any future
separate one-time preparation must be shown in cold-start and batch totals.
The retained convention measures entry through RET; caller CALL17 is additional.
[Initialization audit](BENCHMARK_INITIALIZATION.md) authenticates all measured
entry/timer scopes and the guarded total CPU below; target setup is not free.

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

Guarded references above preserve historical decoder-only counts.
The complete initialization/supplier/decoder Fast references are:

| Guarded mode | Original Fast total CPU T | Pass Fast total CPU T |
| --- | ---: | ---: |
| call | 25,250,354 | 25,245,352 |
| direct | 23,036,803 | 23,031,801 |

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
| ZX0 Maximum branches 127 fast | 5,053 | 139,576,574 | -10.5350% | -10.5350% | [zx0.maximum_branches.build(prefix_cap=127, policy='fast')](zx0/src/zx0/maximum_branches.py#L179) |
| ZX0 Maximum branches 127 real | 5,101 | 139,701,644 | -10.4549% | -10.4549% | [zx0.maximum_branches.build(prefix_cap=127, policy='real')](zx0/src/zx0/maximum_branches.py#L179) |
| ZX0 Maximum branches 127 corpus | 5,111 | 139,915,538 | -10.3178% | -10.3178% | [zx0.maximum_branches.build(prefix_cap=127, policy='corpus')](zx0/src/zx0/maximum_branches.py#L179) |
| ZX0 Maximum branches 228 fast | 7,517 | 139,552,884 | -10.5502% | -10.5502% | [zx0.maximum_branches.build(prefix_cap=228, policy='fast')](zx0/src/zx0/maximum_branches.py#L179) |
| ZX0 Maximum branches 228 real | 7,565 | 139,677,954 | -10.4700% | -10.4700% | [zx0.maximum_branches.build(prefix_cap=228, policy='real')](zx0/src/zx0/maximum_branches.py#L179) |
| ZX0 Maximum branches 228 corpus | 7,575 | 139,891,848 | -10.3329% | -10.3329% | [zx0.maximum_branches.build(prefix_cap=228, policy='corpus')](zx0/src/zx0/maximum_branches.py#L179) |
| LZSA2 Hybrid compact +cold extension | 4,998 | 15,030,346 | -15.3939% | -15.4059% | [lzsa.hybrid.build(**WIDE, profile='compact', cold_match_extension=True)](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid balanced +cold extension | 6,499 | 14,964,996 | -15.7618% | -15.7737% | [lzsa.hybrid.build(**WIDE, profile='balanced', cold_match_extension=True)](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid fast +cold extension | 9,499 | 14,926,306 | -15.9796% | -15.9915% | [lzsa.hybrid.build(**WIDE, profile='fast', cold_match_extension=True)](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid compact-base +cold extension | 3,451 | 15,804,230 | -11.0377% | -11.0503% | [lzsa.hybrid.build(**WIDE, profile='compact-base', cold_match_extension=True)](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid balanced-base +cold extension | 4,498 | 15,665,460 | -11.8189% | -11.8313% | [lzsa.hybrid.build(**WIDE, profile='balanced-base', cold_match_extension=True)](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid fast-base +cold extension | 5,499 | 15,625,370 | -12.0445% | -12.0570% | [lzsa.hybrid.build(**WIDE, profile='fast-base', cold_match_extension=True)](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Wide expanded +cold extension | 7,003 | 15,605,830 | -12.1545% | -12.1670% | [lzsa.wide.build(**WIDE, cold_match_extension=True)](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Wide shared +cold extension | 3,451 | 15,851,360 | -10.7724% | -10.7851% | [lzsa.wide.build(**WIDE, shared_literals=True, cold_match_extension=True)](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Wide shared +short +cold extension | 4,137 | 15,203,367 | -14.4200% | -14.4321% | [lzsa.wide.build(**WIDE, shared_literals=True, short_lengths=[2, 3, 4, 5, 6, 7, 8], cold_match_extension=True)](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Wide shared +short +repeat +cold extension | 4,227 | 15,170,706 | -14.6039% | -14.6159% | [lzsa.wide.build(**WIDE, shared_literals=True, short_lengths=[2, 3, 4, 5, 6, 7, 8], repeat_lengths=[4, 5, 6, 7, 8], cold_match_extension=True)](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Wide expanded +short 3..8 +cold extension | 9,523 | 14,981,483 | -15.6690% | -15.6809% | [lzsa.wide.build(**WIDE, short_lengths=[3, 4, 5, 6, 7, 8], cold_match_extension=True)](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Wide expanded +short 2..8 +cold extension | 9,747 | 14,957,837 | -15.8021% | -15.8140% | [lzsa.wide.build(**WIDE, short_lengths=[2, 3, 4, 5, 6, 7, 8], cold_match_extension=True)](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Hot literals | 9,529 | 14,913,435 | -16.0520% | -16.0639% | [lzsa.hot.build(**WIDE, profile='literals')](lzsa/src/lzsa/hot.py#L214) |
| LZSA2 Hot nibble | 9,515 | 14,918,596 | -16.0230% | -16.0349% | [lzsa.hot.build(**WIDE, profile='nibble')](lzsa/src/lzsa/hot.py#L214) |
| LZSA2 Hot combined | 9,545 | 14,905,725 | -16.0954% | -16.1073% | [lzsa.hot.build(**WIDE, profile='combined')](lzsa/src/lzsa/hot.py#L214) |

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
The total CPU column sums producer+decoder on the same original 63-case supplier
harness and its 21 real blocks. It includes producer begin, decoder begin/sync/EOF
and inline guard patching. Decoder-only deltas remain as historical comparisons.
Caller parameter passing, IRQ, physical sector/ROM time and movie deadlines are separate.

| Variant | Service B | Total CPU T | Decoder-only T | Decoder delta vs pass / original | Builder call / source |
| --- | ---: | ---: | ---: | ---: | --- |
| LZSA2 Wide expanded call | 7,344 / 9,881 | 23,106,239 | 21,822,661 | -8.9272% / -8.9462% | [lzsa.wide_coroutine.build(**GUARDED, streaming=True, direct_header=False, shared_literals=False)](lzsa/src/lzsa/wide_coroutine.py#L16) |
| LZSA2 Wide expanded direct | 7,336 / 9,870 | 20,892,688 | 19,616,975 | -9.8323% / -9.8530% | [lzsa.wide_coroutine.build(**GUARDED, streaming=True, direct_header=True, shared_literals=False)](lzsa/src/lzsa/wide_coroutine.py#L16) |
| LZSA2 Wide shared call | 3,792 / 6,329 | 23,351,769 | 22,068,191 | -7.9025% / -7.9217% | [lzsa.wide_coroutine.build(**GUARDED, streaming=True, direct_header=False, shared_literals=True)](lzsa/src/lzsa/wide_coroutine.py#L16) |
| LZSA2 Wide shared direct | 3,784 / 6,318 | 21,138,218 | 19,862,505 | -8.7037% / -8.7247% | [lzsa.wide_coroutine.build(**GUARDED, streaming=True, direct_header=True, shared_literals=True)](lzsa/src/lzsa/wide_coroutine.py#L16) |

## Guarded total benchmark comparisons

These totals include every measured initialization/guard operation through the
real supplier and the decoder. Do not add their begin costs again. All variants
use the same saved input stream and supplier mode; physical I/O latency is separate.

| Variant | Setup/supplier CPU T | Decoder CPU T | Total T | Total delta vs pass / original |
| --- | ---: | ---: | ---: | ---: |
| LZSA2 Wide expanded call | 1,283,578 | 21,822,661 | 23,106,239 | -8.4733% / -8.4914% |
| LZSA2 Wide expanded direct | 1,275,713 | 19,616,975 | 20,892,688 | -9.2876% / -9.3073% |
| LZSA2 Wide shared call | 1,283,578 | 22,068,191 | 23,351,769 | -7.5007% / -7.5190% |
| LZSA2 Wide shared direct | 1,275,713 | 19,862,505 | 21,138,218 | -8.2216% / -8.2415% |

## E01 increments against the accepted resident variants

These optional calls retain the same compressed data and resident ABI. The
reference is the corresponding accepted `9c28b01f` implementation, rather than
the older Fast references in the main tables. Service includes every emitted
byte and required stack; the embedded two-byte offset is already in code.
All six ZX0 and twelve LZSA2 candidates reduce both real CPU and service memory.
No real block slows. Non-real regressions are explicit below; complete case
names/deltas are retained in the linked native proofs and table validation JSON.

| Variant | Accepted service B -> E01 B | Accepted real CPU T -> E01 T | Delta T | Slower non-real / maximum T |
| --- | ---: | ---: | ---: | ---: |
| ZX0 Maximum branches 127 fast | 5,114 -> 5,053 | 139,916,508 -> 139,576,574 | -339,934 | [103 / +38](evidence/next_e01_zx0_branches.json.gz) |
| ZX0 Maximum branches 127 real | 5,114 -> 5,101 | 139,916,508 -> 139,701,644 | -214,864 | [38 / +11](evidence/next_e01_zx0_branches.json.gz) |
| ZX0 Maximum branches 127 corpus | 5,114 -> 5,111 | 139,916,508 -> 139,915,538 | -970 | [0 / 0](evidence/next_e01_zx0_branches.json.gz) |
| ZX0 Maximum branches 228 fast | 7,578 -> 7,517 | 139,892,818 -> 139,552,884 | -339,934 | [103 / +38](evidence/next_e01_zx0_branches.json.gz) |
| ZX0 Maximum branches 228 real | 7,578 -> 7,565 | 139,892,818 -> 139,677,954 | -214,864 | [38 / +11](evidence/next_e01_zx0_branches.json.gz) |
| ZX0 Maximum branches 228 corpus | 7,578 -> 7,575 | 139,892,818 -> 139,891,848 | -970 | [0 / 0](evidence/next_e01_zx0_branches.json.gz) |
| LZSA2 Hybrid compact +cold extension | 4,999 -> 4,998 | 15,048,469 -> 15,030,346 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Hybrid balanced +cold extension | 6,500 -> 6,499 | 14,983,119 -> 14,964,996 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Hybrid fast +cold extension | 9,500 -> 9,499 | 14,944,429 -> 14,926,306 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Hybrid compact-base +cold extension | 3,452 -> 3,451 | 15,822,353 -> 15,804,230 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Hybrid balanced-base +cold extension | 4,499 -> 4,498 | 15,683,583 -> 15,665,460 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Hybrid fast-base +cold extension | 5,500 -> 5,499 | 15,643,493 -> 15,625,370 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Wide expanded +cold extension | 7,004 -> 7,003 | 15,623,953 -> 15,605,830 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Wide shared +cold extension | 3,452 -> 3,451 | 15,869,483 -> 15,851,360 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Wide shared +short +cold extension | 4,138 -> 4,137 | 15,221,490 -> 15,203,367 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Wide shared +short +repeat +cold extension | 4,228 -> 4,227 | 15,188,829 -> 15,170,706 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Wide expanded +short 3..8 +cold extension | 9,524 -> 9,523 | 14,999,606 -> 14,981,483 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |
| LZSA2 Wide expanded +short 2..8 +cold extension | 9,748 -> 9,747 | 14,975,960 -> 14,957,837 | -18,123 | [586 / +37](evidence/next_e01_lzsa_full.json.gz) |

ZX0 `fast` contracts 61 branches, `real` 13, and `corpus` 3. Their slower
complete-case counts are 103/38/0 for either cap: 47/19/0 main non-real cases
and 56/19/0 high-word cases, with maxima +38/+11/0 T. The `corpus` result
means zero regressions on the tested 473 cases; these policy names do not
promise the same result for arbitrary streams. Each contracted JP costs
10 T before; JR costs 7 T untaken and 12 T taken.

LZSA2 `cold_match_extension=True` removes one service byte and saves 18,123 T
over the same 21 real blocks for every listed layout. Each has 89 faster and
586 slower cases among 675, with all 586 slower cases non-real. The maximum
is +37 T on `random-19`; a tiny single-nibble EOF adds 2 T. These 586 cases
include corpus and directed inputs. They are additional comparisons with
each corresponding classic layout, separate from the retained Hybrid
regression lists against older Expanded. Cold extension supports raw resident
calls only. It does not qualify coroutine or guarded-input wrappers.

The new modes were checked with IRQ, relocation and actual minimum-safe
compressed-input overlap in their complete saved native experiments. This
document rebuild authenticates current bytes, labels, memory and exports
against those proofs; it does not rerun those native measurements.

## F00 faster/larger resident choices

All three are optional self-contained fixed profiles of the same raw decoder.
Each passes675 frozen and60 supplemental cases at six native configurations,
plus nine FFFFh probes. Entry setup is included. Compared with E01 fast:

| Variant | Service B / delta | Real CPU T / delta | Supplemental regressions |
| --- | ---: | ---: | --- |
| LZSA2 Hot literals | 9,529 / +30 | 14,913,435 / -12,871 | 4 at +10 T |
| LZSA2 Hot nibble | 9,515 / +16 | 14,918,596 / -7,710 | 0 |
| LZSA2 Hot combined | 9,545 / +46 | 14,905,725 / -20,581 | 4 at +10 T |

No frozen case slows. The four valid short-word-literal regressions for
`literals` and `combined` are `clone-word-1-cached`, `clone-word-2-cached`,
`clone-word-1-refill`, `clone-word-2-refill`. Their exact input/CPU and all six
configurations are retained. Arbitrary alignment adds up to255 B; with the
13+6-byte IRQ example the largest profile is9,819 B. Raw qualification does
not qualify quota/guarded wrappers. [F00 report](NEXT_F00_HOT_PATHS.md).

## Nondominated resident size/speed choices

These are the best tested points on the complete real-corpus aggregate at
the aligned placements above, with the same resident format/ABI. A point
is omitted here only when another is no larger and no slower, with one
strict advantage. All named measured choices remain in the full table.
Per-case regressions still matter; this finite set establishes no global optimum.

| Codec / variant | Service B | Real CPU T | Function / file |
| --- | ---: | ---: | --- |
| ZX0 Standard (minimum) | 74 | 201,490,104 | [zx0.block.build(**SMALL, variant='standard')](zx0/src/zx0/block.py#L7) |
| ZX0 Turbo | 130 | 160,653,056 | [zx0.block.build(**SMALL, variant='turbo')](zx0/src/zx0/block.py#L7) |
| ZX0 Fast tuned | 197 | 153,706,279 | [zx0.block.build(**SMALL, branch_tuned=True)](zx0/src/zx0/block.py#L7) |
| ZX0 Fast tuned +prefix +tail | 202 | 152,776,831 | [zx0.block.build(**SMALL, branch_tuned=True, literal_prefix=True, inline_tail_refill=True)](zx0/src/zx0/block.py#L7) |
| ZX0 Mega tuned | 674 | 145,701,295 | [zx0.block.build(**SMALL, variant='mega', mega_tuned=True, fast_jumps=True)](zx0/src/zx0/block.py#L7) |
| ZX0 Maximum shared 31 | 2,810 | 141,342,108 | [zx0.maximum.build(prefix_cap=31, shared_prefixes=True)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum shared 63 | 3,578 | 140,403,868 | [zx0.maximum.build(prefix_cap=63, shared_prefixes=True)](zx0/src/zx0/maximum.py#L20) |
| ZX0 Maximum branches 127 fast | 5,053 | 139,576,574 | [zx0.maximum_branches.build(prefix_cap=127, policy='fast')](zx0/src/zx0/maximum_branches.py#L179) |
| ZX0 Maximum branches 228 fast | 7,517 | 139,552,884 | [zx0.maximum_branches.build(prefix_cap=228, policy='fast')](zx0/src/zx0/maximum_branches.py#L179) |
| LZSA2 Small (minimum) | 145 | 20,423,546 | [lzsa.block.build(**SMALL, variant='small')](lzsa/src/lzsa/block.py#L5) |
| LZSA2 Fast compact branches | 222 | 17,724,654 | [lzsa.block.build(**SMALL, fast_jumps=True, compact_branches=True)](lzsa/src/lzsa/block.py#L5) |
| LZSA2 Fast tuned +prefill | 228 | 17,635,500 | [lzsa.block.build(**SMALL, fast_jumps=True, branch_tuned=True, nibble_prefill=True)](lzsa/src/lzsa/block.py#L5) |
| LZSA2 Hybrid compact-base +cold extension | 3,451 | 15,804,230 | [lzsa.hybrid.build(**WIDE, profile='compact-base', cold_match_extension=True)](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Wide shared +short +cold extension | 4,137 | 15,203,367 | [lzsa.wide.build(**WIDE, shared_literals=True, short_lengths=[2, 3, 4, 5, 6, 7, 8], cold_match_extension=True)](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Wide shared +short +repeat +cold extension | 4,227 | 15,170,706 | [lzsa.wide.build(**WIDE, shared_literals=True, short_lengths=[2, 3, 4, 5, 6, 7, 8], repeat_lengths=[4, 5, 6, 7, 8], cold_match_extension=True)](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 Hybrid compact +cold extension | 4,998 | 15,030,346 | [lzsa.hybrid.build(**WIDE, profile='compact', cold_match_extension=True)](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid balanced +cold extension | 6,499 | 14,964,996 | [lzsa.hybrid.build(**WIDE, profile='balanced', cold_match_extension=True)](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hybrid fast +cold extension | 9,499 | 14,926,306 | [lzsa.hybrid.build(**WIDE, profile='fast', cold_match_extension=True)](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 Hot nibble | 9,515 | 14,918,596 | [lzsa.hot.build(**WIDE, profile='nibble')](lzsa/src/lzsa/hot.py#L214) |
| LZSA2 Hot literals | 9,529 | 14,913,435 | [lzsa.hot.build(**WIDE, profile='literals')](lzsa/src/lzsa/hot.py#L214) |
| LZSA2 Hot combined | 9,545 | 14,905,725 | [lzsa.hot.build(**WIDE, profile='combined')](lzsa/src/lzsa/hot.py#L214) |

## Selection and runtime contracts

- Smallest resident decoders: **ZX0 Standard 74 B** (68 code +6 stack),
  **LZSA2 Small 145 B** (137 code +8 stack). Both are slower than Fast.
- Fastest measured resident choices: **ZX0 Maximum branches 228 fast, 7,517 B**
  (139,552,884 T) and **LZSA2 Hot combined,
  9,545 B** (14,905,725 T).
  ZX0 branches127/fast uses 5,053 B and beats the preceding shared228.
  Shared suffixes and the E01 policies support resident calls only.
- The preceding Hybrid compact/fast rows remain selectable: 4,999/9,500 B,
  3.683344%/4.349245% less CPU than old 7,004-B Expanded. Their saved
  regression lists remain valid; E01 cold extension has its own lists above.
- Useful intermediate choices include Mega tuned 674 B and E01 Hybrid compact 4,998 B.
- Maximum ZX0 coroutine requires Spectrum-style undocumented `CP IXH/IXL`.
  Caller IX is restored on every return; IRQ must preserve live IX and AF/AF'.
- Wide figures assume an aligned core. Arbitrary alignment adds up to 255 B.
  Cold Expanded +short2..8 reaches 10,000 B at core low-byte3 before IRQ;
  low-bytes1/2 are rejected. The 13+6-B IRQ example would make 10,019 B there.
  A full guarded reference can exceed 10,000 B after relocation.
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
| ZX0 fixed E01 branch layouts | [zx0.maximum_branches.build](zx0/src/zx0/maximum_branches.py#L179) |
| ZX0 shared-prefix layout | [zx0._shared_prefixes.transform](zx0/src/zx0/_shared_prefixes.py#L26) |
| ZX0 Maximum coroutine | [zx0.maximum_coroutine.build](zx0/src/zx0/maximum_coroutine.py#L6) |
| LZSA2 Small | [lzsa.compact.build](lzsa/src/lzsa/compact.py#L13) |
| LZSA2 Fast and its coroutine | [lzsa.resumable.build](lzsa/src/lzsa/resumable.py#L15) |
| LZSA2 Wide resident | [lzsa.wide.build](lzsa/src/lzsa/wide.py#L16) |
| LZSA2 fixed resident hybrids | [lzsa.hybrid.build](lzsa/src/lzsa/hybrid.py#L129) |
| LZSA2 fixed hot literal/nibble profiles | [lzsa.hot.build](lzsa/src/lzsa/hot.py#L214) |
| LZSA2 known new-offset short copy | [lzsa._wide_kernels.emit_new_offset_short](lzsa/src/lzsa/_wide_kernels.py#L9) |
| LZSA2 known repeat-offset short copy | [lzsa._wide_kernels.emit_repeat_short](lzsa/src/lzsa/_wide_kernels.py#L25) |
| LZSA2 Wide ordinary / guarded coroutine | [lzsa.wide_coroutine.build](lzsa/src/lzsa/wide_coroutine.py#L16) |

## Evidence and reproduction

[E01 ZX0 native branches](evidence/next_e01_zx0_branches.json.gz),
[E01 ZX0 public binding](evidence/next_e01_zx0_public.json),
[E01 LZSA2 native cold extension](evidence/next_e01_lzsa_full.json.gz),
[E01 public API/wheel authentication](evidence/next_e01_public_verification.json),
[F00 full native proof](evidence/next_f00_full.json.gz),
[F00 public/wheel authentication](evidence/next_f00_public_verification.json),
[Initialization and guarded-total audit](evidence/benchmark_initialization.json),
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
