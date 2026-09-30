# Five levels with the established 2x2 dither

Validated 2026-09-30 on `codex/dither-4x4`, after `b7604ab`. This closes
the requested five-level host feasibility experiment. **Retain palette
endpoints and use adaptive four/five-byte cells as the compression
reference for native implementation.** This is not enabled in the player.

**Measured follow-up:** [the row-dictionary compression plan](FIVE_LEVEL_COMPRESSION_PLAN.md)
uses the same exact five-level output and hybrid stream as its baseline.
Bounded selection saves a further 4.886% of bytes with fewer Fast ZX0
T-states; unchanged native lookup opcodes pass isolated rendering checks.
Its dictionary-transition and integrated player costs remain outstanding.

## Pattern and quality contract

Each logical sample still occupies 2x2 native pixels; the grid remains
128x96 with a 128x72 active picture. With canonical lighter INK and darker
PAPER, the pattern family is:

```text
INK coverage:  0/4  1/4  2/4  3/4  4/4
top row:       00   10   10   11   11
bottom row:    00   00   01   01   11
```

These are the established phase-aligned 2x2 patterns, including the upper
quarter previously accessible through reversed endpoints. All five can
now coexist in the same 8x8 attribute cell. There is no 4x4 threshold
matrix, downsampling or temporal alternation. Coverage percentages are
two-colour area mixtures, not calibrated perceptual brightness percentages.

`refine_compact` keeps the selected colour pair and BRIGHT. It adds only
the missing quarter shade, and only when that logical sample's squared
RGB error strictly decreases. Other samples remain unchanged. Attribute
orientation may be canonicalized or used as storage metadata; independently
decoded colours and fixed spatial phase remain identical. FLASH stays zero.
Native implementation must preserve this phase contract, including when
the stored endpoint order changes.

## Representations compared

| Control | Cell bytes | Mode metadata | Purpose |
| --- | --- | --- | --- |
| `four` | 4 | None | Existing four-code input and colour pairs, with phase-aligned host rendering |
| `five` | 5 | None | Four radix-5 rows of four samples, ten bits per row |
| `hybrid` | 4 or 5 | One bit per changed cell | Use endpoint orientation for lower/upper quartet; escape when both quarter shades occur |
| `canonical` | 4 or 5 | Two bits per changed cell | Fixed endpoint order, explicit lower/upper/full-five modes |

The two adaptive variants reproduce **exactly the same native picture** as
`five`. They are lossless storage alternatives for its quantized output.
Quartets include both endpoints and the half-tone; the remaining quarter
is selected by endpoint orientation or the explicit mode. A five-byte cell
is required only if both 1/4 and 3/4 occur. This occurs in 6.05%, 1.06% and
3.16% of active cells in the three measured windows.

Temporal packets retain separate attribute-XOR and cell change masks
(96 bytes each), changed-cell mode bits where applicable, and payloads.
Each packet has a u16 length. ZX0 blocks contain at most 15872 decoded
bytes, plus four-byte headers. No alternate images need to be searched
or decoded on the Spectrum to choose these host representations.

## Measured windows

Original source SHA-256:
`dc2146a2b1172def56730143ad80cd1825b7fad15f1fc9c23a4e7d01a741ac11`.
Source frames 629, 2857 and 3855 start three 32-frame windows with a carried
preceding seed: 96 measured frames plus three seeds. Source rate is 25/3 fps.
Use 256x144 area scaling, central zoom 1.25 and the existing palette selector
with attribute-change penalty 100000. No release adaptive tone grouping
or feedback-budget preprocessing is applied. Seeds are outside byte totals.

| Window | Four-code ZX0 bytes | Full-five bytes | Hybrid bytes | Canonical bytes | Hybrid vs four | Mean RGB error reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 629–660 | 18,304 | 31,048 | 26,926 | 26,983 | +47.10% | 16.14% |
| 2857–2888 | 20,045 | 27,193 | 21,536 | 22,202 | +7.44% | 1.16% |
| 3855–3886 | 17,797 | 24,259 | 20,186 | 20,702 | +13.42% | 6.81% |
| Total | 56,146 | 82,500 | 68,648 | 69,887 | +22.27% | — |

Error is measured against original scaled RGB using each 2x2 native area's
mean colour, not a perceptual accuracy percentage. No measured frame gets
worse on this metric. The per-sample refinement rule also prevents an
individual logical sample from increasing this squared error. It does not
guarantee unchanged temporal flicker or improvement on every visual metric.

