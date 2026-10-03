# Audio codecs for the Spectrum preload budget

Later scope update (2026-10-03): the user relaxed the preferred compression
range to **5:1..10:1**, welcoming higher ratios when fidelity permits, and
selected the project's three-bit IMA subset and predictive VQ for three
Z80 optimization rounds each. The strict 10:1 sweep below is historical;
its measurements and rejection reasons remain useful. See the current
[research backlog](CODEC_RESEARCH_BACKLOG.md) for priorities.

Research and measurements: 2026-10-03. The user clarified **10:1 relative
to mono 8000-Hz PCM16**, so the target is at most **12.8 kbit/s**, including
recording-specific tables and framing. Encoding cost on the PC is unrestricted.
Conversion on the Spectrum must take no more than twice a raw128-KiB read:
the cold Fuse benchmark gives **39.904 s**. Sound preservation takes priority
over declaring a nominal compression success.

No tested candidate currently satisfies all of compression, high fidelity,
and complete Z80 startup timing. This report selects directions and rejects
inadequate prototypes; it is not a new player release.

## Existing codecs: shortlist and sources

Ratios below are relative to128-kbit/s PCM16. Nominal payload ratios exclude
container overhead; measured local ratios in the next section include it.

| Codec | Nominal rate / ratio | Suitability for this project |
|---|---|---|
| ADPCM-XQ, IMA family | 4-bit32k /4:1; 3-bit24k /5.33:1; 2-bit16k /8:1 | Best immediate architectural fit. Expensive PC lookahead and noise shaping retain a simple decoder. It does not itself meet10:1. |
| G.726 two-bit ADPCM | 16k /8:1 | Waveform alternative; misses the rate target, and the predictor is more complex than IMA. |
| Speex narrowband | 11k /11.64:1 payload | Best standard speech-codec audition candidate near the target. Fixed-point implementation exists, but the LPC/CELP decoder needs a separate Z80 feasibility proof. |
| G.729 /G.729A | 8k /16:1 | Standard speech candidate; CS-ACELP synthesis, not a cheap table-only decoder. No timing result here. |
| Opus narrowband | 12k /10.67:1 payload | Useful quality reference. LP synthesis, entropy coding and other decoder work make a Z80 port a high-risk next step; this is an architectural inference, not a measured port. |
| QOA | about25.6k /5:1 | Compact waveform codec with four-tap LMS prediction, but it misses10:1 and requires products in decoding. |
| CVSD /DFPWM | 8..12k /16..10.67:1 payload | Small-state adaptive one-bit waveform codecs. Rate fits; the tested DFPWM variants fail the desired fidelity. CVSD has not been measured here. |
| WavPack /FLAC lossless | input-dependent | Exact reconstruction, but no guaranteed10:1. WavPack hybrid's documented2-bit/sample lower setting already corresponds to16k, before overhead. |
| Codec2 /LPC vocoders | low speech bitrates | Reconstruct speech from a model; poor fit for the user's wish to preserve the actual waveform/timbre. |

Primary sources, retrieved2026-10-03:

