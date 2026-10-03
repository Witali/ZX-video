# Three optimization rounds: IMA3 expansion and PVQ3 decoding

Measured 2026-10-03 on the existing complete 186880-sample, 8000-Hz control
excerpt. The user selected these two decoders and requested three rounds
each. All four versions of each routine reconstruct identical data. No
new playback TRD is qualified by this CPU/buffer experiment.

## Exact IMA subset expansion

The project's ADPCM3-step6 adjustment is `(-1,-1,2,6)` for magnitudes 0..3.
Its magnitude delta is `step/8 + bit0*step/2 + bit1*step`, with each division
truncated independently. Mapping `IMA_nibble = three_bit_code << 1` gives
the same sign, delta and step-index update in the existing IMA decoder.
This is a project-specific subset, not the generic ADPCM-XQ/WAV three-bit
format. It eliminates a separate LPC/PCM synthesis and IMA encoding pass.

Eight MSB-first codes occupy three input bytes. They become four ordinary
low-nibble-first IMA bytes. The full 70080-byte input expands to 93440
bytes; all predictor and index values match an independent scalar recurrence.
No IMA clipping is reported and the final predictor/index are both zero.

| Version | Method | T / 8 samples | Full T | Delta from previous | CPU seconds |
|---|---|---:|---:|---:|---:|
| Baseline | Bit-reading loop | 2515 | 58750730 | -- | 16.563966 |
| Round 1 | Unroll three-bit extraction | 1947 | 45482250 | -13268480 | 12.823099 |
| Round 2 | Three-byte to four-byte algebra | 397 | 9274250 | -36208000 | 2.614748 |
| Round 3 | Four fixed 256-byte tables | 285 | 6657930 | -2616320 | 1.877112 |

Final cost is 35.625 T/sample, a total reduction of 52092800 T. The result
already has the exact byte format consumed by the normal IMA player.
Compression relative to PCM16 is 5.331:1 with a 32-byte framing allowance,
or 5.254:1 including the fixed 1024-byte table. This ratio excludes player
code and disk-sector padding; it is not complete TRD occupancy.

Instruction counts use ordinary Z80 T-states, with no ULA wait states:

- `read_bit` costs 34 T normally or 49 T when reloading a byte. Eight codes
  require 24 reads (three reloads): 861 T, plus 408 T for their CALLs.
  The baseline adds 808 T code work, 136 T outer CALLs, 255 T pair control,
  11 T pair-counter setup and 36 T group control: **2515 T**.
- Round 1 removes 71 T per code (PUSH/POP DE, counter setup/decrements and
  three loop branches): **2515 - 568 = 1947 T**.
- Round 2 uses 55 T to read three bytes, output expressions of
  79 + 82 + 74 + 71 T, and 36 T loop control: **397 T**.
- Round 3 uses 55 T input, PUSH HL 11, four outputs of 31 + 55 + 51 + 36 T,
  POP HL 10 and loop control 36: **285 T**.
- Each of six chunks charges 55 T setup: DI 4, three 16-bit immediate
  loads at 10 each, LD IX 14 and LD B 7. The native harness supplies the
  tail length. This is not a measured final loader call sequence.

The first five chunks read 12288 bytes and write 16384; the final chunk
reads 8640 and writes 11520. Code, tables, input and output guards remain
intact. The assembler rejected an initial invalid `LD L,IYH`; round 3
uses `LD A,IYH` followed by `LD L,A`. Final timing includes both loads.

## Predictive VQ3x512

Each index selects three signed-byte residuals. Reconstruct each using
`base = last_unsigned_sample // 2 + 64`. The PC encoder rejects overflow;
no saturating branch is needed on this verified stream. Eight nine-bit
indices use a high-bit header followed by eight low bytes. The stored book
is 1536 bytes, expanded to 2048 bytes in RAM for four-byte row addressing.

| Version | Method | Full T | Delta from previous | Mean T/sample | CPU seconds |
|---|---|---:|---:|---:|---:|
| Baseline | Sample iterator; history in memory | 31352427 | -- | 167.765900 | 8.839388 |
| Round 1 | History in IXH | 30106547 | -1245880 | 161.099234 | 8.488130 |
| Round 2 | Address lookup tables | 29172137 | -934410 | 156.099234 | 8.224686 |
| Round 3 | One dispatch and three writes per vector | 17460865 | -11711272 | 93.432567 | 4.922852 |

