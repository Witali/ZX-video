# Compact mu-law at approximately 128 kHz

The user requested approximately 128-kHz modulation for the eight-bit mode
on 2026-10-05. This experiment keeps one standard G.711 mu-law byte per
8-kHz source sample in RAM. It replaces eight arithmetic PDM decisions with
sixteen pulses selected through a small, bounded-feedback packet table.
It is not a full-precision second-order sigma-delta implementation.

## Qualified result

The full-capacity prepared source has97024 PCM16 samples at8 kHz, SHA-256
`7983c30d67198ca345138a5dd86409693fb06d6b4442d650cf2d2d512f17a681`.
It is the bounded prefix of the previously archived O. Henry speech WAV,
with a fixed gain1.144779487,80-sample fades and128-sample silent guard.

| Full128-kHz candidate | Minimum fixed-reference SNR | Decision |
| --- | ---: | --- |
| Ordinary G.711 pilot | −2.379847 dB | Retain functional baseline |
| Waveform beam16 | 23.806554 dB | Valid, superseded |
| Waveform beam64 | **25.244120 dB** | Selected |

The selected [TRD](../../../ZX-audiobook-mulaw-128-test.trd) has SHA-256
`c78eeaab5fc14347feb1f09217867a789ad49d30e77f73a6c648645d963041e6`.
Both full Fuse loops score25.244120 dB; no30-dB claim is made. Its source
sample rate measures7995.473579 Hz, or **127927.577261 useful PDM outputs/s**.
Including the balanced guard pulses gives128053.825051 outputs/s. Mean
tempo error is**−0.056580%**, within the user's±2% bound. Each repeat takes
12.134865939 s /43041156 T, exactly607 Spectrum128 fields; both loop phase
deltas are zero. These are averages with nonuniform individual intervals.

Every candidate verifies3107833 output bits and194049 feedback states
across two complete loops. The native cost is41097161 T/loop; Fuse adds
3887990 ULA-wait T across both loops. All eight RAM banks, read-only table
stack, page transitions, message hiding and32 progress updates pass. The
selected startup reads439 sectors after PLAYER loading, taking17.391963
emulator seconds; there are zero disk reads while playing. These disk/ROM
times are not folded into the deterministic Z80 instruction counts.

Normal-speed Program Files Fuse capture is complete, with both wraps and
all paging latches correct. [Source](evidence/speech-full/reference-preview.wav),
[filtered output](evidence/speech-full/output-preview.wav), and
[Fuse mixer capture](evidence/speech-full/recording/fuse-preview.wav) are
retained with the [report](results.json) and [hash manifest](manifest.json).
The beam16/64 searches take45.364 /308.311 seconds on this PC; qualification
and capture are additional. No physical Spectrum has been tested.

On exactly the same complete prepared WAV, the preserved64-kHz `best`
search selects beam32 at**11.927962 dB** (64157.451282 outputs/s,
tempo+0.246018%). The new profile gains**13.316158 dB** under the same
fixed-reference filter/precision/edge criteria. This comparison includes
the changed feedback and repeat-clock handling as well as the higher rate;
it does not isolate oversampling alone. The64-kHz control and all its
candidates retain full native/cold-Fuse proofs, without a new normal-speed
capture because that control is not the release candidate.
[Authenticated comparison](evidence/comparison.json).

## Executable data path

1. BASIC loads the separately assembled player and shadow screen. The
   loader shows “Loading audio data” and a 32-step progress bar, reads
   fixed packet tables and then compact audio bytes, and hides the message.
2. Each audio byte selects a deduplicated table row. The current feedback
   state selects a four-byte record within that row. `POP IY; POP HL`
   retrieves pointers to two eight-pulse routines and the successor state.
3. The routines contain `OUT (C),D` for a one and `ED 71` for a zero,
   always at port `00FE`; D remains16. This uses the original NMOS Z80's
   zero-output instruction, as implemented by the tested Spectrum128 Fuse.
   CMOS replacements with different ED71 behavior are outside this proof.
