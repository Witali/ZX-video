# Loudness-normalized Entertainer: IMA3 and IMA4

Requested 2026-10-04. Build two independently bootable, looping Spectrum 128
and Beta Disk TRDs from the same first 23.344 seconds of the existing public-domain
Entertainer recording. Both receive exactly the same 186880-sample mono
PCM8/8-kHz reference, including the final 128-sample silent guard. This fills
the IMA4 resident payload; IMA3 uses fewer bytes for the same excerpt.

## Normalization

Downmix and resample before measurement. Use FFmpeg's two-pass EBU R128
`loudnorm` filter with -18 LUFS, -2 dBTP and LRA 11 targets. The source has
peaks too high for constant gain alone, so the measured second pass uses
dynamic normalization/peak limiting. Preserve at least the existing PCM8
encoder headroom, apply 10-ms edge fades, quantize and measure again.

The prepared PCM8 music measures **-17.89 LUFS and -1.97 dBTP**, LRA 7.0.
No additional safety attenuation is necessary and no samples are clipped
when quantizing (unsigned range 27..230). The initial downmixed source
measures -16.73 LUFS /+1.83 dBTP; this request is loudness normalization with
peak control, not indiscriminate amplification. The source originally
exceeding 0 dBFS is retained as float until normalization.

The same first 186752 samples of the earlier peak-normalized music reference
measure -19.84 LUFS /-1.31 dBTP. The new prepared music is therefore 1.95 LU
louder on that comparison, with a lower true peak. The older excerpt has no
fade at this truncation point; its original end fade is outside this prefix.
The measurement log is retained. To repeat the old-reference check:

```powershell
ffmpeg -i audiobook-beeper/experiments/ima-3bit-entertainer/source-preview.wav -af "atrim=end_sample=186752,loudnorm=I=-18:TP=-2:LRA=11:print_format=json" -f null -
```

`normalized-source.wav` is fed through `--prepared-pcm` to both codecs so
that their normal peak-gain preparation cannot undo the chosen level.
The per-codec quality reference is this identical normalized PCM8, not the
original full-band stereo file. PDM/codec reconstruction can change the
actual output level; source loudness is not a claim about physical speakers.

## Reproduce

Use the project Python runtime/dependencies with `audiobook-beeper` and
`toolkit` on PYTHONPATH. The output directory must not already exist.

```powershell
python audiobook-beeper/experiments/entertainer-normalized/build.py --output build/entertainer-normalized --ffmpeg path/to/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

The script runs the common converter with explicit `--codec ima3` and
`--codec ima4`, checks that both preserved the exact reference hash, and
retains full conversion logs. IMA3 uses its accepted overlapping waveform
search, while IMA4 uses the historical automatic clock-compensation search.
This is a comparison of the two available pipelines, not of bit depth alone.
Both must pass complete native/Fuse playback and the +/-2% speed check.
The user's earlier permission to deliver the best bounded music result
below 20 dB remains applicable; a missed threshold is disclosed in reports.

## Bounded IMA3 search

All three attempts use the same prepared PCM and the calibrated pilot
schedule, with 64 committed samples per search step. Scores below are
host estimates, not playback verification of the candidate disk.

| Beam width | Horizon, samples | Estimated SNR, dB | Encoding time, s |
| --- | ---: | ---: | ---: |
| 256 | 128 | 18.948458 | 259.859 |
| 512 | 128 | 19.027906 | 526.813 |
| 1024 | 256 | 19.082042 | 2723.703 |

Select the third stream for the final disk. All attempts have zero predictor
saturation events. The uncompensated pilot measures -3.299089 dB and is
retained only as the timing baseline; it is not a listening deliverable.
The expensive third search adds only 0.054136 dB over the second estimate.
This is the complete configured search, not a claim of a global optimum.

The saved source and its rights metadata are in the existing
[Entertainer experiment](../ima-3bit-entertainer/README.md). No new recording
is downloaded. The audiobook reference is unchanged. Z80 hot paths are
unchanged: IMA3 427.375 T/sample and IMA4 423 T/sample, each delta 0 T;
page/bank extras remain +14/+140 T. ROM/disk time and ULA waits are separate.

## Verified deliverables

| Result | IMA3 | IMA4 |
| --- | ---: | ---: |
| Resident audio bytes | 70080 | 93440 |
| First / second loop SNR, dB | 19.082042 / 19.031203 | 17.237725 / 17.246241 |
| Mean speed error | -0.299133% | -0.043272% |
| Measured loop duration, s | 23.430087 | 23.370113 / 23.370112 |
| Mean PDM output rate, Hz | 127652.961 | 128054.581 |
| Fully verified PDM outputs, two loops | 5981841 | 5985301 |
| Cold startup to sound, s, normal recording | 22.815238 | 26.434444 |

- [IMA3 disk](../../../ZX-music-Entertainer-normalized-IMA3.trd) and [Fuse WAV](ima3/result-preview.wav).
- [IMA4 disk](../../../ZX-music-Entertainer-normalized-IMA4.trd) and [Fuse WAV](ima4/result-preview.wav).
- [Common normalized source](normalized-source.wav) and [machine-readable comparison](comparison.json).

Both are **looping listening previews below the 20-dB quality target**.
SNR is measured against the common prepared PCM8/8-kHz reference using the
existing 70-Hz..4.5-kHz measurement filter, without fitting gain, delay or
time stretch. It is not a full-band-original or physical-speaker measurement.
The selected IMA4 stream is compensation pass 2: the pilot and first pass
measure -3.715639 and 17.218503 dB minimum, respectively. IMA3's more expensive
waveform search gives the better final score here; this does not establish
that fewer codec bits intrinsically give better quality.

Each disk passes independent cold Spectrum 128/Beta Disk boot and two complete
loops in Fuse 1.9.0. Every PCM predictor/index and PDM bit passes both native
and full Fuse verification; memory guards and paging checks pass. Each two-loop
run covers 373760 decoded PCM samples. There are no disk reads during
playback. Full-trace cycle phase deltas are 0/0 T for IMA3 and 2/0 T for IMA4;
the latter is not claimed to have exact zero startup phase error. Both pass
the +/-2% speed limit. Separate 100%-speed FMF recordings cover both loops
and preserve paging. These are internal Fuse recordings, not WASAPI speaker
captures; physical hardware and a new user audition have not been tested.

The archive retains normalization logs, all bounded-search summaries,
selected binaries/assembly, exact producer snapshots, full selected Fuse
traces and normal-speed recordings. It is evidence, not a resumable build
cache. Verify its 219 authenticated artifacts and both root disks with:

```powershell
python audiobook-beeper/experiments/entertainer-normalized/archive.py
```

`archive.py --archive build/entertainer-normalized --write-manifest` publishes
a completed build and refuses to overwrite a different saved artifact.
The existing audiobook control and earlier Entertainer examples are unchanged.
