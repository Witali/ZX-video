# Separate resident AY data from the video delivery path

Date: 2026-09-27. Baseline: the complete three-volume two-byte-cache player
at `8bc6a09`. **This report describes the lossless storage prototype.** The
subsequent [Z80 decoder measurement](RESIDENT_AUDIO_Z80.md) verifies all
records and audio-bank fit; integrated playable TRDs are still pending.
The target remains the entire authorized 4221-frame
edit, unchanged resolution, 25/3 fps, AY 50 Hz and independently bootable
disks. This experiment changes packet framing, not sound or picture data.

## Why investigate this

The current FAP3 parser enqueues six AY records only after copying a video
packet. Long input/ZX0 work can therefore delay audio. The new
[trace profiler](profile_audio_lookahead.py) examines all 25,326 records,
378 decoded blocks and 25,955 queue calls from the previous complete Fuse
run. It reconstructs monotonic decoded-byte prefixes from actual queue
states, including active output wrapping at 0000h.

| Volume | Existing AY underruns | Next record definitely decoded | Underrun inside the producing queue call |
|---|---:|---:|---:|
| 1 | 75 | 13 | 62 |
| 2 | 324 | 88 | 236 |
| 3 | 446 | 77 | 369 |

For **178** underruns, the next record is already in a completed decoded
prefix. The remaining **667** occur inside the call that produces it:
these boundary traces cannot tell precisely when that record becomes
readable. None is proved to precede the start of its producing call.
Do not label those 667 records definitely unavailable at the IRQ.

A counterfactual, zero-cost foreground scanner was also tested with usable
FIFO capacities 12, 18, 31, 63, 127 and 255 records. With the **original
producer timestamps held fixed**, every case still has 75/324/446 missed
ticks. Refilling is allowed only at observed foreground boundaries. This
does not prove that a rescheduled producer or larger queue cannot help:
the frozen trace includes the original blocking and backpressure. It does
show why queue capacity alone, without new scheduling evidence, is not a
demonstrated fix. All counterfactual assumptions and record-level readiness
bounds are saved in [the profile](audio_lookahead_profile.json).

## AYH1: exact records without an LZ history buffer

[The new host codec](ay_huffman_stream.py) stores each disk's initial eleven
AY registers explicitly. Each 50-Hz tick contains a register-change mask
and the original values in register order. Two static canonical Huffman
contexts code the low/high mask bytes; eleven contexts code register values.
Singleton contexts consume zero bits. Empty ticks are preserved, as are
noise-channel writes and every register value. There is no quantization,
resampling, note snapping, event merging or dropped tick.
Tables are trained from actual records, with no movie-specific notes or
register values. Other inputs must be checked against the bank limit; an
oversized soundtrack needs different partitioning or a streaming fallback,
never truncation or silent quality reduction.

The serialized header is `AYH1`, u32 tick count, u32 coded-bit count,
eleven initial register bytes, then thirteen sparse tables. Each table has
a u16 symbol count followed by `(symbol:u8, code_length:u8)` pairs. Codes
are MSB-first; unused final padding bits are zero. A singleton's length is
zero. All multi-symbol lengths are 1..24. Exact bounds and malformed input
are checked by the host decoder. This is an experimental format identifier.

| Volume | AY ticks | Original record bytes | AYH1 including tables/state | Unused space in a 16-KiB bank |
|---|---:|---:|---:|---:|
| 1 | 9744 | 42450 | 13279 | 3105 |
| 2 | 7782 | 37928 | 12262 | 4122 |
| 3 | 7800 | 37986 | 12080 | 4304 |
| **Total** | **25326** | **118364** | **37621** | — |

The payload uses **101725 / 93571 / 92085 bits**; headers and sparse tables
occupy **563 / 565 / 569 bytes**. All original record bytes round-trip
exactly. Each volume's explicit initial state equals the preceding state,
so the sound format does not require RAM from another disk. This is a
format-level check, not a new cold-boot test.

## Complete combined storage result

The storage probe removes only the six AY records from each FAP3 packet
and updates its u16 length. Every video field, code, fragment, motion vector
and native mask is retained. The video-only stream is rechunked into
independent blocks of at most 8192 bytes and compressed with **optimal
ZX0 v2**, including four-byte block headers. All **364 new blocks** are
independently decoded. Recombining their packets with AYH1 yields every
byte of the previous packet stream.

