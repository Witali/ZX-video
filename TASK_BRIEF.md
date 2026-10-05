# Focused optimization task

Updated 2026-10-05. Use this brief to continue the project in this or a new
chat. This document scopes work; it does not start an automatic goal.

## Project objective

Fit the authorized movie edit on at most three independently bootable TRDs,
keeping resolution and 50 Hz AY. The user requested 10 fps on 2026-10-01;
prioritize exact five-field video
deadlines. All quality, fallback jitter, memory, cycle accounting, LFS and
release requirements in [AGENTS.md](AGENTS.md) remain mandatory. The generic
converter must also support other videos.

## Repository cleanup checkpoint (2026-10-05)

The user authorized repository consolidation and removal of old worktrees.
Completed AY audition, Speex/PVQ and contour research now belong to main;
volume-Huffman history is reconciled without reverting later improvements.
The [cleanup report](docs/maintenance/2026-10-05-repository-cleanup.md)
records 64 removed trees, 71 removed merged local refs, verified local recovery
archives and five intentionally retained trees. Historical paths may require
restoring an archive or supplying explicit input/tool locations. Existing
research next-step notes are checkpoints, not authorization to start another
experiment during cleanup. Current IMA/PDM playback is unchanged.

## AY speech audition checkpoint (2026-10-05)

The [O. Henry trial](ay-converter/analysis/o_henry/README.md) applies the current
AY music profile unchanged to source seconds 60..84: 1200 states at 20 ms,
persistent channels and chip-model noise fitting. Use
`ZX-audiobook-OHenry-AY50-test.trd` and the original/AY comparison WAV (AY
starts at 25 seconds). Two complete native/cold Fuse loops pass all 26400
writes /2400 fields, zero misses. Ordinary work remains 974 T, delta 0.
Full and detailed spectrograms show preserved pauses/parts of the pitch
contour but extra diffuse noise and lost upper harmonic detail. This is a
listening trial, not a speech-quality release; user acceptance is pending.
Reuse this completed evidence. No converter/player change or speech-specific
retuning was made; the accepted IMA3 speech reference remains separate.

## Completed audio request: gentle compression and normalization (2026-10-05)

After identifying vibration in `ZX-audiobook-IMA4-full-disk.trd`, the user
explicitly requests more source gain, normalization and gentle dynamic
compression. Implement this in the converter, processing the complete selected
track continuously before RAM splits. Preserve an explicit uncompressed
dynamics option and externally prepared PCM. Keep IMA/PDM timing unchanged;
validate the new complete disk and distinguish stronger signal from an actual
elimination of cyclic distortion. No merge/push requested.

The [vibration investigation](audiobook-beeper/experiments/ima4-flutter/README.md)
records all five parts through ordinary installed Fuse and speaker loopback.
It finds repeatable field-synchronous error power, not a strong simple 50-Hz
voice AM/FM component or a large host transport slip. It does not claim the
symptom fixed. The subsequent [source-conditioning change and complete disk](audiobook-beeper/experiments/audio-dynamics/README.md)
are now qualified: default gentle 2:1 compression/normalization, exact peak-only
off mode, prepared-PCM bypass and 30 passing focused tests. The new full IMA4
disk retains 113.712 seconds/all 2560 sectors; fresh complete native/cold Fuse
checks pass every bit/state, all transitions/UI and END OF AUDIO. Its SNR is
15.14..18.95 dB versus 10.33..13.53 previously; speed error is about +0.042%.
Archived streams rebuild the disk byte for byte. Cyclic error remains, and
part 3's fitted AM diagnostic increases; do not claim flutter eliminated or
20 dB achieved. No player/hot-path change, carrier reduction, merge or push.
This milestone is complete; do not open another experiment automatically.

The subsequent 2026-10-05 request authorizes cleanup of unsuccessful attempts,
merge into `main` and push. Retire intermediate candidate payloads, duplicate
traces and generated unselected builds while preserving reports, selected
streams and full release verification. See the cleanup entry in CHANGELOG.md.

## Completed audio request: audit the preferred direct IMA4 disk (2026-10-05)

The user prefers `ZX-audiobook-IMA-ADPCM-direct-test.trd` and asks when sound
quality changed and whether to restore the earlier algorithm. This steers
the active milestone to a historical comparison, not another clock design.
The [completed audit](audiobook-beeper/DIRECT_REGRESSION.md) authenticates four
complete two-loop records with identical source PCM and reconstructs them
with one float64 filter. The current assembler rebuilds the preferred disk
byte for byte; no player rollback is needed to recover that checkpoint.

The generic converter introduced in `d4a980d` dropped the old speech-specific
gain/limiter and band-pass preparation. On the same source position, the old
prepared speech is 8.332 dB louder RMS at the same peak. This is a level
difference, not an isolated measured PDM SNR gain. Modern IMA4 on the identical
old PCM has less measured waveform error; no blanket kernel regression is
established. Keep the preferred disk and reproduction guard, preserve current
converter defaults, and do not silently roll back clock corrections or apply
speech limiting to arbitrary music. No merge/push is part of this request.

## Pending audio requirement: fixed sample duration and fast conversion (2026-10-05)

The user requests equal physical duration for every audio sample, eliminating
recording-specific clock compensation. A complete disk should be generated
within the duration of the retained audio on the host PC. Shorter resident
parts are allowed; reducing PDM frequency is explicitly not allowed. Retain
approximately 128 kHz or higher and measure end-to-end quality. Do not silently
replace compressed IMA storage, reduce source bandwidth, or exempt normal
conversion stages from the speed measurement.

First audit the saved full-disk timing and benchmark the existing encoder
without repeating waveform searches. Native instruction equality alone is
insufficient: ULA port/RAM waits, page and bank transitions must all be included.
Any new player needs complete native/cold Fuse proof and explicit CPU counts;
host simulation, codec-only speed or ordinary-sample measurements cannot qualify
the requested result. Preserve the existing release while this is unverified.
The initial [audit](audiobook-beeper/FIXED_SAMPLE_CLOCK.md) is complete:
909696 measured source intervals span 423..598 T. Encoding 23.36 seconds takes
0.531 s with nearest-delta IMA or 13.517 s with the existing beam-32 encoder.
These are encoding-only results. The candidate 440-T / 16-output budget is
128978.182 PDM outputs/s; no such player is implemented or qualified yet.

## Full IMA4 disk through the public script — complete (2026-10-05)

The user requests a complete disk in IMA4 and explicitly requires our
existing conversion script. Extend `convert_audio.py --codec ima4` with
sequential RAM-sized parts, reusing the existing encoder, calibrated player
and disk controller. Use the supplied O. Henry audiobook. Account for each
part's recording-dependent decoder tables; shorten the final part to fill
the remaining sectors. Preserve the looping preview and IMA3 behavior.
Verify every final part, actual cold disk playback, automatic transitions,
loading UI, speed within 2% and measured quality. Keep loading pauses explicit.
Deliver one independently bootable TRD with source ranges and saved evidence;
do not open unrelated codec experiments or merge/push without a new request.

The [completed disk and evidence](audiobook-beeper/experiments/ima4-full-disk/README.md)
retain 113.712 source seconds in five parts, using all 2560 sectors. Complete
native and cold Fuse checks pass every bit, state, memory/paging check, four
automatic transitions, loading UI and END OF AUDIO. Speed error is about
+0.042%; measured loading pauses are 21.03–22.79 seconds. The fixed-clock
float64 SNR is 10.33–13.53 dB: the 20-dB target is not met, so the report
explicitly marks the otherwise verified output as a quality preview.

Twenty-five focused tests pass. Live timing remains 423 T/sample, delta 0.
The full disk's pulse timings match independently qualified references
exactly; the unchanged 8-T limit still includes every startup sample.
Natural HALT-phase qualification and optional phase-search failure handling
are now automatic. Original failures, exact producers, authenticated full
trace reuse and corrected native timing labels are preserved. Ordinary
looping preview binaries remain byte-identical. No physical-hardware or
multi-disk swap execution is claimed for this IMA4 milestone. Further
quality experiments, merge and push require a new request.

## Two-bit G.726 implementation — feasibility experiment complete (2026-10-05)

The user requests an implementation of G.726 at two bits/sample. Implement
and cross-check the exact16-kbit/s,8-kHz codec, retain the same reference
speech for quality comparisons, and measure a concrete Z80 implementation
before claiming live PDM playback. Keep IMA/mu-law defaults and releases.
Standard G.726 has a substantially larger adaptive predictor than IMA;
do not label a simplified IMA subset or a PC-transcoded disk as native
G.726 playback. The deliverable must include executable code, listening
output, tests, timing evidence and a documented integration decision. If
the measured decoder cannot fit the live budget, preserve that result
without weakening the2% speed requirement or claiming a qualified TRD.

The complete codec, PC converter/audition and separately compiled Z80
decoder now pass exact FFmpeg, cross-optimization and native PCM/state tests.
Three rounds reduce the matched-prefix cost127115.239 ->70442.908 T/sample;
the full186880-sample run averages70415.970 against a443.3625-T live budget.
Its CPU-only preparation time3710.095 s also fails the60-second limit.
The23.36-s payload is46720 bytes/8:1; codec-only filtered SNR17.077649 dB.
Retain this [tested research implementation and evidence](audiobook-beeper/experiments/g726-2bit/README.md),
without adding a misleading native G.726 TRD or changing IMA/mu-law defaults.
This requested bounded implementation is complete; further handwritten
optimization is a separate milestone, not an automatic open experiment.

## All active audio codecs — bounded quality follow-up complete (2026-10-05)

The later request to maximize all active audio codecs authorizes the bounded
[quality follow-up](audiobook-beeper/experiments/quality-max/README.md): finish
the pending speech IMA3 comparison, try the third IMA search for both bit
depths, and add waveform-aware mu-law encoding on the PC. This supersedes
the earlier pause for this milestone. Keep resident capacity, formats and
Z80 kernels unchanged; retain every verified fallback. Run full two-loop
checks for each new stream and preserve rejected prototypes. No new movie,
LPC/Speex/AY study, merge or push is part of this request.

Completed results: IMA3 fixed-clock/f64 minimum20.431992 ->20.655388 dB;
IMA4 keeps22.174535 after rejecting a9.849028-dB candidate. Mu-law's joint
two-clock search yields10.295781 dB versus6.533228 for its timing-only
control; its historical9.672027 metric used a different reference clock.
All new streams pass full native/cold Fuse two-loop verification and the
three selected images have normal-speed recordings. Fifteen tests and a
complete short public CLI conversion pass. Z80 costs and RAM are unchanged.

The subsequent **128-kHz eight-bit milestone is also complete**:
[packet algorithm, timing and full evidence](audiobook-beeper/experiments/mulaw128/README.md).
Compact mu-law remains one byte/sample. Sixteen-pulse table dispatch costs
423 T/sample versus432 (−9), with page/bank extras41/112 T versus35/116;
guard reset adds7 T once. All128 KiB are accounted for; tables reduce the
prefix to97024 bytes/12.128 nominal seconds without PCM/PDM expansion.
The public mu-law CLI defaults to `--pdm-rate 128000`;64000 preserves the
old exact-accumulator control. IMA3 remains the overall codec default.

Selected `ZX-audiobook-mulaw-128-test.trd` measures127927.577 useful outputs/s,
tempo−0.056580%, and25.244120 dB on both complete cold Fuse loops. The same
PCM16 reference gives11.927962 dB with64-kHz `best`. All3107833 bits and194049
feedback states, native RAM, paging, startup UI and repeat phase pass;
normal-speed Fuse capture is complete. Twenty-one tests pass. The30-dB
target is not met; no physical-hardware proof, exact full-precision SD2,
sequential mu-law volumes, merge or push is claimed. Finish this milestone
without opening another codec/model sweep.

