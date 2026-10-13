# Adaptive RAM audio disks and a cover-first loader

Implemented2026-10-13 from main `6168ba14`. The user requests available RAM on
Spectrum128, Scorpion256, Pentagon512 and Pentagon1024, an actual cartoon
title loaded before audio, and a bottom loading progress bar. The song retains
the previously selected original direct IMA4 settings and the main90-second
cut, without its late reprise. The old release remains unchanged.

The new sequential format automatically detects distinct physical banks.
Each candidate is checked against all earlier banks and every probe byte is
restored. Pentagon1024 is distinguished through the EFF7 high-bank alias test;
the512K lock bit is never asserted on a512K device. The worker always restores
normal mapping before TR-DOS calls. Cold disks authenticate their own header,
load their own cover and initialize their own RAM; predecessor RAM is optional.

| Model | Total RAM | Additional sector cache | Native IMA4 ordinary sample | Native IMA3 mean sample |
|---|---:|---:|---:|---:|
| Spectrum128 |128 KiB |0 |423 T, delta0 |427.375 T, delta0 |
| Scorpion256 |256 KiB |128 KiB |423 T, delta0 |427.375 T, delta0 |
| Pentagon512 |512 KiB |384 KiB |449 T, delta+26 |445.375 T, delta+18 |
| Pentagon1024 |1024 KiB |896 KiB |449 T, delta+26 |445.375 T, delta+18 |

These are deterministic CPU counts, excluding ULA, ROM and physical disk
latency. Pentagon FIRST dispatch adds a10-T absolute jump and4/2 four-T NOPs;
the original8-T JP(IY) remains. Scorpion's ULA-paced path needs no added delay.
The IMA4 page and bank extras remain14/140 T, delta0. The approximately128-kHz
16-pulse carrier remains. Complete measured CPU intervals are independently
checked in the native reports; actual rate and disk pauses are measured in Fuse.

Base128 KiB is explicitly allocated: two16-KiB banks for resident code/cache
worker and tables/TR-DOS/stack workspace, plus89856 audio bytes,6912 screen
bytes and1536 bytes for a compressed transient controller. IMA3 uses89850
audio bytes plus six sector-alignment bytes. Active capacity is179712 IMA4
samples or239600 IMA3 samples. Every additional bank stores upcoming raw disk
sectors, including part code/tables, up to real EOF. Empty RAM beyond EOF is
not filled with disk padding. A whole640-KiB TRD fits within Pentagon1024 RAM.

The sector cache avoids floppy reads for complete cached parts. Switching
parts still copies them into the active decoder banks, so short RAM-copy
pauses remain; this implementation does not claim seamless transitions.
After a window is consumed, refill it before audio. No ROM/disk call occurs
during live PDM. A fixed-bank bounce buffer prevents extended paging from
depending on undocumented TR-DOS state. Sixteen persistent bytes in unused
packet-page space at5B70 survive table-sector replacement; models requiring
more than18 feedback entries are rejected rather than overlapping that state.

The original title frame at movie4.5 seconds is converted to a legal256x192
Spectrum screen. Its top160 lines remain visible during loading and playback.
The bottom32 lines contain an outlined bar. The exact denominator includes
PLAYER, recording-specific tables, active audio and new RAM prefetch. The bar
reaches32 cells only after every required sector. Cold and resumed volumes
show their cover before audio; disk prompts and END OF AUDIO retain the old UI.

The public converter defaults to adaptive sequential disks:

```powershell
python audiobook-beeper/convert_audio.py input.wav --output new-output `
  --codec ima4 --cover title.png --fuse 'C:/Program Files (x86)/Fuse/fuse.exe'
```

`--ram-cache off` retains the legacy sequential layout; looping previews remain
legacy by default. `--cover` accepts an image or an exact6912-byte SCR. Existing
codec preparation/search and20-dB quality gates remain; all four machine
measurements contribute to the adaptive converter's quality result. Full RAM
prefetch can exceed the former60-second startup target, which is reported
explicitly. It is the user-requested tradeoff for loading available RAM first.

Reproduce the checks from the repository root with NumPy, Pillow, z80, pyz80,
FFmpeg and Fuse installed:

```powershell
python -m unittest discover -s audiobook-beeper -p test_ram_cache.py
python -m unittest discover -s audiobook-beeper -p test_ram_series.py
python audiobook-beeper/experiments/ram-audio/check_controls.py
python audiobook-beeper/experiments/ram-audio/build.py `
  --prepared audiobook-beeper/experiments/sea-foam-song/evidence/prepared-song.wav `
  --cover audiobook-beeper/experiments/ram-audio/evidence/title-source.png `
  --output new-song-build --fuse 'C:/Program Files (x86)/Fuse/fuse.exe'
```

Use a fresh song output or a matching authenticated resume. The shared LZSA2
serializer and original licensed forward decoder restore only the transient
controller; audio is never expanded to resident PCM/PDM. Generated assembly
retains upstream notices and routine/timing comments.

Verification and limits are recorded in [the saved evidence](evidence).
`verified` is the final song image; `ima3-swap` proves independently cold
volumes, wrong-disk rejection and continuation from actual predecessor RAM
with other banks poisoned; `cli` proves the public default and supplied cover.
Native loading proves every resident byte, code/pacing bytes, cover, bar and
bank guards. Separate complete native PDM runs prove every source pulse,
predictor/index and CPU hold. Full cold Fuse runs retain all source samples,
actual ROM/disk operations, automatic transitions and END OF AUDIO.

Earlier `song` and `final` attempts are retained as superseded diagnostics.
Failures included unmarked native callbacks, DE clobber before sector reads,
stale EOF cache count, too-small controller storage, a missing clone-patch
return, and incorrect Scorpion pacing. Each was corrected and verified.
Scorpion can produce repeated debugger observations at machine-event
boundaries: move the index observation away from the DD-prefixed instruction
and require the full monotonic1..32 progress sequence while allowing identical
repeated observations. The final complete same-image/same-command traces
are rechecked after that observation fix; no samples or timing intervals are
discarded. Saved-trace postflight is identified separately from a fresh run.

The song is a listening preview with the user's original, uncompensated model;
it does not acquire a20-dB fixed-clock qualification merely through caching.
The accepted earlier song has approximately-3 dB against an unfitted fixed
clock and19..21 dB against its actual sample boundaries. The new report keeps
the strict fixed-clock measurement and does not retune source/gain/delay.
Physical Spectrum/clone hardware has not been tested. Paging semantics were
cross-checked with Fuse's [Pentagon512 implementation](https://raw.githubusercontent.com/fuse-emulator/fuse/master/machines/pentagon512.c)
and the local Fuse/libspectrum Scorpion/Pentagon1024 and SZX sources.
