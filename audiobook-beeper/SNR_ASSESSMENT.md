# Beeper SNR assessment — 2026-10-02

For the current 8-kHz IMA audiobook, the next defensible engineering target
is approximately **14–16 dB total reconstruction SNR**, compared with the
current **11.5 dB**. Ideal output of the existing decoded IMA waveform would
give about **23.6 dB** with the same listening filter. Neither figure is a
universal maximum for Spectrum hardware. This assessment changes no player
or disk and does not measure an analog machine.

## Reference and measurement

The complete 28.864-second prepared excerpt contains 230912 unsigned PCM8
samples and 115456 IMA bytes. Source PCM, compressed bytes and saved Fuse
timestamps are authenticated by SHA256. The source is the conditioned PCM8
before IMA encoding, not a noise-free studio recording. Tape hiss already
present in that reference is not counted as a playback error.

The [script](assess_snr.py) reconstructs exact pulse areas at 192 kHz.
Signal and error receive the same 70-Hz high-pass and two second-order
4.5-kHz low-pass filters used in the previous PDM/PWM comparison. The first
and last 0.1 seconds are excluded. There is no fitted gain or phase correction.
Each reference uses its row's sample timing and the same three-slot output
latency; tempo error against a fixed 8-kHz clock is therefore excluded.

Here SNR means `10*log10(mean(reference²)/mean((output-reference)²))`:
**reconstruction error includes distortion**, not just random noise. The
modulator column uses decoded PCM8 as its reference; total SNR uses the
prepared PCM8 before IMA. These are different quantities.

The report also integrates Welch spectra over 70–3800 Hz. This explicitly
selected measurement band gives higher numbers; it does not imply that a
real speaker has a brick-wall filter. The main table retains the established
listening filter for comparability.

## Complete-excerpt results

| Output | Modulator SNR, dB | Total SNR, dB | Evidence |
|---|---:|---:|---|
| Current PDM, 48.287 kHz | 11.78 | 11.52 | Saved full Fuse schedule |
| Identical bits and duration, perfectly uniform output | 11.84 | 11.57 | Host model |
| First-order PDM, 48 kHz | 11.75 | 11.48 | Ideal timing model |
| First-order PDM, 64 kHz | 14.85 | 14.32 | Ideal timing model |
| Damped feedback, 64 kHz | 17.58 | 16.57 | Algorithm model; Z80 cost unresolved |
| Second-order feedback, 64 kHz, half amplitude | 10.79 | 10.57 | Algorithm model |
| First-order PDM, 72 kHz | 16.07 | 15.36 | Ideal timing model |
| First-order PDM, 96 kHz | 19.07 | 17.76 | No complete playback kernel |
| First-order PDM, 128 kHz | 21.93 | 19.68 | No complete playback kernel |
| Second-order feedback, 128 kHz, half amplitude | 25.75 | 21.52 | No complete playback kernel |
| PCM8 without IMA, second-order 128 kHz, half amplitude | 25.81 | 25.81 | Changed format; no complete playback kernel |

Perfectly uniform timing adds only **0.055 dB** to the current modulator
score. This comparison keeps the existing per-sample pulse counts, including
page/bank work. It does not establish that every form of clock jitter is
inaudible; it shows that removing the remaining output-interval variation
alone is not a large average-SNR opportunity in this fragment.

The damped feedback model uses
`u = x + (1+beta)*e_previous - beta*e_older`, followed by a one-bit quantizer.
At `beta=0.5` this still has only one noise-transfer zero at DC; it must not
be described as a true second-order noise shaper. `beta=1` is second order
and was tested at half signal amplitude for headroom. Its poor 64-kHz
listening-filter result is retained: higher order does not automatically
improve the output at a low oversampling ratio.

The independent IMA decode reproduces the earlier raw PCM16 result:
**22.4117 dB**. After conversion to PCM8 and the common filter, the perfect
decoded-waveform reference is approximately **23.6 dB**. This is the
asymptotic reference for faithfully reproducing this fixed encoded stream,
not a limit on another codec or a proof that errors can never cancel.

In the 70–3800-Hz measurement band, total SNR is **12.31 dB** currently,
**15.04 dB** at ideal first-order 64 kHz and **17.73 dB** for damped 64-kHz
feedback. The no-IMA second-order 128-kHz model reaches **29.95 dB** in that
band, versus **25.81 dB** through the wider listening filter. Quoting “30 dB
on the Spectrum” from this host model would be unjustified.

