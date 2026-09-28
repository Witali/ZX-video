# Preparing difficult frames ahead of their deadlines

Date: 2026-09-28. Input: the complete Fast preview at `2881667`, all 4221
frames. This is a fresh analysis of its saved Fuse traces and exact root
TRDs, not a changed player or a new emulator run. Player delta: **0 T**;
stream delta: **0 bytes**. The three-disk capacity and exact AY pass, while
both video timing gates remain failed.

## What the existing reservoirs contain

| Storage | Capacity | Contents and current use |
|---|---:|---|
| Huffman input cache | 2 bytes in B/E | Current and next coded byte; avoids repeated indexed loads while decoding a symbol |
| ZX0 decoded slots | 3 × 15872 = 47616 bytes | Future video packets after the outer ZX0 layer; patch values inside them still use Huffman |
| Fixed packet window | 4704 bytes | One current/pending packet, maximum 4702-byte payload plus two readable guards |
| Compact frame | 3840 bytes | Reconstructed bitmap/attributes used as prediction history and input to native drawing |
| Native screens | 2 × 6912 bytes | Displayed screen and completed/in-progress back screen, including attributes |

The slots share space with their own compressed input and live LZ history;
47616 is maximum decoded capacity, not extra unallocated RAM. The small
Huffman cache is unrelated to the long-term ability to absorb a hard scene.

The existing pipeline already performs advance work. Cold priming fills
the slots, draws frame zero, prepares compact frame one and reads a pending
packet when available. After drawing a back screen, foreground work prepares
the following compact frame and may acquire the next packet. While a ready
screen waits for publication, the producer reads/decompresses ahead. The
50-Hz ISR publishes ready frames against the original six-field deadlines.

Sources: [clock and priming](pipelined_frame_z80.py),
[queue](slot_queue_z80.py), [current memory layout](FAST_ZX0_PLAYER.md),
[Huffman cache](cached_huffman_lookahead.py).

## Current Fast reserve, measured at every packet start

[The analysis](profile_fast_reservoir.py) reconstructs absolute producer and
consumer byte positions from every packet and ZX0 block. All observations
must agree with queue counts, slot ownership, producer phases and the
47616-byte bound. Screen/AY timing remains the original complete Fuse run.

| Disk | Median decoded bytes | Median complete packets available | Starts with at most 6 ready bytes | Total frames |
|---|---:|---:|---:|---:|
| 1 | 30148 | 50 | 99 | 1624 |
| 2 | 9840 | 11 | 478 | 1297 |
| 3 | 4 | 0 | 740 | 1300 |

Packet counts include the requested packet if it fits; they are not counts
of fully reconstructed frames. The maximum decoded reserve is 47616 on
every volume. Compact preparation finishes at least one full nominal frame
period before its own deadline for **1497 / 826 / 524 frames**, respectively.
Advance reconstruction is therefore already active, not merely proposed.

The worst 32-frame windows on disks 2/3 cover global frames **2872..2904**
and **3887..3919** (exclusive end). They request **63230 / 52483 bytes**,
with **0..6 ready bytes at every packet start**. Their assigned foreground
work totals **23704587 / 22738880 elapsed T**, against a nominal 32-frame
budget of **13614336 T**. These stage sums include IRQ/ULA and disk service;
they are not additive deterministic CPU estimates or exact lateness.

## Proposed next steps

1. **Fill the existing reservoir faster.** Test faster lossless ZX0
   tokenizations with the current free disk space, charging added sector
   delivery as well as decoder CPU. All bytes of video/AY stay unchanged.
   This directly addresses the missing data observed in the hard windows.
2. **Measure useful advance work in time, not only bytes.** A large simple
   packet and a small expensive packet can represent different amounts of
   CPU work. Use per-frame reconstruction/output costs and nominal deadlines
   when deciding how much reserve precedes a difficult run. Store any new
   cost hints explicitly and charge their bytes and runtime dispatch.
3. **Evaluate a deeper queue of prepared changes as a separate format.**
   A candidate would store resolved patch values and compact update commands
   so the deadline path only applies changes and draws. Context-dependent
   Huffman decoding uses predicted pixel values, so it cannot in general
   run arbitrarily far ahead without reconstructing the intervening frames.
   Preserve the n-1 compact predictor and n-2 native-screen dependencies.
4. **Account for the memory/copy tradeoff before implementation.** Expanded
   commands or additional compact frames consume RAM now used by compressed
   input, LZ history and decoded packets. Reconstructing into paged memory
   competes with bank-6 Huffman tables. A larger ready-frame queue that needs
   a 3840-byte copy for every frame can lose more CPU than it saves. Prefer
   direct construction in its eventual buffer, and count paging and IRQ-safe
   register preservation as part of the experiment.

The idea can absorb a short burst if preceding frames leave enough CPU and
I/O time to build the reserve. It does not create processing capacity during
a sustained difficult run. Do not reduce resolution, alter AY, move the
schedule origin, or deliberately delay frames to make a buffering result pass.
Any implemented variant still needs full independent boot, EOF, nominal and
fallback recovery checks on all disks.

### First refill experiment completed

[Lossless ZX0 token selection](FAST_TOKEN_PLAYER.md) now completes all three
disks. Faster refill raises disk-2 median reserve from 9840 to 12278 bytes
and reduces disk-3 near-empty packet starts from 740 to 561. Overall late
frames fall 1239→1149, but disk 1 regresses slightly and timing still fails.
The experiment spends 61133 extra compressed bytes, retaining identical
decoded pixels and AY. Keep it optional; deeper prepared-command buffering
has not yet been implemented or validated by this experiment.

## Evidence and reproduction

[All per-frame reserve/preparation records](fast_reservoir_profile.json).
No source movie is required; the committed root TRDs must be hydrated through
Git LFS. With the project Python dependencies:

```powershell
python toolkit/profile_fast_reservoir.py
```

`--write` regenerates the report. The inherited zero-cost-input projection
is explicitly hypothetical: it freezes measured stage durations and removes
all transfer/control work. Its zero-late result is not a feasibility proof
for a real memory layout or scheduler.