## IMA4 overlapping PDM search — requested follow-up complete (2026-10-05)

The user chooses IMA3 for duration and IMA4 for quality and authorizes the
overlap transfer/experiment. Inspection confirms it already exists in
`--codec ima4 --quality best`. Complete only the previously paused speech4
refinement and a matched commit128 no-overlap control; other paused cases
remain paused. [Saved comparison](audiobook-beeper/experiments/ima4-overlap/README.md).
No production encoder/player changes are needed: all extra search remains
on the PC, IMA4 ordinary423 T/sample, delta0, page/bank extras14/140 T.

Both new streams pass complete two-loop native/cold Fuse, every bit and
predictor/index, memory/paging/UI and phase checks. However, the refined
commit64 stream's22.552121-dB host estimate becomes8.126727 dB on its own
clock; the matched commit128 control yields20.922286 dB. Keep the earlier
verified22.164431-dB overlap result. Separate consistent float64 audits
give22.174535 /8.126934 /20.928543 dB respectively. There is no new quality
improvement to claim. Data-dependent ULA waits matter despite unchanged
instruction counts. The final disk is a byte-identical copy of the prior
winner with a new normal-speed recording. Source/stage hashes and search
AST checks authenticate the reused host candidate; no mismatched resume
identity or interrupted Fuse proof is accepted. IMA3 stays default.

## Compact mu-law TRD control — complete, not a quality upgrade (2026-10-05)

The user now authorizes the real eight-bit mu-law converter and asks about
second-order quality. `convert_audio.py --codec mulaw` (`ulaw` alias) builds
an independently bootable looping RAM prefix with standard G.711 bytes,
512-byte inverse companding and all decoded 16 bits retained. No PCM/PDM
audio expansion; all 128 KiB are accounted for, holding121088 bytes/15.136 s.
The [first-order control and PC comparison](audiobook-beeper/experiments/mulaw-trd/README.md)
are complete. Native/cold Fuse verify every bit/level/error across two full
loops, full memory, paging, progress and loading UI; normal-speed audio is
recorded. Average PDM64119.013 Hz, speed+0.185958%, ordinary432 T/sample
(+4.625 versus IMA3); page/bank extras35/116 T. Seven tests pass.

Actual total SNR9.672027 dB is poor despite codec-only approximately39 dB.
Retain as a functional format/control preview; **do not replace IMA3** or
claim the 30-dB target. On the identical new PCM16 prefix, ideal PC SD2
at128 kHz gives27.185326 dB versus SD1's17.130225; at64 kHz11.536644 versus
10.053453. These numbers differ from the previous longer PCM8 study.
No second-order Z80 port or physical-hardware validation is established.
Further SD2 work needs an explicit next milestone; the older IMA quality
study remains paused. No merge or push requested for this deliverable.

## Compact mu-law/A-law audio — PC simulation complete (2026-10-05)

The user subsequently authorized eight-bit mu-law/A-law instead of IMA and
requires inverse companding inside modulation, keeping one stored byte per
sample and no expanded PCM audio buffer. The PC-first instruction remains.
[The new study](audiobook-beeper/experiments/xlaw-pc/README.md) selects mu-law:
30.920091 dB at768-kHz numerical integration,30.917095 dB at1536 kHz, both
using stable float64 filtering and128000-Hz PDM. Same source and filter
frequencies/order; all formats are compared under identical conditions.
A-law gives30.221673 dB; linear PCM8 control32.248227 dB. Old float32 scores
are retained separately after high-rate numerical instability was exposed.
Do not mix these numbers with historical measurements without rescoring.

Both payloads are186880 bytes for23.36 s, with512-byte inverse-companding
tables. The full model input exceeds Spectrum RAM: at the old94458-byte
audio budget it would hold11.80725 s, before new layout tradeoffs. Every
direct-byte pulse matches the expanded control; full independent decoder,
integer recurrence and stable finer-grid checks pass. WAVs and raw bytes
are archived. No Z80 port/TRD/default converter switch has been done or
authorized by this PC-only stage. Real timing, RAM layout and loops still
require proof. The earlier paused IMA quality milestone remains paused.

## 30-dB audio target — PC simulation complete (2026-10-05)

The user requires current IMA compression/duration and requested simulation
before another Z80 port. [The bounded study](audiobook-beeper/experiments/snr30-ima/README.md)
keeps the full 186880-sample speech reference, listening filter and 128-kHz
decision rate. Best ideal-clock total SNR is 21.227136 dB for IMA3 and
24.639507 dB for IMA4; 30 dB is not reached. The modulator alone exceeds
30 dB, but the IMA losses remain. Twenty-four configurations include two
overload rejections; the extra filtered-error encoder is worse. Save all
results and the independent PCM/bit checks. No new Z80 code/TRD/defaults or
hardware claim belong to this simulation. Do not port a candidate solely
because its modulator-only score passes 30 dB. This is not an impossibility
proof for another joint encoder/output algorithm. The older paused study
remains paused.

## Second-order audio experiment — completed, rejected (2026-10-05)

The separate [exact SD2 experiment](audiobook-beeper/experiments/sigma-delta2-128/README.md)
executes at 127652.961 Hz average with unchanged ordinary 427.375 T/sample.
It is noisier: 11.179067 dB after a silent-guard repeat fix, against the
accepted IMA3 reference's 20.436321 dB. Keep the old damped model as default.
All bits, predictor/index states, memory, paging and phase pass two complete
native/cold Fuse loops; normal-speed recording is saved. The guard reset
costs 7 T once per loop, offset by 7 T less calibrated filler. Bank-2 tables
grow by 2816 bytes. Preserve the failed initial candidates and use the
archived evidence instead of repeating this experiment. No physical test.
The user subsequently requested 30 dB while retaining current IMA compression
and duration; this is a separate error-budget investigation, not permission
to replace IMA with precomputed PDM or shorten the excerpt.

## IMA3 / IMA4 quality checkpoint — paused (2026-10-04)

The user requested saving progress and pausing. **Do not resume automatically.**
All study processes are stopped. See the exact
[checkpoint and resume instructions](audiobook-beeper/experiments/ima-quality/CHECKPOINT.md)
and [study](audiobook-beeper/experiments/ima-quality/README.md).

Both converters now offer a shared bounded `--quality best` waveform search,
measured-candidate selection, and verified fallbacks. IMA4 additionally
refines on the winner's measured clock. Fourteen tests pass; both short CLI
paths execute successfully and mark below-target previews correctly.
Ordinary Z80 costs remain IMA3 427.375 /IMA4 423 T/sample, delta 0 T.

Three new root TRDs and recordings are complete: Entertainer IMA3
19.031203 ->19.165090 dB, Entertainer IMA4 17.237725 ->19.897558 dB,
speech IMA4 21.010690 ->22.164431 dB. Music remains below 20 dB.
Speech IMA3 has one complete trace-qualified candidate at 20.659504 dB
(baseline 20.436321), but the other candidate and final recording remain
unfinished. Speech IMA4's final refinement has completed host encoding,
but its own Fuse verification was interrupted. Keep the earlier verified
speech IMA4 disk until the new stream proves better. Host scores are not
release scores. Preserve/reuse completed host searches and all saved traces.

This is a saved partial milestone, not a completed four-case release. The
worktree/branch is `C:/Work/ZX-video/.worktree/lpc-ima-preload` /
`codex/lpc-ima-preload`; no merge or push is part of this checkpoint.

## Exact PC encoder acceleration (2026-10-04)

The user requested faster audio encoding after the long normalized music
build. [Waveform search acceleration](audiobook-beeper/experiments/waveform-speed/README.md)
is complete. Keep beam widths, horizons and quality settings unchanged.
Reuse scratch arrays, parent backpointers and retained-state propagation;
replace full sorting with exact state merging and bounded selection.
An optional C kernel is built automatically with installed MSVC x64 or cc,
cached locally, and covered by producer hashes. No downloads. A compiler-free
NumPy fallback remains. The standalone encoder exposes `--backend` controls.

Three comparable 2048-sample repeats measure median 22.766993 s before,
12.571314 s with optimized NumPy (1.811x), and 5.589146 s with the native
kernel (4.073x). All three complete 186880-sample Entertainer search outputs
match the old bytes: new search times 102.094716/170.451387/652.329028 s.
Previous full CLI times include preparation/scoring and are not an exact
end-to-end comparison. Five new test methods and nine converter tests pass.
Reuse existing complete Fuse/quality evidence for the unchanged streams and
players; both published music disks are unchanged. Z80 delta is 0 T, ordinary
IMA3 cost remains 427.375 T/sample and page/bank extras +14/+140 T. The
28-artifact archive authenticates the comparison; no further sweep is needed.

## Normalized Entertainer pair (2026-10-04)

The requested [normalized music pair](audiobook-beeper/experiments/entertainer-normalized/README.md)
is complete. Use `ZX-music-Entertainer-normalized-IMA3.trd` and
`ZX-music-Entertainer-normalized-IMA4.trd`. Both loop the same first 23.344 s
of music, plus a 128-sample silent guard, from exactly the same PCM8/8-kHz
reference. Two-pass loudness preparation measures -17.89 LUFS /-1.97 dBTP,
1.95 LU above the same prefix of the earlier prepared example, without
clipped quantized samples. IMA4's new explicit `--prepared-pcm` preserves it.

All three IMA3 searches and two IMA4 compensation passes are complete.
Selected full-Fuse minimum SNR is 19.031203 /17.237725 dB, with speed errors
-0.299133% /-0.043272%. Both remain listening previews below 20 dB under the
user's permission to retain the best bounded music result. These compare
the existing different pipelines, not bit depth alone. Both cold boots,
two complete native/Fuse loops, paging/memory checks and normal-speed FMF
recordings pass. The 219-artifact audit authenticates the saved pair.
IMA3/IMA4 ordinary hot paths remain 427.375/423 T/sample, each delta 0 T;
no physical hardware or new user listening acceptance is claimed. Reuse
these reports; no further search is part of this completed deliverable.

## Direct IMA3 / automatic converter checkpoint (2026-10-04)

The [IMA3 and IMA4 comparison](audiobook-beeper/IMA3_IMA4_COMPARISON.md)
records the common recurrence, distinct packing/timing/memory and proposed
transfers. First candidate: automatic IMA4 waveform search with overlapping
windows on its existing player. This is a documented proposal, not a new
implementation or release. Local acceleration/prepared-PCM checkpoints are
identified separately from the inspected main baseline; reuse that work.

The latest AY follow-up is [chip-model noise colour fitting](ay-converter/analysis/noise_colour/README.md).
The music profile searches 31 noise periods and three bounded shared-level
choices using valid-rate Ayumi simulation, retaining all tone/channel IDs,
noise events/routes and the 20-ms grid. On the complete Entertainer example,
both cold Fuse loops improve unpooled spectral error at all three resolutions;
noisy-state error falls about 9–12%. Most benefit is level correction; colour
adds a small, mixed incremental gain. Full 34232 writes /3112 fields pass,
zero misses; 19 tests pass. Player binary unchanged, 974 T ordinary /delta 0.
Use `ZX-music-Entertainer-AY-noise-colour-test.trd` and the saved normal WAV,
matched spectrograms and complete evidence. Early invalid-rate model drafts
are explicitly rejected and archived; do not reuse them as quality evidence.
Default legacy remains byte exact; `--profile music --noise-fit heuristic`
reproduces the preceding tracked50 arrangement. Physical hardware and listening
acceptance remain unclaimed. Reuse the completed proof rather than retuning.

