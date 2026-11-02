# Native artwork audit

Independent review performed on 2026-11-02 for the fourteen approved images
listed in `compiled.json`. No image, crop, SCR, title mask, native preview or
enlarged preview was changed by this audit. Player and TRD qualification are
separate; the target CPU instruction change is 0 T.

## Source metadata

`sanitize_sources.py` excludes nonvisual PNG metadata and saves the untouched
generated files under the ignored task-local `.tmp/artwork-originals` folder.
It does not print metadata contents. The fourteen sources contained caBX
metadata; 324,232 metadata bytes were excluded. Every IDAT payload is byte
identical. Pillow also compared all 22,015,392 decoded source pixels before
and after, including image mode and dimensions, with exact equality.

`source-sanitization.json` records original/source hashes, IDAT hashes and
decoded-pixel hashes. `compiled.json` source hashes now identify the sanitized
project copies. Existing SCR hashes are unchanged. Raw downloaded references
and untouched generated originals remain local.

## Native validation

`verify_native.py` independently decodes Spectrum screen addressing and
attributes rather than importing the compiler. It checks:

- Fourteen exact 6912-byte SCR hashes and valid separate border values.
- 688,128 decoded native pixels against the 256×192 PNGs.
- 6,193,152 enlarged pixels against an exact nearest-neighbor 3× enlargement.
- 10,752 aligned attribute cells, at most two colors with common brightness,
  and no FLASH.
- Every bitmap byte of all fourteen 32-row footers against the same mask;
  black paper, white first-line ink and nonzero scene accent on the second.
- Sanitized source and decoded-pixel hashes, with no retained nonvisual
  metadata chunks.

All checks pass. `verification.json` saves per-image results. The shared mask
SHA256 is `9f4a0ad758a08d59bc253778e8d93e8556cf64d78d095f88d33520576d955ab0`,
also matching the three additional artwork proposals.

## Visual observations

All fourteen actual native PNGs were inspected in sharp 2× contact sheets.
Large scene and character silhouettes remain readable; the common title has
identical shape, size and placement. The city, luminous tree, crystal titan,
Monoco, Esquie, Lampmaster and Visages retain distinct compositions. The Maelle
and Renoir faces keep clear black/white contours. Fine clothing and background
ornament are intentionally simplified by the hardware conversion.

The Gustave portrait has visible red/yellow attribute steps around its facial
highlights, and small decorative details elsewhere occasionally meet an 8×8
color boundary. These are legal, limited conversion artifacts, not displaced
raster rows. Dark blue details in Renoir and the underwater scene have lower
contrast on dark displays. No approved pixels were repainted or recolored.
This audit does not assert screenshot-perfect character likeness, physical
monitor appearance, emulator presentation or slideshow timing.

## Reproduction

Python 3 with Pillow is required. Run from the repository root:

```powershell
python music-menu/artwork/sanitize_sources.py
python music-menu/artwork/verify_native.py
```

Sanitization is idempotent; its saved original/pixel proof is retained on a
subsequent run. Native verification can be rerun without changing image data.
