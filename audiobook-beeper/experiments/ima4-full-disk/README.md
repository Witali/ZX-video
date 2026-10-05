# Full IMA4 disk through the public converter

2026-10-05. The user requests one completely filled IMA4 disk and explicitly
requires the existing script. This experiment extends the public converter
with sequential parts, preserving the live decoder and quality search.
The completed [disk](../../../ZX-audiobook-IMA4-full-disk.trd) occupies all
2560 sectors and retains the first **113.712 seconds** in five parts. Full
native and cold Fuse execution pass through END OF AUDIO. The 20-dB goal is
not reached on this input; the report explicitly marks it as a quality
preview. No further quality experiment is included in this milestone.

## Input and command

The input is the user-supplied O. Henry audiobook:
`003 - О. Генри. Короткие рассказы ＂Дорого как память＂ и ＂Оборотная сторона＂ (1977) [1bqRZ3gM55s].m4a`.
FFmpeg prepares 5340776 mono samples at 8 kHz (667.597 seconds). The existing
sequential preparation applies one track-wide gain, 1.0900884066754377, then
rounds to PCM8 with 10-ms part-edge fades and 128-sample silent guards. This
input/preparation differs from the earlier louder quality-max control; its
SNR must not be presented as a matched comparison with that control.

```powershell
python audiobook-beeper/convert_audio.py "path/to/audiobook.m4a" --codec ima4 --disk-mode single --dynamics off --output build/ima4-full-disk --ffmpeg "path/to/ffmpeg.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --no-recording
```

The explicit `--dynamics off` preserves this historical peak-only preparation
after the later source-conditioning default change. The `best` profile uses all three bounded waveform searches, up to
two clock-compensation passes and the conditional winner-clock refinement.
Native acceleration is used for host searches. `--no-recording` skips only
normal-speed audible host capture; it retains full native/cold Fuse checks
and listening WAVs reconstructed from actual port events. The original
command, parameter/tool hashes and per-stage reports are archived.

For this run, parts 2..5 were precomputed independently using the same public
converter function and exact parameters. Their prepared WAVs and producer
hashes are checked before adoption by the series driver's existing checkpoint
mechanism. The helper source and adoption records are preserved. This changes
host scheduling, not the encoding search or Spectrum playback algorithm.

## Layout and unchanged live costs

The [format documentation](../../IMA4_SERIES.md) records the allocation:
27 fixed sectors, four full 516-sector parts and one 469-sector tail. All 2560
sectors are occupied. Each part includes its own recording-dependent decoder
tables. Total packed audio is 455168 bytes; 910336 prepared samples retain
909696 source samples / 113.712 seconds. Loading pauses remain audible.
IMA3 behavior and the ordinary looping IMA4 preview are retained.

Live code costs 423 T/sample, with 14/140-T page/bank extras: delta 0. The
57-byte exit fits existing padding, preserving the 14336-byte bank-2 code
reservation and full audio RAM. Only the final silent guard changes: 61 T to
clear the beeper versus 103 T to the old next output without filler (-42 T,
different stop/continue endpoints). 33 guard pulses are omitted. ROM/disk
latency and ULA waits are measured separately, not hidden in that count.
The instruction-table/native audit is in `postflight/tail-tstates.json`.

## Complete disk measurements

| Part | Source interval, seconds | Actual fixed-clock SNR, dB | Speed error | Pulse timing difference |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0–23.344 | 11.448644 | +0.042241% | 0 T |
| 2 | 23.344–46.688 | 12.842333 | +0.041995% | 0 T |
| 3 | 46.688–70.032 | 13.266120 | +0.042242% | 0 T |
| 4 | 70.032–93.376 | 13.527789 | +0.042242% | 0 T |
| 5 | 93.376–113.712 | 10.333552 | +0.041952% | 0 T |

All 14565211 PDM bits and 910326 predictor/index observations pass, along with
memory, bank order, loading-text removal, 32 progress steps per part and four
automatic transitions. Cold preparation takes 27.388691 seconds in Fuse;
reload pauses take 22.750524, 22.570542, 22.790507 and 21.031251 seconds.
All 2585 disk-sector calls occur outside active audio. The final screen is
`END OF AUDIO`. The complete report and terminal RAM are in `release/verification/`.

SNR uses the fixed 8-kHz prepared reference, integration at 768 kHz and stable
float64 filtering: 70-Hz high-pass followed by two two-pole 4500-Hz low-passes.
No gain, delay or time-stretch fit is applied. This run has `complete: true`,
`quality_gate_passed: false`, `preview_only: true`. Its quieter preparation
cannot be compared directly with the older, differently normalized 22-dB
speech reference. All speed errors are within the requested ±2%.

TRD size: 655360 bytes. SHA-256:
`a7e4fb4f289b036b2f84e2032938894767875db3b1e70fbe19d79780af106aa7`.

