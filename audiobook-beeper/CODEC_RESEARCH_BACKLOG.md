# Audio codec research backlog

Saved 2026-10-03 at the user's request. This is a research list, not an
automatic task schedule or a promise that the unported codecs fit Z80.

## Current constraints

- Reference rate: mono 8000-Hz PCM16, 128 kbit/s. Preferred compression
  is **5:1..10:1** (25.6..12.8 kbit/s); higher ratios are welcome when
  sound preservation permits. Count framing and recording-specific books.
- The existing test signal has 186880 PCM8 samples, represented as 373760
  PCM16 bytes for the ratio. This does not recover lost 16-bit precision.
- PC encoding complexity is unrestricted. Spectrum preparation must take
  at most twice the measured raw 128-KiB read: **39.904 s** in cold Fuse 128.
- Preserve voice timbre and waveform. Suggested codec SNR 25..30 dB and
  final PDM 20 dB are evaluation targets, not newly approved hard gates;
  also compare listening, clipping, active-window error and speed (within 2%).
- The user selected only three-bit IMA and predictive VQ for three decoder
  optimization rounds each. Other formats remain future research.

## Candidates and priority

Nominal ratios exclude overhead unless a measured total is given. Local
quality results are input-specific; codec SNR is not final beeper SNR.

| Format / approach | Rate or compression | Status and next useful step |
|---|---|---|
| Project ADPCM3-step6 / IMA subset | 24 kbit/s; 5.331:1 including 32-byte framing | Selected. Exact expansion to the existing four-bit IMA stream is possible by `nibble = code << 1`. Existing codec SNR 20.999 dB. Three native optimization rounds completed; integrate and validate separately. |
| Predictive VQ3x512, half-last predictor | 5.217:1 including 1536-byte book and 32-byte framing | Selected. Existing codec SNR 22.185 dB. Three native PCM decoder rounds completed. Still needs fast IMA encoding, resident-bank integration and complete startup/playback checks. |
| ADPCM-XQ, 2-/3-/4-bit variants | Nominal 8:1 / 5.33:1 / 4:1 | Prioritize expensive PC search/noise shaping. Four-bit is the quality baseline outside the preferred ratio. Generic three-bit formats are not necessarily our exact IMA subset. |
| ITU G.726, 16/24 kbit/s | 8:1 / 5.33:1 | Now fits the relaxed rate range. Local 16-kbit/s codec SNR 16.481 dB; existing downstream IMA guard rejected saturation. Test a better preparation/encoding path before any port. |
| QOA | About 25.6 kbit/s; about 5:1 payload | Header overhead makes actual compression slightly less than 5:1. Four-tap LMS decoder needs products; measure quality and integer cost before Z80 work. |
| WavPack hybrid, 2..3 bits/sample | Nominal 8:1..5.33:1 before overhead | Waveform candidate. First measure actual streams and fixed-point decoder cost; the nominal setting alone does not prove a Z80 fit. |
| Speex narrowband | 11/15/18.2/24.6 kbit/s | Standard speech listening reference. CELP/LPC includes excitation information, unlike our simple LPC synthesis. Fixed-point availability is not a Z80 timing proof. |
| Opus narrowband | Roughly 12..24 kbit/s as audition settings | Quality reference before porting. Narrowband speech may use LP-only mode; do not assume MDCT is required in every stream. Entropy decoding and synthesis still need a timing study. |
| ITU G.729 / G.729A | 8 kbit/s; 16:1 | Strong compression, CS-ACELP speech model. No local quality or Z80 timing proof; lower priority than waveform-preserving options. |
| CVSD | Candidate 8/12/16-kbit/s streams | Small-state one-bit adaptive waveform approach; not locally measured. Compare quality with DFPWM before allocating port work. |
| DFPWM | Tested 8/12 kbit/s; 15.98:1 / 10.66:1 with framing | Low priority: measured SNR 6.322/8.789 dB, or 8.705/11.323 dB after constant-delay alignment. Does not meet the desired preservation. |
| Larger / more advanced vector quantizers | Book-dependent | VQ3x1024 previously reached 24.348-dB codec SNR but about 4.62:1, outside the preferred range. The stricter 10:1 sweep was lower quality; improve encoder/model only with explicit rate accounting. |
| Lossless packing of IMA or PCM; FLAC/WavPack lossless | Input-dependent | No fixed 5:1 guarantee. Useful if exact waveform preservation matters; count decoder cost and dictionary/buffer RAM. |
| LPC / Codec2 vocoders | High nominal compression | Deprioritized for timbre preservation. Our actual LPC-to-IMA preloader took 657.181 s in cold Fuse, versus the 39.904-s limit. Other vocoders are not thereby benchmarked or proven impossible. |
| AAC / MP3 | Configurable | Deferred PC quality/size references. No suitable Z80 preload decoder has been implemented or timed here. Do not assume a small disk file means fast decompression. |

## Primary sources

The following sources were researched on 2026-10-03. Suitability judgments
above are project inferences unless accompanied by a local measurement.

- [ADPCM-XQ source and documentation](https://github.com/dbry/adpcm-xq).
- [ITU G.726](https://www.itu.int/rec/T-REC-G.726/en) and
  [ITU G.729](https://www.itu.int/rec/T-REC-G.729/en).
- [QOA specification](https://qoaformat.org/) and
  [reference implementation](https://github.com/phoboslab/qoa).
- [WavPack documentation](https://www.wavpack.com/wavpack_doc.html).
- [Speex manual](https://www.speex.org/docs/manual/speex-manual/node10.html).
- [Opus specification, RFC 6716](https://www.rfc-editor.org/rfc/rfc6716.html).
- [CVSD implementation overview](https://www.adaptivedigital.com/cvsd/).
- [FFmpeg DFPWM decoder](https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/dfpwmdec.c).
- [Codec2 project](https://github.com/drowe67/codec2).

Reuse the [strict 10:1 study](TEN_TO_ONE_CODECS.md), the earlier
[dense-codec measurements](DENSE_CODECS.md), and the rejected
[LPC preloader evidence](LPC_PRELOAD.md). None of these candidate studies
constitutes a newly qualified playback disk.
