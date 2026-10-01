# Generic five-level CB41 converter

2026-10-01, baseline `9885483`. `convert_video.py --video-codec cb41` connects
the verified five-level renderer and LZSA2 transport to ordinary video input.
The existing FAP3 default is unchanged. No movie name, source-frame numbers,
crop, credit edit or volume boundaries are embedded in the new path.

## Command and output

```powershell
python toolkit/convert_video.py "C:/Video/example.mkv" --output "build/example-cb41" --video-codec cb41 --lzsa "C:/Tools/lzsa.exe" --trdos-rom "C:/Tools/Fuse/roms/trdos.rom" --verify fuse --fuse "C:/Tools/Fuse/fuse.exe"
```

Requirements remain Python/NumPy/OpenCV/Pillow, FFmpeg/ffprobe and ZX0;
CB41 additionally needs the LZSA executable. Tool paths can be supplied
explicitly. The trusted TR-DOS 5.03 ROM must have the existing required hash.
The output directory must be new or empty.

- Generic input selection, display aspect, letterboxing, EOF/tail hold,
  audio alignment, silence and AY synthesis are reused unchanged. Complete
  input is retained; the movie-specific authorized credit edit is separate.
- `generic_cell_codebook.py` refines the existing palette with the missing
  quarter shade only where RGB error improves. Five levels precede fixed
  2x2 dithering. Seven attribute bits retain INK/PAPER/BRIGHT; FLASH is zero.
  Black bands keep attribute 1. The preview renders the actual five-level
  reference, and quality reports contain per-frame four/five-level MSE.
- Both preceding screen histories are included in each volume's row union
  and cold bootstrap. Every disk boots independently; continuation uses the
  existing English prompt, series fingerprint and volume ordinal checks.
- Short/static videos can have fewer than 256 observed cell patterns.
  Unused entries are padded with black cells to retain the native 2048-byte
  table and unchanged CB41 packet syntax. Existing full books are unchanged.
- The complete verified native optimization profile is selected together.
  Legacy individual FAP3 optimization switches are rejected in this mode
  instead of being silently ignored.

`conversion.json` records the input and tools, frame/AY counts, disk hashes,
effective native options and verification state. `partition.json` records
local probes and capacity decisions. Exact references and raw reports live
under `work/`. Test/reference disk images are stored through Git LFS.

## Automatic planning and explicit limits

The planner first forms maximal row-valid ranges (at most 256 distinct rows,
including black and both histories), respecting `--max-frames-per-disk` and
the native 10922-frame counter limit. It measures 32-frame compression windows
once, then chooses byte-budget cuts. It does not build alternative complete
disk sets. AY Huffman streams are checked against the exact resident bank
size and ranges are split further when needed. One selected final set is
encoded and checked against actual startup, interleave and TRD capacity.

Window size costs include each local table; the initial reserve is 160
sectors. This is conservative selection, not minimum-volume optimization.
If actual disk capacity still exceeds 2544 sectors, conversion fails with
the measured size and suggests a smaller `--max-frames-per-disk`. A frame
whose rows and required histories cannot fit, an unsafe LZSA2 overlap, or
another native capacity failure is also rejected explicitly. The converter
does not silently drop frames, change levels or lower the frame rate.

The generic mode does not promise any video will fit three disks or meet
every deadline. The original movie's unchanged three-disk result remains
the sustained-delivery evidence. An arbitrary source needs its own complete
verification. Palette/colour-cell limitations of Spectrum output remain.

## Verification and cycle accounting

- `--verify cpu` (default): dirty independent boot and every complete native
  screen/progress step using the instruction interpreter and modeled ROM.
  Host-selected back screens in this check do not prove IRQ cadence.
- `--verify fuse`: also run each actual disk through EOF with real emulated
  disk acquisition, every AY tick/write and actual publication times; compare
  every full screen in five read-only debugger slice passes. Both prompt
  transitions are checked for a generated three-disk case with modeled ROM.
- `--verify none`: host frame/LZSA/AY round trips and actual disk capacity;
  timing remains explicitly unverified.

The native renderer layout/listing and packet listing match archived
`9885483` metadata exactly. LZSA2 retains the same instruction sequence and
absolute T-state table: delta **0 T**. Smaller legacy scaffold tables can
move its core within uncontended bank 2, changing address operands. The
archiver reassembles both old and new placements and checks their exact
machine regions before comparing the instruction tables. Content-dependent
total costs are recorded separately. The
only inherited builder fix corrects a host-side guard for one-frame volumes:
the unused playback loop still contains a reconstruction call although
priming omits the second-frame call. No Z80 opcode changes are introduced.

## Evidence and reproduction

Run `test_generic_cell_codebook.py` with `test_generic_converter.py` for
refinement, all five shades, BRIGHT, FLASH/borders, small books, row capacity,
both histories, window/AY splitting, profile identity and legacy regressions.
The combined suite contains 19 tests.

`check_generic_cb41.py` generates five input cases: single silent frame,
silent portrait, moving colour with sound split across three disks,
non-square source pixels and audio longer than video. Supply `--output`,
`--report`, the four tool paths, `--trdos-rom` and `--fuse`. For the saved
movie comparison also supply:

```text
--movie-states .tmp/cell-codebook-balanced/measured/five-states.npz
--movie-measurements .tmp/cell-codebook-balanced/measured/measurements.json
```

The latter compares every CB41 byte and full host screen hash for all 4221
frames against the saved passing volumes. It does not requantize the movie
or rebuild candidate sets. The root movie images remain unchanged.

Archive a completed run with `summarize_generic_cb41.py --work RUN_DIRECTORY
--checks CHECK_REPORT --evidence toolkit/generic_cb41_evidence
--output toolkit/generic_cb41_profile.json`. This verifies input/report/disk
identities, native code identity and complete timing/content gates before
writing the [summary](generic_cb41_profile.json) and hashed evidence. Short
fixtures alone do not prove sustained delivery; retain the
[full movie checks](CELL_CODEBOOK_BALANCED.md).

The first single-frame attempt stopped at the inherited host guard and
created no disk. After correcting the guard, the complete single-frame
Fuse run and the consolidated media suite exercise that boundary. An initial
sandboxed unit run could not read the installed OpenCV package; rerunning
with access to the same local dependencies passed, without a library change.
The first archive check incorrectly required LZSA2 address operands to match
the movie's placement. It stopped before writing a passing summary; the
corrected check proves both relocated binaries and identical instruction costs.
