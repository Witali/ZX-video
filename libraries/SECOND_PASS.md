# Sequential second optimization pass

Authorized 2026-10-14: work through checklist items10â€“29, prioritize speed
then code size, verify each complete experiment and commit it separately.
Branch `codex/z80-codec-tricks`, initial baseline `3f34a4a4`.
Existing defaults, standard formats and upstream resources remain protected.
Optional candidates do not qualify a movie/player release.

## Item10 â€” nearby ordinary LZSA2 literal helper

**Decision: optional measured candidate.** Use
`build(long_copy=True, near_literals=True, core_limit=0x9000)` or
`--long-copy --near-literals --core-limit 0x9000`. It requires ordinary input;
streaming layouts keep their existing helper and guards.

Move the existing 41-byte literal kernel before `start`. `ManyLiterals`
can now JR directly to it. The original trampoline's JP10/three bytes are
removed, with no added branch. `begin` still jumps directly to `start`.
The word path keeps JR's untaken7 T; match/short paths are unchanged.

From `ManyLiterals` through `AfterLongLiterals`, an eligible count n=18..255
costs `21*nâˆ’18` before and `21*nâˆ’28` after (360 â†’350 T at n=18).
The optional core falls337 â†’334 bytes, no extra state/buffer/stack/payload.
Relative to the ordinary default, the whole long-copy profile now adds84
core bytes, saves60 T per byte-form literal and59 T per byte-form match.
Raw exported region rounding stays three sectors, versus two for the default;
actual boot packing/delivery remains unmeasured.

[Native report](evidence/trick_10.json):95 complete blocks/619480 raw bytes,
26297662 â†’26292702 T (âˆ’4960) versus the previous optional profile; real21
blocks save1690 T. Zero slower blocks/slices;230 accepted synthetic IRQs.
Short escaped-word cases have delta0. Both original and relocated layouts
pass directed length/overlap/word checks. All13 library tests pass, including
all31 exact default layouts and unchanged streaming guard tests.

```text
python libraries/tests/measure_second_pass.py --item 10 --output libraries/evidence/trick_10.json
python -m unittest discover -s libraries/tests -v
```

## Item11 â€” repeated loads across independent instructions

**Decision: retain efficient reloads/live saves.** LZSA2's nibble refill reads
the same input byte twice across EX AF,AF'. BC holds a live token/count;
DE/HL remain output/input pointers. Caching in B while preserving BC gives
the identical full register/flag result but costs51 â†’73 T (+22) across the
refill fragment. Two4-T register transfers already exceed the second7-T
read; safe PUSH/POP adds21 T.512 byte/carry cases pass.

The analogous saved paging-value probe costs33 â†’41 T (+8): retaining A on
the stack costs21 T versus a13-T reload. Ring copying rewrites main scratch
pairs; HL' belongs to the clock. Offset/target values already use patched
operands. Evaluate the distinct `sync` target restore in item20.

[513 native checks](evidence/trick_11.json),31 exact default profiles;
actual decoder delta0 T/code/state/input. No rewrite, no new full-codec run.
Reproduce with `audit_second_pass.py --item 11 --output libraries/evidence/trick_11.json`.

## Item12 â€” direct known-address access

**Decision: already present for fixed state.**256 native byte probes verify
17 â†’13 T for LD HL,nn / LD A,(HL) â†’LD A,(nn) when HL is dead. The decoder's
fixed state uses direct forms already. Its core HL is a live dynamic input/
history pointer: a directed subsequent INC HL reaches6005 before the rewrite
but5001 afterwards. With HL already established, LD A,(HL)7 T beats a fixed
absolute read13 T by6 T. The indexed ring table belongs to item06.

[258 checks](evidence/trick_12.json),31 exact defaults; actual delta0 T/code/
state/input. Reproduce with `audit_second_pass.py --item 12 --output libraries/evidence/trick_12.json`.

## Item13 â€” in-place memory arithmetic

**Decision: no eligible indexed state RMW.** The46 â†’23-T indexed primitive
has no matching state sequence in the adapted decoders. Their shifts consume
compressed input into A/the reservoir, rather than update a memory counter.
256 probes compare LD A,(HL)/SRL A15 T against SRL (HL)15 T: the latter has
no speed gain, leaves A unchanged and alters255 of256 possible input bytes.
That violates immutable input/shared-nibble ownership.

