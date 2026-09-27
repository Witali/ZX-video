# Larger ZX0 reservoir with shared input and output RAM

Date: 2026-09-27. Baseline: the foreground resident-AY player at `da369e6`,
using the exact three-volume streams retained through `d0aea1a`. All **4221
frames** and independently initialized volume boundaries are retained.
This is a complete storage/memory-access experiment, **not a new playable
format or a cadence pass**. No player instructions or root TRDs are changed.

## Why investigate this

The current video slots use banks 0/1/3, each split into 8 KiB of compressed
input and 8 KiB of output/history: **24 KiB** of decoded packet storage.
The compressed prefix becomes dead as ZX0 consumes it. Placing output at
the bank bottom and input near the top can reuse that memory without copying
the whole compressed block. The resident AY bank 4, both screens, tables,
fixed code/cache/stacks and the existing BC00 carry buffer stay allocated.

This increases the reserve of decoded **video packets**, not the number of
already rendered screens. Reconstruction and native drawing still cost CPU;
a larger packet queue cannot by itself prove exact frame publication.

## Exact overlap proof

The [tracer](inplace_zx0.py) visits every compressed-byte read and every
output-byte write, including overlapping LZ matches and the end marker.
After p input bytes have been read, a write at output offset w is safe when
the unread input begins later than w. Thus the minimum input start is:

```text
start_min = max(0, max(w + 1 - p))   over writes with unread input remaining
footprint_min = max(decoded_bytes, start_min + compressed_bytes)
```

Literal reads precede their corresponding writes. Bits already held in
registers no longer require their original RAM byte. A shared-memory replay
checks source reads and live match history, rejecting any overwrite of an
unread byte. Tests verify the exact minimum start and deliberately reject a
placement one byte below it; they also cover literal-only blocks, long/new
offsets, compressible prefixes followed by literal tails, truncated/extra
input, the final marker and all 256 header alignments.

The disk-oriented layout includes the four-byte block header, the stream's
offset within its first sector, and complete 256-byte sectors. The whole
sector span ends at the bank top; the compressed pointer may be unaligned.
The last shared sector **must be copied to fixed carry RAM before decoding**.
Reported carry-copy bytes count that end copy only, not the following load
from carry or header acquisition. Those producer operations are not yet
implemented or timed for the proposed layout.

## Complete compression and RAM results

Optimal ZX0 is rerun for each block size over **2965011 original video
packet bytes**. Every decoded byte matches. The three volume boundaries and
their startup state remain independent; no previous disk's RAM is assumed.

| Output bytes/block | Three-slot reserve | Compressed stream bytes, including headers | Video sectors | Unsafe blocks |
|---:|---:|---:|---:|---:|
| 8192 (baseline) | 24576 | 1832196 | 7158 | 0 / 364 |
| 12288 | 36864 | 1823215 | 7124 | 0 / 243 |
| **15872** | **47616** | **1818909** | **7106** | **0 / 188** |
| 16384 | 49152 | 1817544 | 7101 | 180 / 183 |

The 15872-byte candidate increases the reserve by **23040 bytes (93.75%)**
while reducing compressed video by **13287 bytes** and runtime acquisition
by **52 sectors**. Its smallest safety margins after sector placement are
**255/257/255 bytes**. Maximum required unaligned footprints are
**15877/15877/15876 bytes**. These margins prove only these exact streams;
the converter must check every block for every other video too.

Full 16-KiB output is rejected: **60/59/61 blocks** overwrite unread input,
even when the compressed data end exactly at the bank boundary. Their
minimum footprints reach **16388/16389/16388 bytes**. The extra 1365-byte
compression gain over 15872-byte blocks does not make that layout valid.
All three shorter final blocks fit.

| Disk | New stream bytes | Video sectors | Used sectors if bootstrap unchanged | Free sectors under that assumption |
|---|---:|---:|---:|---:|
| 1 | 606434 | 2369 | 2461 | 83 |
| 2 | 606524 | 2370 | 2462 | 82 |
| 3 | 605951 | 2367 | 2461 | 83 |

These capacity estimates include the existing sector interleave and hold
the old video start and bootstrap fixed. A new loader/decoder changes boot
code and must be built before claiming actual TRD capacity.

Three full initial blocks contain **91/76/41 complete packets**, versus
**52/31/15** before. Across measured three-block windows the minimum complete
packet counts are **35/16/24**, versus **15/9/11**. These are byte-availability
counts, not a simulation of rendering time, dynamic queue occupancy or disk
latency. End-copy traffic for shared final sectors falls **92928→48128 bytes**;
the complete producer's copying/control cost remains to be measured.

