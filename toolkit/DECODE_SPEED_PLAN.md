# Decode-speed improvement plan

Updated 2026-09-27. This is the current plan in English. Earlier proposals
and their dated results remain in the [historical plan](DECODE_SPEED_PLAN_ru.md)
and [changelog](../CHANGELOG.md).

## Objective and acceptance criteria

Fit the authorized edit in [movie_no_credits.json](movie_no_credits.json) on
at most three independently bootable TRDs. Preserve the main story and
post-credit scene through EOF, resolution, 25/3 fps and the existing 50 Hz
AY soundtrack. This fixture has 4221 frames. The converter and optimizations
must also support other videos; do not specialize player behavior to a scene.

Prepare each frame for publication at its nominal six-field deadline:
120 ms, zero late frames. Report every missed deadline. Separately check
the fallback of at most one field late, intervals of 5..7 fields and recovery
to the original schedule without dropped frames or accumulated drift.
Measure actual screen-publication OUT timing as well as field counters.
AY must update on every 50 Hz interrupt. A partial run cannot pass.

For local decoder substitutions, keep the compressed movie stream byte-for-byte
unchanged. The separately measured resident-audio format below changes
framing while preserving every video field and AY record. Count bootstrap/code size separately: a larger bootstrap can
still add disk sectors. Use all 128 KiB as useful, while accounting for both
screens, code, stack, AY/IRQ, TR-DOS workspace, tables and disk buffers.

## Current baseline and evidence

Use the [foreground resident-AY player](RESIDENT_AUDIO_PLAYER.md) at
`da369e6` as the current smaller experimental baseline. It fits three
independent disks and delivers all AY records at 50 Hz, but video timing
still fails. The HL-reader configuration at `074e1e7` and the subsequent
measurements below remain historical comparisons. Do not equate any of
these configurations with generic converter defaults or root release images.

- Stream: **1,919,945 compressed bytes**, 3,083,375 packet bytes, 378 blocks,
  7501 video sectors. Tables are per volume; each disk initializes its own
  state. A compact predictor references frame n-1 while native-screen masks
  reference n-2. Removing an intermediate buffer must preserve both.
- The full HL-reader Fuse run still fails timing: 3073 late frames, 883 AY
  underruns, 660 intervals outside the fallback range. Per-volume rates:
  8.2823025 / 7.9802956 / 7.8841952 fps. All three reach EOF.
- Streaming ZX0 input integration and its full measurements are recorded
  in `8da95ed`.
  It preserves stream bytes but increases the summed publication span from
  1,854,669,649 to 1,863,745,874 T and AY underruns from 883 to 1006.
  Keep `--streaming-input` disabled. See the
  [saved summary](streaming_player_summary.json) and
  [historical implementation report](STREAMING_PLAYER_ru.md).
- The new [full CPU-stage profile](FRAME_HOTSPOTS.md) covers all 4221 frames
  with exact compact data and both complete screens. It totals
  **1,027,719,624 T**: reconstruction 60.36%, output 32.85%, metadata 6.19%.
  This excludes ZX0, copying, queues, IRQ/AY, ULA, ROM and disk latency.
- The [compact cursor experiment](COMPACT_CURSOR.md) now completes all
  4221 frames and all three Fuse volumes. Byte updates within a stripe save
  **4,355,295 deterministic frame T-states** with unchanged compressed data,
  code size and disk layout. AY underruns fall 883→869 and summed publication
  span falls by 1,063,621 T, but bad intervals rise 660→662. Retain
  `--compact-cursor` for measured work and keep both this result and HL-only
  as comparison points; it is not a release and does not pass timing.
- The [two-byte Huffman cache prototype](CACHED_HUFFMAN_LOOKAHEAD.md) uses
  E' for lookahead and moves the motion output cursor to HL'. All 4221 CPU
  frames and both complete screens match. Against compact cursor it saves
  **5,315,088 T** (0.5194% of measured frame stages); 55 frames are slower,
  by at most 50 T. The subsequent [disk integration](LOOKAHEAD_PLAYER.md)
  now enforces a 4702-byte payload limit and two readable guards in the
  existing 4704-byte window, at zero parser CPU or stream cost. All three
  independently bootable volumes complete: 3066 late frames, 845 AY
  underruns, 644 invalid fallback intervals. The summed publication span
  improves by 1,701,794 T with unchanged disk layout. Keep the optional
  cache for measured work; all three timing gates still fail.