## Z80 feasibility and the meaning of a maximum

Use the project's 128K clock, **3546900 Hz**. At 8 kHz there are
**443.3625 T-states per sample** for modulation, decoding, paging and ULA
waits. The existing [native probes](ima-rate-probe.json) establish:

| Ordinary kernel | Mean T/sample | Remaining before ULA/paging |
|---|---:|---:|
| Current six-slot PDM | 438 | 5.3625 |
| Guarded eight-slot probe | 400 | 43.3625 |
| Guarded nine-slot probe | 432 | 11.3625 |
| Guarded ten-slot probe | 464 | -20.6375 |

The optimized pulse core is 32 T: `ADD A,D` 4, `RR E` 8, `RES 3,E` 8 and
`OUT (C),E` 12, versus 40 T with accumulator swaps. Instruction timings
follow the [Zilog manual](https://www.zilog.com/docs/z80/um0080.pdf).
Its isolated throughput is not the throughput of a complete player.

The eight-slot path makes 64 kHz the next practical integration target.
Nine slots target 72 kHz with little margin. Ten slots cannot sustain 8-kHz
PCM in this kernel even before ULA waits. The probes cover all source samples
in independent blocks, but not seamless paging, cold boot or contended
playback. They do not prove uniformly spaced 64/72-kHz output.

More elaborate feedback also needs CPU time. The previous signed 16-bit
damped-feedback [cost probe](rc-pdm-preview/z80-cost.json) took 62 T for the
feedback term alone, before quantization, IMA or output. That implementation
does not fit this budget. It is not a lower bound on every possible table,
precision or register arrangement. The new model uses no RC simulation.

Higher rates or offline noise shaping trade against storage and duration.
For example, packed 128-kHz PDM needs **16 kB/s**, four times the current
IMA rate of 4 kB/s. It would hold only about 7.2 seconds in 115456 bytes,
even if the playback kernel and its memory allocation could be retained.
The existing packed-bit player has not established 128-kHz feasibility.
Precomputed code, shorter clips, narrower bandwidth and different hardware
filters can change the answer, so no absolute machine-wide maximum follows
from the present player.

For scale, ideal 8-bit uniform quantization gives approximately **49.93 dB
for a full-scale sine**. At this speech excerpt's RMS level, the white
quantization-noise estimate is only **38.81 dB**, before IMA, modulation or
analog hardware. The assumptions are explained in
[Analog Devices MT-001](https://www.analog.com/media/en/training-seminars/tutorials/MT-001.pdf).
Oversampling and noise shaping allow a one-bit output to exceed the SNR of
a one-bit quantizer operating at the audio sample rate; their benefit depends
on bandwidth and stability, as described in
[MT-022](https://www.analog.com/media/en/training-seminars/tutorials/MT-022.pdf).
Neither tutorial supplies a measured Spectrum SNR.

## Verification, reproduction and decision

The full actual-schedule result reproduces the previous **11.783161 dB**
modulator measurement to within 1e-9 dB. Every generated baseline bit matches
the independent IMA/PDM reference. All eleven comparisons use the complete
excerpt. A separate first-five-second numerical check of the highest-quality
candidate raises integration rate from 192 to 768 kHz: the listening-filter
score changes by **0.092 dB**. This is a numerical sensitivity check, not a
physical hardware test or an error bound for all possible signals.

Run in the existing Python environment with NumPy, pyz80 and z80 available:

```powershell
python audiobook-beeper/assess_snr.py --output audiobook-beeper/experiments/snr-assessment --ffmpeg <path-to-ffmpeg>
```

[Complete report](experiments/snr-assessment/report.json),
[numerical check](experiments/snr-assessment/numerical-check.json) and
[producer snapshot](experiments/snr-assessment/assess_snr.py.gz).

Decision: retain ordinary PDM. Treat approximately **14–16 dB total SNR**
as the next live-player target, with 64 kHz first and 72 kHz conditional on
timing evidence. Approximately **16.6 dB** is a promising feedback-model
result requiring a new cost proof. Reaching the fixed-IMA reference near
23 dB or the no-IMA 26–30-dB model would need a substantially different
implementation. No player implementation was attempted in this assessment.
