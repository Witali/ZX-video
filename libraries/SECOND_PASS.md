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

## Item15 — running pointers/address reuse

**Decision: running pointers already present; unconditional caching rejected.**
HL/DE already advance via INC/LDI/LDIR. A two-byte pointer reconstruction
probe costs34 T versus20 T for the existing running-pointer form. The
guard's HL+31 high-byte calculation costs22 T; storing/reloading its A in
a new state byte costs48 T on the first ready check (+26), verified over
2048 low/high states including overflow. Later loads would cost at least13 T.

Each new token changes HL/BC, invalidating a previous endpoint. A wait-only
cache needs explicit pointer/overflow/continuation ownership and must preserve
ReadToken reentry after new output targets/frontiers; it is not a free CSE
rewrite of the current ABI. This rejects the unconditional cache proposal,
not every possible future wait-cache design.

[2049 checks](evidence/trick_15.json),31 exact defaults; actual delta0 T/code/
state/input. `audit_second_pass.py --item 15 --output libraries/evidence/trick_15.json`.

## Item16 — adjacent streaming status clear

**Decision: optional measured candidate.** `word_state_init=True` / CLI
`--word-state-init` requires streaming. `input_needed` immediately precedes
`finished`; clear them with LD HL,0 / LD (input_needed),HL (10+16=26 T)
instead of XOR A / two absolute byte stores (4+13+13=30 T). The prefix
shrinks one byte (direct222 →221, CALL224 →223), state/stack/payload unchanged.
HL is overwritten by finish/input loads; SCF initializes the nibble cache
before its first use. The word store finishes before an IRQ can observe it;
no caller relies on the old intermediate byte-store state.

[Report](evidence/trick_16.json):95 full resident-input guarded blocks,
28415177 →28414797 T (−380), exactly−4 per block;252 accepted IRQs, zero
slower blocks/slices. Both partial-input modes pass42 full cases and six
placements: direct4365880 →4365712 T, CALL4368800 →4368632 T (−168 each),
identical waits/producers and167 once-only sectors. Native source/history
guards and short escaped words pass. Dirty prior finished/input_needed flags
are reset correctly. All14 library tests pass;31 defaults remain exact.

```text
python toolkit/test_streaming_lzsa2.py --direct-header --noncanonical --output .tmp/item16-direct-before.json
python toolkit/test_streaming_lzsa2.py --direct-header --noncanonical --word-state-init --output .tmp/item16-direct-after.json
python toolkit/test_streaming_lzsa2.py --noncanonical --output .tmp/item16-call-before.json
python toolkit/test_streaming_lzsa2.py --noncanonical --word-state-init --output .tmp/item16-call-after.json
python libraries/tests/measure_second_pass.py --item 16 --stream-directory .tmp --output libraries/evidence/trick_16.json
```
