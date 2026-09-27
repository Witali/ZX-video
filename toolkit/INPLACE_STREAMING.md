# Sector-streaming input in the larger ZX0 reservoir

Date: 2026-09-27. Baseline: `a84451d`, the complete-input, periodic-drive
resident-AY player. Scope: all 4221 authorized frames on three independently
bootable disks, unchanged resolution, 25/3-fps deadlines and exact 50-Hz AY.

**Rejected as the default.** Every decoded byte remains exact and AY passes
50-Hz delivery, but late frames increase **1321 -> 1457** and invalid fallback
intervals increase **783 -> 943**. Both video timing gates still fail. Keep the
complete-input keepalive player as the current experimental baseline. Root
release images are unchanged.

## Implementation and memory

[The optional installer](inplace_streaming_player.py) reuses the prior
[page-suspended decoder](streaming_inline_zx0.py), with output moved from
E000 to C000 at unchanged **10 -> 10 T**. The same 188 ZX0 blocks, each at
most 15872 decoded bytes, occupy banks 0/1/3. Both screens, AY bank 4,
dictionary bank 6, stacks and disk workspace keep their previous allocation.

[A 49-byte producer wrapper](inplace_streaming_core.py) exposes each loaded
sector prefix. It performs at most one successful sector read per step.
The input frontier uses the producer's next destination page, including its
FFFF-to-0000 wrap, rather than the disk adapter's wrapped slot cursor.
The final carry sector is saved before reporting all input loaded. It need
not be saved before decoding starts: output ends at FDFF and the tail sector
remains at FF00. Native execution checks that every new sector preserves
already produced bytes and that no decoder read crosses the loaded frontier.

The decoder grows **314 -> 462 bytes**, reusing the split 7C00/7C31/8DF2
reservations. The wrapper ends at 7CF7, before the producer at 7D50. The
streaming queue ends at E163 and its demand helper at E294, before the
compiled-mask initializer/runtime at E180/E300. The existing three-slot
rotation and all five resident-AY/drive service hooks remain active. The
cold overlay at A200 is rebuilt with the final 6100 bridge.

Queue phase 3 supplies one missing input sector; the next step resumes
decoding. The explicit ZX0 `finished` flag controls block release. Producing
the last output byte is insufficient when the end marker has not arrived.

## Deterministic CPU measurements

[All 188 old/new block pairs](inplace_streaming_cpu.json) execute the actual
sector/header/carry code and decoder in a Z80 interpreter. ROM calls are
mocked; the idle clock is frozen. Counts exclude IRQ, ULA, physical disk
latency, frame reconstruction, AY service and the integrated queue. Actual
old/new disk starts are respectively 107/108/109 and 108/109/110.
Instruction histograms are checked against the Zilog instruction table.

| Component | Complete input | Streaming input | Difference |
|---|---:|---:|---:|
| Producer | 11,831,304 T | 12,970,065 T | +1,138,761 T |
| Decoder | 189,573,555 T | 208,485,649 T | +18,912,094 T |
| Combined | 201,404,859 T | 221,455,714 T | +20,050,855 T |
| Sector reads | 7,106 | 7,106 | 0 |
| Carry bytes copied | 96,256 | 96,256 | 0 |

The combined CPU increase is about **9.96%**. All 188 blocks produce output
before complete acquisition; there are 6915 input waits. Input read cursors
at every output write match the independent host ZX0 trace. No full-block
copy is introduced, but no existing packet/carry copies are removed either.

The first measurement used the old disk starts for both variants and found
221,456,053 T for streaming. The final report uses the actual new starts and
adds independent instruction-table validation; decoder work is identical,
and producer work differs by 339 T because of disk placement. This was a
measurement refinement, not another player variant or a cadence result.

[Isolated queue-control counts](inplace_streaming_queue_cpu.json) execute
the actual cold-loaded old/new code. They include CALL instructions and
internal queue routines, but intercept external decoder, producer, copy and
AY/drive bodies. Do not add these cases as though they were a playback trace.

| Control path | Before | After | Difference |
|---|---:|---:|---:|
| Full queue returns idle | 75 T | 75 T | 0 |
| Begin next block | 172 T | 172 T | 0 |
| Header not ready | 96 T | 113 T | +17 T |
| Begin decoder after input ready | 169 T | 250 T | +81 T |
| Background decode, more output remains | 302 T | 328 T | +26 T |
| Background decode reaches EOF | 562 T | 578 T | +16 T |
| Copy/release complete ready slot | 764 T | 764 T | 0 |
| Copy ready partial prefix | 808 T | 891 T | +83 T |
| Consumer needs decoder work | 1240 T | 1362 T | +122 T |