## Method: replace indexed access when the whole path is faster

Inspect the generated machine code and measured execution frequency.
Compare IX/IY memory operations with ordinary registers, `(HL)` or direct
addressing. Include address setup, cursor advances, all saves/restores,
branches, code size and extra stack depth. Check live flags and both register
sets across IRQ, calls and paging.

Representative instruction costs, excluding waits and IRQ, from the
[Zilog Z80 CPU manual](https://www.zilog.com/docs/z80/um0080.pdf):

| Operation | Alternative | T before → after |
|---|---|---:|
| `LD r,(IX+d)` | `LD r,(HL)`, address already prepared | 19 → 7 |
| `LD A,(IX+d)` | `LD A,(nn)`, constant address | 19 → 13 |
| `INC IX` | `INC HL`, equivalent cursor | 10 → 6 |
| `LD IX,(nn)` | `LD HL,(nn)` | 20 → 16 |
| Repeated indexed load | Reuse an ordinary register | 19 → 4 |

Do not sum these instruction savings without their surrounding code.
HL already addresses Huffman tables. SP must remain usable by IRQ; treating
input data as a stack risks corruption or long interrupt-disabled periods.

The completed HL-reader substitution is the reference example:
68 repetitions of `LD A,(IX+0); INC IX` (29 T) became
`EXX; LD A,(HL); INC HL; EXX` (21 T). Preserving HL' and setting up cursors
adds 45 T per call: **68 * -8 + 45 = -499 T/frame**, measured for every
frame, **-2,106,279 T** total. Compressed bytes and video sectors are unchanged.
See [the saved verification](hl_mask_reader_summary.json).

## Prioritized work

0. **Decouple AY delivery with a complete resident soundtrack.** The
   [resident-audio prototype](RESIDENT_AUDIO.md) stores each volume's exact
   AY records, tables and initial state in 13279/12262/12080 bytes. Video-only
   ZX0 plus that audio totals **1869817 bytes**, **50128 fewer** than the
   existing mux; all 4221 packets and 25326 ticks round-trip. Estimated free
   sectors with old fixed overhead were 71/66/63. The
   [actual integrated TRDs](RESIDENT_AUDIO_PLAYER.md) now leave **68/65/65**
   sectors free, with dirty-RAM boot and mocked swaps verified. The
   [Z80 decoder and paging bridge](RESIDENT_AUDIO_Z80.md)
   execute all 25326 records exactly. Code, expanded tables and data fit
   in **14230/13215/13037 B**, leaving at least **2154 B** in bank 4.
   The integrated format uses the audio-free parser, three video slots in
   banks 0/1/3, fixed bridges in retired code and bounded startup sections.
   Queue-only six-record service failed with 3830 AY underruns. Adding
   foreground service and increasing the batch limit to 31 eliminates all
   sound gaps through EOF on all three disks: **25326 exact ticks at 50 Hz**.
   The ISR is unchanged. The six-record CPU fixture still reports producer
   **9150603→52600652 T (+43450049)**; it is not the new scheduling total.
   Actual video sectors fall **7501→7158** and summed publication spans fall
   **1851904234→1816733868 elapsed T**. There are still **1745 late frames**
   and **1047 invalid fallback intervals**. Maximum lateness is 103/291/291
   fields; late runs recover 5/3/6 times, but disks 1/2 end late. Average
   8.333333 fps on disk 3 does not establish smooth playback.
   Obtain a complete new CPU replay and retain read/seek intervals separately.
   The [half-row cache integration](HALF_ROW_PLAYER.md) now completes all
   CPU frames and all three disks: frame stages save **15980003 T**, parser
   copies add **333459 T**, and ZX0 adds **7583 B / 30 runtime sectors**.
   Actual occupied sectors grow by 40; 53/52/53 remain free. Sound stays
   exact at 50 Hz, but late frames improve only **1745→1740**, with 1043
   fallback interval violations. Keep it optional and preserve the smaller
   baseline. The subsequent [uncontended half-row body experiment](UNCONTENDED_HALF_COPY.md)
   moves the sixteen LDIs into 33 of the old selector's 38 unused bank-2
   bytes. CALL/RET adds 27 T per half-row, **2659824 T** across all 4221
   fully pixel-checked CPU frames. Complete Fuse playback leaves
   each publication span unchanged, increases late frames **1740→1741**
   and bad intervals **1043→1048**, with byte-exact streams and identical
   disk usage. Reject this placement as a speed improvement; preserve its
   evidence. Capacity and AY cadence pass; both video timing gates fail.
   The frozen-producer FIFO model does not establish that resizing the
   existing AY queue fixes starvation; do not infer missing byte availability
   from a queue call's end timestamp alone.
1. **Reduce repeated reconstruction state work.** Use the bank-aware
   histogram to inspect cache maintenance (112,146,097 T), control
   (66,807,315 T) and no-op traversal (74,830,741 T). Identify redundant
   address reloads and saves; retain the existing fast no-op and selective
   cache paths. Low-byte tile/run cursor updates are now implemented and
   verified; do not count their saving again. Record useful work separately
   from removable overhead. Prioritize larger remaining costs over repeated
   one-instruction changes with a small measured whole-player effect.
2. **Audit remaining Huffman indexed loads and call boundaries.** There are
   1,203,077 indexed memory loads in the profile. A hypothetical 19→7 T
   substitution saves 14,436,924 T before setup costs. Use this as a gross
   ceiling for those loads, not a promised saving. Keep cached-byte and
   inline-patch optimizations already present. The two-byte cache now has
   complete CPU and integrated disk measurements: short symbols save
   7..11 T, long symbols add 18 T and setup adds 46 T/frame. Its packet
   contract, cold-installed inline code, bootstrap sectors and complete
   three-volume delivery are checked. Preserve that work and do not count
   the saving again. For other videos, reject an oversized optional
   configuration or retain the old decoder. Future register-allocation
   changes must preserve the two-readable-byte limit and IRQ state.
3. **Optimize pixel conversion and addressing.** Dense pixel work alone
   costs 136,520,064 T. Try reuse of addresses/lookup results while retaining
   the exact dither output and alternate-screen dependencies. Count writes,
   row/page transitions and ULA effects, not just dispatch instructions.
   Dense-output dispatch and whole-row fill tests have already been
   rejected below. Avoid a runtime scan for uniform rows in this stream;
   successful rows are too rare even under a zero-cost-fill bound.
4. **Revisit producer scheduling only with a cheaper input guard.** The
   streaming prototype shortens some disk bursts but adds too much CPU.
   Preserve EOF handling, unloaded-page protection, one-sector steps and
   IRQ safety. Measure the complete producer/consumer schedule before
   accepting a changed disk buffer or queue policy.
   The two-byte-cache trace has 460/397/619 frames whose foreground stages
   exceed six fields, and no late frames already native-ready at least
   1000 T before the nominal deadline. Empty-input waits total 134,642,123
   elapsed T, including producer work and disk service. Use these traces
   to distinguish burst buffering opportunities from sustained CPU cost;
   do not label all wait time removable overhead or fix only publication.
   The [in-place ZX0 reservoir experiment](INPLACE_ZX0_RESERVOIR.md) now traces
   all bytes of all three resident-video streams at 8/12/15.5/16 KiB block
   sizes. **15872-byte blocks** safely increase decoded packet capacity from
   **24576 to 47616 bytes**, with minimum sector-placement margins of
   **255/257/255 bytes**. Video shrinks **1832196→1818909 B**, runtime sectors
   **7158→7106**. Full 16-KiB output is rejected: **180/183 blocks** overwrite
   unread input, even with exact-end placement. The old 16-KiB compression
   study used another stream and separate input storage and does not prove
   this layout. Preserve both results.
   All 364 old and 188 new blocks also pass native turbo decoding in separate
   and overlapping memory, with identical read/write traces and zero layout
   instruction delta. Larger blocks increase naked-decoder cost
   **160653056→162913389 T (+2260333)**. This excludes the coroutine, queue,
   carry copies, IRQ/ULA and disk waits; only integrated delivery can decide
   whether the reserve and sector savings repay that cost.
   The [integrated larger-slot experiment](INPLACE_SLOT_PLAYER.md) now builds
   and completes all three independent TRDs: **2461/2463/2462 sectors** used,
   **83/81/82 free**. It changes the output base and queue bias, handles split
   headers and the shared tail, and preserves live LZ history. The disk
   adapter advances regions at FFFF/0000, not E000; the new producer restores
   its owned slot. Full native producer/coroutine execution checks every
   packet byte and counts **200004910 -> 201404951 T (+1400041)** with a frozen
   idle clock, excluding ROM/IRQ/ULA and actual queue quotas.
   The first complete run exposes long-idle disk failures: 15 read retries,
   252 AY underruns. A 64-field pre-read SEEK/HLD check removes all retries,
   but successful reads can still wait about 0.64 seconds. The corrected
   complete run has **1496 late frames**, **914 invalid intervals**, and
   **24 AY underruns**, versus 1745/1047/0 in the smaller resident baseline.
   Preserve both attempts; neither is a release or cadence pass.
   Next add **periodic drive maintenance while the queue is full**, before
   idle shutdown, without consuming or rereading any sector. Count the
   extra queue checks and ROM service, test state/IRQ preservation, then
   repeat all three EOF runs. Larger decoded packet storage is not extra
   native-screen buffering and cannot establish cadence on its own.

A small concrete candidate for step 1 is the target setup for nonzero
motion phases. With the new cache,
`LD HL,(target); PUSH HL; EXX; POP HL; EXX` costs **45 T**.
Loading alternate HL directly with
`EXX; LD HL,(target); EXX` would cost **24 T**, if the common HL load moves
to phase zero and no additional preservation is needed. The profile contains
28,773 such entries: setup **1,294,785→690,552 T**, estimated **-604,233 T**.
The earlier DE' allocation gave a smaller 489,141-T estimate.
This is not implemented or IRQ-tested and will not alone resolve playback.
Verify generated placement and all phases before adopting it.

## Avoid repeating rejected or completed experiments

- The current stream already rounds bands with at least 18 changed cells
  to all-FF masks. A new nearly-dense test admits no extra bands and would
  add 531,846 T. A full-eight-cell helper with a new test on every nonzero
  group is estimated to add 1,056,003 T. Both are rejected; see
  [the probe and assumptions](FRAME_HOTSPOTS.md).
- Changing the encoder's density threshold is a separate stream-size
  experiment. It cannot be accepted from decoder cycles alone.
- Whole-row zero/uniform detection was measured on all 83,652 dense rows.
  Only 90 are zero and 332 uniform. Charging just immediate failures while
  making every other test and successful fill free still adds at least
  **1,314,132 / 1,022,816 T**. Reject these two dispatch strategies; this
  does not rule out partial-row methods or precomputed hints. See the
  [complete input profile and lower-bound calculation](FLAT_DENSE_ROWS.md).
- Uncontended compact/cache, compiled masks, cached Huffman bytes, inline
  ZX0 literals/matches, demand decoding, AY-wait prefetch, fast IM2 return,
  Gray-order sparse cells and black-border omission have already been
  investigated. Preserve measured benefits; do not present them as new.
- Removing zero-mask writes alone has a small gross bound and adds state
  checks. Packet-ready guards and current streaming input failed to improve
  the full delivery results. Keep their reports and disabled options.
- RLE, LZSA2 or other block codecs do not automatically retain ZX0's size.
  Reuse the [adaptive-codec results](ADAPTIVE_CODECS_RESULTS_ru.md) before
  proposing another format. Vector encoding remains deferred.

## Verification required for each implementation

1. Save the old and new generated instruction paths, their absolute Z80
   T-states, delta, assumptions, RAM layout and stack requirements.
2. Test meaningful boundaries and IRQ interruption points. Execute all
   frames and compare compact data, both complete screens, AY, cursors,
   buffer ownership and independent-volume startup. Verify stream hashes.
3. Build independently bootable images and check bootstrap size, total
   sectors and LFS rules. Do not replace release TRDs with an unverified
   experiment. Never require retained RAM from the preceding disk.
4. Run all volumes through EOF in Fuse. Report CPU separately from ROM,
   disk acquisition and contention. Check actual nominal deadlines,
   fallback bounds, recovery of late runs, AY continuity and sector order.
   State limitations of emulator timing and any missing physical-drive run.
5. Keep scripts, reports and unsuccessful attempts in the same focused
   commit as their changelog entry. Write maintained documentation and
   agent instructions in English; add Russian translations only on an
   explicit request for that document or task.
