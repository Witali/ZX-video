# Local solid/pattern transitions

This follow-up to `db07319e` addresses visible8x8 solid/pattern rectangles
without adding grain over the whole image. The selected source remains the
same507 RGB frames,50.7 seconds at10 fps, and2535 existing50-Hz AY fields.
The original and previous qualified disks remain in the sea-foam archives.

`texture_colour.py` starts with the previous nearest-level source/physical
bounded selector. A20-degree cone in(R-G,B-G) rejects misleading tint, such
as source orange turning into saturated red. Neutral output is a fallback;
exact Spectrum colours and genuine source contours remain eligible.
This is a defined RGB diagnostic, not a perceptual hue model.

At a gray solid/pattern attribute boundary, both source sides must have RMS
contrast at most8 and output contrast at most40. A band of two logical
samples(four native pixels) on each side gradually introduces sparse dots
or fractional source brightness. A solid sample's target pull is at most8
luma codes, halved one sample farther away. Outside that band the established
2x2 levels stay unchanged. Fractional samples use a screen-anchored phase that
stays fixed in time. True source edges are excluded rather than blurred.
These local samples may exceed the older sample-level physical/RGB bound:
reports explicitly identify the scope and measure their actual errors.

The whole-image density draft in [rejected-density](rejected-density/) improved
cell-mean error and some solid/pattern counts, but visibly reduced clarity and
added grain. The user rejected it. Its source, probe, quality and interrupted
conversion record are preserved. No full native/Fuse qualification was reached.
The initially permissive chroma ratio4 also produced false yellow/red patches;
ratio2 reduced these but did not cure the grain. Do not reuse it as the default.

The native format, lookup phase, resolution, source preparation, audio and
player instructions are unchanged, instruction delta0 T. Data-dependent
decoding, disk traffic and actual publication timing still require a complete
new qualification. Real hardware has not been tested. Spectrum's two colours
per cell can retain visible restrictions; this correction does not promise
perfect gradients or full source gamut.

Reproduce the small probe with `probe.py --baseline` pointing to the previous
materialized `toolkit/analysis/sea_foam/evidence-colour`, and `--output` to a
new directory. Build the same cached source with the existing sea-foam
`build_prefix.py` and its documented executable/cache arguments. Use a fresh
output path: it must not replace the old independently qualified archive.
Then run `compare.py BUILD --baseline PREVIOUS --ffmpeg FFMPEG` for every-frame
metrics and synchronized source/previous/new native-reference video.
`archive.py` requires full cold-Fuse qualification before publishing evidence.
