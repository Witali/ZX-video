# Modern outer codecs on the five-level video fixture

2026-09-30. User requested LZMA, bzip2 and other current codecs, allowing
more author-side compression work. This overrides the brief's prohibition
on an unsolicited codec sweep for this bounded assessment only.

## Measured scope

Baseline `11778ed`: the same 192-frame montage, exact 323940 video-only
bytes, 21 independent blocks of at most 15872 bytes. AY, frame coding,
dictionary and native pixels are unchanged. Verify every encoded block by
PC decompression and byte comparison: 294 new round trips. Reuse the prior
native ZX0/LZSA2 measurements; no new Z80 code or TRD is built (0 T change).

Count the original four-byte block headers. LZMA, DEFLATE and LZ4 use raw
payloads; the other candidates retain normal codec framing. LZMA/DEFLATE/
Zstd/Brotli use a 16-KiB dictionary/window limit. LZ4 references cannot cross
the independent source block. Fixed codec properties are assumed in player
code; new bootstrap bytes are excluded. No external trained dictionaries.

## Results

| Codec / encoder setting | Stream bytes | Sectors | Versus ZX0 |
|---|---:|---:|---:|
| Existing adapted Fast ZX0 | 148971 | 582 | baseline |
| Existing LZSA2 | 154956 | 606 | +4.02% |
| LZMA1 preset 0, lc=3 | 147096 | 575 | -1.26% |
| LZMA1 preset 9 extreme, lc=3 | 133716 | 523 | -10.24% |
| LZMA1 preset 9 extreme, lc=0 | 133084 | 520 | -10.66% |
| LZMA2 preset 9 extreme, lc=0 | 133115 | 520 | -10.64% |
| bzip2 level 1 | 146779 | 574 | -1.47% |
| bzip2 level 9 | 146779 | 574 | -1.47% |
| DEFLATE level 1 | 159005 | 622 | +6.74% |
| DEFLATE level 9 | 144862 | 566 | -2.76% |
| LZ4 default | 218572 | 854 | +46.72% |
| LZ4 HC level 12 | 183448 | 717 | +23.14% |
| Zstandard level 1 | 152573 | 596 | +2.42% |
| Zstandard level 19 | 137607 | 538 | -7.63% |
| Brotli quality 1 | 161247 | 630 | +8.24% |
| Brotli quality 11 | 132043 | 516 | -11.36% |

Negative means smaller. Best LZMA saves 14.11% against the current faster
LZSA2; Brotli saves 14.79%. These are video-only savings on this montage,
not total disk savings or a full-movie extrapolation.

## Decoder feasibility

**LZMA:** strongest small-state candidate in this comparison. With lc=0,
lp=0 the current SDK probability array estimate is
`2 * (1984 + 768) = 5504` bytes, versus 16256 bytes with lc=3. Adding the
16384-byte history gives 21888 bytes before other state/code/input buffers.
History may reuse the output buffer; do not count it twice. Shared input/
output overlap and model placement still need proof in our bank layout.
The SDK range decoder performs 32-bit shifts, comparisons, subtraction and
multiplication for probability decisions. This is a serious Z80 cost risk,
not a measured rejection. Sources: [SDK](https://www.7-zip.org/sdk.html),
[decoder arithmetic and model count](https://raw.githubusercontent.com/ip7z/7zip/main/C/LzmaDec.c),
[16-bit probabilities and dictionary interface](https://raw.githubusercontent.com/ip7z/7zip/main/C/LzmaDec.h).

**bzip2:** level changes the maximum block size. Both tested levels give
the same length because every input fits even the smallest block. The
standard decoder allocates about 500 KB at level 1, or 350 KB in its slower
small-memory mode, exceeding the entire 128-KiB machine. A specialized
decoder with tighter bounds for these short blocks could reduce allocation;
that would be separate implementation work, with unmeasured cost. Reject
such work for the observed 1.47% saving. [Official memory table](https://sourceware.org/bzip2/manual/manual.html#memory-management).

**Brotli:** best observed size, but its standard static word dictionary
alone is 122784 bytes. This experiment did not count dictionary references
or prove they can be omitted. A restricted encoder/decoder could differ;
its size and timing would require another comparison. Do not treat a
16-KiB history limit as the decoder's total memory requirement.
[Dictionary source](https://raw.githubusercontent.com/google/brotli/master/c/common/dictionary.c).

**Zstandard:** saves 7.63%, but adds Huffman/FSE decoding and tables. The
installed desktop reference reports a 95968-byte decoder context before
stream work. That is an implementation measurement, not an irreducible
Z80 memory bound. No reduced Z80 port was measured.
[Format and implementation](https://github.com/facebook/zstd).

**LZ4 HC:** directly matches the idea of expensive encoding with simple
decoding; its block format remains compatible with ordinary LZ4. However,
its 23.14% increase over ZX0 adds 135 sectors, so it is unattractive for
the capacity target. [Official HC description](https://github.com/lz4/lz4).

**DEFLATE:** only 2.76% below ZX0, with Huffman decoding and extra state.
No new resumable native implementation or cadence result is claimed.

## Decision and speed budget

Do not replace the working player on the basis of PC compression results.
Higher encoder effort is worthwhile: LZMA extreme saves roughly 14 KB more
than its preset 0 without enlarging the selected history. A low preset
does not remove the format's decoder operations. PC decode timings in the
JSON are one-run observations, never scaled into Z80 T-states.

For a rough triage estimate, the LZSA2 run averages 31303 elapsed T per
runtime read window. Saving 86 sectors with LZMA allows about 2.69 million
additional decoder T, giving approximately 22.54 million T total, versus
19.84 million T for LZSA2. This is only a heuristic break-even calculation:
sector position, rotation, IRQ, queues, producer and paging would change.
It does not predict fps or relax the zero-late-frame release requirement.

Retain LZMA1 lc=0 / 16-KiB history as the most interesting future small
native feasibility probe: first count actual range-decoder operations on
one representative block and budget Z80 operations/bank placement. Stop if
it cannot plausibly beat the measured delivery budget. Defer integration
of LZMA/Brotli/Zstd; reject bzip2 and LZ4 for this fixture's measured tradeoff.
Continue the already identified packet-copy optimization first; it targets
known CPU work without adding decoder complexity or changing image quality.

## Reproduction

[Script](probe_modern_codecs.py), [complete measurements](modern_codec_probe.json),
[compressed candidates](modern_codec_evidence). Input archive hashes are
checked against [the existing report](row_lzsa_optimization.json).

```text
python -m pip install --target .tmp/codec-probe-packages --only-binary=:all: --no-deps zstandard==0.25.0 lz4==4.4.5 brotli==1.2.0
# Include .tmp/codec-probe-packages and toolkit in PYTHONPATH.
python toolkit/probe_modern_codecs.py --output toolkit/modern_codec_probe.json --artifacts toolkit/modern_codec_evidence
```

Measured Python 3.12.14, zlib 1.3.2, Zstandard 1.5.7. The JSON includes
binding versions, options, per-block hashes, aggregate sizes and limitations.
This experiment is not a release: no native decoder, in-place proof, full
128-KiB allocation or real disk/IRQ/ULA cadence test exists for the new codecs.