[Report](evidence/trick_13.json),31 exact defaults; actual delta0 T/code/state/
input. `audit_second_pass.py --item 13 --output libraries/evidence/trick_13.json`.

## Item14 â€” rotate/mask decomposition and narrower shifts

**Decision: retain existing fast paths; reject unproved narrowing.**256
native high-nibble values confirm current four RRCA +OR F0 costs23 T with
the same final AF as four SRL +OR F0 at39 T (+16). A memory nibble rotation
would instead mutate the compressed input. ZX0 already uses ADD A,A/RLA,
short-offset paths and short-gamma paths; longer gamma values need B.
Omitting RL B from the word shift loses the high byte in256 of512 directed
low-byte/carry states. Item23 separately evaluates more bit-phase expansion.

[768 native checks](evidence/trick_14.json),31 exact defaults; actual delta0
T/code/state/input. `audit_second_pass.py --item 14 --output libraries/evidence/trick_14.json`.

## Item15 â€” running pointers/address reuse

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

## Item16 â€” adjacent streaming status clear

**Decision: optional measured candidate.** `word_state_init=True` / CLI
`--word-state-init` requires streaming. `input_needed` immediately precedes
`finished`; clear them with LD HL,0 / LD (input_needed),HL (10+16=26 T)
instead of XOR A / two absolute byte stores (4+13+13=30 T). The prefix
shrinks one byte (direct222 â†’221, CALL224 â†’223), state/stack/payload unchanged.
HL is overwritten by finish/input loads; SCF initializes the nibble cache
before its first use. The word store finishes before an IRQ can observe it;
no caller relies on the old intermediate byte-store state.

[Report](evidence/trick_16.json):95 full resident-input guarded blocks,
28415177 â†’28414797 T (âˆ’380), exactlyâˆ’4 per block;252 accepted IRQs, zero
slower blocks/slices. Both partial-input modes pass42 full cases and six
placements: direct4365880 â†’4365712 T, CALL4368800 â†’4368632 T (âˆ’168 each),
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

## Item17 â€” carry-based bounded increment/decrement

**Decision: no saturating counter contract.** The corrected14-T bounded
decrement agrees in A for233 inputs23..255, with all final flags different.
Using it for ordinary exact decrements fails all22 directed counts2..23.
Length/offset fields are exact, not clamped. The four-bank ring must wrap:
its last index3 becomes0, whereas saturation holds3 and selects the wrong
bank. The source's original off-by-one remains in the earlier screen.

[259 checks](evidence/trick_17.json),31 exact defaults; actual delta0 T/code/
state/input. `audit_second_pass.py --item 17 --output libraries/evidence/trick_17.json`.

## Item18 â€” tail calls, threading and shared dispatch tails

**Decision: retain existing tails; reject the slower literal merge.**256
native flag states confirm a genuine CALL/RET forwarding leaf37 â†’20 T
(âˆ’17), including the callee's RET. ZX0 already uses tail jumps/inline copy
options. LZSA2 guard/input_wait/yield calls have required post-return work;
a directed discarded-continuation probe loses the required HL increment.

Sharing the existing Case1xx CP/JP tail in the other literal dispatch saves
one byte but costs0/+8/+13 T for 0xx/10x/11x classes. All256 token values
retain AF but verify those slower paths. Do not trade that speed for a byte
under the user's speed-first priority. Item10 already removed the eligible
long-literal jump trampoline without adding a branch.

[513 checks](evidence/trick_18.json),31 exact defaults; actual delta0 T/code/
state/input. `audit_second_pass.py --item 18 --output libraries/evidence/trick_18.json`.

## Item19 â€” preinitialized data/bulk initialization

**Decision: already present for constants; mutable resets retained.** The
generators emit table/state DB/words directly; the compiled ring table is
exactly0/1/3/4. There is no per-byte initialization loop to replace with LDIR.
ZX0's self-modified last offset must reset toâˆ’1 each new block. Five native
prior-offset probes show omitting initialization leaves stale offsets in
four cases; the load/reset probe46 â†’16 T achieves the wrong repeated-entry
semantics. Runtime pointer/end/frontier fields remain caller-owned. Item16
already combines the two runtime zero flags. External BSS would still require
reserved RAM and correct initialization, not free size reduction.

