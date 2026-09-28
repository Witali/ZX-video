# Optional Z80 phase-aligned cell renderer

Measured 2026-09-28. This implements the [host correction](DITHER_PHASE.md)
as actual Z80 instructions in `cell_screen_z80.build(phase_aligned=True)`.
It keeps endpoint colours, BRIGHT and compact values; FLASH is unsupported.
It is an isolated optional renderer, **not enabled in disk builders**.

## Implementation and timing

At each band, derive the compact attribute page from screen D. Sparse cells
look up whether INK is darker than PAPER and select normal or reversed
table-page traversal. Both Gray-order paths preserve pixel addresses and
the caller's mask in AF'. Dense bands prepare 32 page operands and 32
INC/DEC opcodes once, then reuse them for four compact rows. The 65 writable
code bytes are explicitly guarded; other code writes fail the native test.

T-states follow the instruction listing and the Z80 timing table referenced
in [the report](phase_renderer_audit.json). IRQ/ULA/TR-DOS/drive time is
excluded. All executed instructions are independently checked in the CPU
harness, including both LDIR outcomes and branches.

| Path | Previous | Aligned | Delta |
| --- | ---: | ---: | ---: |
| Map copy, 80 bytes, including setup | 1300 | 1695 | +395 |
| Per-band phase setup | 0 | 43 | +43 |
| Sparse Gray cell body, including RET | 254 | 315 | +61 |
| Dense phase preparation, including CALL | 0 | 2172 | +2172 |
| Dense pixel byte, including increments | 51 | 58 | +7 |
| Dense preparation + 128 pixel bytes | 6528 | 9596 | +3068 |

The same-map addition is `395 + 43*bands + 61*sparse_cells + 3068*dense_bands`.
The map-copy LDIR frees 158 main-code bytes. With current output options,
main code/state is **843→824 bytes** (-19); extra lookup **128 bytes** at
9880..98FF and helper **490 bytes** at F900..FAE9, total net **+599 bytes**.
Main code ends at 9338, below the attribute controller at 9360. F900 conflicts
with the optional resumable packet experiment; integrated RAM placement and
cold relocation have **not** been validated, so these options must not be
combined merely by loading the extra regions.

## Evidence and decision

- Exhaustive native coverage of all **128 non-FLASH attributes × 256 packed
  byte values**, both screen banks, sparse orientation-only changes and
  clearing against n-2. Actual AY interrupts inserted after every executed
  instruction preserve registers, alternate registers, paging and stack.
- Fifteen renderer/phase regression tests pass. Legacy default bytes still
  match the saved baseline. The phase option rejects incompatible options.
- **96 movie frames** in three 32-frame windows plus six carried seed frames
  match the aligned native-byte reference exactly. This is not full playback.
- Updating the actual FAP3 native maps changes **251 bytes on 108 frames**;
  packet lengths, colour attributes, Huffman values, motion and AY remain
  intact. Old maps are checked against old native pixels before modification.
- Optimal ZX0 window sizes, including four-byte block headers:
  **27191→27191**, **41794→41794**, **26684→26677**. All blocks round-trip.
  Window boundaries differ from production blocks; no whole-disk saving claim.
- Across all 4221 frame masks, the isolated 18-band/full-active-attribute
  formula gives **370074484→467859829 T**, **+97785345 T** (about +26.4%).
  Maximum **137426→193819 T**. This estimate excludes the existing attribute
  group savings, atomic-page helper, external calls, IRQ/ULA and disk time.
  Both sides use the same stated baseline; the formula is not full-player
  timing and cannot establish frame deadlines.

**Keep this as a correctness/cost baseline, do not enable it by default.**
The storage impact is small but the CPU overhead is material for the
already failing cadence. Compare it with the requested adaptive five-level
consumer and cheaper precomputed phase selection before integration.
No TRD images were generated or changed. Complete EOF validation remains
required for any final selected implementation.

```powershell
python -m unittest toolkit.test_phase_renderer toolkit.test_cell_screen toolkit.test_dither_phase
python toolkit/audit_phase_renderer.py `
  --states .worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz `
  --raw .worktree/volume-huffman/.tmp/probe/volume-1.raw `
  --output toolkit/phase_renderer_audit.json `
  --zx0 .worktree/audio-fidelity/.tmp/bin/zx0.exe `
  --cache .tmp/phase-renderer-zx0
```
