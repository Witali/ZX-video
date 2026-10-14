# Solid colours and source-defined character lines

2026-10-14, baseline `13819086`. The user requested a separate video encoder
with solid source-matched colours, no or extremely little dither, fewer cell
clashes and recognizable cartoon people. Subsequent steering asked for
computer vision. This is an optional host CB41 policy and bounded visual
comparison; the existing default, AY soundtrack and qualified disks remain.

## Usage

Add these options to the normal [public converter](../../GENERIC_CB41.md)
command, retaining its input/output, codec executables, ROM and verification
arguments:

```text
--video-codec cb41 --fps 10 --colour-policy flat
```

For source-defined lines that disappeared during solid colour fitting:

```text
--colour-policy flat --colour-contours
```

For a very small amount of dither restricted to source-detail cells:

```text
--colour-policy flat --colour-dither minimal
```

`--colour-vision regions` additionally tries mean-shift colour-region
guidance. It is experimental, with worse quiet-source variation in the saved
comparison, so do not assume it improves cartoon character recognition.
Contours/regions use OpenCV; direct flat/minimal add no CV operation. The
public converter retains its existing dependencies. The
options can be combined. They require CB41 and are incompatible with the
public monochrome switch. `stable` and `legacy` keep their earlier behaviour.

All modes retain the existing 128x96 logical grid, 256x192 native display,
256x144 active picture, static black bands and ordinary 4608-byte CB41 states.
This encoder does not introduce a full-resolution arbitrary-bitmap player.

## Method and limitations

Direct fitting evaluates the actual endpoints of all 56 legal canonical
normal/BRIGHT Spectrum colour pairs. RGB, opponent colour and encoded-RGB
luma errors guide the choice. A 35-degree opponent-colour cone rejects
misleading endpoint hues; neutral endpoints remain possible. Strong original
gradients inside a cell get additional weight. Three red/black spatial passes
coordinate palettes at source-smooth boundaries, within a per-cell target
score allowance of768. Exact representable source cells stay exact. Quiet
history can add at most64 to that score and is bypassed if any source
component in the cell changes by more than4. Frames are never blended.

With no dither only levels0/4 occur: every native2x2 sample is a solid fill.
Minimal dither allows at most one patterned sample per active8x8 cell, only
in source-detail cells and for a sufficient error reduction after charging
endpoint variance. No global error diffusion or changing dither phase is used.

OpenCV contours come from the original RGB, using3x3 sigma0.65 Gaussian
smoothing, multichannel Canny40/80 and connected components of at least4
samples. Shift the line to its darker source side. Paint only a strong
source line (adjacent RMS>=24) whose filled output retained less than half
its contrast. Use an existing **neutral** darker cell endpoint, keeping actual
palette/FLASH/border constraints; no new blue/red mouth lines are allowed.
This is deliberately stylized outlining and can increase RGB error/flicker.
It detects image structure, not semantic people or anatomical features.

Region guidance uses OpenCV mean shift(sp3, sr24, maxLevel0), connected
neighbour colours with RMS<=8, and original-RGB means for regions of at least8
samples. Target component pull is capped at12 codes. Strong source edges and
their one-sample neighbourhood are protected to preserve eyes/mouths. Regions
are not aligned to hardware cells. All masks are computed from the current
frame, independently of the old output.

