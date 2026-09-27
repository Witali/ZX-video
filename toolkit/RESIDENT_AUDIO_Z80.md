# Resident AY decoder: complete Z80 CPU and RAM measurement

Date: 2026-09-27. Baseline: the AYH1 storage prototype at `1cdb5f1`, with
the existing AY FIFO/consumer from the three-volume player at `8bc6a09`.
**All 25,326 records execute exactly; the audio bank fits.** This is not
an integrated player or a new TRD release. The 4221-frame target, exact
six-field publication deadlines, AY 50 Hz and independent disks remain.

## Implementation

[The generator](resident_audio_z80.py) validates AYH1 on the host and builds
one bank containing executable code, state, explicit initial AY registers,
thirteen root pointers, compact binary Huffman trees and the coded payload.
It replaces the sparse serialized header with runtime tables; it does not
keep both copies. Internal nodes have two 16-bit child pointers. A child
with high byte zero is a leaf whose low byte is the original value.

The input cursor is IX, B holds a sentinel and unread bits, C holds the
register mask, DE addresses the unpublished FIFO slot, and HL traverses
tables. AF' counts written registers. Decoding writes the final count and
register/value pairs directly into the existing A000h FIFO; no temporary
record or second copy is needed. The write index changes only after the
complete record is present. A full FIFO returns immediately. Each fill
call produces at most six records by default (configurable 1..31).

The existing 50-Hz AY consumer is unchanged. It performs no decompression
or paging. The resident initializer writes all eleven initial registers
to the AY ports, clears queue/counters and leaves audio disabled until the
driver starts it. Per-volume initial states match the original soundtrack.

A separate **35-byte fixed-RAM bridge** saves AF, AF', BC, DE, HL and IX,
enters bank 4, calls the resident entry and restores the previous RAM bank.
The other alternate registers remain untouched. Both paging calls use
the existing restartable helper, which merges the latest IRQ-owned screen
bit. The test location at 9300h is **not an allocation in the real player**.
Integration must allocate/verify the bridge, potentially using retired
enqueue code, and must similarly connect initialization.

Other videos use their own trained tables and data. Oversized banks,
tick counts above 65535, malformed data and incomplete canonical trees
are rejected explicitly; the current host encoder creates complete trees.
Partitioning/fallback belongs to the eventual converter integration.

## Bank memory

All volumes include 407 bytes of code, 8 mutable state bytes, 11 initial
register bytes, 86 alignment bytes and a 26-byte root table. The fixed
bridge, existing FIFO, ISR and stack are outside this bank.

| Volume | Coded payload | Tree nodes | Complete bank image | Spare in 16 KiB |
|---|---:|---:|---:|---:|
| 1 | 12716 | 976 | 14230 | 2154 |
| 2 | 11697 | 980 | 13215 | 3169 |
| 3 | 11511 | 988 | 13037 | 3347 |

This proves the resident audio allocation, not the entire proposed memory
map. The proposed video slots still need to shrink from four to three.
Their 24-KiB ready history and sustained disk delivery remain unmeasured.
Bootstrap staging is at most 6912 bytes, so the audio bank must be loaded
in multiple bounded sections instead of one oversized startup section.

## Instruction counts and comparison

