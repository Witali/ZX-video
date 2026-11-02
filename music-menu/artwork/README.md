# Expedition 33 native artwork

Fourteen original generated illustrations, inspired by the game's official
screenshots and character artwork, compiled to actual ZX Spectrum screens.
These are interpretations, not lossless ports of game screenshots. The first
image is the Lumiere city loading screen. The current set also includes the
expedition, a duel, Lune, the guardian, an underwater landscape, Gustave, a
crystal titan, Monoco, Esquie, Renoir, the Lampmaster, Visages and Maelle.

The reference review covered all ten screenshots on the
[official publisher page](https://www.kepler-interactive.com/games/clair-obscur-expedition-33),
the [official media gallery](https://www.expedition33.com/media), and the
[official character page](https://www.expedition33.com/overview/characters).
Monoco, Esquie, Renoir and Maelle used the official character silhouettes;
the flying Esquie composition also used the official overworld images.
Additional boss references were the
[Lampmaster](https://image.thenerdstash.com/2025/04/Clair-Obscur-Expedition-33-Lampmaster.jpg)
and [Visages](https://www.alucare.fr/wp-content/uploads/2025/05/www.alucare.fr-clair-obscur-expedition-33-guide-des-differents-boss-Clair-Obscur-Fight-Visages.jpg).
Downloaded reference images are not redistributed. `prompts.json` records the
generation instructions. Sanitized generated sources retain their exact pixels.

Each `.scr` is 6912 bytes: 6144 bitmap bytes in Spectrum raster order and 768
attributes. Illustrations occupy 256x160; the remaining 32 rows use one shared
Cinzel title mask. Every aligned 8x8 cell has two legal colors with one common
BRIGHT bit, and FLASH is disabled. Borders are separate 3-bit hardware colors.
The `-native.png` files are independently verified 256x192 renders; previews
are exact nearest-neighbor 3x enlargements. See [QA.md](QA.md) for measured
coverage and the limits of the conversion.

Rebuild with Node.js in this directory:

```text
npm ci
node compile.mjs
python verify_native.py
```

The pinned font is licensed under the SIL Open Font License in `font/`.
The artwork is not an endorsement by the game's creators. Player timing,
resident memory allocation and disk qualification are separate from this
asset-only change; this change modifies no target CPU path (0 T delta).
