# Square-aware AY conversion

2026-10-01. Baseline: `c4a28ec`, branch `codex/cb41-10fps`.

## Integrated behavior

`convert_video.py` now uses the following automatically for every source with
audio, for both FAP3 and CB41. AY updates remain at 50 Hz independently of
video cadence. The shared `ay_fidelity.analyse()` entry point also uses the
new fitter, retaining its caller-selected update rate and noise option.

1. Keep the existing competing instrument templates and voice tracking to
   identify bass, harmony and melody. Instruments need not be square waves.
2. Recover an isolated tone wrongly classified as a rest by the old semitone
   dictionary: require at least 85% of spectral power within three FFT bins
   of one peak, interpolate its frequency and select an integer AY period.
   This fixes the steady part of an off-grid 450.559 Hz sine fixture without
   enabling noise there or inventing notes from silence/broadband noise in
   the regression fixtures.
3. Search actual 12-bit tone periods within +/-50 cents of each seed by
   default. Two coordinate passes evaluate the three active channels jointly,
   using odd harmonics with amplitudes 1/h, through harmonic 31 and below
   0.48 of the sample rate. These are the same harmonics as the existing
   preview renderer. Frequency is AY_CLOCK/(16*period), including rounding.
4. Choose nearby discrete volume registers jointly with frequency. Preserve
   the fast tone-power envelope within 0.25 dB of its seed and limit each
   tone-volume change to one register step. A 0.001 cosine improvement gate
   and preference for the preceding period avoid negligible adjustments.
5. Keep the existing noise decisions and R6 colour, lowering active noise B
   by one nominal 3.0103 dB volume step. Preserve the independent bass and
   melody, existing noise attack times, rests and unused register holds.

