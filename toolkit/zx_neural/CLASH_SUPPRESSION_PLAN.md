# ZX Spectrum clash suppression

Use `2f1065b7` as the baseline. Compare decoded 6912-byte SCRs at the same
framing. The previous DIV2K fine-tune improved the palette teacher's
validation loss but added large false attribute steps on 14 of 100
evaluation images. The final decoded screen is the acceptance target.

## 1. Learn to repair the finished screen

- Locate large color or brightness steps on 8×8 borders where adjacent
  4×4 source means change little. Measure their count and the length of
  consecutive segments along the same border.
- For each affected cell, evaluate legal ink, paper and BRIGHT pairs.
  Fit the 4×4 dot counts against its neighbors and preserve pixels on
  strong source edges, source-supported color accents and subject
  boundaries. Use Floyd–Steinberg to place the selected dots.
- Train a 64-channel FP32 model to shortlist the verified candidates. Use
  separate DIV2K photos for training, checkpoint selection and final
  testing. Generate the targets from screened candidate colors, including
  their exact pooled color after dot quantization.
- Compare the learned shortlist with the existing converter and an
  equally sized color-fit shortlist. Reject new severe borders, worse
  pooled color or seam error, and changes on protected strong edges.
  Verify independent SCR decoding and show source, before and after
  for representative successes and any visual trade-offs.

Status: implemented and checked on 188 screens in the
[first experiment](evidence/learned-clash-suppression.json). Large false
steps drop from 11,146 to 3,828. The same five-candidate search with the
color-fit ranking leaves 4,335. Native pixel error rises with the new
halftones. The option is available through `--clash-model`.

## 2. Repair boundaries that need joint changes

- Inspect remaining seams in water, sky, shadow gradients and pale
  materials. Try simultaneous palette or density changes on the two
  sides of an affected border, then neighboring cells where needed.
- Keep the same safeguards and measure the extra host runtime. Add
  support only where a single-cell repair leaves a visible grid.

Status: implemented and checked on 188 screens in the
[joint-search replay](evidence/joint-clash-suppression.json). The initial
four-pixel-only search could not move both sides of the focused runs.
The whole-cell search reduces large false steps from 3,828 to 3,104.
Fitting the neighbors along longer runs reduces them further to 2,907.
The runners' original 68-pixel run disappears and a 32-pixel run
remains elsewhere. The rocket and jellyfish longest runs also shorten.
Native pixel error and extra host runtime are recorded in the replay.

The follow-up [contrast replay](evidence/clash-contrast-and-details.json)
penalizes false step contrast with a fourth-power cost and searches
the strongest remaining joins first. Strong steps of at least 96 RGB
levels fall from 495 to 229, with no new large false steps.

## 3. Improve interior shading and train from the accepted repairs

- Preserve weak folds, gaps and highlights by shaping the dot pattern
  inside the source silhouette. Check translucent subjects, white
  clothes, faces and saturated objects on different photos.
- Use the accepted legal renders as additional palette-ranking targets
  and compare another 64-channel training run against the first stage.
  Keep the existing 88-image regression set and disjoint new photos
  for the final quality check. Record each stage in the project changelog.

Interior shading is implemented and checked on the same 188 decoded
screens. The [contrast and detail replay](evidence/clash-contrast-and-details.json)
shows a decrease in weak-edge error. Attribute bytes and all 4×4
average colors stay exact through the dot exchanges. Direct CLI
comparisons cover white clothes, translucent jellyfish, a face and a
still life with saturated colors.

The [joint-target training experiment](evidence/clash-joint-training.json)
adds 113 labels on the 100 training photos and 16 on the separate
12 validation photos. The second FP32 checkpoint fits the corrected
palettes more closely, while the final contrast-aware renderer adds
12 severe positions and increases the total contrast penalty. The
188-screen comparison covers the 88 previous images in both modes
and the 12 disjoint DIV2K holdouts in pixel-art mode. The first
checkpoint remains bundled. The trained correction, joint search,
contrast penalty and interior detail pass are available through
`--clash-model`.
