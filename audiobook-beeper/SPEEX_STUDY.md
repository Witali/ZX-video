# Speex audition and Z80 feasibility checkpoint

Measured 2026-10-03 at the user's request. This is a complete host codec
audition and an exact Z80 arithmetic probe, **not a Speex playback TRD**.
The mandatory final-PDM target remains at least 20 dB in both complete cold
Fuse loops. Codec-only or PCM-to-IMA scores do not satisfy that gate.

## Same complete reference

Use all 186880 original 8-kHz PCM8 samples (23.36 s), SHA256
`ea3c0d945a0cc349747664c137c3725aee3fe8cf5e17b991ae3e24f51829a304`.
The PCM16 storage denominator is 373760 bytes; its source precision is
still eight bits. Add one silent 160-sample frame to flush the codec and
count that frame in storage. Keep the original gain and clock, remove only
the API-reported encoder 40 + decoder 40 samples of latency, and compare
every source sample. The final 128-sample guard remains unchanged before
IMA encoding. No speech is removed to improve the scores.

The comparison uses the established 70-Hz highpass and two 4500-Hz lowpass
filters at 44.1 kHz, trimming only the same 0.1-s measurement edges. These
are codec-study scores, using the same pipeline as the prior codec study;
they are not the fixed-clock reconstruction of an executed PDM trace.

## Results

Encode with unmodified Speex 1.2.1 floating-point code, complexity 10,
constant bitrate, no VAD or DTX. Decode with its unmodified fixed-point
implementation, disabling the optional codec highpass and perceptual
enhancement through the public API. Disabling a codec filter does **not**
change the common measurement filter.

| Rate, kbit/s | Stored frame bytes + 32-byte framing allowance | PCM16 ratio | Speex SNR | After existing IMA encoder |
|---|---:|---:|---:|---:|
| 8 | 23412 | 15.964:1 | 14.506 dB | Rejected: IMA saturation guard |
| 11 | 32764 | 11.408:1 | 18.702 dB | 17.526 dB |
| 15 | 44454 | 8.408:1 | 21.643 dB | 19.543 dB |
| 18.2 | 53806 | 6.946:1 | 24.752 dB | 21.054 dB |
| 24.6 | 72510 | 5.155:1 | 27.823 dB | 22.037 dB |

The rows include 1169 byte-aligned 160-sample frames, including the flush,
and a 32-byte **proposed** framing allowance. The `.gz` files are archival
wrappers, not the proposed Spectrum compression. Ratios exclude decoder
code, fixed codec books, TR-DOS sector padding and container overhead.
The initial FFmpeg Ogg trial separately reports actual Ogg sizes.

After-IMA uses the already implemented, inexpensive threshold encoder
intended for Spectrum startup, with its exact no-saturation requirement.
It is not replaced by a costly PC beam search. Every accepted stream
decodes to the expected length and finishes at predictor/index 0/0.
The PDM modulator and real machine timing would add further error.

Thirty controlled cases cover five bitrates, optional processing, and both
floating-point and fixed-point decoding. Fixed-point and float versions
give close quality results; this is not a claim of identical PCM bytes.
At 24.6 kbit/s the optional perceptual enhancement lowers fixed-point
waveform SNR to 24.938 dB; removing it gives 27.823 dB. This metric measures
waveform preservation, not a listening panel's preferred timbre.

The first ten FFmpeg trials use the ordinary highpass/enhancement settings.
They score only 3.32..3.51 dB even after their disclosed best integer
delay correction (79 samples). The controlled API tests remove the declared
80 samples instead. Do not compare those two alignment conventions as a
codec improvement. The controlled highpass-on rows also fail badly; the
important improvement comes from the supported processing options.
Do not discard these failed cases or call the default codec unintelligible
on the strength of a waveform metric alone.

## Z80 timing: the tested exact approach misses the budget

