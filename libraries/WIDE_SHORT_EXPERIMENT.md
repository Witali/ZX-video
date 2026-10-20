# Private Wide short-match experiment — 2026-10-20

This is a raw-only native experiment against the current public Expanded
decoder (6,998 code/table bytes, six caller-stack bytes; 15,623,953 T on the
complete authenticated 21-real-block /323,940-byte output corpus). Public
generators, default profiles and package APIs are unchanged. The private copy
retains `_boundary`, `_external_labels` and `_literal_guards` hooks for a
separate wrapper integration; no new wrapper/producer qualification is claimed.

## Result

Each of seven variants passes all 95 corpus cases plus 580 directed cases,
with protected input/output/history, exact source consumption, all 256 token
values in both cache phases, legal short word escapes, exact EOF, IRQ probes
and relocation to 9000h and 9003h. Every case's CPU change exactly equals the
independently calculated sum of per-token costs. The 9003h full-new variant
requires an explicit test-only oversize override: correctness is proved but
its 10,001-byte service footprint is invalid for public use.

| Private options | Code bytes | Service at 8000h | Service at 9003h | Real CPU T | Change versus current Expanded |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shared + new lengths2..8 | 4,132 | 4,138 | 4,391 | 15,221,490 | -402,463 (-2.575936%) |
| Expanded + new length2 | 7,222 | 7,228 | 7,481 | 15,600,307 | -23,646 (-0.151345%) |
| Expanded + new lengths2..4 | 7,838 | 7,844 | 8,097 | 15,423,401 | -200,552 (-1.283619%) |
| Expanded + new lengths3..8 | 9,518 | 9,524 | 9,777 | 14,999,606 | -624,347 (-3.996089%) |
| Expanded + new lengths2..8 | 9,742 | 9,748 | **10,001: rejected** | 14,975,960 | -647,993 (-4.147433%) |
| Expanded + new2..8 except unusedDEh | 9,722 | 9,728 | 9,981 | 14,975,960 | -647,993 (-4.147433%) |
| Shared + new2..8 + repeated4..8 | 4,222 | 4,228 | 4,481 | 15,188,829 | -435,124 (-2.784980%) |

The service counts include all table/alignment/embedded variables plus the
six-byte maximum caller stack, with no extra state/scratch/internal buffers.
Input/output/history and actual IRQ code/headroom remain separate. The test
IRQ handler uses 13 code bytes and six stack bytes. Parent proof of the full
guarded reference currently totals9,881 bytes including its workspace/probe
example; its119-byte headroom must not be confused with consumer-only room.

All Expanded new-offset-only variants have **zero slower cases** among675.
The shared variants improve all21 real blocks but have281 /253 slower non-real
cases across the complete675-case suite, respectively, up to216 T versus Expanded. Every counterexample is
retained in the full report. No universal speed claim applies to sharing.

The DEh omission has zero real frequency and frees20 bytes; it only demonstrates
that the full alignment overflow is small. A fixed magic token exclusion is
not recommended as a public API. Prefer the structured3..8 policy, explicitly
aligned2..8, or the substantially smaller Shared short policy. No startup/EOF
jump experiment was performed.

## Exact instruction changes

For a **new-offset** token with MMM0..6 (length n=2..8), BC still contains the
negative offset before the existing store/clear-count tail. Use:

```asm
ld (offset),bc       ; Preserve the one existing SMC operand for later repeats.
push hl             ; Save the live input continuation.
ld h,b
ld l,c              ; Offset is copied before BC becomes the match counter.
ld bc,n             ; Clears B and initializes C in one 10-T instruction.
add hl,de
; n forward LDI instructions
pop hl
jp ReadToken
```

The complete path from the offset store to the next ReadToken changes
**21n+76 ->16n+80 T**, saving **5n-4 T**:6/11/16/21/26/31/36 T for n2..8.
Code grows4+2n bytes per specialized handler. The native microprobes verify
118->112,139->128,160->144,181->160,202->176,223->192,244->208 T.

For a **repeat-offset** token, B is already zero. Keep LD C,n; load the shared
offset as data with LD HL,(offset), then use n LDIs. The complete path is
**21n+49 ->16n+65 T**, saving **5n-16 T**. Length2/3 would lose6/1 T and remain
unchanged; length4..8 save4/9/14/19/24 T, verified by native opcode probes.
Code grows6+2n bytes per body. Shared has one body per XYZ/MMM, so adding the
five repeated-length kernels costs90 bytes rather than360 expanded bytes.

BC is exactly zero after the last LDI; overlap remains forward. Main A and
AF' ownership do not change. LD BC,nn and the register copies preserve flags;
ADD HL,DE receives the same operands, and final LDI flags match final LDIR.
Only the existing two offset operand bytes are mutable. Input save/restore
and peak stack are unchanged. IRQ must preserve the existing live register
sets including AF'; no interrupt masking or SP redirection is introduced.

MMM7 remains on the original nibble/byte/word paths, including legally short
word-escaped matches. Specialization is selected by the token's known short
field, never by assuming a word escape implies length>=256.

## Handoff and reproduction

- Private builder: `tests/wide_short_profile.py`, copied from the current
  public `lzsa.wide` with additive test-only kernel options.
- Helpers: `emit_new_offset_short(a, token, length)` expects BC=offset;
  `emit_repeat_short(a, token, length)` expects B=0. Both return to ReadToken.
- Broad smaller/faster choice: `build(shared_literals=True,
  short_lengths=range(2,9), repeat_lengths=range(4,9))`.
- Structured expanded choice: `build(short_lengths=range(3,9))`.
- Maximum expanded new-copy choice: `build(short_lengths=range(2,9))`,
  with explicit alignment/cap checking. 9003h is rejected; never hide padding.
- The hybrid agent can import the helpers into its separate sharing-policy
  generator; no public module may import these test files.

Run from the repository root with the native z80 dependency on PYTHONPATH:

```powershell
python libraries/tests/measure_wide_short.py --output libraries/evidence/wide_short_experiment.json
```

[Summary and all exact profile arguments](evidence/wide_short_experiment.json),
[complete675-case rows per variant](evidence/wide_short_experiment_full.json.gz).
All native replays completed before a relative output-path formatting error;
only path normalization was fixed and the finished evidence was summarized
without repeating native execution. The report preserves the measured script
hash before that formatting fix and the final source hash separately.

Recommended integration is an explicit optional short policy with defaults
unchanged. Shared+new2..8+repeat4..8 is faster and smaller on every retained
real block; Expanded3..8 is a clean intermediate, while Expanded2..8 is a
raw speed option subject to alignment. Coroutine/guarded wrappers and total
reference-service memory must be reverified before exposing their new flags.
