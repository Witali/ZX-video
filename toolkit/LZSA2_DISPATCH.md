# Faster LZSA2 token dispatch

2026-09-30; baseline `afc18fc`. **Adopt the restored S/P flag dispatch** in
[resumable_lzsa2.py](resumable_lzsa2.py). This recovers an optimization
already present in the credited spke & uniabis upstream decoder. Our port
had replaced it with slower comparisons because its component CPU only
modeled carry and zero. Improve the verifier rather than paying that cost
on the actual Spectrum.

## Results on the unchanged 192-frame fixture

The same archived 21 blocks, 323940 decoded video bytes, 172-entry row
dictionary, FAP3 fragment allowance 16 and original 50 Hz AY are used.
The runtime stream remains exactly 154956 bytes, SHA-256
`1c8f598fa5fcc4ba2ac5f60355f6b3845cf5d8aa89f2ded328f5f98dd1b21bbc`.

| Measurement | Previous LZSA2 | Flag dispatch | Difference |
| --- | ---: | ---: | ---: |
| Decoder CPU T-states | 19844626 | 19412006 | -432620 (-2.1800%) |
| Producer CPU T-states | 1058423 | 1058423 | 0 |
| Decoder + producer CPU T-states | 20903049 | 20470429 | -432620 |
| Decoder bytes including state | 391 | 384 | -7 |
| Maximum observed 256-byte-demand slice | 20105 T | 19609 T | -496 T |
| Runtime video sectors | 606 | 606 | 0 |
| Total occupied disk sectors | 653 | 653 | 0 |
| Fuse mean fps, normalized to 50 Hz | 7.449298 | 7.478465 | +0.3915% |
| First-to-last publication span | 90904059 T | 90549516 T | -354543 T |
| Missed nominal deadlines | 135 | 134 | -1 |
| Maximum late fields | 137 | 133 | -4 |
| Invalid actual fallback intervals | 27 | 24 | -3 |

Deterministic CPU counts use fixed 256-byte demands and mocked disk service,
excluding ROM, IRQ and ULA contention. The separate full Fuse run executes
the real TR-DOS ROM, disk timing and IRQ/ULA behavior. Observed read windows
increase 18969484 -> 18983778 elapsed T, and seek windows 421025 -> 422033 T;
they overlap other elapsed scopes and must not be added to CPU counts.
The complete publication span still improves, so the CPU saving survives
the disk-delivery check.

**Both release timing gates still fail.** Late runs now cover 43..49
(recovery at 50), 56..57 (recovery at 58), and 67..191 (no recovery by EOF).
Maximum drift is 2.66 seconds. No frames were dropped. This is an optional
192-frame experiment, not smooth 8 1/3 fps or a full-movie capacity result.

## Exact instruction accounting

`AND 24` produces even parity for token literal bits `00` and `11`, odd
parity for `01` and `10`. Use `JP PE` to share the exceptional path, then
`JR NZ` to distinguish extended literals. Reuse the sign flag from
`OR (HL)` for the no-literal offset split; after literal copying, replace
`CP 128` with `OR A; JP P`.

Counts below cover token selection and the common high-bit offset split,
excluding identical literal length parsing/copy work and subsequent offset
parsing. Timings are from Zilog UM0080: logical register op 4 T, memory or
immediate logical op 7 T, `CP n` 7 T, conditional `JP` 10 T, conditional
`JR` 7/12 T, `INC HL` 6 T and `LD A,(HL)` 7 T.

| Literal class | Previous dispatch | New dispatch | Delta/token | Tokens |
| --- | ---: | ---: | ---: | ---: |
| None (`00`) | 54 T | 54 T | 0 T | 20694 |
| One/two (`01`/`10`) | 58 T | 38 T | -20 T | 19683 |
| Extended (`11`) | 58 T | 50 T | -8 T | 4870 |

Prediction: `19683*20 + 4870*8 = 432620 T`; the executed instruction
histograms and independent native core agree exactly. The no-literal path
has an extra 7-T untaken `JR`, compensated by removing its 7-T `CP 128`.
For the word-length literal path the common offset split has the same
3-T saving; unchanged work is excluded consistently from the table.

