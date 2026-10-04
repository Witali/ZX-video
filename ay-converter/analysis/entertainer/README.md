# Entertainer: accuracy review and bounded AY experiments

Measured 2026-10-04 against standalone converter commit `e604de3`. This is an
analysis and proposal, not a replacement release. The production converter,
player and TRDs are unchanged. Reuse their complete native/Fuse qualification.
All candidate comparisons below are host-rendered through the existing Ayumi
YM2149 core, with the same source, 50-Hz rate and register format.

## Input and baseline

Use the first 31.128 seconds requested from the existing The Entertainer
recording, rounded down to 31.12 seconds /1556 records. The performer is IE,
using a Casio WK-3300 electronic keyboard, not an acoustic recording assumed
from the composition's title. The unchanged input and rights are recorded in
[source.json](../../../audiobook-beeper/experiments/ima-3bit-entertainer/source.json).
Input SHA-256 is
`08dc5241de419edf9693ad20797389cb735d9b6fc06bfb6936568bb707f13077`.
The probe includes the same following analysis context as the converter.

The original baseline is reproduced exactly: all register bytes and all four
legacy metrics match the archived music report. That report measured complete
native/Fuse playback without missed fields. Decoder throughput is therefore
not evidence for the audible synthesis errors examined here.

## Findings from code and this recording

1. The analyser models three generic harmonic spectral slopes per semitone.
   Bass, melody and harmony are then selected in sequence with Viterbi paths.
   It has no explicit note-onset, repeated-key, note-off or piano-decay model.
   Selecting bass first and removing nearby notes is a heuristic, not a joint
   optimization of musical importance or a transcription of the performance.
2. Pitch analysis uses 4096 samples at 22050 Hz: **185.76 ms** per centred
   window, although new registers arrive every 20 ms. This can mix adjacent
   attacks. The fast 20-ms RMS envelope does not make the frequency analysis
   window shorter. Bass frequency resolution still needs a long window.
3. Fine spectral fitting can move each note by up to 50 cents every tick.
   Within the encoder's own unchanged note labels, the baseline changes the
   period **279 times for bass, 134 for harmony and 197 for melody**. The
   largest bass step is 60.54 cents between adjacent ticks. These counts
   describe the encoder; there is no annotated note ground truth here.
4. Noise replaces harmony on **243/1556 ticks =15.62%**, totaling 4.86 s.
   Broadband energy from keyboard attacks can compete with real harmony.
   The harmony path also has 34 runs shorter than 60 ms among 159 runs.
   These are reasons to inspect note allocation and transient classification,
   not proof that every short run/noise tick is wrong.
5. The fitter uses ideal 3-dB volume steps, but its own renderer uses the
   measured-style YM2149 DAC table. At register levels 2..14 the difference
   reaches **2.57 dB**. Fixing this model mismatch is independent of adding
   more player bandwidth. Target AY and YM curves should be explicit profiles.
6. The quality gate is coarse: `quality.features` uses 8192 samples /371.52 ms
   and the converter calls it at **10 Hz**. Its onset matcher tolerates one
   such frame, i.e. **100 ms**, not 20 ms. Chroma also discards octave identity.
   Consequently 0.9757 chroma similarity is not 97.57% correct notes, and
   0.8871 onset F1 does not prove accurate short attacks.

The analyser/renderer clock mismatch (1773400 vs1773450 Hz) is only 0.049
cents and is not a useful primary explanation of the current sound.

## Six fixed ablations

The [probe](probe.py) performs one shared decomposition and six predetermined
variants, without an open-ended parameter search. [Full results](results.json)
include hashes, settings, counts and individual source identities. The small
register streams are retained in `registers/`; no experimental TRDs are made.

The additional onset proxy uses a 92.88-ms window, 10-ms hop and 20-ms match
tolerance. It detects spectral-flux events in the source and generated audio;
these are **not labelled piano notes**. Different timbres can create extra
peaks. Its absolute F1 must not be compared directly with the old detector's
F1 because both resolution and feature representation changed.

| Variant | Spectral cosine | Chroma cosine | Legacy onset F1 | Finer onset F1, 20 ms |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 0.89279 | 0.97571 | 0.88710 | 0.65891 |
| No noise | 0.88982 | 0.97768 | 0.88696 | 0.67281 |
| No per-tick fine tuning | 0.89249 | 0.97586 | 0.89431 | 0.68293 |
| Median pitch held per note run | 0.89205 | 0.97547 | 0.88710 | 0.70000 |
| YM2149 volume curve | 0.89214 | 0.97570 | 0.91935 | 0.69636 |
| No noise + no fine tuning + YM curve | 0.88766 | 0.97630 | 0.90598 | 0.68807 |