The preceding AY follow-up is [persistent components + mixed noise](ay-converter/analysis/tracked50/README.md).
The user requires continued sounds to stay on their original channels despite
small pitch/amplitude changes. The current optional `--profile music` tracks
three dominant fundamentals by pitch, with 289 component lifetimes /zero
migrations in the full Entertainer excerpt. Separately detected noise is mixed
on 415 ticks without disabling an active tone. All changes remain on the
20-ms grid. Full cold Fuse passes 34232 writes /3112 fields, zero misses;
14 regression tests pass. Player binary unchanged, 974 T ordinary /delta 0.
Cosine spectral similarity improves, but weak-spectrum error and some rhythm
proxies regress. Reuse the complete plots, every-state audit and normal WAV.
Previous listening disk: `ZX-music-Entertainer-AY-tracked50-test.trd`. The AY9
mixer extension needs the standalone reader; old legacy bytes remain exact.

The [50-Hz AY music improvement](ay-converter/analysis/music50/README.md) is
complete as an optional `--profile music` in the standalone converter.
The user fixes the sound quantum at 20 ms and excludes 100-Hz playback.
Seven bounded host variants select joint voice allocation, held note pitch,
short-window envelopes, YM2149 volume calibration and transient-limited noise.
The full 31.12-s Entertainer preview passes two cold Fuse loops: 34232 register
writes /3112 fields, no missing fields, unchanged player binary and 974 T
ordinary work (delta 0). Spectrogram error improves modestly; long-window
cosine and some other proxies regress. All measured tradeoffs, figures,
normal Fuse WAV and complete proofs are archived. Use
`ZX-music-Entertainer-AY-music50-test.trd` for listening. Keep the earlier AY
disk and default `legacy` profile. Reuse this bounded evidence; subjective
acceptance and physical hardware testing are not claimed.

The user accepted the actual interactive playback of the overlap speech
TRD in **Program Files Fuse 1.9.0** and requested it as the main algorithm.
`convert_audio.py` now defaults to the accepted packed IMA3/direct-PDM
pipeline; select `--codec ima3` or `--codec ima4` explicitly. IMA3 defaults
to one sequential TRD; the older IMA4 mode remains a looping RAM preview.
The separate IMA3 entry point stays compatible. See [converter usage](audiobook-beeper/CONVERTER.md).
The accepted setup is Spectrum 128 + Beta 128, 100% speed, 44.1-kHz/16-bit
host sound, visible window and no recording/debugger. No Z80 or disk changes.
This closes the pending acceptance of that control, without establishing
the cause of the earlier vibration or claiming all arbitrary inputs pass.

Previously, neither short modeled WAV had audible vibration, while the
user reported it in an earlier Program Files session.
The [host-output study](audiobook-beeper/experiments/fuse-host-output/README.md)
tests that native DirectSound build and `tools/fuse-1.9.0-sdl/fuse.exe` with
real WASAPI speaker-loopback capture. Their interior 19.8 seconds of generated
speech are byte-exact after identical resampling. Both valid 44.1-kHz runs
have only a two-sample (0.042-ms) range in coarse 100-ms-window alignment;
a clean 48-kHz control has a one-sample range and no clear improvement.
Windows output changes frequency balance and level; registered Realtek
effects are a hypothesis, not a confirmed cause. No settings were changed.
One small-buffer 48-kHz capture reported discontinuities and is rejected;
the enlarged-buffer repeat is clean. The user also hears **no vibration in
the actual Windows-output WAV**. Thus the reported symptom was not reproduced
in this controlled run. No stored Fuse config or active process was found;
the user's former unsaved settings remain unknown. A manual launcher with
the measured audio/machine options is available in the study for a visible
run without recording/debugger. That visible launch has now been performed
and accepted by the user. Do not resume blind codec tuning.
The earlier `host_audio_muted: true` FMF metadata was incorrect for native
Win32 (the SDL environment flag is ignored); the recorder is corrected.

The earlier vibration report prompted the historical
[residual study](audiobook-beeper/experiments/ima-3bit-residual/README.md), which
records seven bounded host controls and diagnostic WAVs: four-bit coding on
the same saved PDM clock improves a 4.096-s control from 21.600309 to
23.899006 dB, but is not a new executable disk or proof that flutter is gone.
Other three-bit controls are rejected as worse or immaterial. The subsequent
user comparison found no flutter in either short modeled control, and the
subsequent interactive run is now accepted. No new player or
TRD is released. Reuse these reports instead of repeating the same probes.

The narrower boundary-error correction is complete: [overlapping waveform search](audiobook-beeper/experiments/ima-3bit-overlap/README.md)
commits 64 samples of each 128/256-sample horizon. The automatic converter
uses it by default. On the unchanged sequential speech fixture, boundary
noise/interior noise falls from 1.835..1.840 to 0.999; both final parts measure
20.436046 dB, speed -0.271723%. Every native/Fuse output through EOF passes;
normal Fuse WAV is saved. Player/table binaries are unchanged, 427.375
T/sample, delta 0 T, unchanged RAM/payload/capacity. Use
`ZX-audiobook-IMA3-overlap-test.trd` as the accepted listening reference. This removes
the measured periodic boundary excess; residual IMA/PDM noise remains and
the user has accepted the interactive reference. Reuse its complete evidence.

The [sequential converter](audiobook-beeper/IMA3_SERIES.md) now defaults to
one TRD; `--disk-mode all` retains the whole selected track on numbered,
independently bootable volumes, and `--disk-mode preview` keeps the old
looping RAM demo. It loads/plays successive RAM-sized parts with audible
disk pauses. The 57-byte exit fits existing padding: no extra RAM, no new
per-sample cost, unchanged 94458-byte /251888-sample capacity. Five full
parts hold 157.35 seconds of source on one disk. Full native/Fuse tests cover
automatic loading, both cold disk boots, actual-RAM continuation, wrong disk,
all seven banks and CLI defaults. The root
`ZX-audiobook-IMA3-sequential-test.trd` deliberately plays the same 23.36-s
reference twice; measured 20.161979/20.161096 dB and a 19.798231-s load pause.
The synthetic full-capacity fixture is a correctness test below 20 dB,
not a longer quality release. Reuse the [archived evidence](audiobook-beeper/experiments/ima-3bit-series/README.md).

The [compact IMA3 table layout](audiobook-beeper/IMA3_MEMORY.md) is complete.
It reuses 352 code-gap bytes and removes excess padding, reclaiming 1024
physical RAM bytes with all decoder/PDM states retained. Fixed reservation
is 13312 bytes; automatic capacity is 94458 packed bytes /251888 samples /
31.486 s. Pulse instructions and 427.375 T/sample are unchanged, delta 0 T.
Two full cold Fuse reference loops have exactly the old 5981841 bits and
relative timestamps, preserving the existing 20.159645/20.159651-dB result.
Native and cold Fuse verify the new full seven-bank capacity with a synthetic
tail (8060417 outputs), not a longer real recording. Use
`ZX-audiobook-IMA3-compact-tables.trd`; retain earlier disks as baselines.
Reuse this proof instead of repeating the encoder search or quality checks.

The user also requested a movie-style AY version of the same music. The
[generic AY converter](audiobook-ay/CONVERTER.md) and separately assembled
looping player are complete. The 31.12-s The Entertainer example uses 17116
resident bytes; full cold Fuse checks cover 34232 writes / 3112 fields over
two repeats with no missed fields, loading-message hiding and a normal WAV.
Ordinary cost stays 974 T (delta 0); loop restart adds 105 T once per repeat.
Use `ZX-music-Entertainer-AY.trd`. The chip arrangement's musical similarity
metrics are not comparable to PDM waveform SNR; listening acceptance remains
with the user. Reuse this evidence instead of repeating the conversion.

The AY converter is also preserved as a [standalone source folder](ay-converter/README.md).
It includes the analyser, AY formats, TRD helpers, assembly player, renderer,
native/Fuse verifier and FMF parser. It runs without imports from the movie
or beeper projects. Original experiment sources and evidence remain available.

The separate [public-domain music example](audiobook-beeper/experiments/ima-3bit-entertainer/README.md)
uses The Entertainer by Scott Joplin, performed by IE. The user explicitly
accepts the best found music result below 20 dB. Three automatic searches
select a 31.128-s excerpt at 17.837011/17.836344 dB in complete cold Fuse
loops, with -0.328930% speed error and 0/0-T phase errors. The full 93432-byte
audio capacity now contains real music. This remains a listening preview
under the converter's unchanged 20-dB gate; no global optimum or physical
hardware claim is made. Use `ZX-music-Entertainer-IMA3.trd`. The player hot
path is unchanged, delta 0 T. Do not replace the audiobook reference below.

The direct packed-IMA3 implementation now passes the same complete original
186880-sample reference at **20.159645 /20.159651 dB** in two cold Fuse loops,
without Spectrum-side IMA3-to-IMA4 expansion. Resident audio is70080 bytes,
no PCM/PDM buffer; speed error-0.299133%, phase0/0 T, mean PDM127652.961 Hz.
Native427.375 T/sample is+4.375 T from the expanding player's423 T; page/
bank extras stay+14/+140 T. All5981841 outputs and373760 predictor/index
samples pass native/Fuse checks;32 loading progress steps and message hiding
pass. Normal cold boot to sound is22.815238 s; actual two-loop WAV and
completion audit are saved. Full93432-byte /249152-sample capacity is native-tested across seven
banks with a synthetic tail, not a longer real-source release.

Use [the automatic converter and evidence](audiobook-beeper/IMA3_DIRECT.md).
It handles FFmpeg input, preparation, separate assembly, calibration,
waveform search, complete quality checks, TRD and normal WAV automatically.
The selected width256 /128-sample /weight0.03 horizon scores20.159645 dB
on the pilot schedule and passes the newly executed disk. Default four-bit
encoding remains unchanged. A25-dB target is supported but not achieved
by this full-source IMA3 delivery; below-target runs return exit2 and remain
previews. Reuse the saved complete checks and hashed pilot rather than
repeating tuning experiments. The previous expanding20.071-dB disk remains
historical. New disk: `ZX-audiobook-IMA3-direct-test.trd`.

## Separate audio subproject checkpoint (2026-10-03)