The [reference synthesis](https://github.com/xiph/speex/blob/Speex-1.2.1/libspeex/filters.c)
uses ten signed 16-by-16 products with 32-bit state per sample in
`iir_mem16`; [narrowband decoding](https://github.com/xiph/speex/blob/Speex-1.2.1/libspeex/nb_celp.c)
also needs LSP conversion/interpolation, excitation and pitch decoding.
The 39.903992-s budget at 3.5469 MHz permits 757.360 T per output sample,
or 75.736 T per product if **all other work were free**.

The separately assembled [exact lookup kernel](probe-speex-multiply.asm)
uses seven prepared 256-byte planes per coefficient, 17920 bytes for ten
coefficients. It forms the signed 32-bit product without rounding:

`7 loads * 7 + 6 increments * 4 + index move 4 + 3 additions * 4 +
3 result moves * 4 + RET 10 = 111 T`; caller `CALL` adds 17 T.

The native Z80 core verifies **1376146 input pairs**, every possible
coefficient on ten byte/sign boundaries, and every possible input for
eleven representative coefficients. Every result and every 128-T call
matches independently computed signed multiplication. The code remains
unchanged and the stack balances.

For all 186880 samples, the 1868800 products alone take **207436800 T /
58.484 s**, or 67.441 s including CALL. This optimistic projection excludes
table preparation and refresh, argument setup, accumulation, bit parsing,
LSP/pitch/excitation work, clipping, IMA conversion, ULA, paging and disk.
It is based on an executed kernel, **not an executed full Speex decoder**.
It rejects this exact-table strategy under the startup limit; it is not a
proof that every conceivable specialized Speex implementation is impossible.

The PDM player is unchanged: ordinary 423 T/sample, delta **0 T**. No new
disk, cold Fuse run, PDM recording or physical hardware test is claimed.
The user's three optimization rounds remain completed for the previously
selected IMA3 and PVQ decoders; this is a Speex audition and feasibility
screen before committing to a new full Z80 port.

## Decision and saved evidence

Keep **24.6 kbit/s** as the best tested fidelity reference and **18.2 kbit/s**
as the more compact listening candidate. Both clear 20 dB before PDM after
the existing IMA conversion; neither is a qualified end-to-end release.
Speex does preserve this speech much better than the previous simple LPC
vocoder, but no decoder satisfying our preparation limit is established.
Do not present a PC-decoded IMA disk as a disk storing and decoding Speex.

Saved [controlled results](experiments/speex/controlled/report.json),
[initial FFmpeg trials](experiments/speex/ffmpeg/report.json),
[native arithmetic result](experiments/speex/native/report.json), source
archive, compiler logs, hashes and selected WAVs preserve this checkpoint.
The [Speex manual](https://www.speex.org/docs/manual/speex-manual/node10.html)
describes the bit allocation; the [public API](https://www.speex.org/docs/api/speex-api-reference/group__Codec.html)
and versioned source define the controls. Primary sources retrieved
2026-10-03. DSP MIPS are not converted to Z80 MHz.

## Reproduction

Extract the saved official Speex 1.2.1 source archive into a scratch folder.
Use the project Python environment (NumPy, pyz80 and z80), `audiobook-beeper`
and `toolkit` on PYTHONPATH, and an installed MSVC and FFmpeg with libspeex.
All output directories must be new. Set OPENBLAS_NUM_THREADS=1.

```powershell
python audiobook-beeper/build_speex_host.py --source <speex-1.2.1> --output <host-build> --vcvars <vcvars64.bat>
python audiobook-beeper/probe_speex_controlled.py --source audiobook-beeper/experiments/ima-3bit-preload/source-preview.wav --host <host-build> --output <controlled> --ffmpeg <ffmpeg.exe>
python audiobook-beeper/probe_speex.py --source audiobook-beeper/experiments/ima-3bit-preload/source-preview.wav --output <ffmpeg-trial> --ffmpeg <ffmpeg.exe>
python audiobook-beeper/probe_speex_budget.py --output <native-probe>
```

The initial MSVC helper needed fixes for Windows shell quoting, explicit
compiler discovery and localized log decoding. The successful build keeps
raw compiler logs. Stock source emits alignment-cast warnings on Windows
x64; its cast is masked to alignment bits, not used as the full pointer.
The successful codec runs preserve the upstream code and its license.
