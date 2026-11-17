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

Initial probe: neither fixed palettes nor alternatives that preserve
the other three tiles permit a two-sided edit on the longest remaining
seams of `226033.jpg` (68 pixels), `rocket.jpg` (32 pixels), or
`clic-3510902dc65b` (16 pixels). One rocket segment permits a one-sided
edit. Continue with a joint search that can refit all four tiles on
each side, using the same protected-pixel and pooled-error checks.

## 3. Improve interior shading and train from the accepted repairs

- Preserve weak folds, gaps and highlights by shaping the dot pattern
  inside the source silhouette. Check translucent subjects, white
  clothes, faces and saturated objects on different photos.
- Use the accepted legal renders as additional palette-ranking targets
  and compare another 64-channel training run against the first stage.
  Keep the existing 88-image regression set and disjoint new photos
  for the final quality check. Record each stage in the project changelog.
