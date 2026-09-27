# Adapted Fast ZX0 in independently bootable TRDs

Date: 2026-09-27. Repository input: `3aa3e4b`. Comparison: retained Turbo
periodic-drive player at `a84451d`. Scope: all 4221 frames of the authorized
edit, unchanged resolution, 25/3-fps nominal schedule and 50-Hz AY data.

**Fast is now installed by the new builder and all three disks complete in
Fuse.** Retain it as the next experimental baseline: late frames fall from
1321 to 1239 with exact sound and identical video bytes. Neither video timing
gate passes; these images are a preview, not a replacement release.

## Integration

[fast_zx0_player.py](fast_zx0_player.py) installs the exact decoder measured
in [FASTER_ZX0.md](FASTER_ZX0.md). The existing compressor, stream, block
boundaries, three-slot queue, frame decoder, AY engine and drive-maintenance
policy retain their behavior. The new
[builder](build_fast_zx0_player.py) selects Fast directly; older builders
remain available to reproduce comparisons.

The installer verifies the original Turbo bytes, checks that the extra
helper space is empty and preserves the frame return at 8F09h. It remaps
**22 known instruction operands** in the input producer, queue, bridge and
packet validation paths. Every substitution retains its opcode, length and
instruction-table timing: **delta 0 T**. The producer is independently
reassembled against the new labels and compared byte for byte. The low
bridge is also updated in its cold-start overlay at A200h.

Fast uses **401 bytes of code/state versus 314**. Helpers/state occupy
7C00h..7C7Ch; the core occupies 8DF2h..8F05h. Existing bank-5/bank-2 startup
sections load these regions before playback. No video, audio, disk buffer
or dictionary is reduced. No state from a previous disk is required.

The build verifies every original video and AY byte and every decoded ZX0
block. All three disks boot with dirty RAM and prime the expected first
native and second compact frame. The real prompt/bootstrap code accepts
the next disk, rejects a wrong disk/series and reproduces independent cold
RAM; this handoff test mocks TR-DOS sector reads. Fuse playback cold-boots
each disk independently. Actual interactive disk replacement and physical
hardware are not tested.

## Compression and disk occupancy

The stream stays **1,818,909 bytes / 188 blocks / 7106 video sectors**.
Decoded video remains 2,965,011 bytes. AY and pixel data are unchanged.
The increased decoder size causes **no additional occupied disk sectors**:

| Disk | Frames | Occupied sectors | Free sectors | Video start sector |
|---|---:|---:|---:|---:|
| 1 | 1624 | 2462 | 82 | 107 |
| 2 | 1297 | 2463 | 81 | 108 |
| 3 | 1300 | 2462 | 82 | 109 |

The root `ZX-video-fast-preview_part01..03.trd` files are exact copies of
the measured images, stored through Git LFS. Their hashes and timing status
are in [fast_zx0_preview.json](fast_zx0_preview.json). The earlier root
release and older preview remain available.

## CPU and actual playback

The installed core matches the earlier complete paired CPU measurement:
**189,573,555 → 183,122,436 decoder T**, saving **6,451,119 T / 3.403%**.
Producer+decoder saves 3.203%. All 188 blocks improve, but 62 of 11584
individual calls are slower by at most 69 T. The earlier exact instruction
path counts and IRQ/unaligned-demand tests remain applicable to the identical
code. See [the native audit](audit_faster_zx0.py).

The [cold-loaded queue comparison](measure_fast_zx0_queue.py) verifies all
22 remapped references and ten actual queue paths. Absolute control costs
are **75, 109, 172, 96, 169, 302, 562, 764, 808 and 1240 T**, respectively;
each remains unchanged. These exclude decoder, audio, copy and disk callee
bodies. Do not add them to nested full-playback measurements.

Full Fuse runs include memory contention, ROM execution, disk emulation,
interrupts, all publications, all AY records and all runtime sector bytes.
There are no debugger-installed code patches or fast-read retries.

