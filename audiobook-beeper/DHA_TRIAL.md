# DHA codec investigation

The user requested trying the codec in `C:/Work/z80-tester` on 2026-10-19.
The bounded trial and follow-up quality measurement were completed across
2026-10-19 and 2026-10-20; the limit interruption did not restart encoding.
The codec is DHA: a difference-history predictor with five residual symbols,
block gain and tabled ANS. This investigation runs its existing C library in
the isolated `audio-snr-research` worktree. The original IMA encoders, Python
reference, player and delivered TRD remain unchanged.

## Reproducible direct-codec trial

[`dha_host_probe.py`](experiments/song-snr/dha_host_probe.py) snapshots the
external C library before compiling its CLI and an independent decoder DLL.
[`dha_host_corpus.py`](experiments/song-snr/dha_host_corpus.py) extends the
first-song evidence to all nine complete original sources. CLI decoding and
the separately built DLL agree on every sample. Container CRCs, sample counts
and all raw-fallback samples are independently checked by
[`dha_host_score.py`](experiments/song-snr/dha_host_score.py).

All sources retain their original uniform 8-kHz PCM8 values, mapped exactly
to signed PCM16 by `(PCM8 - 128) * 256`. No source level, bandwidth, delay or
clock is fitted. Quality uses the existing f64 listening filter, 768-kHz
intermediate representation and fixed 100-ms edges. These scores measure an
ideal multilevel DAC after decoding; they exclude one-bit output and do not
establish Spectrum playback quality. Every model, header, frame and fallback
byte is charged. DHAF is the library's host container, distinct from the
tester's packed ROM format.

The unmodified defaults are beam 64, eight gain candidates, two-block lookahead,
rate penalty 82, 4096-sample frames and PCM16 fallback enabled. The model hash
is `70582ffa6ec234742248acd008bda13795f5243a884681f496af87bd6609260f`.
It was fitted to a 15-second 25-kHz excerpt of the same sea-foam song in the
tester. It is therefore not an independently trained general-source model.

| Complete source | IMA bytes | DHA bytes | DHA / raw frames | IMA SNR, dB | DHA SNR, dB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Silence | 8448 | 2892 | 5 / 0 | zero error | zero error |
| Quiet 440 Hz | 8448 | 3406 | 5 / 0 | 30.3591 | 8.6878 |
| Loud 3000 Hz | 8448 | 34536 | 1 / 4 | 19.4699 | zero error |
| Steps | 8448 | 34536 | 1 / 4 | -0.2566 | zero error |
| Quiet 997 Hz | 8448 | 2894 | 5 / 0 | 23.8340 | 0.0015 |
| Multitone | 8448 | 34536 | 1 / 4 | 21.2446 | zero error |
| Speech | 93440 | 223137 | 20 / 26 | 25.5923 | 22.9260 |
| Entertainer | 93440 | 65270 | 41 / 5 | 27.5445 | 15.9995 |
| Sea-foam song | 360192 | 1418393 | 4 / 172 | 22.1492 | 38.0952 |

“Zero error” refers to the scored interval after fixed edges; the complete
frame layout remains in each report. A JSON null SNR must be read with its
error RMS: it can mean exact reconstruction, or zero signal for silence.
The high song score is explained by 172 raw PCM16 fallback frames, not an
efficient predictive representation. Encoding the complete song took
19.5597 seconds. Smaller quiet-tone and music files lose substantial quality.
The default direct-8k configuration is rejected as an IMA replacement.

Evidence: [first song and pinned C sources](experiments/song-snr/evidence/dha-host/report.json),
[remaining corpus](experiments/song-snr/evidence/dha-host-corpus/report.json),
[song quality](experiments/song-snr/evidence/dha-quality-default/sea_foam/report.json).

## Common model control

