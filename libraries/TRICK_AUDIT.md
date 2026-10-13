# Sequential Z80 trick applicability audit

The checklist records applicability to the current ZX0/LZSA2 ABI. Primitive
instruction savings are not whole-codec results. Each section has its own
dated, focused commit and native precondition evidence. Default profiles stay
byte-exact unless a separately qualified change is explicitly adopted.

## 02 — Register copies instead of PUSH/POP (2026-10-13)

The [forum pair-transfer example](https://zx-pk.ru/threads/33945-optimizatsiya-z80-koda-dlya-mandelbrota.html#post1138545)
costs PUSH HL11 + POP BC10=21 T versus LD B,H4 + LD C,L4=8 T (-13).
Both are two code bytes, no flags change; the latter needs no temporary
stack word. The user explicitly expands the audit to every direction and
nonadjacent commands. [Native evidence](evidence/trick_02.json) now checks
36864 value/flag/interleaving cases, covering all six ordinary pair transfers:

| Stack transfer | Direct register copy |
| --- | --- |
| PUSH BC / POP DE | LD D,B / LD E,C |
| PUSH BC / POP HL | LD H,B / LD L,C |
| PUSH DE / POP BC | LD B,D / LD C,E |
| PUSH DE / POP HL | LD H,D / LD L,E |
| PUSH HL / POP BC | LD B,H / LD C,L |
| PUSH HL / POP DE | LD D,H / LD E,L |

The stack operations need not be adjacent. Place the LDs at POP when the
source pair retains its pushed value across the intervening code. Place
them at PUSH when the destination is dead and neither read nor overwritten
until POP, even if the source subsequently changes. Account for branches,
calls/IRQ clobbers, stack balance, EX (SP),HL and any explicit SP-relative
access. Independent arithmetic and register-preserving calls pass the native
tests, retaining the same13-T saving. AF is special because F cannot be
copied with an ordinary LD; indexed pairs require a separate instruction/ABI
analysis rather than assuming the8-T result.

ZX0 `banked.py:refill_short` already transfers HL to BC with LD B,H/LD C,L;
`ring_copy` also uses register copies for BC/HL. `incremental.py` copies
DE to BC while retaining a stacked DE for later restoration. LZSA2's
MatchUseC/LongMatchBC push the input HL, overwrite HL with match history,
consume BC down to zero, then restore HL. Reusing BC to save HL destroys
the count; the native counterexample changes8 to0x4000. Suspend/resume
pushes preserve independent live AF/BC/DE/HL (and AF' in LZSA2) across a
caller that may overwrite every working register. ZX0's standard decoder
also keeps its last offset on the stack, with EX (SP),HL ownership changes.
These operations are saves/restores, not eligible pair transfers. In
`incremental.emit_exact_copy`, PUSH BC eventually pairs with POP HL, but BC
has already become the prefix count and HL held the available-space scratch.
The expanded native counterexample loses the saved original count with LDs
placed at either endpoint. Check this nonadjacent case explicitly; scanning
only adjacent PUSH/POP would miss its actual dataflow.

**Decision: already present in eligible paths; no further code change.**
No added code/RAM/stack/table/stream bytes; decoder instruction delta0 T.
The 78-test/31-profile baseline from item01 remains applicable without a
changed decoder. Reproduce the independent primitive/counterexample check:

```powershell
python libraries/tests/measure_tricks.py --item 02 --output libraries/evidence/trick_02.json
```

## 03 — RES/SET instead of accumulator masks (2026-10-13)

LD A,L4 / AND FE7 / LD L,A4 costs15 T; RES 0,L costs8 (-7), both four
versus two code bytes. It is valid only if the changed A and flags are dead.
[1024 native checks](evidence/trick_03.json) preserve the masked L value but
show differing AF, including live carry. RES/SET preserve flags; AND clears
carry and calculates S/Z/P. SET similarly replaces a15-T OR sequence only
when its side effects are unnecessary.

LZSA2 AND24 supplies even parity for LL=00/11, Z for the zero-literal
class, and the masked value used by short literal rotation. AND7 supplies
match length and Z for extension. OR F0 preserves the cached nibble format.
ZX0's bank selector AND3 clears six bits; AND F8 clears three bits. They
are multi-bit masks in A, not a single bit in a pair. Several RES operations
cost more than the existing7-T mask, and would not reproduce its flags.
The generators contain no eligible LD A,pair-byte / single-bit-mask /
LD pair-byte,A sequence. Upstream resources remain immutable.

**Decision: inapplicable to the current mask sites.** Retain the live flag/
value operations; delta0 T/code/state/stack/stream. Reproduce with
`measure_tricks.py --item 03 --output libraries/evidence/trick_03.json`.

## 04 — INC L instead of INC HL (2026-10-13)

INC HL=6 T, INC L=4 (-2), both one byte. INC L preserves carry but changes
S/Z/H/P/N; INC HL preserves all flags. At low byte FF, INC L leaves H
unchanged. [Native evidence](evidence/trick_04.json) checks2304 pointer/flag
inputs, including40FF andFFFF, and confirms crossing/flag differences.

ZX0 `codec.py` already emits INC L / CALL Z,input_next_page for page-aware
input. `streaming.py` and `streaming_inline.py` preserve AF around INC H in
that handler, then enforce the loaded frontier. The minimal increment-only
convention is14 T without crossing and56 T with crossing, before actual
supply/guard work. Its purpose is correct page supply, not a universal2-T
saving over an unguarded contiguous pointer.

LZSA2 token/length/nibble positions and contiguous ZX0 bit-byte positions
can occur at any low address. Even a two-byte length word is not guaranteed
even-aligned after variable tokens/nibbles/literals. Frame packet positions
in `incremental.emit_wait` also move by variable byte lengths. No newly
eligible page-confined increment is proved by the current ABI. The six
native input placements from item01 deliberately exercise these boundaries.

**Decision: already present where page handling is explicit; reject an
unguarded replacement elsewhere.** No decoder change, delta0 T/code/RAM/
stack/stream. Reproduce `measure_tricks.py --item 04 --output
libraries/evidence/trick_04.json`.

## 05 — Aligned fast jump table (2026-10-13)

The [special table](https://zx-pk.ru/threads/30694-vyravnivanie-utrambovyvanie-i-vpikhivanie-koda-bystrye-tablitsy-perekhodov-i-sjasm.html#post1020767)
uses LD L,A4 / LD H,page7 / LD H,(HL)7 / JP (HL)4=22 T. It requires
the handler low byte to equal the input index and destroys HL. LZSA2 keeps
its input in HL. The measured complete selection prefix becomes PUSH HL11,
LD A,(HL)7, AND24=7, the22-T table and POP HL10=57 T.

[All256 token bytes](evidence/trick_05.json) reach the same masked A/flags,
original HL and unchanged BC/DE in both probes. Consistent endpoints are
immediately after class selection, before common length/copy/offset work:

| LL | Current S/P branches | Saved-HL table | Delta |
| --- | ---: | ---: | ---: |
| 00: NoLiterals entry | 31 T | 57 T | +26 T |
| 01/10: first short-length RRCA | 24 T | 57 T | +33 T |
| 11: MoreLiterals entry | 36 T | 57 T | +21 T |

These endpoints differ from the historical dispatch-plus-offset table in
`toolkit/LZSA2_DISPATCH.md`; do not mix those totals. The toy table requires
25 bytes at a256-aligned start (only indices0,8,16,24 are used), up to255
alignment bytes without an existing gap, and handlers with prescribed low
bytes. Real handler bodies would require further placement/padding work;
none is allocated in the player. Saving HL in another working pair just
moves the live-register/stack problem. ZX0's bit/gamma branching has no
existing equivalent dense token index table to replace.

**Decision: reject before a whole-block prototype.** Every LZSA2 selection
class is already faster, and the table adds memory/placement constraints.
No core/stream change; actual delta0 T/bytes. The microcandidate delta is
positive above, not a claimed whole-decoder measurement. Reproduce
`measure_tricks.py --item 05 --output libraries/evidence/trick_05.json`.

## 06 — Power-of-two table placement (2026-10-13)

SET7,H=8 T maps a relative index0..7FFF to8000..FFFF. It does not add
an arbitrary output address to a negative offset. [Native counterexamples](evidence/trick_06.json)
show that offsetFFFF plus outputC001 must addressC000, whereas SET leaves
FFFF. Keep ADD HL,DE=11 T for actual history. Neither codec has an aligned
32-KiB dictionary lookup that can silently replace exact live history.

An eligible narrower use is ZX0's four-byte `ring_banks` table. New optional
`banked.build(aligned_ring_table=True)` pads the table to7F00, then uses
LD L,A4 / LD H,7F7 / LD E,(HL)7 in place of LD E,A4 / LD D,07 /
LD HL,table10 / ADD HL,DE11 / LD E,(HL)7. The address/lookup part drops
39 ->18 T (-21). Whole ring_page including state loads, paging OUT and RET
drops108 ->87 T. With a custom paging CALL it is113 ->92 T (-21).
AF/BC/DE/HL remain scratch; AF'/alternate pairs are untouched. Callers
already save live values. Input ring_region is always0..3, not arbitrary L.

[Full independent banked-native report](evidence/ring_table_native.json):
all16 fast/copy-boundary profiles,128 region/history-page combinations,
64 complete8192-byte blocks (stored, literals and overlaps1/256), all four
ring-bank crossings, exact input and output, poisoned registers between
demands,132 accepted synthetic interrupts. CPU17898920 ->17874728 T
(-24192), zero slower blocks/slices. The full AY/IM2 handler test also
interrupts every instruction with the aligned profile, checking registers,
page, private stack, clock and AY output. All31 default profiles are unchanged.

The instruction body shrinks4 bytes but table alignment adds padding:
net +121..245 bytes depending on profile; ordinary567 ->772 bytes (+205).
The existing four entries remain four bytes, no new state/stack/buffer/
compressed bytes/sectors. All optional extents end at7F04 within bank5's
declared7C00..8000 template reservation. Account for this full range in an
application; it has no integrated player allocation or ULA/disk/publication run.

**Decision: optional measured ZX0 profile; history masking rejected.**
This applies alignment to a real small table with an explicit memory cost.
Reproduce `measure_ring_table.py --output libraries/evidence/ring_table_native.json`
and `measure_tricks.py --item 06 --output libraries/evidence/trick_06.json`.

## 07 — POP/PUSH bulk copy through SP/EXX (2026-10-13)

The [14-byte forum copier](https://zx-pk.ru/threads/22089-memcpy-bystraya-peresylka-dannykh.html#post640226)
costs seven POPs70 + seven PUSHes77 + two EXX8 + two LD SP,nn20=175 T
(12.5 per byte), versus LDIR14=289. [Native probes](evidence/trick_07.json)
verify ordered nonoverlapping output and wrong output for legal match
distances1/2: prefetched bytes have not yet been produced. Forward LDI/LDIR
correctly repeats the seed; bulk prereading copies poisoned bytes instead.

Even literal-only use changes SP, A/AF, both BC/DE/HL sets and specifically
HL'. ZX0 carries its bit reservoir in A; LZSA2 needs the token in A after
literal copying and the shared nibble in AF'. `incremental.py` explicitly
assigns HL' to the IM2 clock, while coroutine returns depend on the private
stack. Save/restore private SP alone adds ED LD (nn),SP20 + LD SP,(nn)20,
before retaining AF/alternate live state and fixing byte-count tails. IRQ
pushes would use data-address headroom that the current input/history ABI
does not allocate, rather than the verified private stack. No IRQ masking
or new temporary literal buffer is introduced by this audit.

**Decision: reject for the current ABI.** The primitive's114-T gain excludes
required preservation and is not a whole-decoder result. Correct LZ overlap,
AY clock ownership and suspension take precedence; no core/RAM/stream changes
(actual delta0 T). Reproduce `measure_tricks.py --item 07 --output
libraries/evidence/trick_07.json`.

## 08 — Constant data as LD rr,nn/PUSH code (2026-10-13)

The [constant word emitter](https://zx-pk.ru/threads/22089-memcpy-bystraya-peresylka-dannykh.html#post640483)
costs LD HL,nn10 + PUSH HL11=21 T per fixed word (10.5 per byte), storing
each two-byte word as four instruction bytes. It only works when values are
known at assembly-generation time, and writes backwards through SP.

[Native fixed128-byte sample](evidence/trick_08.json) is exact:256 body
bytes plus3-byte LD SP entry=259,1354 T including that entry; LDIR-only
costs2683 T. SP save/restore adds8 code bytes/40 T and is excluded from
this primitive. Generic ZX0/LZSA2 literals are runtime input bytes, not
constants. Their exact standard all-literal samples occupy133/132 bytes
respectively in the measured serializer (one isolated256-byte sector);
the compiled version needs two sectors. These are illustrative isolated
payload counts, not a movie allocation or measured physical delivery result.

A repeated-fill/dictionary-specific generator would need a declared data
contract, caller stack/IRQ headroom and whole delivery accounting. A universal
literal-code format or a per-block executable/JIT stage would change the
standard transport and add generation/storage work. The reusable decoders
already initialize their fixed offsets with immediate constants; there is
no fixed literal/dictionary fill to rewrite in their current API.

**Decision: inapplicable to generic standard-format literals.** Retain the
standard stream and codecs; actual delta0 T/code/RAM/stream. Reproduce
`measure_tricks.py --item 08 --output libraries/evidence/trick_08.json`.

## 09 — Carry to a mask with SBC A,A (2026-10-13)

The [carry-mask primitive](https://zx-pk.ru/threads/20455-ispolzovanie-steka-i-preryvaniya.html#post559684)
costs4 T and produces00/FF for carry0/1, independent of the incoming A.
[Native evidence](evidence/trick_09.json) checks all512 A/carry combinations
and another512 high-byte propagation inputs. Existing LD A,H4 / ADC A,07
costs11 T; SBC A,A4 / AND1=7 / ADD A,H4 costs15 (+4), with identical final
AF on the latter inputs. The mask is correct but adds work at these sites.

LZSA2 input-frontier guards already propagate low-byte carry with ADC0;
offset5/13 builders consume carry with RL C/RL B. ZX0 Elias offsets use
RR/RL and its bounds use ADC/SBC directly. None of these sites contains a
carry-conditioned branch that chooses A=00/FF. ZX0's live A bit reservoir
and LZSA2's token/nibble registers also prohibit using SBC A,A as scratch
unless A is proved dead. The primitive overwrites73 with00 when carry is0.

**Decision: no cheaper eligible mask branch.** Retain direct propagation/
rotates; actual delta0 T/code/RAM/stream. Reproduce `measure_tricks.py
--item 09 --output libraries/evidence/trick_09.json`.