Active throughput goal clarified on 2026-10-04: consecutive sample writes
are permitted; do not spend further work on output pacing. Exact Speex
default is now pure-r40: 1487605573 T / 7960.218 T/sample, 40.751%
fewer T than round09, but still 18.195x over the average 437.5-T budget.
Round17 reconciles nested costs with unchanged OUT traces; round18 selects
combined-register multiplication after comparing three candidates. All
1074400 PCM16/PCM8 samples and 589824 extra product/cycle cases pass.
Rounds19/20 replace the seven-bit excitation shift and retain innovation
table state in registers; 396800 isolated shifts and all 64 table energies
pass. Round21 rejects unprofitable zero guards; round22 selects zero-feedback
state copy and removes an unread store, saving exactly 11359020 T. All
4650 arbitrary-history checks per variant pass. Round23 inlines products,
holds offsets in index halves and borrows SP for first-part reads. It saves
98139844 T versus round22 including setup; 7719 arbitrary histories and 128
filter calls per variant pass. Round24 adds a pre-negated table step and saves
12603144 T; all 65536 coefficients and 262144 negations pass after fixing
an initial borrow bug. Code/state 10527/1041 bytes, useful tables 14140 bytes within 16 KiB;
fresh default build matches and every playback code write is forbidden.
The below-10000 intermediate target is met. Round25 reconciles the full
profile with identical PCM/OUT traces: inline feedback 35.880%, decoder
body 16.470%, preparation 13.728%, 44692 observed changed pages. Round26
then saves exactly 16205909 T by keeping the pitch sum in alternate registers;
200187 sum and 589824 helper-preservation cases pass. Round27 shares a history
cursor for pitch >=41, saving 43983608 T; all 81920 address cases per variant
and 1094880 complete-stream samples pass. General path adds one T/sample.
Round28 selects 65 constant pitch-gain routines using same-size pointer
triples: -96923613 T, all 4259840 products per candidate and 1094880 complete
samples pass. Generic energy multiplication and the table arena stay unchanged.
Round29 returns A:HL directly, saving 12976212 T and 325 code bytes:
**below-9000 intermediate target met**. All 4259840 products, 200187 sums,
163840 history cases per variant and 1094880 complete samples pass.
Round30 confirms the 93-T synthesis shift, saving exactly 27 T/sample;
every OUT delta agrees. Both versions pass 393216 isolated shifts, 1572864
rounding boundaries and 128 filter calls; selected 1094880 full samples pass.
Round31 selects two unsigned partials for signed16x16: -40455507 T, code -39.
All 16777216 unsigned and 2228224 signed products, actual operand/cost
reconciliation, instruction/memory guards and 1094880 complete samples pass.
Round32 shares Q14 coefficient normalization: -5359215 T, code +179.
All 1343488 Q14 cases, 1179648 unsigned products and 1094880 complete samples
pass. Full fixtures improve; 40193 individual speech calls regress. Fresh
default identity matches. Round33 removes that double sign reversal and
uses sign-specific combination: -11022228 T, code +8. Every Q14 input saves
30..211 T; 1343488 arithmetic cases and 1094880 complete samples pass.
Round34 removes 64 cancelling EXX pairs per changed page: exactly
-22882304 T, code -128. All 65536 coefficient pages per variant, 1024 page
masks and 1094880 complete samples pass; registers/flags/BSS match. The
44692-page count and preparation/full saving reconcile with identical inputs.
Round35 retains 16*step in BC/BC' and uses aligned group-end addresses:
exactly -7999868 T, code -27. All 65536 coefficients, 10240 address cases,
1024 page masks and 1094880 complete samples pass; every OUT delta matches
179 T per preceding changed page. The below-8500 intermediate target passes.
Round36 selects direct aligned cosine words and an exact polynomial fallback:
-21301571 T, code -2, table bytes -1870. All 25737 angles per binary, 720896
P13 cases and 1094880 complete samples pass; every OUT delta reconciles.
All speech calls align; random packets exercise two fallback calls. All full
fixtures improve, but unaligned individual calls are slower.
Round37 fuses Q14 and its caller negate: -8467830 T, code +153, state/tables
unchanged. All 1343488 arithmetic cases and 1094880 full samples pass;
caller instruction audits and every OUT delta reconcile. All full fixtures
improve, but 6773 individual speech calls regress.
Round38 reads Q14 arguments directly: exactly 45 T/call, -4204800 T, code +2.
All 1343488 arithmetic cases, 18384 pointer cases per binary and 1094880
full samples pass; every OUT delta reconciles. State/tables unchanged; the
retired upper argument bytes are write-protected.
Round39 omits zero top feedback partials: -35432446 T, code +581, state/
tables unchanged. Eligible samples save 653 T, other nonzero samples pay
21 T and zero samples are unchanged. Both binaries pass 196608 feedback
cases and 128 arbitrary-state filter calls; all 1094880 complete samples,
all fixture cost predictions and every OUT delta pass. No full fixture
regresses.
Round40 selects small signed magnitude products with subtractive updates:
-31084822 T, code +902, no extra state/tables. The below-8000 target is met.
All 196608 feedback cases per binary, 327680 negate cases and 1094880 full
samples pass after fixing an intermediate-byte borrow bug. Every fixture
and OUT delta reconciles; two tone fixtures regress by about 0.15%, while
other full streams improve or stay unchanged. Next inspect negative 12-bit
magnitude/subtraction, retaining -4096/general fallbacks; not implemented
or measured. The next intermediate target is below 7800 T/sample.
The average real-time goal is still unmet.
The broader goal remains active. Use the
[throughput worklist](audiobook-beeper/speex-port/THROUGHPUT_TODO.md) and
[round40 report](audiobook-beeper/speex-port/rounds/40/REPORT.md), not the
historical PVQ scheduling milestone, to select the next optimization.

Latest optimization milestone on 2026-10-04: selected PVQ round13 retains
round12 sound and all 80974 stored bytes, while reducing complete unpaced
CPU from 16897348 to 15651480 T (83.7515 T/sample, 7.373% fewer T).
Every 437/438-T port interval and 25 short-length checks pass. Conditional
round14 reaches 62528 bytes / 2.98874:1 and 69.3130 T/sample, but loses
3.6550 dB raw SNR and is rejected against the declared one-dB gate. Keep
round13 selected; exact Speex remains pure-r9. Table RAM remains 4614 bytes;
ULA/hardware timing remains unverified. Both experiments and reproduction
are linked from the [completed target](audiobook-beeper/speex-port/NEXT_TARGET.md).

Further follow-up on 2026-10-04: all six items in the
[new audio worklist](audiobook-beeper/speex-port/FOLLOWUP_TODO.md) are closed
in the same `codex/speex-port` worktree. Exact default `pure-r9` costs
2510789186 T / 13435.302 T per sample, 9.00% less than round04, but still
30.71x over budget. 1074400 exact PCM16/PCM8 checks pass; code/state are
6624/1039 bytes and the table arena remains 16 KiB. Reduced-precision Speex
and periodic waves were tried and not selected. A separate assembly
PVQ3x1024 player now verifies the complete 186880-sample control with exact
437/438-T output intervals including banks and tail; 90.418 T/sample before
pacing, 80974 stored bytes (2.308:1 versus PCM8), 4614 table bytes. Raw source
SNR is 23.510 dB. This changes the format; it is not real-time Speex.
ULA/physical timing, particularly contended input banks, remains unverified.
Reuse [current code, reports and reproduction](audiobook-beeper/speex-port/README.md).

Initial follow-up on 2026-10-04: the separate `codex/speex-port` worktree contains a
complete assembly Speex narrowband mode-3 decoder with direct PCM8 port
output. Its six-item optimization worklist is complete, with a report and
focused commit for every item. The selected `pure-r4` is 1.644x faster than
the original assembly, at 14764.861 T/sample, but **not real time** against
the 437.5-T budget at 3.5 MHz/8 kHz. The table arena is exactly 16 KiB (16010
useful bytes); code/state are 6152/1356 bytes. All 1074400 tested PCM16/PCM8
samples match, including speech, signal/capacity and random mode-3 packets,
with arithmetic/LPC, memory and instruction-timing checks. Reuse the
[implementation and evidence](audiobook-beeper/speex-port/README.md).
At that initial checkpoint the sine-table suggestion was an unimplemented
approximate alternative; a 388-T four-oscillator kernel estimate excluded
parameter extraction, noise, scheduling and ULA contention. It is not a
verified Speex playback result. Prefer assembly for further Z80 programs.

### Earlier preload and codec studies (2026-10-03)

Latest user clarification: allow **60 seconds** for Spectrum audio
preparation. This supersedes the earlier39.904-s limit below; retain the
old raw128 benchmark and measured results as historical evidence. The user
also permits later decoder optimization. Final PDM >=20 dB, full-source
preservation and speed within2% remain mandatory.

**Completed delivery:** the [IMA3 waveform disk](audiobook-beeper/IMA3_WAVEFORM.md)
now measures **20.07106694 dB in both full cold Fuse loops**, on the same
complete186880-sample source and unchanged comparison filter/clock.
It retains70080 compressed bytes,93440 resident bytes, all128 KiB RAM,
progress and looping playback. Native/Fuse all-bit, every preload byte,
FFmpeg IMA and normal sound capture checks pass. Both phase deltas are0 T,
speed error is-0.043271%, and normal boot to audio is27.254263 s (<60 s).
Ordinary playback remains423 T/sample, delta0; silent cycle padding adds2 T.
Use `ZX-audiobook-IMA3-waveform-test.trd` and the saved completion audit.
The 20-dB goal is satisfied for this input in Fuse, not certified on physical
hardware or arbitrary recordings. Reuse the proof; do not repeat tests or
promote the unexecuted width128 host candidate without a new task reason.

The user made **20 dB final PDM SNR mandatory** after the IMA3 preview,
then requested Speex. The [Speex audition](audiobook-beeper/SPEEX_STUDY.md)
is complete on the same full source: fixed-point decoding at 18.2/24.6k
without optional highpass/enhancement gives 24.752/27.823 dB, or
21.054/22.037 dB after the existing IMA encoder, at 6.946:1/5.155:1 with
a 32-byte framing allowance. These are **before PDM**. A verified exact
Z80 lookup product costs 111 T; synthesis products alone project58.484 s,
exceeding39.904 s before other work. Reject that strategy, not all possible
ports. Reuse the saved30 API cases,10 FFmpeg cases and1376146 arithmetic
checks. No Speex TRD has been produced. The later IMA3 waveform result above
satisfies the final20-dB objective without claiming a completed Speex port.

The earlier independently bootable IMA3 disk was integrated as a
[listening preview](audiobook-beeper/IMA3_PRELOAD.md). It expands 70080
audio bytes into the unchanged 93440-byte resident IMA allocation with
progress, then loops through the existing PDM player. Cold Fuse expansion
takes 1.935179 s; full native and two-loop cold-Fuse checks pass. The user
reported vibration in the first uncorrected test; PC timing compensation
raises fixed-clock SNR from -3.004 to 18.171/18.153 dB. Speed error is
-0.04327%; final phase deltas are -2/0 T. It remains below the 20-dB goal;
do not replace the 21-dB four-bit quality reference or claim vibration-free
physical playback. Reuse this evidence rather than rerunning the pilot.

Three optimization rounds for each selected decoder are complete. Exact
IMA3-to-IMA expansion falls from 58750730 T / 16.564 s to 6657930 T / 1.877 s;
PVQ3x512-to-PCM falls from 31352427 T / 8.839 s to 17460865 T / 4.923 s.
Full input matches independent references at every round. These are native
CPU/buffer measurements, excluding disk, ULA and final bank integration;
PVQ additionally excludes IMA re-encoding. These standalone probes did not
qualify a disk; the later IMA3 integration is described above.
Reuse [the round-by-round evidence](audiobook-beeper/DECODER_OPTIMIZATION_ROUNDS.md).
The exact IMA subset expansion was chosen for integration because it avoids
a separate PCM-to-IMA encoding stage.

Latest scope: compression of 5:1..10:1 relative to mono 8-kHz PCM16;
higher ratios are welcome when sound preservation permits. The user chose
three-bit IMA and predictive VQ for three Z80 optimization rounds each.
Keep the [research backlog](audiobook-beeper/CODEC_RESEARCH_BACKLOG.md)
for other formats. PC encoding complexity is unrestricted. The startup
budget is now60 s; the 25..30-dB codec quality target is advice.

