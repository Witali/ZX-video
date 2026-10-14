# Experimental native-pixel source-line drawing

2026-10-14. The user requests the current line-art style at actual 256 x 192
pixel precision, permits the existing vertical crop, rejects extra outlines
around thin strokes, and reports unreadable faces/title lettering in the first
native preview. This finite format experiment does not restart the paused
broader accuracy goal.

## Current result and release limitation

The source is sampled directly at 256 x 144 and placed at y24..167 of a standard
6912-byte Spectrum screen. The original aspect ratio is contained, without
cropping. Every bitmap pixel is independent; this is not an expansion of the
old 128 x 72 samples. Hardware attribute cells still permit two colours each.
No additional dithering is used.

The revised detector filters analogue grain before tracing, paints the core
of narrow source strokes instead of both edges, preserves their colour, and
keeps white lettering/highlights when a neighbouring source shadow supplies
contrast. The original RGB remains untouched for fill selection and error
feedback. The selected readability review uses bilateral diameter5,
colour sigma20/space sigma1.2, fine Canny30/60, coarse40/80, stroke contrast32,
core fraction0.5 and maximum nearby ink fraction0.01 for bright-stroke inversion.
Native source-close solid fills retain the existing dark-region rollback.

- [Corrected title/faces against the rejected noisy native preview](evidence/detail-comparison.png)
- [Original / previous coarse drawing / corrected native drawing](evidence/comparison.png)
- [30-second nominal-cadence preview with unchanged AY simulation](evidence/native-preview.mp4)
- [Full original/coarse/native comparison](evidence/accuracy-comparison.mp4)
- [Experimental TRD](../../../ZX-video-sea-foam-native-lineart-experimental.trd)
- [Complete experiment results](evidence/experiment.json), [all nominal misses](evidence/timing.json)
- [Full native byte comparison](evidence/work/ZX-video-sea-foam-native-lineart_part01/screens.json)

**The TRD is experimental and fails the release timing requirement.**
All300 frames/2,073,600 screen bytes match in complete Fuse runs. Independent
dirty-RAM cold boot passes. All1500 original AY controls remain exact at50 Hz,
with no missing audio fields or underruns. However165 nominal deadlines are
missed, from frame135 through299; the run does not recover. Maximum actual
deviation is37,084,884 T /523 fields /10.46 seconds. The one-field fallback also
fails. Actual first-to-last publication spans40.36 seconds, versus the nominal
29.9-second span. The MP4s render the reference screens at nominal10 fps and
must not be mistaken for recordings of TRD playback cadence.

The disk uses1488 of2544 data sectors, leaving1056 free. The final raw CB47
stream is557,176 bytes; its LZSA2 stream is369,251 bytes. Full runtime delivery
checks1443 physical reads. Size fit is not a sustained-delivery pass.

Active native RGB MSE against the directly decoded source is6522.985329 for
the prior coarse drawing,6054.531982 for the rejected noisy native image and
5070.659015 for the readability revision. This is an RGB measure for a
stylised drawing, not a semantic-recognition score. The coarse fit is centred
one native pixel differently because of rounding at its lower source sampling
rate. Inspect the title and people as well as these aggregate values.

## CB47 and memory

CB47 stores a256-entry book of eight actual row bytes per8 x 8 cell. Each
frame has two72-byte change masks, two-bit modes, cell data and attributes.
Mode0 writes eight literal bytes; mode1 copies a book entry; mode2 copies the
same cell from the front screen; mode3 changes one selected row0..7 using its
actual byte. The maximum payload is5472 bytes. No mutable row-update packet or
radix-five interpretation is used.

All eight128-KiB RAM banks are accounted for in per-volume metadata: screens5/7,
four video slots0/1/3/4, immutable AY6, and the fixed kernel/IRQ/stacks in2.
The book uses2048 bytes and popcounts256 bytes. The inherited512-byte row-table
allocation remains reserved and unused. Retained bank-5 AY/producer helpers
start at7800h. CB47's packet buffer is6200h..7760h, after the6100h..61FFh disk
relay, with160 bytes before those helpers. The old6400h start was unsafe for
native maximum packets and was corrected before the final full run.

| Counted path body | CB46 | CB47 | Delta |
| --- | ---: | ---: | ---: |
| Literal cell |231 T|188 T|-43 T|
| Single-row update |93 T|53 T|-40 T|
| Ordinary packet row-control dispatch |18 T|0 T|-18 T|

Body counts exclude unchanged mode dispatch, cell return, masks, paging,
interrupts, contention and disk service. Dictionary/front-copy instructions
are unchanged. No single constant describes total frame-delivery cost.
Actual elapsed ROM/disk/IRQ/ULA service is measured separately in Fuse.
The author LZSA2 encoder uses `-r -f 2 -m 5` for this native prototype; its
default ratio-first parse and a dense-raster alternative both missed deadlines.

26 component/regression tests pass, including one-/two-pixel horizontal and
vertical strokes, coloured strokes, narrow white gaps, all eight native rows,
both screen banks, maximum packets and interrupt-safe writes. Six existing
renderer variants are byte-identical to `bd01d761`; old formats/defaults remain
available. This evidence does not qualify untested inputs or multiple volumes.

## Preserved attempts and reproduction

[Attempts](evidence/attempts/) retain the failed RGB preprocessing, format gates,
superseded image reviews and data/player experiments:

1. Separately converting the source YUV to BGR for an FFV1 clip rounded differently
   from the canonical RGB extraction. Materializing the already decoded RGB fixed
   the mismatch; every source byte is subsequently checked.
2. The retained AY and streaming installers initially accepted CB46 only. CB47
   removes the row-control queue call, so complete relocation requires three
   packet takes rather than four; the AY phase reference is still checked.
3. Unfiltered narrow-ridge tracing and weak Canny thresholds made faces/letters
   noisy. Two bounded four-frame reviews preserve both the rejected result and
   the source-coherent core/bright-stroke correction selected after user feedback.
4. The initial cell-only stream fully reproduced300 screens/AY but missed170
   nominal deadlines, reaching681 late fields. It is not a release.
5. Dense raster packets measured122,020 T per complete active-screen copy;
   setup31, raster rows109,847 and attributes12,142 T. The first integrated run
   overwrote retained7800h helpers and was interrupted after partial execution.
   Moving the buffer to6200h corrected that memory error. The subsequent complete
   readable raster run still missed184 deadlines, reaching1116 fields, and was
   rejected. Generated code/streams are authoritative; prototype source copies
   were captured at retirement and include intervening threshold changes.
6. The author CLI rejects combining `--prefer-speed` and `-m 5`. The selected
   cell-only `-m 5` run preserves every image/audio byte and improves delivery
   over the raster attempt, but still fails both timing gates as reported above.

The [archive manifest](evidence/archive-manifest.json) hashes181 saved files
(101,390,532 bytes before the manifest itself): exact RGB/reference screens,
prefix source clip, AY controls/model WAV, generated metadata, full traces,
comparisons, source copies and failed attempts. Disk images/media use Git LFS.

`build_test.py` reproduces the exact original prefix with the continuous AY
fit, verifies every extracted RGB byte and runs complete cold/Fuse checks.
`--image-cache` is optional and requires identical source RGB and parameters.
`preview.py` and `compare.py` require explicit `--experimental` when the timing
gate fails. `archive_test.py` preserves a completed run without promoting it
to a release. The original full-source video and continuous fit paths are in
the saved source/audio reports; the archive also retains the exact tested
prefix inputs. Sustained native10-fps delivery remains unresolved.
