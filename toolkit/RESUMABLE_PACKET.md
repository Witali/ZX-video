# Resumable optional packet acquisition

Date: 2026-09-27. Baseline: `a84451d`, resident AY, three 15872-byte
in-place ZX0 slots and periodic drive maintenance. All **4221 frames** and
**25326 AY records** are retained. **Do not enable this experiment by default:**
it improves responsiveness at specific read-ahead boundaries, but complete
playback misses more deadlines. Neither video timing gate passes.

## Implementation and memory

[resumable_packet_player.py](resumable_packet_player.py) adds a **162-byte**
helper at **F900..F9A1 in bank 7**, directly after generated mask bodies.
That includes two state bytes: parser stage and optional-read mode. It uses
two extra stack bytes while calling the queue gate, with no private stack.
Both screens, resident audio, dictionaries, TR-DOS stack and all three
15872-byte slots retain their allocations. No extra packet/frame buffer is
allocated and no already-read packet prefix is copied again.

The helper distinguishes a partially acquired two-byte length from a
partially acquired body. The existing queue already retains pending count,
destination, slot position and ownership. On an optional call, a cleared
native-ready flag allows the reader to return at its next queue boundary.
The scheduler draws the prepared compact frame; its next required read
resumes the same packet. A completed optional call returns 1; a suspended
call returns 0. The original scheduler's pending flag receives that result.

Required reads keep demand decoding. Optional reads consume any available
prefix, or perform one ordinary input-sector / 256-output-byte ZX0 quantum.
They never free an active history slot before decoder EOF. The draw routine
uses the previously saved native map, so replacing or partially replacing
the packet buffer cannot replace the prepared frame's map.

The bootstrap's existing bank-7 section extends through F9A1; mask tables
and bodies are still generated during initialization. Dirty-RAM cold boots
and both disk swaps pass. The initialization space added to the section is
highly compressible; **occupied sectors stay 2462/2463/2462**, with
**82/81/82 free**. Video starts at sectors **107/109/110**, compared with
**107/108/109**. Different placement can affect disk timing despite unchanged
occupied-sector totals.

## Content and CPU checks

The compressed video stream is **byte-for-byte unchanged**: **1,818,909 B**,
188 blocks and 7106 video-sector reads. Every block decodes to the retained
raw-video hashes; AY payload hashes also match. Resolution, pixels, masks,
frame rate and original six-field deadlines are unchanged.

[The CPU test](test_resumable_packet.py) enters the actual cold-loaded parser
before queue prefill. It executes the first **256 packets per volume** in
each baseline, required and forced-resume case, plus eight packets with
real AY-handler instruction stress per volume. Every packet byte matches
and is written **exactly once**. Across the 768 forced-resume cases, **584**
pause; all CPU registers are deliberately overwritten before continuation.
Additional synthetic cases split the length field across two completed
slots, suspend after its first byte, resume with IRQ stress, and verify
release of the last slot at EOF. **4066 IRQ injections** preserve the tested
register, stack, paging and audio-write contracts. This is a parser/queue
test, not a complete integrated CPU movie or physical-disk measurement.