The follow-up10:1 study is complete; no new decoder is selected for release.
The best simple VQ at11.107:1 measures14.213dB before IMA,13.744dB after,
and41.946s for the full native decode/IMA probe before ULA and final writes.
It fails the user's fidelity intent and39.904s startup limit. Encoding
complexity on PC is unrestricted. Proposed codec25..30dB / finalPDM20dB
quality gates are recommendations; preserve the same source and report
rate/quality/CPU separately. Reuse the
[measured study and primary-source shortlist](audiobook-beeper/TEN_TO_ONE_CODECS.md)
instead of repeating its dictionary/DFPWM sweep. ADPCM-XQ-style PC search
is the practical next direction; Speex11k and Opus12k are listening
references, with no verified Z80 decoder here.

In the separate `codex/lpc-ima-preload` worktree, the actual LPC-to-IMA
preloader and both progress bars pass complete native byte/RAM checks but
are **rejected**: cold Fuse conversion takes657.181 s. The corrected user
limit is twice a raw128-KiB read:19.952*2=39.904 s. The user subsequently
rejects LPC timbre changes and requests alternative waveform codecs with
10:1 compression relative to mono8-kHz PCM16; PC encoding cost is unrestricted.
Do not treat the LPC prototype as a playback release. Reuse
[its evidence](audiobook-beeper/LPC_PRELOAD.md).

The waveform-aware PC encoder retains the complete original 186880-sample
control excerpt and 93440-byte live IMA stream. Two complete cold Fuse 128
loops now measure **21.01069 dB** against the original 8-kHz PCM8 clock,
at **-0.04327%** speed error; native/Fuse bits, predictors, memory, paging,
loading and normal-speed sound capture pass. Ordinary player cost remains
423 T/sample (delta 0). This is an input-specific emulator result, not a
physical hardware test or a guarantee for every recording. The different
initial-prefix host probes remain below 20 dB and lack new execution traces.
The generic converter default and root historical disks are unchanged.
Reuse [the complete evidence and new disk](audiobook-beeper/WAVEFORM_IMA.md).

For the user's denser-compression request, the completed
[codec study](audiobook-beeper/DENSE_CODECS.md) selects predictive VQ3x1024
as the next implementation candidate: 13.38% fewer bytes including the book,
0.625-dB codec loss, 100.25 versus 131 native decoder T/sample on average.
Its 216-T boundary path needs prefetch/interleaving; the separate 8196-sample
native probe does not prove full real-time PDM playback. Do not repeat the
size/quality sweep or present the candidate as an integrated player.

## Completed delivery: four refined A/V disks

The user rejected the 15-disk count and requested at most four disks, keeping
the refined picture, new AY50 soundtrack and 10 fps. The full 5066-frame movie
now fits four independently bootable root `ZX-video-refined_part01..04.trd`
images: 2464/2476/2542/2543 occupied sectors. The dynamic dictionary replaces
rows throughout playback; every rendered RGB pixel and all 25330 AY states
remain exact. Full native, cold Fuse, actual predecessor-EOF continuation and
complete screen-byte checks pass for the entire set.

The user's explicit one-field fallback is used: cold starts have one nominal
miss (disk 3 local 933, recovered at 934); sequential playback adds disk 4 local
576, recovered at 577. Actual maxima are70907/70908 T, with no excess beyond
20 ms, invalid field intervals, drift, dropped frames or AY gaps. This is
**not zero-late playback**. The delivery report keeps `release: false` and
`preview_only: true`, with `user_authorized_delivery: true` and the explicit
fallback gate. Root parts 5..15 are retired; historical evidence and the
three-disk 25/3-fps compatibility set remain intact. See
[usage](ZX-video-refined.md), [full report](toolkit/refined_four_report.json)
and `.tmp/refined-four-candidate/`. Do not repeat complete-set measurements
without a material change. The four-disk delivery objective is satisfied;
zero-late playback and the longer-term three-disk target remain future work.

### Current checkpoint: CB46 capacity fits; timing remains open

Latest user steering (2026-10-01): improve compression at unchanged decoding
cost. Prioritize host-side encoding decisions, identical pixels/AY and the
existing player. Compare compressed bytes/sectors AND measured native cycles;
do not accept a smaller stream that increases decoding cost. Reuse one saved
window before any full-set rebuild. Dynamic row replacement is already working.

Latest encoder result: align row indices with their raster bytes and uniform
cell-book indices with the matching row index, then remove selected two-byte
LZSA2 matches only as needed to meet each original block's CPU budget.
The unchanged [4096,4352) window shrinks **185681 ->183997 video bytes**,
**726 ->719 video sectors**, **781 ->777 total occupied sectors**. Every one
of 16 blocks is no larger and no slower to decode. Independent decoder totals
are **16049945 ->15978979 T**; maximum 256-byte-quota slice 22323 ->22104 T.
Renderer code and every frame's counted renderer operations are identical.
All 256 native/Fuse screens (1769472 bytes), 1280 AY ticks and 719 runtime
sectors are exact. Timing still fails: nine late frames, all over one field,
maximum six fields, two invalid intervals; runs 123..123 and 237..244 recover
at 124 and 245. Compare with the baseline's eight misses / maximum 7 (or8)
fields / four invalid intervals. Do not describe aggregate CPU gains as an
every-frame delivery guarantee. Root images remain unchanged.

Reuse `.tmp/dictionary-numbering/budgeted/`, `.tmp/dictionary-budgeted-window/`
and [evidence](toolkit/same_cost_compression_report.json). Reproduce with
`probe_dictionary_numbering.py --variants flat`, `fit_lzsa2_cpu_budget.py`,
then `rebuild_cell_player.py --dictionary-probe <directory>/budgeted` and
the existing four flags (without `--streaming-lzsa2`). The budget fitter is
encoder-only and measures every accepted block with the independent Z80 core.
Do not rerun the unsuccessful distance-only search: exact 187-layout checking
and all 16 real blocks saved zero bytes (731 T only). General book/raster
alignment was also rejected because it increased decoder work.

Full-volume follow-up is complete and rejected: on part 4 [3744,5066), the
same numbering/fitter saves 3256 bytes and 348712 decoder T-states overall,
but blocks 2/5/17/18/32/33 exceed their original byte budgets by
9/26/22/16/52/56 bytes. Do not build this candidate or relax the block guards.
Reuse `.tmp/dictionary-part04/` and
[full-volume evidence](toolkit/full_volume_dictionary_report.json).

The existing four-slot/cache part 4 now has a complete native/Fuse timing
baseline: 1322 exact native screens, 6610 real AY ticks, 2434 exact runtime
sectors, 2543 occupied sectors. Full Fuse screen-byte capture was not run.
There are 29 nominal misses /28 beyond one field, maximum 23 fields, 23 bad
intervals. Runs 378, 588..599, 603..608 and 617..626 recover at
379/600/609/627. Reuse `.tmp/sector-cache-part04-capacity/work/part04/`
and `.tmp/sector-cache-part04-profile.json`; do not rerun this baseline.

New frame-123 diagnosis: packet acquisition has zero disk service or empty
wait, with three complete slots available. Between publications a physical
read consumes 136605 elapsed T and drawing takes 225965 T. Full part 4's
isolated frame 378 similarly has four ready slots and 156777 disk T. These
are optional-background-read admission stalls, distinct from sustained
queue depletion in the longer late runs.

Optional-read admission is now tested and rejected. On the same 256-frame
budgeted stream, a four-field margin gives 30 misses /max38 /15 bad intervals
and an unrecovered tail. A two-field margin gives 11 /max15 /7, recovered at
248; baseline 9 /max6 /2, recovered at 124 and 245. Both eliminate the isolated
frame-123 miss but starve the following burst. Both variants preserve all
256 native/Fuse screens, 1280 AY ticks, 719 runtime sectors and 777 occupied
sectors. There are 1680 admission tests plus instruction-boundary publication
race checks. Keep `--optional-read-gate` disabled; do not sweep more margins.
Reuse [evidence](toolkit/optional_read_gate_report.json),
`.tmp/optional-read-safe-window/` (four fields) and
`.tmp/optional-read-last-field-window/` (two fields).

The final branch-bypass variant now has complete cold/native/Fuse content
evidence for both the saved 256-frame window and full part 4. The window
improves 8 misses /max7 /4 bad intervals ->2 /max1 /0; local 123 and 232 recover
at 124/233. Actual OUT deviation reaches 70914 T (six T beyond one field), so
strict fallback does not pass. Full part 4 changes 29 /max23 /23 bad intervals
->31 /max21 /17, with late runs 378, 591..603, 614..629 and 687 recovering at
379/604/630/688. All native/Fuse screens, AY and sectors are exact; used
capacity is 2544 sectors (one extra bootstrap sector, same video bytes).
Do not select this for release or combine it with the rejected read gate.
Reuse `.tmp/streaming-lzsa2-bypass-window/`, `.tmp/streaming-bypass-part04/`
and [full evidence](toolkit/streaming_bypass_playback_report.json).

The direct header guard is now implemented as opt-in
`--streaming-lzsa2 --direct-lzsa2-header`. Independent Z80 tests confirm
96 ->46 T per available header, saving 50 T. AF is dead at token entry;
AF', HL/DE/BC and suspension remain exact. Explicit `token_guard` and
`token_body` labels replace `Token+3`. Defaults generate identical archived
decoder bytes. Three unit tests /512 AF cases, 40 component blocks and 240
independent full-flags cases pass. Forced-prefix component totals fall
25878233 ->23879878 T. See exact wait/resume path deltas in the changelog.

Both cached scopes have complete cold/native/Fuse screens, AY and sector
verification. Window [4096,4352): two isolated misses, max1, no invalid
intervals, recovered at 124/243; actual max70917 T still exceeds one field.
Full part 4: 31 ->22 misses, 30 ->20 beyond one field, max21 ->15 fields,
17 ->13 invalid intervals; runs 378, 593..601, 615..625 and 685 recover at
379/602/626/686. Streams and occupancy remain unchanged: window 781 sectors,
part 4 2544. Retain the speed improvement as opt-in; neither timing gate
passes. Reuse `.tmp/direct-lzsa2-header-window/`,
`.tmp/direct-lzsa2-header-part04/` and
[direct-header evidence](toolkit/direct_lzsa2_header_report.json).

Earlier prefix admission is tested and rejected. Starting with one completed
slot remaining costs 30 vs27 T (+3) per incomplete-input admission; decoder
instructions and complete-input bypass remain identical. Forty independent
admission cases pass. Window misses increase 2 ->14, max1 ->10 fields,
invalid intervals 0 ->6; recovered at124/252. Full part 4 misses increase
22 ->48 (47 beyond one field), max15 ->30, invalid intervals13 ->32; runs
378,585..609,611..632 recover at379/610/633. Exact media and occupancy are
unchanged. Keep `--early-lzsa2-prefix` disabled. Reuse
`.tmp/early-lzsa2-prefix-window/`, `.tmp/early-lzsa2-prefix-part04/` and
[evidence](toolkit/early_lzsa2_prefix_report.json); do not repeat this sweep.

Invisible attribute removal is implemented with future-visibility checks
and conservative per-block fallback. The bitmap/dither and every rendered
RGB pixel stay exact; only unused attribute bits differ. No later write is
added. Window: 185681 ->185605 bytes (no sector saved),16049945 ->16036695 T,
133 removed writes /5562 renderer T saved. Full part 4 first failed 8 block
budgets; freezing 238 overlapping frames and replanning histories yields
**622695 bytes /2433 video sectors**, 55 blocks individually no larger or
slower, 55754985 decoder T (-53171), 718 removed writes /33337 renderer T saved.
Reuse `.tmp/invisible-attributes-part04-guarded/round01/` and
[evidence](toolkit/invisible_attributes_report.json). Do not repeat this search.