All counts use the [Zilog instruction timings](https://www.zilog.com/docs/z80/um0080.pdf).
The CPU fixture checks every executed instruction against the generated
listing and also checks an independent aggregate formula. Counts exclude
ULA contention, IRQ service, TR-DOS ROM and physical disk latency.

For a symbol of length `b`, containing `o` one bits and requiring `r`
input-byte refills, the tree decoder including RET and excluding CALL is:

```text
symbol = 73 + 71*b + 17*o + 32*r T
```

The constant-context path is 73 T. A consumed bit adds 71 T for the left
branch or 88 T for the right branch; byte refill adds 32 T. Both the tree
traversal and bit reader preserve the register mask and FIFO cursor.

For a full batch of `n` ticks with `w` register writes, the bank-local
routine includes all output stores, FIFO checks, state saves and RET:

```text
fill = 109 + 789*n + 137*w + 71*b + 17*o + 32*r T
```

Here `b/o/r` count the actual bits, one bits and refills within the call.
Across a volume, refills equal coded payload bytes, each read exactly once.
A zero-output EOF call takes 150 T; a full-FIFO call takes 198 T. An early
return after emitting some records also includes its final EOF/full check.

The all-register bridge adds **436 T per call**, including both 92-T
paging routines and the resident CALL. The caller's outer CALL is excluded
from both old and new comparisons. IRQ publication may restart paging,
adding re-executed foreground instructions; that is checked for correctness
in unit tests but is not included in the no-IRQ totals below.

The old six-record enqueue routine takes `1705 + 42*w` T with room in the
queue. Both paths below use one call per six original records and no wait
for queue space. Initializer cost, **1056 T per volume in the mapped bank**,
is reported separately, not folded into the producer delta.

| Volume | Old enqueue | Resident fill + bridge | Difference | Maximum six-tick call |
|---|---:|---:|---:|---:|
| 1 | 3455746 | 19268449 | +15812703 | 22057 |
| 2 | 2844451 | 16721841 | +13877390 | 21340 |
| 3 | 2850406 | 16610362 | +13759956 | 22413 |
| **Total** | **9150603** | **52600652** | **+43450049** | **22413** |

The bank-local total is 50,760,296 T; bridges/paging add 1,840,356 T.
Maximum measured stack use is 24 bytes including the outer return address
and excluding an interrupt. IRQ stress separately checks stack bounds and
register restoration. The unchanged consumer totals 13,223,661 T when
manually called once per record; it is not part of the producer table.

This decoder is more expensive than copying records already decompressed
by ZX0. **Do not call this a net playback speedup.** It provides independent
audio availability and previously measured storage savings. The video-only
format also changes ZX0 and packet-copy work; those costs, service frequency,
queue pressure and physical disk delivery require full integration.

## Verification and next gate

[Nine new tests](test_resident_audio_z80.py) cover all 2048 masks, all 256
values for each register, zero-bit constant contexts, empty input/ticks,
24-bit codes, input-byte boundaries including FFFFh pointer wrap, FIFO wrap
and capacity, independent initial register writes, format/RAM rejection,
all caller registers and real fast IM2 interruption after each instruction
of representative decoding and bridge paths. Screen publication is injected
at every instruction of both paging calls, for both screens and all eight
original RAM banks. No pending record becomes visible before it is complete.
The combined new/AY/host/model suite has **20 passing tests**.

[The full benchmark](benchmark_resident_audio_z80.py) executes all three
volumes (9744/7782/7800 records), compares every publication and every AY
port write/state, enforces read/write guards, checks complete bit consumption
and counts every instruction. [Saved results](resident_audio_z80.json) pin
inputs and implementation sources and include per-call costs and dynamic
instruction counts. The harness starts RAM dirty; this tests resident
initialization, **not TR-DOS cold boot**. Manual consumption is not a 50-Hz
cadence test. Stress IRQ underruns caused by injecting every instruction
are expected and are not playback results.

The [quick auditor](audit_resident_audio_z80.py) rebuilds all three bank
images and checks source hashes, generated listings and saved timing
arithmetic. It does not substitute for replaying the complete CPU benchmark.
Source hashes explicitly use LF-normalized bytes (`source_sha256_lf`), so
Git's CRLF working-tree conversion does not invalidate identical Python
code. Input/report hashes and generated image hashes remain byte-exact.

```powershell
python -m unittest test_resident_audio_z80 test_ay_interrupt test_ay_huffman_stream test_audio_lookahead_profile -v
python toolkit/benchmark_resident_audio_z80.py
python toolkit/audit_resident_audio_z80.py
python toolkit/audit_resident_audio.py
```

Decision: keep this as the measured resident-audio implementation for the
next integration. Replace the muxed video parser, use three video slots,
connect bounded audio service and startup loading, then build actual TRDs.
Measure every volume through EOF, including all nominal frame deadlines,
fallback recovery, AY continuity, pixels, disk sectors and cold/swapped
startup. Root release TRDs and the previous experimental player are unchanged.