4. Lookup of the next source byte overlaps the current sixteen outputs.
   SP reads records but never writes during playback. No decoded PCM or
   expanded PDM audio buffer exists. Disk access occurs only before playback.
5. A page/bank boundary extends one interval. A balanced silent guard
   aligns repeat periods to the same ULA frame phase. Before the last zero
   code, feedback resets to its predecessor state, so the next loop starts
   with the original state16. Source bytes are never modified in RAM.

`mulaw_packet.py` generates only data/includes. The actual Z80 program is
[mulaw-packet-player.asm](../../mulaw-packet-player.asm), assembled by pyz80;
the Python builder then places its binary in the TRD. The established,
commented TR-DOS loader is reused as assembler source includes.

## Feedback and compression of tables

The full G.711 decoded PCM16 level enters the weighted recurrence, without
first discarding low bits. Within a sixteen-pulse packet:

```
x = (decoded_pcm16 + 32768) / 65536
weight = nominal_hold / mean(nominal_holds)
u = x + q / weight + 0.5 * recent
bit = (u >= 0.5)
recent = u - bit
q = q + weight * (x - bit)
```

At each packet boundary q is rounded to eighths and clipped to the bounded
range; recent retains its sign. There are32 representable interface states,
of which11 are reachable. A separate Fraction implementation verifies all
8192 code/state transitions exactly. The boundary quantization distinguishes
this method from an exact multiword sigma-delta modulator.

After deduplication the256 code values use212 distinct rows, each64 bytes.
Each used record contains two pointers plus a successor ordinal encoded in
the low six bits of a64-byte-aligned FIRST address. There are95 FIRST and110
SECOND routines; a512-byte map selects rows. The PC waveform encoder can
try all256 legal bytes. `best` optimizes the beeper waveform; a conventional
G.711 decoder of that stream reproduces its control signal, not the nearest
mu-law quantization of the source.

## Instruction-table timing

All counts below are deterministic NMOS Z80 T-states before ULA contention.
Every OUT costs12 T. Holds run from one OUT to the next; instruction groups
following that OUT are included:

| Slot | Following instructions | Hold |
| ---: | --- | ---: |
| 0 | EXX4, LD A,(DE)7, INC E4, JP cc10, EXX4 | 41 |
| 1 | LD L,A4, LD H,n7 | 23 |
| 2 | LD A,(HL)7, INC H4 | 23 |
| 3 | LD H,(HL)7, OR E4 | 23 |
| 4 | LD L,A4, LD SP,HL6 | 22 |
| 5,6 | two LD A,n7 | 26 each |
| 7 | LD BC,nn10, JP (IY)8 | 30 |
| 8 | POP IY14 | 26 |
| 9 | POP HL10, NOP4 | 26 |
| 10,11 | LD r,r4, AND n7, LD r,r4 | 27 each |
| 12 | three NOP4 | 24 |
| 13 | two LD A,n7 | 26 |
| 14 | LD A,n7, two NOP4 | 27 |
| 15 | LD BC,nn10, JP (HL)4 | 26 |

Total **423 T/sample**, versus **432 T/sample** for the old eight-pulse
control: **−9 T/sample**, twice as many output operations. This is an
average modulation rate, not a uniform27.71-T carrier.

The ordinary continuation after JP cc is EXX4. A same-bank page detour costs
45 T instead: INC D4 + JP cc10 + EX AF4 + EXX4 + shared return23, hence
**+41 T** (old +35, delta +6). A bank detour costs116 T instead: INC D4 +
JP cc10 + JP IX8 + EX AF4 + LD BC10 + LD A7 + OUT12 + LD DE10 + LD IX14 +
EXX4 + JP10 + shared return23, hence **+112 T** (old +116, delta −4).
The guard-only `LD E,n` adds7 T once. Shared return is LD A,L4 + OR n7 +
LD L,A4 + EX AF4 + JP HL4. The detour occurs at slot0 of the penultimate
sample of each section because the final byte is prefetched.

Idle pairs add52 T per pair,7 T for each transition between255-pair blocks,
and the calibrated pad. With filler, its entry hold is127 T, ordinary
alternating holds26 T, block-transition hold33 T and exit66+pad T. The
complete native verifier checks every interval against this independent
count. ULA waits, ROM execution and physical disk latency are separate.

