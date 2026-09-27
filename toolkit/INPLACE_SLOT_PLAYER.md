# Integrate 15.5-KiB ZX0 slots into the three-disk player

Date: 2026-09-27. Baseline: foreground resident AY at `da369e6`, retained
through `1ab9c2c`. Scope: all 4221 frames of the authorized edit, all 25326
AY records, independently bootable volumes ending at 1624/2921/4221.
Resolution, video packets, AY data and the nominal six-field schedule are
unchanged. **Both attempts complete, but neither passes release timing.**

## Implementation and memory ownership

[The producer](inplace_slot_input_z80.py) implements the previously
[proved shared input/output layout](INPLACE_ZX0_RESERVOIR.md). Each of banks
0/1/3 supplies up to 15872 output/history bytes, starting at C000. Total
capacity becomes **47616 bytes**, up from **24576**. These are decoded video
packets, not 47 KiB of already rendered screens. Bank 4 still holds the
resident soundtrack; screen banks, tables and the IRQ workspace stay assigned.

The producer reads a header through the fixed BC00 carry buffer, including
headers split across sectors. It then places the compressed body's sectors
against FFFF. Every input sector is read once; the final shared sector is
saved before decoding can overwrite it. The slot remains owned until its
output is consumed and the decoder has finished. No full compressed-block
copy or additional complete frame copy is introduced.

The disk adapter already supports pages through FF00. It advances its
write-region index at FFFF/0000; the new producer restores the owned slot
before every step. The earlier claim that the adapter itself wraps at E000
was incorrect: that boundary belonged to the old producer's input limit.

[Integration](inplace_slot_player.py) replaces the decoder's E000 output
operand with C000 and six queue constants with the matching C000/4000 base
and relative-offset bias. Four bridge calls select the new producer; their
cold-bootstrap overlay copies are patched too. All eleven substitutions
retain their instruction lengths and T-states. The coroutine's stack,
256-byte background quota and exact-demand behavior remain intact.

The final producer uses **468 bytes versus 368 (+100)**, including state:
281 bytes at 7D50, 113 at 7823 and 74 at 7B00. The latter two regions are
retired bootstrap/initializer space. The private decoder stack remains
7B70..7BDF. Before the idle check was added, this producer occupied 429 bytes.
The builder rejects a block whose host-proved sector placement is unsafe;
it does not assume this movie's overlap margin for another input.

## Actual disk capacity

Both attempts contain the same 188 ZX0 blocks and video/audio data. Actual
bootstrap compression and sector placement are included below.

| Disk | Frames | Video bytes | Video sectors | Occupied sectors | Free sectors |
|---|---:|---:|---:|---:|---:|
| 1 | 1624 | 606434 | 2369 | 2461 | 83 |
| 2 | 1297 | 606524 | 2370 | 2463 | 81 |
| 3 | 1300 | 605951 | 2367 | 2462 | 82 |

Video totals **1818909 bytes**, down **13287**; runtime reads fall
**7158 -> 7106 (-52)**. Occupied sectors fall **7434 -> 7386 (-48)** after
bootstrap and placement overhead. Actual video starts are 106/108/109;
the old starts were 106/107/108. The prior conditional capacity estimate
was one occupied sector too small for disks 2 and 3.

## First complete attempt: idle-drive failures

The larger reserve creates longer pauses between disk reads. The first
implementation had no new idle-drive handling. Fuse completed every volume
with exact video samples and AY records, but **15 direct reads failed** and
used the existing full TR-DOS fallback. Saved traces show long idle intervals
before these failures; some fallback calls take about **5.32 million T**
(1.50 seconds), emptying the sound queue.

| Disk | Late frames | AY underruns | Direct-read retries | Invalid 5..7-field intervals |
|---|---:|---:|---:|---:|
| 1 | 436 | 170 | 10 | 229 |
| 2 | 616 | 68 | 4 | 337 |
| 3 | 762 | 14 | 1 | 491 |

This attempt is rejected. Its source, build, all metadata, full debugger
scripts/reports/traces and CPU fixture remain in
[initial evidence](inplace_slot_evidence/initial/manifest.json). The initial
CPU fixture uses the baseline sector starts for both block sizes; it is a
controlled producer comparison, not the exact new on-disk placement.

## Second complete attempt: restore the drive before a read

Before a sector read, compare the 16-bit field counter with the previous
read-start counter. At **64 or more fields**, invalidate the cached track
with FE, forcing the existing cached SEEK/HLD procedure to run before READ.
FF remains reserved for an uninitialized drive and the full first dispatcher
call. The modulo-65536 difference handles ordinary counter wrap. This is
pre-read recovery, not periodic drive maintenance during a full-buffer pause.

All **15 failed reads disappear**, but a stopped drive can still delay a
successful read for **2.26 million T** (about 0.64 seconds). There are **24
AY underruns**, twelve each on disks 1 and 3; disk 2 has none. The IRQ itself
has no missing/duplicate fields. All AY records eventually play exactly,
but 24 record-field gaps mean the 50-Hz delivery requirement fails.

| Disk | Late frames: old -> new | Maximum lateness, fields | Bad intervals: old -> new | Effective fps |
|---|---:|---:|---:|---:|
| 1 | 213 -> 137 | 68 | 98 -> 87 | 8.333333 |
| 2 | 654 -> 553 | 302 | 365 -> 293 | 8.021788 |
| 3 | 878 -> 806 | 291 | 584 -> 534 | 8.333333 |

