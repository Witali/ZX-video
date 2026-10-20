# DHA codec for host applications

DHA is a small C99 audio codec library with a WAV command-line adapter. The
predictive mode is lossy; ANS entropy coding preserves its selected residual
symbols exactly. A frame may instead contain the original PCM16 samples.
`dha info` reports the actual predictive and PCM16 fallback frame counts, so a
successfully encoded file is not automatically a compression claim.

The library performs no resampling and has no file, MP3, FFmpeg, Python, or
audio-device dependency. It accepts mono or stereo streams at 1–192000 Hz.
Rate, channel count, and sample-frame count are retained in the file header.
The PCM decoder emits the same unsigned-eight-bit rounding used by the DHA1
R2R implementation, represented as signed PCM16; PCM16 fallback frames retain
their original sixteen-bit values. This host container is described in
[FORMAT.md](FORMAT.md); it is separate from the compiled-first Z80 ROM wire.

## Illustrated algorithm

[Encoding and decoding, step by step](ALGORITHM.md) explains the search,
four-table predictor, reverse ANS packing, forward decoding and independent
frame layout with diagrams and a measured predictor/residual trace.
[Русское описание со схемами](ALGORITHM.ru.md) covers the same algorithm.
The byte-level contract remains in [FORMAT.md](FORMAT.md).

Function comments in [the public header](include/dha_codec.h) describe
parameters, ownership, return values and error handling. The C implementation
also explains the search, bit packing, state checks and final-frame validation
next to the code that performs them.

## Build

Configure the library directory directly, or add it to a CMake project:

```sh
cmake -S audio/lib/dha-codec -B build/dha-codec -DDHA_BUILD_ENCODER=ON
cmake --build build/dha-codec --config Release
ctest --test-dir build/dha-codec -C Release --output-on-failure
```

The CLI executable is `dha` (`dha.exe` on Windows); its directory depends on
the selected CMake generator and configuration. To use the library from a
parent project:

```cmake
add_subdirectory(path/to/audio/lib/dha-codec dha-codec)
target_link_libraries(my_player PRIVATE dha::codec)
```

The public header is `dha_codec.h`. Set `DHA_BUILD_ENCODER=OFF` for a
decoder-only library; that configuration omits the encoder and CLI. The
decoder API allocates no memory. The optional encoder may allocate its search
workspace on the host.

`BUILD_SHARED_LIBS=ON` produces a shared library/DLL; the default is static.
For an installed package, use `cmake --install build/dha-codec --config Release
--prefix build/dha-codec/install`, then `find_package(DhaCodec CONFIG REQUIRED)` and
link `dha::codec`. The public C header also supports C++ callers.
The [external consumer example](examples/cmake-consumer/CMakeLists.txt) builds
against the installed package using `-DCMAKE_PREFIX_PATH=<absolute-install-path>`.

## Command line

```sh
dha encode input.wav output.dhaf
dha encode input.wav quick.dhaf --frame 1024 --fast
dha info output.dhaf
dha decode output.dhaf reconstructed.wav
```

`--frame N` selects 1–4096 samples per channel, with 4096 as the default.
`--fast` requests beam width 8, two gain candidates, and no lookahead; it is
useful for quick integration checks and can change the encoded result.
Encoding and decoding refuse an existing output path. A failed operation
closes and removes the output it created; it does not remove a pre-existing
file. Input and output must be different files.

The WAV reader accepts little-endian `RIFF`/`WAVE` PCM16, one or two channels,
one `fmt ` chunk and one `data` chunk. It skips bounded ancillary chunks such
as `JUNK`, accepts `fmt ` before or after `data`, checks odd-byte chunk padding,
RIFF/data boundaries, byte rate, and block alignment, and rejects truncated or
ambiguous input. It scans the complete RIFF container before encoding and
requires a seekable input file. RF64, floating-point PCM, extensible WAV, and
multiple `data` chunks are unsupported. Decoding writes a standard PCM16 WAV
with a known length that fits the 32-bit RIFF size; an unknown-length DHAF
stream can be validated with `info` but cannot be written by `decode`.

Each sample group stores channel 0, then channel 1 when present, using the
same group sequence and sample count. Only the final group may be short.
The CLI checks this order, declared totals, missing/duplicate channels,
trailing data, and every frame's complete decoder result. `info` therefore
validates the payloads and final ANS/padding conditions, rather than only
reading headers. Its statistics contain sample and frame counts, compressed
and PCM16 fallback counts, payload bits, and file/PCM byte sizes. No SNR/SER
calculation is performed.

