# Direct packed IMA3 playback and automatic conversion

Measured 2026-10-04. This subproject removes the Spectrum-side IMA3-to-IMA4
expansion. Three-bit codes stay packed in RAM and are decoded as the PDM
outputs are emitted. There is no complete PCM, IMA4 or PDM buffer.

See [the illustrated decoding pipeline](IMA3_PDM_PIPELINE.md)
([Russian version](IMA3_PDM_PIPELINE.ru.md)) for bit packing, IMA state
transitions, PDM feedback tables and interleaved Z80 output.

The subsequent [speech boundary-error fix](experiments/ima-3bit-overlap/README.md)
uses overlapping PC search windows by default. It improves this reference to
about 20.44 dB and removes the measured excess error at 128-sample boundaries.
The earlier disk and measurements below remain historical baselines.

The [compact table placement](IMA3_MEMORY.md) now frees 1024 bytes without
changing playback instructions. The automatic converter uses it by default;
maximum resident capacity is 94458 bytes /251888 samples /31.486 s. The
original measurements and capacity figures below describe the preceding
93432-byte baseline and remain historical evidence.

The complete unchanged 23.36-s control excerpt now measures **20.159645 /
20.159651 dB** in two full cold Fuse 128 loops. Speed error is **-0.299133%**,
mean PDM output is **127652.961 Hz**, and both loop phase errors are **0 T**.
This meets the requested 20-dB gate for this input. **25 dB is not achieved.**
Use [the independently bootable disk](../ZX-audiobook-IMA3-direct-test.trd),
[actual normal Fuse WAV](experiments/ima-3bit-direct/result-preview.wav) and
[unchanged source](experiments/ima-3bit-direct/source-preview.wav).

## Automatic workflow

The converter now defaults to [one sequential disk](IMA3_SERIES.md):
`audio.trd`, with automatic loading of RAM-sized parts. Use `--disk-mode all`
for the whole track on numbered disks. The workflow below describes the
legacy looping preview, now explicitly selected with `--disk-mode preview`.

Run `convert_ima3_audio.py` once with an audio file supported by FFmpeg:

```powershell
python audiobook-beeper/convert_ima3_audio.py "input.m4a" --output "build/ima3" --disk-mode preview --ffmpeg "path/to/ffmpeg.exe" --fuse "path/to/fuse.exe"
```

The script prepares an initial mono 8-kHz / 8-bit excerpt that fits RAM,
encodes the exact IMA3 subset, assembles the separate Z80 listing, builds
an independently bootable TRD and calibrates its actual two-loop timing.
It captures every output event from cold Fuse, uses that schedule for
waveform-aware PC encoding, searches increasingly wide beams, and verifies
the best candidates on new complete disk executions. The source reference,
comparison filter and clock remain fixed during that search. Default target
is 20 dB in both loops, with mean playback speed within 2%.

The final directory contains `audiobook-preview.trd`, `source-preview.wav`,
`result-preview.wav`, `report.json`, assembly and all intermediate evidence.
By default the result WAV is an actual two-loop Fuse sound-generator capture.
Loading progress is displayed in 32 steps and disappears before playback.
Playback repeats without runtime disk access. Cold preparation must be <=60 s.

- `--duration N` limits the retained initial duration further.
- `--target-snr 25` requests the same bounded search with a 25-dB gate; it
  does not assert that the codec can achieve it on that recording.
- `--resume` reuses complete stages only after matching input, settings,
  tool binaries, producer source and saved artifact hashes. Interrupted
  stage directories are preserved separately. Source-byte changes, including
  checkout line-ending changes, invalidate the cache; a fresh output directory
  rebuilds the pipeline automatically.
- `--reuse-pilot PATH` optionally reuses a completed converter pilot across
  PC search changes. It checks the exact source, assembler listing, tool
  binaries, remaining producer/verifier sources and cached artifact hashes.
  Ordinary conversion requires no pre-existing pilot or manual setup stages.
- `--prepared-pcm` is for the unchanged regression reference: exact mono
  PCM8/8k, whole groups of eight, >=8192 samples, final 128 samples silent.
- `--no-recording` skips only the normal-speed sound capture, not the
  complete native and cold-Fuse bit/sample/timing/SNR checks.

