# Separate optional packet consumer

Date: 2026-09-27. Retained baseline: `a84451d`; preceding global-gate
experiment: `25780a9`. All **4221 frames / 25326 AY records** are retained.
**Experimental only:** the new reader removes the preceding attempt's
mandatory-loop overhead, but still fails both complete video timing gates.

## Implementation and memory

[optional_packet_player.py](optional_packet_player.py) keeps the existing
mandatory queue consumer byte-for-byte. A second consumer in unused bank 7
shares its queue state, slot ownership and copy bridges. Parser dispatch
selects required or optional consumption once per length/body transfer.
There is no temporary runtime code patching or additional packet copy.

The helper occupies **324 bytes at F900..FA43**, including two parser state
bytes, versus the previous 162 bytes. It requires **zero extra stack bytes**
relative to the original calls; the preceding global-gate helper needed two.
Both screens, resident AY, dictionaries, code/ROM stacks and three
**15872-byte** decoded slots retain their allocations. The bank-7 startup
section extends through FA43; no data buffer is added or reduced.

Optional calls consume the available decoded prefix, or one existing
input-sector / 256-output-byte ZX0 step, then check the native-ready flag
at a queue boundary. A cleared flag returns control for native drawing.
The same partially read length or body resumes afterward. Slots remain
owned until decoder EOF. Required calls use the original demand decoder.
Scheduling origins and the AY interrupt are unchanged.

The host builder now actually reuses `--read-cache` entries inherited from
earlier builds. Every hit is keyed by uncompressed SHA-256 and checked by
exact decompression. This changes build time, not player compression policy.

## Exact content and instruction costs

Three cold-bootable images use **2462/2463/2462 sectors**, leaving
**82/81/82 free**, unchanged from both preceding variants. Video starts at
**107/109/110**, versus baseline **107/108/109**. Compressed video remains
**1,818,909 bytes / 188 blocks / 7106 reads**, byte-for-byte identical.
All decompressed video and resident AY hashes match the retained baseline.
Dirty-RAM boots, initial complete native/compact frames and both disk swaps
pass, including rejection of wrong disks and series.