| Volume | Previous combined stream | New ZX0 video | Resident AYH1 | New total | Difference |
|---|---:|---:|---:|---:|---:|
| 1 | 641005 | 610042 | 13279 | 623321 | -17684 |
| 2 | 640198 | 611170 | 12262 | 623432 | -16766 |
| 3 | 638742 | 610984 | 12080 | 623064 | -15678 |
| **Total** | **1919945** | **1832196** | **37621** | **1869817** | **-50128** |

Rounding video and audio separately to sectors, and retaining the previous
fixed disk overhead of 38/42/46 sectors, gives **estimated** used counts
**2473 / 2478 / 2481**, or **71 / 66 / 63 free sectors**. These are not
actual new TRD capacities. The new decoder, runtime table representation,
startup sections, independent initialization and final alignment still
need a real build. This replaces the previous near-zero storage margin
with a promising measured data-size saving, not a release claim.

## Proposed 128-KiB allocation and implementation gates

Use bank 4 for the complete compressed soundtrack and its decoder tables;
retain banks 0/1/3 as three 16-KiB video slots. This preserves the existing
region mapping for video regions 0..2. It reduces ready video history from
32 to **24 KiB**, which must be measured under sustained disk delivery.

| Bank(s) | Proposed contents | Bytes reserved |
|---|---|---:|
| 0, 1, 3 | Three bank-local ZX0 input/history slots | 49152 |
| 4 | Resident AY stream, lookup tables, decoder/workspace | 16384 |
| 2 | Existing fixed code, compact frame/cache, AY FIFO, IRQ/stack | 16384 |
| 5 | Existing screen, packet window and TR-DOS workspace | 16384 |
| 6 | Existing video Huffman tables and inline patches | 16384 |
| 7 | Existing screen, queue and compiled-mask code | 16384 |
| **Total** | | **131072** |

The 3105-byte minimum bank slack above does **not yet prove** that executable
code and expanded lookup tables fit. A compact binary tree or short-prefix
table should be assembled and measured first. AYH1 itself needs no LZ
history. Avoid replacing this saving with an uncounted decompression buffer.

The original next steps are retained below. Steps 1 and 2 now have
[complete Z80 CPU/RAM evidence](RESIDENT_AUDIO_Z80.md); integration and
release checks in steps 3 through 5 remain pending.

1. Implement the resident decoder and foreground FIFO filling on Z80.
   Keep the actual 50-Hz ISR consuming a prepared record without paging,
   decoding or disk access. Count all setup, bit reads, output writes,
   paging and queue checks; test IRQ preservation after every instruction.
2. Execute every actual AY record and all format edge cases. Verify exact
   writes, initial state, empty ticks, coded-input bounds and memory use.
   Compare complete producer cost with the old enqueue path. Current
   player hot-path delta is **0 T** because it has not changed in this probe;
   no new runtime timing claim is made.
3. Integrate a three-slot video queue and the audio-free packet parser.
   Refill AY before long foreground operations; return immediately when
   its FIFO is full so video can recover its original deadlines.
4. Build actual independently bootable TRDs and verify dirty-RAM startup,
   all bytes installed, disk swaps, wrong-disk rejection and LFS packaging.
5. Run all three disks through EOF. Measure disk/ROM latency separately
   from CPU; compare every nominal deadline, one-field fallback recovery,
   AY continuity, exact pixels and full capacity. Keep the old player as
   the comparison until these gates pass.

## Reproduction and verification

Six tests cover arbitrary register masks/values, empty and constant ticks,
truncation and invalid records, output-pointer wrap, service gaps and FIFO
capacity limits. These are host/model tests, not Z80 or disk measurements.
The reports preserve all coded AY bytes and compressed video blocks.

```powershell
python -m unittest test_audio_lookahead_profile test_ay_huffman_stream -v
python toolkit/profile_audio_lookahead.py
python toolkit/probe_resident_audio.py
python toolkit/probe_resident_audio_storage.py --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --cache .tmp/resident-audio-zx0/optimal
python toolkit/audit_resident_audio.py
```

The final [auditor](audit_resident_audio.py) needs only saved repository
evidence; it checks source hashes and independently restores all video
blocks, AY records and original packets. See the [compact summary](resident_audio_summary.json),
[audio report](resident_audio_probe.json), and [complete storage report](resident_audio_storage.json).
The encoded-data saving is verified; a new player, actual TRD capacity,
video timing and continuous AY remain unverified. Root release images and
the current three-disk experimental player are unchanged.
