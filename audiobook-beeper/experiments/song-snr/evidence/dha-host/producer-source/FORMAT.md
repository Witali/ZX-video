# DHAF version1

DHAF stores the existing DHA1 difference predictor and five-symbol tabled ANS
in an independent-frame PC container. The arithmetic, default tables and PCM8
rounding match the selected Z80 R2R/PDM firmware. The file is **not** a64-KiB
ROM or the old monolithic `DHA1` research container. Frame sizes and gain
placement replace the board's compiled-first sample and timed gain prefetch.
No assembler, ROM emitter or external replay file is needed for playback.

For the algorithm and visual explanations, see [the illustrated guide](ALGORITHM.md)
or [его русскую версию](ALGORITHM.ru.md). This document specifies the bytes;
the guide explains how the encoder selects and the decoder reconstructs them.

All multibyte integers are little-endian. Signed values use two's complement.
There are no native-struct dumps, implicit padding or floating-point fields.

## File header:1572 bytes

| Offset | Bytes | Meaning |
| ---: | ---: | --- |
| 0 | 4 | ASCII `DHAF` |
| 4 | 2 | Version1 |
| 6 | 2 | Header length1572 |
| 8 | 4 | Sample rate1..192000 Hz, preserved without resampling |
| 12 | 2 | Channels1 or2 |
| 14 | 2 | Maximum samples per frame per channel1..4096 |
| 16 | 8 | Total sample frames per channel; UINT64_MAX means unknown |
| 24 | 8 | Reserved, all zero |
| 32 | 1024 | Four signed8 predictor rows |
| 1056 | 512 |256 ANS entries: `(symbol<<4)|N`, base |
| 1568 | 4 | IEEE CRC32 of bytes0..1567 |

CRC32 uses polynomial0xEDB88320, initial register0xFFFFFFFF and final XOR
0xFFFFFFFF, equivalent to the common `crc32(data)` result.

Model row0 uses `abs(q)&255`, with index0 representing virtual +256.
For q=0 its correction is zero; for negative q the fetched correction is
negated. Row0 cannot contain-128. Rows1..3 use index`difference+128` and
their index128 must be zero. The default model's byte SHA256 is
`70582ffa6ec234742248acd008bda13795f5243a884681f496af87bd6609260f`.
The default ANS book has frequencies176/36/36/4/4; packed table SHA256 is
`af7cef130c9edf04d1da1944678314a4cd5e2c7d6957ded64f0cc5f028fa7ce8`.
Tables are carried in the file; a decoder must not substitute its defaults.

Each entry has symbol0..4, N0..6 and `base+2^N<=256`. For every symbol,
the ranges`[base,base+2^N)` across its entries must cover0..255 exactly
once. This guarantees a complete encoder inverse and bounds every lookup.

## Frame header:32 bytes

| Offset | Bytes | Meaning |
| ---: | ---: | --- |
| 0 | 4 | ASCII `DHF1` |
| 4 | 4 | Entire packet length, including32-byte header |
| 8 | 4 | Sequence group, starting0 |
| 12 | 2 | Samples in this channel's frame1..header maximum |
| 14 | 1 | Channel0..channels-1 |
| 15 | 1 | Kind:0=PCM16,1=DHA |
| 16 | 2 | Initial q, signed16 |
| 18 | 3 | Initial d1,d2,d3, each signed8 |
| 21 | 1 | Initial full8-bit ANS state |
| 22 | 2 | Reserved zero |
| 24 | 4 | Exact payload bit count |
| 28 | 4 | CRC32 of header bytes0..27 followed by payload |

Frames appear in sequence-group order, with channels0..channels-1 in every
group. All channels of a group have the same sample count. Only the last
group may be shorter than the configured maximum. Known total count must
match exactly. Empty audio has a header and no frames. A known total must
fit the32-bit sequence space: at most`2^32*frame_samples`
samples per channel. A reader seeking to
a particular frame can scan packet lengths once and retain byte offsets;
each frame is decodable without any preceding audio frame.

Kind0 payload is exactly`2*samples` bytes of PCM16. Its bit count is
`16*samples`; initial predictor and ANS state are all zero. This preserves
unencodable transients, or short frames that would otherwise become larger.
It is an explicit fallback and is reported by the CLI, not a compression claim.

Kind1 starts from the supplied predictor state. All samples, including the
first, have a residual symbol. There is no compiled first output. Every
256-sample block starts with a5-bit gain1..30. Each sample then consumes
its ANS suffix; bits are MSB first. Decode entry at the current ANS state,
read N bits, and set`state=base+suffix`. Symbols mean`0,+G,-G,+2G,-2G`.
After the last sample the full ANS state must be0 and the cursor must equal
the declared bit count. The final byte has0..7 zero low padding bits;
extra bytes or bits are forbidden. The payload length is`ceil(bits/8)`.

The recurrence uses only four table lookups and integer additions:

```text
p = q + T0(q) + T1(d1) + T2(d2) + T3(d3)
q_new = p + residual
d1_new = q_new - q
d2_new = d1_new - d1
d3_new = d2_new - d2
```

Initial/current/new q and p stay in-256..254; all differences stay in
-128..127, including the state after the last output. Invalid states are
errors, not clipped. PCM16 output preserves the Z80 unsigned8 R2R target:
`(((q+257)/2)-128)*256`. The encoder uses a flat initial history near the
frame's first input sample; the low-level packer can retain an existing
valid trajectory's exact q/differences at a cut.

## PDM is an output option

Compression stores the predicted audio, not expanded PDM bits. To reproduce
the published one-bit output, convert a decoded PCM16 value to unsignedPCM8
and call`dha_pdm_next`. The8-bit accumulator is initialized once and kept
across frame boundaries. Output is1 when`old_accumulator+PCM8>=256`;
the remainder is reduced modulo256. Each call emits one bit. The historical
25 kHz output makes one call per native sample; the 100 kHz output makes four
calls with the same 25 kHz target and schedules the bits uniformly,10us apart.
The compressed representation and decoded PCM trajectory are unchanged.
PDM timing and reconstruction filtering belong to the output adapter; the
primitive itself provides neither a playback clock nor a quality measurement.
