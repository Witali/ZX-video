# Full-memory live PCM preview

**Disk retirement (2026-10-04):** obsolete speech TRDs described below
were removed at the user's request. Links marked "retired" lead to the
[removal inventory](retired-disks.json), with exact paths, hashes and the recovery
commit. Measurements, WAVs and build instructions remain historical evidence.

The current [bootable TRD (retired)](retired-disks.json) uses all eight
128K RAM banks. It stores **121344 bytes (118.5 KiB)** of unsigned
**8000 Hz /8-bit mono PCM**, converts it to beeper PDM while playing and loops
continuously. This adds **38400 bytes /46.296%** over the previous 82944-byte
live excerpt. The new source interval is **[60,75.168) seconds**, with no
sector-padding silence. Playback in Fuse Spectrum 128 takes **15.4023 seconds**
per loop because its measured PCM clock is 7878.312 Hz.

- [Actual Fuse sound recording](pcm-live-full/sound-128/fuse-preview.wav).
- [Measured-port reconstruction](pcm-live-full/beeper-preview.wav).
- [Source PCM8](pcm-live-full/pcm8k-preview.wav).
- [Build report](pcm-live-full/report.json) and [complete verification](pcm-live-full/verification.json).

Use drive A with Spectrum 128, Beta Disk/TR-DOS, sound enabled and normal
speed. Run `RUN "boot"` in TR-DOS if the disk does not autostart. Loading
finishes before playback; no disk reads occur while sounding. Reset to stop.
The display identifies this version as **121344 PCM BYTES**.

## RAM accounting

| Physical bank | Permanent use | PCM bytes |
|---|---|---:|
| 0, 4, 6, 1, 3, 7 | Entire bank, read through C000..FFFF | 98304 |
| 2 | Code 8000..85FF; PCM 8600..BFFF, read through C600..FFFF | 14848 |
| 5 | Screen 4000..5AFF; workspace/stack 5B00..5FFF; PCM 6000..7FFF, read through E000..FFFF | 8192 |
| **Total** | **All eight banks** | **121344** |

The exact 128 KiB budget is **121344 PCM +1536 code reservation +6912 screen
+1280 workspace/stack =131072 bytes**. Generated code occupies 1396 bytes;
140 bytes align the next PCM load to a 256-byte disk sector. There are no
unassigned whole sectors. This is the maximum within this retained screen,
workspace and sector-aligned layout, not a claim that every byte of the
machine can contain audio simultaneously.

The initial screen is loaded immediately after the code, copied to 4000,
then its staging memory is overwritten by bank 2 PCM. SP moves from B800 to
6000 before sector loading; the stack grows down inside 5F00..5FFF. A cold
Fuse guard rejects a stack write crossing below that area. BASIC/TR-DOS
workspace at 5B00..5EFF stays reserved. Paging bank 2 or 5 at C000 aliases
physical RAM already visible in the fixed windows; the loader addresses
avoid the code, visible screen and stack. No previous disk's RAM is needed.

## Cycle cost and output cadence

The 32-T conversion kernel and 1764-T ordinary four-sample loop are unchanged.
One shared ordinary loop replaces the former per-bank copies; eight short
bank tails retain the next address/page. At a bank boundary:

| Work | Previous corrected player | Shared loop | Difference |
|---|---:|---:|---:|
| Dispatch after page wrap | direct target | `JP (IX)` 8 T extra | +8 T |
| Set next bank-tail pointer | padding `JR next` 12 T | `LD IX,nn` 14 T | +2 T |
| Canonical paging | 27 T | 27 T | 0 T |
| **Extra per bank** | | | **+10 T** |

Thus `441*N +2*(N/256) +23*B` gives **53513836 deterministic T/loop**
for N=121344 and B=8. The paging fix itself was +1 T per bank versus the
original unsafe aliases, making the combined change +11 T per bank at equal
payload/layout. Ordinary output holds remain 44 T, sample transitions 43/49 T,
page work 46 T; bank work introduces 54, 59, 42 and 46 T holds. Counts follow
the [Zilog timing manual](https://www.zilog.com/docs/z80/um0080.pdf) and are
independently checked against executed instructions.

Actual cold Spectrum 128 playback averages **78783.119 PDM outputs/s**,
minimum **60116.949/s**, maximum 84450/s. All measured intervals are 42..59 T.
Both loop-wrap holds are 49 T. Across two loops ULA contention adds 2233052 T;
this is separate from deterministic CPU time. ROM and physical disk timing
belong to initial loading, not the playback formula. Source sampling remains
exactly 8 kHz; real playback is 1.5211% slower. No interpolation, PDM buffer
or lookup table is introduced.

## Verification and limitations

Twelve beeper unit tests pass, including distinct data in each of all eight
banks, exact capacity rejection, fixed-bank aliases, register/stack guards,
all PCM values and legacy-port rejection. Native execution and a fresh Fuse
Spectrum 128 boot verify **2426881 exact PDM bits**, every PCM byte, two whole
loops plus the first bit of the third, all 16 bank changes, 474 startup sector
reads, no runtime reads and the startup stack guard. This is a complete run.

The separate normal-speed sound captures cover both explicit Spectrum 128
and automatic disk startup, the latter having reproduced the previous
silence. Their reports check actual sound throughout two loops, 7FFD bank
values and unchanged 1FFD. See [128 capture](pcm-live-full/sound-128/report.json)
and [automatic capture](pcm-live-full/sound-auto/report.json). Sparse sound
traces complement the complete bit trace; they do not replace it.

The original paging failure and isolated correction remain in
[PAGING_FIX.md](PAGING_FIX.md). No physical Spectrum recording is claimed.
The host reconstruction has correlation 0.953164 and SNR 9.9713 dB against
the same timed/filtered PCM; these are conversion-error measures, not listener
acceptance. The longer passage changes the quality-measurement input, so its
score is not an equal-window quality improvement over the short build.

## Reproduction

```powershell
python audiobook-beeper/build_pcm.py "C:/Audio/book.m4a" --fill-memory --ffmpeg C:/Tools/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output build/pcm-full
python audiobook-beeper/record_pcm.py build/pcm-full --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output build/pcm-full-audio --machine 128
python audiobook-beeper/record_pcm.py build/pcm-full --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output build/pcm-full-auto --machine auto
python -m unittest discover -s audiobook-beeper -p "test_*.py"
```

The input audiobook must match the saved source hash. Preparation retains
the established mono/70 Hz highpass/two 3800 Hz lowpasses, 0.65 peak and
20 ms edge fades, with antialiasing before PCM8 quantization. The longer
excerpt is freshly prepared; its normalized/faded bytes are not assumed
identical to the shorter build. Producer snapshots and evidence hashes are
retained beside the new build.
