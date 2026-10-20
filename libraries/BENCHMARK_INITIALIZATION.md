# Benchmark initialization accounting

Accounting audit of the 74 linked selections, 2026-10-20. No target code or saved native measurements are changed; no CPU replay is run.

The primary guarded service metric is **producer + decoder**, including producer initialization, descriptor/frontier publication, carry handling and guard patching. The preceding decoder-only counts remain historical components. All resident and ordinary-coroutine entry initialization was already included.

## Counter boundaries

- **58 resident selections:** start at the metadata entry and stop after exact EOF/restoration/RET. Offset/cache setup is inside this interval. [libraries/tests/native_block.py:68](../libraries/tests/native_block.py#L68).
- **12 ordinary coroutines:** the first timed invocation selects `begin`; every later invocation selects `slice_until`. The first cost is retained in the sum, including sync, private-stack setup, raw initialization, yields and final return. [libraries/lzsa/src/lzsa/native.py:61](../libraries/lzsa/src/lzsa/native.py#L61), [libraries/lzsa/src/lzsa/native.py:89](../libraries/lzsa/src/lzsa/native.py#L89), [libraries/tests/measure_compact_sync.py:48](../libraries/tests/measure_compact_sync.py#L48), [libraries/tests/maximum_coroutine_native.py:58](../libraries/tests/maximum_coroutine_native.py#L58).
- **4 guarded selections:** producer `begin` is timed first; decoder timing starts before its `begin`, and supplier steps are separately timed. The full sum includes both. [toolkit/benchmark_inplace_streaming.py:61](../toolkit/benchmark_inplace_streaming.py#L61), [toolkit/benchmark_inplace_streaming.py:84](../toolkit/benchmark_inplace_streaming.py#L84), [toolkit/benchmark_inplace_streaming.py:110](../toolkit/benchmark_inplace_streaming.py#L110).

All external caller CALL instructions (17 T each) and argument publication are outside the entry-through-RET convention. Raw HL/DE and coroutine input_pointer/block_end/slice_target are ready at entry. Host writes of these API inputs are not timed guest instructions: [libraries/lzsa/src/lzsa/native.py:24](../libraries/lzsa/src/lzsa/native.py#L24), [libraries/lzsa/src/lzsa/native.py:59](../libraries/lzsa/src/lzsa/native.py#L59), [toolkit/benchmark_inplace_streaming.py:82](../toolkit/benchmark_inplace_streaming.py#L82). Their application-specific loads/stores must be added when benchmarking a concrete caller. This is not full application CPU or a cold-boot benchmark.

There is no external callable table/cache/offset initializer for these resident/ordinary APIs. Tables and initial data are emitted in the binary; dynamic cache/default-offset setup runs at entry. The actual guarded producer publishes descriptors and frontiers in guest code: [toolkit/inplace_slot_input_z80.py:53](../toolkit/inplace_slot_input_z80.py#L53), [toolkit/inplace_slot_input_z80.py:60](../toolkit/inplace_slot_input_z80.py#L60), [toolkit/inplace_streaming_core.py:44](../toolkit/inplace_streaming_core.py#L44). Code/image loading, disk/ROM latency, ULA and application IRQ scheduling remain separate.

## Included initialization ledgers

Static Z80 instruction counts below identify setup already inside the measured paths, before the first parser work. They are not additional costs to add again.

| Raw family | Included entry setup T |
| --- | ---: |
| ZX0 Standard / gamma-JP | 34 |
| ZX0 Small SMC | 43 |
| ZX0 Turbo | 55 |
| ZX0 Fast | 53 |
| ZX0 original Mega | 48 |
| ZX0 Maximum / tuned Mega with JP | 46 |
| LZSA2 Fast | 25 |
| LZSA2 Small / compact EOF | 24 |
| LZSA2 Wide / Hybrid / Hot | 44 |

Ordinary ZX0 Fast `begin` through raw setup is 269 T, or 295 T with the extra literal-prefix sync stores. Maximum index-quota initialization is 304 T (309 T when the initial demand equals block end). Ordinary LZSA2 Fast is 256/261 T, compact-sync 248/253 T, and Wide 275/280 T. Guarded Fast is 286/291 T; guarded Wide 305/310 T. These pairs differ only by the final-demand sync branch. Full instruction components and source hashes are in the JSON.

The producer initializer is 70 T per block: 4410 T across 63 retained cases and 1470 T across 21 real cases. Both amounts are already inside producer totals. The decoder’s own `begin` is a different initializer and is inside decoder totals.

## Guarded totals from saved guest execution

The four profiles and Fast references use the identical 63-block supplier stream (21 real blocks), recorded input/output hashes and 772 sector reads. The supplied totals include all guest library initialization and guard work within this API convention, without adding them twice.

| Profile | Real decoder T | Real producer T | Real full service T | All 63 full service T |
| --- | ---: | ---: | ---: | ---: |
| wide-call | 21,822,661 | 1,283,578 | 23,106,239 | 27,474,785 |
| wide-direct | 19,616,975 | 1,275,713 | 20,892,688 | 25,258,314 |
| wide-shared-call | 22,068,191 | 1,283,578 | 23,351,769 | 27,720,735 |
| wide-shared-direct | 19,862,505 | 1,275,713 | 21,138,218 | 25,504,264 |

| Fast reference | Real full service T | All 63 full service T |
| --- | ---: | ---: |
| call original | 25,250,354 | 29,619,154 |
| call pass | 25,245,352 | 29,614,150 |
| direct original | 23,036,803 | 27,402,683 |
| direct pass | 23,031,801 | 27,397,679 |

### Guard setup and repeated updates

The retained producer uses the inline patcher. Partial/complete calls cost 187/224 T in CALL mode and 174/211 T in direct mode; the callable consumer helper adds its RET 10 T, producing 197/234 and 184/221 T respectively. The caller CALL 17 T remains separate. [libraries/lzsa/src/lzsa/streaming.py:4](../libraries/lzsa/src/lzsa/streaming.py#L4), [toolkit/inplace_streaming_core.py:51](../toolkit/inplace_streaming_core.py#L51).

All 63 blocks execute 795 inline updates: 732 partial and 63 complete. The first update of each block is required initialization; 30 initial updates are partial and 33 complete. The remaining 732 updates follow input waits. The 21 real blocks execute 605 updates: 584 partial and 21 complete, with 21 initial partial setups. These counts are reconciled with the saved producer instruction histogram and input-wait lists.

| Mode / scope | Initial guard setup T | Repeated updates T | Total guard work already in producer T |
| --- | ---: | ---: | ---: |
| call / real | 3,927 | 109,985 | 113,912 |
| call / all | 13,002 | 137,994 | 150,996 |
| direct / real | 3,654 | 102,393 | 106,047 |
| direct / all | 12,183 | 128,478 | 140,661 |

The separate flat-native guarded runner executes and times `update_guards` outside the decode-slice counter. Its returned `tstates` alone excludes this work; use `tstates + guard_update_tstates` for its consumer-plus-patcher cost. The JSON records both components and their sum at every saved placement. [libraries/tests/wide_guarded_support.py:91](../libraries/tests/wide_guarded_support.py#L91), [libraries/tests/wide_guarded_support.py:136](../libraries/tests/wide_guarded_support.py#L136). Do not add that standalone helper to the producer+decoder totals: the producer already executes its inline implementation.

## Reproduction and provenance

```powershell
python libraries/tests/audit_benchmark_initialization.py
```

[Machine-readable audit](evidence/benchmark_initialization.json) lists all 74 selection names/calls, the four guarded keys, exact source lines, instruction ledgers, native-proof/stream/input hashes, standalone helper costs and full source/evidence SHA256. It derives totals from complete retained proof; it runs no emulator or decoder. The mutable generated table is discovery metadata, not the timing oracle.