## Control and retained failures

`micro/` repeats the existing full quality-max IMA4 reference twice. Both
native runs pass all 2990047 bits and 186878 predictor/index observations.
The complete cold Fuse run passes the automatic transition, 32 loading steps
per part, no disk reads during PDM and the terminal screen. Actual pulse
times differ 0..1 T from the qualified control. Each part measures 22.173492 dB
with stable float64 filtering and +0.041482% speed error. Cold preparation
takes 27.388691 s and the loading pause 22.750346 s in Fuse.
The short and full ordinary preview disks regenerate byte for byte; their
reference paths and hashes are saved in `micro/preview-regression.json`.

The first regression harness expected an IMA gzip absent from the short
archive. Its unchanged payload was recovered from its TRD and the
byte-equality check passed. The first generation used portable SDL Fuse, whose
shared stdout.txt prevented independent captured debugger output; its phase
probe timed out and its simultaneous full trace was interrupted/discarded.
Use the installed Program Files build, whose capture was directly tested.
`incomplete/` retains these unqualified attempts and tool hashes.

The first full part exposed a pre-existing orchestration problem: an optional
waveform candidate fails the full repeat-phase gate after a short probe
passes. Preserve the full trace's [626,218]-T phase deviations and reject the
candidate. A second candidate cannot converge in the bounded phase search.
The third completes but scores 6.282434 dB, below the verified second
compensation control's 11.436517 dB. Keep that control. The continuation helper
authenticates saved evidence, uses existing calibration/validation functions
and executes the unchanged converter selection/export code; it does not
relax any phase, bit, memory or speed requirement. The production fix rejects
only this explicit phase failure and keeps verified fallbacks; unrelated
runtime failures and corrupt bits remain fatal. Three dedicated tests cover
that distinction. No 20/30-dB or universal optimum claim is made.

The original full-volume parser stopped after the emulator had completed all
five parts, because it compared only the first cold preview loop. Different
natural HALT phases alter the first active scanline's ULA contention. The
initial comparison found -13..3 T on part 1 (35 pulses beyond 8 T). The fixed
verifier accepts either fully qualified loop and, if needed, independently
qualifies the unchanged preview in the observed natural ready phase. For
part 1, phase 987 was found on the fifth cold start; four early rejections and
the full additional two-loop proof are retained. Part 4 matches its original
warm loop; the others match cold loops. Every final pulse then differs 0 T.
The limit remains 8 T, with no sample exclusions, CPU edits or clock fitting.

`reverify_ima4_volume.py` authenticated the exact disk, tools, debugger script,
complete capture and original successful terminal checks before reusing that
capture. It reran all five native checks and reparsed every actual Fuse event;
the additional phase-reference run executed Fuse normally. This is a verified
reanalysis of the original full-volume run, not a second full-volume emulator
execution. `authenticated_trace_reuse` records its scope and hashes. Future
public conversions perform the reference selection automatically.

The native report formerly printed IMA3's 427.375 T/sample for every codec;
its actual timing assertions already used each codec's metadata. Correct the
label to 423 for IMA4 and rerun all five final and two control native checks.
Retain the old control labels in `micro/native-before-report-fix/`. The tail
audit first completed its assertions but failed to export into a missing
directory; creating it and rerunning succeeded. Twenty-five focused tests
pass, including 8-T acceptance, 9-T rejection and fatal non-phase failures.

## Reproduction and evidence

`run-producers/` preserves the exact original producer bytes and hashes,
including orchestration helpers. `selected/` retains each selected
stream, source reference, assembled player and complete two-loop evidence.
`searches/` retains candidate reports, including rejected candidates. The
subsequent user-authorized cleanup removes superseded payloads and redundant
traces; [retired-artifacts.json](retired-artifacts.json) records their paths,
hashes and recovery commit. Two incomplete-run binary copies have identical
retained final evidence. All selected streams and full verification remain.
`release/` contains the final volume, layout, complete cold
trace, per-part native proofs, actual output timelines/WAVs and terminal RAM.
Saved absolute metadata paths are historical; rebuild fresh local metadata
with the reproducer rather than invoking relocated metadata directly.
`postflight/` retains the final production source snapshots and hashes,
timing audit, completion audit and byte-identical current-source rebuild.

With `audiobook-beeper` and `toolkit` on PYTHONPATH:

```powershell
python audiobook-beeper/experiments/ima4-full-disk/reproduce.py --output build/ima4-reproduced --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --ffmpeg "path/to/ffmpeg.exe"
```

The reproducer first authenticates archived files, assembles all players and
requires a byte-identical TRD, then executes complete native/cold Fuse checks.
`--build-only` stops after byte equality with the qualified disk and explicitly
does not claim a new execution proof. This milestone verifies one full disk;
no physical Spectrum test or new IMA4 multi-disk swap execution is claimed.
