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
