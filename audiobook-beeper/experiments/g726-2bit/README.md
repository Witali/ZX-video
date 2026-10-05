# Exact G.726-16 implementation and Z80 feasibility

Completed 2026-10-05. The user requested two-bit G.726. This experiment
implements the complete codec, provides listening files, and measures a
separately compiled Z80 decoder through three exact optimization rounds.
The implementation passes the functional checks, but **this native port is
too slow for live audio or the allowed preparation time**. No new TRD is
published, and no existing player or release disk is changed.

## Listen and inspect

- [Original prepared speech, PCM16 WAV](evidence/audition/source-preview.wav).
- [After G.726 encoding and decoding, PCM16 WAV](evidence/audition/decoded-preview.wav).
- [Actual packed G.726 stream](evidence/audition/soundtrack.g726).
- [Codec report](evidence/audition/report.json), [complete summary](evidence/summary.json)
  and [native full-stream verification](evidence/native-full.json).

Both WAVs contain **186880 samples / 23.360 s** at mono 8 kHz, with the
same clock, length and gain. The input is exactly the prepared speech used
for the IMA quality study (original WAV SHA256
`6dfd92aac774283ffd96e7549cfa42eaeb833439570ec51f9ca1c69d36bedde0`).
It was PCM8; widening its values to PCM16 does not recover extra precision.

The payload is **46720 bytes**, or **16 kbit/s / 8:1** relative to 373760
PCM16 bytes. The stream is headerless and MSB first; no framing, boot or
checkpoint overhead is hidden in that ratio. PC encoding and decoding
together took0.025166 s here, excluding compiler startup, resampling,
cross-checks and quality measurement.

Raw PCM SNR is **15.767523 dB**. With the project's fixed-clock float64
70-Hz high-pass and two 4.5-kHz low-pass filters, it is **17.077649 dB**.
The filtered measure integrates at768 kHz, compares at44.1 kHz and excludes
100 ms at each edge; no gain or delay is fitted. These are codec-only
measurements. The WAV is not a PDM or Fuse recording, and this does not
achieve the user's hoped-for30 dB.

## Native optimization results

All rows decode the identical8192-sample speech prefix in2048-sample blocks,
including packed-code reads, PCM writes, one reset and state exports.
CPU clock is3546900 Hz. Code size includes linked runtime and constants.

| Round | Change | Mean T/sample | Delta from previous | Code + constants |
| --- | --- | ---: | ---: | ---: |
| 0 | Complete straightforward32-bit port | 127115.239 | baseline | 5024 B |
| 1 | Bounded16-bit Float11 intermediates | 113469.926 | −13645.313 | 4944 B |
| 2 | Bit-length / rounded-product tables | 106288.924 | −7181.002 | 6248 B |
| 3 | Inverse-quantizer table and exact sign simplifications | 70442.908 | −35846.016 | 11123 B |

Round3 saves **56672.332 T/sample, 44.583%**, against round0 on this prefix.
It has100 state bytes and a91-byte observed maximum stack (rounds0..2:92).
Lookup storage is5860 bytes within the code/constants total; it is generic
and contains no recording-specific coefficients or uncompressed audio.

The **complete186880-sample run** takes13159336513 T, averaging
**70415.970 T/sample**. All186880 PCM results and92 full state checkpoints
match the host exactly. The decoder core alone, excluding CALL17 but
including its return sequence, averages70026.769 T and ranges67163..74268 T.
The complete flat execution corresponds to **3710.095 s / 61.835 minutes**
of CPU time for23.36 s of audio. It is159 times the live budget before PDM.

The total live budget at8 kHz is only **443.3625 T/sample**, including
modulation. This particular port fails that budget and the60-second preload
limit by large margins. ROM/disk/ULA/paging/PDM are excluded from this CPU
measurement, so they cannot repair the timing failure. This is not a
physical-hardware measurement or a bound on every possible handwritten
G.726 decoder. Existing IMA/mu-law hot paths have **0 T change**.

## Verification and intermediate attempts

- [Host checks](evidence/host-checks.json): nine8192-sample PCM fixtures,
  exact FFmpeg encoding/decoding in both MSB/LSB packings; all four optimized
  versions agree on PCM and complete state. An additional295936-code stream
  covers every byte, repeated rails and random codes, including257-sample
  streaming chunks. Official ITU conformance vectors were not run.
- [Native full stream](evidence/native-full.json): every sample, state,
  stack and memory bounds; the last short block is checked with its own
  input-read boundary. A [separate8192-code native fixture](evidence/native-edge-cases.json)
  also passes. IX/SP contracts hold; SDCC is allowed to clobber IY.
- Independent Zilog instruction-table audits cover32 speech samples in
  every round and64 arbitrary-code samples in the extra native test. Every
  audited instruction's T-state count matches the emulator, and audited
  totals match fast-counter runs. The full remaining stream uses the
  validated CPU counter; it is not claimed to have a separate per-instruction
  table audit for every instruction.
- [Public converter smoke tests](evidence/cli-smoke.json) pass PCM8 input,
  non-four-aligned padding,44.1-kHz stereo silence resampling, strict JSON
  serialization of undefined silent-signal SNR and invalid-duration rejection.
- The earlier random512-code timing probes are retained under
  [preliminary](evidence/preliminary). The first third round added only the
  inverse table and averaged104198.709 T/sample; replacing general long
  multiplications by signs reduced the revised8192-code random run to
  70083.649 T/sample. Those input scopes differ from the final speech table.
- During development, localized compiler output needed tolerant decoding
  and UTF8 log storage. The first verifier incorrectly required IY to survive
  an SDCC call; the PCM/state matched, and the verifier was corrected to the
  actual ABI. These were harness issues, not accepted output discrepancies.

## Reproduction and decision

See the [algorithm, commands, ABI and license](../../g726/README.md).
`g726.study` builds four variants, runs all functional checks, generates the
audition and records the native timing. `g726.test_cli` reproduces the public
command smoke tests. `g726.archive` copies completed results and authenticates
the saved evidence with [a SHA256 manifest](evidence/manifest.json).
Generated assembly/listings are gzip-compressed; C source, tables, Intel HEX,
link maps, build options and compiler hashes are retained per round.

Keep this standard-compatible implementation as a tested research base.
Do not add it to the playback converter on the strength of compression
alone. Any future native integration needs a substantially faster decoder,
a complete memory allocation, actual PDM timing and independent cold-boot
Fuse verification. PC transcoding G.726 into IMA would be a different
experiment and would not constitute direct G.726 playback.
