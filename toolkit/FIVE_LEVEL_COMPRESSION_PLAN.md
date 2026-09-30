# Compress five-level video without slowing delivery

Measured/planned 2026-09-30, baseline `37578d8`, branch `codex/dither-4x4`.
**Priority: a learned dictionary of four-sample rows, with the existing
two-page Z80 lookup renderer and Fast ZX0.** Select it only when a bounded
window improves both bytes and measured CPU; retain hybrid cells elsewhere.
This is a supported next implementation direction, not a released codec.

## Why rows are useful

The current adaptive format transfers all four or five bytes when a cell
changes. A five-level row has four logical samples: at most `5^4 = 625`
patterns. In the three measured 32-frame windows, changed cells contain only
**114, 93 and 112 distinct rows**, respectively. Every observed changed row
therefore fits in a one-byte dictionary index.

Each index selects two native bytes: the upper and lower scanlines of those
four 2x2 samples. Two 256-byte tables occupy **512 bytes**, the same lookup
space as the current four-code renderer. Table entries hold already expanded
patterns; the Z80 does not calculate divisions or dither thresholds.

Four indices represent a complete cell with all five shades. A cell with
an absent dictionary row retains its existing five-byte representation.
A cell-level hit flag selects the form; there is no per-row hit branch.
Canonical colour attributes keep phase consistent. The dictionary is learned
on the host, with stable tie ordering, and quantized pixels do not change.

Counts above cover **changed rows**, not full seed frames or the whole movie.
The complete decoder must also handle unchanged cells, seeds, two display
banks and pending frames when a dictionary changes.

## Bounded experiments

Reuse the verified uniform-five and adaptive-hybrid streams from
[the previous report](hybrid_five_level_canonical_probe.json), source
windows 629–660, 2857–2888 and 3855–3886. Recover raw packets from verified
ZX0 caches instead of requantizing RGB. Each method reconstructs the
uniform-five packet exactly, including masks and attribute residuals.

The dictionary asset is included at the beginning of each compressed window:
u16 entry count, followed by native lookup planes. Row books contain 230,
188 and 226 bytes including the count; allocation remains 512 bytes. Whole
cell books contain 2050 bytes. Blocks remain <=15872 decoded bytes and have
four-byte headers. Cold seed packets remain excluded, as in the baseline.

### Rejected: dictionary of whole 8x8 cells

The top 256 cells cover only 44.36%, 54.24% and 52.75% of changed cells.
There are 4463, 3254 and 2887 distinct changed cells. References shorten the
intermediate stream and reduce isolated ZX0 CPU, but the many escapes and
dictionary assets increase compressed bytes **68648→77866**. Reject this
candidate for the compression objective. Faster decompression alone does
not compensate for more disk data without an integrated delivery proof.

### Promising: dictionary of four-sample rows

| Window | Hybrid ZX0 bytes | Row dictionary bytes | Fast ZX0 T: hybrid → dictionary | Decision |
| --- | ---: | ---: | ---: | --- |
| 629–660 | 26,926 | 24,536 | 4,217,316 → 4,076,253 | Row dictionary |
| 2857–2888 | 21,536 | 21,769 | 3,784,612 → 3,798,201 | Keep hybrid |
| 3855–3886 | 20,186 | 19,222 | 3,378,479 → 3,321,129 | Row dictionary |

Every changed cell hits the row dictionary in these windows. Escapes remain
implemented and tested for other inputs. More compression is not guaranteed
merely because the dictionary fits: the second window worsens on both axes.

| Sum of independent windows | Baseline hybrid | Offline selection | Change |
| --- | ---: | ---: | ---: |
| ZX0 bytes, including books/headers | 68,648 | 65,294 | -4.886% |
| Fast ZX0 T-states | 11,380,407 | 11,181,994 | -1.743% |
| Mocked sector producer T-states | 481,172 | 452,965 | -5.862% |
| Window sector reads | 270 | 257 | -13 |

The Fast decoder executes actual Z80 instructions with instruction timing
and output guards. Its producer uses a mocked disk service, a frozen clock
and the same first sector 160 for each independent window. These counts
exclude TR-DOS ROM/drive latency, IRQ/ULA, dictionary installation, packet
interpretation and frame publication. The offline selector requires fewer
bytes and no increase in measured decoder+producer CPU. It is not yet an
integrated automatic player/converter policy or a frame-deadline proof.

## Renderer: measured zero per-frame overhead for table hits

Install each learned book into the current 9E00/9F00 tables before running
the **unchanged** four-code Z80 renderer. Synthetic compact states exercise
all entries, both output banks, dense updates and a sparse n-2 update.
The host reference uses the dictionary's exact native bytes; no old
four-colour table is used to validate the new picture.

| Existing renderer fixture | Original tables | Learned tables | Delta |
| --- | ---: | ---: | ---: |
| Dense twenty-band frame | 154,684 T | 154,684 T | 0 T |
| One sparse cell, including map/attributes/control | 27,101 T | 27,101 T | 0 T |

