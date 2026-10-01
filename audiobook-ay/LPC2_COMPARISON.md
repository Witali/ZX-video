# LPC2 reuse: bounded speech comparison

On 2026-10-01 the user found the movie-style AY preview completely
unintelligible and suggested the existing `C:/Work/LPC-sound-codec` project.
This comparison uses its **LPC2 Improved** implementation from `index.html`
(repository HEAD `360af14`, source SHA-256 in the saved report). The source
project is read-only and unchanged. This is a completed 24-second diagnostic,
not a replacement two-minute release or a native Z80 LPC decoder.

**Later listener feedback (2026-10-01):** the user accepted the full LPC2
reference as sufficiently clear, then requested more faithful sound and a
check on YM2149 with 50 Hz interrupt updates and typical Spectrum mixing.
See the [new chip-constrained preview](YM2149_PREVIEW.md). The historical
measurements and pending-listener statements below describe this experiment
at its original completion; the AY formant sample was not accepted.

## Listen to the same passage

Source interval: **60..84 seconds** of the same audiobook. All four files
are mono at 22050 Hz and share the same RMS for comparison.

- [Original](lpc-probe/original-preview.wav).
- [Rejected movie-style AY](lpc-probe/old-ay-preview.wav).
- [Existing LPC2 decoder reference](lpc-probe/lpc2-reference-preview.wav).
- [LPC2 formants mapped to AY](lpc-probe/lpc2-ay-preview.wav).
- [AY experiment TRD](lpc-probe/audiobook-preview.trd), independently bootable
  in Spectrum 128 + Beta Disk mode. It plays the fourth sample's register
  sequence, not the full LPC2 decoder reference.

## What was reused

The [headless bridge](lpc2_bridge.js) extracts the existing codec's DSP
functions without its browser UI or any DSP changes: LPC analysis, LSF
quantization, pitch tracking, excitation classification, bitstream pack/unpack,
synthesis, postfilter and output processing. The settings match its documented
profile: 8 kHz, 20 ms frames, 32 ms window, LPC order 10, pre-emphasis .85,
voicing .38, coefficient repeat .05, pitch smoothing .65, postfilter .35,
4 dB brightness and 70 Hz DC-block. Input is normalized to -1 dBFS with an
18 dB maximum boost. The exact extracted core is archived as gzip.

The resulting 1200-frame LPC2 stream is **4114 bytes**, including the header
(1371.33 bit/s over this particular interval). Pack/unpack/repack is bit-exact.
Decoded excitation modes are 793 voiced, 103 mixed, 193 noise (including
174 silent frames), and 111 transient frames. These are codec classifications,
not a manually verified phonetic transcription.

The one AY candidate selects three resonances from the decoded LPC2 envelope,
uses continuous frequencies rather than musical-note bins, and derives their
levels from spectral-band energy and the source RMS. Nonvoiced consonants use
noise on B with A/C muted. AY still cannot reproduce the LPC filter's shaped
noise, excitation waveform or complete spectral envelope. This mapping is an
experiment; it must not be confused with executing LPC synthesis on the chip.

The [probe script](probe_lpc2.py) reuses the existing 50 Hz resident player
unchanged. Native hot-path delta is **0 T**. Full native and cold Fuse checks
cover all 1200 ticks and 13200 actual AY writes through EOF; no missing or
duplicate fields and no runtime disk reads. See [verification](lpc-probe/verification.json).
The disk occupies 96 sectors. No physical hardware was tested.

## Result and decision

| Signal | Spectral cosine | Loudness correlation | Onset F1 |
|---|---:|---:|---:|
| Previous AY | 0.8474 | 0.9812 | 0.7654 |
| LPC2 reference | 0.8742 | 0.8091 | 0.8406 |
| LPC2-to-AY candidate | 0.5880 | 0.7819 | 0.6563 |

These metrics already failed to predict the user's intelligibility judgment
of the first preview. They are not acceptance criteria for speech. The AY
candidate worsens all listed proxies and is **not selected as an improvement**.
No claim is made that either new sample has been judged intelligible by a
listener. The original two-minute disk remains historical, rejected for speech.

The useful foundation is the LPC2 speech model and compact stream. Its actual
decoder generates digital samples through a ten-order synthesis filter and
optional postfilter. AY's three tone generators and shared noise generator
do not implement that filter. A complete LPC path would need a Z80 decoder
and rapid AY volume output. At 8 kHz, 3.5469 MHz gives only about **443 T per
sample** for decoding, output and service work combined. Feasibility is not
established by the Arduino implementation; no native throughput claim is made.
Another possible implementation would predecode on the host, increasing stored
data. Both are distinct from this formant-mapping experiment.

Three-tone speech is a real research direction, but results for sinusoidal
speech do not establish intelligibility for these square-wave/noise AY states:
[Remez et al., 1981](https://pubmed.ncbi.nlm.nih.gov/7233191/).

## Reproduction

```powershell
python audiobook-ay/probe_lpc2.py "C:/Audio/book.m4a" --lpc-source "C:/Work/LPC-sound-codec/index.html" --node "C:/Tools/node.exe" --ffmpeg "C:/Tools/ffmpeg.exe" --output "build/lpc-probe" --start 60 --duration 24
python audiobook-ay/verify_preview.py "build/lpc-probe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python -m unittest discover -s audiobook-ay -p "test_*.py"
```

The input must match the saved audiobook hash, and the requested interval must
remain within its original 120-second preview. Reports preserve hashes of the
source codec, extracted core, source PCM and all comparison files. The next
useful step is listener assessment of the LPC2 reference, then a bounded Z80
sample-decoder cost test if that reference meets the user's quality target.