- [ADPCM-XQ](https://github.com/dbry/adpcm-xq) describes dynamic noise shaping,
  lookahead and unchanged standard decoding. Its
  [CLI source](https://github.com/dbry/adpcm-xq/blob/master/adpcm-xq.c) accepts
  2..5-bit widths. These modes are not all compatible with our existing
  four-bit player without a decoder change.
- [ITU G.726](https://www.itu.int/rec/T-REC-G.726/en) defines16/24/32/40k modes.
- [Speex manual](https://www.speex.org/docs/manual/speex-manual/node10.html)
  documents the11k mode, CELP construction and approximate decoder complexity.
  [Microchip's implementation](https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/SoftwareLibrary/speex-speech-encodingdecoding/70328C.pdf)
  reports2.1MIPS for narrowband decode on certain dsPIC devices. This is
  **not a Z80 timing number**; processor instruction sets differ substantially.
- [ITU G.729](https://www.itu.int/rec/T-REC-G.729/en) specifies8-kbit/s CS-ACELP.
- [Opus RFC6716](https://www.rfc-editor.org/rfc/rfc6716.html), sections2.1.1
  and4, describes narrowband8..12k operation and the decoder. Do not assume
  its narrowband speech mode always performs an MDCT: LP-only operation exists.
- [QOA](https://qoaformat.org/) stores20 samples in64-bit slices, or3.2bits/sample.
- [CVSD implementation](https://www.adaptivedigital.com/cvsd/) documents
  8/12/16k one-bit modes. [FFmpeg DFPWM decoder](https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/dfpwmdec.c)
  gives the actual charge, strength and reconstruction-filter recurrences.
- [WavPack manual](https://www.wavpack.com/wavpack_doc.html) describes hybrid
  bitrate controls and separate correction data. Lossless ratios are
  input-dependent, not a fixed-rate quality guarantee.
- [Codec2 project](https://github.com/drowe67/codec2) is a speech-codec
  reference, not an established Spectrum implementation.

Speex and Opus use linear prediction, but they also transmit information
about the excitation/residual. They must not be equated with the crude
pulse/noise LPC vocoder solely because both contain an LPC filter. Their
quality needs listening and their speed needs executable Z80 measurements.

## Complete control-excerpt measurements

The control signal is the unchanged186880-sample prepared PCM8 excerpt,
SHA256 `ea3c0d945a0cc349747664c137c3725aee3fe8cf5e17b991ae3e24f51829a304`.
The requested denominator is its **373760-byte PCM16 representation**;
expanding this signal to16bits does not restore missing source precision.
Every row includes a32-byte framing allowance plus all stored dictionary
bytes. `.gz` is only the archive wrapper, not the proposed runtime format.

| Trial | Total bytes | PCM16 ratio | Codec SNR | After ordinary IMA |
|---|---:|---:|---:|---:|
| DFPWM8k |23392|15.98:1|6.32dB|6.26dB|
| DFPWM12k, resampled back to8k |35072|10.66:1|8.79dB|8.70dB|
| G.72616k |46752|7.99:1|16.48dB|Rejected: IMA saturation guard|
| VQ6 samples/256 entries |32715|11.42:1|13.70dB|13.24dB|
| VQ7/512 |33652|11.11:1|14.21dB|13.74dB|
| VQ8/512 |30408|12.29:1|13.43dB|13.01dB|
| VQ8/1024 |37424|9.987:1|14.98dB|14.38dB|
| VQ10/512 |26176|14.28:1|12.37dB|12.07dB|
| Shape/gain VQ10/256 |34720|10.76:1|12.13dB|11.86dB|
| Predictive VQ7/512 |33652|11.11:1|14.22dB|13.72dB|

These are **codec-only** results using the established70-Hz highpass and
two4500-Hz lowpass comparison filters, with no PDM, ULA or speaker model.
DFPWM has filter delay: allowing only a constant integer shift at44.1kHz
improves its values to8.71/11.32dB; no gain adjustment or time stretching
is used. It still does not meet the proposed fidelity target. The after-IMA
column uses the normal fixed sample clock and a128-sample silent guard.
The guard does not mask speech errors. All ordinary VQ books are trained
on this recording and transmitted, not free pre-existing information.

A proposed6000-Hz G.726 /12000-bit/s test was rejected by FFmpeg. It was
not silently relabelled as standard G.726. The initial limited sweep was
extended once to shape/gain and seven-sample predictive VQ; neither improves
the selected candidate after IMA. VQ8/1024 misses10:1 by48 bytes and is
reported as a miss, not rounded to a pass.

## Full native VQ7-to-IMA proof

The external assembler compiles [the CPU probe](probe-vq7-ima.asm). The
native harness executes all186880 samples and compares every PCM8 value
and IMA nibble against independent references. Input genuinely crosses
two RAM banks; the512 seven-byte vectors are expanded to4096bytes in RAM.
Groups of eight9-bit indices use one high-bit header and eight low bytes,
still30036 payload bytes. The dictionary and step table remain unchanged.

VQ decoding costs49T within a vector,203/206T at a new vector,
262/265T when a new high-bit header is also read. Crossing the input bank
adds85T; the actual crossing path is288T. These counts include RET but
exclude the17-T caller CALL. The common path is
EXX4 + DEC IYH8 + JR NZ12 + LD A,(HL)7 + INC L4 + EXX4 + RET10 =49.
At a new vector, the not-taken sample branch, vector/group counters,
49-T read-byte call and address formation give203T; the high-half
JR/SET path adds3T. Reading a new header adds59T. The mean is72.245T
before CALL, or **4.699 s** for the audible VQ decode including CALL.

The unchanged baseline IMA encoder costs538..866T, mean642.927T before
CALL. Whole native VQ + IMA + probe control is **148778057T /41.946 s**.
This already exceeds39.904 s and excludes ULA, final packed-output writes,
resident-bank management and disk/ROM service. The sink is a test port;
this is **not** a complete preload disk or playback validation. The initial
harness needed a fix to ignore the native core's ordinary frame-boundary
yields; no decoder change was needed for the complete successful byte check.

The candidate is rejected for the user's fidelity requirement as well as
being over the current full-conversion budget. Optimizing its IMA encoder
was considered but not implemented after the fidelity requirement was
clarified. The established PDM playback hot path is unchanged:423T/sample,
delta0. Rebuilding its old disk with the conditional LPC changes also
produces the identical SHA256
`68c22d1e49273242393b009c030a86ea395ca234ea9fdf36b988edb5a2568aa6`.

## Proposed quality gate and decision

“Two least significant bits” needs a reference bit depth. Rounding away
two bits of PCM16 means a step of4 and an error around+/-2 PCM16 units.
It is much stricter than the existing PCM8 stage. The latter already
quantizes at256 PCM16 units per step; no new compressor can restore those
discarded source bits. A simple LSB count is therefore not the best sole
criterion for this output chain.

Use a proposed codec-only SNR target of25..30dB, aiming for30dB, together
with peak/percentile errors and short active-window measurements. The main
end-to-end gate remains at least20dB against the same prepared source in
both complete PDM loops, fixed clock/speed within2%, no saturation, and
listening comparisons of consonants, quiet passages and voice timbre.
These new codec thresholds are **recommendations**, not user-approved hard
requirements. SNR does not by itself prove perceptual transparency, and
different constant delays must be aligned fairly before comparing codecs.

Priority: preserve the proven IMA/PDM player and evaluate ADPCM-XQ-style
high-effort PC encoding or stronger encoder-only search. Treat2-/3-bit
ADPCM as explicit quality/rate tradeoffs, not an automatic10:1 success.
If10:1 is retained as a research target, advanced waveform dictionaries
remain worth studying, but the current simple VQ is not adequate. Use
Speex11k and Opus12k as future listening references before committing to
a costly Z80 port. Do not promise a ready standard codec that meets all
three conditions without an actual port and full startup/quality checks.

## Reproduction

```powershell
python audiobook-beeper/probe_ten_to_one.py --source <original-source-preview.wav> --output build/ten-to-one --ffmpeg <ffmpeg.exe>
python audiobook-beeper/verify_vq7_ima.py --input build/ten-to-one --output build/vq7-native --codec vq7x512
```

Use the project Python packages and include`audiobook-beeper` and`toolkit`
on PYTHONPATH. Set OPENBLAS_NUM_THREADS=1 for the bounded dictionary sweep.
Saved [comparison](experiments/ten-to-one/report.json),
[native proof](experiments/ten-to-one/native/report.json) and WAV examples
preserve both successful measurements and the reasons for rejection.