[`dha_fit_common.py`](experiments/song-snr/dha_fit_common.py) fits one fixed
8-kHz predictor to all speech and Entertainer training samples. The song and
six synthetic signals are holdouts. This training is part of the codec;
the measurement still receives no fitted gain, delay or clock. Four rounded
signed-byte table rows are generated without clipping. The model hash is
`199a17a9967bfbb941099039f32a47192af8933faf37cf015047abb51bfb9a7b`.

[`dha_common_host.c`](experiments/song-snr/dha_common_host.c) changes only the
1024-byte model. It preserves the library defaults and ANS tables. The
original model reproduces the original CLI's first frame byte for byte;
the new model's whole nine-source C decodes match the old decoder DLL.
This is a single common-model control, not per-song model selection.

The entire song still needs 1411268 bytes, with five predictive and 171 raw
frames, and scores 37.9248 dB on the ideal DAC. Encoding takes 10.634 seconds.
This does not fix the direct-8k compression failure. Entertainer falls to
37817 bytes and speech to 211803 bytes, but their scores are 16.3624 and
23.3205 dB versus IMA 27.5445 and 25.5923. Quiet 440/997-Hz tones score
6.5393/0.00057 dB versus IMA 30.3591/23.8340. Silence is exact; loud3000, steps and multitone
are exact in the scored interval through raw fallback. Thus the common model
does not establish a general quality/compression improvement either. All nine
quality measurements cover 1195520 source samples; no encoding is repeated
when completing the final audit after the limit interruption.

Evidence: [training protocol](experiments/song-snr/evidence/dha-common-model/report.json),
[all nine C trials](experiments/song-snr/evidence/dha-common-host/report.json),
[whole-song quality](experiments/song-snr/evidence/dha-quality-common/sea_foam/report.json).

## Source-preserving helper lattice

[`dha_bridge2_pilot.c`](experiments/song-snr/dha_bridge2_pilot.c) retains every
original sample at an even coded position and inserts one midpoint helper
between adjacent samples. The helper lattice has twice the physical sample
count. Decoding selects the even positions and plays them at the unchanged
8 kHz. Before lossy coding, this selection restores the entire original
720384-sample source exactly. It neither adds source bandwidth nor changes
the physical quality reference. All helper samples and their headers count
toward storage and decoding work.

The first 16384 physical samples (2.048 seconds) become 32768 coded targets.
With the original model and default rate penalty 82, all eight frames use
DHA, taking 5903 bytes and 21.0323 seconds to encode. This prefix was also
an easy part for direct DHA: its four direct frames use 4889 bytes including
the file header and no fallback. This pilot cannot demonstrate full-song
compression or runtime.

[`dha_bridge2_score.py`](experiments/song-snr/dha_bridge2_score.py) compares
only the original physical positions, using the same original 8-kHz reference
and filter. Pilot ideal-DAC SNR is 22.6552 dB for IMA, 11.8429 dB for direct
default DHA and 16.4125 dB for helper-lattice DHA. Thus the default helper
pilot also fails to match IMA quality. The extrapolated 192-kB song and
15.4-minute encoding time are estimates only and do not justify a full run.

Evidence: [C pilot and exact source mapping](experiments/song-snr/evidence/dha-bridge2-pilot/report.json),
[physical-position quality](experiments/song-snr/evidence/dha-bridge2-quality-pilot/report.json).

### Removing the rate penalty

One causal quality control changes only `rate_penalty` from 82 to 0. The exact
same 32768 targets, original model, ANS tables, beam, gain candidates,
lookahead and frame size remain frozen. No parameter sweep or whole-song
helper encoding is performed. [`dha_quality_host.c`](experiments/song-snr/dha_quality_host.c)
uses the pinned library and records every encoded frame; both the old decoder
DLL and the separately built even-selection DLL verify the complete result.