Hybrid saves 16.79% versus uniform five-level storage. Canonical adds 1,239
bytes (+1.80%) over hybrid in total; it may simplify phase selection during
native expansion, but that CPU benefit has not been implemented or measured.
Do not call the smallest stream the fastest player without that measurement.

For comparison, the prior adaptive 4x4 candidate used 128,856 bytes in the
same three RGB windows, versus 68,648 for this hybrid five-level candidate.
These are their respective cell-stream controls. The previously reported
4x4 increase of 56.19% was relative to **uniform five-level storage**;
the 22.27% here is relative to **four-code storage**. They use different
percentage baselines and must not be compared as equal-denominator gains.

## Verification, visuals and evidence reuse

Ten host tests pass across `test_hybrid_five_level` and
`test_five_level_compatibility`. Coverage includes all 625 radix-5 row
values, mixed cell modes, attribute-only BRIGHT changes, malformed packets,
FLASH rejection, five shades in one cell, exact matching to the previous
phase-aligned patterns, and per-sample nonincreasing RGB error across all
128 non-FLASH attributes. Explicit mode changes do not alter native phase.
All measured packets and ZX0 blocks round trip, and both adaptive layouts
restore the uniform-five levels and canonical colour pairs exactly.

Reviewed [the comparison](hybrid_five_level_canonical_comparison.png),
frames 630, 2876 and 3886: original scaled RGB, four-code and adaptive-five
renderings. Additional intermediate tones are visible on the rabbit and
background, while the fine 2x2 texture and contour grid remain. Existing
palette limitations remain visible. These frames maximize the measured
benefit within each window, not a blind viewing study or full-motion test.

[The current report](hybrid_five_level_canonical_probe.json) includes
per-frame errors, byte counts, tool/source hashes and RGB identities.
The older uncommitted retained-palette report is preserved as
[historical evidence](hybrid_five_level_probe.json); all its three control
stream hashes and compressed sizes match the new run in every window.
Its source hashes precede the canonical-mode addition and are historical.

The [historical broader palette-search report](hybrid_five_level_search_probe.json)
is also preserved, but was not rerun. It used the same windows and temporal
attribute penalty. Four of 96 frames had greater RGB error than four-code
input; hybrid sizes were 26931, 21688 and 20050 bytes. Retaining the selected
colour pairs gives a simpler local error guarantee, so keep that policy.
No historical execution date is inferred from these files.

## Runtime limits and next milestone

These host controls omit FAP3 motion/Huffman/fragments, AY, native n-2 maps,
checkpoints, startup, disk padding and physical disk latency. They do not
establish disk count, independent boot, actual frame publication or EOF.
Existing player code is unchanged: **0 T delta**. No native five-level
consumer, RAM allocation or delivery timing is validated in this milestone.

Storage arithmetic only: a full uniform-five state is 3840 pattern bytes
+ 768 attributes = 4608 bytes, versus 3840 bytes for four-code storage.
Packed hybrid metadata would add 96 bytes per complete frame, or 192 bytes
for canonical modes; cell payload length varies from four to five bytes.
A random-access implementation may also need offsets or indexes. The
existing full-five expansion tables occupy 2048 bytes, versus 512 for the
old four-code tables. Additional quartet/phase tables and paging must be
included in a real RAM plan; none of these counts establishes playback fit.

**Next single deliverable:** implement and profile the selected adaptive
five-level native cell expansion with exact pattern equivalence, n-2 maps,
IRQ safety, RAM placement and instruction T-states. Use the measured
canonical stream as an alternative only if avoiding orientation work
justifies its extra bytes. Build TRDs after an integrated candidate exists;
retain the complete cold-boot/EOF release gate.

## Reproduce

Use the project's NumPy/Pillow environment with `PYTHONPATH=toolkit` and
the existing dependency directory if needed:

```text
python -m unittest toolkit.test_hybrid_five_level toolkit.test_five_level_compatibility
python toolkit/probe_hybrid_five_level.py --source <original.mov> --ffmpeg <ffmpeg.exe> --zx0 <zx0.exe> --cache .tmp/hybrid-five --output toolkit/hybrid_five_level_canonical_probe.json --preview toolkit/hybrid_five_level_canonical_comparison.png
```

[Codec prototype](hybrid_five_level.py), [probe](probe_hybrid_five_level.py),
[format tests](test_hybrid_five_level.py),
[pattern compatibility tests](test_five_level_compatibility.py).