A failed quality target returns exit code 2 and an explicitly marked preview.
It must not be promoted to a passing release. Silent input is identified as
having no meaningful SNR. The bounded search is not a universal optimum.
Use the project Python dependencies (`numpy`, Pillow, pyz80, Z80 emulator)
and put `audiobook-beeper` and `toolkit` on PYTHONPATH.

The bounded search tries beam widths 256/512 with 128-sample horizons, then
width 1024 with a 256-sample horizon; regularization remains 0.03. It stops
only after a new disk passes the requested target on both complete loops.
Each new waveform search commits 64 samples, retaining future context from
the rest of its horizon. This avoids periodically accepting end-of-window
decisions without considering their delayed filter response. It costs more
PC encoding time (roughly twice for the first 128-sample search), with no
additional Z80 instructions, RAM or disk payload. Direct encoder invocations
can use `--commit-size`; omitting it preserves historical full-block probes.
Extending the horizon from 64 to 128 samples improved the full-source host
score from 19.950829 to 20.159645 dB at width 256, with zero extra Z80 work.
The superseded width-1024/64-sample search was interrupted and preserved;
its incomplete attempt is not reported as a measured candidate.

## Decoder and memory

Eight little-endian three-bit codes occupy three bytes. Every bank ends on
an eight-sample boundary; sector alignment is placed before the payload.
An eight-phase extraction dispatcher processes codes crossing byte boundaries
without an unpacking buffer. PDM table entries hold SECOND, feedback/D, FIRST;
postponing the FIRST pop frees HL for that dispatcher. The even IMA nibble
alphabet is `0,2,4,6,8,10,12,14`; host-side ordinary IMA bytes are an independent
verification format and are never loaded into Spectrum audio memory.

The preferred modulator has 128 midpoint levels, feedback clipping 3..12 and
120 usable control levels 4..123. These fit two 128-byte rows per page across
all 60 available bank5 pages, avoiding TR-DOS workspace. All 89 compact 32-byte
IMA decoder rows are in bank2. Every PDM-table access therefore has the same
contention class, independently of the audio amplitude. The control range
is -30720..30719 PCM16; encoder candidates outside it are rejected, without
changing the source waveform or its measurement amplitude.

The complete 186880-sample reference needs 70080 resident audio bytes instead
of 93440, a 25% reduction. The full layout has 93432 usable IMA3 bytes,
249152 samples /31.144 s at8 kHz, including its silence guard. The ordinary
preview still retains all 23.36 s of the existing reference. The extra capacity
was verified with the source followed by synthetic silence; that test does
not claim an additional 31-s real recording or a physical-hardware run.

## Instruction timing

Counts use the Z80 instruction timing table and are independently checked
against every native output interval, including byte and bank transitions.
The 128-level FIRST holds are 36,28,28,31,24,33,34,20 T. SECOND's first five
holds are 26,22,27,23,16 T. Its last three depend on extraction phase:

| Phase | Tail holds (T) | Whole sample (T) |
|---:|---|---:|
| 0 |27,12,30|417|
| 1 |23,12,30|413|
| 2 |49,31,30|458|
| 3 |23,12,30|413|
| 4 |27,12,30|417|
| 5 |41,27,30|446|
| 6 |19,12,30|409|
| 7 |31,34,33|446|

Average 427.375 T/sample, versus 423 T for the expanding player: **+4.375 T**.
The earlier padded64-level direct prototype averaged 425.875 T;128-level
half-page selection costs 19 T, while removing its extraction padding saves
17.5 T average, net +1.5 T. Byte-page overflow adds 14 T and bank handoff adds
140 T, unchanged from the previous baseline. The loading progress code adds
no playback T-states. Native counts exclude ULA waits, ROM work and disk latency.
The actual PDM rate and loop periods are measured separately in Fuse.

## Quality and limitations

The accepted comparison remains 192-kHz pulse integration, followed at 44.1k
by `highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2`, excluding the same
first/last 0.1 s. No fitted gain, delay or time stretch is used. SNR includes
coding, modulation and timing errors against the prepared PCM8 reference;
it is not a full-band comparison against the original media file.

Twenty-five dB would mean RMS error at most 5.62% of reference RMS, versus
10% at 20 dB, or 3.162 times less error power. Neither a larger PDM frequency
nor the higher control resolution proves that result for IMA3 speech.
A measured 20-dB disk is not a 25-dB disk, nor a transparency guarantee.
Physical Spectrum sound output remains untested.

