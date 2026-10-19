# PCM16 arithmetic, uniform timing and frozen host controls

2026-10-19. This continuation proves a 176-byte standalone first-order
modulator that consumes the complete reconstructed PCM16 predictor while
retaining compressed IMA in RAM. Seven outputs at uniform 64-T intervals
fit a 448-T source sample on the uncontended Pentagon CPU. It is a counted
ordinary-path mechanism, not an accepted audio disk. Bank handoff, EOF,
loader/boot, UI and all-clone clocks remain unimplemented.

This follows the [full-input table/selector study](SDM16_PRECISION.md).
Existing player and Python/C encoder sources, delivered disk, source gains,
bandwidth and previous experiments remain unchanged. The user subsequently
prioritized investigation of DHA from `C:/Work/z80-tester`; the partial host
study below was stopped and sealed rather than presented as a complete
corpus result. That codec investigation is outside this milestone.

## Counted alternatives before the uniform kernel

The [runtime residual probe](experiments/song-snr/evidence/sdm16-residual/report.json)
implements `q=floor((U+R)/1024)`, `Rnext=(U+R)%1024` with persistent ten-bit
RAM state and an unchanged 16-bit IX predictor. All 67,108,864 input/residual
pairs satisfy the integer recurrence; 63,490 native cases verify boundaries,
flags, register guards and constant 89-T cost. A one-LSB constant input
changes a real quantized bin after 1023 samples. The existing 70-T
lookup/POPs remain necessary: 159 T exceeds their 96-T lookup-plus-padding
budget by 63 T. The exact recurrence can also return level 64, requiring
a new endpoint policy beyond the current 64-bin model. This implementation
is rejected for the current clock; it is not an impossibility bound.

The [pipeline fragments](experiments/song-snr/evidence/sdm16-pipeline/README.md)
pass 11,160 native cases over 124 SECOND patterns, both phases and ordinary,
page and bank paths. Dead main HL/AF, Pentagon B and alternate BC permit
counted scratch uses. The nominal 26-T pacing delta contains only 16 T of
body work, with the remaining ten T in extra jump overhead. Equal-time
sequences can cache IXL or copy the predictor without a new delay.

Caching the compressed byte and using a uniform full-word source advance
changes the measured LOW/HIGH ordinary fragment from 242 to 241 T, regular
page from 256 to 241 T and bank from 485 to 470 T. With the unchanged
remainder these imply ordinary/page packets of 448 T, but bank packets
still cost 677 T: a 229-T extra. Pulse holds change, so unchanged literal
bits do not prove unchanged sound. No descriptor-prefetch sequencer or
constant-time bank handoff was implemented.

## Full PCM16, seven uniformly spaced outputs

For signed decoded predictor `p`, hold `U=p+32768` for seven decisions, with
the same source-independent initial accumulator 32767:

```text
sum = accumulator + U
bit = (sum >= 65536)
accumulator = sum & 65535
```

Each actual pulse executes `ADD HL,DE` 11 + `SBC A,A` 4 + `AND C` 4 +
`OUT (FE),A` 11 = 30 T. Every following gap is exactly 34 T. Thus seven
64-T holds give 448 T per PCM sample: 8 kHz input and 56 kHz output decisions
at 3.584 MHz. The period differs by -1 T from the existing 449-T packet and
by zero from the optional 448-T experiment, while the output schedule and
decision rate change substantially. No quality improvement follows from
retaining more input precision alone.

Uniform holds make the physical-time area identity exact:
`sum(64*(U/65536-bit))=64*(final_accumulator-initial_accumulator)/65536`.
No unweighted recurrence is applied to unequal old holds. A common-seed
native witness with signed inputs 37/38 changes the first output bit.

| Gap after output | Total T | LOW useful/free T | HIGH useful/free T |
| --- | ---: | ---: | ---: |
| 1: fetch and preserve next nibble | 34 | 34 / 0 | 34 / 0 |
| 2: select decoder stack pointer | 34 | 26 / 8 | 26 / 8 |
| 3: POP delta/row | 34 | 28 / 6 | 28 / 6 |
| 4: update next predictor | 34 | 23 / 11 | 23 / 11 |
| 5: source cursor | 34 | 0 / 34 | 14 / 20 |
| 6: unused scheduling space | 34 | 0 / 34 | 0 / 34 |
| 7: latch predictor and loop | 34 | 16 / 18 | 26 / 8 |

Useful work totals 127/151 T, leaving 111/87 T distributed between deadlines.
Main HL is the accumulator, DE the held PCM16 input, C the EAR mask and IX
the next predictor. Main B/IY are free. Alternate HL/DE/BC hold decoder row,
compressed cursor and delta. AF' owns a prepared nibble only from gap 1 to
gap 2. SP becomes dead after both POPs and is reset before subsequent POPs;
interrupts remain disabled and no CALL/PUSH or RAM write occurs.

