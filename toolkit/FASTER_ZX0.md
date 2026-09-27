# Faster ZX0 decoding with identical compressed data

Date: 2026-09-27. Repository input: `9f14ad9`; retained disk baseline:
`a84451d`. All **188 blocks / 2,965,011 decoded bytes** of the authorized
4221-frame edit, the same three independent volume streams and disk starts.

**Yes: the adapted Fast prototype reduces decoder CPU time by 3.403%,
without changing one compressed byte.** A smaller tuned-Turbo prototype
saves 1.214%. These are complete native CPU measurements, not a new Fuse
playback result or proof of smooth 25/3-fps publication.

## What changes

The project already uses ZX0 v2's Turbo decoder with resumable, token-boundary
copies. The compressor and its output stay unchanged. The upstream project
provides several decoders for the same format:
[official ZX0 documentation](https://github.com/einar-saukas/ZX0/blob/main/README.md).
Its advertised percentages are comparisons on other workloads, not promised
gains over our already modified Turbo player.

[faster_zx0.py](faster_zx0.py) implements two optional CPU prototypes:

1. **Tuned Turbo:** retain the Turbo bit/offset decoder. Use absolute jumps
   on frequently taken copy-boundary checks and remove address-wrap handling
   unnecessary under the current C000h..FDFFh output contract. Simplify
   synchronization and the already-satisfied-request test.
2. **Adapted Fast:** use spke/uniabis' short-offset and inline-gamma paths,
   preserving token-boundary suspension. Replace persistent IX continuation
   with `CALL ReloadReadGamma; JP CopyMatch1`; the caller may clobber IX
   between slices. Merge the literal LDI/LDIR entries into one LDIR entry
   so a literal token has one boundary check. Keep the long-match LDI/LDIR
   sequence and use absolute branches where expanded code needs their range.

The vendored [original Fast assembly](third_party/zx0/dzx0_fast.asm) is
unaltered, from upstream commit `ecde3a2ae05061fe06469ed46df81a33b7de7d86`:
[pinned source](https://github.com/einar-saukas/ZX0/blob/ecde3a2ae05061fe06469ed46df81a33b7de7d86/z80/dzx0_fast.asm).
It retains its authorship and redistribution notice. Our Python emitter is
explicitly an altered adaptation. ZX0 is by Einar Saukas; Fast is by spke
with uniabis' fixes. No existing decoder, builder default or TRD is replaced.

## Full CPU comparison

The [benchmark](benchmark_faster_zx0.py) freshly executes **564 block decodes**
(188 × three variants), including each actual sector/header/carry producer.
Requests use the same 256-output-byte boundaries; token overshoot is allowed
as in the retained player. Every baseline block also matches the earlier
complete [larger-slot comparison](inplace_streaming_cpu.json).

| Variant | Decoder CPU T | Delta | Decoder time saved | Producer + decoder T |
|---|---:|---:|---:|---:|
| Retained Turbo | 189,573,555 | — | — | 201,404,859 |
| Tuned Turbo | 187,272,946 | -2,300,609 | 1.214% | 199,104,250 |
| Adapted Fast | 183,122,436 | -6,451,119 | 3.403% | 194,953,740 |

The producer costs **11,831,304 T** in every case. Including that component,
Fast saves **3.203%**. This excludes queues, packet copying, frame decoding,
audio service, IRQs, ULA, ROM execution and drive latency. Do not present the
decoder percentage as an equal improvement in total playback speed.

| Disk | Retained decoder T | Tuned Turbo T | Fast T | Fast delta |
|---|---:|---:|---:|---:|
| 1 | 59,263,739 | 58,529,967 | 57,418,032 | -1,845,707 |
| 2 | 63,356,172 | 62,591,162 | 61,146,124 | -2,210,048 |
| 3 | 66,953,644 | 66,151,817 | 64,558,280 | -2,395,364 |

Both candidates improve **all 188 complete blocks**, with zero slower
blocks. The benchmark contains **11,584 decoder calls** per variant:

- Tuned Turbo: zero slower calls; maximum call 55,409 T versus 55,492 T.
- Fast: **62 slower calls**, maximum local regression **69 T**; maximum
  call 55,458 T. Whole-block improvement does not imply every slice improves.
- All variants read exactly **7106 sectors**, copy the same **96256 carry
  bytes**, and consume the same **1,818,909 compressed stream bytes**,
  including existing block headers. Compression-ratio and stream-size
  delta are exactly zero; pixels and AY data are unchanged.

The producer clock is frozen and ROM service is mocked. Quanta in the actual
required/optional queue can differ. The previous on-demand packet fixture's
190,422,888 ZX0 T is a separate workload; do not substitute it for this
paired baseline or infer its saving by subtraction.

## Exact instruction paths

Costs use [Zilog UM008011-0816](https://www.zilog.com/docs/z80/um0080.pdf),
especially conditional JP (printed pages 263–264), JR (267–268), and
LDI/LDIR (130–133). Full executed histograms are checked against the timing
table, and [the path probe](probe_faster_zx0_paths.py) separately executes
the boundary decisions while verifying the bit accumulator and registers.

| Boundary decision | Before | Both prototypes | Delta |
|---|---:|---:|---:|
| Output high byte below target high byte | 31 T | 29 T | -2 T |
| Equal high byte, low byte below target | 56 T | 57 T | +1 T |
| Equal target, suspend | 75 T | 74 T | -1 T |
| Equal high byte, low byte above target, suspend | 75 T | 74 T | -1 T |
| Output high byte above target, suspend | 55 T | 58 T | +3 T |

Successful-copy rows end after restoring AF, before transferring any bytes.
Suspend rows include the CALL instruction into `slice_yield`, but exclude
its body and subsequent resumption. Thus the JP substitution is not always
faster: a taken JR costs 12 T, an untaken JR 7 T, and conditional JP 10 T.
The full benchmark includes both favorable and unfavorable branches.

Target synchronization including RET costs **139 → 86 T** for tuned Turbo
(-53 T), or **139 → 112 T** for Fast (-27 T, three patched check sites).
Removing the wrapped-address test also saves **31 T** in the `slice_until`
entry, excluding synchronization. It is valid only because nonempty output
ends at or below FE00h; these prototypes must not replace the older wrapping
E000h..FFFFh decoder without restoring that contract.

Removing upstream Fast's 14-T `LD IX,CopyMatch1` initialization removes
14 T per block. Replacing its 15-T `PUSH IX` continuation with a 17-T CALL
and 10-T JP adds **12 T** whenever that continuation is needed. The full
counts include this tradeoff. There is no new DI region or interrupt delay.

## Memory and integration limits

All addresses below are half-open. The generated code fits the currently
retired regions, retaining screens, three 15872-byte slots, AY bank 4,
Huffman bank 6, TR-DOS workspace and the existing private stack reservation.

| Variant | Bank-5 helper/state region | Bank-2 hot core | Code + state bytes | Delta |
|---|---|---|---:|---:|
| Retained | 7C00h..7C23h | 8DF2h..8F09h | 314 | — |
| Tuned Turbo | 7C00h..7C77h | 8DF2h..8E9Eh | 291 | -23 |
| Fast | 7C00h..7C7Dh | 8DF2h..8F06h | 401 | +87 |

The helper limit is 7D50h; the preserved frame return remains at 8F09h.
Fast leaves three bytes before it. Stack reservation remains 7B70h..7BE0h;
no additional input, dictionary or decoded-data buffer is allocated.

There is a real tradeoff: helpers/state move to potentially contended bank 5.
Instructions executing there account for **2,253,636 T** in the baseline,
**4,229,378 T** in tuned Turbo and **4,530,562 T** in Fast. These are placement
subtotals of the CPU measurements, not measured contention delays. They
also do not classify every data/stack access made from bank-2 instructions.

The extra 87 code bytes do not change video compression, but compressed
bootstrap size and total occupied sectors remain **unmeasured**. Before
adoption, rebuild every absolute queue/bridge/producer reference and cold
overlay; verify initialized helper/state regions, actual bootstrap capacity,
independent cold boots, swaps, full nominal/fallback deadlines and AY in Fuse.
Integration with the separate direct-HL frame prototype must also move this
borrowed core to that prototype's changed retired-region bounds. No decoder
installer has yet been added to the real TRD builder.

## Verification and decision

Four [test groups](test_faster_zx0.py) pass for both candidates:

1. Header/sector crossings, different first sectors, rotating banks, shared
   carry and a short-read retry.
2. Executing the existing AY interrupt code after every producer/decoder
   instruction, checking both register sets, flags tracked by the harness,
   paging, stack, counters and exact AY writes.
3. Ninety synthetic token sequences per candidate: offsets around 127/128
   and 255/256, long offsets, short and 16-bit lengths, new and repeated
   offsets, including legal one-byte repeated matches.
4. One-byte and unaligned demand requests, token overshoot, repeated targets
   and final EOF. Returned output/input positions match the baseline even
   when the caller overwrites all working registers between resumptions.

Full native replay checks every output byte/address, each compressed input
read, no overwrite of unread in-place input, exact host write/input-cursor
digests, protected screens/banks, stack and sector order. Every volume uses
fresh RAM; previous disks supply no required state. All archived source and
generated-code hashes, block/slice/instruction sums pass the
[auditor](audit_faster_zx0.py), including code regeneration.

**Retain Fast as the leading unchanged-stream CPU candidate and tuned
Turbo as a smaller comparison.** Confirmed CPU savings justify a separate
disk integration experiment. Actual elapsed speed and publication timing
are not yet measured; this result does not claim smooth 8⅓ fps. Further
branch-frequency tuning or Mega adaptation remains unmeasured and should
be compared against these complete results, not upstream headline rates.

## Reproduction

Use the existing toolkit Python environment (NumPy/OpenCV) for execution:

```powershell
python -m unittest discover -s toolkit -p test_faster_zx0.py -v
python toolkit/benchmark_faster_zx0.py --output .tmp/faster-zx0-replay.json
python toolkit/probe_faster_zx0_paths.py --check
python toolkit/audit_faster_zx0.py --rebuild
```

The benchmark reads archived streams from Git and never recompresses them.
`--limit N` is a per-volume smoke run and remains incomplete. The default
saved-data audit needs only the standard library:

```powershell
python toolkit/audit_faster_zx0.py
```

Evidence: [all blocks and histograms](faster_zx0_cpu.json),
[summary](faster_zx0_summary.json), [individual paths](faster_zx0_paths.json).
