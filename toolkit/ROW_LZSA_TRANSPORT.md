# Faster transport for exact five-level row video

2026-09-30. Baseline `c6b8475`, same 192-frame montage: 64 frames starting
at source positions 629, 2857 and 3855. Same 172-entry row dictionary,
FAP3 fragment allowance 16, native pixels, attributes and 50 Hz AY.

**Decision:** retain LZSA2 as a separate measured experiment. It improves
delivery, but neither timing gate passes. Generic encoding remains unchanged.
The root `ZX-video-five-level-lzsa2-test.trd` is independently bootable and
stored in LFS. It is not a full-movie release or a three-disk capacity result.

## Comparison

| Measurement | Adapted Fast ZX0 | Resumable LZSA2 | Difference |
|---|---:|---:|---:|
| Compressed video bytes | 148971 | 154956 | +5985 (+4.02%) |
| Runtime sectors | 582 | 606 | +24 |
| Total occupied disk sectors | 633 | 653 | +20 |
| Decoder CPU T-states | 25185674 | 19844626 | -5341048 (-21.21%) |
| Producer CPU T-states | 1024996 | 1058423 | +33427 |
| Decoder + producer CPU T-states | 26210670 | 20903049 | -5307621 |
| Actual mean fps, normalized to 50 Hz | 7.126866 | 7.449298 | +4.52% |
| Missed nominal deadlines | 145 | 135 | -10 |
| Maximum late fields | 194 | 137 | -57 |
| Invalid actual fallback intervals | 28 | 27 | -1 |

CPU uses fixed 256-byte demands, mocked ROM and a frozen service clock.
Every executed decoder instruction is checked against the Zilog timing table;
histograms, absolute counts and block quotas are archived. This is a component
comparison, not a replay of the full queue schedule. Packet copies alone cost
at least 5183040 T (323940 decoded bytes x 16-T LDI), excluding control/paging.

Separately, real Fuse transfer time falls 45170386 -> 39637293 elapsed T.
Observed disk read windows grow 18274347 -> 18969484 T; seeks are
422189 -> 421025 T. These windows include ROM, physical latency and IRQ/ULA.
Do not add them to deterministic CPU totals: their scopes overlap.

The final late runs are 43..49 (recovers at 50), 56..58 (recovers at 59),
and 67..191 (never recovers). Maximum drift is 2.74 s. No frames are dropped.
The priority remains zero late frames on the original six-field schedule.

## Implementation and memory

- Use raw LZSA2 blocks on the same 15872-byte boundaries. Bootstrap remains
  ZX0. Three input/output banks 0/1/3 and the existing carry buffer are unchanged.
- Reuse retired Fast decoder regions: prefix/state `7C00..7C85` (134 bytes),
  core `8DE0..8EE0` (257 bytes). Total 391 versus 401 bytes; no new buffer.
  The core remains in uncontended bank 2. Screens, AY and frame workspace keep
  their baseline allocation. The existing private stack remains at `7BE0`.
- Preserve AF' with the coroutine context; it holds the spare nibble. Resume
  at token boundaries. Finish EOD before yielding when a match reaches the
  block end, including when it overshoots an earlier requested quota.
- All external operand changes have 0 T instruction delta. Reassemble the
  producer independently to verify every reference and refresh the cold
  bridge overlay. Metadata retains the previous decoder and new listing.
- Maximum measured 256-byte-demand slice is 20105 T on this montage.
  Long literal/match tokens can take much longer on other input. Token-boundary
  suspension is not a universal duration bound; do not enable it blindly for
  arbitrary clips without delivery measurements.

The decoder is an explicitly altered port of spke & uniabis's fast decoder,
from Emmanuel Marty's LZSA repository at commit
`15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5`. Original source and the zlib license
are retained in [third_party/lzsa](third_party/lzsa). The host reference is
independent; author-side blocks are also decoded by the upstream executable.

## Verification and corrected attempt

- All 21 blocks: native exact output/input cursors, shared-memory overlap
  proof, sector order and protected banks; poisoned registers between slices.
- 27 additional deterministic cases: 1..15872-byte constants, incompressible
  literals, lengths around nibble/byte/word transitions, offsets around
  32/512/8704, and a short disk-read retry. Every byte is checked.
- This found a prototype bug: a 257-byte match satisfied quota 256, then the
  next call skipped the EOD marker. The output pixels were correct but the
  input contract failed. Fix: recognize actual block end before suspension.
  Initial host parsing also rejected a legal first repeat-offset EOD, which
  needs no match history; validation now rejects it only for a real match.
- Preserve preliminary CPU/Fuse reports separately. After the fix, rerun
  component counts, cold boot/priming and complete actual playback.
- Final Fuse: all 192 publications through EOF, 606 runtime sectors, 1152 AY
  ticks, no audio underruns, gaps or duplicates; 80 pixel bytes checked/frame.
- Six separate full-screen captures at 0/1/63/64/128/191: all 41472 bytes exact,
  including progress and both screen banks. Timing uses a separate continuous run.
- Existing all-frame host/native reconstruction evidence is reused because
  the uncompressed FAP3 bytes and row dictionary are identical. No quality
  re-quantization or new full-movie search was performed. No physical drive test.

## Reproduce and continue

Use the saved states from `five_level_test_evidence/states.npz` and the raw/
metadata archives in [row_lzsa_evidence](row_lzsa_evidence). Extract the gzip
files to a temporary directory. Summary and hashes:
[row_lzsa_optimization.json](row_lzsa_optimization.json).

Run `profile_row_transport.py` for the baseline, `probe_row_lzsa.py` for the
size/round-trip comparison, then `benchmark_row_lzsa.py` and `test_row_lzsa.py`.
Each script lists its required paths with `--help`. `build_row_lzsa.py` consumes
the existing FAP3 raw, states and row metadata plus the unchanged options in
`fast_zx0_player_build.json`; it performs cold boot and priming checks.
Run `measure_fap3_fuse.py --trace-pipeline`, `profile_row_playback.py`, then
`summarize_row_lzsa.py` to save the image and full captures. Run Fuse sequentially.

Next bounded question: can packet consumption avoid copying from the decoded
slot into the packet buffer? Reuse these exact blocks and publication trace;
first account for cross-block packets, slot ownership and AY interrupt paging.
Measure one candidate before any whole-movie build or codec sweep.
