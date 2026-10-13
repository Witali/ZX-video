# Item 01: bounded long-copy unrolling

2026-10-13, baseline `6168ba14`, branch `codex/z80-codec-tricks`.
The [forum memcpy technique](https://zx-pk.ru/threads/22089-memcpy-bystraya-peresylka-dannykh.html)
is already present in ZX0's `banked.build(fast_refill=True)`: exactly256-byte
refills use eight groups of32 LDIs. That routine costs4251 T through RET
versus5381 T for LDIR/RET (-1130 T); requests1..255 take an added20-T test.
The default profile remains unchanged. These are instruction counts, not
physical disk measurements.

## LZSA2 application

`lzsa.resumable.build(long_copy=True, core_limit=0x9000)` adds a long-literal
and long-match kernel. Byte-extended literals are18..255 bytes and
byte-extended matches24..255. Sixteen forward LDIs therefore leave nonzero
BC for LDIR. Short tokens/EOD and all escaped16-bit forms retain their old
paths. Forward copying
preserves distance1/2 overlap and the existing token-boundary overshoot.
AF' remains the nibble reservoir. Matches save the input HL on the existing
private stack and load the shared offset operand as data, avoiding an extra
offset store on every token. Guards establish readable input before copying.

The following costs use Zilog UM0080, N=copied bytes, and include the
specified branch/continuation endpoints. LDIR contributes21N-5 T.

| Path/endpoints | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Ordinary long8 literals: branch from ManyLiterals through OR A | 21N+16 | 21N-34 | -50 T |
| Ordinary long16 literals: JP after reading high byte through OR A | 21N+15 | 21N+15 | 0 T |
| Guarded long8: JP from guard to copy through OR A | 21N-1 | 21N-61 | -60 T |
| Guarded long16: JP from guard to copy through OR A | 21N+9 | 21N+9 | 0 T |
| Complete streaming long8 / long16 bypass | prior path | prior path-60 / prior path | -60 / 0 T |
| Long8 match: LD C,A through POP HL | 21N+36 | 21N-23 | -59 T |
| Long16 match: PUSH HL through POP HL | 21N+32 | 21N+32 | 0 T |

Examples:18-byte ordinary literals394 ->344 T; 256-byte ordinary literals
5391 ->5391 T; 24-byte long8 matches540 ->481 T. Unchanged short/word paths
have delta0 T. The six extra-T cost of reading `LD HL,(offset)`, helper jumps
and the ordinary literal trampoline are included; these are not naive5N savings.

Ordinary prefix/core sizes134/250 ->134/337 bytes (+87); CALL-guarded
224/254 ->224/338 (+84); direct222/251 ->222/335 (+84). No new state,
stack, tables, packets, or compressed payload bytes/sectors. Ordinary core ends at
0x8f31 in bank2; the default 0x8ef7 limit cannot hold it. Reserve the larger
range explicitly and check the application's other allocations. No player
layout or default codec profile is changed. Storing the exported raw regions
as separately rounded256-byte files costs2 ->3 sectors (+1); actual boot
packaging/compression has not been built or measured. Payload-sector invariance
must not be interpreted as unchanged total disk occupation.

## Complete verification and decision

- [Native comparison](evidence/long_copy_native.json):95 complete blocks,
  619480 output bytes, 21 authenticated real blocks plus24 boundary,32
  seeded random and18 short16-bit-form streams. CPU26352611 ->26297662 T
  (-54949); real blocks19412006 ->19387980 T (-24026,0.124%). Zero slower blocks/slices;
  230 accepted synthetic interrupts and exact output with IRQ.
- [Streaming comparison](evidence/long_copy_streaming.json):42 full cases
  in both guard modes, six shared-memory input placements each, byte-exact
  EOF, no unloaded/overwritten input/history, identical waits and167 sectors
  read exactly once. Direct component4365880 ->4365460 T (-420);
  CALL component4368800 ->4368380 T (-420). Each producer is unchanged:
  direct721608 T, CALL724078 T.
  These compare the same guarded decoder before/after unrolling.
- All31 default generated layouts retain their exact bytes and labels.
  Portable/native tests cover relocation, all literal/match length transitions,
  overlap, poisoned caller registers, export and partial/complete guard updates.
  All12 library tests pass, including relocated short16-bit forms; prior66
  toolkit tests protect unchanged defaults. Guarded full comparisons are rerun
  after this correction.

The initial item01 profile incorrectly inferred a >=256 lower bound from the
encoder's canonical choice of16-bit escape. The [pinned format](https://github.com/emmanuel-marty/lzsa/blob/15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5/BlockFormat_LZSA2.md)
specifies the final16-bit value; existing host/native decoders accept shorter
values. Literal3 in a16-bit form caused an invalid write atC003. Preserve
[initial native evidence](evidence/long_copy_native_initial.json) and
[initial streaming evidence](evidence/long_copy_streaming_initial.json) as
superseded canonical-only checks. Removing word kernels first exposed a3-T
regression from replacing untaken JR7 with JP10. A nearby trampoline now
retains the old JR on word forms, charging10 T only to eligible byte forms.
[Correction record](evidence/long_copy_correction.json) retains both failures.

**Decision: optional measured candidate.** The real CPU benefit is small;
the additional bank2 space needs application accounting. No ROM/physical
disk/ULA or full publication run is measured here, so this cannot replace a
release profile. ZX0 already has bounded refill unrolling; applying the same
16-LDI prefix to arbitrary ZX0 lengths would underflow BC on short copies.
Keep its existing bounded profile until a separate useful candidate is scoped.

Reproduce from the repository root with the optional native dependencies:

```powershell
python libraries/tests/measure_long_copy.py --output libraries/evidence/long_copy_native.json
python toolkit/test_streaming_lzsa2.py --direct-header --noncanonical --output .tmp/streaming-before.json
python toolkit/test_streaming_lzsa2.py --direct-header --noncanonical --long-copy --output .tmp/streaming-after.json
python toolkit/test_streaming_lzsa2.py --noncanonical --output .tmp/streaming-call-before.json
python toolkit/test_streaming_lzsa2.py --noncanonical --long-copy --output .tmp/streaming-call-after.json
python libraries/tests/summarize_long_copy_streaming.py --directory .tmp --output libraries/evidence/long_copy_streaming.json
python -m unittest discover -s libraries/tests -v
```