T-states use the [Zilog instruction table](https://www.zilog.com/docs/z80/um0080.pdf).
The test checks each newly executed helper/patch instruction and retains
the full CPU histogram. ROM calls are mocked; IRQ costs are excluded from
the deterministic prefix sums. ULA and physical disk latency are absent.

| Path | Before | After | Delta |
|---|---:|---:|---:|
| Queue count read, required mode, including new CALL/RET | 13 T | 67 T | +54 T |
| Queue count read, optional mode, continue | 13 T | 94 T | +81 T |
| Existing jump to demand decode, required mode | 10 T | 37 T | +27 T |
| Fresh required header dispatch through legacy entry, excluding take body | 37 T | 141 T | +104 T |
| Body dispatch, excluding take body | 47 T | 97 T | +50 T |
| Metadata completion and return | 26 T | 73 T | +47 T |

The required test enters the helper directly, skipping the legacy entry's
10-T trampoline. Its exact parser delta is therefore
`191 * packets + 54 * queue_gates + 27 * demand_gates`.
Producer/disk CPU changes from sector placement are counted separately:
**0 / -92 / -113 T** in these prefixes. Each sum matches the executed
instruction histogram. Real calls through the old entry add 10 T per
fresh required packet. Optional suspensions execute a different sequence;
their measured totals are not extrapolated to the whole movie.

| Volume, 256 packets | Baseline CPU | Required CPU | Forced-resume CPU |
|---|---:|---:|---:|
| 1 | 15,749,661 | 15,890,573 | 16,313,462 |
| 2 | 19,024,975 | 19,173,868 | 19,604,897 |
| 3 | 27,631,846 | 27,793,408 | 28,511,953 |

## Complete Fuse result

Every disk boots independently and reaches EOF. All AY records remain
exact at 50 Hz, with zero underruns, field gaps, duplicate/missing IRQs or
read retries. Fuse samples **80 native-screen bytes per frame**; these are
not a comparison of every screen pixel. Initial complete native/compact
frames are separately checked by the builder. Real hardware is untested;
initial disk and IRQ phases are not matched between variants.

| Volume | Late frames, old → new | Invalid intervals, old → new | Maximum lateness, old → new |
|---|---:|---:|---:|
| 1 | 90 → 89 | 43 → 43 | 64 → 64 fields |
| 2 | 465 → 481 | 249 → 261 | 260 → 266 fields |
| 3 | 766 → 767 | 491 → 493 | 265 → 271 fields |
| **Total** | **1321 → 1337** | **783 → 797** | |

Maximum actual OUT deviations are **4,538,126 / 18,861,528 / 19,216,070 T**.
Recovered late runs: **2/11/3**; volume 2 retains an unrecovered tail at
local frames **1237..1296**. Publication spans are **690,502,104 /
570,242,136 / 552,656,952 T**, totaling **1,813,401,192 T**:
**425,442 T worse** than the retained baseline. Volumes 1/3 still average
25/3 fps after recovery, which does not establish smooth output.

The intended scheduling mechanism is visible in the full traces: **8/19/6
= 33** native draws start before the interrupted packet finishes. Maximum
draw-start delay after the preceding publication is **22,666 / 109,667 /
26,991 elapsed T** in these cases. There are still **6/6/15** overlapping
reads that finish before the next draw. The longest such delay is 60,343 T.
These are elapsed response intervals, not saved CPU. A transfer interval
can now contain another frame's native drawing; the old profiler's sum of
disjoint stages is not applicable. The auditor preserves all event rows.

## Decision and next work

**Retain the implementation and evidence as an experiment only.** Capacity
and exact streams are preserved, but both timing metrics and total span
worsen. Global extra checks and smaller optional decode chunks add work;
earlier drawing can also move the same unfinished packet work to the next
deadline. The measurements do not isolate those causes quantitatively.

A further variant should first eliminate the **+54 T gate and +27 T
demand check from mandatory reads**, retaining the original mandatory path.
An optional-only consumer entry or carefully restored temporary routing
could do that; count setup/restoration too, preserve IRQ safety, and measure
complete delivery again. Do not repeat the global gate or treat the 33
earlier draws as a movie-wide speedup. Acquisition bursts and sustained
work in difficult scenes remain unresolved. Root releases/defaults stay
unchanged, and the three-disk smooth-playback goal remains open.

## Reproduction and evidence

Run in the existing worktree with the recorded dependency path:

```powershell
$env:PYTHONPATH='toolkit;C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/python_packages'
$env:OPENBLAS_NUM_THREADS='1'
python toolkit/build_resumable_packet.py --baseline-build toolkit/inplace_keepalive_build.json --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/resumable-packet-player --report toolkit/resumable_packet_build.json --read-cache .tmp/inplace-keepalive-player/zx0
python toolkit/test_resumable_packet.py --directory .tmp/resumable-packet-player --baseline .tmp/inplace-keepalive-player --output toolkit/resumable_packet_cpu.json --frames 256
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/resumable-packet-player --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/resumable-packet-fuse --trace-pipeline --trace-fields
python toolkit/summarize_resumable_packet.py --archive-directory .tmp/resumable-packet-player --trace-directory .tmp/resumable-packet-fuse --write
python toolkit/summarize_resumable_packet.py
```

The saved run used three separate, sequential Fuse commands with the same
arguments, starting each disk after its image was built. CPU testing first
hit two instrumentation limitations: a stale historical listing address
overlaid by ZX0, then missing SCF in the Python CPU. Both failure reports
are retained; instruction checking now targets the new helper/patches and
the local CPU subclass implements SCF. Neither required a player change.
The 256-packet test later reached disk 3 before its build finished and
exited with FileNotFoundError. The saved incomplete report retains all
completed cases. [The resume script](resume_resumable_packet_tests.py)
executed only missing cases, and the auditor verifies that completed
results were not rewritten. The initial cycle formula also needed the
measured producer sector-alignment delta; it now matches all three cases.

[The summary](resumable_packet_summary.json) passes its archive audit.
The manifest covers **50 gzip files**, including source, build, CPU and complete Fuse traces;
three archived experimental `.trd.gz` images use **Git LFS**. A fresh run
of all tests does not require the historical resume script; the audit checks
the saved-run provenance fields when a resumed report includes them.
