# LZW and LZH on the five-level fixture

2026-09-30. Follow-up requested by the user after `e394688`.
Reuse the exact 323940 video-only bytes, 192 frames and 21 independent
blocks of at most 15872 bytes from the earlier comparison. No new movie
conversion, native player code or TRD build; native instruction delta is 0 T.

## Results

All sizes include the same four-byte block headers. GIF and LHA archive
wrappers are used only for independent verification and are not counted.
The standard `.Z` candidate retains its three-byte header per block.

| Codec | Stream bytes | Sectors | Versus ZX0 |
|---|---:|---:|---:|
| Existing ZX0 | 148971 | 582 | baseline |
| Existing LZSA2 | 154956 | 606 | +4.02% |
| LZW, 10-bit limit, clear on full table | 185256 | 724 | +24.36% |
| LZW, 11-bit limit, clear on full table | 173571 | 679 | +16.51% |
| LZW, 12-bit limit, clear on full table | 166730 | 652 | +11.92% |
| LZW, standard ncompress with 16-bit limit | 162770 | 636 | +9.26% |
| LZH, LHA LH5 | **145725** | **570** | **-2.18%** |

LH5 saves 3246 bytes and 12 sectors versus ZX0, or 9231 bytes (5.96%) and
36 sectors versus LZSA2. It is 863 bytes larger than the previous DEFLATE-9
candidate. LZW is larger even with the reference compressor's larger table.
These are fixture-specific results, not conclusions about every possible
LZW variant or input.

## Formats and verification

- Bounded LZW uses an 8-bit alphabet, 9-bit starting codes, CLEAR=256 and
  EOI=257, with LSB-first GIF-compatible packing. Reset one slot before the
  configured table fills; this keeps early clears compatible with an
  independent standard GIF decoder. The limits are 10/11/12 bits. The
  encoder uses the usual longest-known-phrase dictionary construction.
- Verify every bounded LZW block with Pillow's GIF decoder. Its temporary
  image wrapper carries a grayscale palette so that recovered index bytes
  equal the original video bytes, not a visual approximation.
- The second LZW implementation is [ncompress](https://github.com/valgur/ncompress)
  1.0.2, using standard `.Z` framing with header `1f9d90` (block mode,
  maximum 16 bits). Check every block with both ncompress and independent
  7-Zip decompression.
- LZH is a family: this experiment tests **LH5**, an 8192-byte sliding
  dictionary plus Huffman coding. Use the existing
  [libdragon host encoder](https://github.com/DragonMinded/libdragon/blob/e356bf3f56f7afbf7e5246329562f145965cfdfc/tools/common/lzh5_compress.c),
  derived from [LHa for UNIX](https://github.com/jca02266/lha).
  The exact pinned source, host adaptation and binary hashes are recorded.
  Decode with independent `lhafile` 0.3.1, checking the LHA CRC as well as
  the full byte sequence. Do not confuse LH5 with LH1 or other LZH variants.
- MSVC adaptation only completes two forward array declarations with their
  existing size, 1019, and suppresses the GCC-only function annotation.
  Compression logic is unchanged. The host adapter rejects truncated,
  unsuccessful or incompressible results rather than reporting them as LH5.
- All **105 video block round trips**, **30 bounded-LZW boundary checks**
  and **3 extra LH5 cases** pass. Boundary checks cover code-width changes,
  dictionary resets, tiny/random blocks, constant runs and repeated alphabets.

## Memory and delivery decision

A simple native LZW dictionary with 16-bit prefix and 8-bit suffix tables
would cost 3072/6144/12288 bytes for 10/11/12-bit limits, before phrase
expansion, input/output, bit-reader state and code. These are layout estimates,
not measurements of a built Z80 decoder. A fixed full 16-bit table would
cost 192 KiB; bounded short blocks could support a smaller specialized
allocation. No such implementation is assumed in this comparison.

LH5 needs the 8-KiB history plus Huffman tables, bit-reader state and code.
It avoids LZMA's range arithmetic, but its variable-length symbol decoding
still needs a native timing test. Both codecs require their own resumable
state and memory ownership proof; their output cannot be assumed to share
input safely just because the previous ZX0/LZSA2 layouts did.

**Decision:** reject the tested LZW settings for the disk-capacity objective.
Keep LH5 as a small storage gain, not an accepted player replacement. No
Z80 cycles, actual fps or 128-KiB allocation were measured. With only 36
fewer sectors than LZSA2, its extra CPU work could easily consume the saving.
Retain packet-copy reduction as the next implementation task. A future LH5
probe must first count native decode work, then verify real delivery; the
stored data alone cannot pass the 8 1/3-fps requirement.

## Reproduction

Scripts: [prepare_lzh5_probe.py](prepare_lzh5_probe.py),
[host adapter](lzh5_probe.c), [bounded LZW](lzw_probe_codec.py),
[comparison](probe_lzw_lzh.py). Measurements:
[lzw_lzh_probe.json](lzw_lzh_probe.json),
[compressed streams](lzw_lzh_evidence).

```text
python -m pip install --target .tmp/legacy-codec-packages --only-binary=:all: --no-deps ncompress==1.0.2 lhafile==0.3.1
python toolkit/prepare_lzh5_probe.py --output .tmp/legacy-codecs/src --vcvars "C:/Program Files/Microsoft Visual Studio/18/Community/VC/Auxiliary/Build/vcvars64.bat"
# PYTHONPATH needs toolkit, .tmp/legacy-codec-packages and Pillow (measured 12.3.0).
python toolkit/probe_lzw_lzh.py --encoder .tmp/legacy-codecs/src/lzh5_probe.exe --sevenzip "C:/Program Files/7-Zip/7z.exe" --work .tmp/legacy-codecs/run --output toolkit/lzw_lzh_probe.json --artifacts toolkit/lzw_lzh_evidence
```

The preparation script fetches only two files from pinned libdragon commit
`e356bf3f56f7afbf7e5246329562f145965cfdfc`. Set `--vcvars` to the installed
compiler environment. Dependencies, compiled host code and source downloads
remain in temporary storage; reproducing scripts, hashes and evidence remain
in Git. Existing image quality and AY are preserved through exact bytes.
