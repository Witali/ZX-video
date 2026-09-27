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

For this speed work, keep the compressed movie stream byte-for-byte
unchanged. Count bootstrap/code size separately: a larger bootstrap can
still add disk sectors. Use all 128 KiB as useful, while accounting for both
screens, code, stack, AY/IRQ, TR-DOS workspace, tables and disk buffers.

## Current baseline and evidence

Use the HL-reader configuration measured at `074e1e7`; the source also
contains later experimental options. Do not equate this configuration with
the generic converter's defaults or the root release images.

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
   inline-patch optimizations already present.
3. **Optimize pixel conversion and addressing.** Dense pixel work alone
   costs 136,520,064 T. Try reuse of addresses/lookup results while retaining
   the exact dither output and alternate-screen dependencies. Count writes,
   row/page transitions and ULA effects, not just dispatch instructions.
   Two extra dense-output tests have already been rejected below.
4. **Revisit producer scheduling only with a cheaper input guard.** The
   streaming prototype shortens some disk bursts but adds too much CPU.
   Preserve EOF handling, unloaded-page protection, one-sector steps and
   IRQ safety. Measure the complete producer/consumer schedule before
   accepting a changed disk buffer or queue policy.

A small concrete candidate for step 1 is the target setup for nonzero
motion phases. Currently `LD HL,(target); PUSH HL; EXX; POP DE; EXX` costs
**45 T**. Loading alternate DE directly with
`EXX; LD DE,(target); EXX` would cost **28 T**, if the common HL load moves
to phase zero and no additional preservation is needed. The profile contains
28,773 such entries: setup **1,294,785→805,644 T**, estimated **-489,141 T**.
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
