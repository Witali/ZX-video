# Cell colour artifacts and solid black/white areas

Date: 2026-10-01. Baseline: `7124c9f`, branch `codex/cb41-10fps`.
This is a completed bounded experiment, not a new release or converter default.

## Findings

The five-level refinement retains the colour pair selected by the older
four-code encoder. It only inserts the missing quarter shade when this
reduces squared RGB error. That improves average tone accuracy, but does
not explicitly protect solid black/white areas or perceptual contrast.

For a neutral black/BRIGHT-white pair in the old 0/25/50/100% orientation,
nearest-tone quantization selects white above 191.25/255. Adding 75% moves
this threshold to 223.125/255. In the opposite orientation, adding the
missing 25% shade moves the black threshold from 63.75 to 31.875. Thus
some formerly solid areas become patterned even though RGB error falls.
These examples are palette-specific, not universal luminance thresholds.

Two separate palette choices can make an entire character cell stand out:

- `colour_candidates()` excludes normal white (205), keeping BRIGHT white
  (255). Useful neutral shades are therefore missing from the search.
- The old previous-attribute penalty is 100000 per 4x4 logical cell, or
  2083.33 per RGB component on average. This can retain an unsuitable colour
  pair after the source changes. Five-level refinement inherits that pair.

The physical Spectrum limit remains two colours with shared BRIGHT in an
8x8 cell. Fixing quantization cannot remove every colour-clash boundary.
Randomly changing dither phase is not a solution: fixed phase is retained.

## Controlled comparison

Four authenticated 32-frame windows start at 0, 704, 3392 and 4288 in the
prepared 10-fps edit. Original four-code attribute history is carried into
each window; the resulting baseline five-level bytes reproduce the cache
exactly. Each candidate starts with the same two baseline back screens,
then carries its own palette through the window. Source/AY/resolution are
unchanged. No full-movie candidate sweep was performed.

1. **Palette repair:** search all 56 canonical colour pairs and all five
   levels, including normal white. Keep the previous pair only within
   64 mean squared RGB units/component of the optimum and never above the
   baseline error in that cell. This is an accuracy bound, not a perceptual
   guarantee or a packet-size bound.
2. **Endpoint bias:** a fixed 12..243 input stretch proposes decisions;
   apply only 25%-to-pure-black or 75%-to-pure-white substitutions. Keep
   intermediate decisions, coloured endpoints and attributes unchanged.
   For a neutral BRIGHT pair, the new thresholds are 40.875 and 214.125.
   All five levels remain available; no frame-adaptive histogram stretching
   is used. The stretch is a deliberate accuracy tradeoff.
3. Test both operations together to reveal their interaction. Palette repair
   can replace BRIGHT white with normal white, so combining them does not
   guarantee more bright-white areas than the original baseline.

Percentages below count **solid logical 2x2 blocks inside the active image**,
excluding the black borders. They are not counts of individual white/black
physical pixels within the dither, and the sample is not the whole movie.

| Variant | Solid black | Solid bright white | Mean RGB MSE | LZSA2 window bytes |
| --- | ---: | ---: | ---: | ---: |
| Original four levels | 9.03% | 13.59% | 714.995 | Not encoded |
| Current five levels | 7.45% | 12.78% | 638.461 | 39467 |
| Five + palette repair | 5.17% | 6.78% | 373.287 | 46882 (+18.79%) |
| Five + endpoint bias | 11.78% | 14.41% | 665.018 | 42041 (+6.52%) |
| Both changes | 9.86% | 10.16% | 410.349 | 50693 (+28.44%) |

Palette repair does not raise RGB error in any tested frame or cell,
and average cell chroma-bias RMS falls from 15.277 to 11.738. However, the
opening-window boundary-residual error rises from 51.954 to 93.771; the
other three windows improve. Visual inspection confirms that the strong
coloured pattern in frame 8 disappears, while new colour blocks remain in
the sky and foliage. An RGB minimum alone does not solve spatial coherence.