| Disk | Late frames: Turbo → Fast | Bad intervals: Turbo → Fast | AY underruns | Fast effective fps |
|---|---:|---:|---:|---:|
| 1 | 90 → 86 | 43 → 41 | 0 | 8.333333 |
| 2 | 465 → 404 | 249 → 230 | 0 | 8.075773 |
| 3 | 766 → 749 | 491 → 473 | 0 | 8.333333 |
| Total | **1321 → 1239** | **783 → 744** | **0** | — |

All **25326 AY records** remain exact at 50 Hz, with no missing or duplicate
record fields. Frame progress reaches 100% on every disk. The summed span
between first and last publication falls **1,812,975,750 → 1,812,124,850 T**,
only **850,900 T / 0.0469%**. This span is not full startup/playback time.
Initial IRQ/drive phases were not matched between attempts; these elapsed
differences are observed runs, not a deterministic CPU attribution.

Nominal and fallback timing are checked separately from actual OUT times.
Maximum lateness is **62 / 248 / 244 fields** by disk; maximum actual
deviations are **4,396,302 / 17,585,184 / 17,301,569 T**. Late-run recovery
is **3/3, 13/14 and 3/3**: one disk-2 run has not recovered at EOF. Exact
missed-frame indices and all late runs are saved in the summary. Average
8.333-fps output on disks 1 and 3 does not mean evenly timed frames.

Moving mutable decoder state to bank 5 increases contended-memory work.
Fuse measures the combined result; the CPU percentage must not be presented
as whole-player acceleration. The improvement supports keeping Fast, while
remaining work concerns total packet/frame delivery and deadline misses.

## Verification scope and reproduction

Full native decoding verifies every output byte, input cursor and overlap
constraint. The unchanged frame implementation retains its existing 4221-frame
full-screen CPU proof. Fuse checks 80 deterministic screen bytes per frame,
not every pixel; all 4221 publications and sound records are checked. This
combination is complete for the stated experiment, not a passing release.

Use the project Python dependencies and `PYTHONPATH=toolkit`. From the repo
root, with the existing input/cache worktrees:

```powershell
python toolkit/build_fast_zx0_player.py --baseline-build toolkit/inplace_keepalive_build.json --raw-directory .worktree/volume-huffman/.tmp/probe --states .worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 .worktree/audio-fidelity/.tmp/bin/zx0.exe --read-cache .worktree/streaming-zx0-player/.tmp/inplace-keepalive-player/zx0 --read-cache .worktree/streaming-zx0-player/.tmp/inplace-zx0-cache --output .tmp/fast-zx0-player --report toolkit/fast_zx0_player_build.json
python toolkit/measure_fast_zx0_queue.py --baseline .worktree/streaming-zx0-player/.tmp/inplace-keepalive-player --fast .tmp/fast-zx0-player --output toolkit/fast_zx0_queue_cpu.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/fast-zx0-player --raw-directory .worktree/volume-huffman/.tmp/probe --states .worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/fast-zx0-fuse --trace-pipeline --trace-fields
python toolkit/snapshot_resident_audio_player.py --build toolkit/fast_zx0_player_build.json --directory .tmp/fast-zx0-player --fuse .tmp/fast-zx0-fuse --output toolkit/fast_zx0_player_evidence
python toolkit/summarize_fast_zx0_player.py --write
python toolkit/package_fast_zx0_preview.py --directory .tmp/fast-zx0-player
```

The snapshot refuses to overwrite different evidence. For another timing
experiment, use a separate evidence directory and retain this comparison.
To audit the existing evidence without rerunning the emulator:

```powershell
python toolkit/summarize_fast_zx0_player.py
```

Saved evidence: [build](fast_zx0_player_build.json),
[queue CPU](fast_zx0_queue_cpu.json), [summary](fast_zx0_player_summary.json),
[source/metadata/Fuse traces](fast_zx0_player_evidence/manifest.json).
