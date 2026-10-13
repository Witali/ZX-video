# Real-time Z80 control decoding

Completed 2026-10-13 in `.worktree/six-voice-clicks`, branch
`codex/six-voice-clicks`, following storage commit `b6d8badc`. The user asks
whether the measured command stream can decode in real time. Execute the
actual [19,853-byte one-second-block stream](../six_voice_storage/evidence/columnar-50.zx0)
using native Z80 ZX0 decoders and an experimental native double-buffer/IRQ
consumer. No refitting or changes to the accepted WAV or release player.

**Yes, this complete excerpt fits comfortably in the deterministic Z80 CPU
budget.** Turbo ZX0 plus the command-output interrupt handler uses about
3.68% of a Spectrum128 CPU. This is instruction-level simulation, not a
physical-chip, Fuse/TR-DOS or combined movie-release qualification.

- [Full measurements, checks and source hashes](evidence/report.json)
- [Standard decoder complete field trace](evidence/standard-fields.json.gz)
- [Turbo decoder complete field trace](evidence/turbo-fields.json.gz)
- [Additional successful Turbo one-field preparation trace](evidence/turbo-one-field.json.gz)
- [Standard native benchmark code, origin8000h](evidence/standard.code)
- [Turbo native benchmark code, origin8000h](evidence/turbo.code)
- [Commented generator and reproducer](benchmark.py)

## Measured performance

Clock3546900 Hz; one Spectrum128 field70908 T (about19.9915 ms). Each input
block represents50 updates, nominally one second, and decodes to950 bytes.
Timings include native header skipping, inactive-buffer selection, decoding,
ready publication and return. Interrupt execution is measured separately.

| Decoder | Mean T per block | Maximum T per block | Maximum uninterrupted decode | Decode + all IRQ/output CPU |
| --- | ---: | ---: | ---: | ---: |
| Standard,68 decoder bytes | 67,099.933 | 77,497 | 21.849 ms | 4.059% |
| Turbo,126 decoder bytes | 53,653.800 | 61,583 | 17.362 ms | 3.679% |

Turbo saves13,446.133 T per block on average versus Standard on these same
30 blocks. Total output-side CPU includes IM2 entry/vector jump, register
preservation, column gathering, address/data writes, atomic commit, counters
and buffer switching. Native instructions in the existing release are
unchanged; these are two experimental decoder baselines.

Prepare the next block two fields before it is needed, with IRQs enabled.
Both complete30-second/1500-update runs pass: every output byte matches the
saved controls, every nominal field is serviced, and no buffer underflows.
Worst elapsed preparation including intervening IRQs is22.714 ms Standard
and17.795 ms Turbo. Minimum ready margin is17.297 ms Standard and22.216 ms
Turbo. No field origin is shifted to a late instruction or completed job.

Turbo also passes the complete excerpt when preparation starts just one field
plus100 T before the switch, with minimum2.225-ms ready margin. Standard fails
that short preparation window at field400 (block8, zero-based); only400
earlier fields were verified in that rejected partial run. It is not reported
as a full pass. An initial harness switched after the previous block's final
field; that failed short-window attempt was corrected so switching occurs
immediately before the new block's first field, then all runs were repeated.

Maximum measured IRQ admission delay is15 T Standard/13 T Turbo. Native
frame commits finish at most0.422059 ms after the field edge, including
interrupt entry and the complete bus transaction. They are not claimed to
occur exactly on the edge. Consecutive commit intervals range70808..71008 T
(the additional100 T at block switches is recovered at the following field).
The full traces retain every field edge, admission delay, actual commit time
and handler T-state count. The schedule keeps its original field deadlines
through EOF. Spectrum's field frequency is approximately50.021 Hz; exact
50.000-Hz hardware playback/audio identity was not established here.

## Native routines and timing assumptions

The native job selects the inactive buffer by XORing bit2 of the current
cursor's high byte and clearing its low byte (buffersC000h/C400h), skips the
trusted four-byte size header, then invokes upstream ZX0. It publishes the
ready flag only after decoding all950 bytes. The IRQ saves AF/BC/DE/HL and
does not touch shadow/IX registers or Turbo's self-modified offset. It swaps
only to a ready buffer and outputs one update from the19 column sequences.

The experimental device has19 registers (six period low bytes, six high
nibbles, six packed level/shape/route bytes, shared noise) plus one atomic
commit register. Address/data transactions use FFFDh/BFFDh as an AY-style
bus cost model. An actual AY does not have this register map, six selectable
shapes or the modeled transition/mixer behavior. Bus writes are captured as
control values; no native audio synthesis or actual device is emulated.

Counts follow the repository's Zilog UM0080 instruction timing table in
`validate_fast_sparse.CPU`. The generated routines have these explicit sums:

| Routine/path, entry through return | Calculation | T |
| --- | --- | ---: |
| Flat19-byte baseline output | setup10 +19*(7+12+7+7+12+7) +18*INC HL6 +commit52 +RET10 | 1,168 |
| Columnar output | setup20 +19*52 +18*ADD HL,DE11 +commit52 +RET10 | 1,268 |
| Output path change | Columnar minus flat | **+100** |
| Normal IRQ body | saves44 +ready check29 +cursor/CALL76 +output1268 +counter30 +restore/EI/RETI58 | 1,505 |
| Switch IRQ body | Normal +100 branch/check/switch T | 1,605 |
| IM2 entry and vector stub | interrupt entry19 +JP10 | 29 |

LDIR is executed as individual21-T repetitions and a final16-T iteration,
allowing real interrupt boundaries. Every one of60 uninterrupted native
block decodes has the same output and T-state total as the existing aggregate
LDIR interpreter. Another60 block runs inject an IRQ at varying decoder
phases (including match/literal progress), check full main-register/flag/stack
restoration and exact decoded bytes. The complete schedules additionally
interrupt background jobs with the real periodic native consumer.

## RAM and limits

The benchmark occupies3938 bytes:1281 for code/data, the257-byte IM2 table,
vector stub and alignment padding;693 maximum input bytes including block
header;1900 for two950-byte decoded buffers;64 reserved stack bytes. The
code footprint includes the unused flat baseline output routine. Code, IM2,
input and stack are in fixed uncontended bank2; output buffers are in paged
uncontended bank0. No paging occurs during decode. Screens, TR-DOS workspace,
disk queue and the rest of the128-KiB application RAM are not overwritten or
allocated by this isolated experiment. A full integrated player allocation
and its video/disk producer budget remain outside this request.

The compressed block is supplied in RAM before the measured job. Physical
disk/tape delivery, TR-DOS ROM time, ULA/I/O contention, video work, source
rendering and actual six-voice hardware are excluded. Therefore the result
establishes decoder/command-output throughput with approximately40-ms
lookahead on this excerpt, not a completed hardware player or movie release.
The prior lossless storage/host-WAV replay proof remains unchanged.

## Reproduction

Use the project's NumPy/Pillow/OpenCV toolkit dependencies (OpenCV is imported
by the existing `MiniAssembler` module; no video processing occurs):

```powershell
$env:PYTHONPATH='C:/Work/ZX-video/local_tools/python_packages'
$env:OPENBLAS_NUM_THREADS='1'
python ay-converter/analysis/six_voice_realtime/benchmark.py --output .tmp/realtime-reproduction
```

Use a new output directory. The script regenerates both native programs,
all60 isolated timing checks,60 interrupt stress checks, two complete
two-field schedules, the complete Turbo one-field schedule and the rejected
Standard one-field attempt. It archives code, all passing field traces and
the report with producer/control/stream hashes. No additional fitting or
decoder optimization search is needed for this completed request.
