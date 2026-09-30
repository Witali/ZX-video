# Exact cell-codebook feasibility and native output

2026-09-30, baseline `63947dd`. One saved 64-frame window, indices 128..191
(source frames 3855..3918), with the original two preceding screen states.
This is a new experimental inner video representation carried by unchanged
standard LZSA2. The native component follow-up below uses baseline `d1f32d3`;
the subsequent [integrated window disk](CELL_CODEBOOK_PLAYER.md) and
[complete 192-frame fixture](CELL_CODEBOOK_SUSTAINED.md) now pass actual
playback. Full-movie release verification remains pending.

## Host/transport result: promote to native implementation

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

All multibyte integers are little-endian. The experimental CB41 player
understands this format; the legacy player and production converter do not.

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

## Host/transport fairness, verification and limits

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
- This first experiment did not include native cell output or a dictionary-
  load kernel; the follow-up below supplies those components. Complete packet
  transport, actual disk/ROM/ULA cadence and full-movie checks remain pending.

The older 192-frame root test TRD still measures **7.683025 fps** with
118 missed deadlines. The overall smooth five-level 25/3-fps goal remains
incomplete. Component results do not establish a new playback rate.

## Native component follow-up, 2026-09-30

[cell_codebook_z80.py](cell_codebook_z80.py) now assembles the renderer. Both
variants use the same exact 64-frame payloads and prior screens above.

| Frame-processing component | Old borrowed-literal path | CB41 literal-only | CB41 with book |
| --- | ---: | ---: | ---: |
| Total CPU T for 64 frames | 14295892 | 7198585 | **7910734** |
| Difference from old component | 0 | -7097307 | **-6385158 (-44.66%)** |
| Mean native draw T | — | 112477.89 | 123605.22 |
| Maximum native draw T | — | 180208 | 191369 |
| Code bytes, excluding three state bytes | — | 244 | 335 |

**Scope:** the old component includes reconstruction, metadata, output and
associated paging in the full borrowed-literal fixture. CB41 receives an
already accessible validated payload and mapped target screen. This is
not a complete delivery comparison: packet acquisition/copying, caller
paging, publication, real AY/IRQ, ULA contention and disk/ROM latency are
excluded. The source/input hashes and instruction histograms are archived.

Book output costs **712149 T more** than literal-only output on this window,
including mask counting and mode parsing. Adding their separately measured
LZSA2/producer components gives literal-only **12886680 T**, book **12107210 T**
(book saves **779470 T**). These hypothetical sums omit the costs above and
startup. They justify an integrated test, not an fps prediction.

### Registers, memory and absolute instruction costs

- Main HL streams pixel/attribute values; DE addresses the target screen;
  BC indexes row/book pages. Alternate HL scans masks, DE scans mode bytes,
  B holds the mode-bit sentinel and C counts mask groups. AF' protects the
  rotating cell mask during each changed-cell write.
- Entry: HL points to the validated frame payload without its length word;
  A is `40h` or `C0h` for the already mapped back screen. Return HL points
  exactly past the payload. Both AF/BC/DE/HL sets are clobbered; IX/IY/SP are
  preserved. No paging, screen publication, DI/EI or packet copy occurs.
  IRQ code must preserve any working registers it touches in either set.
- Provisional fixed-bank layout: code/state at `9000h`, existing 512-byte
  row table at `9E00h`, 2048-byte book at `A800h`, 256-byte popcount table at
  `B000h`. Book/popcount **replace part of the old compact-frame allocation**;
  integration must remove its old users and validate the full 128 KiB map.
- Native startup transposes 256 consecutive eight-byte patterns into eight
  scanline pages. This avoids per-cell multiplication and costs **54028 T**
  once per book. Its cost is separate from the frame totals. Formula:
  `7 + 256*(7 + 8*(7+6+7) + 7*4 + 4) + 255*12 + 7 + 10`.

Instruction costs use the [Zilog Z80 CPU manual](https://www.zilog.com/docs/z80/um0080.pdf),
with no wait states. Every executed instruction is checked against its
declared timing, then total time is checked in an independent full-flags core.

| Changed-cell work, excluding caller CALL/mask scan | Absolute T |
| --- | ---: |
| Dictionary load and eight writes, including jump to common return | 200 |
| Four row-index loads and eight writes | 231 |
| Common screen-pointer restore / AF exchange / RET | 29 |
| Book mode selection, dictionary / literal, no refill | 39 / 44 |
| Book mode selection, dictionary / literal, with refill | 55 / 60 |
| Literal-only AF exchange | 4 |

Thus the complete dictionary helper costs **268/284 T**, versus **304/320 T**
for its fallback and **264 T** for a literal-only helper; taken CALL adds
17 T in each case. The prepared bitmap saves 31 T in the write body, but
mode selection and mask counting must also be charged.

The first banked run stopped at unsupported `SCF` (opcode `37h`); the
literal-only 64-frame path had passed. Inspection showed that instruction
was redundant: a drained sentinel is B=1, so `SRL B` already sets carry;
`LD A,(DE)` and `INC DE` preserve it for `RRA`. Removing SCF reduces refill
by **4 T**, **9768 T** over 2442 refills in this window, and code 336 -> 335
bytes relative to the initial assembly. This delta is derived, not a full
timed comparison of the interrupted version. Final independent checks pass.

### Native verification and next step

- Both variants reproduce all 64 complete screens exactly and preserve the
  other screen, row/book tables, code, payload, stack pointer and paging contract.
  Guards reject reads outside supplied input/tables/code/stack and writes
  outside the active screen area/state/stack. Black fields are untouched.
- 22 native synthetic variants cover all book indices, full literal output,
  BRIGHT, unchanged/attribute-only frames and mode boundaries. The largest
  synthetic draw costs 240190 T.
- Independent full-flags runs agree on every frame and loader cycle count.
  Separate IM1 tests inject 40/61 window interrupts plus five edge interrupts
  (**106 total**, zero unavailable events) while preserving both register
  sets. This is not a real AY handler or 50-Hz scheduling measurement.

Retain the verified component. The subsequent
[integrated window test](CELL_CODEBOOK_PLAYER.md) supplies an independent
disk, full screens, AY and actual deadline checks. Its next step is sustained
delivery on the complete 192-frame fixture, then full-movie validation.

## Reproduction and retained evidence

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

For the native follow-up, run [verify_cell_codebook_z80.py](verify_cell_codebook_z80.py)
with `--work .tmp/cell-codebook --states toolkit/five_level_test_evidence/states.npz
--metadata .tmp/borrowed-literals/metadata.json --baseline-frames
.tmp/borrowed-literals/cpu.json --output .tmp/cell-codebook/native.json`.
It requires the existing NumPy/Z80 Python packages used by previous native
checks. Then run [summarize_cell_codebook_native.py](summarize_cell_codebook_native.py)
with `--input .tmp/cell-codebook/native.json --output
toolkit/cell_codebook_native_profile.json --evidence toolkit/cell_codebook_evidence`.
[Native summary](cell_codebook_native_profile.json) and
[complete native evidence](cell_codebook_evidence/native.json.gz) retain
per-frame results, assembled bytes, instruction listings/histograms and hashes.
