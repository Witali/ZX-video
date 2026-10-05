# Two-bit G.726 experiment

Implemented on 2026-10-05: G.726 at **16 kbit/s, mono 8 kHz**, with a
PCM16 interface, a PC encoder, a streaming decoder, and a complete native
Z80 decoder compiled separately with SDCC. Four codes occupy one byte;
the payload is exactly **8:1** relative to PCM16. No IMA transcoding is used.

The implementation is executable research. The measured Z80 port does
**not** meet real-time playback or the 60-second preparation limit. It is
therefore not a new `convert_audio.py` playback mode and does not generate
a TRD. Existing IMA and mu-law players, defaults and release disks are
unchanged. See the [measured results and listening files](../experiments/g726-2bit/README.md).

## Codec and transport

The encoder subtracts the adaptive prediction from each PCM sample and
quantizes the difference into two bits. The decoder inverse-quantizes that
code, adds the prediction, and updates the adaptive state. It contains:

- A two-pole and six-zero predictor with eight Float11 products per sample.
- Reconstructed-sample and difference histories, represented by sign,
  exponent and six-bit mantissa.
- Fast and slow scale factors, activity averages and tone/transition logic.
- A 100-byte state in this portable implementation. This is an implementation
  layout, not a claim that the standard requires that exact amount of RAM.

The standard decoder is substantially more involved than adding a signed
step and adjusting a step index in IMA. Reducing the number of bits per code
does not reduce that predictor work.

`soundtrack.g726` is headerless, MSB first: bits7..6 hold the first sample's
code, then bits5..4, bits3..2 and bits1..0. Keep state across bytes and file
chunks; reset only at the start of an independent stream. The wrapper also
supports FFmpeg `g726le` packing, but the native benchmark consumes MSB-first
data. The audition converter pads at most three final samples by repeating
the last level; the JSON records the exact count. No framing, seek table,
checkpoint or boot-loader overhead is included in the 8:1 ratio.

Integer details matter. Encoder division by four truncates toward zero.
Float11 products round with `(mantissaA * mantissaB + 48) >> 4` before
exponent scaling. Adaptive updates use arithmetic right shifts. The
uniform PCM interface deliberately follows FFmpeg's signed16 wrapping
behavior after its wider reconstruction clamp; replacing that with IMA-like
saturation would change the output. All four versions retain this behavior.

## Three optimization rounds

`core.c` selects each independently reproducible version with `OPT=0..3`:

| Version | Change from the preceding version | Generic lookup bytes |
| --- | --- | ---: |
| 0 | Straightforward wide-integer baseline | 0 |
| 1 | Proven bounded 16-bit Float11 intermediates; avoid unnecessary wide shifts | 0 |
| 2 | Leading-bit and rounded mantissa-product lookups | 1280 |
| 3 | Inverse-quantizer lookup over every reachable scale; replace products by signs with comparisons/additions | 5860 |

The tables are generic, not trained on the recording. Adaptive state remains
32-bit where narrowing has not been proved safe. Native measurements include
table reads, packed-bit extraction, writes, initialization and state-copy
overhead; separate core costs exclude CALL17 but include the function's
return sequence. The saved table reports absolute T-states and differences
between rounds on exactly the same input and block size.

This is an SDCC-compiled exact port, not a hand-optimized assembly speed
limit for all possible G.726 implementations. Further handwritten work
would be a separate experiment. The existing PDM hot paths change by **0 T**.

## Use and reproduce

From the repository root, with Python, NumPy and an installed host C compiler
(MSVC on Windows or `cc` elsewhere):

```powershell
$env:PYTHONPATH='audiobook-beeper;toolkit;C:/Work/ZX-video/local_tools/python_packages;C:/Work/ZX-video/.tmp/lzma-z80-packages'
$env:PYTHONUTF8='1'
$ffmpeg='C:/path/to/ffmpeg.exe'
$sdcc='C:/path/to/sdcc.exe'
python audiobook-beeper/convert_g726_audio.py input.wav --ffmpeg $ffmpeg --outdir build/g726-audition --seconds 60
```

The converter writes the resampled PCM16 reference, raw G.726 payload,
decoded PCM16 WAV and a JSON report. It verifies both encoding and decoding
against FFmpeg. Resampling to 8 kHz uses FFmpeg's band-limited resampler;
there is no additional loudness normalization or fade. `--library` can reuse
an already compiled host library. The default retains the initial 60 seconds.

To rebuild all four Z80 versions and run the complete study, the Python
`z80` CPU emulator and the repository's timing helpers must be importable:

```powershell
python -m g726.study --source audiobook-beeper/experiments/quality-max/evidence/ima3/selected/source-preview.wav --outdir build/g726-study --ffmpeg $ffmpeg --sdcc $sdcc
```

`--reuse` explicitly reuses the four compiled snapshots in that output
directory. It does not assert they were rebuilt from the current sources;
each snapshot carries source/compiler hashes. SDCC generates and assembles
the Z80 code outside Python. `codec.py` preserves major-routine comments in
the generated assembly; Python loads the resulting Intel HEX for testing.

## Verification scope

Host tests compare nine PCM fixtures against FFmpeg in both byte packings,
including silence, rails, impulses, ramps, tones and random data. A separate
arbitrary-code test compares all output and all 100 state bytes across every
optimization, including streaming with non-byte-aligned API chunks.

The native verifier runs every sample of the selected recording and checks
PCM and state at each block boundary. It guards memory, stack, mailbox and
output bounds. It separately checks executed instruction costs against the
Zilog timing table, including indexed instructions and taken branches, then
compares that sum with the emulator's counter. A separate arbitrary-code
native fixture covers byte patterns, repeated codes and random data.

The flat CPU fixture loads code at0200 and state at8000; it is not a Spectrum
RAM allocation or boot image. The entry uses mailbox8F00, packed input9000,
PCM outputA000 and stack belowFF00, with no ROM, disk, interrupt or ULA time.
`g726_decode_one` uses SDCC's ABI: state pointer HL, code byte above the
return address, PCM16 result DE; the callee removes that byte. IX is
preserved; IY is scratch. The outer entry preserves its stack/IX contract.

The listening WAV is decoded PCM. Its SNR includes codec error, and a second
measure applies the established 70-Hz high-pass/two 4.5-kHz low-pass filters
with float64 arithmetic and fixed sample boundaries. Neither includes PDM,
Fuse output, analog circuitry or a speaker. Do not compare it directly with
the IMA end-to-end numbers as if the measurement scopes were identical.

## Provenance and license

`core.c` is adapted from Roman Shaposhnik's FFmpeg implementation, licensed
under LGPL-2.1-or-later. The original source and full license are retained
as [ffmpeg-reference.c](ffmpeg-reference.c) and
[COPYING.LGPLv2.1](COPYING.LGPLv2.1). Modifications specialize the two-bit
mode, expose a standalone API, add exact bounded optimizations and the
native benchmark interface.

- [ITU G.726 recommendation](https://www.itu.int/rec/T-REC-G.726/en).
- [FFmpeg n8.0 source used for the port](https://raw.githubusercontent.com/FFmpeg/FFmpeg/n8.0/libavcodec/g726.c).

The independent executable comparison uses the installed FFmpeg8.1.1.
Official ITU conformance vectors were not run; FFmpeg compatibility is the
tested claim. The archive records hashes of the source, binaries, input and
tools actually used.
