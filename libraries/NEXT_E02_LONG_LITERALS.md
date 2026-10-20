# E02: LZSA2 long-literal continuations

Completed bounded rejection screen, 2026-10-20. Baseline: E01 at `9fbd9ce7`,
`lzsa.hybrid.build('fast', cold_match_extension=True)`, 9,499 aligned service
bytes and 14,926,306 T on the unchanged 21 real blocks. The three bounded
constructions are test-only; no public decoder/default or format changes.

## Complete helper and memory model

The emitted `LongLiterals` helper occupies 45 bytes and serves 64 LL3 CALL
sites. It has three RET exits at offsets 27/37/44 for nibble, byte and word
literal lengths. E00 observes 4,870 real calls: 4,701 nibble, 169 byte and
zero word. CALL17 +RET10 alone costs 131,490 T. Byte/word paths still need
their exact input fields, including legally short one/two-byte word literals.

Removing these helper return words cannot reduce the complete six-byte
stack reservation: the caller return and saved caller HL' occupy four bytes,
and the unchanged match-copy `PUSH HL` needs another two. Code/tables/padding,
embedded offset state counted once, caller/private stacks and scratch all
belong to service memory. Compressed input and output/history are separate.

The [private emitter](tests/next_e02_profiles.py) makes count-checked source
substitutions in a private namespace. The package's globals remain intact;
the transformed source identity and all final regions/labels are saved.

1. **Implicit HL' continuation.** Each dispatch leaves the handler entry in
   HL'. Replace CALL with JP, use `EXX; INC HL` four times `; JP (HL)` at each
   helper exit, and insert EXX at the 64 continuations. Full 16-bit INC handles
   page crossings and preserves flags. Each RET1 becomes six bytes (+15 B
   over three exits); 64 continuation EXXs add 64 B: **+79 service B**.
   JP10 +return32 +EXX4 replaces CALL17 +RET10: **+19 T per call**.
2. **Clone one hot nibble path.** Only token248/body_224_1 gets a 27-byte hot
   inline path, with a six-byte cold CALL/JP trampoline replacing CALL3:
   **+30 service B**. The other 63 callers retain the shared helper. A hot
   call saves 27 T; a byte/word escape adds 10 T. Real hits 483/17 predict
   **-12,871 T**. Even impossible free cold exits leave +24 B of growth;
   combining this clone with the two-byte tail saving still grows by 28 B.
3. **Share cold copy/return tails.** Keep the hot LDIR/RET. Replace each
   three-byte byte/word LDIR/RET suffix with a two-byte JR to that same tail:
   **-2 service B**, **+12 T per byte/word call**. Final spans are -12/-18;
   the preceding word-choice JR shifts from +4 to +3. Real cost grows 2,028 T.

## Measured screen and decision

All three actual emitted constructions match the independent E00 timing
equations on all 675 frozen complete blocks:

| Test-only construction | Service B | Real CPU T | Delta service B | Delta real T |
| --- | ---: | ---: | ---: | ---: |
| Implicit HL' return | 9,578 | 15,018,836 | +79 | +92,530 |
| One hot nibble clone | 9,529 | 14,913,435 | +30 | -12,871 |
| Shared cold tail | 9,497 | 14,928,334 | -2 | +2,028 |

The direct return slows 659 cases, maximum 5,833 T; 16 are equal. The clone
improves 23 cases, 652 are equal and none slow. The shared tail slows 657
cases, maximum 228 T; 18 are equal. Direct return/shared tail slow all 21
real blocks. Named per-case lists remain in the full evidence.

The qualified local C flat guarded core first reproduces all 675 accepted
baseline counts from the original kosarev E01 proof, with exact input/output
hashes. It then executes 2,025 candidate cases. Four extra word-literal1/2
cases force the cloned continuation in both cache phases; baseline and all
three constructions run on both cores (16+16 supplemental runs). All three
helper exits, output/EOF/cursors, preserved IX/IY/alternate pairs, permitted
code writes and dirty offset pass. Every observed stack maximum is six bytes.

All 768 low-byte alignment builds save actual regions/labels/relative spans
and complete service inventories. The full report authenticates the qualified
DLL/build/source proof and frozen executed sources. This is flat screening;
IRQ, compressed-input/output overlap and relocated runtime promotion matrices
were deliberately not run because every construction already fails one
acceptance metric. No wrapper or hardware-contention qualification is claimed.

All fail the current requirement to reduce both complete real CPU and
service memory. Retain E01. The faster/larger clone is preserved as experiment
evidence; it is not an installed option or a universal optimum claim.

An initial run selected an unusable unqualified default DLL alias and stopped
before any replay; the final command authenticates the separate qualified
artifact explicitly. A preliminary screen was interrupted to correct inherited
nominal service metadata on the private prototypes; their actual instructions
were unchanged. The complete final run uses corrected metadata/source hashes.

[Summary](evidence/next_e02_lzsa.json),
[complete native/alignment evidence](evidence/next_e02_lzsa_full.json.gz),
[reproducer](tests/next_e02_measure.py),
[focused geometry/format tests](tests/next_e02_tests.py).

```powershell
python libraries/tests/next_e02_tests.py -v
python libraries/tests/next_e02_measure.py --dll .tmp/codec-cpu-qualified/codec_cpu.dll --output libraries/evidence/next_e02_lzsa.json
```
