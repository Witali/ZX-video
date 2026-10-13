# Lossless six-voice control storage

Measured 2026-10-13 in `.worktree/six-voice-clicks`, branch
`codex/six-voice-clicks`, from `593301b6`. The user reports good overall sound
with some residual squeaking/ringing and asks for the compressed command size.
Reuse the exact accepted spectral candidate's O. Henry source[60,90) controls;
no refitting, waveform changes, player changes or new quality search.

## Actual sizes for the complete 30 seconds

All sizes include a 36-byte model header. Compressed files also include four
bytes per block; codec framing is included. KB/MB below use decimal units.

| Representation | Bytes for 30 seconds | Linear minute estimate | Linear hour estimate |
| --- | ---: | ---: | ---: |
| Uncompressed 16-byte control frames | 24,036 | 48.1 KB | 2.88 MB |
| Columnar DEFLATE, one 30-second block | 18,261 | 36.5 KB | 2.19 MB |
| Columnar ZX0, one 30-second block | **17,897** | **35.8 KB** | **2.15 MB** |
| Columnar ZX0, independent 1-second blocks | **19,853** | **39.7 KB** | **2.38 MB** |
| Columnar XZ/LZMA, one 30-second block | 16,180 | 32.4 KB | 1.94 MB |

The original mono PCM16/44100-Hz WAV occupies 2,646,044 bytes. The existing
NumPy NPZ archive occupies 21,465 bytes; it is not a playback command format.
Minute/hour figures scale this excerpt, including repeated headers. Other
speech/music was not measured and may compress differently. Player/synthesizer
code and disk directory/sector rounding are excluded.

Retained prototype command files (each contains our header and framed codec
blocks, so it is not a bare ZX0/XZ file):

- [30-second ZX0 block](evidence/columnar-1500.zx0)
- [Thirty independent 1-second ZX0 blocks](evidence/columnar-50.zx0)
- [30-second XZ/LZMA block](evidence/columnar-1500.xz)
- [All 18 measurements, checks and hashes](evidence/report.json)

ZX0 with one-second blocks gives approximately 662 bytes/second including
framing and uses at most 950 decoded control bytes per block. The single
30-second columnar block decodes to 28,500 bytes. These are storage/control
buffer sizes, not total decoder/renderer memory or Z80 timing measurements.

## What is stored and checked

At each of 1500 updates (50 Hz), preserve six 12-bit periods, six 4-bit level
codes, six 2-bit shape selections, six 2-bit tone/noise routes, and one shared
5-bit noise period: 125 bits per update. A byte-aligned frame occupies 16
bytes, with three zero padding bits. Continuous bit packing alone would occupy
23,438 payload bytes; it was calculated, not separately compressed/tested.

The columnar layout uses 19 byte sequences: six low period bytes, six high
period nibbles stored in bytes, six packed level/shape/route bytes, and noise.
Each block stores those sequences consecutively. This uses more raw bytes but
compresses better than mixed 16-byte frames on this excerpt. The delta layout
subtracts successive periods modulo4096 and XORs control/noise bytes, starting
from zero per block; it worsens whole-block compression and is rejected.
None of the layouts discards muted-voice frequency changes or inaudible noise
clock changes, because they can affect phase at a later audible update.

The 36-byte little-endian header uses `<4sBBHIIIdfHBB`: magic `S6P1`, layout,
flags (aligned triangle/DC compensation in low two bits; codec in upper bits),
update Hz, tick count, oscillator clock, output sample rate, float64 gain,
float32 transition milliseconds, uint16 bandwidth Hz, oversampling, model
version. Each compressed block has `<HH>` decoded length and coded length.
The model version implies six voices, the existing oscillator/noise initial
conditions, shape meanings and renderer. It is a measurement prototype, not
a newly supported converter/player interchange format.

Every combination of three layouts, three codecs (DEFLATE9, XZ/LZMA6 and
optimal ZX0 v2) and two block lengths (1500/50 updates) is complete. All
codec roundtrips and independent saved-stream decodes restore all 1500
control states and exact model metadata. A full 1,323,000-sample synthesis
from recovered controls/header settings produces a byte-identical WAV.
Source-control/WAV, producer and encoder hashes are retained. There is no
source PCM in these command files and no additional sound degradation.

## Compatibility and reproduction

The current sound uses six selectable square/triangle/sine voices, smooth
4-ms transitions and a balanced mixer. One real AY has three square-wave
tone channels; even two AYs cannot directly replay all these model features.
These sizes apply to the existing hypothetical six-voice synthesizer. Actual
AY/TurboSound storage and sound quality require a separate fit and measurement.
No real-chip playback, native parser, Z80 decoder timing or release TRDs are
implemented or qualified by this storage probe. Existing native code is
unchanged, so no player hot-path cycle delta applies.

From the task worktree with NumPy and the project's ZX0 v2 executable:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
python ay-converter/analysis/six_voice_storage/measure.py --output .tmp/storage-reproduction --zx0 C:/Work/ZX-video/.worktree/compression/.tmp/ZX0/win/zx0.exe
```

Use a new output directory. The script retains all 18 generated streams and
the JSON report. Only the three useful comparison streams are archived here;
all other files can be reproduced. The bounded storage request is complete.
