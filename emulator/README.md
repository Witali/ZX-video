# Native CPU and Spectrum128 test platform

This project develops its own headless test platform around the Z80 Tester
C CPU. Sources, bus, build tools, Python API and tests live here; running it
does not require `C:/Work/z80-tester`. Decoder packages stay self-contained
and do not acquire a compiler/emulator dependency.

The pinned floooh/chips CPU and derived instruction slices are under
[vendor/z80_tester](vendor/z80_tester/provenance.json), with their
[zlib license](vendor/z80_tester/LICENSE). Local adapter changes belong in
[codec_cpu.c](src/codec_cpu.c); the original upstream header stays pinned.
The [C API](src/codec_cpu.h) exposes registers, native guards/counters, single
T-states and optional fused flat execution. The source project is read-only.

## Build and run

From the repository/worktree root on Windows with Visual Studio C++ Build
Tools and Windows SDK:

```powershell
.\emulator\build_codec_cpu.ps1
python -m unittest discover -s emulator/tests -v
```

Build artifacts go under ignored `.tmp/codec-cpu`; no DLL is committed.
Use `-OutputDirectory .tmp/my-cpu` for a separate build, then select it with
`$env:CODEC_EMULATOR_DLL=(Resolve-Path .tmp/my-cpu/codec_cpu.dll).Path`.
`CODEC_CPU_DLL` is a compatibility alias. Python uses only the standard
library at runtime. Cross-core comparisons additionally need the existing
project `z80==1.2.0` test dependency and frozen library fixtures.

## Two execution modes

The [Python API](cpu.py) has two explicit modes:

- `execute_block(profile, packed, expected)` is a guarded, disjoint, flat
  64 KiB CPU replay. It checks source order, exact output, code patch
  permissions, caller stack/cursors and preserved registers. C handles byte
  checks and optional branch counters without entering Python per byte.
  `fast=False` runs original single-T execution for independent slice checks.
- `CPU` plus `Spectrum128` attaches a native banked bus, including ROM
  protection, physical RAM aliases, 7FFD paging/lock and frame INT. Attaching
  a bus disables fused flat execution and flat memory guards. Use the
  Spectrum runner's physical-bank/final-state checks; do not describe them
  as live unread-input guards. The independent library overlap/IRQ runners
  remain required correctness gates.

For an already built resident decoder and valid forward ZX0 v2/raw LZSA2
payload:

```python
from emulator.cpu import execute_block

result = execute_block(profile, packed, expected_output)
print(result['tstates'], result['stack_bytes'])
```

For the banked Spectrum runner:

```python
from emulator.spectrum_runner import execute

result = execute(profile, packed, expected_output, codec='zx0',
                 output_bank=0, interrupts=True, frame_phase=0)
```

It places source at 4000h, code/table in fixed RAM2, output atC000h in a
selected physical bank and caller SP atBFF0h. It rejects physical aliases
of code/stack or compressed source before setup, checks all eight final RAM
banks and records exact IRQ acknowledgements. Supply `codec='lzsa2'` for
raw LZSA2. Test ROM interrupt/return stubs are explicit setup, not a boot ROM.

The default flat source is 2000h, output C000h, code comes from the profile and
caller SP is BFF0h. These are test allocations, not a Spectrum ROM layout.
Supply `source`, `output` and `caller_stack` for other disjoint placements.
Input/output/history stay outside the target decoder's service-memory count;
host C/Python emulator memory is not target Z80 memory.

## Spectrum128 model and timing scope

[spectrum128.c](src/spectrum128.c) is a headless original Spectrum128 bus,
with references to Fuse/libspectrum timing and paging sources in its header
comments. It supplies eight16 KiB RAM banks and two caller-loaded16 KiB ROM
pages. Fixed windows map RAM5 at 4000h and RAM2 at 8000h; 7FFD selects the
C000h bank, screen and ROM, and its lock. ROM images are not distributed.
Frame INT and CPU/ULA-wait accounting are separate from application IRQ code.