The core shrinks from 257 to 250 bytes at `8DE0..8ED9` inclusive, remaining
in uncontended bank 2. Prefix/state stays 134 bytes at `7C00..7C85`; private
stack stays at `7BE0`. Buffers, paging, quota/EOD behavior and the AF'
nibble reservoir keep the prior contract. No new buffer or stack entry.

## Verification

- All 21 banked component blocks retain exact output/input cursors,
  in-place overlap proofs, protected screens/banks and sector order.
  Every executed decoder instruction is matched to its timing-table row.
- All 27 existing edge cases pass, including lengths around nibble/byte/
  word transitions, offsets around 32/512/8704 and a short disk read.
- The component CPU gains narrowly scoped logical sign/parity handling
  in [lzsa2_test_cpu.py](lzsa2_test_cpu.py). It rejects unsupported flag
  flows; it does not pretend to implement general arithmetic overflow.
- [Independent native validation](verify_lzsa2_dispatch.py) uses `z80==1.2.0`
  with full CPU flags. For all 21 blocks, both old and new generated code
  produce exact bytes and **every slice's cycle count** matches the first
  emulator. Repeated runs with synthetic register-preserving IM1 interrupts
  pass: 185 baseline and 184 candidate injections. Caller registers are
  poisoned between slices. Sign/parity identities cover all 256 token bytes.
  Synthetic 100000-T emulator events are not the production 50-Hz clock.
- Independent cold boot and priming pass. Full Fuse playback reaches frame
  192/EOF, reads all 606 runtime sectors and verifies all 1152 AY ticks
  without underruns, gaps or duplicates. Eighty pixel bytes per frame pass.
- Six separate full screen captures at 0/1/63/64/128/191 match all **41472
  bytes**, including attributes and disk progress. The timing run is separate
  and uninterrupted. No physical-drive or full-movie test is claimed.

An initial disk build used an already changed `.tmp/row-fragments/video.raw`:
its hash differed from the archived baseline and its video size was 115271
bytes. It was rejected before playback comparison. Its build report is
archived as `wrong-fixture-build.json.gz`; it is not evidence of decoder
compression savings. The final build uses the archived FAP3 input hash
`198971aa8c9721afa876fe57101dfd021590132574baf636f4b090f536c8988c`.
Optional expected input/video hash arguments now reject such scope mistakes.

## Reproduction and saved evidence

Extract `fap3-video.raw.gz`, `fast_zx0-metadata.json.gz`, `video.raw.gz` and
`video.stream.gz` from `row_lzsa_evidence` into a temporary directory.
Use `five_level_test_evidence/states.npz` and `fast_zx0_player_build.json`.
Dependencies: repository `requirements.txt` and `requirements-lzma-z80.txt`.

1. Run `benchmark_row_lzsa.py` on the archived stream/decoded raw, and
   `test_row_lzsa.py` with the pinned LZSA compressor.
2. Run `verify_lzsa2_dispatch.py --cpu <cpu.json> --output <native.json>`.
3. Run `build_row_lzsa.py` with archived FAP3 raw/metadata and the two
   `--expected-raw-sha256` / `--expected-video-sha256` values above.
4. Run `measure_fap3_fuse.py --trace-pipeline` on the resulting disk with
   the same FAP3 raw and states. Do not run concurrent Fuse instances.
5. Run `summarize_lzsa2_dispatch.py` with `--work`, `--fuse`, `--states`,
   `--evidence`, `--output` and `--trd` to verify six full captures, retain
   reports and update the optional experimental image.

The [summary](lzsa2_dispatch.json) links hashed evidence under
`lzsa2_dispatch_evidence`, including old/new instruction counts, generated
code in build metadata, native results and actual publication traces.
`ZX-video-five-level-lzsa2-test.trd` is updated in Git LFS, SHA-256
`adc85a5bcf8b56ca1a301818e0536d34e9262a4a8064b91d155294223018dbfd`.
The previous comparison and artifacts remain in Git history and
[ROW_LZSA_TRANSPORT.md](ROW_LZSA_TRANSPORT.md).

Next work remains packet-copy reduction. Match copying is also substantial,
but adopting an unrolled loop would require a separate size/length-distribution
and real delivery check; this finite change does not start another sweep.
