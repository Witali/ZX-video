# Bounded signed8 difference-history audio screen

This is an offline C encoder and self-contained host replay experiment. It does
not publish firmware. Its three attempts compare the unchanged generic q9
predictor with a compact difference-history predictor, then retrain only the
symbol probability estimate once. The model is fixed throughout both new runs.

The source is the same cached original 56â€“58 s excerpt at native 25000 Hz,
50000 samples, SHA-256 `bedf9fc62fb9dfd7f034bbb01b83b0d99cd50e00241b362afadb499c2afef6a2`.
This phase performs no resampling. The cache was produced directly from the
original MP3 in one FFmpeg conversion with `filter_size=256:cutoff=0.98`, without
normalization, delay fitting, a fade, or intermediate-rate audio. Reference and
original-source provenance are retained in the report.

## Predictor and restrictions

From previous reconstructed samples h0,h1,h2,h3, the PC search computes

```
q1 = h0
d1 = h0-h1
d2 = h0-2*h1+h2
d3 = h0-3*h1+3*h2-h3
p = q1 + T0(q1) + T1(d1) + T2(d2) + T3(d3)
```

Every current and output difference must lie in [-128,127], including the state
after the final sample. Every prediction and reconstruction must lie in
[-256,254]. Residual labels are 0,+G,-G,+2G,-2G, with G1..30 per 256 samples.
Every branch must also stay within 18 physical DAC steps of its reference.
The generic control has no signed8 difference restriction. This narrow profile
is a candidate for suitable music and voice; the generic q9 state remains the
fallback for material that cannot satisfy these bounds.

`probe.py::fit_model` independently decodes the frozen full15s quality-pass
trajectory, reconstructs its four histories, and performs ordinary least
squares on all375000 samples, with no intercept, ridge, gain, or time fitting.
Each row product is rounded nearest-even. Coefficients are approximately
[-0.03965039152806261,0.8990253695520664,0.463045998278022,
0.26278664629475357]. The resulting1024 bytes have SHA-256
`70582ffa6ec234742248acd008bda13795f5243a884681f496af87bd6609260f`.

T0 stores one odd half: byte index `abs(q1)&255`, with index0 representing
virtual +256. q1=0 has an explicit zero correction; negative q1 negates the
stored correction. A T0 byte of -128 is forbidden. The next three256-byte
signed rows use index `d+128`. The exact stored rows, not floating-point
coefficients, control decoding. Model provenance includes full trajectory,
reference and reconstructed-q hashes. Frozen-history innovation79.3252 qÂ² and
five out-of-range predictions are diagnostics; neither is a closed-loop
quality or compression measurement.

## Search and independent validation

The fixed search settings are beam64, shortlist8, lookahead2 and lambda64.
Gain shortlisting and beam search execute in C. The initial search probabilities
are [171,37,36,6,6]/256. The retrained run uses the first result's fitted book.
Search costs are probability approximations: each finished result refits the
entropy book from its own output labels. Reported ANS bits are actual emitted
bits, not the search's approximate prices or a claim of a pinned book.

The C search retains four histories. The scalar file decoder instead retains
(q1,d1,d2,d3) and updates independently:

```
new_d1 = q-q1
new_d2 = new_d1-d1
new_d3 = new_d2-d2
```

Fixtures compare C with an independent full-history Python implementation for
2064 prediction cases and18576 output-boundary cases, including signed8 edges,
zero and q1=-256. There are18 all-G greedy comparisons, six exhaustive tiny
searches,12 format roundtrips,135 malformed/unsafe rejections and two
infeasible-cap cases. A specific path has four legal outputs and an illegal
final d3=150; both packing and decoding reject it. The generic control accepts
15657 output-boundary cases that the narrow profile must reject.

## DHA1 host format

The44-byte little-endian header `<4sBBBB9I>` stores magic DHA1, version1,
order4, precision9, mode, native sample rate, count, model length, payload
length, reconstructed-q CRC, full profile-state-path CRC, full ANS terminal0,
state-profile ID and row-rounding ID. Mode0 stores4096 bytes of signed16
control tables; mode1 stores the1024 bytes above. Both profile and rounding IDs
must match the mode. No external predictor setting is required to replay.

The512-byte ANS book has256 entries `(label<<4|N, base)` and all five labels
must possess a complete, nonoverlapping inverse. Positive result-trained
frequencies normalize to256; N<=8. The payload starts with the full8-bit ANS
state and5-bit G. Control0 wraps;31 marks a partial final block and is followed
by its gain. The next block control is prefetched one bit per sample over five
(or ten for a partial marker) samples. Each sample then appends its ANS suffix.
The initial partial block uses the same explicit marker. Counts with fewer
than five tail samples are rejected. The decoder checks every G, current and
new state, full terminal, both CRCs, exact total size and at most seven zero
padding bits. Extra zero payload bytes with an adjusted header are rejected.
Every successful result is replayed independently and canonically repacked
byte for byte, including all50000 physical R2R DAC outputs.

## Measured two-second results

| Search | SER dB | Payload bytes | ANS bits/sample | Peak/RMS | Maximum N | D+64R |
|---|---:|---:|---:|---:|---:|---:|
| Exact generic table control |25.361479|8491|1.33846|6.678679|6|107.884763|
| Difference initial |25.340618|8493|1.33878|6.662658|6|108.012248|
| Difference P retrain |25.111443|8355|1.31680|6.489165|7|107.815531|

The control exactly reproduces the saved beam64 q/s/G. Initial difference
prediction loses0.020861 dB and adds2 payload bytes while saving1024 bytes
against the board's2048-byte model. The retrained result loses0.250036 dB and
saves136 payload bytes; its measured D+64R improves only0.069231. The initial
result is the closest quality match and the stronger candidate for a separate
full-length decision. This short screen does not establish a15s26 dB result.
No fourth search or full-length run was performed.

All three peak errors are15.7421875 DAC steps. The initial result's state
ranges are q[-256,251], d1[-92,97], d2[-79,67], d3[-78,89]; retrained ranges
are q[-256,248], d1[-92,93], d2[-73,84], d3[-81,83]. Actual fitted books are
[175,37,35,4,5] for control, [175,36,36,4,5] initial and [175,37,36,3,5]
retrained. The last book requires N7, within the audited N8 parser budget.
Full DHA1 container sizes are13143,10073 and9935 bytes, respectively; these
include host headers and generic control tables and are not complete ROM
sizes. Both new results replay all50000 q/label/G values and DAC outputs and
repack byte-exactly. `--replay-only` reproduces the same report SHA-256
`67faeffadd0f95535c08d45108014fd3095f356c682ea32542a6ad63bb031718`.

## Reproduction and scope

Run `probe.py --build <ignored-build-dir>` from a Visual Studio developer
prompt, then `verify_audio.py --library <difference.dll> --output
<build-dir>/verification.json`. Run `probe.py --library <difference.dll>` for
the bounded phase. Existing progress prevents restarting a live/completed
phase. `probe.py --replay-only` validates saved containers without C searches.
The retained report is [audio-screen.json](../r2r/25k/reports/audio-screen.json).
Temporary DLLs, containers, process progress and the native PCM remain under
ignored `build/audio/capacity-stage33-difference-*`.

The separate [hardware audit](hardware.py) measures the register-only kernel
and parser skeleton. Its1024-byte difference model is compared with the
2048-byte board delta model;4096-byte generic tables in this host format are
not the board baseline. The401T kernel and audited N8 parser fit the800T
schedule, but these PC results alone do not prove execution of compressed
audio in the CPU or on a physical board. Full15s conversion, new firmware and
publication require a later decision.