The [native report](experiments/song-snr/evidence/sdm16-uniform7/report.json)
records 8190 decoded samples, 57,330 source bits, all next predictor/index
states, seven full-range vectors and the one-LSB witness. Every actual
hold is 64 T and every sample costs 448 T. The source crosses ordinary
pages inside one physical 16-KiB bank. The first callback is at 29 T; only
that constant observation origin is removed. No source clock is fitted.
The complete producer run took 8.463501 seconds.

A separately assembled signed-24-bit area-feedback kernel handles the old
`[30 x 10,148]` holds. Its true intermediate requires 25 signed bits, so
ADC overflow disambiguates wrapped sign. All 917,504 native cases pass,
including 17,713 true-25-bit intermediates; every path costs 78 T per pulse.
Eleven inner pulses alone cost 858 T, excluding product formation/loads
and IMA decode. This concrete weighted implementation is rejected for a
448-T packet.

## Interrupted frozen-IMA host comparison

The [C host](experiments/song-snr/sdm16_uniform7_host.c) and
[driver](experiments/song-snr/sdm16_uniform7_host.py) have exact parity with
all 57,330 saved native ordinary-kernel bits and their 64-T intervals,
plus the extreme and one-LSB cases. The full-16-bit recurrence also matches
the independent complete-stream integer reference. The matched `floor6`
control maps `U` to `U & 0xFC00`; it is a host input-precision control, not
the previous player's table modulator or a separately native-proved player.

The interrupted run retains seven source folders and 111 hashed artifacts,
with `complete:false` in its [manifest](experiments/song-snr/evidence/sdm16-uniform7-host/manifest.json)
and [interruption record](experiments/song-snr/evidence/sdm16-uniform7-host/interrupted.json).
It does not complete the nine-source corpus or long controls. Native/C
parity is complete; audio acceptance is not.

The existing 449-clock jointly optimized IMA nibbles were frozen and not
reoptimized for uniform 448-T timing. Both variants use the same source,
seed, 70-Hz high-pass and two 4.5-kHz low-pass stages, 768-kHz integration,
100-ms edge exclusion and no fitted gain/delay/clock. Results below are
unfitted source-relative total SNR and a separate PDM-only diagnostic
against that same frozen decoded IMA16 signal:

| Source | Total floor6/full16 dB | PDM-only floor6/full16 dB |
| --- | ---: | ---: |
| Song, 720,384 samples | -3.003 / -3.002 | 18.013 / 18.142 |
| Silence | undefined / undefined | -67.750 / -30.204 |
| Quiet 440 Hz | -8.249 / -8.221 | -6.395 / -6.327 |
| Loud 3 kHz | -2.805 / -2.808 | 16.914 / 17.180 |
| Steps | -0.808 / -0.777 | 10.030 / 10.301 |
| Quiet 997 Hz | -13.816 / -11.114 | -11.724 / -8.678 |
| Multitone | -3.060 / -3.061 | 16.627 / 16.753 |

The song PDM-only change is +0.128686 dB. Its full16 total is -3.002195 dB;
even the decoded-IMA16 control is -2.968504 dB on this source clock. Those
values disclose the frozen 449-optimized stream's mismatch with the new
uniform transport. They are neither a new attainable ceiling nor evidence
of the requested five-dB release improvement. Silence's source total has
zero signal power, so its SNR is undefined; the decoded-IMA diagnostic must
not be treated as silence quality. Some coherent-error lines rise and
legacy modulation fits are inapplicable, leaving the no-background and
no-AM/FM requirements unproved. The partial host comparison accepts no
sound-quality candidate.

## Reproduction and remaining work

The immutable manifests authenticate 148 retained files across
[uniform7](experiments/song-snr/evidence/sdm16-uniform7/manifest.json),
[residual](experiments/song-snr/evidence/sdm16-residual/manifest.json),
[pipeline](experiments/song-snr/evidence/sdm16-pipeline/manifest.json) and
the interrupted host run. Their hashes and producer identities were checked
without repeating the passed full executions for this documentation commit.
Each evidence folder retains its exact inputs, counts and execution scope.

Standalone reproducers are
[uniform7](experiments/song-snr/sdm16_uniform7.py),
[residual](experiments/song-snr/sdm16_residual_quantizer.py),
[pipeline](experiments/song-snr/sdm16_pipeline.py) and the C host/driver above.
Use a new output directory for another run, preserving the frozen evidence.

The kernel has no physical bank switch, descriptor handoff, EOF or complete
RAM allocation. At Scorpion 3.5 MHz its unchanged 448-T period is 7812.5 Hz;
all-clone compatibility is unproved. A bootable disk, loader/progress UI,
matched encoding, full-source artifact checks, Fuse and physical playback
remain release gates. Work stopped at this bounded milestone for the user's
DHA investigation priority; no new release or goal completion is claimed.