## Native Z80 verification

The [native benchmark](benchmark_inplace_zx0.py) executes the bundled
126-byte turbo decoder on every baseline and candidate block, once with
separate input/output memory and once with overlapping input/output in a
bank. It guards all input/history access, output order, code writes, stack,
paging and final cursors. Every output write's input cursor must match the
host trace; this includes the final bytes and source-pointer wrap at FFFF.

This scope excludes the player's resumable wrapper, IRQ, ULA waits, paging,
the sector producer and queue. Its instruction costs follow the existing
[Zilog timing table](https://www.zilog.com/docs/z80/um0080.pdf).

All **364 baseline and 188 candidate blocks** pass both layouts: **1104
native runs**, covering **11860044 output writes**. Per-block read-cursor
trace hashes match the independent host model. Shared and disjoint layouts
execute identical instructions with **zero T-state delta** on the same block.

| Disk | 8192-byte blocks, turbo T-states | 15872-byte blocks, turbo T-states | Delta |
|---|---:|---:|---:|
| 1 | 50104312 | 50873268 | +768956 |
| 2 | 53675760 | 54440030 | +764270 |
| 3 | 56872984 | 57600091 | +727107 |
| Total | **160653056** | **162913389** | **+2260333** |

The larger blocks are smaller on disk but cost **1.407% more** uninterrupted
decoder work. Therefore retain 15872 as an integration candidate, not an
accepted speed improvement. Fewer block boundaries and sectors may offset
some cost; the nearly doubled reserve may absorb delivery bursts. Neither
effect has been measured in the new producer/scheduler. Full frame timing
must decide whether to keep this layout.

## Next implementation and acceptance checks

1. Keep the smaller resident-AY baseline. Add an optional block-size/layout
   contract with per-block safety rejection or splitting; keep the usual
   four-byte length header and every video/AY byte. Do not assume this movie's
   margins apply to another source.
2. Move the resumable ZX0 output base to C000 and retain its private stack,
   input cursor and live history while suspended. Update every queue/demand
   conversion between absolute and relative offsets (E000/2000 becomes
   C000/4000), final EOF handling and length bounds. Compare generated code,
   absolute cycles, all output bytes and IRQ interruption boundaries.
3. Read the first header through existing fixed carry storage, calculate the
   top-aligned sector destination, and read each later sector once. Handle a
   header crossing a sector, input ending at 0000 after FFFF, and the last
   shared sector. The current disk adapter assumes an E000 input limit and
   advances regions there; that behavior must be replaced or bypassed.
   Count header/carry copies, paging, code size and all producer T-states.
4. Enforce slot ownership until output is consumed and ZX0 has read EOF.
   A consumed output prefix remains live LZ history until its block ends.
   Preserve audio service and the six-field schedule; add no intentional
   lateness or changes to the AY interrupt.
5. Build all three independent TRDs, execute dirty cold boots, both disk
   swaps, full compact/native comparisons and complete Fuse EOF playback.
   Measure actual publication deadlines, recovery, AY cadence, sector order
   and elapsed read/seek intervals. Report CPU separately from those waits.
   Only complete timing evidence can replace the existing release images.

## Reproduction and evidence

Use project Python dependencies and `PYTHONPATH=toolkit`:

```powershell
python -m unittest test_inplace_zx0 test_inplace_zx0_native -v
python toolkit/probe_inplace_zx0.py --directory .tmp/resident-audio-player-foreground --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --cache .tmp/inplace-zx0-cache --evidence toolkit/inplace_zx0_evidence --output toolkit/inplace_zx0_probe.json
python toolkit/benchmark_inplace_zx0.py --probe toolkit/inplace_zx0_probe.json --evidence toolkit/inplace_zx0_evidence --output toolkit/inplace_zx0_cpu.json
python toolkit/audit_inplace_zx0.py
```

The [probe](inplace_zx0_probe.json) pins original TRDs, every block and all
12 archived compressed streams (7153056 packed bytes). The
[CPU report](inplace_zx0_cpu.json) pins the native generator and model. The
[auditor](audit_inplace_zx0.py) independently decodes every archive, rechecks
all overlap witnesses, replays safe layouts, rejects unsafe ones and verifies
the saved native trace hashes and cycle totals. Its [summary](inplace_zx0_summary.json)
keeps storage estimates distinct from player verification.