## RAM budget

| Physical bank | Audio range while paged at C000 | Bytes |
| --- | --- | ---: |
| 0,4,6,1,3 | C000..FFFF each | 81920 |
| 7 | DB00..FFFF, after shadow screen | 9472 |
| 2 | F100..FFFF, after resident player | 3840 |
| 5 | F900..FFFF, after tables and TR-DOS workspace | 1792 |

**97024 audio +12544 resident code/map +6912 shadow screen +13568 packet
rows +1024 TR-DOS workspace/loader stack =131072 bytes.** All audio is
compact mu-law. The capacity is12.128 nominal seconds, including128 silent
guard samples, versus15.136 seconds in the64-kHz control. A larger disk
does not remove this RAM constraint; sequential mu-law volumes are not
implemented.

## Search and proof

The finite default search keeps the ordinary encoder as a fallback and
tries beam16/horizon16/prior0.1 and beam64/horizon32/prior0.03, both with
eight-sample commits. The objective integrates the real pulse holds and
filter history against a fixed8-kHz PCM16 reference; a Lanczos16 prior uses
the actual sample centers. Only states with the same parent, output word
and successor can merge: matching feedback alone loses filter history.
The optional C kernel and NumPy fallback make identical decisions in tests.

Each candidate is separately assembled, phase-calibrated, executed for two
complete native and cold Fuse loops, and checked for every bit and packet
state. Native execution guards every fixed/paged RAM byte. Fuse checks
loading/progress, sector reads, paging latches, actual OUT intervals and
speed. The winner additionally receives a normal-speed Fuse sound-generator
capture. This is not a physical Spectrum or sound-card-loopback test.

Measurement uses exact held output levels integrated at768 kHz, float64
70-Hz high-pass and two4500-Hz two-pole low-pass filters, then44.1-kHz output.
The100-ms edges are excluded. There is no fitted delay, gain or time stretch;
the worse of two fixed-reference loop SNRs selects the winner. Listening
source/reconstruction WAVs use the same fixed0.5 gain. Fuse's own recorded
sound uses its normal mixer level and should not be compared as loudness
normalized evidence.

## Reproduction

Use the normal project Python dependencies and include `audiobook-beeper`
and `toolkit` on PYTHONPATH. Output directories must be empty.

```powershell
python audiobook-beeper/convert_audio.py audiobook-beeper/experiments/mulaw-trd/qualified/source-preview.wav --codec mulaw --pdm-rate 128000 --quality best --output build/mulaw128/speech-full --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --ffmpeg "path/to/ffmpeg.exe"
python audiobook-beeper/convert_audio.py build/mulaw128/speech-full/pilot/source-preview.wav --codec mulaw --pdm-rate 64000 --prepared-pcm --quality best --output build/mulaw128/control64 --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --ffmpeg "path/to/ffmpeg.exe" --no-recording
python -m unittest test_mulaw_packet test_mulaw_waveform test_mulaw_player test_g711_codec test_quality_search -v
python audiobook-beeper/experiments/mulaw128/archive.py --work build/mulaw128
python audiobook-beeper/experiments/mulaw128/archive.py --verify
```

The archive retains the uncalibrated all-byte test, short balanced speech,
ordinary full control and rejected search candidates. The first assembler
prototype failed due to missing spaces in an IF expression; the initial
Fuse parser incorrectly treated the callback PC as the OUT address rather
than the following address. Both were fixed before qualification. An early
RAM test expected96768 bytes; exact table deduplication allows97024, and the
assertion was corrected. None of those failures is presented as a release.

Twenty-one unit/regression tests pass. Producer snapshots preserve the
versions executing the measured run. Afterwards, the public packet CLI
gained automatic snapshotting of its additional dependencies and reports
undefined SNR for a silent reference; neither change affects this nonzero
speech's DSP, assembly, timing or selection. Earlier64-kHz and quality-max
archives and release images remain unchanged. No merge or push is included.