Endpoint bias raises overall RGB MSE by 4.16% versus five levels; 115/128
frames worsen in that metric. Some shadow detail merges into black. It is
still lower aggregate MSE than the four-level baseline, but that is not a
claim that the new picture looks better everywhere. Combined changes have
two frames worse than the current baseline. Inspected frames: 8, 710, 3398,
4318; full per-frame metrics are archived.

The window byte totals include their individual codebooks/block headers;
they cannot be extrapolated directly to a full-volume disk count. All tested
window row dictionaries fit 256 entries; a whole volume may not.

## Decoder checks and cost

No packet format, native instructions, dither phase, AY code or RAM allocation
changed. The exact native instruction delta is **0 T**; book loading remains
**54028 -> 54028 T**. Data-dependent output work nevertheless changes:

| Output component, 128 frames per variant | Baseline | Endpoint bias | Difference |
| --- | ---: | ---: | ---: |
| Mean Z80 T-states/frame | 84330.070 | 86339.375 | +2009.305 (+2.38%) |
| Maximum in sample | 204903 | 206222 | +1319 |

The maxima need not occur on the same frame. Every executed instruction is
checked against the timing table, all 256 published-screen results match
the host reference (1769472 bytes), and guard checks cover the other screen,
stack, code, tables and registers. An independent Z80 emulator checks the
first and last frame of each variant/window (16 checks). Seventeen unit and
regression tests pass. The initial endpoint unit fixture incorrectly used
array repetition instead of tiling; it was corrected before the passing run.

These component timings exclude LZSA2, packet copies, paging, ULA contention,
IRQ/AY, TR-DOS and drive latency. No new full-player timing or disk release
claim follows. The verified root TRDs and default converter are unchanged.

## Decision and next bounded milestone

Keep these selectors as reproducible research functions, not defaults.
The endpoint-only option answers the contrast complaint but costs bytes,
CPU and detail. The palette-only option improves colour error but can reduce
solid white further and costs more data. Neither is ready for release.

Next, compare one cell selector that considers colour-boundary error,
temporal stability, solid endpoints and packet cost together. Start with
these saved windows; measure frame-level error, endpoint coverage, flicker,
actual compressed bytes and total delivery cost. Prefer local corrections
to a global contrast boost. Only after selection, check whole-volume row
capacity and perform the complete independent-boot/EOF/AY/deadline gate.

## Evidence and reproduction

- [Summary and archive hashes](cell_palette_quality_report.json)
- [All variants](cell_palette_quality_evidence/preview.png)
- [Endpoint-only comparison](cell_palette_quality_evidence/endpoints.png)
- [Per-frame quality/compression](cell_palette_quality_evidence/report.json.gz)
- [Native component measurements](cell_palette_quality_evidence/native.json.gz)
- [Selector](cell_palette_quality.py), [tests](test_cell_palette_quality.py)

Use the configured Python environment and existing author LZSA executable:

```powershell
$env:PYTHONPATH='local_tools/python_packages;.tmp/lzma-z80-packages;toolkit'
$env:OPENBLAS_NUM_THREADS='1'
python -m unittest toolkit.test_cell_palette_quality toolkit.test_five_level_dither toolkit.test_hybrid_five_level
python toolkit/probe_cell_palette_quality.py --prepared .tmp/cb41-10fps-movie/prepared/preparation.json --lzsa .worktree/three-disk-quality/.tmp/codec_sources/lzsa_build/lzsa.exe --output .tmp/cell-palette-final
python toolkit/profile_cell_palette_quality.py --work .tmp/cell-palette-final
python toolkit/archive_cell_palette_quality.py --work .tmp/cell-palette-final --tests .tmp/cell-palette-tests.log --output toolkit/cell_palette_quality_evidence --summary toolkit/cell_palette_quality_report.json
```

Capture the passing unittest output in the `--tests` log. The archive retains
window RGB inputs, both seeded histories, candidate states, raw/packed
streams, row tables, reports, previews and script snapshots. Codec scratch
files are omitted. Full preparation identity and source hashes are recorded
in the report; regenerating the four-level baseline uses that preparation.