Instruction costs use the [Zilog table](https://www.zilog.com/docs/z80/um0080.pdf).
They exclude IRQ/ULA time and physical disk latency. CPU fixture ROM calls
are mocked; complete Fuse call durations are reported separately.

| Path | Original | Global gate | Separate consumer |
|---|---:|---:|---:|
| Required queue count read | 13 T | 67 T | 13 T, delta 0 |
| Optional gate continuing through count read | 13 T | 94 T | 40 T, delta +27 |
| Required demand dispatch | 10 T | 37 T | 10 T, delta 0 |
| Fresh header through legacy entry, excluding consumer | 37 T | 141 T | 168 T, delta +131 |
| Body dispatch, excluding consumer | 47 T | 97 T | 124 T, delta +77 |
| Metadata completion and return | 26 T | 73 T | 73 T, delta +47 |

The transfer selector costs **27 T required / 37 T optional**, excluding
the caller's existing CALL. Fresh required packets execute two selectors.
The CPU test enters `required` directly, excluding the old entry's 10-T
trampoline. Its parser delta is exactly **245 T per packet**. Actual
producer/disk alignment deltas are **0/-92/-113 T** per measured prefix;
these are added separately. Every formula matches executed instruction
histograms. Required prefixes never execute the optional clone or gate.

| Volume, first 256 packets | Original required | Global-gate required | Separate required | Separate forced-resume |
|---|---:|---:|---:|---:|
| 1 | 15,749,661 | 15,890,573 | 15,812,381 | 16,216,182 |
| 2 | 19,024,975 | 19,173,868 | 19,087,603 | 19,499,843 |
| 3 | 27,631,846 | 27,793,408 | 27,694,453 | 28,383,398 |

Compared with the global-gate experiment, required prefixes save
**78,192/86,265/98,955 T** and forced-resume prefixes save
**97,280/105,054/128,555 T**. These are explicit prefix measurements, not
an extrapolated whole-movie CPU improvement. Required reads still cost
more than the original parser because they retain resumable parser state.

[The test](test_optional_packet.py) reuses the historical fixture unchanged
and pins its saved baseline cases. Every packet byte is exact and written
once, including **584 forced pauses** and continuation after register
clobber. Eight IRQ-stressed packets per volume plus synthetic split-length,
final-slot/EOF cases pass **4976 real AY-handler injections**, preserving
tested registers, stack, paging and sound-write behavior.

## Complete Fuse playback

All three independent runs reach EOF. All **25326 AY records** are exact
at 50 Hz, with zero underruns, IRQ gaps/duplicates or read retries.
Fuse checks **80 native-screen bytes per frame**, not every pixel. The
builder separately compares initial complete native/compact frames.
Physical drives and matched initial disk/IRQ phases remain unverified.

| Volume | Late frames: original / global / separate | Bad intervals: original / global / separate | Max lateness: original / global / separate, fields |
|---|---|---|---|
| 1 | 90 / 89 / 89 | 43 / 43 / 45 | 64 / 64 / 64 |
| 2 | 465 / 481 / 474 | 249 / 261 / 254 | 260 / 266 / 263 |
| 3 | 766 / 767 / 766 | 491 / 493 / 491 | 265 / 271 / 269 |
| Total | 1321 / 1337 / 1329 | 783 / 797 / 790 | |

Actual maximum OUT deviations are **4,538,121 / 18,648,804 / 19,074,250 T**.
Recovered late runs: **2/10/3**; volume 2 retains an unrecovered tail at
local frames **1237..1296**. Publication spans total **1,813,188,468 T**:
**212,724 T better than the global gate**, but **212,718 T worse than the
retained original**. Exact nominal timing and fallback jitter both fail.

Traces verify **8/20/7 = 35** native draws before the suspended packet
finishes. Their maximum delays after the preceding publication are
**42,745 / 113,132 / 35,717 elapsed T**. Remaining overlapping blocking
calls number **7/5/16**, with maximum delays **32,685 / 41,572 / 69,409 T**.
These intervals are elapsed response measurements, not saved CPU work.
Suspended transfers can contain another frame's drawing and must not be
summed with those draws as disjoint stages.

Measured Fuse read-service totals are **73,660,197 / 73,586,754 /
73,457,258 T**; seek/maintenance totals are **1,672,354 / 1,665,847 /
1,664,502 T**. These combine ROM, emulated disk, IRQ and contention and
are not instruction-only or physical-drive measurements.

## Decision and next work

**Keep as an experiment, without enabling it by default.** Removing the
global gate yields the expected CPU improvement and better complete
playback than that attempt, but does not outperform the retained baseline.
Earlier drawing alone does not remove the unfinished transfer/reconstruction
work needed for following frames. These comparisons do not quantitatively
isolate every cause of the remaining lateness.

Do not repeat mandatory-loop gating or treat optional responsiveness as a
cadence result. The next scheduling change must reduce measured work in
the long late runs or prepare more of that work before those runs, while
accounting for the finite decoded reservoir. Small register substitutions
remain useful incremental savings; they cannot explain multi-field stalls
away. Root releases and converter defaults remain unchanged.

## Reproduction and archived evidence

Run in the existing worktree:

```powershell
$env:PYTHONPATH='toolkit;C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/python_packages'
$env:OPENBLAS_NUM_THREADS='1'
python toolkit/build_optional_packet.py --baseline-build toolkit/inplace_keepalive_build.json --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/optional-packet-player --report toolkit/optional_packet_build.json --read-cache .tmp/resumable-packet-player/zx0 --read-cache .tmp/inplace-keepalive-player/zx0
python toolkit/test_optional_packet.py --directory .tmp/optional-packet-player --output toolkit/optional_packet_cpu.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/optional-packet-player --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/optional-packet-fuse --trace-pipeline --trace-fields
python toolkit/summarize_optional_packet.py --archive-directory .tmp/optional-packet-player --trace-directory .tmp/optional-packet-fuse --write
python toolkit/summarize_optional_packet.py
```

The first audit assumed the old archive included TRDs and stopped with
`KeyError: part01.trd`; no build or playback rerun was needed. The archive
step now reads the retained baseline images, checks their published hashes
and saves bank-7 bootstrap payloads. The auditor checks those payload hashes
against the historical metadata and verifies the unchanged required loop
and every relocated clone instruction against their actual bytes.

The [summary](optional_packet_summary.json) audits **51 gzip files**:
sources, reports, three experimental TRDs, baseline bank-7 payloads and
complete Fuse evidence. The three `.trd.gz` images use **Git LFS**. Archived
build/test hashes, exact streams, actual cold-installed code and full
publication/IRQ/read traces are checked. This is a complete experimental
comparison, not a smooth-playback release.
