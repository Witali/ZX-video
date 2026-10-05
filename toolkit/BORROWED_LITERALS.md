# Read literal fragments directly from LZSA2 slots

Maintenance, 2026-10-05: explicitly unsuccessful TRD payloads from this study were removed at the user's request. Reports, source snapshots and measurements remain historical evidence; [retirement identities and reasons](../docs/maintenance/2026-10-05-retired-trds.md) allow recovery. This does not change the original results.

2026-09-30, baseline `dacb24f`. **Adopt this optional, host-validated mode**
for temporal/whole-fragment streams. The unchanged 192-frame five-level test
improves from **7.478465 to 7.683025 fps** in a complete Fuse run. Exact 25/3
fps is still not achieved. No change to quantization, pixels, AY or runtime
compressed bytes; the general player remains available.

## Measured result

Same three 64-frame windows (source 629/2857/3855), 21 blocks, 172 row-table
entries and the existing fragment allowance of 16 bytes.

| Measurement | Previous | Borrowed literals | Delta |
| --- | ---: | ---: | ---: |
| Packet copy bridges, CPU fixture | 5511858 T | 1950856 T | -3561002 T |
| Full metadata/reconstruction/output CPU | 41965760 T | 43760146 T | +1794386 T |
| Combined component difference | | | **-1766616 T** |
| First-to-last publication, real Fuse | 90549516 T | 88138641 T | **-2410875 T** |
| Mean observed fps, normalized to 50 Hz | 7.478465 | 7.683025 | +2.74% |
| Missed nominal deadlines | 134 | 118 | -16 |
| Maximum late fields | 133 | 99 | -34 |
| Invalid actual fallback intervals | 24 | 24 | 0 |
| Runtime video | 154956 bytes / 606 sectors | same | 0 |
| Total occupied disk sectors | 653 | 653 | 0 |

The new paths avoid copying **226819 bytes** in 171/192 packets in the
component fixture. Prefixes include two readable Huffman lookahead bytes.
Twenty crossing packets and the final packet keep normal copying.
Both the two-byte packet length reads and payload reads are included in
the copy-bridge CPU measurement. Small suffixes also keep normal copying.

Paging/table bridges add 1794386 T to frame processing: 1022414 T of bridge
control and 771972 T in the existing atomic paging routine. Pixel output,
fragment reconstruction, Huffman decoding and metadata have unchanged
instruction totals. The aggregate saving includes that overhead rather
than claiming all avoided LDI work as a gain.

The component fixture supplies fully available blocks and excludes the
queue, LZSA2 execution, IRQ, ULA, ROM and physical drive service. Its sum is
not a complete integrated CPU model. Real Fuse measures actual scheduling
separately. Read windows change 18972412 -> 18967938 elapsed T; seek windows
421824 -> 420371 T. These nested windows must not be added again to playback
time. The publication span improves by about **0.680 seconds**.

## How it works

The old path copied every decoded packet from a slot to fixed bank 5 at
6400h, then read its literal suffix while reconstructing the compact frame.
The new queue-copy hook copies only the prefix: header, vectors, masks,
native map, Huffman data and two lookahead bytes. It retains a pointer and
bank number for the remaining literals. The packet parser still uses its
original field layout and virtual payload end.

Before reconstruction, the prepare bridge substitutes the literal pointer
and maps its slot. Compact frame writes remain in fixed, uncontended bank 2.
Nonempty Huffman patches and coded attributes temporarily select bank 6;
small paging bridges preserve AF/BC, including the cached Huffman byte.
Raw attributes continue to read the literal bank. Screen output is unchanged.

### Ownership and memory rules

- Enable the path only when one copy covers the entire packet body and the
  queue retains its slot. If a completed slot would be released, use the old
  copy path. With no completed slot, an active prefix stays owned until EOF.
- Crossing packets use ordinary copying. A subsequent length read clears
  the previous borrowed-bank state. There is only one pending packet; its
  compact reconstruction completes before the next packet is read.
- Background decoding may append to the retained slot and use its history;
  it must not overwrite already-produced literal bytes. No slot capacity,
  disk read buffer, block size, paging ABI or IRQ schedule is changed.
- The builder validates every video-only packet before installation:
  no motion-cache flag, and only vectors 0/85/86/87/88 (temporal retention
  and whole fragments). Other streams are rejected by this explicit
  experimental mode; use the normal builder for them.
