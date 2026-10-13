# Sequential Z80 trick applicability audit

The checklist records applicability to the current ZX0/LZSA2 ABI. Primitive
instruction savings are not whole-codec results. Each section has its own
dated, focused commit and native precondition evidence. Default profiles stay
byte-exact unless a separately qualified change is explicitly adopted.

## 02 — Register copies instead of PUSH/POP (2026-10-13)

The [forum pair-transfer example](https://zx-pk.ru/threads/33945-optimizatsiya-z80-koda-dlya-mandelbrota.html#post1138545)
costs PUSH HL11 + POP BC10=21 T versus LD B,H4 + LD C,L4=8 T (-13).
Both are two code bytes, no flags change; the latter needs no temporary
stack word. [Native evidence](evidence/trick_02.json) checks1536 values/flag
combinations and demonstrates why a live save cannot use the same rewrite.

ZX0 `banked.py:refill_short` already transfers HL to BC with LD B,H/LD C,L;
`ring_copy` also uses register copies for BC/HL. `incremental.py` copies
DE to BC while retaining a stacked DE for later restoration. LZSA2's
MatchUseC/LongMatchBC push the input HL, overwrite HL with match history,
consume BC down to zero, then restore HL. Reusing BC to save HL destroys
the count; the native counterexample changes8 to0x4000. Suspend/resume
pushes preserve independent live AF/BC/DE/HL (and AF' in LZSA2) across a
caller that may overwrite every working register. ZX0's standard decoder
also keeps its last offset on the stack, with EX (SP),HL ownership changes.
These operations are saves/restores, not eligible pair transfers.

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