[Report](evidence/trick_19.json),31 exact defaults; actual delta0 T/code/state/
input. `audit_second_pass.py --item 19 --output libraries/evidence/trick_19.json`.

## Item20 â€” arithmetic target restore after comparison

**Decision: optional measured candidate.** `restore_compare=True` / CLI
`--restore-compare` applies to ordinary or streaming LZSA2. After OR A /
SBC HL,DE, ADD HL,DE restores the same target instead of reloading it from
state. Modular restoring carry equals subtraction borrow; S/Z/PV are retained.
Only Z is consumed by the following branch; H/N/undocumented flags are dead.
Nonfinal `sync` including RET127 â†’122 T, final132 â†’127 T; prefixâˆ’2 bytes,
no state/stack/payload increase. Defaults remain exact.

[Report](evidence/trick_20.json):95 full blocks/619480 bytes,
26352611 â†’26340326 T (âˆ’12285), real21 blocksâˆ’6330; exactlyâˆ’5 per caller
demand, no slower block/slice,230 accepted IRQs. Both guarded modes pass42
cases/six placements: direct4365880 â†’4364930 and CALL4368800 â†’4367850 T
(âˆ’950 each), identical producer/waits/167 once-only sectors. Directed sync
checks cover equality, signed/unsigned boundaries and FFFF; combined near/
word-init/long-copy profiles pass IRQ replay. All15 library tests pass.

```text
python toolkit/test_streaming_lzsa2.py --direct-header --noncanonical --output .tmp/item20-direct-before.json
python toolkit/test_streaming_lzsa2.py --direct-header --noncanonical --restore-compare --output .tmp/item20-direct-after.json
python toolkit/test_streaming_lzsa2.py --noncanonical --output .tmp/item20-call-before.json
python toolkit/test_streaming_lzsa2.py --noncanonical --restore-compare --output .tmp/item20-call-after.json
python libraries/tests/measure_second_pass.py --item 20 --stream-directory .tmp --output libraries/evidence/trick_20.json
```

## Item21 â€” local counter width/register-role proof

**Decision: retain structural bounds; reject global byte-range assumptions.**
Thirteen decrement probes show DEC C loses the borrow from B at256/512/8192/
15872. BC's role changes from token/negative offset to count; omitting B=0
after saving offsets leaves the wrong count in20 of24 role probes. All18
legal short escaped-word blocks replay exactly, again ruling out a large-length
assumption based only on encoding. Existing Fast short-gamma/offset paths,
byte-form unroll and fixed256-byte refill already exploit proven local bounds.

[55 checks](evidence/trick_21.json),31 exact defaults; actual delta0 T/code/
state/input. `audit_second_pass.py --item 21 --output libraries/evidence/trick_21.json`.

## Item22 â€” residue-entry whole-run unrolling

**Decision: reject the generic dispatch.** The measured private-code candidate
uses16 LDI instructions per loop, a patched JR entry for the residue, and
PUSH/POP AF around the selector. Only structurally nonzero byte-form lengths
enter it; all escaped words retain LDIR. Forward overlap and AF' stay intact.
Compared with the existing16-byte prefix, counts below40 pay44 extra T.
For n>=40, the copying/dispatch portion costs `83+16*n+10*ceil(n/16)`
versus `21*n-85`, excluding the common final JP. At40 the gain is only2 T.
It adds112 core bytes and two private-stack bytes, no input/state bytes.

[95 complete native blocks](evidence/trick_22.json),619480 decoded bytes,
26297662 ->26162449 T overall (-135213), but the21 real blocks are8767 T
**slower**, with19 slower blocks and405 slower slices in the entire corpus.
227 accepted IRQs and exact output/input/history/EOF checks pass. Long synthetic
runs conceal the cost on frequent short real copies. Reject this speed-first
candidate before guarded/player integration; production APIs remain unchanged.
Existing fixed256-byte ZX0 refill avoids this selector and remains useful.