One full direct-header playback build is at
`.tmp/invisible-attributes-playback-part04/`: 2543 occupied sectors, complete
cold/native/Fuse screens and AY checks. Actual timing still fails: 22 nominal
misses, 21 beyond one field, max 15, 11 bad intervals; runs 378,593..602,615..625
recover at 379/603/626. This is a small encoder saving, not a release fix.
Keep defaults/root images unchanged. The opt-in cached rebuilder accepts
`--invisible-attributes-probe <selected folder>` and rechecks RGB equivalence.

Generic consolidation is complete as opt-in `convert_video.py --video-codec
cb41 --guarded-cb46 --fps 10`. It selects the measured player components as
one profile and enforces per-original-block byte/CPU budgets automatically;
otherwise it keeps original packets/streams. The saved window reproduces
185605 bytes and 16036695 T exactly, with nine distinct recompressions.
The initial short-video build exposed an 8D98h decoder/renderer overlap;
build-time relocation now pins the unchanged decoder to 8D74h, preserving
public entries, producer bytes and every instruction's absolute T-state count.
The generic planner checks actual fixed AY trees/tail and the B900h cache gap.
Twenty-one tests plus five generated media cases pass: seven test TRDs,
23 frames /158976 full screen bytes, 115 AY ticks, zero nominal misses and
both modeled-ROM swaps of a three-disk fixture. These are integration checks,
not sustained movie evidence. Reuse `.tmp/generic-guarded-window/`,
`.tmp/generic-guarded-colour-fixed/`, `.tmp/generic-guarded-edge-cases/` and
[archive](toolkit/generic_guarded_cb46_report.json). Defaults/root releases
remain unchanged; do not repeat these fixture builds.

Side-only disk reads now pass the saved window and full part 4. Runtime
tracks already follow the minimum one-way cylinder path; remove redundant
same-cylinder SEEK and READ-84 settling, retaining a 717 T (>200 us) side
pause. Actual cylinder changes, FEh idle recovery, FFh dispatcher, periodic
head maintenance and short-read retry stay intact. Decoder/renderer/media
bytes are unchanged. RAM helper side paths cost 401 ->1009 T (side 1) and
391 ->999 T (side 0); cylinder-side-0 costs 391 ->456 T. These small CPU
increases replace much longer controller waits; ROM/IRQ/ULA are separate.
Helper 89 ->107 bytes, two extra stack bytes, no extra disk sector.

Window [4096,4352): 45 ->22 read-path SEEKs, **2 ->0 nominal misses**, actual
OUT phase deviation at most16 T. Full part 4 [3744,5066), with the accepted
invisible-attribute stream: 152 ->76 SEEKs, **22 ->0 nominal misses**, max19 T,
zero bad intervals/retries/AY underruns. Full cold/native/Fuse screen-byte
checks pass for both scopes; 781/2543 occupied sectors are unchanged.
Generic `--guarded-cb46` enables this automatically; a new three-disk colour
fixture passes all ten frames, 50 AY ticks and both modeled-ROM swaps.
Reuse `.tmp/side-only-seek-window-fixed/`, `.tmp/side-only-seek-part04/`,
[method](toolkit/SIDE_ONLY_SEEK.md) and [evidence](toolkit/side_only_seek_report.json).
Eight component tests include 2560 geometry and1024 independent full-flags
cases. No physical drive was measured; standard CPU clock and the SA460
200 us side-select contract are explicit assumptions.

The coherent four-volume build and full cold/continuation gates are now
complete, as recorded above. Its media-derived common ID, independent cold
states and next-disk validation are verified. For future zero-late work, reuse
the disk 3 local 933 trace: optional cylinder acquisition crosses publication
and delays drawing, despite an available decoded slot. Avoid another whole
set sweep until a bounded scheduling change proves useful. Previously
rejected generic read gates remain disabled; do not assume they now pass.

The sector-streaming LZSA2 experiment remains unselected. Eager
prefix decoding produces 27 late frames / maximum 40 fields in the complete
256-frame window; deferring prefixes while completed slots remain gives
13 /9, versus the sector-cache baseline's 8 /7 (an earlier baseline run was
8 /8). Native screens, AY and sector sequence remain exact. The final variant
bypasses all guard branches after complete input, retaining zero per-token
overhead; its full playback follow-up is recorded above. Keep
`--streaming-lzsa2` opt-in. Reuse
[evidence](toolkit/streaming_lzsa2_report.json); root release disks are unchanged.

Latest exact mode: CB46 mode 3 stores one changed row-pair within a literal
cell, using selector 0..3 plus a row-table index. Other CB44 modes, the
mutable row table, colour attributes and LZSA2 stay unchanged. Three cached
256-frame windows save 10466 bytes (2.39%). The one selected full partition
saves 59832 video bytes, with all 5066 host screens and original AY exact.
Actual native capacity with shared AY/three video slots is now
**2464/2475/2542/2543 sectors**, all fitting 2544; all four dirty-RAM cold
loads pass. Do not rebalance or re-encode this partition just for capacity.
Reuse `.tmp/partial-row-four/` and `.tmp/partial-row-four-capacity/`.

The four-slot [4096,4352) native/cold/Fuse window verifies every screen,
1280 AY ticks and all 726 runtime sectors. Size 780 sectors. There are
31 nominal misses, 29 beyond one field, maximum 28 fields, 12 invalid
intervals; all late runs recover, last at local frame 254. Both timing
gates still fail. Reuse `.tmp/partial-row-window/`,
`.tmp/partial-row-profile.json` and [evidence](toolkit/partial_row_report.json).
Fifteen tests / 32 independent native cases pass. Exact renderer delta:
`7*book_cells - 131*partial_cells` T. No-refill partial cell 186 vs317 T;
book 288 vs281 T. Not every frame is faster; use measured total delivery.

Part 4's 1170-byte AY overflow now occupies checked fixed B398h..B82Ah;
the first 16384 payload bytes remain in bank 6. Four video slots work on this
full volume at unchanged **2543 sectors**. Twenty tests and all 6610 native
AY ticks pass; fill saves 1488 T and init 20 T versus bank-spanning shared AY.
The complete cold/Fuse volume preserves 9137664 screen bytes, all AY50 ticks
and all 2434 runtime sectors. It misses 60 deadlines (57 beyond one field),
maximum 42 fields, 34 invalid intervals; all late runs recover. Reuse
`.tmp/fixed-audio-tail-part04/` and [evidence](toolkit/fixed_audio_tail_report.json).
The smaller cached window above remains useful; do not compare its 31 misses
directly with the full volume's 60 as if the scope were identical.
All 1322 native frames pass guards on bank 6, the fixed payload and unused
RAM. `.tmp/fixed-audio-tail-profile.json` records 70 empty-queue entries;
active draw/disk/decoder elapsed 125.55M/72.02M/58.65M T within 468.51M T.
Packet stages overlap those totals. Retain the full trace for burst analysis.

Latest bounded optimization: opt-in `rebuild_cell_player.py --inline-cells`
inlines the eight CB46 cell handlers, saving exactly 17 T per changed cell.
The additional 8E80h..9000h gap is fully native-guarded; renderer ends at
93BFh, and screen state at 93C1h, leaving the 9400h audio allocation intact.
Four test methods / 28 new independent cases and all 256 native/Fuse frames
pass exact content checks. Window remains 780 sectors; misses 31 ->13,
beyond-one 29 ->13, maximum 28 ->17 fields, bad intervals 12 ->7. Local run
237..249 recovers at 250. Full part 4 remains 2543 sectors with exact cold
boot (revised full-part playback not run). Reuse `.tmp/inline-cell-window/`,
`.tmp/inline-cell-profile.json`, `.tmp/inline-cell-part04-capacity/` and
[evidence](toolkit/inline_cells_report.json). Do not rebuild from the older
window without `--inline-cells` when comparing the next player change.

The next completed opt-in is `--sector-cache`: audit bank 7 E300h..FFFFh,
then use 28 sectors at E400h..FFFFh, prefetch code E300h..E336h and fixed
helper/state B900h..B954h. When decoded slots are full, read compressed input
ahead. Cache hits copy through BC00, adding CPU work but reducing I/O stalls.
Complete window native/Fuse screens, AY, disk sequence and FIFO guards pass.
Two runs have eight late frames, all beyond one field; maximum 8 /7 fields,
four invalid intervals. Run 237..244 recovers at 245. Trace proves 112 cached
sectors, four cursor wraps and zero final occupancy. Window 781 sectors;
part 4 cold capacity remains 2543. Reuse `.tmp/sector-cache-window/`,
`.tmp/sector-cache-profile.json`, `.tmp/sector-cache-part04-capacity/` and
[evidence](toolkit/sector_cache_report.json). Keep all four flags:
`--shared-audio --four-video-slots --inline-cells --sector-cache`.

Previous decoder scope (parked by the steering above): remove the complete-input gate before decoding. The remaining
stall is block 14 (12492 compressed bytes) while the cache holds only 7168;
14 queue-empty entries and longest empty wait 0.81M T remain. Reuse existing
`inplace_streaming_core.py` and `streaming_slot_queue.py` as design references
(they implement ZX0, not LZSA2). `inplace_streaming_player.py` preserves AY/
drive hooks and safely remaps external queue operands. A LZSA2 variant must
guard token headers AND entire literal runs against the loaded input frontier,
preserve AF' and the suspended decoder stack, save the shared sector before
it can be overwritten, and keep explicit EOF completion. Retain existing
LZSA2 bytes and in-place proofs; first validate boundaries in a component
fixture, then reuse this complete window. The core ends at 8E6Eh and the
inline renderer starts at 8E80h, so helper placement must be checked.
Full part 4's preceding renderer's main late
run is local 577..632 (global 4321..4376), recovered at 633. Avoid re-encoding
or building a full set for each trial. Preserve exact stream bytes for
player-only changes; compare native counts separately from real disk service.
Only then build the full four-disk set and run complete cold/continuation
timing and content gates before replacing the root release images.
CB46 is currently available to the cached rebuilder via `--cell-probe`;
generic converter CLI selection still needs integration before completion.
Earlier experiments and constraints below are retained for provenance.

The CB42 implementation keeps the 256-slot / 512-byte row table, but adds
lossless replacement records. The host chooses farthest-next-use eviction
among rows not needed by the current frame; index zero stays black. Already
rendered physical screen histories and the physical cell book are independent
of row indices. Fifteen unit/regression tests pass. A 12-frame synthetic
native playback with 369 row replacements preserves both screens exactly.
Full Fuse checks of that fixture and the 64-frame real window pass: 525312
screen bytes, 380 AY ticks and zero late frames. Ordinary packet parsing
adds 18 T; drawing is unchanged. Row replacement costs 207 + 74*N T excluding
the queue body, dispatch, length read, IRQs, contention and disk latency.