- The validated absence of motion makes its native code region available.
  New code/state occupies **243 bytes** in bank 2 at `887B..88C3` and
  `897B..8A24`, below retained clear/patch handlers. This includes ten state
  bytes; no new data buffer is allocated. New nested paging bridges require
  up to eight extra stack bytes. The existing 96-byte frame-stack guard passes.
- The original three 16-KiB video slots (banks 0/1/3), AY bank 4, Huffman
  bank 6, screens and TR-DOS workspace remain allocated as before. Every
  disk still carries the code, table and initial state needed for cold boot.

Initial placements in presumed free areas at 7800h and DF00h were rejected
by occupied-memory guards before native execution: the resident-AY
initializer/input producer and the disk driver already use those areas.
The final placement uses the host-excluded motion body. The native format
check and the overwritten-region hashes are saved in build metadata.

## T-state accounting and verification

Every executed new instruction is checked against its generated Zilog
UM0080 timing row. Existing CALL/JP replacements retain 17/10 T respectively;
all additional costs are in the executed helpers. Original and new copy
bridges run against identical source bytes, region, destination and count.
The absolute totals and net delta are in the table above.

- All 192 full compact frames and both complete native screens match in the
  CPU model. Huffman/literal cursors, fixed inputs, borrowed banks, screen
  history, stack bounds and TR-DOS workspace are checked.
- 45 additional native copy cases cover all three slots, short suffixes,
  the two lookahead bytes, active prefixes and completed-slot release.
  Candidate calls start with a stale borrowed-bank marker to verify reset.
- Five host contract tests include eight rejected motion/spatial vectors,
  the motion-cache flag, truncated bodies and invalid prefix lengths.
- Cold dirty-RAM boot and first-native/second-compact priming pass. Full Fuse
  reaches EOF, checks all 606 runtime sectors and all 1152 exact AY ticks,
  with no audio underruns, missing ticks or duplicates. Eighty pixel bytes
  per frame pass. Six separate full Fuse captures check all **41472 bytes**,
  including attributes and progress, at frames 0/1/63/64/128/191.
- During verifier setup, the block-list length and host-write guard state
  were corrected; the successful retained runs follow those fixes. The
  native candidate did not change after its successful cold-boot build.

**Both timing gates still fail.** Frame 43 recovers at 44, frame 67 at 68,
but run 76..191 stays late through EOF. Maximum lag is 99 fields / 1.98 s.
No frames are dropped. Exact AY records do not imply synchronization with
late video. This is a 192-frame experiment, not full-movie or hardware proof.

## Artifacts and reproduction

- [Native builder](borrowed_literals.py), enabled by
  `build_row_lzsa.py --borrow-literals`; the default is unchanged.
- [CPU and copy verifier](verify_borrowed_literals.py),
  [host contract tests](test_borrowed_literal_contract.py),
  [capture/archive script](summarize_borrowed_literals.py).
- [JSON summary](borrowed_literals_profile.json) links hashed reports,
  generated code, instruction timings and complete Fuse traces under
  [borrowed_literals_evidence](borrowed_literals_evidence).
- Updated optional [LFS test disk](https://github.com/Witali/ZX-video/blob/d0e47315262e09db9ceae70e90281fcce0d58c1b/ZX-video-five-level-lzsa2-test.trd),
  SHA-256 `14788fa7b7272c1d8ae4d47e63804cd60998d8ee95032ce56c879a120226e2d5`.
  Runtime compressed stream stays
  `1c8f598fa5fcc4ba2ac5f60355f6b3845cf5d8aa89f2ded328f5f98dd1b21bbc`.

Use archived FAP3 `row_lzsa_evidence/fap3-video.raw.gz`, row states
`five_level_test_evidence/states.npz`, `lzsa2_dispatch_evidence/metadata.json.gz`
and `fast_zx0_player_build.json`. Run the existing build command with
`--borrow-literals`, the expected raw/video SHA options and a separate output
directory. Run the verifier with `--raw`, decoded `--video`, `--states`,
candidate `--metadata`, and `--output`. Then run `measure_fap3_fuse.py` with
`--trace-pipeline`, followed by the capture/archive script. Python dependencies
are unchanged; use the PYTHONPATH in [the preceding profile](LZSA2_STAGE_PROFILE.md).

**Next:** reduce native pixel writes/address computation, which still costs
20246890 CPU T on this fixture. Preserve five brightness levels, exact bytes,
both screen histories and independent boot; measure total delivery again.
Keep the full movie and every-volume timing checks as the eventual goal gate.
