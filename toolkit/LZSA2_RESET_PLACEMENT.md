# Bounded LZSA2 reset-placement experiment

2026-09-30, baseline `8b03511`. Change the last five blocks of the archived
192-frame five-level stream, touching frames 151..191 (69988 raw bytes).
The preceding 16 blocks, full decoded video, total 21-block count, native
decoder and 15872-byte output ceiling remain unchanged. No new TRD.

## Result

Neither tested placement warrants adoption. The ordinary packet-aligned
variant is slightly worse in measured total component work. A follow-up
changes the distribution of spare capacity and saves 73 bytes, but no sector,
and costs more measured decoder/copy work. This is not a proof that all
possible reset placements are inferior; stop broadening this small heuristic.

| Complete-stream component | Baseline | Aligned | Shifted |
| --- | ---: | ---: | ---: |
| Compressed bytes, including headers | 154956 | 155007 | 154883 |
| Video sectors | 606 | 606 | 606 |
| Decoder T | 19412006 | 19421269 | 19424888 |
| Packet-copy bridge T | 1950856 | 1943810 | 1953310 |
| Producer T, excluding ROM/physical disk | 1058423 | 1058487 | Not remeasured |
| Frame reconstruction and output T | 43760146 | 43760258 | Not remeasured |
| Total component delta T | 0 | **+2393** | Not fully measured |
| Decoder + copy delta T | 0 | +2217 | **+15336** |
| Borrowed packets in fixed ownership model | 171 | 171 | 171 |

Aligned accounting: `+9263 decoder -7046 copy +64 producer +112 frame =
+2393 T`. All assembled player instructions are unchanged; the data selects
different paths. The banked decoder/producer and copy/frame harnesses verify
executed timings against their existing Zilog UM0080 instruction tables.
These are component CPU counts, not elapsed playback time.

## Candidate selection

[probe_lzsa2_resets.py](probe_lzsa2_resets.py) chooses the latest packet start
that fits the next block while leaving enough space for the remaining blocks.
If no packet start is feasible, it keeps a valid byte cut. Both candidates
retain all four-byte block headers and the same decoded byte sequence.

- Aligned raw cuts: `253952,268541,283843,298277,313065,323940`.
  All four new interior cuts coincide with packet starts.
- Shifted raw cuts: `253952,263467,278621,292809,308681,323940`.
  Request 4686 bytes of initial slack (half the tail's 9372-byte total slack)
  to test a different reset phase. Three cuts align to packets; the fourth
  uses the 15872-byte limit to keep the block count unchanged.

The author compressor reproduces all five original payloads before each
comparison. Both variants round-trip through author and independent host
decoders, and pass every write/input-cursor in-place overlap proof at their
actual compressed stream offsets. All ten changed candidate blocks pass
the independent full-flags Z80 core plus 40 synthetic interrupts per variant.
Earlier block cycles are reused from their identical verified baseline.

## Packet-copy verifier correction

The former verifier divided raw offsets by 15872, which was valid only for
the old fixed-size block layout. [verify_borrowed_literals.py](verify_borrowed_literals.py)
now reads and validates contiguous `raw_start/raw_end` metadata, then locates
the owning block by its actual start. Source pointers and remaining-byte
counts use that block's real bounds. The native player is not modified.

[check_lzsa2_reset_copies.py](check_lzsa2_reset_copies.py) reproduces the entire
saved baseline copy report exactly, including all 45 edge cases, before
comparing new boundaries. It creates explicitly cost-only metadata; this
is not a newly built disk manifest. All candidate packet-copy instructions,
source data, destination guards, bank state and borrowing eligibility pass.

Packet alignment does not guarantee borrowing: a packet that ends exactly
at a completed slot boundary may release that slot and therefore require
a copy. The fixed ownership snapshot still borrows 171 packets in each
variant. Actual queue state and block-read timing would require Fuse.

## Coverage and decision

The aligned variant also passes the complete guarded 21-block banked
transport check: exact sectors/EOF, input and output cursors, protected banks,
carry copies and all instruction timings. Changed-block slices agree with
the independent native runs. All 192 compact frames and both native screens
are reverified exactly, including attributes and retained history.

For the shifted variant, verification stops after author/host/native block
and native packet-copy checks. Full banked producer and frame effects are
unmeasured; the +15336 T partial sum is not a full-frame timing claim.
Its 73-byte saving does not reduce the 606 sectors, and these component
results do not justify expanding it into a disk/playback trial.

No candidate real disk, ROM, ULA, actual AY cadence or publication timing
was measured. Root TRD hash remains
`14788fa7b7272c1d8ae4d47e63804cd60998d8ee95032ce56c879a120226e2d5`.
Last actual playback remains **7.683025 fps**, 118 missed deadlines; the
smooth five-level 25/3-fps goal is still incomplete.

## Reproduction and evidence

Use the same local author DLL and Python environment as the
[distance experiment](LZSA2_DISTANCE_SELECTION.md). Run the probe with
`--raw .tmp/lzsa2-stages/video.raw --stream .tmp/lzsa2-stages/video.stream
--author .tmp/lzsa2-oracle/build/lzsa2_oracle_host.dll`, first with
`--output .tmp/lzsa2-resets`, then with `--first-slack 4686 --output
.tmp/lzsa2-resets-shifted`. For each directory run the copy checker with
`--work <directory> --metadata .tmp/borrowed-literals/metadata.json
--baseline-cpu .tmp/borrowed-literals/cpu.json`.

For aligned only, run `benchmark_row_lzsa.py` on its stream/raw using the
retained metadata, saving `cpu.json`. Run `verify_borrowed_literals.py` with
the archived input FAP3 and states, its `video.raw`, and `cost-metadata.json`,
saving `frames.json`. Finally run [summarize_lzsa2_resets.py](summarize_lzsa2_resets.py)
with `--aligned .tmp/lzsa2-resets --shifted .tmp/lzsa2-resets-shifted
--baseline-frames .tmp/borrowed-literals/cpu.json --output
toolkit/lzsa2_reset_profile.json --evidence toolkit/lzsa2_reset_evidence`.

[Summary](lzsa2_reset_profile.json) and [hashed evidence](lzsa2_reset_evidence/)
preserve exact inputs, cuts, command timing, proofs, decisions and coverage.
The next separate candidate is a bounded 4x4 logical-block codebook with
exact fallback, following the user's brightness-before-dither ordering.
Measure actual coverage and compressed cost before designing native output.
