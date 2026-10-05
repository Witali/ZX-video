# IMA4 audio to TRD converter

The [2026-10-05 overlap follow-up](experiments/ima4-overlap/README.md) completes
the paused speech refinement and compares an otherwise identical search
without overlap. The earlier verified overlap result remains best at
22.174535 dB in a separate stable float64 audit. The refinement's22.55-dB
host estimate fails on its changed real clock; the converter must keep its
measured fallback. IMA3 remains the duration/default option; IMA4 keeps the
automatic overlapping waveform search for quality. No Z80 cost is added.

Updated 2026-10-04: the default `--quality best` adds the shared PDM waveform
search with overlapping windows to the unchanged four-bit player. It keeps
the old verified candidates, recalibrates the two best host candidates on
their own clocks and selects the best complete two-loop result. A final
clock-refinement pass re-encodes the winner against
its measured data-dependent waits; `--no-refine-clock` omits that pass.
The prior verified result remains eligible if refinement is worse. Use
`--quality balanced` to reproduce the earlier PCM-search workflow described
below. See [current search controls](CONVERTER.md). This change adds no
Z80 instruction: ordinary cost remains 423 T/sample, delta 0 T.

`convert_audio.py --codec ima4` accepts an ordinary local audio file readable by FFmpeg,
keeps its initial fragment that fits the resident player and generates one
independently bootable TRD. This historical architecture uses live
4-bit IMA ADPCM decoding and direct PDM output. The
[denser predictive codec](DENSE_CODECS.md) is a measured candidate, not yet
an integrated player option.

## Run

Install/use the project's Python environment with NumPy, pyz80 and the native
`z80` package. FFmpeg and Fuse with Spectrum 128/Beta Disk are required for
the complete verification pipeline. Supply executable paths when they are
not on PATH. On this checkout, the existing packages can be selected with:

```powershell
$env:PYTHONPATH='C:/Work/ZX-video/local_tools/python_packages;C:/Work/ZX-video/.tmp/lzma-z80-packages;C:/Work/ZX-video/audiobook-beeper'
$env:OPENBLAS_NUM_THREADS='1'
python audiobook-beeper/convert_audio.py "C:/Audio/recording.m4a" --codec ima4 --output build/my-audio --ffmpeg "C:/Tools/ffmpeg.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

Use `--duration 5` for an initial five-second excerpt. An existing nonempty
output folder is rejected rather than overwritten. By default the final
verification also plays/captures two loops through Fuse at normal speed;
`--no-recording` omits that audible capture, retaining full native/cold-Fuse
checks and an integrated-port WAV. The WAV report distinguishes these paths.

`--prepared-pcm` preserves an already normalized mono PCM8/8-kHz WAV without
applying a second gain, fades or padding. It must contain 8192..186880 samples
in multiples of 512 and end with 128 silent samples (unsigned value 128).
It cannot be combined with `--duration`. This permits an identical prepared
reference for IMA3 and IMA4 comparisons.

The useful outputs are:

- `audiobook-preview.trd`: bootable looping disk for Spectrum 128 + Beta Disk.
- `result-preview.wav`: actual Fuse capture, or the documented port-rendered
  fallback when `--no-recording` was selected.
- `source-preview.wav`: prepared mono 8-kHz PCM8 quality reference.
- `clock-aware-output-preview.wav`: measured port events through the fixed
  comparison filter; not a recording of a physical speaker.
- `report.json`: selected quality, speed, retained duration, truncation,
  hardware limitations and verification coverage.
- `input.json`, calibration directories and `producer-source`: reproducible
  source preparation, rejected candidates and source snapshots.

## Preparation and quality policy

Only a bounded prefix is decoded on the PC. One extra output sample detects
truncation. The current payload limit is 93440 bytes / 186880 prepared samples;
128 samples are reserved for silence, leaving **23.344 seconds** of input.
RAM is the limiting resource even though the TRD has free sectors. There are
no disk reads during playback and no full PCM/PDM expansion in Spectrum RAM.

FFmpeg downmixes to mono and resamples to 8 kHz. A fixed peak normalization
sets the maximum to 109/128 of full scale, preserves relative dynamics, and
applies at most 10-ms fades at the boundaries. Silence stays silence. PCM is
rounded to unsigned 8-bit, padded to a 256-byte IMA-sector boundary, and encoded
using the existing beam-32 encoder. SNR compares against this prepared signal,
not the full-band stereo input; AAC's `bits_per_sample=0` means unspecified
PCM bit depth, not zero-bit audio.

A clip shorter than about one second repeats internally until its prepared
loop is at least 8192 samples. This bounds the fractional cost of rounding
the overall loop to an integer video-field count; repetition and padding are
explicit in `input.json`. Playback of the completed disk is always cyclic.

For each encoded stream, a bounded 24-candidate phase search measures cold
Fuse loops. Only a <=3-T cold transient followed by an exact field-aligned
second loop is accepted. Full native and cold-Fuse checks then verify every
bit, predictor/index, bank transition and loading indicator for two loops.
The PC compensates the original sample clock from that measured schedule,
re-encodes, **recalibrates the changed stream**, and validates again.
The uncompensated pilot is retained as an identity-transform candidate.
Up to two compensation passes are considered, with early exit when both
loops measure at least 20 dB and mean speed is within the requested +/-2%.
Otherwise the better speed-compliant verified candidate is retained and
the unmet 20-dB goal remains explicit. Silence has `null` SNR, not Infinity.

The reference clock is explicitly 8000 Hz; there is no fitted delay, gain or
pitch correction in the measurement. The phase filler only extends the
already silent tail. The physical sample intervals still vary with ULA
contention; offline compensation addresses the resulting voice timing.
This is a bounded search within the best currently verified player design,
not proof of a universal codec optimum. New arbitrary inputs can expose
calibration limits; failures retain diagnostics and are not qualified as
successful conversions. No physical Spectrum measurement is claimed.

## Player timing and variable length

The generic loader supports 256..93440 IMA bytes in 256-byte steps, using
only the required banks in order 0,4,6,1,3,7,2. The final partial bank is
right-aligned so that the existing cursor overflow remains authoritative.
Empty bank loads are omitted. Each bank tail receives its actual successor;
the phase filler follows the actual final section, not a fixed bank number.

Instruction timings are unchanged: **423 T per ordinary sample, +14 T at
ordinary pages, +140 T at bank transitions**. Delta from the old player is
zero for each executed path. Optional silence costs 52 T per output pair,
7 T per group, plus the recorded pad. Native cycle totals, ULA wait totals
and preload ROM/disk time are recorded separately. All 128 KiB are accounted
for, including unused audio capacity for shorter inputs, screens, tables,
code, stack and TR-DOS workspace.

`verify_direct_lengths.py` confirms byte-identical regeneration of both
previous full-capacity disks, and complete native/cold-Fuse playback at the
256-byte minimum and a 16640-byte two-bank partial tail. The converter is
also exercised on a short M4A prefix, a 37-ms silent stereo WAV, and the full
resident prefix of the user-supplied audiobook. These are distinct coverage
checks, not a claim that every possible input has been tested.

## Saved audiobook example

The [disk](experiments/audio-converter/audiobook-preview.trd) retains the
first 23.344 seconds of the supplied M4A, with all 93440 IMA bytes used.
The selected second compensation pass measures 15.80350/15.80023 dB on the
two complete loops, and mean prepared-sample speed differs by -0.04327%.
The source differs from the earlier 18.99410-dB experiment, so this is not
a same-input quality comparison. The 20-dB goal remains open.
[Full report](experiments/audio-converter/report.json) and
[Fuse WAV](experiments/audio-converter/result-preview.wav).