The explicit memory/internal/I/O contention primitives have independent
tests. **Instruction-level ULA contention is not yet qualified.** The CPU's
pin callback alone cannot supply all internal-cycle addresses or the original
core's memory WAIT sampling phases. `Spectrum128.attach` therefore rejects
`contention=True`; normal instruction runs are clearly marked uncontended.
The before-T API allows separately verified phase/address annotations to be
developed here rather than guessing delays from stale pins.

Unknown input/floating-bus/AY/disk I/O is counted explicitly. This platform
does not claim sound synthesis, TR-DOS delivery, ROM boot or full movie
publication timing. Those application gates remain separate from decoder
CPU measurements, as required by [the optimization plan](../libraries/NEXT_TRICKS_PLAN.md).

## Verification status

The independent reference is still the existing protected kosarev native
runner. Core qualification must compare identical decoder bytes, full RAM,
CPU T, exact source/output, stack and named register fields before using this
backend for screening evidence. ZX0 and LZSA2 comparisons are recorded
separately; differences in clobbered undocumented flags must be retained and
explained, never silently masked as full-state equality.

All **31** CPU, bus, Python API and Spectrum decoder tests pass on the final
qualified build. [Authentication](evidence/verification.json) and its
[verifier](verify_evidence.py) bind the exact compiled sources, generators,
test log and complete reports. DLLs remain generated, ignored artifacts.

The [flat cross-core proof](evidence/native_comparison.json.gz) checks 1,148
cases:473 ZX0 and 675 LZSA2. CPU T and complete64 KiB RAM match exactly.
All twelve compared ZX0 registers match. Ten non-real LZSA2 cases differ
only in clobbered AF' F3/F5 bits; documented flags, A, preserved pairs, source,
stack, output and CPU T match. There are no such differences on real inputs.
The independently tested LDIR-repeat and SCF/Q rules follow
[hardware observations](https://raw.githubusercontent.com/wiki/hoglet67/Z80Decoder/Undocumented-Flags.md).
The [full diagnostic trace](evidence/flag_difference_trace.json.gz) retains
the first divergence. Minimal vectors are reproduced by the CPU unit tests;
the original ad hoc trace sources are archived as historical data, not a
runtime dependency.

The [Spectrum proof](evidence/spectrum_decoder_baseline.json.gz) runs all 417
ZX0 and 675 LZSA2 normal cases with exact old-backend CPU equality at source
4000h. Another 300 IRQ configurations cover six safe banks and five frame
phases; CPU is exactly plain CPU + 95 T per acknowledged diagnostic IRQ. All
eight final physical banks, source, output/cursors and preserved registers
pass. Every one of these 1,392 configurations is revalidated on the final
build; original execution and later revalidation identities stay distinct.
High-word synthetic flat cases need not fit a real Spectrum RAM allocation.

Median host test times below use three repetitions with rotated engine order,
the frozen real corpora, all native setup/validation included. They measure
**test execution on this host**, not a faster decoder on the target Z80:

| Codec | Native C guards s | Existing Python guards s | Guarded speedup | Existing unprotected native s |
| --- | ---: | ---: | ---: | ---: |
| ZX0 | 1.08403 | 4.44859 | 4.10x | 0.43060 |
| LZSA2 | 0.07344 | 0.49677 | 6.76x | 0.05043 |

The old unprotected native core remains faster for bare execution; native
guards/counters remove Python callback overhead where protection/profiling
is needed. Target real CPU totals stay 139,892,818/14,944,429 T and target
service memory is unchanged. No library mode/default is promoted by this
host-tool change. Actual-overlap, quota/guarded supplier and release checks
still use their qualified independent runners.

Reproduce the saved scopes with the project native dependency environment:

```powershell
python emulator/tests/test_codec_cpu.py --full-report .tmp/native-comparison.json.gz
python emulator/spectrum_runner.py --report .tmp/spectrum-baseline.json.gz
python emulator/spectrum_runner.py --report .tmp/spectrum-baseline.json.gz --revalidate
python emulator/verify_evidence.py
```

Regeneration initially exposed a stale imported slice artifact missing eight
repeat-stage hooks. Local generation restores them and now reproduces both
included headers exactly; true fused repeat-boundary tests cover that path.
An early comparison also stopped on a zero-length-output test allocation;
the harness was corrected before the complete final run. Preserve these
findings in provenance rather than labeling the initial artifacts qualified.
