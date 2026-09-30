# Native Z80 C compiler comparison

2026-09-30; baseline `3608253`. The same portable
[C89 raw LZMA1 decoder](lzma_decoder_c89.c) was compiled with SDCC,
HI-TECH C and z88dk/ZSDCC and executed on a guarded Z80 CPU emulator.
**z88dk is the fastest tested C toolchain, but remains 2.3242x the CPU cost
of the existing specialized assembly decoder. Do not integrate this LZMA
decoder into realtime playback.** This result concerns this decoder and
these options, not a general ranking of C compilers.

## Unchanged input and measured results

Reuse the archived 21 transport blocks, 323940 raw bytes and 192 frames
from [the native ASM assessment](LZMA_Z80.md). No new video encoding:
all variants consume the same 133000 payload bytes. Including the existing
four-byte header per block, the transport occupies **133084 bytes / 520 sectors**.
Raw LZMA1 parameters are `lc=0, lp=0, pb=2`, dictionary limit 16384,
output limit 15872 bytes and mandatory end marker.

| Decoder | Linked code bytes | Total Z80 T-states | Extra T vs fast ASM | Observed stack bytes |
| --- | ---: | ---: | ---: | ---: |
| Existing specialized fast ASM | 1464 | 2305838368 | 0 | 14 |
| z88dk 2.4 / ZSDCC 4.5.0 | 2344 | 5359269651 | +3053431283 | 70 |
| SDCC 4.6.0 | 2443 | 6286416196 | +3980577828 | 69 |
| HI-TECH C 3.09-21 | 2638 | 8213010715 | +5907172347 | 87 |

z88dk saves **927146545 T (-14.7484%)** and 99 code bytes versus SDCC.
The tested C source has 29 scalar bytes and 3886 probability bytes; the
ASM baseline uses 64 scalar bytes and the same probabilities. Code sizes
include linked arithmetic helpers, exclude BSS and CP/M record padding,
and contain no OS CRT. SDCC's 227-byte `_HOME` helper segment is included.
Stack figures are observed high-water marks, including the entry return
address, not a proof of a universal stack bound.

All three C variants pass **21 exact video decodes, six additional data
cases and 24 malformed/truncated-input cases each**. The additional cases
cover empty/one-byte output, maximum-length overlapping copies, alphabet,
random data and matched literals. Input/code writes, model/BSS boundaries,
unwritten output reads and stack bounds are guarded; output size, complete
input consumption, type widths and return SP are checked. SDCC and z88dk
preserve IX but clobber IY in these runs; HI-TECH preserves both. Do not
assume preservation of alternate registers by C runtime helpers.

## What the generated code spends time on

All C toolchains emit a generic 32-bit multiplication for
`(range >> 11) * probability`. The specialized ASM implementation exploits
the eleven-bit probability and uses its measured unrolled EXX multiplier.
HI-TECH additionally calls library helpers for long shifts, comparisons,
OR and subtraction. The SDCC listing includes indexed byte shifts and
stack locals; z88dk's peephole/library combination reduces this overhead.

The separate 14-byte sample `abcabcXabcabcY` was audited one complete
instruction at a time against the Zilog UM0080 timing table, and its sum
was checked against an ordinary continuous emulator run:

| C toolchain | Audited T-states | DD/FD-prefixed instructions | Their T-states | Share of sample CPU |
| --- | ---: | ---: | ---: | ---: |
| SDCC | 637839 | 7310 | 131824 | 20.67% |
| HI-TECH | 1193509 | 19204 | 361040 | 30.25% |
| z88dk | 574188 | 3601 | 62043 | 10.81% |

These counts include probability initialization and indexed register setup,
not just indexed memory accesses. They are **not whole-movie profiles** or
the saving achievable by removing indexes. For reference, `LD r,(IX+d)`
costs 19 T versus `LD r,(HL)` at 7 T, excluding pointer setup. An indexed
shift costs 23 T versus 8 T for a register shift. The bounded timing audit
covers the instructions exercised by that sample, not every possible path.

The emulator can stop after an IX/IY prefix alone; the harness allows its
body to execute before comparing complete-instruction timing. This fixed
an initial audit mismatch (4 T for a prefix versus 15 T for `PUSH IX`);
the continuous decoding measurements were unaffected.

