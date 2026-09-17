# Project rules

- Store release disk images in Git LFS. When introducing another disk-image
  extension, add its LFS rule to `.gitattributes` before staging the image.
- For every change to the ZX Spectrum player hot path, count Z80 T-states
  from the instruction timing table. Compare the new path with the previous
  implementation and record both the absolute count and the difference.
- Optimize total frame delivery time, including packet decoding, memory
  writes, paging, and disk-sector acquisition. Do not trade fewer decoder
  T-states for enough extra sectors to reduce sustained playback speed.
- Separate deterministic player CPU T-states from TR-DOS ROM execution and
  physical disk latency; measure the latter in the emulator when it affects
  the producer/consumer schedule.
- Keep cycle calculations and their assumptions in build metadata or project
  documentation so that later optimizations can be checked against the same
  baseline.