Total late frames fall **1745 -> 1496 (-249)** and invalid intervals
**1047 -> 914 (-133)**. Summed publication spans fall **1816733868 ->
1815953880 T (-779988)**, but disk 2's span grows by 779988 T. Initial disk
and IRQ phases were not matched, so this is an end-to-end outcome, not an
isolated instruction-speed claim. An average of 8.333333 fps on disks 1/3
does not mean their frame spacing is correct.

Maximum actual publication deviations are **4821748 / 21414216 / 20634225
T**. Recovered late runs number **8 / 10 / 6**. Disk 2 ends with an
unrecovered run at local frames 1016..1296. Neither nominal deadlines nor
the one-field fallback passes. The [summary](inplace_slot_summary.json)
retains every missed frame index, run and recovery, and the raw traces remain
in [reload evidence](inplace_slot_evidence/reload/manifest.json).

## Deterministic CPU costs

[The native benchmark](benchmark_inplace_slot.py) executes every baseline
and candidate block, including actual header parsing, slot paging, sector
cursor updates, shared-sector copying and resumable decoding. Each output
byte must equal the source; each input-cursor-at-write must match the
independent overlap proof. Other slots and screens must remain intact.
Every producer instruction is checked against its timing-table entry.

| Work over all three volumes | 8192-byte baseline, T | 15872-byte candidate, T | Delta, T |
|---|---:|---:|---:|
| Sector/header/carry producer | 12248310 | 11831396 | -416914 |
| ZX0 coroutine, 256-byte quotas | 187756600 | 189573555 | +1816955 |
| Total of these stages | **200004910** | **201404951** | **+1400041 (0.700%)** |

Carry copies shrink **185088 -> 96256 bytes (-88832)**. The final benchmark
uses the actual new sector starts and installed producer bytes. Its field
counter stays at zero: ordinary idle checks are included; rare recovery
branches are measured separately by boundary tests. The first no-idle-check
fixture total was 200495567 T at the controlled baseline sector starts.

The new check has no previous instructions at its insertion point (0 T).
Including its caller's CALL, the added cost is **128 T** before 64 fields,
**177 T** on expiry within the low-byte range, **161 T** when the difference
has a nonzero high byte, and **153 T** for the tested uninitialized-drive
expiry case. These figures exclude the subsequent cached SEEK and ROM.
The tests also measure the respective helper bodies: 111/160/144/136 T.

All figures exclude ROM execution, ULA waits, IRQ/AY and physical disk time.
Queue-selected quotas differ from the fixed benchmark quotas; this is not a
complete integrated-player CPU total. Full Fuse traces measure the combined
emulated delivery cost separately. The naked turbo-decoder counts from the
earlier overlap proof remain a distinct baseline.

## Verification and decision

Six boundary/stress tests pass: split headers and first-track arrangements,
all slot banks at full output size, shared-sector reuse, short-read fallback,
invalid sizes, idle threshold/wrap and real AY IRQ between instructions.
Both complete builds pass dirty-RAM boot, complete first native and second
compact frames, immutable soundtrack, and both disk swaps including wrong
disk/series rejection. The first build wrapper initially failed while
collecting source hashes because of a stale copied filename; after correction
the whole build/check sequence was repeated successfully.

Full producer/decoder execution checks all 2965011 packet bytes per variant.
Rendering code and decoded packets are unchanged; the prior full-frame CPU
comparison is reused. Both Fuse runs cover EOF on all three volumes, checking
80 screen bytes per frame, all AY writes, runtime sector order, progress and
actual publication/IRQ timing. This is not a fresh full-screen comparison
inside Fuse and is not a physical-drive test.

Retain this as an **optional experimental larger reservoir**, not a release
replacement. The next necessary experiment is periodic SEEK/HLD while the
queue is full, before the drive stops. It must preserve live registers,
slot ownership and AY, avoid reading/discarding any sector, count every
added path and run all volumes again. Reuse the established TR-DOS 5.03
keepalive contract; pre-read recovery alone is insufficient. After fixing
AY delivery, address burst frame/transfer work; no late frame in the current
profile was already rendered at least 1000 T before its deadline.

## Reproduction

Run from the task worktree using the project's Python dependencies:

```powershell
python -m unittest test_inplace_slot -v
python toolkit/build_inplace_slot_player.py --baseline-build .tmp/resident-audio-build-foreground.json --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --read-cache .tmp/inplace-zx0-cache --read-cache .tmp/resident-audio-player-foreground/zx0 --output .tmp/inplace-slot-reload-player --report toolkit/inplace_slot_player_build.json
python toolkit/benchmark_inplace_slot.py --build toolkit/inplace_slot_player_build.json --output toolkit/inplace_slot_cpu.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/inplace-slot-reload-player --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/inplace-slot-reload-fuse --trace-pipeline --trace-fields
python toolkit/snapshot_resident_audio_player.py --build toolkit/inplace_slot_player_build.json --directory .tmp/inplace-slot-reload-player --fuse .tmp/inplace-slot-reload-fuse --output toolkit/inplace_slot_evidence/reload
python toolkit/summarize_inplace_slot.py
```

The snapshot refuses to replace different evidence. Use a new directory
for a new attempt. Root release images remain the verified fourteen-disk set.
