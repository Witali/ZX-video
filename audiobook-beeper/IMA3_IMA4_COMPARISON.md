# IMA3 and IMA4 comparison and shared improvements

Reviewed 2026-10-04 against `main` at `6ce7f55`. This records the current
algorithms and proposed transfers; it does not change a converter, player
or disk. The strongest first step is to bring the existing waveform search
and overlapping search windows into the automatic IMA4 workflow. A common
host pipeline can retain separately optimized Z80 extraction routines.

## Shared decoding algorithm

Both modes use the same 89-entry IMA step table, signed 16-bit predictor,
index adaptation and shift/add rounding in [ima_codec.py](ima_codec.py).
The project's IMA3 is a restricted four-bit IMA alphabet, not a drop-in
standard three-bit WAV stream. Eight even nibbles are represented by three
bits; IMA4 permits all sixteen nibbles.

For a stored code `c` and bit width `bits`, the shared mathematical model is:

```text
n = c << (4 - bits)                 # IMA3: even nibble; IMA4: unchanged
step = STEPS[index]
delta = (step >> 3)
      + ((n & 4) ? step : 0)
      + ((n & 2) ? (step >> 1) : 0)
      + ((n & 1) ? (step >> 2) : 0)
predictor += (n & 8) ? -delta : delta
index = clamp(index + INDEX[n & 7], 0, 88)
```

The host rejects predictor overflow before release. The Spectrum reads
precomputed signed deltas and next-row pointers instead of evaluating this
formula or performing saturation checks in the playback path. The shift
above is a mathematical mapping, not a requirement for an extra Z80
instruction or an expanded IMA4 buffer. Initial predictor/index are 0/0;
the silent guard returns the stream to that state.

In both modes the reconstructed amplitude and saved feedback state select
PDM output routines. Decoding is interleaved with their OUT instructions.
Audio stays compressed in RAM; neither mode needs a complete PCM or PDM
buffer. See the [decoding diagrams](IMA3_PDM_PIPELINE.md).

## Current differences

| Property | Current IMA3 profile | Historical IMA4 profile |
| --- | --- | --- |
| Packing | Eight codes in three bytes, least significant bits first | Two nibbles per byte, low nibble first |
| Payload at nominal 8 kHz | 24000 bit/s, 3000 bytes/s | 32000 bit/s, 4000 bytes/s |
| Codes per IMA index | 8 | 16 |
| Decoder table | 89 x 8 x 4 = 2848 bytes | 89 x 16 x 4 = 5696 bytes |
| Decoder placement | All 89 rows in uncontended bank 2 | 25 frequently used rows in bank 2; 64 in contended bank 5 |
| PDM amplitude grid | 128 levels, supported control levels 4..123 | 64 levels |
| PDM implementation | Shared short SECOND prefixes and eight extraction tails | Nibble extraction within the four-bit packet routines |
| Ordinary native work | Eight phases, mean 427.375 T/sample | 423 T/sample |
| Page and bank extras | +14 / +140 T | +14 / +140 T |
| Maximum resident payload in current layouts | 94458 bytes / 251888 prepared samples | 93440 bytes / 186880 prepared samples |
| Automatic PC search | Measured waveform objective; horizons 128/256, commit 64 | PCM beam width 32, followed by measured clock compensation and re-encoding |
| Disk workflow | Sequential RAM-sized parts; one disk by default or whole-track series | One looping RAM excerpt |
| Restartable conversion | Has checked stage caches and resume | No matching stage-resume workflow |

The capacity figures include guard/padding, not only audible input. IMA3
uses 25% fewer payload bytes for equal sample counts; IMA4 needs 33.3% more
than IMA3. Code, tables, screens, stack, TR-DOS workspace and sector padding
are additional costs. The three-bit phases are
`417, 413, 458, 413, 417, 446, 409, 446` T. Their mean exceeds IMA4 by
4.375 T/sample. These counts exclude ULA waits, ROM and disk latency and
do not describe a uniform physical PDM clock.

Sources: [three-bit builder](ima3_direct_player.py),
[four-bit builder](direct_player.py), [compact allocation](IMA3_MEMORY.md),
[four-bit workflow](IMA4_CONVERTER.md), and [sequential disks](IMA3_SERIES.md).

## Transfers with the strongest evidence

### Share the waveform search and overlapping windows

The generic [waveform encoder](ima_waveform_encoder.py) already accepts
either alphabet through `allowed_codes`, plus `commit_size` and profile
control bounds. This is shared capability, not a missing codec. The gap is
that [the automatic IMA4 converter](convert_audio.py) still calls the PCM
beam encoder, while [the IMA3 workflow](convert_ima3_audio.py) invokes the
waveform search with overlapping windows.

A separate [complete IMA4 experiment](WAVEFORM_IMA.md) already improves
18.994103 to 21.010690 dB on the same 186880-sample control, with both cold
Fuse loops checked. Ordinary CPU cost stays 423 T/sample. Promote that
method into the automatic IMA4 candidate search, then compare full-window
commits with the IMA3-style 64-sample commits. The overlap implementation
already carries the accepted prefix's predictor, index, PDM and filter
states; its additional benefit on a real IMA4 disk remains to be measured.