With the rate penalty removed, the pilot reaches 25.21597 dB on the same
physical 8-kHz ideal-DAC measurement, +2.56078 dB over the 22.65519-dB IMA control.
It now costs 15475 bytes versus 8192 IMA payload bytes for these 16384 physical
samples (1.889 times as large, including all DHA headers and helpers). Eight
predictive frames and no raw fallback remain; encoding plus C decoding takes
28.15865 seconds. Even subtracting the 1572-byte file header, this pilot is
larger than IMA. The improved quality is therefore not stronger compression.
The default configuration compresses this prefix more, but loses quality;
this configuration improves quality, but expands storage. Neither establishes
an IMA replacement or justifies extrapolating a good full-song result.

Evidence: [rate-zero C trial](experiments/song-snr/evidence/dha-bridge2-quality0-pilot/report.json),
[unchanged physical-reference score](experiments/song-snr/evidence/dha-bridge2-quality0-score/report.json).

## Precision and player feasibility

The existing C decoder returns eight effective PCM bits shifted into a
16-bit word. Its internal predictor q has 511 levels, but the public output
rounds that result. Relabelling the returned type as PCM16 does not preserve
16 effective bits. [The precision audit](experiments/song-snr/evidence/dha-precision/report.json)
checks all q values and the C model/ANS identities.

The test board's actual current player needs 800 T per sample at 20 MHz:
399 T for parsing and 401 T for prediction, R2R output and return. Pentagon
8-kHz playback has only 448 T at 3.584 MHz, including one-bit modulation.
The board implementation is not a drop-in Spectrum decoder. The
[architecture audit](experiments/song-snr/evidence/dha-architecture/report.json)
independently decodes its entire 375000-sample wire stream, authenticates
the retained native certificate and separates the host and ROM formats.
Its published 25.2833-dB R2R result covers a different 15-second 25-kHz
excerpt; it is not the whole-song beeper measurement. The original prepared
reference is absent from the tester checkout, so that scalar is rechecked
from retained sums rather than freshly recomputed from source PCM.

One possible Spectrum route is decoding during loading and playing resident
PCM8. The song then requires 720384 audio bytes, which fits a 1024-KiB
machine in principle, before a complete memory map is proved. It cannot be
fully resident in 512 KiB. A separate 90-byte native first-order output
component uses eight equally spaced 56-T pulses per 448-T sample. All
65536 input/phase pairs and a 16383-sample trajectory pass, totaling 655368
native outputs. It preserves the documented registers and writes no RAM.
Compared with the current 449-T ordinary packet its period changes by -1 T;
compared with the optional 448-T control the period is equal but pulse
positions differ. This component covers one source bank only. Bank handoff,
EOF, other clone clocks, complete quality and a bootable TRD remain unproved.
[Counted native output evidence](experiments/song-snr/evidence/dha-pcm8/report.json).

No DHA disk or replacement player is accepted by these codec/component trials.
Complete-source quality, generality, modulation/background, RAM transport and
actual full playback gates remain open.

## Final audit

The [independent evidence audit](experiments/song-snr/evidence/dha-audit/report.json)
passes 86 checks with no failures: 29 manifests, 667 immutable artifacts,
29 current/archived producer pairs and 15 pinned external source/config/test
files. All 18 complete default/common containers are independently decoded
again without reencoding; CRCs, source values, counts, fallback samples and
saved unfiltered metrics agree. Filtered measurements are authenticated from
their immutable artifacts, rather than rerendered. Both helper pilots and
their scores pass the mapping and decoder checks.

The [portable common-quality audit](experiments/song-snr/evidence/dha-quality-common-audit/report.json)
retains 39 further audit artifacts, the nine quality manifests and historical
terminal records. Eight new quality jobs exited zero in a combined 18.686
seconds; the existing song measurement was unchanged. Its stdlib verifier
works without the temporary job directory. No historical timestamp is
invented where the execution logs did not record one.

Original tracked code remains identical to both `f009fb18` and `9879e8a9`;
the delivered 655360-byte disk retains SHA256
`b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e`.
