# The Entertainer: public-domain music on Spectrum 128

Experiment started on 2026-10-04 using the automatic direct-IMA3 converter
from commit `acf1682`. The user selected an unrestricted recording instead
of Queen. This is a separate music example; the audiobook reference stays
unchanged.

The user subsequently accepted the best achievable result for this example
even if it remains below 20 dB. The converter's normal 20-dB gate is retained
in the machine-readable report: a below-target listening preview is an
authorized deliverable, not evidence that the threshold was met. This does
not change the established audiobook reference or its quality requirement.

## Result

Use [ZX-music-Entertainer-IMA3.trd](../../../ZX-music-Entertainer-IMA3.trd)
in Fuse with Spectrum 128 and Beta 128/TR-DOS. The disk cold-boots
independently, shows loading progress, then repeats the fragment.
[result-preview.wav](result-preview.wav) is the normal-speed Fuse sound
capture; [source-preview.wav](source-preview.wav) is the prepared source.

| Check | Result |
|---|---:|
| Retained music / prepared duration | 31.128 / 31.144 s |
| Actual duration per repeat | 31.246780 s |
| Final SNR, first / second complete repeat | 17.837011 / 17.836344 dB |
| Mean speed error | -0.328930% |
| Mean PDM output rate | 127652.897 Hz |
| Phase error, first / second repeat | 0 / 0 T |
| Verified PDM outputs / decoded samples | 7977485 / 498304 |
| Runtime disk reads | 0 |
| Loading progress steps | 32 |
| Normal cold boot to sound | 26.454422 s |
| Normal WAV duration (two repeats) | 62.505964 s |

The original PCM-oriented pilot scored -3.279182 / -3.279105 dB against
the fixed-clock reference, before waveform timing compensation. The three
automatic host searches scored 17.598735 dB (width 256, horizon 128),
17.663213 dB (width 512, horizon 128), and 17.837011 dB (width 1024, horizon 256).
All used regularization 0.03 and the same source, level, clock and filter.
The third candidate was selected and independently verified on a new TRD.
The first two are host estimates, not independently executed disk results.

This is the best candidate found by the configured three-attempt search,
not a proof of a global codec optimum. The unchanged 20-dB gate remains
false; the converter returns exit code 2 and `preview_only:true`. This expected
quality status is distinct from a build or playback failure.

The [report](report.json), [native check](native.json),
[cold Fuse check](fuse.json), [normal recording check](sound-128/report.json),
[completion audit](completion-audit.json) and [artifact hashes](artifact-hashes.json)
preserve the evidence. Full selected output timestamps and compressed Fuse
trace are retained, along with all search reports and calibration probes.
Archived evidence is a selected snapshot, not a resumable converter cache.
An integrity-checked resume of the original working output reused all six
stages without replay and returned the expected quality-status exit code 2.

TRD SHA-256: `fb3eee76e9cfbf8060d60619f2e283f4b19484a6de5f2b10e6952d0653cb5a6f`.

## Source and rights

Scott Joplin's **The Entertainer**, performed by **IE** on an electronic
keyboard. The [recording page](https://commons.wikimedia.org/wiki/File:The_Entertainer_-_Scott_Joplin.ogg)
separately identifies the composition as public domain and the performance
as dedicated to the public domain by its performer, with a permission
fallback where dedication is unavailable. These declarations apply to
this particular recording. No Queen music is included.

[source.json](source.json) records the page revision, retrieval date,
download URL and SHA-256. [original.ogg](original.ogg) preserves the complete
downloaded input. The initial 31.128 seconds are retained; the original
recording is 233.850794 seconds, stereo 44.1 kHz Vorbis. Preparation uses
one fixed gain, mono 8-kHz PCM8, 80-sample edge fades and a 128-sample silent
guard. It fills 93432 bytes of resident packed IMA3 (249152 prepared samples).

## Reproduction

From the repository worktree, with the Python dependencies described in
[IMA3_DIRECT.md](../../IMA3_DIRECT.md):

```powershell
python audiobook-beeper/convert_ima3_audio.py audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --output .tmp/entertainer-rebuild --ffmpeg C:/path/to/ffmpeg.exe --fuse C:/path/to/fuse.exe
```

The default 20-dB threshold and three-attempt bounded search are unchanged.
The script performs preparation, separate assembly, cold-boot calibration,
waveform-aware encoding, complete two-loop verification and a normal-speed
Fuse audio capture. Use a new output directory for a new build; `--resume`
is available only with matching source, tools, settings and producer hashes.

The Z80 hot path is unchanged: ordinary 427.375 native T/sample, delta **0 T**
from `acf1682`; page/bank extras remain +14/+140 T. It decodes packed IMA3
directly, has no full PCM/PDM buffer and loops without runtime disk reads.
ROM/disk loading and ULA waits are measured separately in Fuse. The SNR
reference is the prepared PCM8 signal with the established comparison
filter, not the original full-band stereo recording. Physical hardware
has not been tested.