Nine executions across three books pass exact bitmap/attribute checks,
paging, stack/source guards and instruction timing checks. The opcode
hashes are identical. This demonstrates the lookup fast path, not a full
five-level decoder: escape expansion, packet dispatch, initialization,
dictionary switching, IRQ stress and release playback remain outstanding.
No player hot-path source was changed; current production change is 0 T.

The first audit used pixel coordinates where the screen helper expects
byte columns. Corrected that host reference, added a regression test and
reran all nine fixtures successfully. Four dictionary tests pass, including
all 625 row values, exact phase, mixed hits/escapes, attribute XORs and
malformed packets.

## Implementation plan, in priority order

1. **Integrate the row-table fast path first.** Include seed/retained-state
   rows when building a book; retain escapes for arbitrary videos. Prefer
   a stable per-volume book when it fits. Independent cold boot must load
   its own dictionary. For window changes, preserve the old table until
   queued frames no longer reference it, or translate/materialize the
   affected retained state. Count book loads, parsing, any remapping and
   n-2 map generation. A prefetched second book would add 512 bytes; a full
   RAM plan is still required. Do not shrink the disk buffer on this result.
2. **Use bounded selection with a delivery-cost gate.** Begin with the
   existing 32-frame evidence, carried predictors and native screen state.
   Compare exact bytes and full affected instruction costs, including
   dictionary transitions. Keep hybrid for the second measured window.
   Preserve a fixed dictionary while frames using it are buffered. Measure
   physical delivery and publication timing after integration.
3. **Omit escape metadata when coverage is complete.** A window/volume type
   can certify that every needed row is in its dictionary and use fixed
   four-byte cells. Select the decoder path once per region. This can remove
   mode bits and dispatch work, but its additional saving is unmeasured;
   certify seeds and retained states as well as transmitted changes.
4. **Then evaluate partial-row updates.** A four-bit row mask can avoid
   retransmitting and rendering unchanged rows inside a changed cell.
   Use preselected unrolled handlers and choose full-cell output whenever
   mask/dispatch cost exceeds saved work. Compute display changes against
   the actual n-2 screen, including dictionary changes and attributes.
   No new size or timing claim is made for this proposal yet.
5. **Keep expensive selection on the host.** Stable dictionary/index choices
   and equivalent representation choices may improve ZX0 repetition without
   new runtime arithmetic. Measure actual ZX0 tokens and T-states; unchanged
   decoder opcodes alone do not guarantee unchanged decompression time.

Do not add another entropy layer merely to reduce the five-byte cell size.
The measured opportunity is a different symbol representation that can use
the existing lookup operations. Keep Fast ZX0 while testing this direction.

## Integrated test follow-up: timing does not pass

The user's subsequent single-TRD request produced a 192-frame fixture with
one 172-row book covering all full frames and cold seeds. It reuses FAP3
packet consumption and the unchanged renderer, avoiding dictionary changes.
The full real-Fuse run verifies pixels and AY but averages 6.7491 fps, with
174 late frames and 5.38 seconds of accumulated delay. It fails both timing
contracts; see [the test report](FIVE_LEVEL_TEST_TRD.md). The earlier probe
numbers above remain valid only within their isolated scope.

The [subsequent fragment-selection test](ROW_FRAGMENT_SPEED.md) profiles
those costs and bypasses expensive prediction/Huffman through existing
handlers. Its optional direct mode saves 44.63% frame-stage CPU, grows ZX0
32.58%, and reaches 7.1269 fps. Both timing gates still fail; the compact
default is preserved. This is another bounded result, not a release.

**Next finite deliverable:** split the now-dominant transfer stage into ZX0,
packet copies and physical/ROM windows, then compare one change that reduces
transport or decoded volume. Reuse the saved fixture and exact pixels;
avoid another allowance sweep, dictionary transition or full-set rebuild.

## Evidence and reproduction

- [Whole-cell probe](probe_five_cell_dictionary.py) and [report](five_cell_dictionary_probe.json).
- [Row probe](probe_five_row_dictionary.py) and [report](five_row_dictionary_probe.json).
- [Z80 table audit and offline selection](audit_five_row_tables.py), [report](five_row_tables_audit.json).
- [Dictionary/phase/reference tests](test_five_dictionaries.py).

Use the existing NumPy/Pillow/Z80 test dependencies with `PYTHONPATH=toolkit`.
If the source cache is absent, regenerate it with the preceding
[five-level probe](HYBRID_FIVE_LEVEL.md#reproduce); source hashes are checked.

```text
python -m unittest toolkit.test_five_dictionaries
python toolkit/probe_five_cell_dictionary.py --cache .tmp/hybrid-five --zx0 <zx0.exe> --output toolkit/five_cell_dictionary_probe.json
python toolkit/probe_five_row_dictionary.py --cache .tmp/hybrid-five --zx0 <zx0.exe> --output toolkit/five_row_dictionary_probe.json
python toolkit/audit_five_row_tables.py --cache .tmp/hybrid-five --zx0 <zx0.exe> --output toolkit/five_row_tables_audit.json
```

Both compression probes are complete within their stated 96-frame scope.
Those two probes did not perform new quantization, movie-wide dictionary
search, TRDs or full playback. Identical restored packets imply identical five-level
pictures given the same seed; the tests do not replace cold-start validation.