The baseline finer detector finds 92 source and 166 generated events, matching
85. Pitch holding finds 148 generated events and matches 84: its improved F1
comes mainly from fewer extra detections, not recovery of more source attacks.
No-noise finds 125 events and matches only 73, demonstrating its tradeoff.
The calibrated curve slightly reduces loudness correlation (0.99535 ->0.99317).
No variant dominates all metrics, and no subjective preference is asserted.

Pitch holding is promising for this fixed-pitch keyboard recording. Preserve
intentional bends/vibrato in other instruments instead of imposing this rule
globally. Do not adopt the combined switch set solely because its onset score
is higher: it has the largest spectral loss among these six variants.

## Recommended implementation order

1. **Measure notes and attacks explicitly.** Annotate representative fast
   phrases, chord changes, repeated notes and bass jumps from this exact
   performance. Track melody/bass note precision and recall, octave errors,
   attack-time error and durations. Keep the current signal metrics as
   secondary diagnostics. Use equally loud blind comparisons on the complete
   excerpt and the difficult phrases; do not optimize only this recording.
2. **Add a note-oriented music profile on the PC.** Use short 256/512-sample
   windows for attack timing, longer windows for bass/pitch, explicit note
   lifetimes and onset-aware tracking. Fit one stable pitch per keyboard note,
   plus global performance tuning, instead of chasing changing overtones.
   Allocate voices jointly, prioritize melody and bass, and require evidence
   before interrupting sustained harmony. Existing R0..R10 playback can remain.
3. **Model dynamics and the actual chip together.** Select AY/YM level curves,
   fit each note's attack/decay/release rather than the whole mixture's RMS
   alone, and compare rendered output with a multiresolution spectral and
   onset objective. Include penalties for unsupported pitch/voice switching.
   Test the calibrated curve with the new envelope model rather than treating
   the isolated DAC ablation as a proven final improvement.
4. **Separate tonal music and sound-effect noise decisions.** For piano-like
   sources prefer three tones, with noise allowed for short, well-supported
   transients. For actual effects retain noise colour, duration and envelope
   modeling; global noise removal is not an improvement. The current AY9
   format only supports the fixed three-tone /noise-only-B mixer policies.
5. **Consider 100 Hz only after the above.** It can improve event timing and
   volume envelopes, but cannot undo a 186-ms analysis window or recover a
   missed note. The current HALT-based player is tied to 50-Hz interrupts;
   a second timed update per field requires a new scheduler and complete
   native/Fuse deadline checks. Keep 50 Hz as the initial compatible target.

Automatic note transcription is a plausible alternative analysis front end,
not a measured improvement here. [Onsets and Frames](https://magenta.tensorflow.org/onsets-frames)
separates piano onsets from sustained-note detection; [Basic Pitch](https://github.com/spotify/basic-pitch)
supports polyphonic audio-to-MIDI and works best on one instrument at a time.
Test either on this keyboard recording before choosing it. If a symbolic
score/MIDI is used as a reference, align it to this performance's timing;
another rendition is not ground truth for these audio samples.

## Spectrum cost and physical limits

All six probes keep 1556 eleven-byte records. Proposed PC analysis changes
can retain the existing player: ordinary field work **974 ->974 T, delta 0**,
17116 resident register bytes for this excerpt, 550 bytes/s at 50 Hz.

For a prospective faster scheduler, data bandwidth is 1100 bytes/s at 100 Hz
or 2200 at 200 Hz. The current six-bank capacity would fall from 178.68 s to
89.34 or 44.67 s. Repeating only the present 974-T ordinary work gives ideal
foreground CPU estimates 1.37% /2.75% /5.49% at 50/100/200 Hz. These exclude
the changed timer, bank/wrap overhead, IRQ, HALT, ULA, ROM and disk latency;
they are not qualified faster-player timings.

Three tone generators cannot retain every simultaneous note of a piano
arrangement, and square-wave tones cannot reproduce an arbitrary piano
timbre. AY envelope use (R11..R13) and more flexible mixer decisions could
broaden timbres, but require stream/renderer/player changes; the hardware
envelope is shared. Fast arpeggios can suggest additional chord notes while
altering their timing. Neither is the first step toward fidelity here.

## Reproduce

Use the converter's external Python dependencies, FFmpeg and Node.js, with
`OPENBLAS_NUM_THREADS=1`. From the repository root:

```powershell
python ay-converter/analysis/entertainer/probe.py --input audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg --baseline audiobook-ay/music-preview --output build/ay-entertainer-analysis --ffmpeg FFMPEG --node NODE
```

The output directory must be new. The script verifies exact baseline register
and metric reproduction, writes all six full WAVs and registers, and saves
the complete report. The existing production sources and image hashes must
remain unchanged. No candidate has new Fuse/hardware/listening qualification.
