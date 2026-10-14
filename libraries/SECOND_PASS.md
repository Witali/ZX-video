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

## Item11 — repeated loads across independent instructions

**Decision: retain efficient reloads/live saves.** LZSA2's nibble refill reads
the same input byte twice across EX AF,AF'. BC holds a live token/count;
DE/HL remain output/input pointers. Caching in B while preserving BC gives
the identical full register/flag result but costs51 →73 T (+22) across the
refill fragment. Two4-T register transfers already exceed the second7-T
read; safe PUSH/POP adds21 T.512 byte/carry cases pass.

The analogous saved paging-value probe costs33 →41 T (+8): retaining A on
the stack costs21 T versus a13-T reload. Ring copying rewrites main scratch
pairs; HL' belongs to the clock. Offset/target values already use patched
operands. Evaluate the distinct `sync` target restore in item20.

[513 native checks](evidence/trick_11.json),31 exact default profiles;
actual decoder delta0 T/code/state/input. No rewrite, no new full-codec run.
Reproduce with `audit_second_pass.py --item 11 --output libraries/evidence/trick_11.json`.

## Item12 — direct known-address access

**Decision: already present for fixed state.**256 native byte probes verify
17 →13 T for LD HL,nn / LD A,(HL) →LD A,(nn) when HL is dead. The decoder's
fixed state uses direct forms already. Its core HL is a live dynamic input/
history pointer: a directed subsequent INC HL reaches6005 before the rewrite
but5001 afterwards. With HL already established, LD A,(HL)7 T beats a fixed
absolute read13 T by6 T. The indexed ring table belongs to item06.

[258 checks](evidence/trick_12.json),31 exact defaults; actual delta0 T/code/
state/input. Reproduce with `audit_second_pass.py --item 12 --output libraries/evidence/trick_12.json`.

## Item13 — in-place memory arithmetic

**Decision: no eligible indexed state RMW.** The46 →23-T indexed primitive
has no matching state sequence in the adapted decoders. Their shifts consume
compressed input into A/the reservoir, rather than update a memory counter.
256 probes compare LD A,(HL)/SRL A15 T against SRL (HL)15 T: the latter has
no speed gain, leaves A unchanged and alters255 of256 possible input bytes.
That violates immutable input/shared-nibble ownership.

[Report](evidence/trick_13.json),31 exact defaults; actual delta0 T/code/state/
input. `audit_second_pass.py --item 13 --output libraries/evidence/trick_13.json`.

## Item14 — rotate/mask decomposition and narrower shifts

**Decision: retain existing fast paths; reject unproved narrowing.**256
native high-nibble values confirm current four RRCA +OR F0 costs23 T with
the same final AF as four SRL +OR F0 at39 T (+16). A memory nibble rotation
would instead mutate the compressed input. ZX0 already uses ADD A,A/RLA,
short-offset paths and short-gamma paths; longer gamma values need B.
Omitting RL B from the word shift loses the high byte in256 of512 directed
low-byte/carry states. Item23 separately evaluates more bit-phase expansion.

[768 native checks](evidence/trick_14.json),31 exact defaults; actual delta0
T/code/state/input. `audit_second_pass.py --item 14 --output libraries/evidence/trick_14.json`.