This transfer adds no decoding instructions. It can change data-dependent
ULA delays, so every new stream still needs fresh phase calibration and
full execution checks. Reuse the fixed source, filter and playback clock;
do not copy an IMA3 timing trace to qualify an IMA4 disk.

### Reuse the recent PC acceleration for both alphabets

Local branch checkpoint `de6d02b`, separate from this document's `main`
baseline, accelerates `ima_waveform_encoder.py` with backpointers, reduced
temporary arrays and an optional native kernel. Its tests include both
8-code and 16-code alphabets. The measured 4.073x native speedup belongs
to the saved IMA3 benchmark; it is not an IMA4 throughput measurement.
This work should be reused rather than implemented again when the common
waveform workflow is integrated. Inspect its saved report with
`git show de6d02b:audiobook-beeper/experiments/waveform-speed/README.md`.

The related local checkpoint `fb29e4a` adds prepared-PCM handling to IMA4.
Reuse it to compare identical normalized samples without normalizing the
source again. Neither checkpoint is merged as part of this documentation
change, and neither automatically replaces IMA4's current PCM search.

### Carry IMA4 amplitude freedom into a common player family

IMA4's additional codes offer finer choices of predictor increments. A
[saved control](experiments/ima-3bit-residual/README.md) on 4.096 seconds of
the same speech and the same hypothetical IMA3 pulse timeline scores
21.600309 dB with eight codes and 23.899006 dB with sixteen. This is a host
model result, not an executable four-bit disk on that timeline. It supports
investigating an IMA4 variant of the newer PDM architecture; it does not
establish an achievable release SNR or identify the former audible flutter.

Enabling all sixteen codes requires four-bit storage and the larger decoder
table. It cannot retain the three-bit bitrate without introducing another
coding scheme. For the user-accepted IMA3 playback status, use the later
[converter checkpoint](CONVERTER.md); the residual study is historical.

## Useful transfers that need new player verification

| Proposed transfer | Expected benefit | Cost or unresolved constraint |
| --- | --- | --- |
| IMA3's 128-level PDM grid and restricted feedback states to IMA4 | Finer amplitude control; potential reconstruction gain | New table contents/layout and amplitude-selection instructions; gain is unmeasured |
| IMA3's uncontended IMA rows to IMA4 | Remove decoder-index-dependent memory contention | The 64 currently contended IMA4 rows occupy 4096 bytes to relocate, before accounting for reused/freed gaps |
| IMA3's aligned code-gap allocation to IMA4 | Recover unused fixed-bank bytes | IMA4 rows need 64-byte slots, versus 32 for IMA3; the saved 1024-byte IMA3 gain cannot be assumed |
| IMA3's shared SECOND prefixes to IMA4 | Potentially reduce repeated output code and free table space | Register lifetimes, packet-entry order, extraction and OUT spacing differ; copying routines is insufficient |
| IMA3's sequential loader, progress and stage verification to IMA4 | Longer recordings and matching converter options | Recalculate four-bit RAM/sector capacity and controller handoff; loading pauses remain |

The simpler IMA4 nibble reader is useful as a distinct extraction backend.
It cannot replace IMA3's reader without spending the extra 33.3% payload
memory or adding an expansion pass. Conversely, a single runtime reader
that branches on bit width at every sample has no demonstrated advantage
over build-time specialization.

## Proposed common architecture and implementation order

Use one profile description for bit width/alphabet, packing, IMA row size,
PDM grid/bounds, memory layout, extraction schedule and verification model.
Share source preparation, mathematical transitions, waveform-search engine,
reporting and disk-series orchestration. Generate a specialized player for
the chosen profile at build time, with no per-sample codec selector.
Keep the currently verified timing models separate until a measured change
justifies replacing either one.

1. Consolidate shared host code while reproducing existing streams and
   player binaries exactly. Reuse the local acceleration and prepared-PCM
   work with its recorded evidence.
2. Add automatic waveform search with overlap to IMA4, retaining its current
   player. Compare the same prepared speech and normalized music, including
   per-window errors; select only fully verified candidates.
3. Extend the common disk-series workflow to IMA4 with explicit capacity and
   handoff checks. Keep both modes independently bootable.
4. Investigate one IMA4 PDM/table-layout change at a time. Count absolute
   T-states and deltas for every affected path; measure ULA and disk costs
   separately. Do not bundle a layout experiment into a pure host refactor.

Each player candidate needs complete native/cold-Fuse output and state
checks, every bank/part transition, EOF or two full preview loops, loading
progress, fresh audio capture and the existing +/-2% speed gate. Report an
unmet SNR target explicitly. Host scores only rank candidates; recordings
and physical hardware have their own verification scope.

This review reuses existing code and reports; it adds no new performance,
quality or hardware measurement. Player deltas for this documentation-only
change are 0 T in both modes. Preserve the byte-exact
[YouTube-linked historical IMA4 disk](../ZX-audiobook-IMA-ADPCM-direct-test.trd)
at its current path even if a newer common implementation supersedes it.