## Toolchains and reproduction

- [SDCC](https://sourceforge.net/projects/sdcc/files/sdcc-win64/4.6.0/):
  4.6.0 #16555, official x64 installer extracted locally with 7-Zip.
  `-mz80 --std-c89 --opt-code-speed --max-allocs-per-node 100000`,
  no CRT, code at 0200 and DATA at 9000.
- [HI-TECH C maintainer distribution](https://github.com/agn453/HI-TECH-Z80-C):
  3.09-21, revision `c7e943fb01855213a20e15dba9535be7d178d086`.
  Copyright HI-TECH Software; use under the upstream distribution terms.
  Runs under locally built [ZXCC](https://github.com/agn453/ZXCC), revision
  `c45e5065eca63dd045d60511a8b21ab7f567303a`. Compiler `-O -C -V`;
  linker `-Ptext=0200h,bss=9000h -C0200h`, with its original `LIBC.LIB`.
- [z88dk v2.4](https://github.com/z88dk/z88dk/releases/tag/v2.4): locally
  built in Ubuntu/WSL from the official source package. ZSDCC reports
  **4.5.0 #15242**, despite the dependency archive name `r15248`.
  `+embedded -clib=sdcc_ix -SO3 -O3 --opt-code-speed
  --max-allocs-per-node100000 --no-crt`, default supplied arithmetic library.
  This compares whole toolchains, including different backend versions and
  libraries; it does not isolate the z88dk patch against identical SDCC.
  No sweep of reserved-IY or alternate library configurations was performed.

Read [the security check](Z88DK_SECURITY_CHECK.md) before using the packages.
The prebuilt Windows z88dk ZIP was quarantined and never executed; setup
does not redownload it. SourceForge initially returned HTML rather than
the SDCC installer; setup follows its download redirect and verifies hashes.
NSIS extraction requires restoring the `cc1.exe` filename. HI-TECH rejected
`volatile`, `UL` suffixes and a typedef-based width assertion, so the shared
source uses its supported C subset and checks widths through the mailbox.
This mailbox is synchronous; it is not an interrupt-shared ABI.

The initial ZXCC BIOS build incorrectly concatenated multiple ORG regions,
causing stalled bootstrap processes. They were stopped; the reproducer
preserves ORG gaps and checks the FF00 jump. CP/M tools can report errors
with exit status zero, so the build script requires fresh output artifacts.

With Python dependencies from `requirements-lzma-z80.txt`, 7-Zip and MSVC
available, run in the repository root:

```powershell
python toolkit/prepare_z80_c_compilers.py --z88dk-source
# In Ubuntu/WSL, install the build dependencies listed in this script:
wsl -d Ubuntu -- bash /mnt/c/Work/ZX-video/toolkit/build_z88dk_wsl.sh
python toolkit/build_z80_c_decoders.py
python toolkit/benchmark_z80_c_compilers.py
```

Adjust the WSL repository path on other machines. The setup script pins
download hashes, builds ZXCC without its external install destination,
and keeps tools under ignored `.tmp`. The builder preserves actual flags,
versions, compiler hashes and listings. [The benchmark JSON](z80_c_compiler_benchmark.json)
records image/source/input identities, per-block cycles and checks.
Compressed generated listings and maps are in `z80_c_compiler_evidence`;
host compiler binaries are not vendored. `--reuse <complete-report.json>`
requires matching source/image identities and the fixed fixture, avoiding
repeated full block execution. Only the bounded instruction audit reruns.

## Scope and next step

These are deterministic uncontended Z80 component cycles, including model
initialization and the mailbox wrapper. The test map uses addresses below
4000 as RAM and therefore is **not a physical Spectrum memory map**. It
excludes OS startup, IRQ/AY work, paging, ULA contention, disk acquisition,
packet application and screen publication. No new TRD, full movie, real
drive or release cadence check was performed.

The z88dk C decoder still costs **270.06x** the existing LZSA2 decoder CPU
on the same blocks. Keep z88dk available for C component experiments;
reject realtime integration of this LZMA implementation. Player hot-path
change is **0 T**. Resume the already planned packet-copy reduction; do
not start another LZMA compiler/option sweep without a new hypothesis.