For MP3 or another source format, an external application must first decode
the original into PCM16 WAV. Keep the source rate when possible. If a target
rate is needed, convert directly from the original source to that rate in
one conversion; do not repeatedly resample an intermediate WAV. Neither the
CLI nor the library implicitly changes the rate.

## Frame and stream integration

The caller owns the validated stream header, packet storage, and output
buffers. Read exactly `DHA_FILE_HEADER_BYTES` before calling
`dha_header_read()`. Frame packet length is the little-endian 32-bit value at
offset 4; bound it by `DHA_FRAME_HEADER_BYTES` and `DHA_MAX_FRAME_BYTES` before
reading the remaining packet. A network or file adapter must additionally
enforce channel order, sequence groups, totals, and final-frame lengths.
Keep the stream tables and packet bytes immutable while decoding, and use
separate input and output storage. CRC checks detect damaged files.

```c
#include "dha_codec.h"

/* Header bytes and one complete packet were supplied by the transport. */
dha_stream_info info;
int16_t pcm[DHA_MAX_FRAME_SAMPLES];
size_t produced = 0;
int status = dha_header_read(&info, header_bytes, DHA_FILE_HEADER_BYTES);
if (status == DHA_OK) {
    status = dha_decode_frame(&info, packet, packet_bytes,
                              pcm, DHA_MAX_FRAME_SAMPLES, &produced, NULL);
}
/* Consume pcm[0..produced) only after a successful complete-frame decode. */
```

For incremental output, initialize a caller-owned `dha_decoder` with
`dha_decoder_init()` and call `dha_decoder_next()` until `DHA_DONE`. Every
`DHA_OK` produces one PCM16 sample; `DHA_DONE` produces none. Finish the frame
even when the advertised sample count has been reached: malformed tails may
be rejected at the last sample or final completion. Do not treat partially
decoded output as an authenticated complete frame.

For encoding, initialize `dha_stream_info` with `dha_stream_default()` and
`dha_encoder_options` with `dha_encoder_default()`. Pass one channel's
contiguous PCM16 samples, its channel number, and the shared group sequence
to `dha_encode_frame()`. Store its returned frame kind and size as actual
results; PCM16 fallback is supported and transparent to the decoder.
Default search is beam64, eight gain candidates, two-sample lookahead and
rate penalty82. These are per-call options, not mutable library globals.
Set `allow_pcm_fallback=0` to require predictive DHA, even when its packet
would be larger than PCM; an infeasible trajectory then returns an error.
`dha_pack_frame()` packages an existing valid predictor trajectory without
running an audio search.

For a continuous firmware trajectory, call `dha_encode_trajectory()` with an
explicit reconstructed `initial` state and caller-owned q/symbol/gain arrays.
Pass the returned final state into the next call. Each nonfinal call must
contain a multiple of256 samples; gain and search decisions then match one
larger call at the same block boundaries. This API never chooses PCM fallback.
The browser uses flat initial history at the first input level, avoiding an
artificial zero-to-signal transition without fading or changing the input.
The public API also permits another valid initial state when the consuming
decoder supports it. q values are exact predictor outputs, before output
rounding, and `dha_pack_frame()` can frame that same path without another
lossy search.

## Browser C/WASM adapter

The website imports [web/codec.js](web/codec.js), which wraps the C search and
decoder compiled into [wasm/codec.wasm](wasm/codec.wasm). The checked-in module
needs no build tool on the visitor's computer. Rebuild it with Emscripten:

```sh
node audio/lib/dha-codec/src/build_web.mjs --emsdk /path/to/emsdk
node --test audio/lib/dha-codec/tests/web-codec.test.mjs
```

[wasm/build.json](wasm/build.json) records compiler flags and source/artifact
hashes. `EMSDK` or `--emcc` may be used instead of `--emsdk`.

```js
import {createAudioCodec} from './web/codec.js';
const codec = await createAudioCodec();
const encoded = await codec.encode(monoPCM16At25000Hz, {
  beamWidth: 16, gainCandidates: 4, lookahead: 1, ratePenalty: 82,
  onProgress: ({completed, total}) => showProgress(completed / total),
  signal: abortController.signal
});
const decoded = codec.decode(encoded.dhaf);
const retained = codec.truncate(encoded.dhaf, firmwareStoredSamples);
```