## Regression and converter tests

Default four-bit PCM and waveform encoding remain byte-identical to63898f5
on the saved fixtures. IMA3 agrees with the independent recurrence, rejects
invalid alphabets and settles all seven nonzero/extreme guard seeds to0/0.
The new128-level table is checked against4096 exact-rational transitions.
Full-capacity native execution verifies7972865 outputs and498304 predictor/
index samples across all seven banks twice, with memory guards intact.

The normal input-path test uses two seconds of stereo PCM24 at16 kHz,
resampled/downmixed by the converter. It reaches20.948752/20.949015 dB and
-1.134646% speed error in complete new cold-Fuse loops. This is a separate
smoke test, not a substitute for the complete186880-sample acceptance source.
A separate invocation with target25 dB produces20.948905/20.948362 dB and
correctly returns exit2, `target_met:false` and `preview_only:true`.
Resuming the completed20-dB run reuses all three complete stages; a modified
cached artifact is rejected before execution. Reports are in
[the evidence directory](experiments/ima-3bit-direct/).

## Rejected intermediate variants

The [attempt ledger](experiments/ima-3bit-direct/attempts.json) retains the
pilot measurements and their source/assembler inputs. The initial direct
extractor takes408.375 native T/sample but runs2.8701% fast in Fuse, outside
the2% limit. Padding experiments at420.375,422.375,423.875 and425.875 T/sample
restore speed, but unchanged old encodings no longer follow the source clock.
Measured-model64-level host search reaches19.288/19.654 dB, yet an actual
new disk falls to2.604/2.598 dB: moving between contended/uncontended PDM
rows changes the sample schedule with the signal by up to0.766 ms.

Uniform-memory128-level rows reduce the measured difference between two
new payload/model schedules to0..3 T, less than0.846 microseconds. A width256
search scores19.952800 dB on its pilot schedule, then19.944257/19.943702 dB
in two complete new disk loops. Width512/reg0.01 scores19.938054 dB on the
host and is not separately executed. These results remain below20 dB;
neither host scores nor functional correctness alone qualify a release.
An earlier128-level model without feedback clipping required22 states /
132 bytes per row and failed the two-row layout; an independent rational
check also rejected a floating-point tie case. No release uses that model.

The earlier [SNR model study](SNR_ASSESSMENT.md) measured25.81 dB for
ideal128-kHz second-order output directly from PCM8, without IMA, on its
different28.864-s reference. That supports25 dB as an algorithm research
target. It is not evidence that the current packed IMA3 player, real Z80
schedule or physical Spectrum achieves25 dB.


## Completed delivery audit

The [completion audit](experiments/ima-3bit-direct/completion-audit.json)
checks the unchanged source, all5,981,841 native and cold-Fuse outputs,
373,760 predictor/index samples, RAM guards, both phases, every independent
FFmpeg IMA sample, loading progress and the normal audio recording.
Cold boot to sound is22.815238 s; the two-loop WAV lasts46.869388 s. Final
startup, encoding, disk construction, checks and capture ran through the
single converter command. An integrity-checked earlier pilot was reused;
no manual encoding parameters or binary patching were applied to the result.
A separate run through the final normal-input path gives21.116910 /
21.115089 dB on its2-s stereo24 fixture. Resuming the final full run reuses
all four complete stages, including its recording, without opening Fuse again.

Disk SHA256: `601ba65fa7a12b4b6c67f384ba5ed32530bee95816bb86d8effcc0c7de7d34c0`.
Source SHA256: `ea3c0d945a0cc349747664c137c3725aee3fe8cf5e17b991ae3e24f51829a304`.

To reproduce the exact full-source acceptance input, use the saved source
with `--prepared-pcm`; an ordinary user input omits that option. Optionally
pass `--reuse-pilot audiobook-beeper/experiments/ima-3bit-direct/pilot` to
reuse its exact measured schedule when producer bytes still match. Otherwise
omit the cache option and let the script measure a fresh pilot. Use a fresh
output directory. The saved
run manifest records tool and producer hashes; all raw trace/capture paths
and hashes are retained even where the large raw files stay local.