One bounded real [4216,4280) comparison costs 62916 bytes static / 63118 bytes
dynamic, with exact pixels and original two-screen history. No full-size or
full-timing claim follows. Equal movie quarters need 267/271/258/261 distinct
rows and 17489/18632/19202/21012 resident audio bytes. Dynamic rows remove the
first constraint. Audio's 16-KiB bank is still a separate obstacle. Lossless
low-period-byte prediction was tested on all 25330 ticks and is insufficient:
four estimated resident sizes with a 256-byte native-code reserve are
16639/17689/18611/20468 bytes. This host prototype is not enabled in the player.
Reuse [the exact round-trip comparison](toolkit/ay_period_delta_probe/report.json).
The optional `--audio-banks 2` now uses bank 6 for a second exact AYH1
segment (AYB1 wrapper). The fixed-RAM producer changes banks without resetting
the global AY counter, FIFO or chip state; the interrupt consumer is unchanged.
Equal-quarter native bank sizes are [9984,10234], [10481,11067],
[11784,9975], [13123,10802], all within their individual 16-KiB limits.
Thirty-three tests and full Fuse playback of the dynamic-row fixture and
real 64-frame window pass: 525312 exact screen bytes, 380 exact AY ticks,
zero late frames/underruns. Reuse `.tmp/banked-audio-fixture-fixed-ram/` and
`.tmp/banked-audio-window/`; [evidence](toolkit/banked_audio_report.json).
Two incorrect helper placements were caught before acceptance and are
archived: a later producer overwrite, then a helper in pageable memory.
The final helper occupies the checked fixed gap 78A0h..7900h.
Refill overhead is 486 T (+50), switch refill 645 T (+209), EOF refill
516 T (+80), excluding the decoder body, outer service, IRQ/contention/ROM.
Initialization adds 40 T; the AY consumer and row renderer add 0 T.
Four cuts were then selected by minimax planning over 159 short CB42 windows:
[0,1312,2672,3744,5066]. Only this full partition was encoded. Video alone
uses 2558/2530/2540/2520 sectors (10148 total), leaving 28 of the four disks'
10176 sectors for all sound/startup. The first video already exceeds one
disk. Do not build this oversized candidate. All 5066 host screens and LZSA2
blocks round-trip exactly; this is not native timing or a release check.
Eleven planner/generic tests pass. Reuse `.tmp/four-dynamic-probe/` and
[the archived streams/window costs](toolkit/four_dynamic_report.json).
A host-only CB43 whole-cell replacement experiment then tested three
256-frame windows at 0/2560/4096, with exact pixels and all replacement
bytes. Static books total 453253 bytes; replacements every 32 frames cost
455017 (+0.39%), every 64 cost 452835 (-0.09%). The difficult window grows
in both cases. Fifteen tests pass, including exact old CB42 fixture bytes.
Do not implement this weak CB43 variant in the native player yet. Reuse
`.tmp/dynamic-cell-probe/` and [evidence](toolkit/dynamic_cell_report.json).
Host-only CB44 now measures exact reuse from the immutable front screen.
On the same three windows: 453253 baseline bytes, 438082 with same-position
copies, 437973 adding neighbour moves, 437906 refitting the static book to
non-reused cells. CB45 XOR attributes worsen all three windows (443312 total).
Keep only same-position reuse and book refitting for native development;
neighbour modes and XOR are prototypes, not proposed runtime requirements.
Nineteen tests pass; all compared screens are exact, including old CB42
fixture bytes. [Bounded evidence](toolkit/front_cell_report.json).

One full CB44 partition with the existing four cuts is encoded on the host:
628680/622126/637883/633641 video bytes; 2456/2431/2492/2476 sectors (9855
total). This saves 74724 bytes versus CB42, with all 5066 exact screens and
unchanged AY. Only 321 sectors remain for all boot/audio; final capacity is
not established. Reuse `.tmp/front-four/` and [exact streams](toolkit/front_four_report.json).
Native CB44 now supports exact same-position front copies; neighbour mode 3
is rejected before building. Generic and prepared conversion accept
`--front-reuse` (implies dynamic rows), `--dynamic-rows`, `--audio-banks 2`.
Twenty-eight tests pass. The 12-frame fixture is fully exact/zero-late, but
the complete 256-frame [4096,4352) window fails timing: 116 nominal misses,
115 beyond one field, maximum 89 fields. All 1769472 screen bytes and 1280
AY records are exact. Root images stay unchanged; this is not a release.
Native book/literal cells cost 281/317 T versus 268/304 T; front cells 299 T,
excluding caller/refill. Full counted formula and twenty boundary cases are
in [native evidence](toolkit/front_native_report.json).
Follow-up CB44 mask skipping and inline attribute writes reduce every draw
in this window: average 128487 -> 122716 T (-4.49%), with identical video/AY
streams. Ten tests / 24 independent component cases pass; 255 measured
frame deltas match the exact formula (frame zero is bootstrap-primed).
Full Fuse screens and AY remain exact, but 110 frames are late (108 beyond
one field), maximum 82 fields. This is an improvement, not a timing pass.
Code grows 57 bytes; this diagnostic image uses one extra startup sector
(797 -> 798), video unchanged at 735 sectors. The builder enables it for
CB44 automatically, CB41/42 defaults stay unchanged. Reuse
`.tmp/front-fast-masks/` and [evidence](toolkit/front_fast_masks_report.json).

The first complete selected volume before mask optimization fails capacity:
2558 sectors versus 2544,
including 2456 video and 102 startup/audio sectors. No full-set TRDs were
emitted. Reuse `.tmp/front-four-native-capacity/` and the exact cached video.
The complete real Fuse pipeline trace finds drawing 35.10M T, active disk
service 19.16M T and active LZSA2 bridge slices 15.21M T within 95.02M T
from first packet to last publication. Decoder slices include paging/IRQs/
contention; these are not deterministic CPU counts. Packet intervals overlap
disk/decode and must not be added again. An independently booted trace has
117 misses, same maximum 89; report both runs rather than replacing the
original result. Queue empty at 115/256 packet entries. Next reduce native
mask/render overhead and inspect producer scheduling on this cached window;
an extra buffer alone does not establish sustainable delivery. See
[implementation, cycles and reproduction](toolkit/CB44_DYNAMIC.md).
The next completed step retires old reconstruction at 8000h..8D74h in this
layout (derive the upper bound from decoder metadata, never hardcode it).
Guarded native execution of 268 frames makes zero reads/writes/fetches in
those 3444 bytes. Cold Fuse screens/AY are exact for the real 256-frame
window and two six-frame fixture disks; actual predecessor-EOF continuation
also passes at zero late frames for the fixture. The real window remains
late: 113 misses, maximum 82 fields, reflecting changed disk alignment.
Active instructions/draw T-states and video/AY streams are unchanged.
Diagnostic capacity improves 798 -> 796 sectors. The first full selected
volume now needs 2556 / 2544 sectors (12 over); still no four-disk release.
Reuse `.tmp/front-retired-core/`, `.tmp/front-retired-fixture/`,
`.tmp/front-retired-capacity/` and [guarded evidence](toolkit/retired_cell_report.json).
`rebuild_cell_player.py` reuses existing metadata/scaffold/raw/LZSA2/AY;
use it for player-only changes instead of preparing/encoding again.

Shared fixed-RAM AY is now implemented behind `rebuild_cell_player.py
--shared-audio`. The B100h..B700h gap passes a full native access guard.
Seventeen tests pass; all 25330 selected-volume ticks are native/chip exact.
Fixed storage is 3860/3940/3932/4053 bytes. Payloads are
14137/16118/12516/17554 bytes, with only part 4 using a 1170-byte bank-6 tail.
AY fill costs 69212242 -> 70408859 T (+1196617); this saves storage, not CPU.
Real 256-frame cold/Fuse content is fully exact; size 796 -> 793 sectors.
Timing still fails: 108 misses, all beyond one field, maximum 82 fields.
Complete four-volume capacity is 2543/2541/2588/2588 sectors: 84 sectors
(21504 bytes) over the total available 10176. The first two volumes pass
dirty-RAM cold loading; no four-disk release or whole-movie timing claim.
Reuse `.tmp/shared-audio-window/`, `.tmp/shared-audio-four-capacity/` and
[the saved evidence](toolkit/shared_audio_report.json).
Four video slots are now opt-in for one-bank AY: cached rebuild flags
`--shared-audio --four-video-slots`. Move AY to bank 6 and restore video
banks [0,1,3,4], using their original mapper and in-place layout. Spanning
audio is rejected. Capacity 47616 -> 63488 decoded bytes; cursor cost
39/47 -> 11 T; admission and AY relocation add 0 T. Eighteen tests pass.
Complete native/cold/Fuse checks preserve all 256 screens and 1280 AY ticks.
Real-window timing improves 108 -> 37 misses (36 beyond one field), maximum
82 -> 43 fields, 15 invalid intervals; size stays 793 sectors. Still fails
both timing gates. Reuse `.tmp/four-video-slots-window/` and
[the evidence](toolkit/four_video_slots_report.json); do not repeat builds.
Next scoped step: inspect the remaining 41 empty-queue packet entries and
late runs in the full saved pipeline profile, and handle full part 4's
1170-byte audio overflow. Protect it from BOTH compressed input and output,
or first audit further fixed RAM (B700h..BA00h is not yet audited). The old
plan's suggested video map [0,1,3,6] would require new paging code; the
implemented one-bank case instead retains the original [0,1,3,4] mapper.
In parallel capacity work, target the remaining total sector excess;
moving volume cuts alone cannot remove it. Do not reduce media quality.
Retain full image/AY, 10 fps and the entire edit; do not rebuild all four
TRDs until a bounded test and complete capacity checks support the candidate.
Reuse `.tmp/dynamic-rows-probe/`, `.tmp/dynamic-rows-fixture/` and
`.tmp/dynamic-rows-window/`; do not rebuild the previous 15-image set.
Saved [native/Fuse proof and archives](toolkit/dynamic_rows_report.json).
An initial full-capture gate caught a build-only placeholder hash overwriting
the correct five-level reference hash. The parent-volume metadata override
is fixed; recovered checks preserve the original failed metadata. This did
not change any generated player/data bytes or relax the pixel comparison.

## Earlier deliverable: 10 fps

Develop this track on **`codex/cb41-10fps`**, as requested on 2026-10-01.
The branch retains `5ae85fc` and `d2d7e1b`, including all tests, LFS fixtures
and failed-capacity evidence. Local `main` stays at `a878583`: the verified
25/3-fps implementation plus its read-only cadence assessment. Keep further
10-fps changes on this branch; merge only when requested. The working
directory and ignored preparation caches remain in the repository root.

Resample the original at 10 fps, retain the authorized edit and all existing
AY ticks, and publish every frame on five-field deadlines. First validate
short fixtures and a difficult movie window; build one selected complete
set using window-based planning. Confirm full EOF timing, screen bytes,
sound and cold boots before replacing the verified root images. The prior
three-disk 25/3-fps set remains the compatibility baseline until this passes.
Record actual disk count; do not label an oversized or late candidate a
release. Avoid unrelated codec experiments.

Implemented in `5ae85fc`: `convert_video.py --video-codec cb41 --fps 10`,
five-field video and independent AY50. All 23 short fixture frames pass.
The 256-frame difficult window `[4128,4384)` also passes full Fuse timing,
all 1769472 screen bytes and 1280 AY ticks, zero nominal misses or underruns.
Full preparation is complete: 5066 frames, all 25326 original AY ticks plus
four silent tail ticks. Reuse `.tmp/cb41-10fps-movie/prepared/` and the saved
reports; do not redo quantization or compression probes without a reason.

One selected three-volume plan `[0,1808,3408,5066]` failed actual capacity:
first volume 2782 sectors / 2544 maximum. No new full-movie TRD was emitted;
later volumes were not encoded. All 159 window costs are cached in
`.tmp/cb41-10fps-full/partition.json`. This is not an impossibility proof.
The earlier disk-count preference is resolved: on 2026-10-01 the user
authorized additional disks for the refined colour and sound rebuild,
retaining the new image, new AY soundtrack and 10 fps. Do not reduce these
to enforce the earlier three-disk cap on this rebuild.
[Evidence, limits and reproduction](toolkit/CB41_10FPS.md).

