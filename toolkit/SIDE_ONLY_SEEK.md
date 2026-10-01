# Sequential disk-head traversal

Updated 2026-10-01. Experimental CB46 player improvement; the full four-disk
release gate remains open. See [measurements](side_only_seek_report.json).

## Change

Runtime video sectors already follow consecutive logical tracks. Each pair
of logical tracks occupies the two sides of one cylinder. The old cached
reader selects a side, issues SEEK even when the cylinder is unchanged, and
sets READ SECTOR to 84h (settling enabled).

`--side-only-seek` compares the old and requested cylinder **before** updating
the cache. On an unchanged cylinder it selects the side, waits at least
200 microseconds, and leaves the reader's 80h command intact. Actual cylinder
changes retain SEEK, the selected drive's step rate, and READ 84h. FFh cold
state uses the original dispatcher. FEh after an idle interval forces the
full SEEK path. Periodic head-loaded maintenance and short-read fallback
remain active. Both register sets, the destination pointer, IM2 and the fast
IRQ vector retain their contracts.

The generic `convert_video.py --video-codec cb41 --guarded-cb46 --fps 10`
profile enables this automatically. Other profiles retain their defaults.
The cached rebuilder exposes the separate flag for controlled comparisons.
No packet, LZSA2, renderer, media, interleave or disk geometry changes occur.

## Hardware basis and limits

The pinned TR-DOS 5.03 ROM has SHA-256
`91259fca6a8ded428cc24046f5b48b31d4043f2afbd9087d8946eaf4e10d71a5`.
Tests check the actual bytes: 1FEBh/1FF6h only update the system latch and
select the side; 3E44h issues SEEK with the head-load bit. The
[disassembly](https://github.com/programandala-net/tr-dos) supplies readable
context. The [FD179x data sheet](https://www.abc80.net/archive/luxor/diskdrives/drives/western-digital-FD1791.pdf)
defines READ's E settling flag separately from side selection.

The [Shugart SA460 service manual, section 1.4.7](https://deramp.com/downloads/floppy_drives/shugart/SA410-460%20Service%20manual.pdf)
requires 200 microseconds after side selection. `LD B,55` plus 55 `DJNZ`
iterations takes `7 + 54*13 + 8 = 717 T`, over 200 microseconds at the
standard 3.5469 MHz clock. The pause starts after ROM side selection returns;
ROM return work, IRQs and contention only lengthen it. This is a standard-clock
assumption, not a turbo-machine guarantee or a physical-drive measurement.

The cache is trusted only while the existing idle recovery/keepalive contract
holds. Do not omit those safeguards or reuse a previous disk's RAM state.

## Deterministic Z80 cost

Counts use the [Zilog instruction table](https://www.zilog.com/docs/z80/um0080.pdf).
These are helper-entry through RET RAM instructions, including JP to the ROM
trampoline but excluding ROM bodies, controller delay, IRQs and ULA waits.

| Path | Previous T | Current T | Difference |
|---|---:|---:|---:|
| Same-cylinder side 0 to 1 | 401 | 1009 | +608 |
| Same-cylinder side 1 to 0 | 391 | 999 | +608 |
| New cylinder, side 0 | 391 | 456 | +65 |
| FEh head reload, side 1 | 401 | 466 | +65 |
| Same-track ordinary read | unchanged | unchanged | 0 |
| Cold dispatcher | unchanged | unchanged | 0 |

The small CPU increase pays for the explicit short pause and decision. The
benefit is removing the much longer controller settling delay. Decoder and
renderer instruction changes are **0 T**. Helper size is 89 ->107 bytes at
9A90h..9AFBh, still below the 9B00h row table; two extra stack bytes hold AF.
The component report also records complete adapter counts and retry costs.

## Measured playback

| Scope | Video bytes | Occupied sectors | SEEK calls, before ->after | Nominal misses, before ->after |
|---|---:|---:|---:|---:|
| Saved 256-frame window [4096,4352) | 185681 | 781 | 45 ->22 | 2 ->0 |
| Full part 4 [3744,5066), 1322 frames | 622695 | 2543 | 152 ->76 | 22 ->0 |

All source streams, AY, reference states and decoder/renderer code are
identical to their respective baselines. The window uses the direct-header
baseline; part 4 includes the already accepted invisible-attribute savings.
Do not compare their bytes as if they were the same encoding experiment.

Full Fuse runs have no missed nominal field, no invalid publication interval,
no accumulated drift, no read retry and no AY underrun. Maximum actual OUT
phase deviation is 16 T for the window and 19 T for part 4, rather than the
previous 70917 /1063627 T. Actual publication timing is recorded, not inferred
solely from field counters. Native and Fuse checks compare every screen byte;
the report also includes dirty cold boots and a three-volume generic fixture.

**The physical cylinder distance was already minimal.** Saved read traces
visit consecutive cylinders without any backward step. The optimization
halves redundant SEEK commands on this layout; it does not halve physical
travel. Keepalive SEEK calls target the current cylinder and are counted
separately. Reordering runtime tracks cannot reduce the existing one-way
distance; future scheduling work should address rotational sector wait and
buffer availability only if complete timing evidence requires it.

## Reproduction and remaining release work

1. Run `python -m unittest test_side_only_seek test_inplace_keepalive`.
2. Rebuild each recorded cached baseline with `rebuild_cell_player.py`, adding
   `--shared-audio --four-video-slots --inline-cells --sector-cache
   --streaming-lzsa2 --direct-lzsa2-header --side-only-seek --verify cold`.
3. Run `verify_cached_cell_player.py`, `measure_fap3_fuse.py --trace-pipeline`
   and `capture_cell_codebook_full.py` on each output. Use one Fuse at a time.
4. Run `check_generic_cb41.py --guarded-cb46 --fps 10 --only colour`, supplying
   tool paths, the pinned ROM, Fuse, a new output directory and report path.
5. Run `analyze_side_only_seek.py --root . --evidence toolkit/side_only_seek_evidence
   --output toolkit/side_only_seek_report.json`, followed by
   `verify_refined_av_archive.py` with `--index` after staging the LFS images.

The report names all cached input/output scopes and hashes every artifact.
Parts 1..3 and actual preceding-EOF continuation across the four-volume movie
still need full validation. The generic fixture's two transitions use modeled
ROM bootstrap checks. Root release images remain unchanged until the complete
set passes. No physical floppy drive has been tested.
