# Exact cell-codebook feasibility

2026-09-30, baseline `63947dd`. One saved 64-frame window, indices 128..191
(source frames 3855..3918), with the original two preceding screen states.
This is a new experimental inner video representation carried by unchanged
standard LZSA2. No native cell renderer or player integration exists yet.

## Result: promote to native implementation

| Same 64-frame window | Current packets | Direct cells, literal rows | Direct cells + 256-entry book |
| --- | ---: | ---: | ---: |
| Raw bytes, including new header/table where applicable | 105999 | 88788 | **59396** |
| LZSA2 bytes including block headers | 51022 | 42675 | **42303** |
| Payload sectors | 200 | 167 | **166** |
| LZSA2 decoder T | 6353724 | 5393835 | **3923387** |
| Producer T, excluding ROM/physical disk | 350445 | 294260 | **273089** |
| Decoder + producer T | 6704169 | 5688095 | **4196476** |
| Maximum 256-byte-demand slice T | 19190 | 19348 | **21530** |

The dictionary candidate saves **8719 bytes (17.09%)** and **2430337 decoder
T (38.25%)** relative to current packets on this window. Decoder + producer
saves **2507693 T**. All candidate pixels and attributes are exact; no lossy
approximation or lower frame rate is used.

The control isolates the mechanism: most compressed-size savings come from
simpler cell deltas. The book adds only **372 compressed bytes** of savings
over the control, but removes **29392 raw bytes** and **1470448 decoder T**.
Thus its main additional benefit here is less data to decompress, not a
large extra compressed-size ratio. Its higher maximum slice cost must be
checked in the real producer/consumer schedule; mean CPU is not a deadline.

Of **19303 changed cells**, **11294 (58.51%)** match the 256-entry dictionary.
There are 5010 distinct changed patterns. Selection uses exact occurrence
frequency in this same window; it is not an unseen-video or full-volume
coverage claim. The complete **2048-byte bitmap table** is included in the
candidate byte counts, as are masks, mode bits, lengths and fallback values.

## Representation and dither order

A cell is 4x4 logical brightness samples, displayed as one aligned 8x8
Spectrum character cell. Compare its four existing row symbols with the
same cell two frames earlier, which is the content of the back screen.
Skip unchanged cells. An updated cell uses either a dictionary index or
four exact row indices; no motion interpolation or residual reconstruction
is necessary in this experiment. Attributes have a separate change mask
and retain all seven non-FLASH bits, including BRIGHT.

Dictionary entries are generated in the user's specified order:

1. Resolve row symbols to their four brightness levels in 0..4.
2. Apply the existing fixed-phase 2x2 dither to each reconstructed level.
3. Store the resulting eight bitmap bytes for the complete cell.

The independent scalar generator agrees with every existing row-table entry.
Lookup of a complete prepared pattern therefore fuses the same operations;
it does not dither individual transform contributions before summing them.
This prototype selects observed exact patterns, **not DCT coefficients**.
It tests the ready-block mechanism before adding any approximation.

The native player would write into its back screen and flip on the original
deadline. No change to AY is proposed; audio is outside these video payloads.
The black bitmap fields are retained, and the host probe asserts that their
attributes do not change. The separate progress indicator is not encoded here.

## CB41 experimental wire layout

All multibyte integers are little-endian. This format is not understood by
the current player and is not enabled in the production converter.

- `CB41`, `u16 frame_count`, `u16 dictionary_entries` (0 or 256 in this probe).
- For 256 entries: 256 consecutive eight-byte bitmap patterns, scanline order.
- Each frame: `u16 payload_bytes`, followed by the payload below.
- 72-byte bitmap-change mask for 18x32 active cells (screen cell rows 3..20).
- 72-byte attribute-change mask for those same cells.
- With a book: `ceil(changed_bitmap_cells/8)` mode bytes; one means dictionary,
  zero means literal. There are no mode bytes for the literal-only control.
- Ascending changed cells: one-byte dictionary index or four row indices.
- Ascending changed attributes: one attribute byte each.

Masks use bit 0 first within each byte. The payload extent must be consumed
exactly. New packet sizes peak at **1333 bytes** in the window; the synthetic
all-literal/all-attribute case is **3096 bytes**, before its two-byte length.
This fits the present 4704-byte packet workspace by size only; ownership,
copying and streaming integration have not been implemented.

## Fairness, verification and limits

All three comparisons begin with fresh LZSA2 resets and use blocks at most
15872 bytes. This local baseline is a freshly compressed copy of the same
64 original packets, not their contribution to the existing full stream's
shared history. Earlier screen/predictor state is supplied explicitly.
The common 512-byte row table, existing AY, player code and initial history
are excluded from every column. No cold-boot capacity estimate is implied.
Every final disk must include its own book and starting state.

- Both new representations restore all 64 full 6912-byte screens, while
  also checking the untouched other screen after every frame, against the
  accepted five-level reference. Zero differing pixels or attributes.
- 22 synthetic variant cases cover an unchanged frame, attribute-only
  changes, every dictionary index 0..255, all 576 cells using fallback,
  all active BRIGHT attributes, and mode-mask boundaries 1/7/8/9/15/16/17.
- All 17 compressed blocks pass original-author and independent host
  decoding, per-write overlap proofs, guarded banked transport, exact
  sector order/EOF and instruction timing checks.
- The independent full-flags Z80 core agrees on every decoder slice;
  synthetic runs inject 60/53/37 interrupts for the three variants, with
  zero unavailable events. This is not actual 50-Hz AY verification.
- No native cell output, complete packet transport, dictionary-load kernel,
  actual disk/ROM/ULA cadence or full-movie run is claimed. A 2-KiB dictionary
  still needs an explicit bank allocation, including the retained row table.

The current root TRD is unchanged and still measures **7.683025 fps** with
118 missed deadlines. The overall smooth five-level 25/3-fps goal remains
incomplete. The promising component result justifies the next implementation;
it does not establish a new playback rate.

## Next implementation and evidence

Build a real Z80 CB41 cell renderer and verify all masks, dictionary and
literal paths, attributes, cursors, stack, preserved input and bank state.
Count every instruction and compare complete frame work with the old path.
Consider transposing the book into eight 256-byte scanline pages at startup
to avoid multiplying each index by eight. Account for that load and RAM;
keep the original transmitted eight-byte pattern layout initially.
Then integrate packet delivery and actual deadlines on one selected window.

Use [probe_cell_codebook.py](probe_cell_codebook.py) with `--states
toolkit/five_level_test_evidence/states.npz --metadata
.tmp/borrowed-literals/metadata.json --video .tmp/lzsa2-stages/video.raw
--author .tmp/lzsa2-oracle/build/lzsa2_oracle_host.dll --output .tmp/cell-codebook`.
The local DLL/Python setup is the [same as the earlier oracle](LZSA2_EXACT_ORACLE.md).
Run [test_cell_codebook.py](test_cell_codebook.py) with those states/metadata,
`--probe .tmp/cell-codebook/probe.json --output .tmp/cell-codebook/tests.json`.
For each of `current`, `direct_rows`, `codebook`, run `benchmark_row_lzsa.py`
on the emitted raw/stream and retained metadata, then `verify_lzsa2_search.py`
against that CPU report. Finally run [summarize_cell_codebook.py](summarize_cell_codebook.py)
with `--work .tmp/cell-codebook --output toolkit/cell_codebook_profile.json
--evidence toolkit/cell_codebook_evidence`.

[Summary](cell_codebook_profile.json) and [hashed evidence](cell_codebook_evidence/)
retain all payloads, initial screens, per-frame checks, timings and provenance.
