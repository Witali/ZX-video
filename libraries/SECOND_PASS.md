# Sequential second optimization pass

Authorized 2026-10-14: work through checklist items10–29, prioritize speed
then code size, verify each complete experiment and commit it separately.
Branch `codex/z80-codec-tricks`, initial baseline `3f34a4a4`.
Existing defaults, standard formats and upstream resources remain protected.
Optional candidates do not qualify a movie/player release.

## Item10 — nearby ordinary LZSA2 literal helper

**Decision: optional measured candidate.** Use
`build(long_copy=True, near_literals=True, core_limit=0x9000)` or
`--long-copy --near-literals --core-limit 0x9000`. It requires ordinary input;
streaming layouts keep their existing helper and guards.

Move the existing 41-byte literal kernel before `start`. `ManyLiterals`
can now JR directly to it. The original trampoline's JP10/three bytes are
removed, with no added branch. `begin` still jumps directly to `start`.
The word path keeps JR's untaken7 T; match/short paths are unchanged.

From `ManyLiterals` through `AfterLongLiterals`, an eligible count n=18..255
costs `21*n−18` before and `21*n−28` after (360 →350 T at n=18).
The optional core falls337 →334 bytes, no extra state/buffer/stack/payload.
Relative to the ordinary default, the whole long-copy profile now adds84
core bytes, saves60 T per byte-form literal and59 T per byte-form match.
Raw exported region rounding stays three sectors, versus two for the default;
actual boot packing/delivery remains unmeasured.

[Native report](evidence/trick_10.json):95 complete blocks/619480 raw bytes,
26297662 →26292702 T (−4960) versus the previous optional profile; real21
blocks save1690 T. Zero slower blocks/slices;230 accepted synthetic IRQs.
Short escaped-word cases have delta0. Both original and relocated layouts
pass directed length/overlap/word checks. All13 library tests pass, including
all31 exact default layouts and unchanged streaming guard tests.

```text
python libraries/tests/measure_second_pass.py --item 10 --output libraries/evidence/trick_10.json
python -m unittest discover -s libraries/tests -v
```