Primary implementation references:
[OpenCV image filtering](https://docs.opencv.org/4.13.0/d4/d86/group__imgproc__filter.html),
[OpenCV Canny](https://docs.opencv.org/4.x/da/d22/tutorial_py_canny.html).
No neural model, person detector or semantic segmentation weights were used.

## Evidence

Six fixed16-frame windows start at9.0,14.4,25.2,28.8,49.6 and78.4 seconds
of the same prepared sea-foam source. Each new selector gets two context
frames. All96 measured frames are saved with exact original RGB and the
previous qualified native states in `states.npz`. These fixed difficult
windows include the boy's face, king close-up, wider multi-person scene and
dark interior. They are not the whole90-second movie.

- [Character comparison: original / existing / flat with CV contours](evidence/characters.png)
- [Silent9.6-second motion comparison, six separate windows](evidence/comparison.mp4)
- [All variants](evidence/all-variants.png)
- [Per-frame and aggregate measurements](evidence/report.json)
- [Exact packet/compression checks](evidence/packets.json)
- [Preserved initial trial](initial-trial/report.json)
- [Preserved coloured-contour trial](unbounded-contour-trial/report.json)

The first endpoint/soft-contour trial lost facial detail and created flat
areas; the mean-shift variant did not fix that. Its patterned-sample share
fell65.683% ->0%, but strong averaged-RGB gradient retention fell70.066%
->35.444% for the regions variant. Reject it as an improvement to the default.
The follow-up restores thin lost source lines and limits sparse dither to
detail cells, but revealed occasional coloured outlines. Preserve that full
trial; the final neutral-only guard removes this failure mechanism.

The reports separate actual native RGB error (including within-sample grain),
averaged logical RGB error, source-weighted artificial seams, gradient
retention and quiet-source residual variation. Lower native pixel MSE alone
does **not** establish better recognition: the old dither approximates far
more intermediate shades, while the flat picture can lose facial shading and
merge background/foreground. Neither gradient retention nor a contact-sheet
inspection is a semantic recognition score. User listening/audio work is
irrelevant to these silent previews; the soundtrack is unchanged.

Host screen and exact LZSA2 roundtrips check all selected window packets,
with matched two-screen baseline histories. Dictionary entries include
those histories. These are actual compressed window byte counts, not a
full-volume capacity estimate. Native player instructions are unchanged,
instruction delta0 T. Data-dependent work and sustained disk delivery remain
unmeasured; no new TRD or full Z80/Fuse timing qualification is claimed.

## Final measurements and decision

|96 fixed frames|Existing selector|Flat|Flat + CV contours|Minimal dither|
|---|---:|---:|---:|---:|
|Patterned logical samples|65.683%|0%|0%|1.094%|
|Averaged RGB MSE|534.998|3371.693|3641.166|3285.797|
|Actual native RGB MSE|8852.682|3371.693|3641.166|3386.428|
|Strong RGB gradient retention|70.066%|35.408%|44.246%|41.680%|
|Source-weighted boundary residual MSE|174.984|483.017|739.800|493.742|
|Quiet-source luma residual MSE|66.622|110.218|175.448|114.204|
|Actual LZSA2 window bytes|69993|37385|46261|47170|
|Maximum rows, including two baseline histories|242|147|147|201|

The final contour version recovers more strong source lines than unoutlined
flat output, with no within-sample grain. Inspected boy/king/wider-person
frames reveal eyes, mouth and beard lines absent from simple flat fills.
Facial shading and substantial scene detail still remain weaker than in the
old quantizer. Keep all new variants **optional**, choose the neutral-contour
version for the audition, and do not promote any to the default. Mean-shift
regions reduce flat boundary residual483.017 ->454.522, but quiet variation
110.218 ->240.080 worsens; adding contours further increases it to301.594.
Automatic region guidance is not justified by this evidence. Do not claim
that neural/person segmentation was tested or that attribute clash is solved.

The43-test integration suite passes, and the final8 flat-specific contracts
pass after matching CLI/API option validation.36 final packet windows and
all576 host reference screens roundtrip exactly through CB41/LZSA2; the
same36-window checks for each preserved earlier trial also pass. The final
MP4 is768x168,96 frames at10 fps,9.6 seconds, independently read with FFprobe.
No complete native player run was required or claimed for this host prototype.

## Reproduce

Use NumPy, Pillow, and OpenCV in the existing Python environment:

```text
python -m unittest toolkit.test_flat_colour toolkit.test_texture_colour toolkit.test_stable_colour toolkit.test_generic_cell_codebook toolkit.test_generic_converter
python toolkit/analysis/flat_colour/probe.py --baseline toolkit/analysis/attribute_pattern/evidence-full-disk --output NEW_EMPTY_DIRECTORY --selected contours --ffmpeg PATH_TO_FFMPEG
python toolkit/analysis/flat_colour/measure_packets.py NEW_EMPTY_DIRECTORY --baseline toolkit/analysis/attribute_pattern/evidence-full-disk --lzsa PATH_TO_LZSA
```

The source and qualified baseline arrays are authenticated by the report's
SHA256 values. For old trials, use their exact saved producer sources, rather
than silently running the final selector. Artifact manifests pin producer and
output hashes. The MP4 is a host native-screen reference at10 fps, not a Fuse
recording or a timing test. Existing releases stay independently qualified.