The [frozen emitted profiles](tests/fixtures/item22_loop_profiles.json) retain
both complete byte regions, labels, patches and opcode timing metadata for
replay without shipping the rejected option.31 defaults remain exact.
`measure_second_pass.py --item 22 --output libraries/evidence/trick_22.json`
reproduces the failure as well as correctness. No streaming/release claim.

## Item23 â€” phase-expanded ZX0 Mega

**Decision: optional measured one-shot profile.** The pinned upstream673-byte
Mega expands the Elias paths for each bit-reservoir phase. Export with
`python -m zx0 build --variant mega --core 0x8000 --core-limit 0x8300 --output build/mega`.
No paging/yield/quota hook is supported. HL=input, DE=output; preserve working
AF/BC/DE/HL across IRQ, reserve caller-stack headroom and keep the two offset
operand bytes writable. Input/history must be resident, output nonwrapping.
The existing coroutine Fast is unchanged; a raw no-boundary adaptation of
its emitter supplies the equal-ABI baseline, rather than comparing wrappers.

[417 full native blocks](evidence/trick_23.json),3204723 decoded bytes,
include all364 authenticated8192-byte real-stream blocks and53 directed/random
length/offset/phase inputs. Aggregate Fast161515003 ->Mega151879545 T
(-9635458); real156012520 ->146422274 T (-9590246,6.147%). Zero slower
blocks. Turbo real160653056 T, Standard201490104 T. The measured paths include
the actual real-stream bit-phase mix and EOF, rather than upstream percentages.
Mega costs673 bytes versus the no-boundary Fast profile (see emitted sizes in
the report); raw code needs three256-byte sectors. No extra format/state/buffer
bytes. Maximum plain stack use4 bytes including caller return, versus6 Standard.
1305 accepted IRQs, exact bounded source/history/EOF, relocated Mega at9103,
dirty prior-offset tests and16 library tests pass. All31 defaults remain exact.
No coroutine/player adoption, sustained disk or movie-release qualification.

```text
python libraries/tests/measure_bit_phases.py --output libraries/evidence/trick_23.json
python -m unittest discover -s libraries/tests -v
```

## Item24 â€” distance-one repeated-byte prefix

**Decision: reject the generic selector.** A test-only LongMatchBC specialization
checks the saved offset FFFF using LD A,H / AND L / INC A / JR NZ. AF is dead,
AF' unchanged, B=0 and byte-form count>=24. On a hit, read one seed and emit24
LD (HL),A / INC HL pairs; restore DE, subtract24 from C, skip zero remainder,
otherwise LDIR forward from DE-1. All word/short/default paths stay intact.
No new stack/state/input bytes. Counting from the loaded offset through the
common final JP: original `21*n-64`; hit398 T at24 (440 ->398, -42),
`21*n-110` at25..255 (-46), miss `21*n-40` (+24). The guard dominates when
distance1 is insufficiently frequent; no assumed page alignment or zero LDIR.

[95 full blocks](evidence/trick_24.json):26297662 ->26307336 T (+9674),
real21 +3816 T,51 slower blocks/400 slices;230 IRQs and exact output/source/
history/short escaped words pass.31 defaults exact. Reject before streaming/
player integration under the speed-first requirement. The reproducible
[test-only generator](tests/measure_repeat_match.py) requires an exact unique
production source site and saves emitted code/labels/timing metadata in its
report. `--output libraries/evidence/trick_24.json` replays the failed attempt.
The earlier known16-byte primitive alone omitted selector/residue costs.

## Item25 — stack-word exchange

**Decision: already present where its ownership fits.** ZX0 Standard already
uses EX (SP),HL twice around the match copier. Native1024 word/flag cases
confirm EX DE,HL / POP HL / PUSH DE25 T ->EX (SP),HL19 T (-6, -2 bytes)
only when DE is dead. In all1024 directed live-output cases the old chain
puts old HL in DE while the replacement leaves DE at the output cursor.
Fast/Turbo/LZSA2 use patched offsets and live DE; suspension saves include
live input/output/count/reservoir and return continuations. No eligible chain
exists there under the current contract. Do not replace a live save merely
because a stack word is owned. [Report](evidence/trick_25.json),31 exact defaults,
actual delta0 code/state/stack/payload/T; no decoder rewrite/new release run.
`audit_second_pass.py --item 25 --output libraries/evidence/trick_25.json`.
