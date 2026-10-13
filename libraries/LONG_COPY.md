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
and long-match kernel. Extended literals are >=18 bytes, extended matches
>=24, and 16-bit forms >=256. Sixteen forward LDIs therefore leave nonzero
BC for LDIR. Short tokens/EOD never take these kernels. Forward copying
preserves distance1/2 overlap and the existing token-boundary overshoot.
AF' remains the nibble reservoir. Matches save the input HL on the existing
private stack and load the shared offset operand as data, avoiding an extra
offset store on every token. Guards establish readable input before copying.

The following costs use Zilog UM0080, N=copied bytes, and include the
specified branch/continuation endpoints. LDIR contributes21N-5 T.

| Path/endpoints | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Ordinary long8 literals: branch from ManyLiterals through OR A | 21N+16 | 21N-46 | -62 T |
| Ordinary long16 literals: JP after reading high byte through OR A | 21N+15 | 21N-45 | -60 T |
| Guarded long8: JP from guard to copy through OR A | 21N-1 | 21N-61 | -60 T |
| Guarded long16: JP from guard to copy through OR A | 21N+9 | 21N-61 | -70 T |
| Complete streaming long8 / long16 bypass | prior path | prior path-60 | -60 T |
| Long8 match: LD C,A through POP HL | 21N+36 | 21N-23 | -59 T |
| Long16 match: PUSH HL through POP HL | 21N+32 | 21N-27 | -59 T |

Examples:18-byte ordinary literals394 ->332 T; 256-byte ordinary literals
5391 ->5331 T; 24-byte long8 matches540 ->481 T. Unchanged short paths
have delta0 T. The six extra-T cost of reading `LD HL,(offset)` and both
helper jumps are included; these are not naive5N savings.

Ordinary prefix/core sizes134/250 ->134/339 bytes (+89); CALL-guarded
224/254 ->224/342 (+88); direct222/251 ->222/339 (+88). No new state,
stack, tables, packets, compressed bytes or sectors. Ordinary core ends at
0x8f33 in bank2; the default 0x8ef7 limit cannot hold it. Reserve the larger
range explicitly and check the application's other allocations. No player
layout or default codec profile is changed.

## Complete verification and decision

- [Native comparison](evidence/long_copy_native.json):77 complete blocks,
  618746 output bytes, 21 authenticated real blocks plus24 boundary and32
  seeded random streams. CPU26320517 ->26242238 T (-78279); real blocks
  19412006 ->19385952 T (-26054,0.134%). Zero slower blocks/slices;
  230 accepted synthetic interrupts and exact output with IRQ.
- [Streaming comparison](evidence/long_copy_streaming.json):24 full cases
  in both guard modes, six shared-memory input placements each, byte-exact
  EOF, no unloaded/overwritten input/history, identical waits and165 sectors
  read exactly once. Direct component4144763 ->4143045 T (-1718);
  CALL component4147449 ->4145731 T (-1718). Each producer is unchanged:
  direct533509 T, CALL535745 T.
  These compare the same guarded decoder before/after unrolling.
- All31 default generated layouts retain their exact bytes and labels.
  Portable/native tests cover relocation, all literal/match length transitions,
  overlap, poisoned caller registers, export and partial/complete guard updates.
  All12 library tests and66 existing toolkit regression tests pass.

**Decision: optional measured candidate.** The real CPU benefit is small;
the additional bank2 space needs application accounting. No ROM/physical
disk/ULA or full publication run is measured here, so this cannot replace a
release profile. ZX0 already has bounded refill unrolling; applying the same
16-LDI prefix to arbitrary ZX0 lengths would underflow BC on short copies.
Keep its existing bounded profile until a separate useful candidate is scoped.

Reproduce from the repository root with the optional native dependencies:

```powershell
python libraries/tests/measure_long_copy.py --output libraries/evidence/long_copy_native.json
python toolkit/test_streaming_lzsa2.py --direct-header --output .tmp/streaming-before.json
python toolkit/test_streaming_lzsa2.py --direct-header --long-copy --output .tmp/streaming-after.json
python toolkit/test_streaming_lzsa2.py --output .tmp/streaming-call-before.json
python toolkit/test_streaming_lzsa2.py --long-copy --output .tmp/streaming-call-after.json
python libraries/tests/summarize_long_copy_streaming.py --directory .tmp --output libraries/evidence/long_copy_streaming.json
python -m unittest discover -s libraries/tests -v
```
