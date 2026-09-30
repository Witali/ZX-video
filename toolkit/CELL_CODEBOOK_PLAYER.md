# Independently bootable CB41 window player

2026-09-30, baseline `d77b8ad`. The [native component](CELL_CODEBOOK.md) now
runs through actual disk delivery, AY50 and publication in a separate
64-frame TRD (commit `4006665`). The root path now holds the verified
[192-frame successor](CELL_CODEBOOK_SUSTAINED.md). **The full-movie goal is incomplete.**

## Complete window result

| Measurement | Result |
| --- | ---: |
| Saved frames / original source frames | 128..191 / 3855..3918 |
| First-to-last publication span | 26803227 T |
| Mean fps, normalized to 50 Hz | **8.3333324** |
| Missed nominal deadlines / accumulated late runs | **0 / none** |
| Field intervals | **all 6** |
| Actual OUT phase relative to first publication | 0..16 T, under 4.6 microseconds |
| Actual OUT intervals, nominal 425448 T | 425435..425456 T |
| Exact AY records / field gaps / duplicates / underruns | **384 / 0 / 0 / 0** |
| Runtime LZSA2 / sectors | **42303 bytes / 166** |
| Total file sectors including startup/player/audio/checkpoints | **218** |
| Sectors read after first publication | **36** |
| Full published screen bytes checked | **442368, all exact** |
| Final current-disk progress | **100%** |

The uninterrupted Fuse run reaches EOF, checking every runtime sector,
every AY write/tick and 80 image samples per frame. Separate capture runs
check **all 64 complete screens after publication**, including attributes,
fixed-phase dither, black fields and progress. Captures stop only after the
selected OUT and are not cadence tests. No debugger code is installed.
Dirty-RAM cold boot and all integrated native frames/progress steps also
pass the CPU fixture with mocked ROM. Brightness still precedes dithering.

Actual elapsed Fuse time: bootstrap **12039405 T**, driver entry through EOF
**35922986 T**, combined **47962391 T**. Runtime includes prefill before first
publication. These include IRQ, ULA, ROM and emulated physical drive latency;
they exclude BASIC loading PLAYER and human disk changes. An earlier run of
the identical image also had no late frames. The final retained run uses
the final metadata; small instruction-boundary phase variation is reported.

**Limit:** 130/166 sectors arrive before first publication. Four blocks with
three slots do not prove sustained movie throughput. The exact initial
screens and AY checkpoint are on this disk, but the book was selected on
this window. Do not compare its fps directly with the earlier full 192-frame
run or extrapolate at-most-three-disk capacity.

## Implementation and CPU accounting

[cell_codebook_player.py](cell_codebook_player.py) keeps the identical
59396-byte CB41 stream, including header/book, and the existing LZSA2 queue,
TR-DOS reader, AY and six-field ISR. Read the table once and transpose it
before playback; copy each packet into fixed `6400h..7017h` and draw directly
into the back screen. No intermediate compact frame is built. Prepare only
the next packet after drawing; old extra-packet lookahead would overwrite
its pending input. Both screens are addressable while bank 7 is selected,
so no paging bridge is required for native drawing.

- Native draw: **7910734 T**, unchanged from the verified component, delta **0**.
- New packet/parser and draw-wrapper instructions: **23636 T**. Each read
  has **252 T**, the first adds **84 T**, each draw wrapper has **116 T**:
  `64*252 + 84 + 64*116`. These exclude the called queue, copy, service and
  draw bodies. Book transposition remains **54028 T** once, delta **0**.
- Four named IRQ screen-state operands move out of the retired renderer;
  opcodes stay unchanged, **13 -> 13 T each, delta 0**.
- Priming clock contributes **81 T**. The retained CPU histogram totals
  **7988479 T** for these executed instructions, including startup/first
  frame. This is not total playback CPU or disk time. The old frame-component
  comparison of 14295892 T retains the ownership caveat in the native report.

The verifier checks each executed new instruction against the generated
Z80 timing table. Actual Fuse timing is measured separately, with the real
publication/audio ISR. The component's independent full-flags/IRQ tests
remain applicable to the unchanged native kernel.

## Full RAM allocation

All eight physical banks are accounted for: **5/7** contain screens and
fixed/paged control code, **0/1/3** are video slots, **4** holds resident AY,
**2** holds fixed code/state/tables, **6** retains unused legacy Huffman data.
No additional bank or frame buffer is assumed. Kernel/state uses
`9000h..9153h`, rows `9E00h..9FFFh`, book `A800h..AFFFh`, popcount
`B000h..B0FFh`. The latter two replace old compact-frame memory. Main stack
top remains `9DF0h`, disk stack `9C00h`, decoder stack `7BE0h`. Existing
disk carry, IM2/AY and TR-DOS workspace allocations remain in place.
The 3096-byte packet bound is below existing staging capacity.

The first CPU run matched every video frame, but inspection found that
retiring old packet/clock code also removed progress code. Before any Fuse
run, restore the routine and initial counters, guard its boundary and add
checks for every progress step. The first image is not distributed. An
archiving attempt exposed an unnecessary OpenCV import; the archiver now
uses only the standard library. Final player bytes were unaffected by it.

## Artifact, reproduction and next step

The 64-frame LFS image in commit `4006665` is `ZX-video-cb41-test.trd`,
SHA-256 `dee53aefae57ae81c3e1ea4fc1708bcd86568886b0ada1c47da3c39098957d78`.
Older root images remain available. [Summary](cell_codebook_player_profile.json)
and [hashed evidence](cell_codebook_player_evidence/) contain build metadata,
CPU checks, uninterrupted timing trace, all full screens and capture traces.

Use [build_cell_codebook_trd.py](build_cell_codebook_trd.py) with:

```text
--raw .tmp/lzsa2-stages/input.fap3
--states toolkit/five_level_test_evidence/states.npz
--metadata .tmp/borrowed-literals/metadata.json
--probe .tmp/cell-codebook/probe.json
--cell-raw .tmp/cell-codebook/codebook.raw
--options toolkit/fast_zx0_player_build.json
--zx0 .worktree/compression/.tmp/ZX0/win/zx0.exe
--lzsa .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe
--output .tmp/cell-codebook-integrated
```

Reuse `PYTHONPATH=local_tools/python_packages;.tmp/lzma-z80-packages;toolkit`
and the retained trusted tools. Run `measure_fap3_fuse.py` with
`--fuse tools/fuse-1.9.0-sdl/fuse.exe --trd <output>/candidate.trd --metadata
<output>/metadata.json --raw <same FAP3> --states <same states> --output
<output>/timing.json`. Run [capture_cell_codebook_fuse.py](capture_cell_codebook_fuse.py)
with the same fuse/trd/metadata/states, `--work <output>/captures --output
<output>/captures.json`. Archive via [summarize_cell_codebook_player.py](summarize_cell_codebook_player.py),
`--work .tmp/cell-codebook-integrated --output toolkit/cell_codebook_player_profile.json
--evidence toolkit/cell_codebook_player_evidence`.

Next test **all 192 saved frames**, starting at frame zero, with one book
and uninterrupted pipeline across the three scenes. Exercise repeated slot
turnover beyond prefill. Then cover the complete authorized movie edit,
every independently bootable volume and generic converter integration.
The full goal and three-disk release requirement remain unproven.