All 186882 values, including two final padding samples omitted from the
WAV, match the independent decoder. Final savings are 13891562 T. The
payload is 70081 bytes; with book and 32-byte framing it is 5.217:1, or
5.180:1 if the fixed 512-byte pointer tables are charged too.

| Version | Common sample | New vector, lower/upper half | New header, lower/upper half |
|---|---:|---:|---:|
| Baseline | 120 | 259 / 262 | 282 / 285 |
| Round 1 | 115 | 249 / 252 | 272 / 275 |
| Round 2 | 115 | 234 / 237 | 257 / 260 |
| Round 3, entire three-sample vector | -- | 276 / 279 | 299 / 302 |

Counts include output stores, CALL/RET and loop control. Baseline common
decoder work is EXX 4 + DEC IYH 8 + JR 12 + read 7 + INC L 4 + ADD 4 +
history store 13 + EXX 4 + RET 10 = 66 T. The caller adds 54 T:
CALL 17 + write 7 + INC DE 6 + DEC BC 6 + LD A,B 4 + OR C 4 + JP 10.
New-vector work is 205 + 54 = 259 T; the high-half path adds 3 T and a
new header adds 23 T. Round 1 saves 5 T per sample plus 5 T per new vector.
Round 2 reduces pointer formation from 48 to 33 T, saving 15 T/vector.
Round 3 saves 188 T/vector against round 2: two CALL/RET pairs 54, two
outer controls 48, sample dispatch/counters 66, two history stores 16 and
the final INC L 4. Thus `234 + 115 + 115 - 188 = 276` T.

The harness verifies the complete histogram, output buffer guards and
unchanged input/tables. It initializes registers between twelve chunks;
startup, paging and that host-side initialization are not counted.

## Quality, limitations and next decision

CPU seconds use a Spectrum 128 clock of 3546900 Hz. Both experiments
exclude disk/ROM latency, ULA contention and the final resident-bank
loader. PVQ timing additionally excludes PCM-to-IMA encoding, so its 4.923 s
is not directly comparable to IMA's 1.877 s as a complete preparation path.
The final disk must independently load its data/code and pass complete
cold-start, memory, speed and PDM waveform checks.

The prior [dense-codec study](DENSE_CODECS.md) measured 20.999-dB codec SNR
for this IMA3 stream and 22.185 dB for PVQ3x512. These optimizations preserve
those decoded values exactly; they do not improve coding quality or prove
20-dB final beeper SNR. The suggested 25..30-dB codec target remains advice.
Ordinary PDM playback stays unchanged at 423 T/sample (delta 0).

Prefer the exact IMA subset for the next integration: it removes a whole
re-encoding stage. Keep PVQ and the other [format candidates](CODEC_RESEARCH_BACKLOG.md)
for later work. No unmeasured candidate is declared a successful release.

## Reproduction and saved evidence

Use project Python packages plus `audiobook-beeper` and `toolkit` on
PYTHONPATH; pyz80 assembles the separate source files. The input directory
must contain materialized files from `experiments/dense-codecs`.

```powershell
python audiobook-beeper/probe_ima3_expansion.py --input audiobook-beeper/experiments/dense-codecs --output build/ima3-rounds
python audiobook-beeper/probe_pvq3_rounds.py --input audiobook-beeper/experiments/dense-codecs --output build/pvq3-rounds
```

Sources: [IMA assembly](ima3-expand.asm), [IMA harness](probe_ima3_expansion.py),
[PVQ assembly](pvq3-decode.asm), [PVQ harness](probe_pvq3_rounds.py).
Saved [IMA report](experiments/decoder-rounds/ima3/report.json) and
[PVQ report](experiments/decoder-rounds/pvq3/report.json) include every chunk,
cycle delta and assembled binary hash. Each archive retains all four
assembler configurations, listings, binaries and its decoded WAV preview.
