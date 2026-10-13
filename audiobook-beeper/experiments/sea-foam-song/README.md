# Main sea-foam song with the preferred original direct IMA4 player

2026-10-13. The user requests the main song from the existing cartoon source,
retaining the original vocal and music on one TR-DOS disk. The later reprise
is explicitly excluded. The user supersedes the initial full-disk settings
with the exact settings of `ZX-audiobook-IMA-ADPCM-direct-test.trd`.

- [Bootable song TRD](../../../ZX-music-Sea-Foam-IMA4-direct.trd)
- [Original song WAV](evidence/original-song.wav)
- [Complete build and execution report](evidence/report.json)
- [Authenticated artifact manifest](evidence/manifest.json)

The selected source interval is **[133.6,223.6) seconds**, or **90 seconds**.
The unprocessed `original-song.wav` retains stereo 44.1-kHz PCM16 decoded from
the existing AAC source. The separate Spectrum preparation is mono PCM8 at
8 kHz. Both are extracted from the same authenticated cartoon source, SHA256
`995ddb8988fd57f5d718df9f4811faf7d7dc68999164116effe04ce1178bd931`.

The public song-only clip [LxoQbVhXmkw](https://www.youtube.com/watch?v=LxoQbVhXmkw)
was used only to locate the main number. Its 88.448-second decoded audio
matches the source near 134.5 seconds; the selected cut includes short
musical margins. Source captions and inspected scene boundaries distinguish
the later dialogue and reprise. No audio from that different upload is mixed
into the output. It is not part of the reproducible build's inputs.

## Preserved settings

The preferred reference SHA256 is
`9ce319e8b9352a96ed965d87ff3d1d8698df7d788221563758d306d23c053013`.
The current assembler reproduces every byte of that reference from its
archived packed payload. See `evidence/reference-rebuild.json` and the
[historical preparation audit](../../DIRECT_REGRESSION.md).

- Source filtering: 70-Hz high-pass and two two-pole 3800-Hz low-passes.
- Normalize the complete selected song's filtered peak to 0.65, add the
  historical 20-ms outer fades, then apply `volume=4` and
  `alimiter=limit=0.85:attack=5:release=100:level=0:latency=1`.
- Preserve the historical 192-kHz preparation rate, then round-trip through
  8-kHz unsigned PCM8 using FFmpeg's resampler and explicit nearest rounding.
- Encode with the historical PCM beam search: width 32, block 64 samples.
- Preserve the original native-weight feedback table, beta 0.5, extent 1,
  and sixteen PDM pulses per decoded sample. Do not substitute the later
  measured-weight table, waveform search, offline clock compensation, or
  silent repeat-phase lock.

The explicit request authorizes the historical voice limiter on this music.
It changes dynamics and is not waveform-transparent. The original WAV remains
available for ordinary listening. No generic converter default changes.

## One-disk layout and timing

The existing sequential IMA4 controller fits all **720000 source samples** in
four parts: [0,23.344), [23.344,46.688), [46.688,70.032), [70.032,90) seconds.
Each part appends at least 128 silent samples and fades its last 160 retained
samples into the reset guard, as in the original packet preparation.
The final part is rounded to 160256 prepared samples, without repeating audio.

The disk uses **2039 of 2560 sectors**, leaving 521 free. It boots independently
on Spectrum 128 + Beta Disk, automatically loads subsequent parts and ends at
`END OF AUDIO`. Blocking floppy reads occur between parts and cause audible
pauses. This preserves the requested direct PDM algorithm; it is not gapless
floppy playback.

The source-bearing hot path remains **423 T/sample**, delta **0 T** from the
preferred reference. Its holds are 36/28/28/31/24/26/22/20 T and
22/26/22/30/31/27/34/16 T, summing to 215+208=423 T. Page/bank extras remain
14/140 T, each delta 0. These are the previously counted instruction-table
costs in [DIRECT.md](../../DIRECT.md). The series exit is in the silent guard:
61 T to clear the beeper versus 103 T to the old next output, delta -42 T
between different endpoints; 33 final guard pulses are omitted. No musical
sample or source-bearing pulse is excluded. Disk ROM time, emulated physical
delivery and ULA waits are measured separately in full execution.

All 128 KiB remain accounted for: 93440-byte maximum packed audio, 6912-byte
shadow screen, 16384-byte bank-5 tables/TR-DOS workspace and 14336-byte bank-2
resident reserve. Smaller parts leave the remaining audio capacity unused.
There is no full PCM or PDM expansion buffer.

## Verification and reproduction

The complete cold Fuse run reaches `END OF AUDIO`, checking **11534204 PDM
bits** and **720888 predictor/index observations**, protected memory, paging,
all 32 loading progress steps per part and all three automatic transitions.
Timing differences against independently qualified resident loops are
[-5,3], [0,0], [0,1] and [0,1] T; every pulse stays within the existing 8-T
limit. No additional ready-phase reference was needed on this input.
The separate resident proofs check two complete loops each: **23068676 bits**
and **1441792 predictor/index observations** in total.

Cold preparation takes **27.388691 seconds** in Fuse. The three reload pauses
are **22.730355,22.550431,20.751192 seconds**. All **2054 disk-sector calls**
occur outside active audio. Complete part speed errors are
**+0.041303%..+0.041484%**, within the 2% requirement. These are emulator
measurements, not physical-drive tests.

| Part | Minimum resident sample-boundary SNR, dB | Full-volume fixed-8-kHz SNR, dB |
| --- | ---: | ---: |
| 1 | 19.260738 | -3.114068 |
| 2 | 19.662949 | -3.052649 |
| 3 | 20.641649 | -3.152757 |
| 4 | 19.569271 | -3.172644 |

The first column follows actual sample boundaries, as the preferred disk's
historical quality measurement did. The second uses the original fixed
8-kHz timeline: the explicitly preserved, uncorrected clock accumulates
phase differences, which are counted as waveform error on this tonal music.
These measurements are not interchangeable or a listening test. A universal
20-dB quality gate or a removal of the reported vibration is not claimed.
The report explicitly marks this user-selected legacy listening artifact
as a preview, with acceptance pending.

TRD size: 655360 bytes. SHA256:
`ba7f2924a030f72ccd5cbfe0b1bae34ab34b29dc1b2c9446393bb456b7bb588f`.

`build.py` checks the exact source and preferred reference hashes, preserves
every complete native and cold Fuse proof for each resident part, independently
decodes every IMA sample with FFmpeg and then checks the complete chained disk.
The standard volume verifier retains its **8-T pulse timing limit**. If its
natural cold ready phase differs, an additional complete two-loop proof
qualifies the unchanged legacy preview in that naturally occurring phase.
The modern phase-lock requirement is not imposed on the explicitly selected
old player, which never had that filler. All bit, predictor/index, memory,
paging, speed, startup UI, automatic transition and EOF checks remain.

From the repository root, use the existing NumPy, pyz80 and native Z80 package
environment with `audiobook-beeper` and `toolkit` on PYTHONPATH:

```powershell
python audiobook-beeper/experiments/sea-foam-song/build.py --source .tmp/youtube-WGc7ptKfA9c.mkv --reference-disk ZX-audiobook-IMA-ADPCM-direct-test.trd --output .tmp/sea-foam-song-rebuild --ffmpeg C:/Tools/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

Use `--resume` only with the exact same script, producer and executable hashes.
`archive.py` retains 327 authenticated files /331192377 bytes before the
manifest itself, including full resident/volume traces, exact output times,
WAVs, assembled code, input settings and producer snapshots. The TRD and
large WAV/gzip artifacts are stored in Git LFS.
`check_archive.py`, run from the repository root, authenticates all 329
archived/root/index artifacts against the manifest, including 178 LFS
identities. The complete index check passes with zero mismatches. Byte-preserving
attributes follow generic JSON rules, preventing newline conversion of the
copied reference-rebuild report.

To reassemble the disk from saved packed streams without requiring the
external cartoon source or repeating encoding:

```powershell
python audiobook-beeper/experiments/sea-foam-song/reproduce.py --output .tmp/sea-foam-song-byte-rebuild --build-only
```

The [completed build-only check](rebuild-check.json) reproduces all 655360 bytes exactly. Omit
`--build-only` and supply `--fuse` and `--ffmpeg` for another complete playback
check. Byte reproduction is separate from the original full execution proof.

The independently bootable TRD is a listening artifact; user acceptance and
physical hardware results are not claimed. Sample-boundary SNR follows actual
timing as in the preferred disk. The full-volume verifier additionally records
fixed-8-kHz-reference SNR, including the preserved old clock distortion; these
two clock definitions must not be conflated.