The manufacturer describes three square-wave tone generators and the
clock/16/period relationship in the [General Instrument data sheet](https://map.grauw.nl/resources/sound/generalinstrument_ay-3-8910.pdf).
Odd 1/h partials are the Fourier model of a 50% duty square wave. The fitter
adds magnitudes without phase cancellation; the preview preserves tone phase
and shared LFSR noise. Neither is a cycle-exact model of the analogue board,
AY counter writes or chip-specific volume curves. A three-voice AY cannot
faithfully reproduce arbitrary speech, instruments and effects simultaneously.
This is a local search around tracked pitches, not a global optimality claim.

### Options and reports

- Default command: `python toolkit/convert_video.py input.mp4 --output build/new`.
- `--ay-noise-steps 0`: preserve the old noise level; default is 1.
- `--ay-tuning-cents 0`: keep seed periods; default 50, supported range 0..100.
  One cent is 1/100 of a semitone. These switches do not change AY update rate.
- `audio-quality.json` records the model, settings, recovered/tuned tick
  counts and independent signal proxies. `work/audio-preview.wav` contains
  the synthesized output; `work/ay.bin` contains the actual nine-byte states.
- `arrange_for_chip(..., square_fit=False)` retains the former method for
  controlled baseline comparisons. It is not the generic converter default.

## Evidence and decisions

Three eight-second windows from Big Buck Bunny at source 60, 170 and 430 s,
each with one second of analysis context on both sides. The mono downmix is
the generic converter's mix, not the historical front-L/R-only soundtrack.
Source and artifact hashes: [index](ay_square_fit_evidence/index.json).
Each window has 400 evaluated AY updates. Independent measurements use an
8192-sample FFT (fitter: 4096), semitone/chroma energy and RMS; onset tolerance
is one 20 ms AY tick. Scores are engineering proxies, not perceived accuracy.

| Source window | Spectral cosine before / after | Chroma before / after | Loudness correlation before / after | Onset F1 before / after |
|---|---:|---:|---:|---:|
| 60..68 s | 0.8950 / 0.9084 | 0.9675 / 0.9749 | 0.9832 / 0.9825 | 0.6875 / 0.7429 |
| 170..178 s | 0.8676 / 0.8780 | 0.9705 / 0.9761 | 0.9941 / 0.9946 | 0.9630 / 1.0000 |
| 430..438 s | 0.8559 / 0.8634 | 0.9689 / 0.9731 | 0.9819 / 0.9774 | 0.7778 / 0.8571 |

The selected fit improves spectral/chroma/onset proxies in all three windows.
Loudness correlation falls slightly in two. Noise remains active on 307/1200
ticks; its summed nominal squared level falls exactly 50% (amplitude -29.3%).
The saved ablations separate quieter noise from square-aware fitting: removing
noise alone worsens the effects-heavy 430 s spectrum. Fine period selection
more than recovers that loss in this sample. Whole-movie quality is unverified.

- **Rejected unconstrained volume fit:** fixed-gain spectral least squares
  reduced its own error but used a long FFT to control short attacks.
  Loudness correlations fell to 0.9022 / 0.8265 / 0.8917. Do not adopt it.
  [Saved measurements](ay_square_fit_evidence/rejected-unconstrained.json).
- **Superseded fixed-pitch envelope guard:** fixed dynamics, but combined
  noise reduction still lowered the 430 s spectral cosine to 0.8497.
  [Saved measurements and ablations](ay_square_fit_evidence/superseded-fixed-pitches.json).
- **Selected integer-period search:** requested by the user's follow-up;
  metrics above. A complete-converter sine test then exposed 22 falsely silent
  off-grid ticks, fixed by the isolated-tone recovery. The movie-window output
  states remain identical after that fix. [Final comparison](ay_square_fit_evidence/comparison.json).

Listen to equal-RMS excerpts: [source](ay_square_fit_evidence/60s/original.wav),
[before](ay_square_fit_evidence/60s/before.wav),
[after](ay_square_fit_evidence/60s/after.wav). Other previews are gzip-compressed;
their uncompressed hashes are in `comparison.json`. Analysis PCM, periods,
volumes and all four AY variants are also archived.

## Storage and CPU cost

The nine-byte record, native instructions and memory layout are unchanged
(instruction substitution delta **0 T**). More accurate changing frequencies
produce more register writes and Huffman symbols, so runtime cost increases:

| Window | AYH1 bytes before / after | Producer + consumer T-states before / after | Delta |
|---|---:|---:|---:|
| 60 s | 919 / 1679 | 1,066,601 / 1,361,302 | +294,701 |
| 170 s | 933 / 1570 | 1,037,348 / 1,305,837 | +268,489 |
| 430 s | 1072 / 1891 | 1,193,719 / 1,534,816 | +341,097 |
| Total | 2924 / 5140 (+75.79%) | 3,297,668 / 4,201,955 (+27.42%) | +904,287 |

These are isolated eight-second streams with separate headers, not a projected
full-movie disk count. The added CPU is about 1.06% of the 24 s / 3.5454 MHz
budget. The checked Z80 harness replays all **2400 old/new ticks**, verifies
register values and guarded memory, and checks producer instruction timings
against the instruction table. It uses paging wrappers and batches of 31.
The consumer is 367+83*writes T for nonempty ticks, 377 T for empty ticks,
plus 24 T on EOF; maximum measured consumer tick remains 1280 T.

The first profiling attempt correctly failed its inherited full-batch formula
on a partial final batch. The added EOF iteration costs 41 T:
JR NZ taken instead of not taken +5, LD HL,(remaining) 16, LD A,H 4,
OR L 4, JR Z taken 12. The corrected formula matches every measured stream.
[Native report](ay_square_fit_evidence/native.json).

Excludes the IRQ wrapper, ULA contention, TR-DOS ROM execution and physical
disk latency; the harness drains the queue explicitly. It does not prove
sustained full-player timing. Existing converter memory/capacity checks and
Fuse release gates remain required. No root TRD or prepared movie soundtrack
has been replaced; cached/prebuilt AY is not automatically reconverted.

## Verification and reproduction

27 tests pass across `test_ay_square_fit`, `test_ay_fidelity`, `test_ay_noise`
and `test_video_cadence`: square spectrum, detuned single tones and chords,
off-grid sine recovery, absence of noise/rest false positives in fixtures,
power bounds, serialization, converter integration, tail silence, IRQ/register
contracts and unchanged 50 Hz cadence.

A real CLI conversion of a generated 0.6 s / 450.559 Hz sine video produced
one temporary TRD: five video frames and 30 AY updates, complete CPU replay,
exact audio and screens. This is an integration smoke check with ideal data,
not a disk-timing or full-film release. [Converter evidence](ay_square_fit_evidence/converter/conversion.json).

Set `PYTHONPATH` to include `toolkit` and installed project packages. Set
`OPENBLAS_NUM_THREADS=1` for a repeatable bounded probe. Tool paths below are
the reused local binaries; the converter itself has no machine-specific paths.

```powershell
python -m unittest test_ay_square_fit test_ay_fidelity test_ay_noise test_video_cadence
python toolkit/probe_ay_square_fit.py --input MOVIE --ffmpeg FFMPEG --output .tmp/ay-square-fit-final
python toolkit/profile_ay_square_fit.py --probe .tmp/ay-square-fit-final --output .tmp/ay-square-fit-final/native.json
ffmpeg -v error -nostdin -f lavfi -i 'color=c=black:s=256x144:r=25:d=0.6' -f lavfi -i 'sine=frequency=450.559:sample_rate=22050:duration=0.6' -shortest -c:v mpeg4 -c:a pcm_s16le .tmp/source.avi
python toolkit/convert_video.py .tmp/source.avi --output .tmp/ay-cli-check --verify cpu
```

`archive_ay_square_fit.py` stores hashed evidence and checks artifact identities.
The original rejected reports are retained as measurements; the final scripts
implement the selected fitter. Next release gate: rebuild selected audio for
the intended movie timeline, check resident-bank capacity and actual disk
delivery, then verify full EOF playback and listen to difficult scenes.