Each result owns detached arrays: signed `q`, residual `symbols`, block
`gains`, the signed1024-byte `model`, interleaved512-byte `ans`, rounded PCM16
`pcm`, and the framed `dhaf` bytes, plus `sampleRate` and the explicit
`initial` predictor state. Encoding expects mono25 kHz PCM16 and performs no
resampling or level adjustment. Run the adapter in a Worker; the encoder
yields between256-sample C search blocks and checks cancellation there.
The DHAF frames contain up to4096 samples, with each stored initial state
carrying the preceding frame's final history. Loading checks the complete
file, CRCs, packet order, ANS termination and predictor continuity.

The browser ROM path accepts mono predictive DHAF with flat first history;
it rejects PCM16 fallback and independently reset frames explicitly. The
general C library retains its broader independent-frame/stereo support.
`truncate()` repacks an authenticated prefix, including a partial last gain
block, without another lossy encode. DHAF remains a host container; the
website's separate firmware builder converts its trajectory into the
compiled-first Z80 wire and performs the actual64 KiB capacity check.
The builder accepts `output: 'pdm'` (175 kHz on D0, default) or
`output: 'r2r'` (25 kHz PCM8 on D0..D7), preserving the same decoded samples.
See [firmware compilation](web/FIRMWARE.md) for output-specific ROM budgets,
timing, API options and native/WASM execution proofs.

`dha_pdm_next()` is an optional one-bit first-order accumulator primitive for
an unsigned PCM8 value. Initialize `dha_pdm_state.accumulator` to zero once
and preserve it across frames or playlist repeats. It produces one bit per
call; oversampling and audio-device scheduling belong to the application.
For the four-pulse output used by the 100 kHz Z80 variant, hold each 25 kHz
PCM8 target constant for four calls, and schedule their bits 10 microseconds
apart. This changes the output carrier without resampling or expanding the
compressed file. Keep one accumulator per output channel; do not reset it
when starting a new DHAF frame.

```c
/* Initialize once, outside the frame/sample loops. */
dha_pdm_state pdm = {0};
/* For each decoded mono PCM16 sample: */
uint8_t target = (uint8_t)(((int32_t)pcm16 + 32768) / 256);
uint8_t pulses[4];
for (unsigned k = 0; k < 4; ++k)
    pulses[k] = dha_pdm_next(&pdm, target);
/* An audio/device adapter emits pulses[] at uniform 10 us intervals.
   Calling the primitive four times does not itself provide that timing. */
```

## Verification

[Documentation verification](reports/documentation-verification.json) checks
unchanged C tokens after adding comments, the existing three CTest suites,
reproducible standalone figures, local links and complete static export of
the illustrated guides and their assets.

[Recorded verification](reports/verification.json) covers MSVC19.51 on Windows,
shared and decoder-only static builds, installed C++ consumers, C tests, CLI
files and the complete saved Z80 trajectory. No analog or SNR/SER assessment
is part of this library integration.

C tests cover frame lengths1/2/255/256/257/4096, the predictor/ANS boundary
conditions, CRC/truncation/terminal errors, unchanged output on failed whole-
frame decode, mono/stereo metadata, PCM fallback and the PDM accumulator.
The command-line integration suite runs automatically under CTest when a
Python3 interpreter is available. Python is only a test dependency.

The optional repository compatibility test reads the retained Z80 NPZ fixture
with NumPy, packages all375000 samples into92 independent frames and checks
every reconstructed q, difference, gain, ANS state and physical R2R code.
It also compares750001 continuous PDM outputs with the published native/WASM
certificate. The resulting standalone file is67838bytes versus750000bytes
of mono PCM16, including all headers and tables. This is lossless repackaging
of the already selected lossy trajectory, not a new quality measurement.

```sh
python audio/lib/dha-codec/tests/z80_compat.py \
  --library build/dha-codec/Release/dha_codec.dll \
  --replay audio/music/sea-foam/recorded-difference-history/r2r/25k/artifacts/replay.npz \
  --output build/audio/dha-codec/z80-compat
```

Use the platform's shared-library filename, such as `libdha_codec.so`, on
other systems. Runtime sources and tables are entirely inside this directory;
the optional compatibility test is the only part that uses a repository fixture.