New input-wait paths cost 321 T to suspend a background decode, 112 T to
supply a sector, and 1837 T for a consumer request requiring input and decode,
with the same callee-body exclusions. There is no equivalent baseline path.

## Full Fuse runs and capacity

All three images boot independently, reach EOF, preserve the exact video/AY
payloads and pass mocked correct/wrong-disk handoffs. Occupied sectors remain
**2462/2463/2462**, leaving **82/81/82**. The compressed video remains
**1,818,909 bytes / 7106 sectors**. Bootstrap placement shifts the first video
sector by one on each disk without changing total occupied sectors.

| Disk | Late frames before -> after | Bad intervals before -> after | Maximum lateness | Effective fps |
|---|---:|---:|---:|---:|
| 1 | 90 -> 91 | 43 -> 53 | 63 fields | 8.328202 |
| 2 | 465 -> 532 | 249 -> 307 | 306 fields | 8.017817 |
| 3 | 766 -> 834 | 491 -> 583 | 345 fields | 8.333333 |

All **25326 AY records** meet the 50-Hz gate, with zero underruns, record gaps,
duplicate record fields, missed IRQ fields or sector retries. Actual screen
OUT timing is measured. Maximum deviations are **4,467,215 / 21,697,855 /
24,463,259 T**. Recovered late runs number **2/8/2**; disks 1 and 2 still have
unrecovered tails at EOF. All missed frame indices and late-run boundaries
are saved in [the summary](inplace_streaming_summary.json).

The summed first-to-last publication span increases **1,812,975,750 ->
1,816,662,970 T (+3,687,220)**. Initial disk/IRQ phases are not matched between
the runs, so this is an observed whole-system comparison, not a claim that
all elapsed differences come from decoder instructions alone.

Streaming reduces worst transfer bursts substantially: disk 1 drops from
1,696,808 to 422,462 elapsed T, disk 3 from 1,884,022 to 741,426. However,
aggregate transfer time on disks 2/3 rises to **112,168,058 / 146,784,032 T**,
and lateness grows. Smoothing a single block-read stall does not solve sustained
delivery. A future streamed variant needs a cheaper fast path when sufficient
input is already available; it should first beat these CPU counts before
another full integration. Also continue reducing reconstruction/output work
on the retained complete-input baseline.

## Verification and reproduction

- Five native tests cover all 256 EOF alignments, split headers, all slot
  banks, shared carry, short-read retry, long literals/matches and actual AY
  IRQ code after each instruction. Both register sets, flags, paging and
  protected banks are checked. The first test run had an overly high test-only
  wait-count expectation (48 observed versus >50); it was replaced with the
  relevant per-block early-output/wait assertions. All five then passed.
- All 188 full native blocks are byte-exact, including read/write cursor
  proof and instruction-table CPU sums.
- All three cold boots use poisoned RAM; the complete first native screen,
  second compact frame, resident AY contents and both handoffs are checked.
- All 4221 Fuse publications, 25326 AY records and 7106 runtime sectors are
  covered. Fuse samples 80 pixels per frame. Full-screen CPU verification
  is reused from unchanged frame code/data; this is **not** an all-pixel Fuse
  comparison or physical-drive verification. A full integrated CPU replay
  including every queue/audio hook is not claimed.

The [archive manifest](inplace_streaming_evidence/manifest.json) preserves
49 compressed evidence/source files. The audit checks their hashes, source
pins, build/trace identities, paired CPU arithmetic, instruction timings,
capacity, disk independence and full timing gates.

From this worktree, with its Python dependencies configured:

```powershell
python -m unittest -v test_inplace_streaming
python toolkit/build_inplace_streaming.py --baseline-build toolkit/inplace_keepalive_build.json --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/inplace-streaming-player --report toolkit/inplace_streaming_build.json --read-cache .tmp/inplace-keepalive-player/zx0 --read-cache .tmp/inplace-slot-reload-player/zx0 --read-cache .tmp/inplace-zx0-cache
python toolkit/benchmark_inplace_streaming.py --output toolkit/inplace_streaming_cpu.json
python toolkit/measure_inplace_streaming_queue.py --baseline .tmp/inplace-keepalive-player --streaming .tmp/inplace-streaming-player --output toolkit/inplace_streaming_queue_cpu.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/inplace-streaming-player --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/inplace-streaming-fuse --trace-pipeline --trace-fields
python toolkit/summarize_inplace_streaming.py --archive-directory .tmp/inplace-streaming-player --trace-directory .tmp/inplace-streaming-fuse --write
python toolkit/summarize_inplace_streaming.py
```
