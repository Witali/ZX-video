# Sequential IMA3 audio disks

Updated 2026-10-04. The automatic converter now defaults to **one TRD**.
The general `convert_audio.py` entry point selects this IMA3 profile by
default; `--codec ima3` is optional. The user accepted its overlap speech
reference in interactive Fuse playback.
It fills that disk with consecutive RAM-sized parts, stopping before the
next whole part that would overflow it. `--disk-mode all` retains the entire
selected input across numbered disks. Each disk boots independently.

```powershell
python audiobook-beeper/convert_audio.py "input.m4a" --output "build/audio" --ffmpeg "path/to/ffmpeg.exe" --fuse "path/to/fuse.exe"
python audiobook-beeper/convert_audio.py "input.m4a" --output "build/full-track" --disk-mode all --ffmpeg "path/to/ffmpeg.exe" --fuse "path/to/fuse.exe"
```

The default output is `audio.trd`; all mode produces `audio-0001.trd`,
`audio-0002.trd`, etc. `report.json` records retained source samples,
truncation, measured quality, disk count and complete verification.
`volumes.json` maps parts to disks. Temporary per-part disks under `work/`
are encoder/verification artifacts; only root-level TRDs are deliverables.

The previous repeating RAM demo remains available with `--disk-mode preview`
and writes `audiobook-preview.trd`. The advanced `--prepared-pcm` and
`--reuse-pilot` flags apply to that preview mode. `--duration N` bounds the
selected prefix in every mode. `--resume` requires unchanged source, tools,
settings and producer files; completed per-part searches are hash checked
and reused, then the final volumes are verified again.

The [overlapping encoder](experiments/ima-3bit-overlap/README.md) is now used
automatically during waveform search. It reduces periodic block-boundary
errors without changing the player. For the updated speech listening test,
use [ZX-audiobook-IMA3-overlap-test.trd](../ZX-audiobook-IMA3-overlap-test.trd).
It retains the same two 23.36-s excerpts and loading pause as the earlier test.

## Playback and capacity

Load the disk through TR-DOS. The player displays `LOADING AUDIO DATA` and
32 progress steps, hides the loading text, plays the part, then loads the
next one automatically. After the final part on a nonfinal volume it shows
`INSERT DISK NNNN` / `THEN PRESS SPACE`. Insert the requested disk into the
same drive and press Space. A wrong volume or another recording is rejected
before playback. The last disk displays `END OF AUDIO` rather than looping.

This PDM implementation monopolizes the CPU while producing sound. Blocking
TR-DOS sector reads therefore happen **between** parts; those pauses are
audible. They are not gapless playback, and the program does not compress
the source timeline to hide them. [Gentle compression and global normalization](AUDIO_DYNAMICS.md)
are applied continuously to the whole selected track; `--dynamics off` keeps
the previous peak-only gain. Parts have 10-ms edge fades and at least 128 silent guard
samples. A very short final part is zero padded to 8192 samples, never
repeated. All-mode source sample ranges cover the input exactly once.

The normal profile keeps 94458 packed bytes /251888 prepared samples in
seven audio banks, including the unused tail of fixed bank 2. Subtracting
the guard gives **31.470 seconds of source per full part** at 8 kHz. Five
full parts fit one TRD: **157.350 seconds of source**. A sufficiently short
last source part can fit as a sixth; otherwise remaining sectors are left
free. The format prioritizes full-RAM parts rather than splitting another
part just to occupy the last disk sectors.

## Memory and timing

The 57-byte resident exit stub fits the compact player's existing 64-byte
padding at B3C0..B3FF: **zero additional physical RAM reservation**. Bank 2
still reserves 13312 bytes. The 2048-byte transient controller is loaded
into 4000..47FF only after audio stops, replacing PDM tables. Its headers
use 4800..4BFF; the stack stays at 6000, clear of TR-DOS workspace. All audio
is loaded again for each part. The two PDM table files occur once per disk.
The separately assembled controller and player binaries are packaged by
Python; Python does not emit Z80 instructions.

Playback retains the phase costs 417/413/458/413/417/446/409/446 T, averaging
**427.375 T/sample, delta 0 T** from compact preview mode. Page/bank extras
remain +14/+140 T. Only the final bank tail changes: `JP chain_exit` takes
10 T, followed by DI(4), LD SP(10), LD IY(14), IM 1(8), XOR A(4), OUT(11).
Thus it clears the beeper 61 native T after entering that tail. The previous
tail reached its next output after 103 T without filler: the new stopping
path is 42 T shorter. With 420 filler pairs /48 T padding in the reference,
the old next-output cost is 103+420*52+2*7+48 = 22005 T; the new stop is
21944 T earlier. These endpoints have different purposes (stop/continue).
This is outside
source audio: 33 of the final guard's PDM pulses are omitted. No per-sample
branch or new table lookup is added. Disk-controller/ROM time and ULA
contention are measured separately in Fuse, not added to these native costs.

The preceding looping compact TRD still reproduces byte for byte with SHA
`284deb33a5822d5df65f73a8c284f53a66d785104fab5492161e0db62f8350f0`.

## Verification and limitations

`test_ima3_series.py` checks default CLI mode, exact disk boundaries, source
coverage, the short tail and capacity. `verify_ima3_series.py` executes every
part natively with memory guards, then every complete final volume in cold
Fuse Spectrum 128 + Beta Disk. It checks every bit, predictor/index sample,
the loading UI and absence of disk reads during PDM. Later disks are also
executed from the predecessor's captured RAM; unrelated audio banks are
poisoned. The swap test resumes after the key press, so it proves loader
continuation, not a physical drive swap or keyboard interaction.

Different disk reads can change HALT/ROM-interrupt entry alignment by a few
T-states. Relative pulse times must remain within eight T of the independently
qualified part, and the actual final-disk waveform is measured again with
the existing fixed 8-kHz source and 70-Hz..4.5-kHz comparison filter. No fitted
gain, delay or time stretch is used. The final guard interval is omitted;
source-bearing intervals remain. This score is reported separately from
the two-loop candidate score. Below-target output remains a preview and
returns exit code 2. Speed must remain within 2%; cold preparation and
between-part loading must remain under 60 seconds in the tested emulator.

The archived [series experiment](experiments/ima-3bit-series/README.md) records
the exact input scopes, timings and full-run evidence. These are Fuse
measurements, not physical-hardware certification or a universal SNR promise.
