# Additional Spectrum artwork proposals

Prepared 2026-11-02 from actual Clair Obscur: Expedition 33 screenshots using
the built-in ImageGen tool. These are **three final proposals**, not a
qualified player/TRD release. RAM capacity, decompression and playback timing
remain the integrating player's responsibility. No target instructions
changed here; CPU T-state delta is 0.

| Screen | Composition and recognition | Border |
| --- | --- | ---: |
| `paintress.scr` | Colossal white-haired Paintress, Monolith 33 and gold halo over the sea; tiny foreground expedition silhouettes emphasize scale. | 0, black |
| `sirene.scr` | Engraved hollow mask, black hair and ribbon arcs, with a wide receding stage/cavern and small dancers. | 0, black |
| `gestral-village.scr` | Crimson ground, plank path, elevated bridge, giant brush posts, stalls and small brush-headed Gestrals. | 6, yellow |

Each screen is 256×192 and exactly 6912 bytes. Every hardware attribute cell
uses a legal pair from its scene's restricted Spectrum palette, with one
shared brightness and no FLASH. `*-native.png` is the exact decoded screen;
`*-preview.png` enlarges it 3× with nearest pixels. The chosen border is a
separate normal Spectrum color and is not baked into the 256×192 screen.
The village's yellow border follows its warm sky/opening; the automatic
global-luminance candidate was black and remains recorded in `compiled.json`.

The bottom 32 rows reuse the **exact shared Cinzel wordmark bitmap** supplied
by the main artwork set. Its shape, size and placement are identical; only
the second line's ink changes by scene. `wordmark-mask.json` is pinned by
SHA256 `9f4a0ad758a08d59bc253778e8d93e8556cf64d78d095f88d33520576d955ab0`.
There is no local font lookup or fallback in this proposal compiler.

The first Sirene generation was a closer upper-body portrait. It was
superseded after the request for more environment variety. The wider final
is `sources/sirene.png`; `sources/sirene-study.png` is retained only as an
intermediate final-edit reference and does not enter the three-screen list.
Exact prompts, source hashes and reference URLs are in `provenance.json`.
No downloaded third-party reference screenshot is distributed here.
Project source copies exclude nonvisual generated `caBX` metadata; all PNG
IDAT pixel streams remain byte-exact. Original and publishable hashes are
recorded in `source-sanitization.json`; untouched originals remain local.

## Reproduction

The compiler is a self-contained copy of the main artwork compiler's PNG
and attribute-pair logic, adapted to these three scenes and the existing
shared wordmark mask. Node.js built-ins suffice:

```powershell
node music-menu/artwork/proposals/compile.mjs
python music-menu/artwork/proposals/verify.py
```

Verification additionally requires Pillow. Its PNG reader is independent
of the compiler's PNG implementation. The saved `verification.json` checks
all 147,456 native pixels, 1,327,104 enlarged pixels and 2304 attribute cells,
all three source/screen hashes, and every shared footer bitmap byte.

Visual inspection of all three native previews confirms the main silhouettes
survive reduction. Fine mask/coat ornament is deliberately simplified and
some local colors are reassigned at attribute boundaries. This is not
physical display, emulator or transition-effect verification.