## Latest scoped result: cell colours and contrast

The user reported conspicuous coloured cells and fewer solid black/white
areas. The completed 128-frame probe on `codex/cb41-10fps` reproduces the
baseline and confirms lower endpoint coverage. A palette repair improves
RGB error but costs 18.79% more bytes and worsens dark-scene cell seams.
An endpoint-only bias restores coverage at +6.52% bytes, +2.38% measured
output CPU and +4.16% RGB MSE. Seventeen tests and 256 native frame draws
pass. These are experimental selectors; defaults/root images are unchanged,
and full playback for their data is unverified. Reuse the saved RGB windows,
states, streams and metrics. [Decision and next bounded milestone](toolkit/CELL_PALETTE_QUALITY.md).

## Monochrome visual preview completed

At the user's request, root `ZX-video-monochrome-preview.trd` contains the
256-frame `[4128,4384)` window with fixed black/BRIGHT-white attributes and
five dither coverages, 10 fps and original AY50. Full screens, AY, sector
reads and independent boot pass; 669 sectors used. Two frames (80/115) are
one field late, recovering on 81/116. The authorized fallback passes but
zero-late timing does not. This is a visual preview, not the complete movie
or a replacement release. The prepared builder accepts `--monochrome`;
ordinary colour defaults are unchanged. [Evidence and reproduction](toolkit/MONOCHROME_PREVIEW.md).

## Optional contour experiment completed

Source-RGB contours were compared on 96 cached monochrome frames. Strong
tracing overdraws texture and exceeds the 256-row limit in two windows;
reject it. A softened pre-dither variant changes 2.11% of samples, costs
5.37% more window bytes and 2.20% more native output T-states, and fits all
three window dictionaries. All 192 baseline/soft native draws and eight
tests pass. Keep this as an optional prototype: no new TRD/default change,
full-player timing or full-volume capacity claim. A host comparison GIF is
saved. [Evidence and next gate](toolkit/MONOCHROME_CONTOURS.md).

## Joint colour and grain prototype completed

At the user's request, compare joint colour/coverage selection against the
monochrome source reference on 128 cached frames. The selected version guards
average and physical-model RGB error per 2x2 sample and luma error per cell.
RGB MSE drops 52.00% versus monochrome / 8.39% versus old colour, but boundary
residual error increases. Bytes +19.24% and output CPU +6.38% versus mono;
local row tables fit. All 256 native draws and nine tests pass. Keep this
optional prototype; defaults/TRDs remain unchanged and full-player timing
is unverified. Next address boundaries within these RGB bounds before a
release gate. [Comparison and evidence](toolkit/FAITHFUL_COLOUR.md).

## Audio conversion integrated: square harmonics and quieter noise

On 2026-10-01 the user authorized audio changes and requested flexible frequency
selection inside the converter. `convert_video.py` now automatically fits
integer AY periods and nearby volume levels against odd square harmonics,
recovers isolated off-grid tones and lowers noise by one nominal 3 dB step.
AY remains 50 Hz. Three eight-second source windows improve spectral/chroma
and onset proxies; 27 tests, 2400 isolated native AY ticks and one complete
five-frame CLI/CPU fixture pass. Audio bytes +75.79%, audio CPU +27.42% in
these windows. No full-film timing/capacity claim; root TRDs and cached AY stay
at the verified baseline. Reuse [audio evidence and reproduction](toolkit/AY_SQUARE_FIT.md).

## Refined full-movie rebuild completed (fallback preview)

The user requested new root TRDs with the joint colour/grain selector and
square-aware AY fitting. Full preparation is cached in
`.tmp/refined-av-movie/`: 5066 frames, 25330 AY ticks, 506.6 seconds including
120 ms of silent tail padding. The authorized credits cut retains the
post-credit scene through source EOF. Mean frame RGB MSE is 692.855 versus
743.070 for the former colour selector; all per-sample RGB and per-cell luma
guards pass. This is a numerical comparison, not a perceptual percentage.

An eight-disk complete Fuse run had 207 missed nominal deadlines and failed
the one-field fallback on three volumes. A targeted 64-frame probe with
the final series identity and real preceding histories passed with zero
misses. Explicit timing-driven cuts preserve every frame and AY tick; they
do not claim a minimum disk count. Reuse
[the archived failed run and probe](toolkit/refined_av_attempt_report.json).
The selected complete rebuild is now published as root LFS
`ZX-video-refined_part01..15.trd`. Extra disks are authorized for this set.
All 5066 frames / 35016192 screen bytes, 25330 AY ticks and 10126 runtime
sector reads pass cold Fuse playback. All 15 independent boots, 14 prompt
transitions and 14 actual-predecessor-EOF snapshot continuations pass.
Both cold and sequential runs have four isolated late frames: disk 1 frame
1040, disk 3 frame 159, disk 8 frames 92/95 (zero-based). Every late frame
recovers on the next frame. Maximum phase is 70916 T cold / 70915 T resumed,
one 70908-T field plus instruction-level variation. AY has no missing or
duplicate fields or underruns. The one-field fallback passes; nominal
zero-late timing does not, so this is a full-movie preview, not a strict
release. Keep the verified three-disk 25/3-fps compatibility set.

Reuse `.tmp/refined-av-final/`, the 544-file
[final archive and report](toolkit/refined_av_movie_report.json), and the
[integrity/LFS check](toolkit/refined_av_archive_check.json). The failed run
and probe have another 268 authenticated artifacts. All 35 relevant tests
pass. [Finalization](toolkit/finish_refined_av.py) verifies actual EOF
continuations before publishing, and
[archive verification](toolkit/verify_refined_av_archive.py) checks hashes,
source identities and staged LFS pointers. No physical floppy drive test
or minimum-disk-count claim follows. This deliverable is complete; further
disk-count or zero-late optimization is a separate milestone.

## Working method

1. **Define one deliverable.** State the problem, baseline, hypothesis and
   completion criterion briefly. An explanation request should produce an
   explanation with proportionate evidence. An implementation request should
   complete the authorized change. Do not expand either into adjacent work.
2. **Reuse evidence.** Begin with Git status, this brief and the relevant
   source/report. Check input and source identities before reusing results.
   Read targeted sections of [the plan](toolkit/DECODE_SPEED_PLAN.md), not
   the entire history or every report. Preserve unrelated working changes.
3. **Run one comparison first.** Compare the baseline with one candidate.
   Add another only to resolve a specific uncertainty revealed by that
   comparison. Close a hypothesis when evidence supports adoption,
   rejection or deferral; do not keep polishing an unpromising candidate.
4. **Use bounded experiments.** Reuse representative 32–64-frame windows,
   including a difficult scene and relevant boundary cases. Carry required
   predictor, back-screen and producer/consumer state. Select locally;
   build one selected final disk set instead of searching with full sets.
5. **Verify according to risk.** Documentation needs a diff review. Codec
   changes need independent round trips and relevant edge cases. Native
   changes need instruction timings and affected RAM, paging, screen and IRQ
   contracts. Retain required checks; repeat them only when a relevant
   change, failure or unresolved risk invalidates prior evidence.
6. **Keep tool output small.** Search names first; read the relevant function
   or JSON fields. Prefer summaries and failure details over raw reports,
   full listings or repeated source dumps. Save reproduction scripts and
   evidence in the repository; use caches keyed by relevant inputs/options.
7. **Finish the deliverable.** Fix defects needed to complete the authorized
   change. Record each meaningful attempt in the changelog and commit each
   completed logical change separately. Report result, evidence, limitations
   and one next step. A failed experiment can be a completed decision; it
   does not complete the overall project goal. Do not automatically open a
   new research branch after that decision.

No routine confirmation is needed for authorized, reversible work. Ask only
when missing information or a genuine permission boundary prevents a sound
decision. These scope controls must not reduce verification or hide failures.

## Current state: five-level playback and generic integration verified

The full authorized movie edit is verified at 25/3 fps with five brightness
levels on three independently bootable root LFS images:
`ZX-video-five-level_part01..03.trd`. All 4221 frames meet their nominal
six-field deadline, all 25326 AY ticks remain exact, and all 29175552 screen
bytes match. Disk usage is 2475/2505/2511 sectors. Both prompt transitions
and actual-predecessor-EOF snapshot continuations pass. Physical drive swaps
were not measured. Reuse [the complete movie evidence](toolkit/CELL_CODEBOOK_BALANCED.md).

`convert_video.py --video-codec cb41` now connects the same native player to
ordinary video inputs, without movie-specific paths or cuts. It retains
aspect ratio, EOF, audio offsets/tail and silence; refines to five levels;
selects row/cell books and the verified native options; plans with 32-frame
windows; checks resident AY and actual disk capacity; and verifies independent
volumes. Native table/capacity failures are explicit without dropping frames
or reducing quality. FAP3 remains the default for compatibility.

Five generated cases (single, portrait, moving colour/sound split across
three disks, non-square pixels, audio tail) pass complete Fuse playback:
20 frames, 120 AY ticks, seven disks, 138240 exact screen bytes, zero late
nominal deadlines. Both prompt transitions pass; 19 unit/regression tests
pass. The generic representation reproduces every saved CB41 byte and screen
hash for all 4221 movie frames. Root disk identities and all 84 full-movie
archive hashes were checked. Renderer/packet code is identical; LZSA2
relocation within bank 2 preserves every instruction and absolute T-state
cost (0 T instruction delta).

[Generic command, evidence and reproduction](toolkit/GENERIC_CB41.md) ·
[Saved report](toolkit/generic_cb41_profile.json) ·
[Detailed experiment history](CHANGELOG.md)

## Completion evidence and practical limits

| Requirement | Current evidence |
| --- | --- |
| Complete authorized edit, five levels, unchanged resolution/AY | Saved full-movie preparation, exact generic CB41 reproduction, unchanged root hashes |
| At most three independent disks | Actual sector counts, dirty cold boots and complete individual Fuse runs |
| Every frame on its original six-field deadline | All 4221 frames and 4218 intra-disk intervals; zero late runs, drift or dropped frames |
| Exact displayed screens and progress | Full 29175552-byte movie screen verification; full generic fixture screens |
| 50-Hz AY and sustained disk delivery | All 25326 movie AY ticks and 7187 sectors exact; most sectors read during playback |
| Disk continuation | Both prompt/identity/bootstrap checks plus movie runs from actual predecessor EOF RAM |
| Generic converter | Five complete input cases, exact row/AY/native-capacity gates, 19 tests, one selected final set |
| Reproducibility and cycles | Committed scripts/reports/hashed evidence; native instruction tables and 0 T delta; TRDs in LFS |

The requested movie playback objective and generic integration milestone are
complete. Arbitrary new videos still require their own full timing/content
gate; no universal cadence, three-disk limit or perceptual 95% claim follows
from these fixtures. A local size estimate that fails final capacity can
require a smaller --max-frames-per-disk on retry. These limits are reported,
not hidden by quality loss. No further codec sweep is part of this milestone.

## Release gate for a future changed candidate

For a selected release candidate, complete cold-boot and actual EOF playback
of every volume, including video publication times, missed nominal deadlines,
jitter recovery and AY continuity. Window tests never replace this gate.
Rerun a final set only when fixes or invalidated evidence justify it. Reuse
the passing root movie set and archives when their identities are unchanged.
