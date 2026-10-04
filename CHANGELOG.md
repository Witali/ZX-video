# Changelog and optimization experiments

## 2026-10-04: Preserve component channels and mix independently detected noise

Following `c886631`, the user requires three dominant tonal components to
retain their hardware channels under small frequency/amplitude changes and
asks to detect/add noise separately. Keep the exact 20-ms quantum. Add
dominant fundamental selection with retention hysteresis and pitch-based
permutation matching independent of amplitude rank. The current optional
music profile records persistent component IDs and all states at 50 Hz.
Independently estimate broadband noise energy/colour and route it through
the AY mixer without disabling active tones, using one stable route per
noise event. Fit the occupied channel's shared volume to the Boolean mix;
independent tone/noise levels remain a hardware limitation.

Four predetermined complete host variants use the same Entertainer source
and 31.12-s /1556-tick scope. Select dominant tracked tones + noise. Its
unpooled 512/2048/8192-window cosine rises .83381/.82558/.81513 ->
.83882/.83063/.82231 versus v1. Role-selected tracking is weaker; disabling
noise has better tonal cosine but omits the user's noise requirement. Log
error and fine onset F1 regress against v1; preserve the tradeoff and all
variants rather than claiming universal improvement.

The selected CLI stream exactly matches the host candidate. Its 289 estimated
component lifetimes have zero channel migrations. Noise uses 415 ticks,
398 mixed with a tone /17 on a free channel; zero active tones disabled and
zero routing changes within a noise event. Extend AY9 using unused high bits
and an explicit marker, preserving legacy bytes. R0..R10 and the Z80 player
binary are unchanged: 974 ->974 T ordinary, delta 0, 17116 resident bytes.
Legacy movie readers need the new marker decoder for extended streams.

All 14 regression tests pass, including all 32×64 noise/mixer encodings,
independent decoding and native execution of all 64 mixer states, amplitude
swaps, small pitch changes, released-channel reuse and noise/pure-tone tests.
Full cold Fuse passes two loops: 34232 exact writes /3112 fields, zero missed
fields, 67 startup sectors, no runtime reads, correct loading-message hiding.
Startup 10.677687 s; normal WAV 62.226236 s. The complete default CLI still
reproduces the original disk/streams/WAVs byte for byte; 176 prior image hashes
are unchanged. New LFS disk: `ZX-music-Entertainer-AY-tracked50-test.trd`.

Compare actual Fuse sound against the original legacy disk at all three STFT
scales: first-loop cosine .81846/.80556/.79872 ->.82651/.81248/.80224, also
improved in loop two. Medium/long-window log-magnitude error worsens; finer
onset F1 is .62963 ->.64662 and .64093 ->.63396. Visually inspect full and
fixed-region plots plus channel tracks. Deliver the requested behavior as
a listening preview, with spectral/rhythm limitations stated. No subjective
acceptance, perfect source separation or physical-hardware result is claimed.

Save [implementation and reproduction](ay-converter/analysis/tracked50/README.md),
[four-variant results](ay-converter/analysis/tracked50/evidence/results.json),
[channel/mixer audit](ay-converter/analysis/tracked50/evidence/comparison/channel-audit.json),
[complete native/Fuse proof](ay-converter/analysis/tracked50/evidence/release/verification.json),
normal sound, every 20-ms state, comparison WAV and readable spectrograms.
The existing spectrum-analysis methods and original disks remain available.

## 2026-10-04: Implement and qualify a 20-ms AY music profile

The user authorizes the proposed music improvements at 50 Hz, excludes
100-Hz playback, fixes the sound quantum at 20 ms and requests spectrogram
comparison. Baseline `8bcc3c3`, unchanged 31.128-s Entertainer request /1556
states /31.12-s output, source SHA-256
`08dc5241de419edf9693ad20797389cb735d9b6fc06bfb6936568bb707f13077`.
Add an optional `--profile music` to the standalone folder, retaining the
exact old default stream. Implement joint beam voice allocation, attack
evidence, faster note envelopes, held note periods, YM2149 DAC calibration
and transient-limited tonal noise. The file grid and existing player remain
unchanged. No recording-specific score or waveform is added.

Seven predetermined full host comparisons select joint voices + 0.5 envelope
blend + transient noise. Host unpooled STFT cosine at 512/2048-sample windows
rises .83076/.82366 -> .83381/.82558; 8192 decreases .81797 -> .81513.
Spectral convergence decreases at all three scales; finer onset F1 rises
.65891 -> .74783, though the sequential combined candidate reaches .78414.
Noise falls 243 ->109 ticks. Individual calibration, envelope, noise and
joint variants trade off; reject universal/default replacement. Short harmony
runs increase 34 ->51 and repeated-attack bass tuning remains imperfect.
Archive every variant, including those not selected; no open-ended tuning.

The selected CLI stream exactly matches the host candidate. Full cold Fuse
passes both loops: 34232 register writes /3112 fields, zero missed fields,
67 startup sectors, no runtime disk reads, correct loading-message handling.
Startup 10.677687 s; normal captured WAV 62.226236 s. Player binary identical:
ordinary 974 ->974 T, delta 0; 17116 resident bytes. Eight regression tests
pass, plus complete native offset/one-shot CLI playback and event clipping.
All 175 prior image hashes remain unchanged. New independently bootable LFS
preview: `ZX-music-Entertainer-AY-music50-test.trd`.

Full Fuse spectrogram comparison uses equal global RMS, unpooled bins,
three resolutions and the same fixed known clock correction for both disks;
raw-time results are also retained. First-loop log-magnitude MAE improves
9.92776/9.26998/7.78490 ->9.71170/9.13648/7.64777 dB, with improvements in
both loops. Fine onset F1 rises .62963/.64093 ->.77533/.74894. Long-window
cosine falls in both loops and second-loop long-window convergence slightly
worsens. Inspect complete and fixed-region spectrograms: changes are modest,
with remaining timbre/polyphony errors. Fix cropped detail-figure margins
before delivery. No subjective or physical-hardware acceptance is claimed.

Save [implementation, decisions and reproduction](ay-converter/analysis/music50/README.md),
[seven-variant report](ay-converter/analysis/music50/evidence/results.json),
[complete native/Fuse proof](ay-converter/analysis/music50/evidence/release/verification.json),
[actual-sound spectral report](ay-converter/analysis/music50/evidence/comparison/fuse-spectrogram.json),
normal sound, comparison WAV, readable figures and hash audit in the same
focused change. Decision: deliver this optional 20-ms music preview and keep
the old disk/default; reuse this complete evidence for any later work.

## 2026-10-04: Analyse Entertainer AY accuracy with six bounded host probes

At the user's request, review the standalone AY converter and propose ways
to improve melodic and timbral accuracy using the unchanged Entertainer
example. Baseline is `e604de3`, original source SHA-256
`08dc5241de419edf9693ad20797389cb735d9b6fc06bfb6936568bb707f13077`,
31.128-s request /31.12-s AY output. Reproduce every baseline register byte
and the archived coarse metrics before comparing six fixed variants:
baseline, no noise, no fine tuning, median pitch per note run, YM2149 volume
curve, and no-noise/no-tuning/YM combined. This is one bounded analysis;
the production algorithm, assembly and existing release disks are unchanged.

The baseline uses noise for 243/1556 ticks. Its period changes within its own
fixed note labels number 279/134/197 for bass/harmony/melody. The 185.76-ms
analysis window and a 371.52-ms /10-Hz legacy metric obscure short events;
the old onset match tolerance is 100 ms. The nominal volume curve differs
from the actual rendering model by up to 2.57 dB. These findings motivate
note/onset-aware tracking, stable keyboard-note pitches, chip calibration
and separate music/effects noise policies before raising the update rate.

With the added 92.88-ms-window /10-ms-hop /20-ms-tolerance signal-onset proxy,
baseline F1 is 0.65891; median-note pitch gives 0.70000 and YM calibration
0.69636. Spectral cosines are 0.89279 /0.89205 /0.89214 respectively. Pitch
holding mainly removes extra detections, rather than recovering more source
attacks. The combined switches score 0.88766 spectral / 0.68807 finer F1;
reject automatic adoption because metrics trade off. Noise removal also
loses matched source events. No result is a subjective preference or an
annotated-note accuracy score; no candidate dominates all measurements.

Save the [review and staged recommendations](ay-converter/analysis/entertainer/README.md),
[reproducing probe](ay-converter/analysis/entertainer/probe.py),
[complete report](ay-converter/analysis/entertainer/results.json) and six
compressed register streams. All six full host renders complete. Reuse the
existing full baseline native/Fuse evidence; candidates have no new Fuse or
physical-hardware qualification. Ordinary player work stays 974 T, delta 0 T,
with the same 17116-byte excerpt and 550 bytes/s. Faster-rate costs in the
review are explicitly estimates requiring a new scheduler and complete
timing qualification. Decision: deliver the analysis and prioritize the
note/attack and chip-model work; do not replace the current release.

## 2026-10-04: Preserve the AY converter as an independent source folder

At the user's request, retain audio-to-AY conversion in
[ay-converter](ay-converter/README.md), including all project source required
for analysis, AY/register formats, TRD packaging, separate Z80 assembly,
Ayumi rendering, metrics, native/Fuse verification and FMF audio extraction.
Baseline is `2a55226933f12f529cee8256d82ccf48b16d8039`. Extract the required
audio routines and disk helpers from the movie/beeper modules; replace parent
imports with local modules. Preserve the original experiments and evidence.
Include third-party Ayumi source/license, Python requirements, native tests,
source provenance and standalone instructions. No synthesizer or player
algorithm is changed; the ordinary field path is 974 ->974 T, delta 0 T,
with the existing 105-T loop-restart extra.

Validation runs a copied source folder from a separate directory with only
external Python packages on PYTHONPATH. Convert the full unchanged 31.128-s
The Entertainer request to 1556 AY ticks /31.12 s, then execute both complete
cold Fuse repeats and capture normal-speed sound. All 34232 writes and
3112 nominal fields pass, with zero missed/duplicate fields, 67 startup
sector reads and zero runtime reads. The final TRD, player binary, screen,
both register streams and all three WAVs are byte-identical to the previous
verified example. TRD SHA-256 remains
`c6139c9c5cd4c18df82d3b1f208064790487a48db3883b26f916d00765fc177c`.
All 27 extracted function/class syntax trees match their origins, allowing
only removal of the local TRD helpers' former `base.` qualification. Both
native tests pass, covering bank edges, six-bank capacity, looping and EOF.
See the [saved verification](ay-converter/verification.json) and
[source manifest](ay-converter/SOURCE_MANIFEST.json). Physical hardware and
new listening acceptance are not claimed. Accept this source separation;
the conversion result and existing release images remain unchanged.

## 2026-10-04: Retire obsolete speech preview disk images

At the user's request, remove 24 obsolete speech TRDs from the current
checkout: 12 root listening previews and 12 archived copies/earlier builds.
Baseline is `9dbe81c20912e18a0b79fb724cdcbeed72cbd0df`. The selected files total
15728640 bytes (15 MiB); this is checkout image size, not Git/LFS storage
reclaimed. The [retirement inventory](audiobook-beeper/retired-disks.json)
records each exact path, SHA-256, reason and recovery commit. Selection
covers rejected early AY speech and superseded PDM/IMA/PWM speech previews;
it is not a new cross-codec SNR measurement.

Retain current overlap speech, qualified IMA3 and four-bit waveform
baselines, both music examples, the pending pitch-aware AY candidate,
movie releases and calibration/correctness fixtures. Keep the old
`ima-preview/audiobook-preview.trd` needed by two research scripts and point
those scripts to that exact archived copy instead of its retired root alias.
The existing PDM rebuild regression now checks the archived report's SHA-256,
preserving exact-byte verification without the duplicate TRD fixture.
Sources, WAVs, traces, historical reports and earlier log entries remain.
Update active links and identify retired disks in their historical guides.

Verification: all 24 selected images match their HEAD LFS identities before
removal; all 175 other tracked TRD hashes are unchanged afterward; no Markdown
link outside this historical log targets a deleted image. The retained ADPCM
baseline matches its Fuse proof. All six existing `test_pdm.py` tests pass
with the bundled Python 3.12 and project packages on PYTHONPATH; initial
default-interpreter attempts lacked compatible NumPy. Syntax and diff checks
pass. No player hot path changes (0 T delta), new audio measurements, history
rewrites, LFS pruning or worktree cleanup are included.

## 2026-10-04: Document the direct IMA3-to-PDM pipeline

At the user's request, save the chat's decoding explanation and diagrams in
[the audio documentation](audiobook-beeper/IMA3_PDM_PIPELINE.md), with the
requested Russian description retained in a linked translation. Cover the
three-byte/eight-code packing, IMA delta/index table, biased predictor,
six-byte PDM dispatch entries, 17 reachable feedback states, PC table
construction and FIRST/SECOND/TAIL output pipeline. Link the guide from
IMA3_DIRECT and reference the current source and verified profile. This is
documentation only: player, timing, tables and release images are unchanged;
no new performance measurements are claimed. Check local links, diagram
fences and the patch before committing.

## 2026-10-04: Remove periodic speech encoder boundary-error bursts

The user reported voice vibration in the latest sequential speech TRD.
Keep the unchanged 186880-sample PCM8/8-kHz reference and the same two-part
test scope. Analysis of the actual old disk found noise/signal power in the
first eight samples after a 128-sample boundary 1.8353057/1.8399391 times
the block-interior value. The waveform encoder committed complete search
windows without future costs for their delayed filter response. Commit 64
samples per 128/256-sample horizon instead, carrying exact decoder/PDM/filter
state. The generic converter applies this automatically; old standalone
probes keep full-block commits unless requested otherwise.

Bounded 4.096-s active-speech probes: baseline 21.371719 dB /20.938 s;
overlap 21.600309 dB /41.468 s; overlap with extra quantized filter history
21.584004 dB /62.125 s. Reject history as slower without improvement. Full
overlap encoding takes 236.812 s; host 20.436321 dB is then independently
verified in complete native/Fuse loops at 20.436321/20.436366 dB, phase 0/0 T.
An early normal-Fuse/trace comparison gave an invalid -6.55-dB diagnostic
residual when it assumed an exact normal audio clock. Observed FMF chunks
and local Blip_Buffer source expose the 815/65536 clock factor; correcting
that clock and fitting the stationary transfer gives a 27.66-dB residual.
This fitted diagnostic is not source SNR and changes no delivery/acceptance
audio. Preserve its reports/script snapshots and reject the initial result.

Final independently bootable `ZX-audiobook-IMA3-overlap-test.trd`: both parts
measure 20.436046 dB (baseline 20.161979/20.161096), speed -0.271723%, full
5980094 native/Fuse live pulses exact, zero reads during audio, 32-step UI
and automatic transition to EOF pass. Loading pause 19.818222 s; normal
first-part Fuse WAV captured at 100% speed. Boundary/interior error ratio
falls to 0.999314 at 128 samples and 0.993068 at 64; boundary error power falls
about 47%. Initial comparison-script parsing required support for archived
Fuse command abbreviations; the corrected parser uses the full original
trace, not inferred times. All 20 player/table binaries match the old final
layout. Native 427.375 T/sample, delta 0 T; page/bank +14/+140 T and 13312-byte
reservation /70080-byte payload /94458-byte capacity are unchanged. Added
exact output-time evidence, a reproducible boundary diagnostic and three
tests; all eight tests including disk planning pass. Physical hardware and
subjective listening are not claimed. The measured periodic excess is fixed;
remaining codec/modulation noise is not eliminated. See the
[experiment, scripts and complete reports](audiobook-beeper/experiments/ima-3bit-overlap/README.md).

## 2026-10-04: Merge completed audio conversion work into main

At the user's request, merge `codex/lpc-ima-preload` through `d969aae` into
main, retaining its independently completed Speex assembly work through
`9ef19e9`. Resolve only overlapping additions to this log and TASK_BRIEF;
preserve both histories and identify the earlier codec studies as historical.
Player and converter source bytes are unchanged by conflict resolution.
All five sequential planning/CLI tests pass using main's modules; all 481
archived series evidence hashes and the final TRD hash match. Reuse the
completed native/Fuse evidence rather than repeat playback experiments.

## 2026-10-04: Speex item 06, select optimized decoder and reject real time

Complete the six-item worklist and select `pure-r4` as the default. A fresh
offline build exactly reproduces the verified image. Original assembly
4536172045 T falls to 2759257254 T, delta -1776914791 T, 1.644x faster and
39.17% fewer T. Audio and 23360-byte compressed input are unchanged. Code/state
are 6152/1356 bytes; table payload is 16010 in a 16384-byte arena.

Real time FAIL: 14764.861 T/sample is 33.748x the 437.5-T budget. Actual OUT
intervals are 5473..889303 T; all 186879 subsequent outputs miss their nominal
deadlines, maximum lateness 2676721156.5 T. Synthesis alone remains over
budget. Do not add pacing or claim a playback release. CPU results exclude
ULA/disk/hardware. Record approximate oscillator/periodic synthesis as a
separate possible next experiment, not an implemented replacement. See
[decision and final profile](audiobook-beeper/speex-port/rounds/06/REPORT.md)
and the completed [TODO](audiobook-beeper/speex-port/TODO.md).

## 2026-10-04: Speex item 05, final exactness and timing audit

Complete the final verification item without changing decoder instructions.
Across speech, signal/capacity fixtures and 512 random mode-3 packets, all
1074400 PCM16/PCM8 samples match upstream. Compact LPC matches round03 on
1104 ordered, unordered and extreme angle vectors. Arithmetic, all table
entries/products, input/code/static-table immutability, declared RAM writes
and control cases pass. Two complete silence frames including cache reuse
audit at 3320178 T / 443264 instructions, each matching the instruction table.
The saved full speech OUT trace reconciles with every reported deadline.
No mismatch occurred; real time remains unqualified. See
[item 05 report](audiobook-beeper/speex-port/rounds/05/REPORT.md).

## 2026-10-04: Speex round 04, compact symmetric LPC

Complete TODO item 4: exact signed16 LSP interpolation, descending half-
polynomial recurrence and shifts for constant endpoints. General Q14 calls
fall from 50 to 20 per LPC reconstruction; no polynomial-array clearing is
needed. Full speech is 2759257254 T, delta -330262705 T versus round 03.
Code/state fall to 6152/1356 bytes; table arena remains 16 KiB. Every sample,
all extra fixtures, primitives and memory guards pass. First-frame table
audit is 2016616 T, delta -291502 T. Accept, with real time still rejected.
See [round 04 report](audiobook-beeper/speex-port/rounds/04/REPORT.md).

## 2026-10-04: Speex round 03, register arithmetic and coefficient tables

Complete TODO item 3. On the original full speech control, register-based
signed multiplication measures 3408073402 T; adding exact per-coefficient
nibble tables measures 3089519959 T, delta -847132343 T versus round 02.
Select the latter despite its larger startup cost (2308118 T first frame).
Include table construction; the aligned table arena is exactly 16 KiB.
Both candidates pass every PCM16/PCM8 value, all extra fixtures and guards;
the selected variant also passes 40960 coefficient entries and 12800
coefficient products. Instruction audits and all general arithmetic checks
pass. Clarify dynamic-table write/immutability metadata in round 02 without
changing measurements. Real time still fails. See
[round 03 report](audiobook-beeper/speex-port/rounds/03/REPORT.md).

## 2026-10-04: Speex round 02, cached innovation tables

Complete TODO item 2 with exact quotient/remainder table generation and
per-gain reuse. Full speech CPU cost is 3936652302 T versus 4128347261 T,
delta -191694959 T including table construction. Reserve 1024 bytes for
792 dynamic table bytes; the arena stays within 16 KiB. Every PCM16/PCM8
sample, seven extra streams, all 8448 possible table entries and guarded
memory checks pass. First-frame instruction count is 2196131 T, delta
-93459 T. Accept; real-time playback is still rejected. See
[round 02 report](audiobook-beeper/speex-port/rounds/02/REPORT.md).

## 2026-10-04: Speex round 01, exact 24-bit excitation

Complete TODO item 1 on the original 186880-sample speech control. Replace
scaled pitch products with signed8x16 and bounded signed24 arithmetic,
preserving every PCM16/PCM8 sample. Full native cost is 4128347261 T versus
4536172045 T, delta -407824784 T; tables remain 12658 bytes. All seven extra
fixtures, 12048 multiplier cases, 5056 energy/shape cases and memory guards
pass. First-frame instruction audit is 2289590 T, delta -71629 T. Correct
the audit's handling of an index prefix split by an emulator frame yield.
Accept the speedup; real time still fails, excluding ULA/disk/hardware.
See [round 01 report and reproduction](audiobook-beeper/speex-port/rounds/01/REPORT.md).

## 2026-10-04: require comments for Z80 routines and complex code

At the user's request, add a project rule requiring useful comments for
major assembly routines and difficult blocks, including generated assembly.
Cover calling conventions and non-obvious arithmetic, layout and timing
without narrating every instruction. No player code or timing changes.

This log preserves accepted, rejected and incomplete experiments. Detailed
calculations and commands remain in the linked `toolkit` reports. The initial
history was reconstructed on 2026-09-17 from reports, builds and Git; unknown
dates of earlier attempts are not assigned that reconstruction date.

## 2026-10-04: assembly Speex-to-PCM port decoder; real-time target rejected

Follow-up authorized on 2026-10-04: execute the saved
[six-item optimization worklist](audiobook-beeper/speex-port/TODO.md), retaining
a separate report and focused commit for each completed step. The initial
commit saves the plan only; no additional acceleration is claimed.

User objective: attempt real-time Speex decoding from RAM on a 3.5-MHz Z80,
with lookup tables within 16 KiB, unsigned PCM8 directly to an 8-bit output
port, no PDM, and a separate worktree. The user subsequently preferred
assembly. Implement the complete narrowband mode-3 decoder in generated,
reviewable Z80 assembly on `codex/speex-port`, retaining C only as a host
oracle and measured initial baseline. Use official Speex 1.2.1 fixed-point
mode 3 (8 kbps), with decoder enhancement/highpass disabled, and the entire
existing 186880-sample 8-kHz speech control. It encodes into 1168 raw frames,
23360 bytes; do not substitute offline PCM expansion for Z80 decoding.

Exact compressed integer-cosine tables, expanded codebooks, energy gains
and a quarter-square multiplier occupy 12658 bytes (12800-byte aligned
span). Default assembly code is 10122 bytes, state 1885, reserved stack 256;
input uses physical banks 0,1,3,4,6,7. The 16-KiB limit is met for tables,
not for the entire program. Output uses low port byte FB and a sample-
dependent high address byte. There is no 8-kHz output pacing or hardware
DAC validation because sustained decoding is already far too slow.

Complete final speech CPU results, with countdown-boundary overshoot
accounted for: C baseline 10083761163 T; ordinary full assembly 5033419430 T
(delta -5050341733); assembly with exact zero/8-bit operand fast paths
4536172045 T (delta -497247385). The final average is 24273.181 T/sample,
55.482 times the available 437.5 T/sample. Synthesis alone costs 13259.530
T/sample. First output is at 883960 T; intervals are 2627..1431069 T, and all
186879 subsequent outputs miss the deadlines anchored at the first output.
Nominal CPU time is 1296.049 s for 23.36 s of audio. Exclude ULA contention,
ROM/disk latency and physical hardware; no playback release is claimed.

Verification: every PCM16 sample and PCM8 output matches unmodified
libspeex for all three complete speech runs. The final assembly additionally
passes six 3200-sample signal fixtures and a full 4915-frame/786400-sample
six-bank capacity stream; input/code/tables stay unchanged and all CPU
writes remain in allocated state/stack. Zero count, excessive count and
unsupported modes are checked. Both assembly variants pass exhaustive
65536-pair unsigned multiplication and 25737-angle cosine tests, plus
10400 signed products, 3000 Q14 cases and 12 saturation edges. Independent
instruction-table audits cover each instruction of one complete first
frame: 4282588 versus 2361219 T, delta -1921369 T. Full-stream counts use
native emulation, not an extrapolation from the first frame.

Exploratory failures/partial work: the initial hybrid assembly filter
clobbered its output pointer when calling SDCC multiplication; saving IY
fixed the local failure, but that hybrid is not claimed as a verified
final variant. An early complete-assembly pitch-history address error and
signed cosine-delta error were fixed before final checks. A measured hybrid
table attempt remained too slow and was superseded by complete assembly.
The first native long-run counter lost a few instruction-tail T-states at
each budget boundary; final reports recover them using the independent
frame clock. Historical approximate counts are not used for the final
comparison. A packet refill guard and six-bank count limit are included.

Decision: retain a correct, bounded-mode assembly reference and reject this
implementation for real-time playback. The user's sine-table suggestion
could replace exact CELP synthesis with a cheaper approximation. A four-
oscillator estimate is 388 T/sample with 4 KiB of sine/amplitude tables,
but excludes parameter extraction, noise, scheduling and ULA contention;
it has not been implemented or assessed for speech quality. Finish this
measured attempt before selecting that separate codec/synthesis experiment.
See [README and reproduction](audiobook-beeper/speex-port/README.md),
[assembly](audiobook-beeper/speex-port/assembly/decoder.s),
[native verifier](audiobook-beeper/speex-port/verify.py),
[instruction audit](audiobook-beeper/speex-port/check_primitives.py), and
[saved evidence manifest](audiobook-beeper/speex-port/evidence/manifest.json).

## 2026-10-04: Sequential audio parts; one TRD by default

The user requests one or many disks, maximum-RAM load/play cycles, and
explicitly selects one TRD as the default. Add `--disk-mode single|all|preview`
to the [automatic converter](audiobook-beeper/IMA3_SERIES.md), a separately
assembled transient TR-DOS controller, per-volume identity headers, automatic
part transitions, next-disk/Space prompts and wrong-disk rejection. Each disk
is independently bootable. All mode covers each source sample once; single
mode stops before the next whole RAM part that cannot fit. Keep global gain,
short edge fades and silent guards. Final quality decisions include complete
execution of the actual published volumes. Disk reads cause audible pauses.

The controller replaces bank-5 PDM tables only after sound stops. Its 57-byte
resident exit fits existing 64-byte padding: bank-2 reservation remains
13312 bytes and maximum packed audio 94458 bytes /251888 samples. Source
capacity excluding the guard is 31.470 s per full part, 157.350 s for five
parts per TRD. Shared tables are stored once per disk. Ordinary phases remain
417/413/458/413/417/446/409/446 T, **427.375 T/sample, delta 0 T**; page/bank
extras +14/+140 T are unchanged. Only the final silent guard exits: 61 native
T to clear the beeper versus 103 T to the former next output without filler
(-42 T), or 22005 T with the reference's filler (-21944 T). These are stop
versus continue endpoints, not an increased sustained PDM rate.

Two copies of the unchanged 186880-sample reference verify all **5980094**
live bits natively and in complete cold Fuse 128 playback. Final-disk SNR is
20.161979 /20.161096 dB, speed about -0.27172%, and automatic loading pause
19.798231 s. A two-disk short fixture verifies both independent boots,
predecessor-RAM continuation and wrong-disk rejection; no disk calls occur
during audio. The final all-seven-bank synthetic-tail fixture verifies
4030175 bits, RAM guards and EOF; cold ready takes 28.608176 s. Its 18.563389-dB
score is below target and is not promoted as a quality release. The ordinary
stereo-input CLI test creates one TRD at 20.978697 dB; silent default/all CLI
tests verify output names and nonapplicable SNR. Five planning/CLI tests pass.
The legacy compact looping disk remains byte-identical.

Retain development findings: corrected assembler string/padding syntax;
corrected signed-marker/Windows-newline trace parsing; exact clock reuse
rejected after a three-T HALT/IRQ alignment difference, replaced with bounded
clock checks and actual-waveform measurement; superseded 251200-sample
reservation passed but wasted 256 bytes, removed after measuring the stub.
The larger final capacity was tested afresh. No physical hardware or real
drive swap is certified. Full counts, inputs, source snapshots, raw traces,
reports and reproducing scripts are in the
[series experiment](audiobook-beeper/experiments/ima-3bit-series/README.md).
Save `ZX-audiobook-IMA3-sequential-test.trd` in LFS as a clearly labelled
two-repeat loading test; preserve previous release disks.

## 2026-10-04: Reduce IMA3 table overhead without changing output timing

The user requests smaller auxiliary table allocations. Audit the current
PDM/IMA3 player; the recent AY player's service tables are already small.
Use the complete unchanged 186880-sample audiobook reference from
`ima-3bit-direct`, baseline TRD SHA-256
`601ba65fa7a12b4b6c67f384ba5ed32530bee95816bb86d8effcc0c7de7d34c0`.
Do not run another codec/quality search. The source uses 88 of 89 IMA indices
and all 120 legal PCM control levels, so retain the complete tables.

[The compact layout](audiobook-beeper/IMA3_MEMORY.md) relocates 352 bytes of
the 2848-byte IMA table into existing aligned code gaps and reduces trailing
reservation padding from 736 to 64 bytes. Bank 2's reservation falls from
14336 to 13312 bytes: **1024 physical bytes reclaimed**. Maximum IMA3 payload
grows from 93432 to 94458 bytes, including two formerly unusable remainder
bytes, giving 251888 samples /31.486 s instead of 249152 /31.144 s. All 89
rows, 712 transitions and PDM feedback states remain exact. The converter
automatically uses the new capacity. Larger external loop fillers skip the
startup gap; a 300-T fixture reserves 13568 bytes. Assembly assertions check
every gap; the maximum normal 1530-pair /260-T filler with seven banks ends
startup at 8365, before the first relocated row at 8380.

The original binary and disk reproduce byte for byte. Pulse/extraction
instruction bytes and addresses remain identical. Native phase totals stay
417/413/458/413/417/446/409/446 T, mean **427.375 T/sample, delta 0 T**;
page/bank extras remain +14/+140 T, delta 0. Complete new native and cold
Fuse 128 reference runs verify all **5981841 outputs /373760 predictor-index
samples** over two repeats. Every relative Fuse timestamp equals the old
trace. This exact waveform/clock equivalence reuses the prior
20.159645/20.159651-dB quality and -0.299133% speed result; it is not a new
encoder search, subjective listening approval or physical-hardware test.

A separate full-capacity fixture appends synthetic silence and verifies
**8060417 outputs /503776 samples**, all seven banks, native RAM guards and
complete cold Fuse loading into the reclaimed bank-2 region. It makes 429
startup sector reads and zero runtime reads; both loading UI checks pass.
This uncalibrated fixture proves capacity, not additional real audio or a
quality-qualified 31.486-s release. The retained 64-level model also passes
262145 native outputs /16384 samples. Accept the compact placement and save
`ZX-audiobook-IMA3-compact-tables.trd` in LFS; retain existing root disks.

[Reproducing verifier](audiobook-beeper/verify_ima3_memory.py),
[comparison and full evidence](audiobook-beeper/experiments/ima-3bit-memory/comparison.json),
[completion audit](audiobook-beeper/experiments/ima-3bit-memory/completion-audit.json).
No additional table/codec experiment is opened by this change.

## 2026-10-04: Generic AY converter and looping music disk

The user asks to convert the same music with the AY method used by the movie
and to provide a reusable script. Existing `audiobook-ay/build_preview.py`
already accepts arbitrary audio but has an audiobook screen and a one-shot
player. Add [convert_audio.py](audiobook-ay/convert_audio.py) around the
unchanged movie analyser/square fit, plus a separate, commented
[ASM player](audiobook-ay/ay-player.asm). Python supplies constants/data and
packages the assembled binary; it emits no instructions. The generic CLI
handles arbitrary FFmpeg input, a bounded initial excerpt, title/start/duration,
looping by default or optional one-shot playback, chip-model previews and
optional complete native/Fuse verification with normal-speed WAV capture.

Use the same original The Entertainer recording and requested 31.128-s initial
interval as the preceding PDM experiment. The 50-Hz grid retains 31.12 s /
1556 ticks; no 8-kHz intermediate is used. Resident audio is 17116 register
bytes, AY9 is 14004 bytes before archive gzip. Six audio banks raise capacity
to 8934 ticks / 178.68 s; fixed code, screen, stack, IM2 and TR-DOS banks are
accounted separately. Full capacity is native-tested with synthetic data,
not claimed as a complete longer recording. Mono Ayumi YM2149 rendering uses
the actual three tone generators, one shared noise generator and chip DAC
levels. No original waveform is added to the synthesis.

The ordinary path remains 974 native T (delta 0 from the earlier AY player);
near-bank, bank-change and exact-boundary EOF costs remain 992/1091/1007 T.
Restart adds 105 T once per repeat, giving a 1079-T first repeated field;
tick zero is published on the original next interrupt, with no extra silent
field. Five unit tests cover the old player, IRQ preservation, one-tick loops,
all important bank/EOF boundaries, and both complete six-bank repeats.
Initial assembler directive syntax errors were corrected before these tests
passed; no failing binary was delivered. Loading-message clearing is boot-only
and adds zero playback T-states.

The first complete prototype passed two cold Fuse repeats before adding the
loading label; preserve its reports and disk under
`audiobook-ay/music-preview/attempts/before-loading-label`. The final disk
again passes all 34232 register writes / 3112 nominal fields, no missing or
duplicate fields, 67 startup reads and zero runtime reads. First-OUT phases
are 150..255 T and intervals 70805..71010 T, including wrap. The loading
message is shown before payload reads and cleared before playback; all 768
bitmap bytes in its area are checked. Normal startup is 10.677687 s and the
two-repeat Fuse WAV is 62.226236 s. Clock-derived tempo error is +0.042308%.
ROM/disk loading and ULA waits are separate from deterministic CPU counts.

Musical signal proxies are spectral cosine 0.892788, chroma cosine 0.975713,
loudness correlation 0.995346 and onset F1 0.887097. These are not waveform
SNR, percentages of fidelity, or listener acceptance. Deliver
`ZX-music-Entertainer-AY.trd` and the actual Fuse WAV as a listening comparison.
See [instructions and evidence](audiobook-ay/CONVERTER.md). Physical hardware
has not been tested. Existing movie, audiobook and beeper releases are retained.

## 2026-10-04: Public-domain music example with direct packed IMA3

The user requests a recognizable melody on TRD, selects an unrestricted
recording instead of Queen, and explicitly accepts the highest found SNR
even below 20 dB. Use Scott Joplin's The Entertainer, performed by IE; the
source page separately declares the composition public domain and the
recording dedicated to the public domain with a permission fallback.
Preserve the exact downloaded Ogg, attribution, page revision, URL and hash
in [the music example](audiobook-beeper/experiments/ima-3bit-entertainer/README.md).

Run the unchanged automatic converter from acf1682 on the initial 31.128 s
of stereo 44.1-kHz Vorbis, preparing 249152 mono 8-kHz PCM8 samples with the
128-sample guard. This fills 93432 bytes of packed IMA3 across all seven
resident audio banks. No IMA4, full PCM or PDM expansion buffer is added.
The Z80 hot path stays 427.375 native T/sample, delta 0 T; page/bank extras
remain +14/+140 T. The selected native loop costs 106544136 T; the actual
Fuse loop costs 110829204 T including ULA effects. Disk/ROM startup remains
separate, with 425 startup sector reads and zero runtime disk reads.

The uncompensated pilot measures -3.279182/-3.279105 dB and is rejected for
delivery. Automatic host searches at width 256/horizon 128, width 512/horizon 128
and width 1024/horizon 256, all regularization 0.03, score 17.598735, 17.663213
and 17.837011 dB. Execute the selected third candidate on a new cold-booted
disk: complete loops measure 17.837011/17.836344 dB, -0.328930% speed error,
127652.897 mean PDM outputs/s and 0/0-T phase errors. Full native and Fuse
verification covers 7977485 outputs and 498304 predictor/index samples;
memory guards, all banks, 32 loading progress steps and message hiding pass.
Normal-speed Fuse capture confirms two wraps, correct paging latches,
26.454422-s cold startup and a 62.505964-s WAV, with signal in every half-second
window. Integrity-checked resume reuses all six stages and returns the
expected quality-status exit code 2 without replaying the audio.
The source and comparison filter stay fixed; no fitted gain/delay/time
stretch is used. First/second search results remain host estimates only.

Deliver `ZX-music-Entertainer-IMA3.trd` as the user-authorized listening
preview. The converter correctly retains its 20-dB gate failure and exit code 2;
do not claim 20 dB, a universal maximum, or physical-hardware verification.
Keep the existing 20.1596-dB audiobook release unchanged. The source, TRD,
WAVs and large trace data use Git LFS; reproduction commands, full selected
trace, timing data, measurements and unsuccessful search results are saved
with the example.

## 2026-10-04: Packed IMA3 playback, uniform table timing and automatic conversion

The user requests removal of the IMA3-to-IMA4 conversion, optionally higher
PDM frequency, at least20 dB final SNR, asks whether25 dB is possible, and
requires the complete conversion workflow to run automatically. Keep the
same complete186880-sample source/hash as the previous20.071-dB delivery.

Implement a separate assembler player that consumes eight little-endian
three-bit codes from each three bytes in resident RAM. Reorder packet
entries to defer the FIRST pointer and use eight extraction phases. There
is no resident IMA4, PCM or PDM expansion buffer. Resident audio falls from
93440 to70080 bytes; full available capacity is93432 IMA3 bytes /249152
samples (31.144 s at8 kHz, including the guard). The new native capacity
probe covers7972865 bits and498304 predictor/index samples over seven banks
twice, with synthetic silence after the original clip; no longer real audio
or physical-machine verification is implied.

The unpadded408.375-T prototype (+2.8701% speed) is rejected. The420.375,
422.375,423.875 and425.875-T padding trials retain complete native/Fuse
verification but fail quality on the unchanged old encoded data. A measured
64-level model gives19.288/19.654-dB host estimates, but a real new disk falls
to2.604/2.598 dB because signal-dependent table contention changes its sample
schedule by0.766 ms. Preserve every meaningful attempt and assembly input in
[the ledger](audiobook-beeper/experiments/ima-3bit-direct/attempts.json).

Move all120 supported128-level PDM rows into the same contended bank5 memory
class (two rows/page), keep all89 compact IMA rows in uncontended bank2, and
constrain offline control levels to4..123 with feedback clipping3..12. This
does not attenuate, crop or replace the source reference. Exact-rational
checking covers4096 table cases. A rejected earlier128-level model needed
22 states /132 bytes per row; it also exposed a floating-point tie error.
The corrected model and table-layout guards are independently checked.

Ordinary cost is427.375 T/sample, **+4.375 T** from the prior423-T player and
+1.5 T from the padded64-level direct experiment. Page and bank overhead
remain+14/+140 T. Loading progress has zero playback cost. The full width256
candidate takes79891688 native T per cycle, then83104176 T including actual
ULA waits:23.430087 s, -0.299133% speed and127652.961 mean PDM outputs/s.
This does not improve the previous128053.556-Hz mean rate. Runtime disk
reads remain zero;32 loading progress steps and message hiding pass.
Uniform-memory sample schedules differ by only0..3 T (<0.846 microseconds)
across the tested changed payload/model, versus the old0.766-ms discrepancy.

A width256/reg0.03 host estimate19.952800 dB becomes19.944257/19.943702 dB in
complete cold disk loops, still below20. Width512/reg0.01 scores19.938054 dB
on that earlier host schedule. Do not label these as passing releases.
The source clock, integration rate, filter, edge exclusions, amplitude and
full excerpt remain unchanged; no gain, delay or time-scale fitting is used.

Add `convert_ima3_audio.py`: arbitrary FFmpeg input, bounded initial excerpt,
separate assembler, automatic cold timing calibration, waveform search,
complete native/two-loop Fuse checks, best measured candidate, WAV and TRD.
It supports an explicit25-dB target and integrity-checked resumable stages.
Below-target results return exit2 and remain previews. A stereo24/16k
input-path smoke test gives20.948752/20.949015 dB and -1.134646% speed; a
separate25-dB invocation gives20.948905/20.948362 dB and correctly fails its
target. These2-s tests do not replace full-source acceptance. All three
completed stages resume without recalculation; modified cached data is
rejected. Default4-bit encoding remains byte-identical on regression fixtures.

The earlier no-IMA, ideal128-kHz host study's25.81 dB concerns another input
and algorithm, not this TRD or physical hardware. Keep that distinction in
[the implementation notes](audiobook-beeper/IMA3_DIRECT.md).

The completed automatic run extends the PC horizon to128 samples at
width256/weight0.03: host20.159645 dB, then **20.159645 /20.159651 dB** on
both complete new cold-Fuse loops, phase0/0 T. This satisfies the20-dB gate
on the unchanged full source. No additional Z80 work is introduced. The
superseded width1024/64-sample search was interrupted after65536 samples
of progress and is preserved as incomplete. The final automatic stereo24
smoke test measures21.116910/21.115089 dB; it remains a separate short input.

Normal100%-speed recording confirms both wraps, matching paging latches,
continuous activity and **22.815238 s** cold boot to audio (<60 s); recorded
playback is46.869388 s. Complete-run resume reuses all four hashed stages,
including the sound capture. Cross-run pilot reuse checks the exact source,
player, tools and remaining producers; a one-sample source change is rejected.

Save `ZX-audiobook-IMA3-direct-test.trd` (SHA256
`601ba65fa7a12b4b6c67f384ba5ed32530bee95816bb86d8effcc0c7de7d34c0`),
normal WAV, pilot, assembly, producer snapshots, per-attempt results and
[completion audit](audiobook-beeper/experiments/ima-3bit-direct/completion-audit.json).
Decision: deliver direct packed IMA3 and the automatic converter.25 dB is
not achieved; no physical-hardware or arbitrary-recording SNR guarantee is
made. Keep the earlier expanding disk and all rejected evidence.
A final whitespace-only source cleanup leaves the Python AST and entire
rebuilt TRD byte-identical; its proof and original measured producer bytes
are archived. No additional playback verification is needed for that cleanup.

## 2026-10-03: measured instruction cost on eight external TR-DOS disks

Answer the user's request for an empirical Z80 instruction average using
five games (Dizzy, Elite, Exolon, R-Type, Renegade), Aeon, the 63 BIT
credits/menu and Beta Commander 5.02+. Download exact SCL archive versions
from Virtual TR-DOS; preserve URLs and hashes. Instrument a separate,
pinned Fuse libretro core on Pentagon 128K, with existing ROMs, to count
completed instructions, nominal/elapsed T, HALT idle cycles, block-repeat
continuations and RAM/ROM/TR-DOS attribution. Player code is unchanged.

The eight visually checked 1500-frame windows total 245.76 emulated seconds,
79425697 instructions/iterations and 698325097 nominal T: 8.792181 T per
instruction, with per-program means 7.432900..10.362469. Equal-program mean
is 8.742091; five-game pooled mean is 8.870355. Counting whole repeating
block operations once gives 8.903544. HALT idle is 18.792692% of selected
elapsed time; including it and interrupt-entry time gives 10.829744 T per
executed instruction as a throughput measure. Observed nominal costs span
4..23 T. Preserve separate startup windows and actual TR-DOS ROM counters.

An independent 2073-instruction fixture matches 20705 nominal T and its
complete histogram, with 735 extra contended T versus zero for uncontended
data, correct block repeats and HALT handling. All final histogram counts,
weighted T sums and clock decompositions reconcile. This is a bounded
emulator convenience sample, not a population average, hardware timing,
complete-game test or player release. Pentagon has no ULA contention;
original Sinclair 128K elapsed overhead is not measured by this sample.

Exploratory attempts are retained locally: F Commander 5.5 returned to the
Spectrum menu, including a local boot-name experiment, so replace it with
Beta Commander. Initial model-comparison validation loaded the same 48K
snapshot twice; correct the final test to an explicit two-address-region
48K comparison. Resolve startup trainers, game controls and R-Type's sixth
Detach key before final sampling; do not count failed menu pilots as play.
Accept the measured result for the requested informational survey. Reuse
[scripts, methodology and compact evidence](toolkit/instruction_survey/README.md)
instead of rerunning the study without a new sampling question.

## 2026-10-03: IMA3 waveform disk passes the mandatory 20-dB gate

Preserve the complete original186880-sample source and its hash
`ea3c0d945a0cc349747664c137c3725aee3fe8cf5e17b991ae3e24f51829a304`.
Extend PC waveform-aware beam search with the even-nibble IMA3 alphabet,
including exact silent settling. Keep default four-bit behavior byte-identical
on the regression fixtures. The selected width32 /64-sample /weight0.1 search
scores20.208549 dB on the old pilot clock; a newly assembled, calibrated and
fully executed IMA3 disk confirms **20.07106694 dB in each cold Fuse loop**.
Baseline was18.171046/18.152640 dB. No fitted delay, gain, source shortening
or comparison-filter change is used. This meets the user's minimum20-dB
requirement for the control excerpt in the emulator, not every recording
or physical hardware.

During the work, the user increases preparation allowance from39.904 to
**60 s** and permits later decoder optimization. Add an explicit verifier
limit override while preserving the historical raw128 benchmark. Actual
cold expansion is1.934749 s; compressed-data ROM reads11.045818 s;
preloader entry to ready18.683671 s. Normal reset/boot to audio is27.254263 s,
and the two-loop sound capture lasts46.749410 s with matching paging latches.

Transport remains70080 bytes (+64 sector padding), expanding to93440 IMA
bytes. The473-sector bootable disk accounts for all131072 RAM bytes and
uses no full PCM/PDM buffer. Expansion remains285 T/eight samples and
6896434 native T total, delta0. Ordinary PDM remains423 T/sample, page14 T,
bank140 T extra, each delta0. Silent calibration uses1273 pairs /69 T pad
instead of67 T; native cycle79122530 ->79122532 T, delta+2 T. Complete Fuse
cycles are82891452 T each, phase0/0, speed error-0.043271%.

Each native/cold Fuse playback check covers5985253 outputs and373760
predictor/index samples. All preload bytes, seven output banks, progress
steps, RAM guards, loading display and zero runtime disk reads pass.
Independent FFmpeg verifies all186880 IMA samples. Normal recording checks
both wraps and audio activity; the recorded disk hash matches the full trace.

A width128 host search started while the full width32 check was pending
scores20.518986 dB on the pilot schedule. Preserve it as an unexecuted
candidate; once width32 passes the actual required gate, finish that delivery
instead of promoting a host-only score. The acceptance margin is0.071 dB,
so no large-margin or perceptual-transparency claim is made.

Save the separate `ZX-audiobook-IMA3-waveform-test.trd`, normal WAV, complete
[audit and evidence](audiobook-beeper/experiments/ima-3bit-waveform/completion-audit.json),
producer snapshots, timings and both host trials. Keep the prior18-dB disk.
Reproduce with [the commands and methodology](audiobook-beeper/IMA3_WAVEFORM.md).
Decision: deliver the verified compressed disk; the requested20-dB goal is
achieved within the new60-s budget. A Speex port remains separate research.

## 2026-10-03: Speex audition and exact Z80 arithmetic feasibility

After the user makes final PDM SNR >=20 dB mandatory and requests Speex,
test the unchanged186880-sample control, hash
`ea3c0d945a0cc349747664c137c3725aee3fe8cf5e17b991ae3e24f51829a304`.
Preserve all speech, fixed8-kHz clock/gain and the standard comparison filter.
Run10 initial FFmpeg cases at8/11/15/18.2/24.6 kbit/s using both decoders,
then30 controlled API cases with unmodified Speex1.2.1, complexity10,
CBR and no VAD/DTX. Compare highpass/enhancement options and float/fixed
decoding. Include the silent flush frame and a32-byte framing allowance.

Default processing has poor waveform scores even after its disclosed
79-sample fitted integer delay. Controlled tests remove only the declared
40+40-sample latency. With both optional filters disabled, fixed-point
18.2k/24.6k scores24.752/27.823 dB; existing threshold IMA yields
21.054/22.037 dB at6.946:1/5.155:1 relative to PCM16. Record all rejected
IMA saturation paths. These scores exclude PDM and are not release passes.

Compile and execute an optimistic exact signed16x16 table-product kernel.
Every1376146 input pair is exact; all calls cost128 T (111 T plus17 CALL),
using1792 bytes per coefficient. Ten products/sample for the full source
project207436800 T /58.484 s without calls;67.441 s with calls. Exclude
table generation, argument setup, MAC/state work, excitation, LSP, IMA,
disk, ROM, ULA and paging explicitly. This fails39.903992 s already and
rejects this strategy, not every conceivable Speex implementation. A full
decoder has not been ported or timed. Existing PDM stays423 T/sample,
delta0; no TRD, cold Fuse PDM or physical hardware qualification is added.

Initial host build attempts fail on Windows command quoting, compiler
discovery and localized log decoding. Correct the helper and preserve
successful raw logs; no upstream codec algorithm is changed. Save the
official source archive/license, build hashes, compressed frames, reports,
and selected audition WAVs. The IMA waveform-search extension considered
before the user's Speex steering was not implemented or measured.

Decision: retain24.6k as the best fidelity reference and18.2k as the more
compact audition; defer a full port under the current startup budget.
The final20-dB objective remains unmet. Reproduce using the three Speex
probe scripts and host builder linked in
[the study](audiobook-beeper/SPEEX_STUDY.md), with
[saved evidence](audiobook-beeper/experiments/speex/manifest.json).

## 2026-10-03: bootable IMA3 preload disk and voice-timing correction

Create the requested new-compression TRD on the unchanged full 186880-sample
8-kHz control. Store 70080 bytes of the even-nibble IMA3 subset, plus 64
sector-padding bytes, and expand thirteen blocks through a 6144-byte buffer
into all 93440 resident IMA bytes. Preserve independent cold boot, seven-bank
allocation, progress bars, disappearing loading message and looping PDM.
Occupied file sectors fall from 517 to 473 including the new preloader:
25% audio-payload saving, but 44 sectors / 11264 bytes net disk saving.

The final full native preloader costs 6896434 T, 238504 T more than the
standalone round-3 benchmark; its expansion core remains 285 T/eight samples.
Cold Fuse checks every expanded byte and all progress steps. Real compressed
data ROM service is 11.064859 s, expansion is 1.935179 s including ULA,
and preloader entry to player-ready is 18.720633 s. Initial BASIC/bootstrap
loading precedes that interval. Conversion is within the 39.903992-s limit.

The uncorrected pilot passes full native/Fuse bits but fails fixed-clock
fidelity at -3.004 dB; its warped-reference score is 18.522 dB. The user
hears added voice vibration during its normal-speed recording. Apply the
existing Lanczos timing compensation on PC, re-encode IMA3 with beam32,
freeze the hot-row layout and recalibrate. The new complete traces measure
18.171/18.153 dB at -0.04327% speed error. This improves the timing-related
error; it is not a claim of perceptual transparency or attainment of 20 dB.
Keep the pilot reports and recording for comparison instead of discarding
the unsuccessful first result.

For each final playback check, verify all 5985253 outputs and 373760
predictors/indices over two loops, exact native timing, paging and RAM guards.
FFmpeg independently reproduces all 186880 IMA samples. Actual Fuse cycles
are 82891450/82891452 T (-2/0 T from 1169 fields). Native playback remains
423 T/sample, +14 T/page and +140 T/bank, each delta0. The final silent tail
uses 1273 pairs and 67 T padding; cycle79122530 T is 2 T below the pilot.
The final normal-speed capture checks both wraps, paging and audio activity.

An initial full-trace run pauses in the debugger before execution because
Fuse rejects underscores in variable names. Confirm with a minimal parser
probe, stop only the owned process, rename the variable and rerun fully.
This is a harness failure, not a player failure. Preserve the correction
in both the all-bit verifier and the audio recorder.

Deliver this as a listening preview, not a 20-dB release or a physical
hardware qualification. Keep the higher-fidelity four-bit player as the
existing quality reference. See [IMA3_PRELOAD.md](audiobook-beeper/IMA3_PRELOAD.md),
its scripts, archived reports and WAVs. No claim of longer resident playback
follows from the smaller disk payload.

## 2026-10-03: three native optimization rounds each for IMA3 and PVQ3

Under the relaxed 5:1..10:1 preference, optimize only the user-selected
three-bit IMA and predictive VQ decoders. Reuse the complete 186880-sample
control and existing dense-codec payloads; do not retrain or change quality
while comparing CPU cost. Discover that ADPCM3-step6 is an exact subset of
ordinary IMA: expand each code with `nibble = code << 1`, avoiding PCM
synthesis and re-encoding. Independent predictor/index checks pass and
the final state is 0/0. Compression is 5.331:1 including 32-byte framing,
or 5.254:1 if the fixed 1024-byte lookup is charged too.

IMA expansion baseline and rounds 1..3 cost 2515/1947/397/285 T per eight
samples. Unroll bit extraction, substitute byte algebra, then four lookup
tables. Full native totals are 58750730/45482250/9274250/6657930 T, including
55 T setup per chunk; final 1.877 s versus 16.564 s baseline. All 93440
output bytes, code/input/table protection and buffer guards pass. An initial
round-3 `LD L,IYH` was rejected by the assembler and replaced by two valid
loads; setup accounting was corrected from 64 to 55 T before final reports.

PVQ3x512 rounds keep history in IXH, replace address arithmetic with 512
lookup bytes, then dispatch/store once per three-sample vector. Totals are
31352427/30106547/29172137/17460865 T: final 4.923 s versus 8.839 s baseline.
Verify all 186880 source samples plus two vector-padding samples, exact
instruction-path histograms, input/table protection and output guards.
The reproduction script now creates a fresh output directory itself.

These are native CPU/buffer proofs, excluding disk/ROM, ULA, full resident
bank management and (for PVQ) subsequent IMA encoding. No new disk or final
PDM SNR is claimed. Existing codec-only SNR is 20.999 dB for IMA3 and
22.185 dB for PVQ3, reused from the prior study. Ordinary playback remains
423 T/sample, delta 0. Preserve all four assembled versions, WAV previews,
cycle deltas, scripts and reports in
[DECODER_OPTIMIZATION_ROUNDS.md](audiobook-beeper/DECODER_OPTIMIZATION_ROUNDS.md).
Prefer exact IMA expansion for the next integration, with full cold-start
and playback validation still required.

## 2026-10-03: 10:1 waveform codec study rejects low-fidelity candidates

After the LPC rejection, the user prioritizes fast preparation and sound
preservation, defines10:1 relative to mono8-kHz PCM16, permits unlimited PC
encoding complexity and asks for research on existing codecs. Reuse the
complete186880-sample PCM8 control signal; its PCM16 storage denominator
is373760bytes, not newly recovered16-bit precision. Include every book and
a32-byte framing allowance. Compare FFmpeg DFPWM8/12k and G.72616k, five
ordinary VQ sizes, shape/gain VQ and predictive VQ. G.7266k/12k is rejected
by FFmpeg and not called a supported mode. The best simple qualifying VQ
uses33652bytes (11.107:1), but delivers only14.213dB codec SNR /13.744dB
after IMA. VQ8/1024 is48bytes over the10:1 limit. No row reaches the proposed
25..30dB codec fidelity target; that target is advice, not user approval.

The full native VQ7-to-IMA probe verifies186880 PCM values and IMA nibbles,
both input banks and read-only tables. Decoder paths are49/203/206/262/265T
excluding CALL; the actual input-wrap path is288T. Total148778057T /41.946s
already exceeds the39.904s budget before ULA and final output-RAM handling.
An initial harness frame-yield handling error was fixed; the full run then
passed exact output checks. Reject this candidate for fidelity and startup;
do not present it as a working TRD. No player hot-path change:423T/sample,
delta0. The ordinary baseline disk rebuild is byte-identical.

Research official ADPCM-XQ, G.726, Speex, G.729, Opus, QOA, CVSD/DFPWM,
WavPack and Codec2 documentation. Select high-effort ADPCM encoding as the
best immediate Z80 architecture fit, with Speex11k/Opus12k as prospective
listening references, not proven Z80 ports. No candidate is claimed to
meet all requirements. Preserve measured reports, payloads and WAVs in
[TEN_TO_ONE_CODECS.md](audiobook-beeper/TEN_TO_ONE_CODECS.md).

The user subsequently relaxes the preferred ratio to 5:1..10:1, with
higher compression welcome if fidelity survives, and selects three-bit
IMA and predictive VQ for three optimization rounds each. Preserve the
[format backlog](audiobook-beeper/CODEC_RESEARCH_BACKLOG.md), including
previously rate-excluded options, source links, measured failures and
unmeasured candidates. This does not authorize or schedule every listed
port; the selected decoder rounds are a separate experiment.

## 2026-10-03: LPC-to-IMA preload with progress is correct but rejected as too slow

Create the user-requested `codex/lpc-ima-preload` branch and separate
`.worktree/lpc-ima-preload` checkout. On the unchanged full 186880-sample
8-kHz control excerpt, implement LPS1 storage (32736 bytes), actual Z80
ten-stage lattice synthesis and standard IMA encoding into all 93440 audio
bytes. Sector-count and emitted-byte progress bars each reach 32 verified
steps. The independently bootable experimental disk loads its own code,
LPC and playback tables. Existing player hot-path cost remains 423 T/sample,
delta0; the generic converter default and root disks are unchanged.

An initial low-gain host attempt produced PCM111..150; fixed normalization
produces PCM32..224, without counted forward lattice clips or IMA saturation.
A two-billion-T native budget stopped after 170400 correct samples; raising
only that harness limit verifies every PCM/IMA byte and final paged RAM.
Complete native preparation costs 2192183887 T (618.056 s), excluding ROM,
disk and contention. Cold Fuse conversion takes657.181 s. The initial timing
question compared with compressed LPC loading (5.326 s); the user clarified
that the limit is twice a complete raw128-KiB read. A real512-sector cold
Fuse benchmark gives19.952 s, so the correct limit is39.904 s.

Reject LPC preload: it fails that limit and the user finds LPC changes the
sound too much. A cold phase probe reaches playback, but complete PDM bits,
final-loop calibration and physical hardware are not qualified for this
rejected disk. Preserve the attempt, progress implementation, inputs,
standalone assembler sources and reports in
[LPC_PRELOAD.md](audiobook-beeper/LPC_PRELOAD.md). The next authorized work is
an alternative-codec study; do not promote this prototype to a release.

## 2026-10-03: waveform-aware IMA reaches 21.01 dB in two complete Fuse loops

Continue the 20-dB goal without shortening the original 186880-sample,
8000-Hz PCM8 control excerpt or expanding its 93440-byte IMA payload.
Change only the PC encoder: beam search carries decoder/modulator state
and six analytic filter states, scoring the actual filtered PDM waveform.
The analog baseline reproduces 19.00195 dB versus the established
18.99410-dB FFmpeg measurement; final acceptance still uses the original
fixed 8-kHz reference and the unchanged 70/4500-Hz comparison filter.

Record the failed initial-prefix search: width 16, uniform prior and weight
0.00001 yield 9.83315 dB with excessive control excursions. A compensated
prior and weight 0.1 give 18.19550 dB at width 32; width 64 plus quantized filter
history gives 18.36698 dB. These three results use the old timeline only;
none is a new disk or a 20-dB claim for the different, quieter prefix.

On the original complete excerpt, width 32/weight 0.1 predicts 21.99406 dB.
Build the ordinary live-IMA player, freeze the old hot-row layout and
recalibrate the changed stream in four phase probes. Complete cold Fuse
execution measures **21.010690/21.010690 dB**, not the optimistic host score.
Both loops take **82891452 T /23.37011249 s**, with zero repeat-phase drift
and **-0.043271%** speed error. All **5985253 PDM outputs /373760 predictors
and indices** pass both native and Fuse checks. Memory, paging, 425 preload
sectors, zero playback reads and loading indicators pass. Independent
FFmpeg IMA reconstruction checks all 186880 predictors. Normal-speed Fuse
capture records 46.74943 s, two wraps and signal in every half-second window.

Ordinary instructions remain **423 T/sample**, page/bank extras **14/140 T**,
each delta 0. The calibrated silent tail changes from 1274 pairs/212-T pad to
1273 pairs/69-T pad: added native work 66495 ->66300 T. Native loop totals
79122727 ->79122532 T (-195 T); ULA contributes 7537840 T across two loops.
Average PDM rate 128053.56 writes/s is not a uniform clock. Full 128-KiB RAM
allocation, source length and live decoding are unchanged. Archive 89 hashed
artifacts and 23 producer sources, keeping bulky raw traces locally by hash.

Accept the 20-dB result for this complete emulator-verified benchmark. It is
not a physical hardware measurement, a guarantee for arbitrary recordings
or a default-converter replacement. Keep the separate new disk; historical
root disks remain unchanged. The denser PVQ study still requires integrated
PDM scheduling before it can claim real-time playback. Reproduce with
[encoder](audiobook-beeper/ima_waveform_encoder.py) and
[full verifier](audiobook-beeper/verify_waveform_disk.py); see
[method, disk and WAVs](audiobook-beeper/WAVEFORM_IMA.md) and
[archived report](audiobook-beeper/experiments/ima-waveform/report.json).

## 2026-10-03: locate the remaining PDM noise and reject coarse corrections

Continue the 20-dB goal from both complete saved timelines. On the older
excerpt, timing target /IMA16 /six-bit level /PDM stages score
25.25390/22.58842/21.49069/18.99410 dB. On the initial prefix they score
28.95125/25.07499/20.58585/15.80350 dB. The latter has half the source RMS;
the main remaining error is amplitude selection/modulation, not a missing
gain correction. Both baseline final scores reproduce exactly.

Reject greedy packet-area steering: unrestricted six-bit controls score
12.08682 dB; feedback0.5/1 worsens this to11.87138/10.67521 dB. Nonlinear
64-level maps help only modestly: weak/medium/strong give
19.36783/19.33124/19.23206 dB on the old excerpt and
16.54155/16.56011/16.56071 dB on the initial prefix. They fit the existing
counted state/pattern bounds (14080..14336 resident bytes, unchanged planned
423-T paths), but their new contention has not been executed or verified.

A bounded robust-word search uses only the medium palette's10320 supported
pattern combinations and16 feedback states. Error-energy plus covariance
weights0/4/16/64 score15.78310/15.82289/16.20488/16.35899 dB, all worse
than its original16.56011 dB. Reject that cost function; do not continue
this weight sweep. All candidates are host-only on old clocks; no new TRD,
runtime, physical hardware or20-dB success is claimed. Native code remains
unchanged (423 T/sample, zero delta). Next optimize the actual filtered
waveform in the PC encoder while retaining the live IMA decoder.
[Method and reproduction](audiobook-beeper/RECONSTRUCTION_ERROR.md),
[evidence](audiobook-beeper/experiments/reconstruction-error/manifest.json).

## 2026-10-03: general audio-to-TRD conversion with per-input timing checks

Implement the requested one-disk converter for arbitrary FFmpeg-readable
local audio, retaining its initial resident fragment and explicitly reporting
truncation. Prepare mono 8-kHz PCM8 with fixed peak normalization, short edge
fades and a silent loop guard; encode with beam-32 IMA. Keep IMA as the
verified default while the denser PVQ decoder remains a separate candidate.
For each encoded stream, calibrate the silent tail against real Fuse loop
periods, measure the complete timeline, compensate source timing, re-encode
and recalibrate. Compare up to two compensation passes against the original
prepared 8-kHz clock, requiring both repeats and +/-2% mean speed.

Generalize the existing player to 256..93440 compressed bytes, loading only
used banks and right-aligning a partial final bank. All executed instruction
paths retain their counts: **423 T/sample, +14 T/page, +140 T/bank; delta 0**.
The prior weighted and phase-locked full disks reproduce byte for byte.
Minimum 256-byte and partial-bank 16640-byte payloads pass two complete native
and cold-Fuse loops with exact bits/predictors, protected memory, paging,
loading indicators and no runtime reads. One-second M4A and 37-ms silent
stereo WAV conversions pass; silence reports null SNR. Existing output
directories are rejected without modifications. A source-snapshot test's
initial expected count was corrected from 20 to the actual 19 files; all
archive digests then passed.

The full run uses the actual audiobook's first **23.344 seconds**, not the
older comparison excerpt, filling 93440 IMA bytes. The first compensation
pass measures 15.40508/15.40829 dB; the second wins with
**15.80350/15.80023 dB**. Mean prepared-sample speed is **-0.04327%** from
8 kHz. The output still does not meet 20 dB; do not compare this different
source directly with the older 18.99410-dB checkpoint. The final native loop
costs 79122946 T, with 7537011 additional ULA T across two loops. Compared
with the prior excerpt's 79122727 T, the 219-T increase comes entirely from
the newly calibrated idle tail (1281 pairs, six groups, 60-T pad); ordinary
playback code is unchanged. Full checks cover 5985285 bits / 373760 predictors
and indices, 425 startup sectors and zero runtime reads. Normal-speed capture
and full native/cold-Fuse evidence accompany the final disk; no physical
hardware claim is made. The full-trace repeat-phase guard was added while
the long conversion ran and is also applied to its saved final trace;
this additional post-check is recorded separately from emulator execution.
New conversions save producer sources at startup and also retain the
uncompensated pilot if its measured quality is better.
[Usage and timing](audiobook-beeper/CONVERTER.md),
[converter](audiobook-beeper/convert_audio.py),
[evidence](audiobook-beeper/experiments/audio-converter/report.json).

## 2026-10-03: compare denser audio codecs and execute a PVQ decoder

Study the unchanged 186880-sample /8-kHz source with ten codec/predictor
choices, counting recording-specific dictionary bytes. A three-sample,
1024-entry predictive vector dictionary with half-last-sample prediction
uses **80940 bytes vs93440 IMA bytes (-13.38%)**, with codec-only SNR
**24.34763 vs24.97253 dB**. The 512-entry version saves23.35% but scores
22.18453 dB; 3-bit ADPCM saves25% but scores20.99909 dB. Retain IMA as the
verified default; select PVQ1024 as a candidate for future PDM integration.
Byte-Huffman IMA payload saves11.08% before its book; gzip saves13.19%.
Neither lossless compressor has a live decoder timing result here.

Compile the standalone PVQ Z80 probe externally and execute8196 samples,
checking every decoded byte, interval and all memory. Decoder body paths
are **51/193/216 T**, averaging **100.25 T vs131 T (-30.75 T)** for IMA;
the worst boundary increases by85 T and must be scheduled ahead of time.
Test-only OUT/JP adds21 T, excluded from decoder comparisons. The probe
uses4096 RAM bytes for the3072-byte book plus512 pointer bytes; no final
RAM-capacity or PDM-rate claim follows from the mean. No ULA, disk, physical
hardware or complete PDM player test was performed for PVQ. The first
INCBIN assembly failed; replacing it with supported MDAT fixed the build.
Full-source host quality and partial-source native coverage are separate.
Root disks are unchanged; this does not satisfy the20-dB end-to-end goal.
The measured quality table uses packed indices; full native five-byte group
alignment adds two bytes (80942 total rather than80940), explicitly accounted
for separately from dictionary RAM expansion.
[Method/reproduction](audiobook-beeper/DENSE_CODECS.md),
[comparison](audiobook-beeper/experiments/dense-codecs/report.json),
[native evidence](audiobook-beeper/experiments/dense-codecs/native/report.json).

## 2026-10-03: stabilize compensated voice across repeated playback

Extend the complete 186880-sample /93440-byte speech experiment with a
balanced high-frequency idle tail; keep every source sample, live IMA
decoding, the loading UI, all RAM accounting and 423-T ordinary samples.
The final 1274 output pairs /five groups /212-T pad add **66495 CPU T per
loop**, for **79122727 native T**. ULA separately adds 7537450 T over two
loops. Full native/cold Fuse checks pass **5985257 bits /373760 predictors
and indices**, all native timing/RAM, paging and loading checks. FFmpeg
independently confirms all IMA samples; normal-speed capture passes two wraps.

Both actual loops are exactly **82891452 T /1169 fields /23.37011249 s**;
the PCM-count equivalent is -0.04327% from 8 kHz. Compensated speech is
compared with the explicitly chosen original 8-kHz clock, zero-extended in
the silent tail. Both loops score **18.99410 dB**; 20 dB remains open.
The 0.1-s PCM-count windows crossing the added silence fail the old window
gate (worst -16.55%); retain this result and distinguish it from voice pitch.
One-second windows stay within 1.91%. Physical hardware was not measured.

Record the unsupported DS syntax repair, rejected 600-pair calibration,
reverted JR page-branch probe, full 1270/222 pilot, and re-encoded stream
whose phase drift required the final 1274/212 adjustment. A bounded beta
and extent probe found no worthwhile executable improvement; keep its
host-only scores separate from the final measured table. Root TRDs are
not replaced by this checkpoint. The user's next requested deliverable is
a generic one-disk initial-fragment converter, with a study of denser
codecs that still decode in real time alongside PDM.
[Method and timing](audiobook-beeper/VOICE_TIMING.md),
[report](audiobook-beeper/experiments/ima-direct-locked/report.json).

## 2026-10-03: precompensate voice timing; reject changing repeat phase

From the weighted direct player's complete 186880-sample source and measured
Fuse timeline, evaluate radius-16 Lanczos reconstruction at actual hold
centers and re-encode IMA with beam 32. Preserve the original PCM as the
quality reference, all 93440 compressed bytes of capacity, terminal state
0/0, and the original hot-row placement. No assembly instructions change:
**423 T/sample, 79056232 T/loop, zero CPU delta**. The frozen-layout build
also reproduces the previous disk byte for byte on its original input.

The host estimate is **19.5984 dB**. Full native and independent cold Fuse
verification passes two loops /5980161 bits /373760 predictors and indices,
native timing/RAM guards, complete paging and loading-message checks.
Actual clock-aware scores are **19.6064 dB on the first loop, 13.8469 dB on
the second**, despite mean speed remaining within 0.043% of 8 kHz. The disk
does not restart at the same ULA phase; the source compensation is therefore
insufficient for continuous clean playback. Extend clock-aware acceptance
to both loops and save integrated-port previews, not a claimed speaker test.

Decision: retain the useful first-loop improvement, reject this candidate
as final and keep root TRDs unchanged. Fix repeat phase next; do not hide
the second-loop regression behind the host estimate. No audible Fuse
capture or physical hardware test was run for this attempt.
[Script](audiobook-beeper/precompensate_voice.py),
[method](audiobook-beeper/VOICE_TIMING.md),
[evidence](audiobook-beeper/experiments/ima-direct-precomp/report.json).

## 2026-10-03: expose voice flutter despite 20.09-dB warped-clock score

Continue from the complete direct-player source and real Fuse timeline.
A bounded 14-case table probe compares native/mean/median/partial/double
weights, beta 0.25..0.75, and four alternate recent-error extents. The
selected table uses eighth-T rounded mean weights, beta 0.5 and recent
representatives +/-0.25. It needs 122/86 code patterns and the same RAM
reserve. Correct the ordinary-sample filter from old slot 15 to direct
slot 14; the selected rounded weights and results are unchanged.

The new opt-in `--measured-model` disk passes two complete native and cold
Fuse loops, **5980161 exact bits /373760 predictors and indices**, all
native timings/RAM guards, paging and loading checks. FFmpeg confirms every
IMA sample and normal-speed capture passes two wraps. The PCM8/IMA bytes
are identical to the prior source. Native cost remains **423 T/sample,
79056232 T/loop (0 delta)**; actual ULA overhead is 7529824 T over two loops.
Mean rate is 8003.3267 samples/s (+0.0416%), with all previously checked
0.1-second/one-second windows within +/-2%. Both loops score at least
**20.08555 dB** under the old warped-reference measurement.

During that sound capture the user reported trembling voice, not merely
a high whistle. [New timing analysis](audiobook-beeper/analyze_voice_jitter.py)
finds -0.2614..+0.2005 ms sample-clock error and a strong 50-Hz component
(0.0910-ms amplitude). Five-millisecond speed ranges are 7657..8385 Hz.
Using a uniform reference at the measured mean rate yields only
**8.4298 dB**, with 8.5984 dB from clock warping alone. Same source, filter,
edges and first-sample phase; no fitted gain/delay or audio alignment.
The earlier warped reference excluded precisely this error.

Decision: **do not mark the goal complete or promote this candidate**.
Retain it as a fully executed modulation experiment, but require clock-aware
quality and suppression of audible flutter for the final voice player.
Physical hardware remains untested. Root TRDs are unchanged by this attempt.
[Method and continuation](audiobook-beeper/VOICE_TIMING.md),
[candidate report](audiobook-beeper/experiments/ima-direct-weighted/report.json),
[diagnostic](audiobook-beeper/experiments/ima-direct-weighted/voice-jitter.json).
Candidate TRD SHA256: `e90f56c1e5cf13f37522e11cf882352b25fadd069733959038fb6f8d12fbb8e7`.

## 2026-10-03: direct packet pointers fix speed and reach 18.85 dB

Keep the exact 186880-sample PCM8 source and 93440-byte IMA stream from the
packet disk. The user requires +/-2% playback speed while the 20-dB goal
remains active. [Direct ASM](audiobook-beeper/direct-player.asm) uses six-byte
table entries and POP HL/IY/DE, with alternate DE as the input cursor.
Exhaustive closure over all PCM bins safely reduces 32 mathematical states
to 18 reachable states, compiling 128/86 first/second code patterns.

Interleave IMA rows in unused packet-page space. Relocate four packet pages
outside TR-DOS workspace and place 25 popular IMA rows (65.175% of operations)
in uncontended bank 2. Keep identical audio capacity and full 128-KiB memory
accounting. Both nibble paths cost **423 T**, down **45 T** from the packet
baseline. Page/bank extras are 14/140 T. Full native loop is **79056232 T**,
down **8410969 T**; Fuse adds **7529822 ULA T** across two loops. Preload uses
425 table/audio sectors; no runtime disk reads. [Complete timing/memory](audiobook-beeper/DIRECT.md).

Full native/cold Fuse checks pass two loops: **5980161 bits /373760 exact
predictors and indices**, every native interval and protected RAM, paging,
loading UI and all actual output timestamps. All 2048 mathematical table
entries match exact rational arithmetic. FFmpeg independently confirms all
186880 IMA samples. Normal-speed sound capture covers two wraps with correct
paging and no silent half-second window. Its legacy literal date is corrected
to the observed 2026-10-03 capture date; future recorder runs use local date.

Measured rate is **8003.3268 samples/s (+0.0416%)**, with **128053.23 outputs/s**.
First-loop duration is 23.35034 s for 23.36 s of unchanged source. Every
sliding 0.1-second and one-second window (100-sample hop, two full loops)
passes +/-2%: worst errors **0.1112% /0.0501%**. No resampling/pitch correction
was used. Total SNR rises **17.2551 ->18.8455 dB**, while the CPU-only model
is 21.1982 dB under the same listening filter and edge exclusion. Thus the
speed gate passes but 20 dB remains unachieved; no physical hardware claim.

The first assembler attempt failed on macro labels without explicit ASSERT.
The first native timing assertion revealed a missing 10-T JP in the bank
estimate; correcting metadata (not instructions) produced exact counts.
Decision: retain this fully verified separate listening disk and continue
the quality work from its real ULA timing. [Report](audiobook-beeper/experiments/ima-direct/report.json),
[TRD](ZX-audiobook-IMA-ADPCM-direct-test.trd),
[actual WAV](audiobook-beeper/experiments/ima-direct/result-preview.wav).
TRD SHA256: `9ce319e8b9352a96ed965d87ff3d1d8698df7d788221563758d306d23c053013`.

## 2026-10-03: diagnose packet timing noise; require playback speed within 2%

Resume the 20-dB goal from the verified packet disk. The user rejects its
9.18% slow playback and permits at most **+/-2%** speed/pitch deviation.
The existing disk remains an experiment failing that new acceptance gate.

Reuse all 186880 source samples and the saved first-loop Fuse timestamps.
[Host diagnosis](audiobook-beeper/probe_packet_contention.py) compares five
duration weight choices without rebuilding a disk. Native/median weights
reproduce 17.2551 dB. Mean measured ordinary holds yield **17.8286 dB**;
half/double corrections yield 17.7080/17.6347 dB. Mean weights require
154/80 code patterns and an estimated 14080-byte resident reserve. These
are host models on the old trace, not native or Fuse proofs of a new table.
[Complete measurements](audiobook-beeper/experiments/ima-packet-contention/report.json).

Decision: do not deliver a mean-weight rebuild; the gain is insufficient
and does not address speed. Reduce the cycle itself and its exposure to
contended memory before another full bootable candidate. This probe changes
no player instruction or T-state count. The previous goal turn made concrete
progress by delivering and verifying the packet disk; 20 dB remains open.

## 2026-10-02: deliver the bootable compact packet-PDM disk

The user requested a disk with the new output method. Deliver the compact
version of the already executed packet kernel, retaining live IMA decoding,
stock Spectrum128/Beta Disk, preload status and continuous looping. The
unimplemented direct-pointer 434-T proposal is outside this delivery.

[ASM](audiobook-beeper/packet-player.asm) compiles 156/82 used eight-output
sequences, with a duration-aware 32-state integral-feedback table. Balance
both nibble paths to **468 T/sample**: +18/+8 T versus the probe's 450/460-T
paths, mean +13 T; +34.75 T versus the old 433.25-T eight-output player.
There are 16 outputs per sample. Non-bank page/bank extras are 18/131 T.
Full native loop is **87467201 T**; two Fuse loops add **7532826 ULA T**.
Preload ROM/disk execution is separate, with 420 sectors and no runtime I/O.

Use shadow screen bank 7 and all 128 KiB: 93440 bytes of IMA, 6912 screen,
16384 bank-5 tables/workspace, 14336 bank-2 resident code/tables. Source is
the same prepared prefix shortened to **186880 samples /23.36 seconds**,
with a 20-ms final fade and 128 silent samples. Beam32 encoding ends exactly
at predictor/index 0/0 for seamless decoder looping. Modulator state carries
across loops. This shorter scope is not an identical-source comparison to
the earlier 26.624-second probe.

[Native and cold Fuse verification](audiobook-beeper/experiments/ima-packet/report.json)
checks two complete loops, **5980161 bits /373760 predictors and indices**,
every native interval, protected native RAM, paging, loading message and
shadow screen selection. All 2048 table entries match an independent exact
rational recurrence. FFmpeg independently confirms all 186880 IMA samples.
Normal-speed Fuse recording covers two wraps, with correct paging and signal
in every complete half-second window. Actual mean output is **116245.69 Hz**,
PCM rate 7265.36 Hz, loop 25.72223 seconds; pitch/speed is about 9.18% lower
than the 8000-Hz input. Maximum hold is 192 T at a bank transition.

Measured total SNR is **17.2551 dB**, modulation 18.0449 dB, codec 25.1981 dB
under the established 70-Hz HP/two 4.5-kHz LP filters, excluding 0.1-second
edges and following actual sample timing. CPU-only model gives 20.4512 dB;
ULA contention prevents reproducing that score in Fuse. Do not claim a
20-dB stock-machine result or physical-hardware testing. Keep the new disk
as a separate listening experiment; existing root images are unchanged.

The first full debugger launch hit Windows error 206 (command line length),
before Fuse ran. Replacing per-codebook stop breakpoints with one port stop
fixed the harness without changing the player. The full corrected run passes.
[Disk](ZX-audiobook-IMA-ADPCM-packet-test.trd),
[actual WAV](audiobook-beeper/experiments/ima-packet/result-preview.wav),
[reproduction, memory and instruction counts](audiobook-beeper/PACKET.md).
TRD SHA256: `53b0b19a0fb7bb8b77ef48c990827b7dbc65a2bf0be14fd787a681b970d3ad87`.

## 2026-10-02: probe integral-feedback PDM packets toward 20 dB

The user made 20-dB SNR the active goal. Preserve the complete current
26.624-second source, live IMA decoding, and the established listening
filter. Do not substitute a host model for a verified player. The separate
loading-message request was completed without replacing this goal.

The [bounded model probe](audiobook-beeper/probe_feedback_packets.py) compares
four rectangular-state tables at 128 kHz: total SNR 20.2173 /18.9547 /20.0592
/15.1348 dB for 64/32/128-state damped and 64-state half-gain second-order
variants. Transform the state to accumulated error q plus recent error;
16 q states and two recent bins give **20.6333 dB** at ideal 128 kHz in 8 KiB.
Four recent bins give only 20.5197 dB; retain the smaller model.

Duration-aware generation on an estimated balanced 460-T schedule gives
19.8787 dB with old IMA, or **20.5970 dB** with the separately verified beam
encoding. The first weighted measurement wrongly applied the old three-slot
pipeline delay across unequal holds and reported about 11.4 dB. Correct it
to the packet design's zero latency; preserve the invalid report. These are
host models, not live-player improvements.

The [separately assembled packet kernel](audiobook-beeper/ima-packet-probe.asm)
uses constant-output codebooks instead of extracting each PDM bit. The
[native verifier](audiobook-beeper/probe_packet_cpu.py) checks both complete
IMA streams in 208 independent blocks each: 212992 PCM samples, 3408080
outputs, exact predictor/index/bit/timing, unchanged RAM, and 2048 table
entries against an independent integer recurrence. CPU cost is 450/460 T,
mean **455 T/sample**, +21.75 vs the live feedback baseline; 16 instead of
eight outputs gives **124726.15 Hz** before ULA/paging. Code occupies 26621
bytes (reserve 26624), plus an 8192-byte producer table and other tables.
Initial assembly attempts failed on COMET bitwise syntax; explicit macros,
spaced `& 1`, and the assembler's omitted trailing DS bytes are now handled.

On the verified alternating native schedule, the duration-aware host table
with beam IMA gives **19.9686 dB**, not 20 dB; the larger recent-error table
gives 19.8284 dB. No cold Fuse, runtime refill, paging, memory-allocation or
loop proof exists for the new kernel. Current release images are unchanged
by this experiment. [Saved reports and binary](audiobook-beeper/experiments/ima-packet-probe/native-beam32.json),
[exact-schedule model](audiobook-beeper/experiments/ima-packet-probe/beam32-native-schedule.json),
[continuation checkpoint](audiobook-beeper/FEEDBACK.md#active-20-db-work-packet-codebooks-and-better-ima-encoding).
Decision: keep the goal active; next remove the intermediate second-pattern
lookup using direct code pointers, compact unused templates, and prove the
complete memory/timing design before a new TRD. The 434-T estimate in the
checkpoint is an unimplemented design, not a native result.
After this report, the user accepted approximately 20 dB if achieved on a
real computer. Preserve stock-hardware feasibility and full-playback checks;
no physical-machine test has been performed.

## 2026-10-02: improve offline IMA encoding for the active 20-dB goal

Keep the complete current 212992-sample /26.624-second PCM8 source and the
unchanged four-bit IMA format. The new opt-in [beam encoder](audiobook-beeper/ima_beam.py)
retains 32 distinct predictor/index states over 64-sample blocks, minimizes
PCM16 squared error, and carries the selected state between blocks. Forbid
saturating transitions so the guarded Z80 decoder remains valid. This changes
only offline encoding; no playback instruction or decoder T-state changes.

On the identical source, raw codec SNR improves **22.322176 ->24.156331 dB**
(+1.834155 dB), with the same **106496 bytes**. Predictor range is -29027..29889,
with zero saturation. The [independent verifier](audiobook-beeper/verify_ima_beam.py)
compares every PCM16 sample against FFmpeg IMA WAV decoding, using four
correctly seeded WAV blocks: all 212992 samples are exact. This is codec
quality, not the whole playback SNR and not a new TRD release.

[Encoding report and source identity](audiobook-beeper/experiments/ima-beam32/report.json),
[FFmpeg proof](audiobook-beeper/experiments/ima-beam32/verification.json), and
[encoded stream](audiobook-beeper/experiments/ima-beam32/soundtrack.ima.gz).
Reproduce with `ima_beam.py experiments/ima-feedback64/source-preview.wav
--output <new-directory>` and `verify_ima_beam.py <new-directory> --ffmpeg <ffmpeg>`
from `audiobook-beeper`. Decision: retain this encoding improvement as an input
for the next PDM player; the 20-dB whole-chain goal remains active.

## 2026-10-02: show audio-loading status before feedback playback

The user requested an English message while audio data loads, disappearing
when loading finishes. Add **Loading audio data** in the unused top 24 pixel
rows of the feedback player's screen. The ready image contains hidden black
attributes; two startup loops reveal/hide 96 attributes around the existing
audio reads. The two loops add 20 code bytes (1740 ->1760), remaining within
the 1792-byte reserve. No playback hot-path instruction or native cycle count
changes: 92289184 T/loop, **0 T delta**.

Full native and cold Fuse128 verification covers two cycles, 3407985 output
bits and 425984 predictors/indices, memory guards, paging and no runtime disk
reads. Fuse checks the message before loading, throughout all 416 audio
reads, and verifies all 96 attributes hidden before playback. Visually inspect
the [before/after screen](audiobook-beeper/experiments/ima-feedback-loading/status-preview.png).
Actual output is 63919.4670 Hz; total SNR is 14.029210 dB under the same filter.
Measured ULA overhead differs by one T across two loops; native timing and
the encoded audio are unchanged. No physical hardware test or new sound
algorithm is claimed.

Update the root feedback TRD, SHA256
`38823c7b5a75877863649d848658452ef1586ae5014a71153d7379f3e91b5d72`.
Preserve the original feedback experiment and WAV. The
[new report](audiobook-beeper/experiments/ima-feedback-loading/report.json)
archives metadata, compiled binary, source snapshots and full output times;
the complete raw debugger trace remains in `.tmp/feedback-loading`.
Reproduce with `build_feedback.py --output <empty-directory> --fuse <fuse>
--ffmpeg <ffmpeg>`. Decision: deliver the requested startup UI change;
the separate active 20-dB goal remains unfinished.

## 2026-10-02: record 20-dB target and PDM buffer feasibility

The user asked whether 20-dB total SNR is possible and whether a small
predecoded PDM buffer could improve speed/quality, then requested saving
and pushing the current progress. Reuse the completed feedback player's
14.0291-dB result and the original full-excerpt host models; this follow-up
is analysis only, with no new player, TRD, WAV or runtime measurements.

Record the **3.95x error-power reduction** needed for 20 dB and the
approximately **22.49-dB modulation budget** assuming uncorrelated errors
and the fixed codec's 23.6-dB reference. The saved 128-kHz second-order
host model reaches 21.5165 dB, but no live implementation proves that rate
or quality. Full-precision damped feedback at 64 kHz reaches only 16.5686 dB.

Compare a proposed 1-KiB buffer split into two halves: packed bits hold
32 ms per half at 128 kHz; ready port bytes hold 4 ms. Reclaiming 1 KiB
from IMA would cost 0.256 s before layout/code changes. A ready-byte OUTI
costs 16 T versus the existing 30-T output core (-14 T), excluding producer,
control and ULA costs. At 128 kHz only 27.7102 T is available per pulse.
The Z80 must interleave production/output; buffering does not supply a
second processor or eliminate sustained refill costs. Memory placement
and total timing remain unresolved. See the
[saved calculations and limitations](audiobook-beeper/FEEDBACK.md#follow-up-20-db-target-and-a-small-output-buffer).

Decision: preserve the verified feedback preview and the theoretical
buffer proposal as a continuation checkpoint. Do not claim an SNR gain,
a buffered player or a new release. Verification reuses existing reports
and checks documentation/diff only; no unchanged playback tests rerun.

## 2026-10-02: implement live IMA feedback PDM near 64 kHz

The user requested a playable version of the 64-kHz damped-feedback model
from the SNR assessment. Baseline is the unchanged uniform PDM disk and
prepared 8-kHz PCM audiobook excerpt starting at 60 seconds. A direct
arithmetic feedback term does not fit the live decoding budget. Implement
an **8192-byte table** which produces eight PDM bits and the next feedback
state for each decoded IMA sample. Authoritative instructions remain in
[separately assembled, commented ASM](audiobook-beeper/ima-feedback-player.asm);
Python only prepares data and packages the assembled binary.

The beta=0.5 recurrence is approximated with 64 PCM bins and 64 history
states. Recent/older errors are quantized at block boundaries into 16/4
midpoint bins over [-0.5,0.5]. It contains no RC model. An earlier 8/8-bin
allocation gave 16.1552 dB modulation SNR at ideal 64 kHz on the full
28.864-second source, versus 16.3805 dB for 16/4; choose the latter. Both
are below the original full-precision model. Native code retains exact
PCM16 IMA prediction and generates PDM live without PCM/PDM buffers.

Use all 128 KiB: 106496 bytes IMA, 16384 resident code/tables, 6912 screen,
1280 startup workspace/stack. The new source holds 212992 samples /26.624 s,
with a new final 20-ms fade; verify that preceding IMA bytes match the old
prefix. The table takes the former bank-2 sound capacity. Every disk is
independently bootable; all 416 audio sectors load before playback.

The first integrated kernel passed two full native/Fuse cycles at
**63306.105 Hz**, total SNR **13.6214 dB** versus the matched old prefix's
11.5532 dB. Its low/high paths were 428/446 T, mean 437, full loop
93087904 T. A table using average slot-area weights gave 14.1048 versus
14.1061 dB modulation SNR on that measured schedule; retain unweighted
feedback because this did not improve quality. Preserve the first kernel's
[verification](audiobook-beeper/experiments/ima-feedback-initial/verification.json),
source/binary snapshots and evidence index; full traces remain in
`.tmp/feedback-live`.

Unroll four input bytes to remove three ordinary high-path branches.
Unit execution rejected an early 6-T estimate for INC IY (actual 10 T);
use 8-T INC IYL where group alignment proves that no carry is possible.
Final low paths take 428 T, high paths 436/436/436/446 T, mean
**433.25 T**, -3.75 vs first feedback and -4.75 vs standard six-slot PDM.
The pulse kernel is 30 T (8+4+7+11), versus the previous isolated PDM's
40 T. A page adds 18 T, a bank 434 T including one duplicate eight-bit
block. Exact loop `433.25*212992+18*(416-7)+434*7` =**92289184 T**, saving
**798720 T** against the first feedback attempt. Counts exclude ULA,
TR-DOS and disk latency. Code is 1740 bytes in a 1792-byte reserve.

Final full cold Fuse128 verification measures **63919.467 Hz average**,
80.533 Hz below a strict 64-kHz target. PCM is **7989.671 samples/s**,
0.1291% slow; no pitch correction. Loop durations 26.658452/26.658388 s,
maximum hold 85 T (minimum instantaneous rate 41728.235 Hz). Measured ULA
adds 4531131 T across both loops. The result is approximately 64 kHz,
not a uniform-clock or every-period 64-kHz guarantee.

The [tests](audiobook-beeper/test_feedback.py) pass all 16384 PCM8/history
combinations against an independent Q16 reference and assembled lookup,
44496 safe IMA transitions across all eight paths, exact cycle counts,
memory guards and rejection of unsafe predictors. The
[full native/Fuse verifier](audiobook-beeper/verify_feedback.py) checks
3407985 bits, 425984 predictors/indices, every paging latch, fixed and
paged RAM guards, startup stack and zero runtime disk reads over two loops.
The first full Fuse instrumentation run timed out because port-FE already
matches both output levels and the added 10FE breakpoint double-counted
ones; a short trace exposed duplicate timestamps. The corrected single
breakpoint completes both cycles. This was an instrumentation failure.

Using the established common 70-Hz HP /two 4.5-kHz LP filter on matched
source prefixes, total reconstruction SNR is **14.0291 vs11.5532 dB**
(+2.4759); modulation-only is **14.5659 vs11.8282 dB**. First-order PDM
modeled on the new exact schedule scores 13.6354 dB modulation SNR, so
feedback itself contributes about 0.93 dB. Quantization and nonuniform
holds keep the final result below the ideal host model's 16.6 dB total.
Metrics include distortion and exclude tempo error against a fixed 8-kHz
clock. Actual normal-speed Fuse audio captures both wraps with signal in
every half-second window; delivered WAV contains 1175638 mono PCM16 frames
at 44100 Hz, peak 6921, no full-scale samples. No physical hardware test.

Decision: deliver the separate looping
[feedback TRD](ZX-audiobook-IMA-ADPCM-feedback-test.trd), SHA256
`606fcd747e53398c73a01347beb10488d2afe86c984a9bc402e855d0d6060cbd`, and
[actual Fuse WAV](audiobook-beeper/experiments/ima-feedback64/result-preview.wav).
Retain original PDM and both PWM disks byte-for-byte unchanged. Independent
binary packaging reproduces the new disk; the packer now applies its
existing saturation guard to this feedback format too.
[Builder](audiobook-beeper/build_feedback.py),
[algorithm/timing notes](audiobook-beeper/FEEDBACK.md),
[complete report](audiobook-beeper/experiments/ima-feedback64/report.json),
[delivery checks](audiobook-beeper/experiments/ima-feedback64/delivery.json).

## 2026-10-02: assess achievable beeper SNR and separate codec error

The user requested an analysis of maximum achievable SNR on the Spectrum.
Baseline: the unchanged uniform-PDM disk, 230912 prepared PCM8 samples at
8 kHz and 115456 IMA bytes, source excerpt 60..88.864 seconds. Authenticate
source PCM, packed IMA and complete saved Fuse output times. This is a host
analysis; no player, disk, hot-path instruction or memory allocation changed.

[Reproducing script](audiobook-beeper/assess_snr.py) evaluates the complete
excerpt with the established 70-Hz HP /two 4.5-kHz LP filter, and separately
with a Welch 70–3800-Hz measurement band. Use exact pulse-area reconstruction,
the same reference delay/schedule and no fitted gain/phase. SNR includes
reconstruction distortion and excludes tempo error against a fixed 8-kHz
clock. Current modulation-only 11.783161 dB is reproduced within 1e-9 dB;
total SNR relative to prepared PCM8 before IMA is **11.5163 dB**. Independent
IMA decode reproduces **22.4117 dB** raw codec SNR; the filtered ideal decoded
waveform gives approximately **23.6 dB** against prepared PCM8.

Eleven bounded comparisons separate timing, frequency, feedback and format.
Uniform reclocking of the same bits adds only **0.055 dB** modulation SNR.
Ideal first-order output at 64/72/96/128 kHz gives total SNR
**14.3178 /15.3583 /17.7634 /19.6798 dB**. Damped beta=0.5 feedback at 64 kHz
gives **16.5686 dB**, but native cost is unresolved. True second-order feedback
at half amplitude gives only **10.5743 dB** at 64 kHz, so it is not an automatic
improvement; at 128 kHz it gives **21.5165 dB**. Removing IMA at that rate gives
**25.8117 dB** with the listening filter, or **29.9542 dB** in the selected
70–3800-Hz band. These rates/algorithms are models, not verified players.

Numerical verification on the first five seconds of the no-IMA 128-kHz
candidate raises integration rate 192 ->768 kHz and changes the score by
**0.0915 dB**. This convergence check is partial; the eleven primary
comparisons cover the full excerpt. No analog noise, speaker or physical
hardware was measured. The first script launch lacked SciPy; replace that
dependency with explicit NumPy Welch calculation before obtaining results.

Decision: complete the analysis and retain the current player. Existing
native probes suggest 64 kHz as the next practical target and 72 kHz as tight,
with **14–16 dB total SNR** a modeled target rather than a release guarantee.
Do not call the ideal 8-bit full-scale-sine figure (~50 dB), fixed-IMA
reference (~23 dB), or a host-only 30-dB band result a hardware maximum.
[Assessment and assumptions](audiobook-beeper/SNR_ASSESSMENT.md),
[full report](audiobook-beeper/experiments/snr-assessment/report.json),
[numerical check](audiobook-beeper/experiments/snr-assessment/numerical-check.json)
and [archived producer](audiobook-beeper/experiments/snr-assessment/assess_snr.py.gz).

## 2026-10-02: optimize error-feedback PWM past 40 kHz average

The user requested at least 40 kHz PWM after the 15.606-kHz experiment.
Retain identical IMA input (115456 bytes /230912 samples, source 60..88.864 s),
full 128 KiB allocation, independent boot and live decoding. The new
[fast assembly](audiobook-beeper/ima-pwm-fast-player.asm) uses two widths
with an 8-bit first-order error accumulator, distributing intermediate
levels between successive PWM periods. It is an additional experiment,
not a replacement of the original non-RC PDM model.

The first fully checked version used 30/42-T pulses and 12-T JR balancing.
Native sample 433 T /loop 100027154 T; cold Fuse measured **39929.767 Hz**,
below target, and 7982.559 PCM samples/s. It was rejected. Preserve its
[verification](audiobook-beeper/experiments/ima-pwm40-jr-attempt/verification.json),
ASM/verifier snapshots and assembled binary; full trace/timestamps remain
in `.tmp/ima-pwm-fast/`, with hashes in the saved evidence index.

Replacing each path's JR with JP cuts the kernel 58 ->56 T (-2), changing
wide pulses 42 ->40 T. Narrow pulses remain 30 T. The first all-JP expansion
exceeded the 1536-byte code reserve by 81 bytes; sharing the last two stages
across seven bank tails fits 1342 bytes, versus the JR build's 1513, without
taking audio RAM. The shared jump adds 3 T per nonfinal bank. Native ordinary
periods are 84/84/84/87/84 T: sample 433 ->423 T. Page extra 84 T, bank extra
511 T (final 508). Exact loop `423*230912+84*443+511*7+508` =97717073 T,
-2310081 versus JR, -6655895 versus the 16-width PWM. Deterministic counts
exclude ULA, TR-DOS and disk latency; measured ULA adds 2839565 T over two loops.

[Full native and cold Fuse128 verification](audiobook-beeper/experiments/ima-pwm40/verification.json)
passes two cycles, 4620205 edges, every PCM8 value and PWM width choice,
461824 exact predictors/indices, paging latches, startup stack and native
memory guards. All native pulse widths and periods match the independent
reference. Tests cover 11124 safe transitions across both nibbles, all 256
PCM8 levels and accumulator phases, 28055 narrow /27565 wide pulses.
The separate binary packer reproduces the disk; previous general/uniform
PDM and 16-width PWM disks still rebuild byte-for-byte unchanged.

Actual average carrier is **41325.200 Hz**; all 111 complete half-second
windows measure 41320..41330 Hz. This satisfies the average-frequency target,
not an every-period floor: 343781 /2310102 periods (14.882%) exceed 25 us;
maximum 98 T /27.642 us, equivalent to 36192.857 Hz. Period counts are not
confused with the twice-as-large FE write rate. Actual PCM is 8261.527 Hz,
3.27% above the unchanged 8-kHz source; first loop 27.950218 s. No pitch
correction, resampling or physical hardware measurement was performed.

Normal-speed Fuse audio capture lasts 55.907392 s with two wraps, correct
latches and signal in every half-second window. Delivered WAV is the first
loop-length prefix aligned to ready, without added gain/filter. The fixed
nominal PWM AC range is 18.5474 dB quieter than full-scale PDM. Under the
same 70-Hz HP /two 4.5-kHz LP comparison, fixed PWM compensation 8.46 and
common gain 0.604277, SNR is **6.9781 dB** versus PDM 11.7832 and slower PWM
13.5337. Frequency improved; audio quality did not. Keep this as a test
option and retain uniform PDM as the primary version.

The separate [PWM40 TRD](ZX-audiobook-IMA-ADPCM-PWM40-test.trd), SHA256
`6dd21e62b2965477835b63d69cf36f32e1fb83dc4f1bc7468c0a9e9259bcffd9`, boots
independently and loops, with the same 451 startup sectors and no playback
reads. [Build](audiobook-beeper/build_pwm.py) (`--fast --record`),
[tests](audiobook-beeper/test_ima_pwm_fast.py),
[report](audiobook-beeper/experiments/ima-pwm40/report.json),
[rate windows](audiobook-beeper/experiments/ima-pwm40/rate-windows.json), and
[delivery checks](audiobook-beeper/experiments/ima-pwm40/delivery.json).

## 2026-10-02: add an independently bootable live PWM comparison

Objective: try PWM alongside the original non-RC PDM player. Baseline is the
uniform disk `9c316c9acad7eb44e0fa72a61f628d95d8f079f98c4f4133c6b42b3b80e884d8`,
with identical 115456 IMA bytes /230912 samples, source 60..88.864 s. No source
re-encoding, RAM unpacking or change to existing PDM disks is used.

The externally compiled [PWM source](audiobook-beeper/ima-pwm-player.asm)
interleaves guarded IMA decoding with two 226-T PWM periods per sample.
Complementary 15-NOP ladders produce 16 widths, high 68..128 T in 4-T steps.
Main L retains the width while A is scratch; the second stage's 5-T RET C is
never taken after AND15. The input guard proves no predictor saturation is
needed. Since pyz80 lacks the ED71 mnemonic, that instruction is explicitly
encoded and commented in ASM; it outputs zero on the target NMOS Z80.
Python prepares data and packages the separately assembled binary.

Compared with uniform PDM: ordinary sample 438 ->452 T (+14); non-bank page
extra 74 ->0 T; bank extra 361 ->89 T, final 121 T. Full loop 101175126 ->
104372968 T (+3197842), exactly `452*230912+7*89+121`. Counts exclude ULA,
TR-DOS and physical disk latency. Code 1193 ->1484 bytes still fits the
1536-byte reserve. All 128 KiB allocations and 451 preload sectors are
unchanged, with no playback reads.

[Full native and cold Fuse128 verification](audiobook-beeper/experiments/ima-pwm16/verification.json)
passes two cycles: 1847297 native edge values/widths/periods, 461824 exact
predictors and indices, all Fuse width selectors, paging latches, native
memory guards and startup stack bounds. Component tests cover 11124 safe
low/high transitions and all 16 widths, including initial flags FFh. The
independent packer reproduces the disk; both old general and uniform PDM
disks rebuild byte-for-byte unchanged.

Measured carrier 15606.400 Hz, PCM 7803.200 Hz, first loop 29.591941 s;
ULA adds 1173527 T over two loops. Playback is 2.46% slower than the 8000-Hz
source, without pitch correction. This does not meet the earlier 40-kHz PDM
target. At 40 kHz a 3.5454-MHz Z80 has only about 89 T per PWM period for
width selection, output and decoding; this budget observation is not a
proof that all other PWM implementations are impossible.

[Matched-filter comparison](audiobook-beeper/experiments/ima-pwm16/report.json)
gives 13.5337 dB PWM SNR vs 11.7832 dB PDM (+1.7505 dB), using 70-Hz HP and
two 4.5-kHz LPs with no fitted delay. PWM's narrower AC range is 10.9586 dB
quieter; comparison applies the fixed 226/64 correction and one common
0.793961 gain. Actual Fuse recording has no added filter, gain or pitch
correction: 59.186689 s, two wraps, every half-second window contains signal.
The delivered WAV is a first-loop-length prefix aligned to ready, not
exactly the first OUT. A 15.6-kHz carrier may itself be audible; better
filtered error does not establish better raw sound. Physical hardware and
CMOS-Z80 replacements are untested.

Decision: retain PWM as a separate listening experiment and uniform PDM as
the main option. The [PWM TRD](ZX-audiobook-IMA-ADPCM-PWM-test.trd), SHA256
`1d4845cd98c9b13063f98181ee8fd2de886fed7776a3a8c57f9969b84dc1182f`, independently
boots and loops. [Reproduction](audiobook-beeper/build_pwm.py),
[tests](audiobook-beeper/test_ima_pwm.py), [usage](audiobook-beeper/README.md)
and [delivery checks](audiobook-beeper/experiments/ima-pwm16/delivery.json).

## 2026-10-02: keep ordinary PDM and equalize native output timing

The user chose the original non-RC modulator and requested better command
selection for uniform timing. Baseline: the working general IMA disk at
SHA256 `f349d949e6ca6a2c59605bb2caab17706da81dd05f520a1cd8927cdb3f9b69b5`,
six accumulator-PDM slots per sample, 230912 samples /115456 IMA bytes,
source 60..88.864 s. Keep identical encoded audio, PCM8 values, PDM bit
sequence, slot counts, eight-bank allocation and all 128 KiB RAM use.

[ima-uniform-player.asm](audiobook-beeper/ima-uniform-player.asm) separates
nibble preparation, table addressing and both table POPs into equal slots.
Use documented 5-T untaken `RET C` only after proven carry clears, 6-T
`INC SP` only on a dead table cursor, and 9-T `LD A,R` only into dead scratch
A. The comments identify flags, register lifetimes and every counted path.
Saturation and row-sign tags are omitted only after a host audit proves all
raw sums stay in PCM16 (-29878..30985 for this stream). Builder and separate
binary packer both reject streams needing clipping. The general saturating
player remains available and rebuilds to its exact previous disk bytes.

Native ordinary holds become **[73,73,73,73,73,73] T**, versus low
74/72/74/73/72/74 and high 74/72/74/73/72/72. Low/high sample costs change
439/437 ->438/438 T: unchanged 438-T average. Page overhead 76 ->74 T;
bank overhead 362 ->361 T. Full-loop CPU cost **101176020 ->101175126 T**
(-894 T), maximum native hold 79 ->77 T. Keep the short 67-T paging slot
for ULA I/O headroom. Code size 1322 ->1193 bytes; reservation and payload
remain unchanged for an exact audio comparison. ROM and disk latency are
excluded from these deterministic counts.

[Complete native/cold Fuse128 verification](audiobook-beeper/experiments/ima-uniform73/verification.json)
passes two loops: 2771911 exact PDM bits, 461824 exact PCM16 predictions and
indices, correct paging latches, startup stack bound, 451 startup sectors
and no runtime disk reads. Measured PDM increases **47702.626 ->48287.384 Hz**
(+1.226%); PCM playback 7947.667 ->8045.093 Hz. First loop 29.054047 ->
28.702241 s, retaining every sample. ULA waits over two loops fall
3751657 ->1257540 T. Actual interval standard deviation **2.5544 ->1.1910 T**;
the longest rare hold remains 85 T /minimum 41728.235 writes/s. Native
equality is not a claim of perfectly equal wall-clock intervals on Spectrum.

[Matched timing/noise comparison](audiobook-beeper/experiments/ima-uniform73/timing-comparison.json)
finds 78.75% of first-loop intervals exactly 73 T and a 53.37% drop in their
standard deviation. Synthetic midscale's largest 1..8 kHz idle tone falls
9.656 dB with the same reconstruction filter. Speech reconstruction SNR
changes modestly 11.5066 ->11.7832 dB; no source gain/filter changes or RC
model. These modeled metrics are not listener approval or a physical-speaker
measurement.

[Native tests](audiobook-beeper/test_ima_uniform.py) cover 11124 safe
transitions across both nibble paths, including hostile starting flags,
memory guards, 438-T counts and overflow rejection. The general decoder's
4272 transitions and two random full loops still pass. Separately packaging
the compiled binary reproduces the candidate disk exactly. A normal-speed
Fuse128 recording verifies two wraps, all paging latches and signal in
every half-second window. Save an unchanged PCM first-loop-length prefix as
[listening WAV](audiobook-beeper/experiments/ima-uniform73/result-preview.wav).

Decision: accept the uniform ordinary-PDM variant and deliver it separately
as [ZX-audiobook-IMA-ADPCM-uniform-test.trd](ZX-audiobook-IMA-ADPCM-uniform-test.trd),
SHA256 `9c316c9acad7eb44e0fa72a61f628d95d8f079f98c4f4133c6b42b3b80e884d8`.
The former root disk and RC research remain intact. Reproduce with
[build_uniform_ima.py](audiobook-beeper/build_uniform_ima.py),
[compare_uniform_ima.py](audiobook-beeper/compare_uniform_ima.py) and the
existing recorder/packer. See [build report](audiobook-beeper/experiments/ima-uniform73/report.json)
and [delivery evidence](audiobook-beeper/experiments/ima-uniform73/delivery.json).

## 2026-10-02: RC-aware PDM generation with a capacitor model inside feedback

Objective: implement the user's additional generator experiment. The user
clarified that RC must affect bit selection, not just filter an existing WAV:
model capacitor voltage internally and choose charging/discharging bits.
Reuse the current IMA payload and its fully verified first-loop Fuse128
schedule: 1385955 holds, 29.054047 s, source 60..88.864 s, approximately 47.7 kHz.
No change to the existing live player/TRD or its Z80 timing is claimed.

[Generator](audiobook-beeper/rc_pdm_experiment.py) models the earlier ideal
20 kHz RC (R=1000 ohms, C=7.957747 nF) with exact exponential transitions and
integrates capacitor-voltage error to retain DC tracking. Desired voltage
is the same RC applied to delayed decoded PCM8. Three bounded candidates:

- [Beta0](audiobook-beeper/rc-feedback-preview/report.json): first-order area
  feedback gives speech-band SNR 11.7566 dB versus baseline 11.7634 dB. Reject
  as a quality upgrade; preserve its report, bits, audio and source snapshot.
- [Beta1](audiobook-beeper/rc-feedback-order2-preview/report.json): full
  second-order feedback worsens to 7.9194 dB; peak internal error reaches
  7.418 average slots. Reject this aggressive setting.
- [Beta0.5](audiobook-beeper/rc-pdm-preview/report.json): damped feedback
  reaches 14.1084 dB, **+2.3450 dB**, about 24% lower speech-band error RMS.
  A matched timing/beta control with the internal RC bypassed reaches
  13.5511 dB: the RC model's isolated contribution is **+0.5574 dB**.
  Wideband SNR after RC alone worsens -5.8308 ->-8.8777 dB. Retain as an
  additional experimental generator, not an unconditional quality replacement.

Save equal-gain 44.1 kHz PCM16 comparison WAVs with RC alone and with the
same 70 Hz highpass/two 4.5 kHz two-pole speech filters. Keep the new PDM bits
packed separately. Full source/timing artifacts authenticate against the
existing build report. Checks cover analytic RC charging, five DC levels,
capacitor rail limits, independent integrated-error/state identities, full
loop length, all exports unclipped, and rendering-rate convergence. Doubling
705600 ->1411200 Hz changes the candidate by 0.000302 RMS before gain.

Intermediate verification/export attempts are retained as history: an
initial fixed 0.8 listening gain hit the clipping guard after antialias
resampling; use one common peak-safe gain, not independent normalization.
The first convergence run failed the 5e-4 RMS gate because export bins began
at sample timestamps, giving rate-dependent half-bin shifts. Centre the bins
and pass the unchanged gate. Its incomplete export remains under ignored
`.tmp/rc-pdm-precenter/`; earlier candidate reports/source snapshots predate
the final waveform-export checks. The initial beta0.5 result is preserved in
[its report](audiobook-beeper/rc-feedback-damped-preview/report.json).

The commented, externally assembled [Z80 cost probe](audiobook-beeper/rc-feedback-cost.asm)
measures only one direct 16-bit extrapolation term: **62 T**, versus baseline
0 T for that absent term (**+62 T/pulse**), 2025 signed cases verified by
[runner](audiobook-beeper/probe_rc_cost.py). At 47.7 kHz this alone adds 83.38%
CPU before RC update, quantizer, IMA and register allocation. This is a cost
for one implementation, not a universal lower bound. Save the exact counts
and exclusions in [cost report](audiobook-beeper/rc-pdm-preview/z80-cost.json).
Decision: deliver the host-model listening comparison; a practical live port
requires a separate compact fixed-point/table design and full timing checks.
The user's frequency follow-up is answered by this distinction: the host
comparison fixes PDM timing at the baseline rate, whereas a naive live port
would slow down. No unchanged-rate claim is made for execution on Z80.
The root TRD stays at SHA256
`f349d949e6ca6a2c59605bb2caab17706da81dd05f520a1cd8927cdb3f9b69b5`.

## 2026-10-02: higher IMA/PDM rate, guarded CPU feasibility study

Objective: answer whether the current IMA decoder can increase PDM rate
while retaining approximately 8 kHz speech. Scope is investigation, not a
replacement release. Baseline: `ima-player.asm`, ordinary 439/437 T samples,
six pulses, 40-T saved-A modulator, and the previously verified Fuse128
average 47702.626 PDM writes/s. Reuse its full cold-boot evidence. Input is
the same 115456-byte stream /230912 samples from source 60..88.864 s.

The complete decoded stream has **zero saturations**, raw predictor sums
**-29878..30985**. Investigate a build-guarded fast path with untagged table
rows and no saturation logic; retain the existing general player for now.
The user additionally asked whether the constraint can be enforced while
preparing/filling the stream: yes, by validating every decoded addition and
the initial state; reject/re-encode or use the general decoder on failure.
Input peak limiting alone does not prove that ADPCM predictions cannot clip.

[Standalone probe ASM](audiobook-beeper/ima-rate-probe.asm) gives main A to
PDM except during address formation, using 32 T for most pulses instead of
40, and `LD D,IXH` at 8 T instead of 12 T for the PCM8 update. Exact native
low/high counts: eight unpadded slots **393/407 T** (mean400, **-38** from438);
eight padded slots **437/437 T** (mean437, **-1**); nine **425/439 T**
(mean432, **-6**); ten **457/471 T** (mean464, **+26**). At 3546900 Hz,
8 kHz permits 443.3625 T/sample before allocating ULA and boundary overhead.
The eight-slot padded ordinary hold pattern is 58/60/56/50/55/52/56/50 T;
equal sample lengths do not imply equal PDM hold times or improved sound.

[Runner](audiobook-beeper/probe_ima_rate.py) compiles all variants with
external pyz80, then executes all 230912 samples in 902 independent blocks
per variant. All predictor/index/PCM8 values, PDM bits, memory guards and
instruction-table interval counts pass. Deliberately unsafe positive and
negative predictor examples also trigger the host guard. Block PDM state resets; page/bank
tails, continuous loops, ULA, TR-DOS/cold boot and audible quality are
**excluded**, not passed. Save hashes, counts, baseline Fuse evidence and
coverage in [report](audiobook-beeper/ima-rate-probe.json); reproduce with
`python audiobook-beeper/probe_ima_rate.py`. Temporary listings/binaries
remain in ignored `.tmp/ima-rate-probe/`.

Decision: about 64 kHz with eight slots is the next practical integration
target; about 72 kHz with nine is plausible but has only 11.3625 T/sample
remaining before ULA/boundary costs in this probe. Ten already exceeds the
8 kHz CPU budget and is rejected for this kernel. No full Spectrum timing
or audio improvement is claimed. Keep the working root TRD unchanged at
SHA256 `f349d949e6ca6a2c59605bb2caab17706da81dd05f520a1cd8927cdb3f9b69b5`.

## 2026-10-02: simulate an RC low-pass on the TRD playback WAV

The user requested a filter emulating an RC circuit. Retain the preceding
20000 Hz cutoff and process the unfiltered `result-preview.wav` with an
ideal unloaded series-R/shunt-C model, taking output across C. R=1000 ohms
and C=7.957747 nF give tau=7.957747 microseconds. This is one physical pole,
with a -6.0206 dB/octave asymptote and unity DC gain; it is not a cascade
with the preceding second-order Butterworth export.

[apply_rc_filter.py](audiobook-beeper/apply_rc_filter.py) solves
`tau*dy/dt+y=x` exactly for linearly interpolated input at 705600 Hz (16x),
using a double-precision IIR stage between SOXR up/down sampling. The RC
stage evaluates to -3.033288 dB at 20 kHz versus the analog -3.010300 dB;
this check excludes the resamplers and final PCM16 quantization. Verified
stable pole/unity DC gain, unchanged 44.1 kHz mono PCM16 format and
1281283 frames, and no full-scale output samples. No gain normalization.
Save [RC listening WAV](audiobook-beeper/listen-original-vs-ima/result-rc-20k-preview.wav)
and [parameters, command and hashes](audiobook-beeper/listen-original-vs-ima/result-rc-20k-preview.json).
Player, TRD and prior listening files remain unchanged; this is an offline
RC model, not a complete Spectrum speaker-circuit simulation.

## 2026-10-02: apply a 20 kHz low-pass to the exported TRD playback WAV

At the user's request, process the existing first-loop Fuse128 recording
`listen-original-vs-ima/result-preview.wav` with one forward pass of FFmpeg's
second-order Butterworth low-pass, cutoff 20000 Hz, Q=1/sqrt(2). Save
[result-lowpass-20k-preview.wav](audiobook-beeper/listen-original-vs-ima/result-lowpass-20k-preview.wav)
without extra gain or normalization. Source fingerprint, unchanged 44.1 kHz
mono PCM16 format and 1281283-frame duration are checked; output has no
full-scale samples. Parameters, command and input/output hashes are in
[lowpass-20k.json](audiobook-beeper/listen-original-vs-ima/lowpass-20k.json).
This is offline WAV processing; the tested player and TRD remain unchanged.

## 2026-10-02: export original and actual IMA playback for listening

At the user's request, export two directly playable WAVs of the same excerpt
in [listen-original-vs-ima](audiobook-beeper/listen-original-vs-ima/report.json).
The original is source 60..88.864 s, decoded directly from the authenticated
AAC to 44.1 kHz stereo PCM16, with no gain/filtering or codec preprocessing.
The result is the first approximately 29.054 s loop of the existing Fuse128
capture of TRD `f349d949e6ca6a2c59605bb2caab17706da81dd05f520a1cd8927cdb3f9b69b5`,
44.1 kHz mono PCM16, with no additional processing. The small duration
difference reflects the measured Spectrum playback rate; it is not corrected
by time stretching. Verified the source hash, WAV headers/durations and exact
prefix equality with the Fuse capture. The report retains commands and hashes.
No player or TRD changes; reuse the complete playback evidence below.

## 2026-10-02: IMA ADPCM, standalone commented ASM and quieter live PDM

Objective: implement the user's IMA ADPCM request, compile the commented ASM
separately and package its binary with Python, then address the reported
whistling/noise. Baseline: published PCM8 live player (`4b2f8ea`, 121344 samples,
15.402 s, 441 T/sample, 32-T PDM kernel). Input remains the authenticated
O. Henry recording at source 60 s, prepared as 8000 Hz unsigned PCM8 mono.
The final resident excerpt contains 230912 samples /28.864 source seconds,
stored in 115456 IMA bytes: 2:1 versus PCM8, 4:1 versus decoded PCM16.

Implementation: [ima-player.asm](audiobook-beeper/ima-player.asm) is the
authoritative source, with register contracts, saturation, paging, SP usage
and instruction-cycle comments. External pyz80 1.3.0 compiles it to
`player.bin`; [pack_ima.py](audiobook-beeper/pack_ima.py) independently packages
that existing binary without emitting/patching Z80 instructions. The first
ASM migration matched all 14336 bytes of the Python prototype. Final code
is 1322 bytes, with 5696 bytes of transition tables. Code/table reservation
7424 + ADPCM 115456 + screen 6912 + workspace/stack 1280 = all 131072 bytes.
There are no decoded PCM or PDM buffers. Playback uses SP only for read-only
table POPs, IRQs disabled, canonical 7FFD paging and an endless RAM loop.

Intermediate attempts retained rather than presented as releases:

- The initial integer-product delta rounding failed independent FFmpeg
  comparison at decoded sample 49 (-13 versus -11). Replaced it with exact
  IMA reference shift/add rounding. All 230912 samples now match FFmpeg's
  IMA-WAV decoder. This host-table correction changes no Z80 instruction time.
- [First timing attempt](audiobook-beeper/experiments/ima-first/failure.json):
  native 438/452 T per low/high sample, 48-T isolated PDM, max native hold 81 T.
  Two full Fuse loops had exact content but max actual hold **94 T**, failing
  >=40 kHz. Ordinary read slots mixed contended memory with ULA I/O.
- [Tag clearing moved](audiobook-beeper/experiments/ima-tag-tail/failure.json):
  replace 7-T AND during address formation with 8-T RES in the tail: +1 T/sample,
  input slot 81 ->74 T. Native 439/453 T; one Fuse interval still reached
  **90 T** from combined 7FFD and FE I/O contention. This also fails the gate.
- Loading only the already-zero pointer's high byte changes bank setup
  LD DE,nn 10 T ->LD D,n 7 T (-3 T/bank). The
  [first timing-valid version](audiobook-beeper/experiments/ima-unbalanced/report.json)
  passed every bit through two loops, max87 T, average PDM47069.611/s and
  29.435 s/loop. It was superseded for sound quality, not correctness:
  reconstructed PDM SNR was **-1.075 dB** on this quiet speech excerpt.
  Temporary pyz80 macro/DS/indirection syntax errors emitted no accepted disk.

Final optimization keeps PDM BC/DE in the main register bank, input in HL
and table/delta in alternate HL/BC. Removing EXX from each PDM pulse changes
**48 ->40 T (-8 T/pulse)**. Redistributed lookup/padding gives ordinary holds
**72..74 T instead of 56..81 T**, low/high **439/437 T**, mean **438 T**:
-8 T/sample versus the first timing-valid IMA, -3 T versus PCM8. One extra
pulse covers each non-bank 256-byte crossing (+76 T); five extra pulses
cover a bank crossing (+362 T). Full native loop cost is
`438*230912 +76*(451-8) +362*8` = **101176020 T**, down from 102995498
(-1819478 T). Native bank holds are 67..79 T. Exact paths are reproduced by
[verify_ima.py](audiobook-beeper/verify_ima.py); costs follow the
[Zilog instruction table](https://www.zilog.com/docs/z80/um0080.pdf).

Quality: use 4x pre-encoding gain with a 0.85 lookahead peak limiter, 5 ms
attack,100 ms release, delay compensated. RMS rises .05370 ->.19679;
this deliberately changes loudness dynamics. ADPCM SNR against that PCM8
is **22.412 dB**. On complete measured Fuse schedules, with identical 70 Hz
HP/two 4.5 kHz LP reconstruction, PDM SNR rises **-1.075 ->11.507 dB**.
The matched-input ASM-only improvement is **1.394 dB**; most of the combined
12.581 dB comes from level conditioning. The largest modeled idle tone in
1..8 kHz falls **10.716 dB**. These are reconstruction metrics, not a claim
of noise-free playback or physical-speaker measurements. The
[comparison script](audiobook-beeper/compare_ima_noise.py) and
[saved comparison](audiobook-beeper/ima-preview/noise-comparison.json) include
before/after WAVs with matched speech loudness and common attenuation.

Final verification: 4272 native predictor/index/nibble cases and two complete
seeded nonrepeating loops; then two complete real-speech native/cold-Fuse128
loops. All **2771911 bits**, **461824 PCM16 predictors/step indices**, every
PCM8 value, all eight banks/repeat transitions and the startup stack guard
pass. Fuse measures **29.054047/29.054074 s**, **7947.667 samples/s**,
**47702.626 PDM writes/s average**, **41728.235/s minimum**, max **85 T**.
There are 451 preload sector reads and zero runtime reads. CPU counts above
exclude the measured 3751657 ULA T-states across two cycles and approximately
26 s of ROM/disk startup. Actual Fuse audio is also captured at normal speed.
See [complete evidence](audiobook-beeper/ima-preview/verification.json).

Decision: deliver [ZX-audiobook-IMA-ADPCM-test.trd](ZX-audiobook-IMA-ADPCM-test.trd),
a separately bootable, looping 640 KiB TRD occupying 508 sectors. Keep all
earlier root PCM/PDM disks unchanged. This is a roughly 29-second resident
preview, not a full-book or two-minute streaming release. Reproduction,
binary/listing links and listening instructions are in the
[subproject README](audiobook-beeper/README.md).

## 2026-10-02: measure whether LPC synthesis can share the beeper PDM loop

Objective: answer the user's request to optimize the existing LPC decoder
for simultaneous LPC synthesis and live PDM. Baseline is `4b2f8ea`, 8 kHz
source PCM and a 32-T first-order PDM kernel, with the previous >=40 kHz
output requirement. Read the user's external `C:/Work/LPC-sound-codec`
without modifying it. Its AVR implementation uses ten 16-bit Q11 feedback
products and a hardware PWM timer; the accepted host LPC2 reference also
has a twenty-product formant postfilter. Hardware PWM does not represent
the software beeper workload on the Spectrum. LSF conversion can move to
preparation, but feedback synthesis is still required for every sample.

At 3546900 T/s, 8 kHz allows **443.3625 T/sample**. Five 32-T PDM kernels
consume 160 T, leaving at most 283.3625 T before any other work. The isolated
register layout in this probe adds EXX/EX AF/EX AF/EXX, 16 T per pulse:
**48 T instead of 32 T**. Five such pulses leave 203.3625 T. This is a
measured implementation choice, not a universal minimum for all layouts.

Built and executed native Z80 lookup/accumulate kernels at orders 4, 6 and
10, both with and without interleaved PDM. The deliberately favorable
16-bit-product kernel uses **49 T/tap, 490 T/order-10 sample**, assuming
ready tables and only 8-bit history. This alone exceeds the 8 kHz budget;
the real AVR decoder's 16-bit history is not implemented by this shortcut.
The first 8-bit-product/accumulator trial cost **31 T/tap, 310 T/sample**.
Fusing LD A,(HL)/ADD A,E/LD E,A into ADD A,(HL) reduces it to **23 T/tap,
230 T/sample: -8 T/tap, -80 T/order-10 sample**. Even 230+5*48=470 T exceeds
443.3625, with excitation, history update and frame work still excluded.

To check output gaps rather than average CPU demand alone, split work at
instruction boundaries into <=32-T chunks between 48-T isolated PDM slots.
The final order-10 byte kernel spans **614 T** with eight pulse intervals,
an optimistic 5776.710 samples/s ceiling. Its 16-bit-product counterpart
spans **1450 T**, ceiling 2446.138 samples/s. Native output intervals stay
at most 80 T (44336.25 outputs/s minimum at the 128 clock). These are native
CPU measurements, **not Fuse/ULA timing, a complete LPC decoder, audio
quality evidence or a playable release**. The short final chunk and initial
PDM pulse are accounted separately in the saved measured totals.

Verification: **420 deterministic arithmetic/register/PDM/timing cases per
version, 840 total**, including zero, signed extremes and seeded random data.
The old 31-T trial remains in [initial evidence](audiobook-beeper/lpc-budget/report.json)
with its exact producer; the optimized version is in
[final evidence](audiobook-beeper/lpc-budget-fast/report.json).
Reproduce with `python audiobook-beeper/probe_lpc_budget.py --output build/lpc-budget`.
The [probe](audiobook-beeper/probe_lpc_budget.py) records source fingerprints,
timing assumptions, opcode dumps and all excluded work. Instruction costs
follow the [Zilog manual](https://www.zilog.com/docs/z80/um0080.pdf).

Decision: the examined kernels do not establish full LPC2 at 8 kHz plus
>=40 kHz PDM on the stock Spectrum. This is not an impossibility proof for
every possible algorithm. A separately re-encoded, reduced-order profile
around 4 kHz is a reasonable next bounded quality/timing experiment; no
sample-rate or LPC-order change is silently applied to the current disk.
It must solve coefficient-table reuse as well: ten prepared 512-byte tables
per 20 ms frame would require 256000 bytes/s before interpolation, worse
than PCM storage, and generating/replacing them also costs CPU. Byte-table
arithmetic wraps and loses precision; it is not a validated stable LPC
filter or preservation of the accepted voice. A PCM buffer cannot repair a
sustained CPU deficit. Current TRD and player remain unchanged.

## 2026-10-02: fill all eight banks with resident live PCM

Objective: fulfill the user's request to fill all possible memory, retaining
on-the-fly PDM, indefinite repeat and the verified paging correction from
`9f636b2`. Baseline: 82944 stored PCM bytes, six data banks, 3414 code bytes
and a 10.528-second excerpt. The same authenticated audiobook now supplies
[60,75.168) at 8000 Hz /8-bit mono, freshly normalized and edge-faded with the
established filters. There is no added sector-padding silence.

The new shared ordinary loop reduces code to 1396 bytes in a 1536-byte
reservation. Reuse screen staging for PCM after copying the display; move
SP from B800 to 6000. Six full data banks supply 98304 bytes, bank 2 adds
14848 and bank 5 adds 8192: **121344 PCM bytes /118.5 KiB**, +38400 /46.296%.
Exact RAM accounting: PCM 121344 +code 1536 +screen 6912 +workspace/stack
1280 =131072 bytes. Code reservation includes 140 alignment bytes; no whole
sectors remain unassigned. This is full use of the chosen safe layout,
not audio overwriting code or the TR-DOS workspace.

Hot-path comparison: kernel stays 32 T and ordinary four-sample block 1764 T.
Sharing adds JP(IX) 8 T and replaces JR padding 12 T with LD IX,nn 14 T:
**+10 T per bank boundary** versus the paging-corrected baseline. Canonical
paging remains 27 T (itself +1 versus the original alias). New cycle formula
`441*N +2*(N/256) +23*B` gives **53513836 deterministic T per loop**. Actual
Spectrum 128 PDM averages **78783.119 Hz**, minimum **60116.949 Hz**; actual
PCM is 7878.312 Hz, -1.5211% versus source. Loops take 15.402261 and
15.402308 seconds, both wrap holds 49 T. ULA adds 2233052 T across two
loops; 474 disk sectors are acquired before playback, none during it.

Verification: twelve native beeper tests pass, including bank-specific
patterns in all eight banks, fixed-bank aliases and capacity bounds. Cold
Fuse Spectrum 128 verifies **2426881 exact outputs**, every PCM input and
PDM bit, two complete loops plus the next bit, all paging latches and the
5F00 stack-boundary guard. Separate normal-speed, sound-enabled recordings
on explicit 128 and automatic startup observe both loop wraps, correct
7FFD, unchanged 1FFD and signal in every full half-second audio window.
Startup lasts 26.254 /23.590 seconds respectively in those two recordings;
ROM/disk time is separate from the playback CPU counts. No physical hardware
test is claimed. Reconstruction SNR 9.9713 dB /correlation 0.953164 concerns
the new longer input; it is not a same-passage quality improvement claim.

Decision: publish the independently bootable root
[live test TRD](ZX-audiobook-PDM-live-test.trd), SHA-256
`fd234adcb7fc84989616638135d3d58c66994b0c76e980d01a9125a7a49fd79e`.
Retain the isolated short paging fix and all older experiments. See
[memory map, cycle counts and reproduction](audiobook-beeper/FULL_MEMORY.md),
[build](audiobook-beeper/pcm-live-full/report.json),
[full verification](audiobook-beeper/pcm-live-full/verification.json),
[128 sound capture](audiobook-beeper/pcm-live-full/sound-128/report.json),
[automatic sound capture](audiobook-beeper/pcm-live-full/sound-auto/report.json)
and [delivery evidence index](audiobook-beeper/pcm-live-full/delivery.json).

## 2026-10-02: fix live-PCM silence after the first bank

Objective: diagnose the user's early silence in Fuse (reported model 128)
without changing the 82944-byte PCM excerpt. Explicit 128/Beta sound playback
passed, but automatic disk startup reproduced silence after the first bank.
The debugger proved that the 10FD..17FD aliases changed 1FFD while 7FFD stayed
at 10h. Automatic model identity is not inferred from its A timing code.

Use BC'=7FFD and EXX/LD E,n/OUT(C),E/EXX: 27 T versus 26 T, +1 T per
bank, +6 T per excerpt. Kernel 32 T and ordinary block 1764 T stay unchanged.
Native and cold Spectrum 128 checks cover 1658881 exact outputs, two loops,
PCM order, accumulator, code/stack, all paging latches and 324 startup reads,
zero runtime reads. Actual PDM is 78783.428 Hz average /51404.348 Hz minimum;
first loop 10.528161 seconds. Eleven beeper tests passed, including rejection
of legacy aliases by the stricter port model. The separate normal-speed,
sound-enabled automatic run now has signal throughout both loops, correct
7FFD and unchanged 1FFD. No physical hardware test is claimed.

Decision: replace the root live disk with the corrected image and preserve
the original sources and diagnostic evidence. See [details and reproduction](audiobook-beeper/PAGING_FIX.md),
[build](audiobook-beeper/pcm-live-fixed/report.json),
[full verification](audiobook-beeper/pcm-live-fixed/verification.json) and
[sound capture](audiobook-beeper/paging-fix-evidence/fixed-short-auto/report.json).
The user's subsequent full-memory request is a separate capacity change.

## 2026-10-02: consolidate the complete audiobook chat work log

The user requested preservation of everything done in this chat. This entry
records the conversation's decisions, chronological milestones and current
handoff state; the detailed experiment entries below retain the parameters,
instruction counts, measurements, verification coverage and rejected attempts.
This is a documentation checkpoint at implementation commit `453b93e`, not
a new audio experiment. Dates below come from existing entries and Git history.

### Source, original objective and user feedback

- The supplied source is O. Henry's 1977 recording of the two short stories
  "Dorogo kak pamyat" and "Oborotnaya storona", file ID `1bqRZ3gM55s`, under
  `C:/Work/AudioBooksDownloader/Audiobooks`. The
  [source-format record](audiobook-beeper/source-format.json) preserves its
  full original filename/path and SHA-256
  `a34f27c44c0df7f817814df2c43eb3c58d2d415e0892434c99dc23b6b2d2e779`.
  The source is AAC, 44100 Hz, stereo, 667.596916 seconds. AAC does not have
  a fixed original PCM bit depth; FFprobe's `fltp` describes decoder output.
- The initial request was a separate audiobook subproject using the existing
  movie's AY approach. When asked to choose, the user explicitly selected
  compact AY synthesis and then requested at least a two-minute preview.
  That 120-second preview was delivered and rejected as unintelligible.
- The user proposed the existing LPC codec and supplied
  `C:/Work/LPC-sound-codec`. The software-decoded LPC2 comparison was judged
  sufficiently clear; the next request was to preserve more sound detail.
  This acceptance applies to the full software LPC reference, not AY replay.
- The user then specified the real chip constraints: three tone generators,
  one shared noise generator, updates on the 50 Hz interrupt and typical
  Spectrum mixing. The modeled A/B/C outputs were summed equally to mono;
  shared noise is routed through those channels, not a fourth analogue output.
  After requesting and trying the resulting TRD, the user again reported
  that nothing was intelligible and selected beeper PDM at at least 40 kHz.
- Subsequent requests were to increase PDM frequency, identify the source
  sample format, convert the input to 8 kHz /8 bits, save a TRD and repeat
  the demo continuously. Those changes were completed before the AY revisit.
- The later AY revisit was motivated by the recognizable rabbit exclamation
  in the movie. The user's location cue was the first part/first disk,
  approximately after its first third. The bounded [36,52) movie comparison
  is an approximate investigation around that cue, not a user-confirmed
  exact timestamp or an isolated vocal stem. A new pitch-aware AY candidate
  was delivered; no listening acceptance of that candidate was received.
- The latest implementation request returned to the beeper and asked for
  PCM-to-PDM conversion while playing, with minimum Z80 conversion cost.
  The presumed previous expansion into a PDM RAM buffer was corrected:
  the old disks already stored packed PDM and shifted it directly. The new
  format stores raw PCM and moves modulation from the host into the Z80 loop.

### Completed work in chronological order

| Date / commit | Work and measured outcome | Saved evidence / disposition |
|---|---|---|
| 2026-10-01 / `8cb13c1` | Created `audiobook-ay`; reused the movie synthesizer for [0,120). One bootable TRD, 6000 consecutive AY fields, 66000 exact register writes, 302 occupied sectors. | [Initial AY report](audiobook-ay/preview/report.json), [verification](audiobook-ay/preview/verification.json). User rejected intelligibility; preserve the original comparison. |
| 2026-10-01 / `621dadf` | Reused LPC2 Improved from external commit `360af14` through a headless bridge, without editing that repository. Compared original, previous AY, full LPC2 and a formant-to-AY mapping on [60,84). LPC2 uses 4114 bytes; the AY mapping worsened the listed proxies. | [LPC comparison](audiobook-ay/LPC2_COMPARISON.md), [report](audiobook-ay/lpc-probe/report.json). Full software LPC was later accepted as clear; the AY mapping was not selected. |
| 2026-10-01 / `7950579` | Tried 10 ms /exact-repeat LPC: 12601 bytes, improved host reconstruction. After the explicit 50 Hz requirement, selected 20 ms /exact-repeat analysis, 6461 LPC bytes, and a YM2149/Ayumi mono model. Verified 1200 fields /13200 writes; native player remains 974 T/tick. | [100 Hz host experiment](audiobook-ay/lpc-detail/report.json), [50 Hz chip experiment](audiobook-ay/YM2149_PREVIEW.md). The 100 Hz profile was not selected for AY; neither mapping executes a native LPC filter. |
| 2026-10-01 / `2a22f77` | Published the already verified 24-second YM2149 test as a root TRD, with no player/encoding change or redundant emulator run. | [YM2149 test disk](ZX-audiobook-YM2149-test.trd). User rejected speech intelligibility and switched to the beeper. |
| 2026-10-01 / `912c0d8` | Created `audiobook-beeper`; host-generated second-order PDM. Improved the first 64-T player (54.823 kHz average) to 52 T (66.916 kHz), with a verified 11.753-second resident excerpt and 96 KiB packed PDM. | [64-T archive](audiobook-beeper/experiments/pdm64/report.json), [selected 52-T report](audiobook-beeper/preview/report.json), [comparison](audiobook-beeper/comparison.json), [root disk](ZX-audiobook-PDM-test.trd). Minimum actual rates exceed 40 kHz. |
| 2026-10-01 / `7b612af` | Pinned saved debugger scripts to LF so artifact hashes survive Windows Git checkouts. | Archive-integrity correction only; audio, player and timing unchanged. |
| 2026-10-02 / `5c9200a` | Verified the original AAC format, produced exact 8000 Hz /unsigned 8-bit mono PCM, shortened packed-PDM playback to 46 T and added continuous repeat. Average PDM 75.924 kHz; 10.358-second loops, both wrap holds 48 T. | [Single-pass archive](audiobook-beeper/preview-8k8/report.json), [looping report](audiobook-beeper/preview-8k8-loop/report.json), [root disk](ZX-audiobook-PDM-8k8-test.trd). Two full loops plus the next first bit are exact. |
| 2026-10-02 / `55c1a8c` | Inspected the rabbit cue and added a 50 Hz AY candidate retaining F0 and fitting two additional harmonic square waves. On [60,84), spectral cosine rises 0.666873 ->0.926218; full 1200-field replay remains exact at unchanged 974 T/tick. | [Movie comparison](audiobook-ay/pitch-preview/movie-cue/report.json), [AY candidate](audiobook-ay/PITCH_AWARE_PREVIEW.md), [root disk](ZX-audiobook-YM2149-voice-test.trd). Signal proxies improve, but listener acceptance remains open. |
| 2026-10-02 / `453b93e` | Added live PCM8-to-PDM conversion without a PDM buffer/LUT. Four-instruction kernel costs 32 T. Preserved the fast 13-pulse version (104.428 kHz) and selected the steadier 10-pulse version (78.783 kHz) after diagnosing unequal pulse-area error. | [Fast archive](audiobook-beeper/experiments/pcm-live-fast/report.json), [comparison](audiobook-beeper/pcm-comparison.json), [method](audiobook-beeper/PCM_LIVE.md), [selected root disk](ZX-audiobook-PDM-live-test.trd). Both variants have full native/cold-Fuse evidence. |

### Rejected, corrected and interrupted attempts are retained

- The initial AY boundary-test expectation was four T-states low; it was
  corrected to 1007 T without changing player bytes. See the original
  two-minute experiment entry below and its native tests.
- The first LPC-to-AY formant mapping failed the measured comparison and
  was not promoted. The 10 ms LPC refinement remains a host-only experiment
  after the 50 Hz clarification. The full LPC reference and the restricted
  chip rendering must not be substituted for each other in quality claims.
- The 64-T PDM render gate initially rejected a one-T pilot/speech startup
  difference after full playback verification. Rendering resumed with the
  documented three-T startup allowance; the every-interval 40 kHz gate stayed
  unchanged. The selected 52-T candidate and its equal-window comparison
  retain independent complete checks.
- The first repeated-PDM debugger harness stalled before collecting its
  trace. Its [saved script and pilot](audiobook-beeper/experiments/loop-debugger-interrupted/timing-pilot/verification-work/fuse-debugger.txt)
  remain archived. Separate breakpoint conditions fixed the harness, after
  which the complete looping test passed.
- The fast live converter is correct but was not selected as the primary
  listening disk: uneven output holds reduce reconstruction SNR to 6.5376 dB.
  The same bits under an ideal uniform schedule score 12.7522 dB; that is an
  offline diagnostic, not a measured hardware result. The steadier selected
  converter scores 9.8698 dB, with the same exact PCM input bytes and each
  version's own schedule-aligned reference. See the saved comparison above.
- The first steady live-PDM verification logged one extra output because
  Fuse finishes the instruction at an exit breakpoint. The strict count
  gate rejected it. Preserve [that unaccepted run](audiobook-beeper/experiments/pcm-live-stop-extra/interrupted.json);
  moving the stop to a non-I/O instruction fixed the harness, without changing
  the player, and the complete verification was repeated successfully.

### Current state for resuming this chat

The selected live-conversion image is
[ZX-audiobook-PDM-live-test.trd](ZX-audiobook-PDM-live-test.trd), SHA-256
`12163ecf5f206ac60e685cb96269cf7d5d46e458968f86a6517dca6d6cae8793`.
It contains 82944 PCM bytes, including 79 midpoint padding samples, versus
98304 bytes in the previous packed-PDM demo. The TRD has 368 occupied sectors
instead of 428. The player preloads 324 sectors and performs no disk reads
during sound. Both loop transitions retain the accumulator/pipeline, without
an inserted reload or mute. The six data banks, code, stack, screen and
TR-DOS workspace are accounted for in the method document.

Its full cold-Fuse run verifies 1658881 exact outputs over two loops and the
first pulse of the third; ten beeper tests pass. Average PDM is 78783.411 Hz,
minimum instantaneous rate 59115 Hz, with approximately 10.528-second loops.
The stored PCM format is exactly 8000 Hz /8-bit mono, but this fixed software
clock plays it at 7878.341 Hz (-1.5207%, slightly slower/lower-pitched).
The preserved fast disk averages 104428.484 PDM pulses/s and 8032.960 PCM
samples/s (+0.4120%). These are emulator measurements, not nominal CPU-only
estimates. Deterministic T-states and ULA delays remain recorded separately.

Boot the live test in original Spectrum 128/+2 with Beta Disk/TR-DOS, drive A,
using `RUN "boot"` if required; reset stops the loop. Its paging alias does
not support +2A/+3. PDM runs with interrupts disabled, superseding the earlier
AY-only 50 Hz output constraint for this separate beeper path. The newest
[listening preview](audiobook-beeper/pcm-live-preview/beeper-preview.wav)
integrates measured port holds through the documented filter; it is not a
recording of a physical speaker. Earlier TRDs/WAVs remain available above.

The full audiobook has not been converted, and a two-minute beeper stream
has not been built; the completed two-minute preview belongs to the original
AY experiment. There is no native Z80 LPC decoder, runtime disk-streaming
PDM solution or physical-hardware verification in this chat. The newer
pitch-aware AY and live PDM versions have not received listener acceptance.
Metrics cannot establish intelligibility, and SNRs from different reference
signals/filters are not interchangeable. No claim is made that the small
first-order live modulator preserves all quality of the previous offline
second-order encoder. Movie release files and the external LPC repository
remain unchanged. This log request does not authorize or start another
codec experiment; resume from the saved evidence after further user direction.

## 2026-10-02: convert resident PCM8 to beeper PDM directly on the Z80

- User scope: return to one-bit sound, remove the proposed expanded PDM RAM
  stage and minimize live conversion CPU cost. Baseline `55c1a8c`; reuse the
  exact 82865-byte 8000 Hz /8-bit mono passage from the looping 8k8 test,
  beginning at source second 60. Clarification: the older player already
  loaded packed PDM and shifted it directly; it had no decompressed buffer.
  The new player stores raw PCM and performs modulation during playback.
- Implement a branchless first-order integrator in A and a three-slot output
  pipeline in E. `ADD A,D` 4 + `RR E` 8 + `RES 3,E` 8 + `OUT(C),E` 12 gives
  **32 T/pulse**, versus the previous precomputed kernel's 30 T (**+2 T**).
  No amplitude LUT or PDM RAM buffer. Unroll four samples and distribute
  paging/pointer work across output slots. Use original 128/+2 paging aliases
  10FD..17FD, explicitly excluding +2A/+3. [Instruction and RAM contract](audiobook-beeper/PCM_LIVE.md).
- First complete candidate: 13 pulses/sample, four NOPs per four samples,
  **1744 T/4 samples**, 14 extra T/page and 36 extra T/bank. Deterministic
  cycle 36168336 T. Cold Fuse verifies 2156545 exact outputs over two loops
  and the first bit of loop 3, every PCM value, all banks and both wraps.
  Actual PDM **104428.484 Hz**, minimum 56300 Hz; PCM 8032.960 Hz (+0.4120%).
  SNR **6.5376 dB**, correlation 0.904615: unequal holds degrade reconstruction.
  Preserve its disk, WAVs, full trace and compressed exact producers in
  [fast experiment](audiobook-beeper/experiments/pcm-live-fast/report.json).
- One bounded correction follows the measured failure. The same fast bits
  give SNR 12.7522 dB with ideal uniform holds versus 6.7833 with native CPU
  timing and 6.5376 with real Fuse holds. These ideal/native schedules are
  diagnostics, not hardware evidence. Select 10 pulses/sample and mostly
  44-T holds. Kernel stays 32 T, with 12-T register/flag-neutral padding;
  ordinary **1764 T/4 samples =44.1 T/pulse**, versus old 46 T (-1.9 average).
  Page/bank overhead becomes 2/12 T; deterministic loop **36579024 T**.
  [Reproducing comparison](audiobook-beeper/compare_pcm.py) and
  [saved result](audiobook-beeper/pcm-comparison.json).
- The first steady verification attempt was rejected by its strict count
  gate: Fuse completes the instruction at an exit breakpoint, so stopping
  on OUT recorded 1658882 writes instead of 1658881. Preserve the unaccepted
  trace/script/disk and reason in
  [stop experiment](audiobook-beeper/experiments/pcm-live-stop-extra/interrupted.json).
  Move the stop to a non-I/O instruction and rerun the full test. No player
  byte changed for this harness fix; no partial run is accepted.
- Final verification: ten beeper tests pass, including all 256 PCM values,
  all six full banks, a partial final bank, exact native timing, accumulator,
  stack/code guards and the preserved fast trim mode. Full cold Fuse checks
  **1658881 exact outputs**, two loops and first pulse of loop 3, all input
  bytes and bank switches. **324 startup reads /zero runtime reads**; no
  reload, mute or accumulator reset at either wrap. Actual average PDM
  **78783.411 Hz**, minimum 59115 Hz, maximum 84450 Hz; holds 42..60 T, both wrap
  holds 49 T. Durations 10.5281629/10.5280465 s. Actual PCM 7878.341 Hz is
  **-1.5207%** versus the 8 kHz source; report the slight speed/pitch change.
  ULA adds 1526221 T over two loops, kept separate from deterministic CPU
  counts and startup ROM/disk. [Full report](audiobook-beeper/pcm-live-preview/report.json)
  and [verification](audiobook-beeper/pcm-live-preview/verification.json).
- On the same PCM bytes, schedule-aligned conversion SNR improves
  **6.5376 ->9.8698 dB**, correlation **0.904615 ->0.952116**. The clock and
  oversampling ratio differ; these proxies are not listener acceptance.
  First-order live conversion lacks the prior host encoder's second-order
  area feedback, dither and band-limited interpolation. Do not claim that
  moving it to Z80 improves quality over the older precomputed-PDM disk.
- Decision: deliver the steadier looping
  [ZX-audiobook-PDM-live-test.trd](ZX-audiobook-PDM-live-test.trd) in Git LFS,
  keeping the faster archive for comparison. Image 655360 bytes, 368 occupied
  sectors versus 428; raw PCM 82944 bytes (79 midpoint padding samples), down
  15360 bytes /15.625% versus 98304 precomputed PDM bytes. SHA-256
  `12163ecf5f206ac60e685cb96269cf7d5d46e458968f86a6517dca6d6cae8793`.
  Independent boot verified; resident excerpt only, no physical hardware
  recording or full-book/disk-streaming claim. Existing movie/AY/PDM disks
  remain unchanged. [Delivery integrity](audiobook-beeper/delivery-pcm-live.json).

## 2026-10-02: preserve vocal pitch in a new AY50 speech candidate

- User scope: revisit speech on AY/YM2149 after recognizing the rabbit's
  exclamation on movie disk 1, approximately after its first third. Baseline
  `5c9200a`; compare one offline encoder against the rejected 24-second
  YM2149 LPC/formant mapping on the identical audiobook [60,84) passage.
  Keep three tones/shared noise, mono mixing and **50 Hz** register updates.
- Inspect unchanged movie encoder and saved registers. It tracks bass,
  harmony and melody; the previous speech mapper ignores LPC `pitch_hz`
  and places independent tones at formants. Opening source images and disk
  1's 131.2-second duration locate a bounded [36,52) movie comparison around
  the user's approximate cue. Authenticate full source and register hashes,
  render with phase history from time zero, and retain original/AY clips.
  Across 800 states, average active tones 2.1825, 125 noise states, median
  lowest active tone 143.39 Hz. The mixed soundtrack is not an isolated vocal
  stem and these numbers do not identify the vocal generator by themselves.
  [Movie evidence](audiobook-ay/pitch-preview/movie-cue/report.json).
- One candidate: keep tracked F0 on A, fit two additional harmonic tone
  periods and nonnegative powers to the short-time source spectrum, including
  the odd harmonics of actual integer-period squares. Use the YM DAC table,
  32-ms analysis windows and unchanged 20-ms states. Fit shared-noise period
  on unvoiced/transient frames. No envelope, high-rate volume writes, PCM
  playback, fourth channel or native LPC synthesis is added. Of 1200 states,
  894 are voiced, 132 noise and 174 silent.
- Equal-source/equal-renderer result: spectral cosine **0.666873 ->0.926218**,
  chroma **0.846220 ->0.981201**, onset F1 **0.757576 ->0.794118**; loudness
  correlation declines slightly **0.874808 ->0.870788**. Prior values reproduce
  exactly. These signal proxies support a listening candidate, not a claim
  that speech is intelligible. [Report](audiobook-ay/pitch-preview/report.json).
- Verification: ten Python tests and existing YM tone/noise/mixer/DAC tests
  pass. Full independent Z80 and cold Fuse agree on all 1200 ticks /13200
  writes, with no missing/duplicate fields, exact final hold/mute, 52 startup
  sectors and zero runtime reads. The unchanged native hot path remains
  **974 T/tick, delta 0 T**. First OUT phase 150..153 T, intervals70905..70909 T.
  CPU counts exclude IRQ/ULA/ROM/disk; actual playback is measured separately.
  [Verification](audiobook-ay/pitch-preview/verification.json).
- Decision: deliver matched original/previous/new WAVs and
  [ZX-audiobook-YM2149-voice-test.trd](ZX-audiobook-YM2149-voice-test.trd)
  in Git LFS. Independently bootable 655360-byte image, 96 occupied sectors,
  SHA-256 `37e0ae4d8876e5441c0f21cb87f0152bd98b5cc13dfe78e05fba6da1cfdf66a6`.
  Listener acceptance remains open; no physical recording or full-book
  conversion is claimed. Existing movie/AY/PDM releases remain unchanged.
  [Method and reproduction](audiobook-ay/PITCH_AWARE_PREVIEW.md).

## 2026-10-02: faster beeper PDM from 8 kHz /8-bit audio, looping TRD

- Scope: baseline `7b612af`, the verified 52-T resident audiobook test.
  The user asked to raise PDM frequency, identify the source format, convert
  audio to 8 kHz /8 bits, save the current TRD, and repeat it continuously.
  Keep the same source passage beginning at 60 seconds and 96 KiB payload.
  FFprobe confirms AAC, 44100 Hz, stereo, 127999 bit/s; decoder `fltp` does
  not specify an original PCM bit depth. [Source evidence](audiobook-beeper/source-format.json).
- One faster player: distribute housekeeping across 16-T slots and use
  relative branches. Output kernel stays 30 T; ordinary output is **46 T/bit,
  368 T/byte**, versus 52 /416: **-6 T/bit, -48 T/byte**. Boundary flag test
  costs 34 T across slots. The opt-in repeat path prepares bank 0 while the
  last byte plays; its absolute return costs **48 T** for the final bit
  (final byte 370 T, -46 versus 416). Total deterministic repeat cost is
  `786432*46+2` T. ULA, ROM and disk are excluded from these CPU counts;
  [instruction table and memory contract](audiobook-beeper/README.md) record
  the details. The default 52-T disk still reproduces byte for byte.
- Host conversion: existing 70 Hz highpass/two 3800 Hz lowpasses, peak 0.65,
  20 ms edge fades; antialiased resampling to 8000 Hz, nearest-level unsigned
  8-bit quantization, then band-limited reconstruction of those exact bytes
  at 192 kHz for the second-order PDM modulator. Save the actual 8-bit WAV;
  listening WAVs remain 44100 Hz /16-bit mono. TRD data is packed one-bit PDM.
- The first single-pass build completed before the repeat request:
  **75924.035 bit/s average, 62226.316 minimum, 10.3581429 s**. Full native
  and cold Fuse checks pass 786432 bits. Retain its disk, reports, WAVs and
  compressed exact producer sources in [preview-8k8](audiobook-beeper/preview-8k8/report.json).
- The first loop-verification harness stalled before collecting a trace;
  terminate that specific Fuse process and retain the
  [interrupted pilot/script](audiobook-beeper/experiments/loop-debugger-interrupted/timing-pilot/verification-work/fuse-debugger.txt).
  Replace inline breakpoint conditions with the existing `condition id`
  syntax, then rerun the complete pilot and speech checks. This interrupted
  attempt does not count as playback evidence.
- Final looping delivery: cold Fuse verifies **1572865 exact writes** (two
  complete cycles plus the first bit of cycle 3), both repeat edges, all
  thirteen bank selections, 384 startup reads and **zero runtime reads**.
  Actual average **75923.916 bit/s** (+13.46% versus 66915.539), minimum
  **62226.316**, maximum 77106.522. Intervals are 46/47/48/49/50/57 T;
  both wrap holds are 48 T. Cycle durations are 10.3581434 and 10.3581747 s.
  Pilot and speech first-cycle timestamps agree exactly. Six native/DSP
  tests cover all byte values, partial/full banks, both rates, two repeats,
  stack/code guards, DC preservation and hold integration. See
  [complete verification](audiobook-beeper/preview-8k8-loop/verification.json).
- First-cycle reconstruction correlation 0.981439, SNR 14.1700 dB against
  this build's converted PCM using the same explicit 4.5 kHz filter. These
  are not directly comparable to the old higher-resolution source metric,
  a listener acceptance score, or a physical speaker recording.
- Decision: deliver [ZX-audiobook-PDM-8k8-test.trd](ZX-audiobook-PDM-8k8-test.trd)
  in Git LFS, SHA-256
  `db99485573022ba5eb015fc87e6d02edf191dcfe4aea2c1166b6ef40e2a8a4a5`,
  655360 bytes /428 occupied sectors. Independently bootable, repeats from
  RAM until reset; no streaming/full-book claim. The old disk is unchanged.
  [Integrity check](audiobook-beeper/delivery-8k8.json) authenticates 38 saved
  artifacts, exact producer sources and PCM formats. Reproduce with
  `build_pdm.py --bit-tstates 46 --pcm8k --repeat` and the documented paths.

## 2026-10-01: switch audiobook speech to high-rate beeper PDM

- User feedback/scope: the YM2149 test TRD is also unintelligible. The user
  requested PDM on the beeper with a carrier of at least 40 kHz. Baseline
  `2a22f77`; preserve the AY history and implement a separate
  [audiobook-beeper](audiobook-beeper/README.md) subproject. Use a bounded
  resident excerpt beginning at the same source time 60 seconds, not a
  streaming/two-minute/full-book release. Source identity is authenticated.
- Initial implementation: 64 deterministic T/bit, 80 KiB, second-order
  area-weighted error-feedback PDM. A complete timing pilot and speech run
  verify all 655360 bits in independent Z80 and cold Fuse. Actual average
  54823.104 bit/s, minimum 44336.25, 11.954084 s; 320 startup reads, zero
  runtime reads. The first render-only gate expected identical pilot/speech
  timestamps and stopped on a one-T startup difference after full playback
  had already passed. Retain the disk, reports, waveforms and exact producer
  snapshots in [the 64-T archive](audiobook-beeper/experiments/pdm64/report.json).
  Resume rendering with a bounded three-T startup allowance, actual final
  timestamps and the unchanged every-interval >=40 kHz gate.
- One follow-up addresses quantization noise by shortening the output cycle.
  Spread pointer-wrap preparation and page switching over several output
  slots, preserving the wrap-test flags with AF'. Kernel 30 T + housekeeping
  22 T = **52 T/bit /416 T/byte**, versus 64 /512: **-12 T/bit /-96 T/byte**.
  Final sample hold is 52 T. Source table/assumptions are documented; existing
  movie and AY player code is unchanged. Native tests verify every byte value,
  all six banks, partial banks, invalid sizes and stack/code integrity.
- Final build uses 96 KiB in banks 0,4,6,1,3,7; banks 2 and 5 retain code,
  stack, display, BASIC and TR-DOS workspace. Both complete independent Z80
  and cold Fuse runs verify **786432 exact speech bits**. Actual intervals
  52/53/55/56/60 T give **66915.539 bit/s average, 59115 minimum**. Duration
  **11.7526065 s**, 384 startup reads, zero runtime reads, final mute exact.
  The 428-sector TRD boots independently. No IRQ runs during PDM. Pilot/speech
  phase differs by two T (0.564 us), without accumulating drift.
  [Full evidence](audiobook-beeper/preview/verification.json).
- Audio preparation: mono, 70 Hz highpass, two two-pole 3800 Hz lowpasses,
  peak 0.65, 20 ms edge fades, fixed small TPDF dither. Reconstruct the final
  measured port hold times at 192 kHz and provide filtered and wideband WAVs.
  The 4500 Hz listening filter is explicit, not a physical speaker model.
  Four tests pass, including nonuniform-slot DC preservation and exact hold
  integration. Packing/unpacking and every actual output bit are exact.
- On the common [60.1,70.1) passage with identical reconstruction filters,
  waveform correlation improves **0.907986 ->0.964705** and SNR **6.6909
  ->11.2622 dB** (+4.5713 dB). [Comparison](audiobook-beeper/comparison.json)
  supports selecting 52 T; it is not a perceptual intelligibility score.
- Decision/delivery: publish [ZX-audiobook-PDM-test.trd](ZX-audiobook-PDM-test.trd)
  in Git LFS, SHA-256
  `3aa0a4d1f7e40e9943330d5dcbc44f0495990f91b8d660b42ec9521005d40dad`,
  identical to the verified final disk. Deliver the roughly 12-second test
  for listening; no physical recording or longer streaming claim is made.
- Archive follow-up: pin debugger scripts to LF so the saved artifact hashes
  also survive a Windows checkout with `core.autocrlf`; audio/code are unchanged.

## 2026-10-01: publish the YM2149 test disk in the project root

- The user requested a TRD to listen in an emulator. Baseline `7950579`;
  publish [ZX-audiobook-YM2149-test.trd](ZX-audiobook-YM2149-test.trd) as a
  byte-identical copy of the verified 24-second [60,84) audiobook candidate.
  It retains 50 Hz register playback and the existing independent cold boot.
- The 655360-byte image has SHA-256
  `190ce25bfc5e113d2c7f499df3c6971219f44cca024733a2a5f60e6fccfc49ab`, matching
  the saved [full native/Fuse verification](audiobook-ay/ym2149-preview/verification.json).
  Reuse its 1200-tick /13200-write, zero-missed-field evidence; no re-encoding
  or player change (0 T delta), and no redundant emulator run. Store the
  root image in Git LFS and document drive A / `RUN "boot"` startup.

## 2026-10-01: improve LPC parameters and check 50 Hz YM2149 mono playback

- Objective and input: after accepting the full host LPC2 reference as clear,
  the user requested better preservation, then explicitly constrained the
  chip check to three tones/shared noise, one update per 50 Hz interrupt and
  typical Spectrum mixing. Baseline `621dadf`; reuse the exact [60,84) source
  passage and unchanged external LPC2 DSP. The accepted reference was not AY.
- First bounded host candidate: 10 ms hop and exact-only coefficient repeats,
  otherwise unchanged. 4114 ->12601 LPC bytes, 1200 ->2400 frames; spectral
  cosine 0.874207 ->0.896003, loudness correlation 0.809145 ->0.920091, onset
  F1 0.840580 ->0.869565. The baseline stream and metrics reproduce exactly.
  Independent Python frame parsing, round-trip packing and all 192000 finite
  decoded samples pass. Retain [evidence](audiobook-ay/lpc-detail/report.json)
  but do not select 100 Hz updates after the user's cadence clarification.
- Final candidate keeps 20 ms frames and removes approximate LSF repeats:
  4114 ->6461 LPC bytes; repeat frames 516 ->11, unchanged excitation/pitch/
  silence classifications. Map LPC formants to chip periods and actual YM
  fixed-volume levels. Render with vendored, unmodified MIT Ayumi JS revision
  `3a1fb9120cc2c5ef8f538af59b46701e4c2305bb`: 1773450 Hz, 50 state updates/s,
  three tone channels, one shared LFSR, true Boolean mixer, equal mono sum.
  No full LPC filter or high-rate DAC output is attributed to the chip.
- Same-chip old/new proxies: spectral cosine 0.596526 ->0.666873, loudness
  correlation 0.858975 ->0.874808, onset F1 0.711864 ->0.757576. Full software
  LPC remains at 0.889800 spectral cosine. These are not perceptual quality
  percentages. Save equal-RMS original, old mapping, new YM and full LPC WAVs
  in [the listening comparison](audiobook-ay/YM2149_PREVIEW.md).
- Native hot path is unchanged: 974 T/tick, delta 0 T. Complete independent
  Z80 and cold Fuse playback verify 1200 ticks /13200 exact writes, no missing
  or duplicate fields, final full-field hold, 52 startup and zero runtime
  sector reads. First OUT phase 150..153 T, intervals 70905..70909 T. The
  diagnostic TRD uses 96 sectors. Seven Python tests plus chip period, shared
  noise taps, all 16 mixer combinations, DAC, silence and sample-count checks
  pass. [Timing evidence](audiobook-ay/ym2149-preview/verification.json).
- Decision: deliver this 24-second **50 Hz mono chip-model candidate** for
  listening, without claiming it preserves the accepted full LPC clarity.
  The disk replays prepared register states; no native LPC decoder exists.
  Ideal 20 ms/atomic waveform updates, sequential native OUTs and physical
  analogue loading are distinguished. No physical hardware was recorded.
  The original two-minute disk and movie releases remain unchanged.

## 2026-10-01: reuse LPC2 for a bounded audiobook speech comparison

- User feedback: the first movie-style audiobook AY preview is completely
  unintelligible. The user pointed to `C:/Work/LPC-sound-codec` as a possible
  foundation. Baseline `8cb13c1`; use only the same source interval [60,84),
  preserving the rejected two-minute preview for comparison.
- Found the separate LPC2 Improved codec (HEAD `360af14`) and reused its
  existing DSP through a headless [bridge](audiobook-ay/lpc2_bridge.js), with
  source/core hashes and an archived exact core. The LPC repository remains
  unchanged. Settings: 8 kHz, order 10, 20 ms frames / 32 ms analysis, .85
  pre-emphasis, .38 voicing, .05 repeats, .65 pitch smoothing, .35 postfilter,
  4 dB brightness and 70 Hz DC block. One 1200-frame LPC2 file is 4114 bytes;
  unpack/repack is bit-exact. A full LPC2 reference WAV is provided separately.
- One candidate maps LPC2 envelope resonances to three AY periods without
  musical-note quantization, and nonvoiced modes to noise on B. It reuses
  the resident player unchanged (hot-path delta 0 T). It is not a native LPC
  decoder or PCM/DAC player. [Probe](audiobook-ay/probe_lpc2.py) and
  [comparison](audiobook-ay/LPC2_COMPARISON.md) preserve the original, previous
  AY, full LPC2 reference and candidate AY as equal-RMS 24-second WAVs.
- Results at 10 Hz: old AY / full LPC2 / LPC2-to-AY spectral cosine
  0.847394 / 0.874207 / 0.588041, loudness correlation
  0.981217 / 0.809145 / 0.781854, onset F1 0.765432 / 0.840580 / 0.656250.
  These proxies do not prove speech intelligibility; no new sample has been
  accepted by a listener. The formant mapping worsens all listed proxies.
- Complete candidate verification: all 1200 fields and 13200 actual AY
  writes match through EOF in native execution and cold Fuse. No missed or
  duplicate fields; first OUT 150..153 T, intervals 70905..70909 T. All native
  ticks cost 974 T. One diagnostic TRD uses 96 sectors, with 52 startup reads
  and zero runtime reads. Five tests pass, including known LPC resonances,
  silence/nonvoiced modes, all bank boundaries, maximum length and IRQ state.
  [Full evidence](audiobook-ay/lpc-probe/verification.json) is archived; physical
  hardware and complete LPC decoding on Z80 remain untested.
- Decision: do not promote the AY formant mapping or rebuild the two-minute
  preview with it. Keep the bounded diagnostic and LPC2 reference for listening.
  The reusable foundation is the LPC speech model/bitstream. Preserving the
  full filter requires sample synthesis and rapid AY volume output; the
  approximately 443 T/sample budget at 8 kHz still needs a native feasibility
  test. No unsupported quality improvement or Z80 throughput is claimed.

## 2026-10-01: add a two-minute compact AY audiobook subproject

- Objective: add a separate folder for the supplied O. Henry recording.
  The user explicitly selected compact AY synthesis as in the movie, then
  requested a two-minute preview. Baseline `c7e1554`; source duration
  667.596916 seconds, SHA-256 recorded in the [report](audiobook-ay/preview/report.json).
  Deliver only source interval [0,120), with one second of analysis context.
  Full-book conversion and PCM/DAC playback are outside this selected scope.
- Added [audiobook-ay](audiobook-ay/README.md), a reproducible bounded audio
  converter, a resident Spectrum 128 player, comparison WAVs and one cold-
  bootable TRD. Reuse the movie's square-aware synthesizer unchanged: 50 Hz,
  three tone voices, optional noise on B, one-step noise attenuation and
  50-cent period refinement. Original and AY WAVs share RMS 0.0603964.
  The WAV is the existing approximate renderer, not a physical AY capture.
- Capacity: 6000 ticks, 54000 packed bytes / 25039 gzip archive bytes,
  66000 resident register bytes. One TRD uses 302 of 2544 sectors. Five
  data banks hold whole eleven-register records; screen, fixed code, stack,
  IRQ table and TR-DOS workspace are accounted for; bank 7 is spare.
  All 258 audio sectors load before playback, with zero runtime disk reads.
- Complete verification: all 66000 register values and their order match in
  independent native Z80 replay and real Fuse cold boot through EOF. All
  6000 fields are consecutive; no dropped/duplicated AY ticks or drift.
  Actual first-OUT phases are 150..153 T; adjacent intervals 70905..70911 T.
  All four bank changes and the final full-field hold pass. Native EOF
  mutes every channel. Physical hardware and full-book delivery are untested.
- CPU: ordinary field work 974 T, near-bank-end 992 T, bank change 1091 T,
  exact-boundary EOF 1007 T. IRQ body 18 T plus 19 T IM2 acknowledge and
  10 T vector jump; HALT/ULA/boot ROM/disk latency are separate. The existing
  movie hot path changes by 0 T. The old queued eleven-write audio routine
  is 1280 T; this separate no-queue foreground path is 974 T (-306 T), with
  its different contract documented. Zilog instruction sums and independent
  CPU execution agree. An initial boundary-test expectation was 4 T low;
  it was corrected to 1007 T without changing the generated player.
- Quality proxies at 10 Hz: spectral cosine 0.850804, chroma cosine
  0.960339, loudness correlation 0.989443, onset F1 0.807198. These are
  not speech intelligibility or accuracy percentages. Listening judgment
  remains with the user; the tonal/noise approximation changes the voice.
- Decision: deliver the complete requested preview and await sound feedback
  before another encoder experiment or full-book streaming milestone.
  [Builder](audiobook-ay/build_preview.py), [verifier](audiobook-ay/verify_preview.py),
  [native boundary tests](audiobook-ay/test_player.py),
  [full playback evidence](audiobook-ay/preview/verification.json) and compressed
  actual-OUT trace are preserved. TRD and comparison WAVs use Git LFS.

## 2026-10-01: deliver the full refined movie on four independent disks

- Objective: replace the 15-disk refined movie with at most 4 disks, retaining
  the complete authorized edit, refined RGB, square-aware AY50 and10 fps.
  Baseline `f1476a2`. Build one coherent set from accepted cached CB46 streams
  with boundaries0/1312/2672/3744/5066. Reuse the guarded part 4 attribute
  stream; no media quantization, compression sweep or alternate partition.
- New scripts: `build_cached_cell_set.py` authenticates cached media and
  creates a common content-derived series ID plus independent cold state;
  `check_cached_cell_set.py` runs native verification concurrently with serial
  Fuse cold runs, predecessor-EOF continuations and full screen captures;
  `finish_cached_cell_set.py` audits all gates, archives evidence and installs
  only the expected numbered refined images. Wrong disks/series are rejected
  at all 3 boundaries. The root-hash guard preserves unrelated changes.
- Capacity: **2464/2476/2542/2543 occupied sectors**, each within 2544, leaving
  80/68/2/1 sectors. Total video 2462188 bytes; four TRDs total 2621440 bytes.
  First 3 volumes reuse 608061/604926/626506 video bytes, part 4 reuses 622695.
  Decoder, renderer, packet and side-reader machine bytes match the passing
  full part 4 baseline exactly; instruction delta 0 T. Build-time identity
  changes only ID data. Per-volume CPU histograms and disk/IRQ/ULA elapsed
  profiles are retained separately.
- Fidelity: every prepared chunk is hash-checked and its five-level states
  compared with the canonical 5066-frame movie. Independent full-frame RGB
  proof preserves every visible pixel, including both screen histories;
  only unused attribute bits differ. All25330 AY register states and every
  disk-boundary checkpoint match the prepared refined soundtrack. The
 90-second credits cut is unchanged; retained source frame 0 through 5965
  includes the post-credit scene and source EOF. The8 difficult/source/EOF
  comparison samples were inspected; existing sky colour bands remain and
  no new visible change is introduced. Frame-level quality metrics are saved.
- Complete verification:4 dirty-RAM cold boots,4 native full-volume replays,
  all 5066 cold Fuse frames and all 5066 sequential frames; each mode compares
  **35016192 screen bytes** and25330 AY ticks. Continuation captures now load
  the exact same predecessor-EOF snapshot as the timing run and verify its
  hash, closing the previous cold-only full-screen capture scope. No dropped
  frames, read retries, AY gaps/duplicates or audio underruns occur. Physical
  drive/controller state across swaps was not measured; emulator restarts
  retain actual predecessor RAM and deliberately poison the other banks.
- Timing: the strict zero-late target is **not achieved**. Cold disks have
  0/0/1/0 misses, maximum actual 70907 T. Sequential playback has 0/0/1/1,
  maximum 70908 T (20 ms). Disk3 local 933 recovers at 934; continuation disk 4
  local 576 recovers at 577. All field intervals stay 4..6 and the original
  schedule is restored immediately. The disk 3 trace identifies a new-cylinder
  read overlapping publication, followed by 227523 T of elapsed drawing.
- Decision: use the user's already authorized one-field fallback to deliver
  the four-disk set. The explicit `--allow-fallback` gate rejects even 1 T
  beyond 70908 T;4 regression tests also reject absent recovery, invalid field
  counts, incomplete playback and sound gaps. Every nominal miss remains
  listed. The report retains `release: false` /`preview_only: true` for the
  unachieved zero-late target, and separately marks the authorized delivery.
  This is the complete movie, not a smaller timing fixture or reduced-fps set.
- Root `ZX-video-refined_part01..04.trd` replace the prior preview; obsolete
  refined parts 5..15 are removed after verifying all new copies. Images use
  Git LFS. Historical evidence, other experiments and the verified three-disk
  25/3-fps compatibility set remain intact. See [usage](ZX-video-refined.md),
  [report](toolkit/refined_four_report.json), [gate tests](toolkit/test_cached_set_gate.py)
  and `.tmp/refined-four-candidate/` for reproduction. Future zero-late work
  should reuse the recorded isolated stalls before attempting another build.

## 2026-10-01: skip redundant disk SEEK and settling on side-only changes

- Objective: improve sustained delivery without increasing compressed bytes
  or decoder cost, then fulfill the user's explicit request to minimize disk
  head travel. Baseline `23dc128`; reuse the direct-header 256-frame window
  [4096,4352) and accepted invisible-attribute part 4 [3744,5066). No new
  media preparation, packet format, interleave or full-set sweep.
- The existing runtime order already traverses consecutive logical tracks,
  with minimum one-way cylinder travel. The redundant work was SEEK plus
  READ 84h settling at every side change. The opt-in helper now compares
  physical cylinders, selects the side, waits 717 T (>200 us at3.5469 MHz),
  and uses READ 80h when the cylinder remains unchanged. Real cylinder
  changes retain the drive's step rate, SEEK/HLD and READ84. FFh cold state,
  FEh idle recovery, periodic head-loaded maintenance and short-read fallback
  remain intact. The generic `--guarded-cb46` profile selects this automatically.
- Hardware evidence: pinned TR-DOS 5.03 bytes at1FEBh/1FF6h/3E44h, FD179x
  E-bit semantics, and the Shugart SA460 manual's200 us side-select minimum.
  This is a standard-clock, emulator-verified implementation; no physical
  drive or turbo mode was tested. Source links and assumptions are in
  [SIDE_ONLY_SEEK.md](toolkit/SIDE_ONLY_SEEK.md).
- Exact RAM helper counts, excluding ROM/controller/IRQ/ULA: side1
  **401 ->1009 T (+608)**, side0 **391 ->999 (+608)**, cylinder-side0
  **391 ->456 (+65)**, FEh recovery-side1 **401 ->466 (+65)**. Same-track and
  cold adapter paths change by0 T. The explicit short pause increases RAM
  work but replaces the long controller delay. Decoder/renderer opcodes and
  timing tables change by0 T. Helper89 ->107 bytes, extra stack2 bytes;
  startup still occupies the same number of sectors.
- Window:185681 video bytes /781 occupied sectors unchanged. Read-path SEEKs
  **45 ->22**, nominal misses **2 ->0**, maximum actual OUT deviation
  **70917 ->16 T**, zero invalid intervals. Full part4:622695 video bytes,
  2433 runtime sectors /2543 occupied unchanged; SEEKs **152 ->76**, nominal
  misses **22 ->0**, actual deviation **1063627 ->19 T**, invalid intervals
  **11 ->0**. No late runs remain. Keepalive calls are separate and stay on
  the last-read cylinder; they are not physical backward motion.
- Verification:8 component tests pass, including2560 geometry/drive/bank
  combinations, sentinels, corrupted short-read fallback,1024 independent
  full-AF cases, minimum delay, exact default bytes and existing real-AY IRQ
  keepalive checks. Both scopes pass dirty cold boots, complete native and
  complete Fuse screen-byte comparison:1578 frames /10907136 screen bytes,
  7890 exact AY ticks, no read retries or audio underruns. The generic
  converter also passes a fresh10-frame/50-tick colour fixture on3 independent
  disks (31/42/41 occupied sectors), zero misses and both modeled-ROM swaps.
- Initial window build stopped before producing a TRD because the install
  guard expected a top-level `cached_seek` flag not yet present during RAM
  construction. Corrected it to validate actual seek labels, pinned ROM
  identity, old machine bytes, free space and active keepalive; the builder
  also requires its fast/cached options. The failed log is preserved.
- Decision: retain and enable this in the guarded profile. It fixes the
  previously failing full part4 timing while preserving compression and
  media. Root releases remain unchanged: parts1..3 and actual preceding-EOF
  continuation of one coherent four-volume set remain unverified.
  Reproduce with [analyzer](toolkit/analyze_side_only_seek.py),
  [tests](toolkit/test_side_only_seek.py) and the cached rebuilder; reuse
  `.tmp/side-only-seek-window-fixed/`, `.tmp/side-only-seek-part04/`,
  `.tmp/side-only-seek-generic/` and [hashed evidence](toolkit/side_only_seek_report.json).

## 2026-10-01: generic converter selects the guarded four-slot CB46 profile

- Objective: connect the measured compression/delivery components to the
  ordinary video converter without movie-specific paths or cuts. Baseline
  `7cfbacf`. Keep default profiles unchanged; add opt-in `--guarded-cb46`.
- The profile selects dynamic rows, front reuse, partial row pairs, inline
  cells, four video slots, fixed AY trees/tail, compressed-sector cache and
  direct-header streaming LZSA2 as a unit. Planning retains the existing
  32-frame probes and checks the actual AY forest/tail, including its B900h
  cache-helper boundary. It does not build alternate complete disk sets.
- The generic host selector removes invisible attribute writes, measures
  every block with the independent Z80 core and enforces its original byte
  and CPU budgets. It restores failed frame packets, replans histories and
  retains the original stream if no byte saving remains. Unchanged blocks
  reuse their encoding; repeated candidates are cached. The flat measurement
  input moved to 2000h so near-incompressible blocks cannot overlap the
  7C00h wrapper; this is not a player RAM-layout change. The existing fitter
  retains its previous default input address for other callers.
- Saved movie window [4096,4352): the generic representation and accepted
  output reproduce the earlier candidate exactly: 185681 ->185605 bytes,
  16049945 ->16036695 decoder T, unchanged rendered RGB and row/cell books.
  Only nine distinct blocks are recompressed. Reuse
  `.tmp/generic-guarded-window/`; no new movie TRD was built.
- The first generated colour fixture failed before writing an image:
  its inherited LZSA2 core starts at 8D98h and overlaps the inline renderer.
  The new opt-in build-time relocation pins it to 8D74h after retiring the
  unused legacy renderer. Public entries/state and producer bytes stay
  fixed. Every listed instruction keeps its absolute T-state count: the
  old/new timing arrays are archived, per-instruction and total deltas zero.
  The final 222-byte cold wrapper and 251-byte streaming core are identical
  to the measured full-volume decoder. No new playback opcode is introduced.
- Verification: 21 focused tests pass, including unchanged default modes,
  real independent decoder costs, forced CPU-budget fallback, both screen
  histories, exact RGB, fixed AY limits and the B900h collision boundary.
  Five generated media cases (single frame, portrait, colour, non-square
  pixels and longer audio tail) produce seven independently bootable test
  TRDs. All 23 frames /158976 screen bytes and 115 AY ticks pass complete
  native/cold/Fuse checks with zero nominal misses. The colour case spans
  three disks; both modeled-ROM swap/bootstrap checks pass. This does not
  claim full preceding-EOF Fuse continuation for the movie.
- Decision: retain the generic profile as experimental. These short tests
  prove converter integration, not sustained delivery of the movie. Root
  releases remain unchanged; full part 4 still has 22 nominal misses, and
  the four-volume cold/continuation release gates remain open.
- Reproduce with [selector](toolkit/guarded_cb46.py),
  [window check](toolkit/check_guarded_cb46.py), `check_generic_cb41.py
  --fps 10 --guarded-cb46`, [tests](toolkit/test_guarded_cb46.py) and
  [archive verifier](toolkit/verify_guarded_cb46.py).
  [Report](toolkit/generic_guarded_cb46_report.json) retains the failed
  placement attempt and all successful checks; test TRDs use Git LFS.
- Next bounded timing investigation: the current cached-seek helper always
  issues SEEK and sets the delayed READ command 84h after changing logical
  track, including a side change on the same cylinder. Check the actual
  ROM/controller requirements before attempting to omit that work. Compare
  the same window and complete part 4 if a guarded path is feasible; keep
  codec/media bytes unchanged and account separately for CPU and disk time.

## 2026-10-01: invisible attribute removal saves bytes within every original decoder budget

- Objective: improve compression at unchanged decoding cost on cached CB46
  data. Baseline `32c6649`; original [4096,4352) window and complete part 4
  [3744,5066), fixed bitmap/dither, mutable row table, static cell book,
  AY50 and 10 fps. No new video preparation or whole-set image sweep.
- Encoder-only transform: retain the previous physical attribute through
  an entire constant-attribute run on the same back-screen parity when its
  used INK/PAPER RGB colours remain identical throughout. Check future
  visibility, not just the first frame. BRIGHT remains significant except
  for black. No bitmap bit, dither phase, visible RGB pixel or AY value changes.
  No later attribute write is added relative to the original stream.
- Recompress the affected raw blocks with the existing pinned LZSA2 and keep
  each original output extent after deleted bytes. The existing short-match
  fitter enforces original Z80 CPU budgets. If any block still exceeds its
  byte or CPU budget, freeze all overlapping original frame packets, replan
  attribute histories and measure again. Do not splice alternatives with
  inconsistent physical histories. The frozen frame set only grows.
- Window: the unfitted transform saves 77 bytes but slows blocks 3/4 by 886/101 T.
  Fitting costs one byte and removes those regressions. Accepted result:
  **185681 ->185605 bytes** (-76; still 726 video sectors), **16049945
  ->16036695 decoder T** (-13250), all 16 blocks no larger or slower.
  Removing 133 attribute writes saves 5562 renderer T. Window coverage is host
  RGB/packet proofs plus independent decoder execution, not physical playback.
- Full part 4: the first candidate removes 787 writes and saves 268 bytes /
  50063 decoder T overall, but blocks 1/4/5/10/18/48/49/54 violate an individual
  budget. One fallback iteration freezes 238 frames. Final accepted result:
  **623005 ->622695 bytes** (-310), **2434 ->2433 video sectors**,
  **55808156 ->55754985 decoder T** (-53171), all 55 blocks no larger or
  slower. Removing 718 writes saves 33337 renderer T. This is a small gain,
  not evidence that larger compression gains remain available by this method.
- Renderer instructions are unchanged. Exact fast attribute-mask accounting:
  nonempty group 233 T +23 T per write; empty group 94 T, or 93 when E wraps.
  A removed write saves 23 T while its group remains nonempty; removing the
  last write also saves 139/140 T. Five tests cover 49152 colour/usage cases,
  future visibility, parity, all 16 restoration subsets, boundary mapping,
  complete restoration, and 24 guarded/independent native renderer executions.
  Decoder counts use identical non-streaming instructions and 256-byte output
  quotas, excluding TR-DOS, physical reads, IRQ and ULA contention.
- One full part 4 TRD uses the previously verified direct-header player.
  Occupancy **2544 ->2543 sectors**. Dirty-RAM boot, complete guarded native
  playback and full Fuse screen capture pass (1322 frames /9137664 screen
  bytes); 6610 AY ticks and 2433 runtime sectors are exact. Physical attributes
  match the transformed reference; independent RGB comparison proves its
  picture is identical to the original, including borders and dither.
- Actual timing remains unsuitable for release: 22 nominal misses before
  and after; 20 ->21 beyond one field; maximum 15 fields, actual 1063627 T;
  invalid intervals 13 ->11. Runs 378,593..602,615..625 recover at 379/603/626.
  Deterministic CPU savings do not imply improved physical publication timing.
- Decision: retain this guarded host pass and cached rebuild option
  `--invisible-attributes-probe`; do not change converter defaults or root
  release images. Four-volume timing and preceding-EOF continuation gates
  remain open. No image quality tradeoff or relaxed timing requirement.
- Reproduce with [host transform](toolkit/invisible_attribute_writes.py),
  [probe](toolkit/probe_invisible_attributes.py),
  [automatic budget fallback](toolkit/fit_invisible_attribute_budgets.py),
  [tests](toolkit/test_invisible_attributes.py), cached rebuilder and
  [archive verifier](toolkit/verify_invisible_attributes.py).
  [Report](toolkit/invisible_attributes_report.json) retains both unsuccessful
  passes, accepted streams, pixel proofs, full playback and separate profiles.

## 2026-10-01: earlier prefix admission preserves content but worsens delivery

- Objective: finish the bounded scheduling test after the direct header
  optimization. Baseline `3fa1167`; unchanged CB46/LZSA2 streams, four slots,
  inline cells, sector cache, 10 fps and AY50. Test the same [4096,4352)
  window and complete part 4 [3744,5066), without rebuilding the movie.
- Opt-in `--early-lzsa2-prefix` requires the direct header guard. Prefix
  decoding may start with one completed slot remaining; two or more retain
  the complete-input preference. The incomplete-input count test changes
  `LD A,(count); OR A; JP NZ` (13+4+10=27 T) to
  `LD A,(count); CP 2; JP NC` (13+7+10=30 T), delta +3 T. Complete-input
  bypass delta is zero. Decoder machine code is identical, although changed
  scheduling changes how often its guards and suspensions execute.
- Two independent Z80 tests cover 40 admission cases: counts 0..3,
  complete/partial input, available/unavailable prefixes, both variants,
  exact costs, stack and count preservation.
- Window: 2 ->14 nominal misses, all 14 beyond one field, maximum 1 ->10
  fields (709079 actual T), invalid intervals 0 ->6. Runs 123 and 239..251
  recover at 124/252. Video remains 185681 bytes, 726 runtime sectors and
  781 occupied sectors.
- Full part 4: 22 ->48 misses, 20 ->47 beyond one field, maximum 15 ->30
  fields (2127250 actual T), invalid intervals 13 ->32. Runs 378,
  585..609 and 611..632 recover at 379/610/633. Video remains 623005 bytes,
  2434 runtime sectors and 2544 occupied sectors.
- Both scopes pass dirty-RAM boot, complete native playback with frontier,
  sector-cache and retired-memory guards, full Fuse screen comparison
  (1769472/9137664 bytes), exact AY50 (1280/6610 ticks), and disk-sector
  checks. Profiles separate physical disk/IRQ/ULA elapsed time from the
  deterministic instruction counts above.
- Decision: reject earlier admission and keep its option disabled. Exact
  content does not offset worse timing. Root releases are unchanged; no
  four-volume release or preceding-EOF continuation is claimed.
- Reproduce with [admission tests](toolkit/test_early_lzsa2_prefix.py), cached
  rebuilder with `--early-lzsa2-prefix`, existing full native/Fuse tools and
  `verify_streaming_bypass_playback.py --early-prefix`. Saved
  [report](toolkit/early_lzsa2_prefix_report.json) includes the builds/traces.
- Next: test removing invisible attribute writes on the host, preserving
  every rendered RGB pixel and introducing no later writes. Keep the same
  renderer/codec and require measured compression and CPU benefit.

## 2026-10-01: direct LZSA2 header guard saves 50 T and improves complete part-4 delivery

- Objective: improve the remaining input-prefix path without changing
  compressed data or the completed-input fast path. Baseline `ca70859`;
  branch-bypass CB46/LZSA2, four slots, sector cache, inline renderer, AY50,
  10 fps. Reused the exact 256-frame window and full part 4.
- New opt-in `--direct-lzsa2-header` requires `--streaming-lzsa2`. The quota
  branches enter a guard directly, then jump to the token body. Token parsing
  overwrites AF, so the header guard can omit CALL/RET/PUSH AF/POP AF. AF',
  HL/DE/BC and the private decoder stack remain preserved across suspension.
  Long-literal guards are unchanged. Explicit `token_guard`/`token_body`
  labels replace the fragile `Token+3` assumption in producer and tests.
- Independent Z80 checks confirm the available-header path **96 ->46 T**,
  delta -50. Frontier-wait entry **98 ->63 T**, delta -35; overflow-wait entry
  **89 ->51 T**, delta -38. After input_wait, rechecking the output quota costs
  **12 ->31/59 T**, delta +19/+47, depending on its high-byte comparison.
  That re-entry is necessary when the last sector has switched to the complete
  input path. Completed-token/long16 deltas remain 0 and long8 remains -2 T
  versus the original non-streaming decoder. ROM/IRQ/ULA/disk costs are excluded.
- Three unit tests cover 512 AF/register cases, both archived default decoder
  variants byte-for-byte, frontier/overflow waits and resume costs. Forty
  component blocks and 240 independent full-flags in-place cases pass, including
  six stream alignments, injected interrupts, long literals and all offset
  widths. With the same deliberately forced sector-prefix workload, total
  component cost falls **25878233 ->23879878 T**, saving 1998355 T. This is
  not a physical-playback timing estimate.
- Window [4096,4352): two nominal misses remain, at 123/242, recovered at
  124/243; max one field, zero invalid intervals, actual maximum 70917 T.
  This still exceeds the strict 70908-T fallback by nine T. Capacity remains
  781 sectors and video remains 185681 bytes.
- Full part 4 [3744,5066): **31 ->22 nominal misses**, **30 ->20** beyond one
  field, **21 ->15 maximum fields**, **17 ->13 invalid intervals**. Runs 378,
  593..601, 615..625 and 685 recover at 379/602/626/686. Maximum actual deviation
  is 1063618 T. Capacity stays 2544 sectors and video stays 623005 bytes.
- Both scopes pass dirty-RAM cold boot, every native screen with input-frontier,
  cache and retired-memory guards, full Fuse screen-byte capture (1769472 /
  9137664 bytes), exact AY50 (1280/6610 ticks) and runtime sectors (726/2434).
  Retain this measured speed improvement as opt-in, not a release: complete
  four-volume timing and preceding-EOF continuations remain unverified.
- Reproduce with [unit tests](toolkit/test_direct_lzsa2_header.py),
  `test_streaming_lzsa2.py --direct-header`, cached rebuilder, existing native/
  Fuse verifiers and `verify_streaming_bypass_playback.py --direct-header`.
  [Report](toolkit/direct_lzsa2_header_report.json) preserves exact inputs and
  traces. Root images and converter defaults remain unchanged.
- Next bounded scheduling question: with cheaper prefix checks, can decoding
  begin while one completed slot remains, instead of waiting for count zero?
  Preserve the full-input fast path with two or more slots. Check the same
  window and full part 4; do not sweep other formats or rebuild the whole set.

## 2026-10-01: complete branch-bypass LZSA2 playback, window gain does not pass full-volume timing

- Objective: finish verification of the existing, previously cold/component-only
  decoder before another implementation experiment. Baseline `2c3bf78`; exact
  sector-cache streams, CB46, four slots, inline renderer, AY50 and 10 fps.
  The optional-read admission gate is disabled.
- The [4096,4352) window improves from eight nominal misses/max7 fields/four
  invalid intervals to two isolated misses/max1/zero invalid intervals.
  Local frames 123 and 232 recover at 124 and 233. Actual OUT deviation reaches
  70914 T, six T beyond one 70908-T field: the strict actual-OUT fallback still
  fails. This distinction is not rounded away. Occupancy stays 781 sectors.
- Full part 4 [3744,5066) changes from 29 nominal misses/28 beyond one field/
  max23/23 invalid intervals to 31/30/max21/17. Runs 378, 591..603, 614..629,
  687 recover at 379/604/630/688. The long late run extends beyond the short
  window's EOF. Actual maximum deviation is 1489065 T. Full part 4 occupies
  2544/2544 sectors, versus 2543 before; extra bootstrap code costs one sector,
  while raw packets, compressed LZSA2, AY and dictionary bytes stay identical.
- Both builds pass dirty-RAM boot, every native screen with input-frontier,
  cache and retired-memory guards, every Fuse screen byte (1769472 window /
  9137664 full disk), exact AY (1280/6610 ticks) and runtime sectors (726/2434).
  This is full cold playback evidence for these two scopes, not evidence for
  the other disks or actual preceding-EOF continuation.
- No new decoder instructions were introduced in this follow-up. Existing
  completed-input branches cost +0 T per token/long16 and -2 T per long8
  versus the original decoder; available-prefix guards still cost 96 T per
  header and 135 T per long literal including CALL. These deterministic
  instruction costs remain separate from real decoder/paging/IRQ/ULA elapsed
  times in the saved profiles. Prefix checks remain a target during starvation.
- Decision: retain as an unselected experiment; the window improvement does
  not meet full-volume timing. Do not combine it with the rejected read gate
  or publish new root images. Next inspect the token-entry header guard:
  AF is overwritten by token decoding, so a direct guard-to-token branch may
  remove CALL/RET and AF saves. Preliminary available-header count 96 ->46 T
  is a hypothesis requiring independent native, interrupt and full playback
  checks; preserve the zero-overhead complete-input path and current bytes.
- Reproduce with cached `rebuild_cell_player.py --streaming-lzsa2`,
  `verify_cached_cell_player.py`, `measure_fap3_fuse.py --trace-pipeline`,
  `capture_cell_codebook_full.py`, `profile_cell_delivery.py` and
  [archive verifier](toolkit/verify_streaming_bypass_playback.py).
  [Report and evidence](toolkit/streaming_bypass_playback_report.json).

## 2026-10-01: optional track-read admission removes isolated misses but starves the queue

- Objective: prevent the measured background track read from delaying the next
  draw, without changing LZSA2 bytes, AY or pixels. Baseline `d3127c0`, cached
  dictionary-budgeted CB46 [4096,4352), 256 frames, 183997 video bytes,
  719 runtime sectors, 777 occupied sectors, four decoded slots and sector cache.
- Added opt-in `rebuild_cell_player.py --optional-read-gate`. A bank-7 helper
  E340h..E38Ah wraps only the clock's optional queue step. With at least two
  ready slots, it can defer a track-changing physical read near publication;
  decode quanta and available cached input pass through. Required packet
  acquisition and startup prefill retain the existing path.
- The first cold-only prototype read READY before both counters. Inspection
  found a publication race, so the measured variants read READY after both
  counters. Two tests cover 1680 state combinations, counter wrap and simulated
  register-preserving publication updates at every instruction boundary.
  These component injections do not stand in for real AY interrupt timing.
- Deterministic gate cost is 0 ->30..301 T per optional step (delta +30..301),
  depending on its path. The patched CALL remains 17 ->17 T, delta 0. Exact
  measured paths: 30/77/91/104/148/168/205/225/230/244/262/287/301 T, excluding
  unchanged queue work, IRQ/ULA/ROM and physical latency. Decoder and renderer
  machine code are identical; no compressed bytes or sectors are added.
- A four-field admission threshold gives 30 nominal misses, all beyond one
  field, maximum 38 fields and 15 invalid intervals. Runs 224 and 227..255;
  the latter does not recover before EOF. A two-field threshold (only the
  final field deferred) gives 11 misses, all beyond one field, maximum 15,
  seven invalid intervals; run 237..247 recovers at 248. Compare baseline
  nine misses/max6/two bad intervals, recovered at 124 and 245. Both remove
  frame 123's isolated miss but worsen sustained delivery: **reject both**.
- Both measured variants pass dirty cold boot, all 256 native screens with
  memory/cache guards, all 1769472 Fuse screen bytes, 1280 exact AY ticks and
  719 real sectors. No full-volume or continuation run is claimed. The optional
  experiment stays disabled; root disks and generic converter defaults are
  unchanged. Reproduce with [tests](toolkit/test_optional_read_gate.py), cached
  rebuilder, existing native/Fuse verifiers and
  [archive verifier](toolkit/verify_optional_read_gate.py).
  [Report](toolkit/optional_read_gate_report.json) records both failures.
- Next: test the already-built final branch-bypass streaming decoder, whose
  complete-input fast path has no per-token guard overhead. Its earlier
  guarded predecessors failed timing, but the final variant has only component
  and cold evidence. Use its saved window before any full-set rebuild.

## 2026-10-01: full-volume dictionary budgets and delivery profiling

- Objective: validate the encoder-only compression improvement on one full
  disk toward the four-volume goal, retaining per-block byte/CPU budgets,
  exact pixels, AY50 and 10 fps. Baseline commit `3237312`; cached CB46 part 4
  [3744,5066), 1322 frames, 55 LZSA2 blocks, original four-slot/cache player.
- Flat numbering plus the existing short-match CPU fitter reduces video
  623005 ->619749 bytes (2434 ->2421 logical sectors), saving 348712 native
  decoder T-states overall. Six blocks (2/5/17/18/32/33) exceed the original
  byte limits by 9/26/22/16/52/56 bytes. All CPU limits pass. Decision:
  **reject this full-volume candidate**, retain the bounded-window result;
  no candidate TRD was built and no guards were relaxed.
- Completed the original cache player's full native replay and real Fuse
  timing run: 1322 exact native screens, cache/memory guards, 6610 exact AY
  ticks and 2434 exact runtime sectors. The disk occupies 2543/2544 sectors.
  Fuse full-screen-byte capture and continuation were not performed here.
  Timing fails: 29 nominal misses, 28 beyond one field, maximum 23 fields,
  23 invalid actual intervals. Runs 378, 588..599, 603..608 and 617..626 recover
  at 379/600/609/627. This is not a release or evidence for all four disks.
- Full-volume active elapsed time is 468502967 T; physical disk service
  71347152 T, decoder bridge 58784640 T, inclusive draw phases 121154041 T.
  These measured phases include IRQ/ULA effects and can overlap; do not sum
  them as disjoint instruction counts. Packet acquisition has 6552623 T
  empty-queue wait; difficult late runs operate mainly at zero/one ready slot.
- Investigated the previous window's extra isolated miss (local frame 123):
  three ready slots, no packet disk service or empty wait, 136605 elapsed T
  in disk service between publications and 225965 T drawing. Full part 4's
  isolated frame 378 has four ready slots, 156777 disk T and 216445 draw T.
  This separates optional-read admission near publication from sustained
  starvation. Next: test a deadline-aware optional-read gate on the saved
  window without changing compressed bytes, then address burst supply.
- Reproduce with `probe_dictionary_numbering.py --variants flat`,
  `fit_lzsa2_cpu_budget.py`, `verify_cached_cell_player.py`,
  `measure_fap3_fuse.py --trace-pipeline`, `profile_cell_delivery.py` and
  [delivery window analysis](toolkit/analyze_cb46_delivery_windows.py).
  [Verifier](toolkit/verify_full_volume_dictionary_probe.py) and
  [report](toolkit/full_volume_dictionary_report.json) archive the rejected
  candidate, exact inputs, native counts and full baseline trace. Root release
  images and converter defaults remain unchanged.

## 2026-10-01: improve compression without increasing any block's decoder cost

- User priority: better compression at unchanged unpacking cost. Baseline
  `bc615ab`, one cached CB46 [4096,4352) window, 256 frames /16 LZSA2 blocks,
  185681 video bytes, refined colour and original AY50. Reuse raw packets;
  do not re-prepare media or change the player.
- A new distance-only objective minimizes bytes while forbidding slower
  individual tokens/EOF. All 187 exhaustive short layouts /2716 alternatives
  and every native 256-byte decode slice pass. It saves **0 bytes**, 731 T;
  reject as a compression improvement and do not broaden that search.
- Renumbering rows toward their raster bytes alone costs 113 extra bytes,
  saves 39130 T: reject. Also aligning all book entries saves 2113 bytes but
  adds 15250 decoder T: reject under the user's cost constraint. Restricting
  book alignment to uniform cells saves 1770 bytes and 25830 total T, but
  eight blocks are slower. Full native/Fuse screens and AY are exact; this
  intermediate candidate has nine misses, maximum seven fields, four invalid
  intervals. Preserve its evidence instead of claiming unchanged local cost.
- Added `fit_lzsa2_cpu_budget.py`: greedily replace selected two-byte matches
  with literals, accounting for repeat-offset and nibble-phase effects on the
  whole suffix. Independently execute each resulting block on the unchanged
  Z80 decoder; enforce its original payload-byte and decoder-T budgets.
  Removing 167 matches uses 86 bytes of the numbering gain. Final video is
  **183997 bytes (-1684, -0.91%)**, **719 vs726 sectors**; every block is no
  larger and no slower. Native decoder total **15978979 vs16049945 T**
  (-70966, -0.44%); maximum fixed-quota slice **22104 vs22323 T**. Quota
  boundaries may change, so this does not prove every frame's delivery cost.
- The decoder and renderer machine code remain identical. Renderer stage
  counts match on all 255 post-prime frames, **0 T change per frame**. Two
  test methods cover dynamic eviction/replacement, independent volume history,
  unchanged non-index packet bytes and exact short-match cost predictions
  against full reserialization. The numbering harness initially lacked its
  compressor scratch directory; initialization was fixed before measurements.
- Rebuilt the selected window with `--dictionary-probe .../budgeted` and the
  existing shared-AY/four-slot/inline-cell/sector-cache flags. Dirty-RAM cold
  boot, all 256 native frames and all **1769472 Fuse screen bytes** pass;
  all 1280 AY ticks and 719 runtime sectors are exact, with no audio gaps,
  duplicates or underruns. Total occupied sectors **781 ->777**: three extra
  startup sectors offset part of the seven-sector video saving. TRD physical
  file size remains the standard 655360 bytes.
- Timing remains incomplete for release: **nine nominal misses**, all beyond
  one field, maximum six fields, two invalid intervals. Local late runs
  123..123 and 237..244 recover at 124 and 245. Baseline has eight misses,
  maximum 7/8 fields, four bad intervals. The new isolated miss is not hidden
  by improved aggregate CPU, maximum lateness or interval counts.
- Decision: retain this encoder-only method as a measured compression gain,
  with strict per-block byte/CPU budgets; keep generic defaults and root
  images unchanged pending complete-volume physical timing/continuation.
  [Numbering probe](toolkit/probe_dictionary_numbering.py),
  [budget fitter](toolkit/fit_lzsa2_cpu_budget.py),
  [verifier](toolkit/verify_same_cost_compression.py),
  [reports, exact streams and LFS diagnostic images](toolkit/same_cost_compression_report.json).

## 2026-10-01: guarded LZSA2 sector prefixes, parked after compression priority

- Objective/input: reduce the CB46 input stall using the unchanged 256-frame
  [4096,4352) stream, 185681 video bytes, shared AY and four decoded slots.
  Baseline `bc615ab` uses a compressed-sector cache; complete Fuse runs had
  eight nominal misses, maximum eight/seven fields, four invalid intervals.
- Added opt-in `rebuild_cell_player.py --streaming-lzsa2`, a guarded LZSA2
  coroutine and explicit input-wait/EOF queue states. Guard whole literal
  runs, preserve AF', and save shared-sector carry before final decoding.
  The first component implementation failed when called again after early
  EOF; a finished check fixed that. The failure log is archived.
- The initial safe guard costs 38125210 vs 21322803 deterministic T across
  40 component blocks and was rejected. Guard 32-byte token prefixes and
  separately check only long literals instead. All 40 producer/component
  cases and 240 independent full-flags replays pass, including six sector
  alignments, synthetic IRQs, caller clobbers and in-place input/output.
- Eager guarded decoding passes all 256 native frames, dirty cold boot,
  1280 real AY ticks, 726 real sectors and Fuse pixel samples. It regresses
  to 27 late frames, all over one field, maximum 40 fields, 19 invalid
  intervals; the last run 229..255 has no recovery inside this window.
  Active decoder elapsed grows 13571059 ->17613460 T; active physical disk
  service stays 16630787 ->16621892 T. These elapsed stage measurements
  include IRQ/ULA; they are separate from deterministic instruction sums.
- A hybrid policy delays prefix decoding while completed blocks remain.
  Same full native/Fuse coverage, but 13 late frames, maximum nine fields,
  six invalid intervals. Runs 180..180 and 240..251 recover at 181 and 252.
  Both variants remain 781 sectors and fail both timing gates.
- Final host-installed branch bypass restores original token and long-16
  branches after complete input (0 T extra), and long-8 branches save 2 T.
  Active input guards cost 96 T per header and 135 T per long literal call.
  All 40 components total 25878233 vs 21322803 T (+4555430); these deliberately
  stream every block, not the hybrid playback schedule. The final variant
  passes dirty cold boot at 781 sectors; its full native/Fuse playback is
  **not verified**. Prefix/helper ends at 7D4Fh, hot core at 8E72h.
- Decision: keep a reproducible opt-in experiment, not a release or default.
  The user redirected work to improving compression at the same decoding
  cost. Pause decoder experiments and optimize encoder decisions instead.
  Default decoder bytes, all media bytes and root TRDs are unchanged.
  [Verifier](toolkit/verify_streaming_lzsa2.py),
  [component test](toolkit/test_streaming_lzsa2.py),
  [saved reports and LFS diagnostic images](toolkit/streaming_lzsa2_report.json).

**Latest refined A/V preview (2026-10-01):** root LFS
`ZX-video-refined_part01..15.trd`, 5066 frames at 10 fps and new AY50 sound.
Complete cold and predecessor-EOF playback pass the one-field fallback:
four isolated late frames per full run, all recovered on the next frame.
Full screens and sound are exact. This is not a zero-late release; the user
authorized extra disks to retain the new picture, sound and 10 fps.

**Verified zero-late compatibility set (2026-09-30):** root LFS
`ZX-video-five-level_part01..03.trd`, the full 4221-frame authorized edit,
five brightness levels and unchanged AY50. All three disks pass full Fuse
playback at 25/3 fps with zero missed deadlines, exact full screens and AY.
Independent boots and predecessor-EOF snapshot continuations pass. Generic
CB41 conversion was integrated on 2026-10-01; see the latest entry and evidence.

**Earlier release:** `69754f3`, 14 TRDs, the complete 4971-frame movie,
AY at 50 Hz and video at 25/3 fps. The target is at most three disks, with
only subtle pixel changes allowed. On September 19 the user authorized
removing final credits while preserving the post-credit scene. Video jitter
of up to 20 ms with compensation on subsequent frames was also authorized;
AY remains at 50 Hz. The priority is an exact 120-ms frame schedule; the
20-ms allowance is only a fallback. The earlier 14-disk set retains the
credits and does not meet the new target. The separate experimental
`ZX-video-optimized-preview_part01..04.trd` set from September 21 reaches EOF
but fails timing. On September 24 a separate set of **three independently
bootable TRDs** was built and played through all volumes. Capacity was
achieved; video/AY timing failed. It did not replace the earlier root release.

Current documentation and new entries are maintained in English. Dated
historical entries below retain their original text and measurements.

## 2026-10-01 — prefetch compressed sectors while decoded slots are full

- Objective: reduce the remaining whole-block input stall with unchanged
  CB46/LZSA2 bytes, refined pixels, AY50 and 10 fps. Baseline `dd71448`; reuse
  the complete [4096,4352) window and cached full part 4 for cold capacity.
- Audit bank 7 E300h..FFFFh over all 256 native frames: no runtime access.
  Add opt-in `rebuild_cell_player.py --sector-cache`, requiring four-slot
  CB46. Use E400h..FFFFh for 28 compressed sectors (7168 bytes), E300h for
  a 54-byte prefetch routine, and B900h for an 84-byte fixed helper/state.
  Reject collisions with resident AY. Cache state is initialized by the
  ordinary independent bootstrap; unread cache data may remain dirty.
- When all decoded slots are full, queue service can acquire another sector.
  The consumer copies a cached sector through BC00 to its original input
  address. Physical reads share the existing cursor/remaining count, so
  no sector is reordered or read twice. The decoder and renderer do not
  change. This deliberately adds copying to move physical I/O earlier.
- Two test methods pass, including 100-sector FIFO/full/empty/EOF scenarios,
  wraparound and independent full-flags Z80 checks of cache hits. Native
  guards prohibit reading unfilled cache entries, overwriting occupied entries,
  executing cached data, or writing bank 6. Complete window playback passes.
  The first test expected the EOF idle path to cost 88 T; instruction summation
  and emulation both give 78 T. Correct the expectation only; archive that failure.
- CPU costs: miss adds 27 T; cached header 4718 T, cached body 8991 T, each
  +4 on index wrap. These include existing copy/page bodies. Prefetch adds
  219 T around the existing physical-read body (+4 on wrap). Full-cache idle
  14 ->44 T; EOF idle 14 ->78 T. Exclude outer caller, IRQ, ULA and physical
  read/ROM time. These are scheduling gains, not a reduction of total CPU work.
- Full cold/Fuse checks preserve 1769472 screen bytes, 1280 AY ticks and all
  726 runtime sectors. Window size 780 ->781 sectors. Nominal misses 13 ->8,
  all beyond one field; maximum 17 ->8 fields, bad intervals 7 ->4. The sole
  late run 237..244 recovers at 245. A second complete run with additional
  cache tracing also has eight misses and four bad intervals, maximum seven
  fields; retain both measurements. Both timing gates still fail.
- The second trace verifies 112 enqueues and 112 dequeues, four read/write
  cursor wraps, and zero final occupancy. Queue-empty packet entries fall
  22 ->14; longest empty wait 1.38M ->0.81M T. Actual cached part 4 still fits
  **2543/2544 sectors** and independently cold-boots; revised full-part playback
  is not verified. No root images are replaced.
- Decision: retain the opt-in prefetcher. The remaining stall precedes
  block 14, whose compressed input is 12492 bytes, larger than the 7168-byte
  cache; its last sectors still block all decoding. Next evaluate guarded
  incremental LZSA2 input with the existing sector-streaming queue pattern,
  preserving bytes and in-place overlap proofs. Avoid full-set recoding.
  [Implementation](toolkit/compressed_sector_cache.py),
  [tests](toolkit/test_compressed_sector_cache.py),
  [verifier](toolkit/verify_sector_cache.py), [report](toolkit/sector_cache_report.json),
  [archive check](toolkit/sector_cache_archive_check.json).

## 2026-10-01 — inline cell drawing halves the remaining window misses

- Objective: reduce rendering cost without changing CB46/LZSA2/AY bytes or
  disk capacity. Baseline `d4e878c`; reuse the exact [4096,4352) difficult
  window and the cached fourth volume, preserving refined pixels and 10 fps.
- Add opt-in `rebuild_cell_player.py --inline-cells`. Emit the eight bitmap
  bit handlers directly: replace taken `CALL C` plus `RET` (17+10 T) with
  `JP NC` (10 T), saving **17 T per changed cell**. Unchanged-cell dispatch
  remains 10 T; mode refills, row table, attributes and payload stay identical.
  Dispatch-inclusive no-refill costs: book 305 ->288, literal 334 ->317,
  front 316 ->299, partial 203 ->186 T. Exclude IRQ, ULA, outer service and disk.
- Renderer code grows 424 ->1340 bytes, placed at 8E80h..93BFh (exclusive).
  Its state follows the code; screen state ends at 93C1h, before 9400h audio
  allocation. The preceding LZSA2 core ends at 8E6Eh. Guard the extra
  8E80h..9000h region over the complete old 256-frame native window before use;
  no accesses occur. Existing generator defaults reproduce the old metadata.
- Four test methods pass, including 28 new independent full-flags sparse/dense
  cases, both screens, all modes and IRQ preservation. Complete guarded native
  replay preserves every screen, bank 6 and other allocations. Every one of
  the 255 post-prime kernel deltas equals `-17*changed_cells`; mean kernel
  120828.65 ->115969.25 T (-4.02%). Complete draw mean 121326.16 ->116466.76 T.
- Complete cold/Fuse verification retains all 1769472 screen bytes, 1280 AY
  ticks and 726 runtime sectors. Window size remains **780 sectors**. Nominal
  misses **31 ->13**, beyond-one-field misses **29 ->13**, maximum **28 ->17
  fields**, invalid actual intervals **12 ->7**. Only local run 237..249
  remains late, recovered at 250. Both timing gates still fail.
- The native startup of cached full part 4 still fits **2543/2544 sectors**
  and cold-boots exactly; full playback of that revised volume was not run.
  Trace of the window shows 22 empty-queue entries (previously 30), draw
  elapsed 31.79M T, disk service 17.38M, decode bridge 13.55M. Active elapsed
  remains about 90.66M T because both runs regain the original deadline at
  the end; these stage intervals must not be summed with overlapping packet work.
- Decision: retain the opt-in optimization; continue on the cached window
  to remove the remaining input stall. No root release change or four-disk
  timing/continuation claim. [Cycle/layout notes](toolkit/CB44_DYNAMIC.md),
  [tests](toolkit/test_inline_cells.py), [verifier](toolkit/verify_inline_cells.py),
  [report](toolkit/inline_cells_report.json),
  [archive check](toolkit/inline_cells_archive_check.json).

## 2026-10-01 — fixed AY overflow enables four buffers on the last volume

- Objective: let the selected fourth volume use all four video slots while
  keeping exact refined pixels, square-aware AY50, 10 fps and the existing
  [0,1312,2672,3744,5066] cuts. Baseline `13879a8`; cached CB46/LZSA2 and AYB1
  inputs, no movie preparation or full candidate-set sweep.
- Guard B700h..BA00h against native accesses across the complete 256-frame
  window, then allocate the 1170-byte fourth-volume AY overflow after its
  fixed forest at B398h..B82Ah. First 16384 coded bytes remain in bank 6;
  video banks 0/1/3/4 retain 63488 decoded bytes. Reject allocation overflow.
  The AY wire format, video blocks and rendering instructions stay identical.
- Twenty tests pass, including independent full-flags cycle comparisons and
  IRQ injection across the pointer boundary. All 6610 native AY records and
  chip updates are exact. Ordinary payload reads stay 65 T; first wrap
  251 ->74 (-177), final byte 92 ->65 (-27), bridge 442 ->436 (-6/refill),
  init 1076 ->1056 (-20). Total fill 20308726 ->20307238 T (-1488); consumer
  remains 4088727 T. These CPU counts exclude IRQ/ULA/ROM/physical disk.
- Build only cached part 4: **2543/2544 sectors**, unchanged capacity, dirty-RAM
  cold boot passes. Full Fuse checks preserve all 1322 screens (9137664 bytes),
  6610 AY ticks and 2434 runtime sectors, with no audio gaps, duplicates or
  underruns. There are 60 nominal misses, 57 beyond one field, maximum 42
  fields, 34 invalid intervals. All five late runs recover, the longest at
  local frame 633. Both nominal and fallback gates fail.
- Decision: retain the fixed allocation as a prerequisite for the four-slot
  last disk. It is not a released four-disk set; root images are unchanged.
  Reuse the complete trace to address producer starvation and rendering cost.
  Guarded native playback checks all 1322 frames and prevents runtime writes
  to bank 6 or the fixed payload. The trace records 70 empty-queue packet
  entries: active elapsed 468.51M T, drawing 125.55M, disk service 72.02M,
  decoder bridges 58.65M. Packet stages overlap those and are not additive.
  Full-set timing and actual predecessor-EOF continuation remain required.
  [Implementation and cycle calculation](toolkit/CB44_DYNAMIC.md),
  [capacity/rebuild tool](toolkit/measure_shared_audio_capacity.py),
  [verifier](toolkit/verify_fixed_audio_tail.py),
  [report](toolkit/fixed_audio_tail_report.json),
  [archive check](toolkit/fixed_audio_tail_archive_check.json).

## 2026-10-01 — exact partial-row cells fit the selected four-volume capacity

- Objective: remove the remaining 21504-byte total excess and reduce work
  on literal cells. Baseline `a6a2081`, same refined five-level pixels,
  original square-aware AY50, 10 fps and [0,1312,2672,3744,5066] cuts.
  Inspecting startup sections showed that frame-payload changes offered
  a broader saving than altering only the independent screen histories.
- Add CB46: retain CB44 modes 0..2, and use mode 3 for one changed row-pair
  of a literal cell. Store row 0..3 plus its mutable row-table index instead
  of four indices. Preserve the other three pairs in the actual back
  screen. Static book, attributes, row replacements and outer LZSA2 format
  stay unchanged. The builder validates selectors and complete extents.
- Reuse three cached 256-frame windows at 0/2560/4096. Compressed sizes
  121912/127989/188005 -> 117701/124058/185681 bytes: 10466 saved (2.39%).
  All 768 host screens are exact. Encode only the existing full partition:
  608061/604926/626506/623005 video bytes, saving 59832 bytes, with all 5066
  host screens exact. No image resampling, sound changes or candidate-set sweep.
- Actual complete startup/video sizes with shared AY and three video slots
  are **2464/2475/2542/2543 sectors**, all <=2544. Every candidate passes
  dirty-RAM cold loading. Total 10024 leaves 152 sectors across four disks.
  Capacity images were built and checked in memory; no root set is published.
- Fifteen regression tests pass, including 32 independent full-flags native
  cases on both screens and IRQ tests. No-refill cell costs: book 281 ->288
  T, full literal 317 ->317, front 299 ->299, partial 317 ->186 (-131).
  Whole-renderer delta is exactly `7*book_cells - 131*partial_cells` T.
  The first test caught a 10-T arithmetic error in the expected partial
  cost (196 instead of 186); machine code was unchanged, failure archived.
- Full four-slot [4096,4352) native/cold/Fuse replay verifies 1769472 screen
  bytes, 1280 AY ticks and 726 runtime sectors, with no writes to AY bank 6.
  Diagnostic size 793 ->780 sectors. Renderer-only deltas match the formula
  on all 255 separately measured draws. An initial whole-wrapper assertion
  caught 124 T of changed disk-service work near EOF; count that separately,
  rather than attributing it to rendering or weakening the exact formula.
- Timing: 37 ->31 nominal misses, 36 ->29 beyond one field, maximum
  43 ->28 fields, 12 invalid intervals. All late runs recover, last at
  local frame 254. Mean complete draw call 122715.74 ->121326.16 T; 39
  frames are slower because their book-cell surcharge exceeds partial-cell
  savings. Both timing gates still fail. Keep this measured size/aggregate
  improvement; do not label it a zero-late release.
- Reproduce with [window probe](toolkit/probe_partial_row_cells.py),
  [selected partition](toolkit/measure_partial_row_four.py), cached rebuild
  `--cell-probe FILE.json`, and [verifier](toolkit/verify_partial_row_cells.py).
  [Complete evidence](toolkit/partial_row_report.json). Generic CLI selection,
  fourth-slot allocation for part 4's 1170-byte audio tail, complete movie
  timing and actual EOF continuation remain outstanding.

## 2026-10-01 — reclaim a fourth video slot with bank-6 AY

- Objective: address measured empty-queue stalls. Baseline `5751e6e`, same
  complete 256-frame [4096,4352) window and exact raw/LZSA2/AY streams.
  `--shared-audio --four-video-slots` places a one-bank AY payload in bank 6
  and restores the original video map [0,1,3,4]. Reject spanning audio.
  This avoids changing slot paging, block layout or compressed data.
- Decoded capacity increases 47616 -> 63488 bytes. Restore two admission
  checks (7 -> 7 T) and two cursor sites (39/47 -> 11 T, -28/-36 T per
  execution). Loading the constant AY bank changes 14h -> 16h at 7 T;
  decoder, IRQ consumer, drawing and packet instructions stay unchanged.
  Old component metadata remains historical; `four_video_slots.patches`
  and the final queue listing describe installed instructions.
- Eighteen tests pass, including independent full-flags Z80 verification
  that AY relocation has exactly zero CPU-cycle delta, and rejection of
  audio that would overlap bank 4. Complete cold/Fuse replay verifies all
  1769472 screen bytes, 1280 AY records and 735 runtime sectors.
- Timing improves 108 -> 37 nominal misses, 108 -> 36 beyond one field,
  maximum 82 -> 43 fields; 15 actual intervals remain invalid. Image size
  stays 793 sectors. Both timing gates still fail; keep root releases.
- Full pipeline trace sees an empty queue at 41/256 packet entries, down
  from the earlier three-slot pre-shared-audio profile's 115/256. Within
  91.66M active elapsed T, drawing uses 33.37M, disk service 17.92M and
  decode bridges 14.37M. These elapsed values include IRQ/ULA/ROM effects
  and overlap packet intervals; do not add the packet total again.
- The initial integrated CPU build predated the explicit immutable-AY-bank
  guard. Re-run the complete native window with that guard in the verifier;
  keep both CPU reports. Generic conversion and full-movie timing/actual
  continuation for this opt-in layout remain outstanding. Selected part 4
  still requires an audio-tail allocation before it can use four slots.
  [Report/evidence](toolkit/four_video_slots_report.json),
  [reproducer/verifier](toolkit/verify_four_video_slots.py).

## 2026-10-01 — shared fixed-RAM AY model, exact four-volume capacity

- Objective: reclaim bank 6 and reduce duplicated sound tables for the
  four-disk goal. Baseline `9893f79`; reuse the exact cached CB44 video,
  refined AY and selected cuts [0,1312,2672,3744,5066], without re-preparing
  frames or encoding alternative whole-disk candidates.
- Implement an opt-in fixed-RAM Huffman decoder/forest and one exact AYH1
  model per volume. Additional B100h..B700h storage passes guarded native
  replay of all 256 real-window frames with zero reads/writes/fetches before
  reuse. Actual fixed storage is 3860/3940/3932/4053 bytes. Payloads occupy
  bank 4; part 4 alone needs a 1170-byte tail in bank 6. The video queue
  still has three slots; freed bank space is not yet a throughput gain.
- Seventeen tests pass, including independent full-flags Z80 execution,
  every forced payload boundary and instruction-by-instruction IRQ stress.
  Initial tests caught missing SCF emulation, a stress-run instruction guard
  and an incorrect unbounded expectation for the 16-bit IRQ clock. Add the
  exact opcode model, use single-record batches for stress, and compare the
  counter modulo 65536. Preserve the final failed clock run in the evidence.
- Every one of the 25330 original AY ticks passes native decoding and chip
  comparison. Total fill cost increases 69212242 -> 70408859 T (+1196617),
  excluding real IRQ/ULA/ROM/disk. The shared model saves storage, not CPU.
  A normal payload-byte refill is 37 -> 65 T when spanning is enabled;
  the first bank switch costs 251 T and final wrap 92 T. See the exact
  bridge/init accounting in [CB44_DYNAMIC.md](toolkit/CB44_DYNAMIC.md).
- Complete real [4096,4352) cold/Fuse playback verifies 1769472 screen bytes,
  1280 AY ticks and all 735 runtime sectors. Diagnostic size 796 -> 793
  sectors. Timing still fails: 108 nominal misses, all beyond one field,
  maximum 82 fields, no AY underruns. This is not a release or timing pass.
- Actual complete startup/video capacity is **2543/2541/2588/2588** sectors,
  versus 2544 per TRD. Parts 1 and 2 also pass dirty-RAM cold loading.
  Total 10260 exceeds 10176 by 84 sectors (21504 bytes). Parts 3/4 do not
  fit, and changing cuts alone cannot eliminate this total excess.
- Keep this measured opt-in implementation for further development; root
  images are unchanged. Full-movie timing, native integrated bank-6 tail
  playback and actual EOF continuation remain unverified for this layout.
  Reproduce with [cached rebuild](toolkit/rebuild_cell_player.py),
  [native AY benchmark](toolkit/benchmark_fixed_resident_audio.py) and
  [capacity measurement](toolkit/measure_shared_audio_capacity.py).
  [Saved report and evidence](toolkit/shared_audio_report.json).

## 2026-10-01 — retire unused reconstruction and measure shared AY tables

- Objective: reduce startup storage and reclaim fixed RAM for the four-disk
  goal. Baseline `e747b02`; same 256-frame [4096,4352) video, original AY,
  plus a two-volume six-frame fixture for independent boot/continuation.
- CB44 retires 8000h..8D74h (3444 bytes). Derive the end from the actual
  LZSA2 core origin; the earlier 8DF2h planning value was not this build's
  address. Active native/packet/clock instructions are identical: 0 T delta,
  confirmed on all 255 separately called real frame draws. A guarded CPU
  rejects any access/fetch in the freed range; all 268 frames pass.
- Full Fuse cold playback confirms 1852416 screen bytes and 1340 AY ticks.
  The fixture also passes actual predecessor-EOF continuation with poisoned
  unrelated RAM and zero late frames/AY gaps. Physical drive swaps remain
  untested. The real window has 113 misses, 110 beyond one field, maximum
  82 fields, 51 invalid intervals and no AY underruns. Disk alignment
  changed; this is not a runtime speedup or timing pass.
- Diagnostic capacity 798 -> 796 sectors. First full selected volume needs
  2556 / 2544, 12 sectors over capacity (previous pre-mask candidate 2558).
  Video and AY streams remain byte-identical. Keep root images unchanged.
- Add cached player-only rebuilding to avoid repeating preparation and
  compression. Generalize continuation input to the converter manifest;
  the movie-specific publication wrapper initially rejected fixture metadata
  for missing `ay_ticks`, before any continuation run. No metadata was
  invented; direct generic continuation then completed successfully.
- Next-step host probe checks all 25330 original AY ticks with one global
  model per selected volume. Trees+payload: 83674 -> 74373 bytes before
  startup compression. Payloads 14137/16118/12516/17554 bytes; only part 4
  overflows one bank by 1170. Trees plus a reserved 512-byte decoder require
  3946/4026/4018/4106 fixed bytes, exceeding the newly freed interval alone.
  Audit the B100h..B700h gap and implement a fixed decoder before claiming
  bank 6 as another video slot. Native size, paging and throughput unverified.
- Decision: retain guarded retirement; develop shared fixed audio/extra
  video buffering next, preserving quality and cadence. [Rebuilding](toolkit/rebuild_cell_player.py),
  [audio sizing](toolkit/probe_shared_resident_audio.py),
  [verification/archive](toolkit/verify_retired_cell_code.py),
  [complete evidence](toolkit/retired_cell_report.json).

## 2026-10-01 — skip empty masks and inline CB44 attribute writes

- Objective: reduce the measured drawing cost from `0bb033f`, retaining
  exact video/AY data. Empty bitmap groups cost 144 -> 39 T; empty attribute
  groups 160 -> 51 T (50 with E wrap). Nonempty bitmap groups add 14 T;
  a nonempty attribute group with k changes costs 160+45k -> 190+23k T.
  The full frame formula is saved in [CB44 documentation](toolkit/CB44_DYNAMIC.md).
- Ten tests pass, including 24 independently replayed component cases over
  every mask byte value, both screens, full flags and IRQ preservation.
  The same real [4096,4352) window has byte-identical raw/compressed video
  and AY. All 255 separately called frame draws match their calculated
  delta: average 128487 -> 122716 T (-4.49%), worst 232322 -> 227162 T.
  Frame zero is bootstrap-primed and has formula-only separate accounting.
- Code grows 348 -> 405 bytes. The diagnostic disk uses 797 -> 798 sectors;
  the 188005-byte video still uses 735. An initial comparison incorrectly
  expected unchanged packet CPU costs; the extra startup sector shifts
  track/side boundaries. Report those measured differences separately
  (-434 T total), without crediting them to the renderer.
- Complete cold native/Fuse playback preserves 1769472 screen bytes, 1280
  AY ticks and all sectors. Timing improves to 110 nominal misses, 108 over
  one field and maximum 82 fields (baseline 116 misses / maximum 89).
  Fifty intervals remain invalid; no AY underruns. Both timing gates fail.
- Decision: retain this bounded rendering improvement automatically for
  CB44; keep CB41/42 defaults unchanged. Do not call it a four-disk release
  or replace root images. No full-volume capacity claim after code growth.
  [Exact comparison script](toolkit/compare_fast_cell_masks.py),
  [tests](toolkit/test_fast_cell_masks.py),
  [full evidence](toolkit/front_fast_masks_report.json).

## 2026-10-01 — native CB44 preserves pixels but fails sustained delivery

- Objective: integrate the selected exact front-cell reuse after `3bb7aa9`
  without changing image or AY data. CB44 adds two-bit native modes to CB42
  dynamic rows; unsupported neighbour mode 3 is rejected. Generic/prepared
  converters expose front reuse, dynamic rows and one/two resident AY banks.
- Book/literal cells change from 268/304 to 281/317 T; front cells cost
  299 T, excluding caller/refill. Setup saves 16 T; mode refill is every four
  cells instead of eight. The complete counted delta and 20 boundary cases
  are saved with the report. Twenty-eight tests pass, including independent
  full-flags/IRQ replay, old formats and guarded accesses.
- Synthetic 12-frame native/Fuse playback is exact and zero-late. Complete
  real [4096,4352) playback preserves 1769472 screen bytes, 1280 AY records
  and 735 sectors, but misses 116 nominal deadlines: 115 exceed one field,
  maximum 89 fields, 54 invalid intervals. No AY underruns. Reject as a
  release. An initial cut list failed the two-bank audio limit before TRD
  generation; corrected cuts retain the real preceding screen histories.
- Complete native first-volume capacity at cuts [0,1312,2672,3744,5066]
  is 2558 sectors / 2544 maximum: 2456 video and 102 startup/audio. This
  failed build emitted no image. Root images remain the previous set.
- Extend read-only Fuse tracing for cell-player packet/draw/decode calls;
  the old tracer expected retired reconstruction calls and initially stopped
  before emulator launch. Additional complete tracing reports 117 misses,
  same 89-field maximum, exact AY and pixels sampled against reference.
  Do not replace the original full-screen run's result with this separate
  bootstrap/rotation phase. Of 95.017M active elapsed T, drawing takes
  35.103M, disk service 19.159M and decoder bridge slices 15.205M. Packet
  intervals overlap disk/decode; residuals include IRQ/ULA/control. They
  are not deterministic CPU measurements. Empty queue at 115/256 entries.
- Decision: retain the exact optional format, prioritize rendering and
  producer delivery before a final four-disk build. No claim that more
  buffering alone solves throughput. Preserve all failed capacity/timing
  evidence and reproducing scripts. [Implementation and cycle formula](toolkit/CB44_DYNAMIC.md),
  [native/Fuse report](toolkit/front_native_report.json),
  [window verifier](toolkit/verify_player_windows.py),
  [stage profiler](toolkit/profile_cell_delivery.py).

## 2026-10-01 — exact front-screen reuse reduces the selected movie stream

- Objective: reduce repeated payload after the dynamic-cell result in
  `7ea4b4d`. Baseline CB42 compares against the physical back screen two
  frames ago. Host-only CB44 adds two-bit cell modes for literals, book
  indices and exact copies from the immutable previous front screen. All
  picture samples, attributes and AY records stay unchanged.
- Three 256-frame windows at 0/2560/4096: CB42 totals 453253 bytes;
  same-position reuse 438082; neighbour reuse 437973; same-position reuse
  with the static book fitted only to non-reused patterns 437906 (-3.386%).
  All flags, row controls and LZSA2 framing are included. Neighbour copying
  saves only 109 bytes beyond same-position copies, so leave it host-only.
- Additional host-only CB45 XORs attribute bytes with the old back screen.
  It increases all three refitted windows to 123345/129101/190866 bytes,
  totaling 443312. Reject this variant. No native code changed (0 T); no
  proposed native cycle reduction or playback claim is inferred from size.
- Nineteen tests pass, covering settled cells, spatial sources, independent
  two-screen histories, one-frame book fitting, attribute prediction and
  byte-identical old CB42 fixture data. All window screens are host-exact.
- After the bounded result, encode only one full CB44 partition, retaining
  the selected cuts [0,1312,2672,3744,5066]. Exact video sizes:
  628680/622126/637883/633641 bytes, a 74724-byte (2.877%) saving versus
  the full CB42 candidate. Video uses 2456/2431/2492/2476 sectors, 9855
  total. All 5066 screens and every LZSA2 block round-trip exactly; original
  AY streams/sizes are retained. This leaves 321 sectors for all boot/audio.
- Decision: retain same-position reuse and refitted static books as the next
  native candidate. CB44/45 are not accepted by the player or converter yet;
  no new root images were emitted. Four-disk capacity, native T-states,
  complete timing, cold boots and continuations remain unverified. The next
  bounded native/Fuse gate must precede any release build. Further startup
  savings may be available by retiring obsolete reconstruction code; that
  memory/reachability hypothesis has not been implemented or measured.
  [Front reuse](toolkit/front_cell_reuse.py),
  [window comparison](toolkit/probe_front_cell_reuse.py),
  [full selected stream measurement](toolkit/measure_front_four.py),
  [bounded evidence](toolkit/front_cell_report.json),
  [full encoded streams](toolkit/front_four_report.json).

## 2026-10-01 — dynamic whole-cell replacement has insufficient size benefit

- Objective: recover startup/audio space for four disks after the capacity
  failure in `0863674`. Three bounded 256-frame windows start at 0, 2560,
  4096. The refined pixels, 10-fps samples and AY stream are unchanged.
- Host-only CB43 adds cell replacement controls (slot plus eight physical
  bitmap bytes). Choose scene-local cells every 32 or 64 frames only when
  expected literal-byte savings exceed replacement cost plus a 12-byte
  margin. Keep the existing 256-cell/2048-byte book and dynamic row cache.
  Ordinary frame packets retain their CB41/42 layout. Native code is not
  implemented/enabled; existing player instruction delta is 0 T.
- All replacement overhead is included in LZSA2 streams. Static window
  sizes: 127287/135750/190216 bytes. Dynamic32: 127614/135875/191528.
  Dynamic64: 126717/134621/191497. Totals: 453253 / 455017 / 452835 bytes;
  dynamic64 saves only 418 bytes (0.092%), and grows the difficult window.
  Lower raw packet size alone did not translate into useful compression.
- Fifteen tests pass, including replacements across different scenes, both
  physical screen histories and byte-identical old CB42 fixture output.
  All three variants preserve every host-decoded screen. No native update
  timing, disk playback or whole-film capacity claim follows from this probe.
- Decision: preserve the prototype and evidence, keep native CB42. This
  particular update policy does not justify new native complexity for the
  required storage reduction. Next measure front-screen cell reuse in short
  windows; no existing pixel or AY quality should change.
  [Book planner](toolkit/dynamic_cell_dictionary.py),
  [probe](toolkit/probe_dynamic_cell_dictionary.py),
  [tests](toolkit/test_dynamic_cell_dictionary.py),
  [results and exact streams](toolkit/dynamic_cell_report.json).

## 2026-10-01 — four dynamic-row volumes still exceed storage capacity

- Objective: select four refined A/V cuts after removing static-row and
  single-bank AY limits. Baseline `d22f72e`; all 5066 original refined frames
  and 25330 ticks. No quality, cadence or native instruction changes (0 T).
- Extend the converter's window planner with minimax dynamic programming,
  a 16-frame boundary grid and an optional static-row constraint. Existing
  three-volume static planning stays unchanged. Eleven tests pass, including
  an independent exhaustive small-input minimax oracle and two-screen row
  history constraints. No candidate disk sets are built during planning.
- Measure 159 32-frame CB42 windows, choose [0,1312,2672,3744,5066], and
  compress only that full partition. Exact video sizes are
  654636/647466/650028/644924 bytes, or 2558/2530/2540/2520 sectors. The
  10148-sector sum leaves just 28 sectors (7168 bytes) out of four disks'
  10176 sectors for every player, bootstrap and audio segment. The first
  volume's video alone exceeds its 2544-sector limit. No final TRD emitted.
- The four volumes require 11/15/2/6 row replacements. All frames and LZSA2
  blocks decode exactly on the host. AY bank pairs
  [10327,10475], [11040,12135], [10094,8991], [13327,11381] all fit. Host
  checks do not establish actual CPU, boot, disk latency or playback timing.
- Decision: retain reusable planner and exact failure evidence; this selected
  partition fails capacity, not proof that four disks are impossible. Next
  evaluate dynamic whole-cell book replacement on bounded windows, counting
  replacement bytes and CPU as well as literal savings. Root TRDs unchanged.
  [Probe](toolkit/probe_four_dynamic_disks.py),
  [planner tests](toolkit/test_balanced_volumes.py),
  [saved measurements and encoded streams](toolkit/four_dynamic_report.json).

## 2026-10-01 — fit exact resident AY across banks 4 and 6

- Objective: remove the audio RAM obstacle to four refined A/V volumes,
  baseline `0e7b825`. Keep every original AY record, image and 10-fps frame.
  Add optional `--audio-banks 2` to the prepared converter. AYB1 contains two
  independently Huffman-coded segments; the foreground bridge switches at
  the segment boundary without resetting the FIFO, global count or AY state.
  Bank 6 replaces an obsolete entropy table. Video banks 0/1/3 and the two
  physical screens retain their allocations. Both segments load at cold boot.
- All 25330 ticks round-trip exactly. Four equal quarters need native bank
  pairs [9984,10234], [10481,11067], [11784,9975], [13123,10802] bytes.
  Every individual bank fits 16384 bytes. This solves resident memory only;
  it does not establish four-disk capacity or whole-movie playback timing.
- Deterministic old refill bridge: 436 T. New ordinary refill: 486 T (+50),
  one bank-switch refill: 645 T (+209), EOF refill: 516 T (+80). Initialization
  adds 40 T. These exclude the resident decode body and outer service call;
  per-tick decode/AY consumer instructions are unchanged. Generated listings
  and native instruction execution check all counts. IRQ/contention/ROM/disk
  delays are separate and included in actual Fuse playback measurements.
- Verification: 33 tests, including FIFO wrap/backpressure, every-instruction
  IRQ injection through the boundary, preserved caller registers and paging.
  Complete Fuse cold playback of a 12-frame fixture with 369 row replacements
  and real [4216,4280) movie window: 525312 exact screen bytes, 380 exact AY
  ticks, zero missed nominal deadlines, gaps, duplicates or underruns.
  Previous frame histories are preserved. This remains a bounded test.
- Two intermediate placements failed integration: 7823h conflicted with the
  later in-place producer; DB80h was paged out during audio execution. Both
  failed reports are archived. The accepted helper uses checked fixed RAM
  at 78A0h, below the old 7900h wrapper; a new guard rejects pageable placement.
- Decision: retain this optional allocation for the four-volume experiment.
  Root release/preview disks and one-bank defaults are unchanged. Next choose
  four cuts using short-window costs and measure capacity and complete timing.
  [Encoder/native helpers](toolkit/banked_resident_audio.py),
  [tests](toolkit/test_banked_resident_audio.py),
  [verification/archive script](toolkit/verify_banked_resident_audio.py),
  [saved report and reproduction inputs](toolkit/banked_audio_report.json).

## 2026-10-01 — reject period-byte prediction as a sufficient audio-bank fix

- Objective: remove the independent 16-KiB AY bank obstacle to four refined
  A/V disks. Baseline `85f3527`; all 25330 original refined ticks, equal video
  quarters [0,1266,2533,3800,5066]. No audio, image or cadence changes.
- A host-only AYD1 prototype codes modulo-256 differences for frequency low
  registers 0/2/4, leaving masks and other registers unchanged. It uses the
  existing context Huffman coder after prediction. All four independent
  initial states and every original tick record round-trip exactly.
- Baseline native resident sizes: 17489/18632/19202/21012 bytes. Predicted
  sizes with a conservative extra 256-byte code/alignment reserve:
  16639/17689/18611/20468 bytes. These are host estimates; no native predictor
  was implemented or timed. Even the sum without that reserve exceeds four
  16-KiB banks, so this does not solve the present allocation problem.
- Keep the probe and exact coded evidence; do not change the player/audio
  default for this insufficient saving. Native instruction delta is 0 T.
  Next use currently unused bank 6 for a second resident audio segment and
  preserve the exact original AY records. Four-disk capacity and complete
  timing remain open. [Probe](toolkit/probe_ay_period_delta.py),
  [host prototype](toolkit/ay_period_delta.py),
  [saved comparison and payloads](toolkit/ay_period_delta_probe/report.json).

## 2026-10-01 — dynamically replace row dictionary entries during playback

- User rejected 15 disks and requested at most four, then explicitly requested
  row eviction/replacement during playback. Baseline `1d59d25`, unchanged
  full refined A/V preparation. Keep the full edit, image and AY50 at 10 fps.
- Added CB42: retain the 256-slot, 512-byte row cache and physical cell book,
  and send lossless `(index, top byte, bottom byte)` replacement batches before
  frame packets. The host evicts the farthest future literal-row use while
  preserving every row needed by the current frame. Index zero stays black.
  Existing physical screen histories need no rewrite or copy when a row is
  evicted. The renderer and ordinary CB41 frame payload are unchanged.
- Z80 accounting: normal packet dispatch +18 T (BIT 7,H: 8 T; JP NZ: 10 T),
  renderer +0 T. A row control handler costs `207 + 74*N` T, excluding queue
  body, dispatch, length read, IRQs, contention and disk latency. Native
  execution of eight batches / 369 replacements measures exactly 28962 T,
  agreeing with that formula. Packet code/state grow 102 -> 166 bytes
  (+63 code, +1 state), inside the existing allocation. No extra row-table
  RAM or screen copy is introduced.
- Fifteen unit/regression tests pass. A 12-frame synthetic fixture uses more
  than 256 literal rows over time, exercises real eviction/reuse, and passes
  CPU execution plus complete Fuse screens/AY. A bounded real [4216,4280)
  window retains both actual predecessor screens, all 64 images and 320 AY
  ticks. Across the two complete Fuse runs, all 525312 screen bytes and 380 AY
  ticks match, with zero nominal misses or underruns. Independent cold boots
  pass. These are component/window checks, not the full four-disk release.
- Bounded lossless compression comparison: 62916 -> 63118 bytes (+202 / 0.32%)
  including each full cell book, exact LZSA2 round trips and safe in-place
  layouts. This real window needs no replacement after initial cache load;
  the synthetic fixture supplies the 369-replacement timing/IRQ coverage.
- The initial complete-capture attempt stopped at the reference hash gate:
  inherited volume metadata overwrote the five-level reference hash with
  the build-only compact placeholder hash. Fix the final metadata assignment,
  preserve both original metadata files, and complete the checks using the
  unchanged images and correct independent references. No timing or pixel
  comparison was weakened. A fresh native build produces the identical
  verified TRD and the correct reference hash without metadata repair.
  [Verification and evidence](toolkit/dynamic_rows_report.json),
  [encoder](toolkit/dynamic_row_dictionary.py),
  [probe](toolkit/probe_dynamic_rows.py), [verifier](toolkit/verify_dynamic_rows.py).
- Four equal parts still need 17489/18632/19202/21012 bytes for resident AY,
  beyond the current 16-KiB allocation. Their whole-part row counts are
  267/271/258/261, now representable through replacement. Adopt the dynamic
  row mechanism for the four-disk effort. Next test lossless prediction of
  refined period bytes to remove the independent audio-memory constraint;
  then measure one selected four-volume stream and complete full playback.
  Root disks remain the previous verified preview until that gate passes.

## 2026-10-01 — publish the complete refined colour/AY50 preview on 15 disks

- User-authorized deliverable: new colour/grain and square-aware sound,
  unchanged resolution, 10 fps, additional independently bootable disks
  permitted. Publish root `ZX-video-refined_part01..15.trd` through Git LFS;
  each image is 655360 bytes. The full authorized edit is 5066 frames /
  25330 AY ticks / 506.6 s. The post-credit scene and source audio EOF remain.
- Reuse preparation from the preceding attempt. Based on its failed timing
  regions and the passing bounded probe, select exclusive frame ends
  `1158,1957,2753,3584,3672,3710,3902,4216,4280,4344,4408,4472,4680,4893,5066`.
  The final set uses 11088 sectors in total. Several parts are deliberately
  short so their data can be loaded before playback. Fifteen disks is a
  measured working partition, not a minimum-size result. No further image,
  audio or frame-rate reduction was made to repair timing.
- Full cold Fuse verification: all 35016192 screen bytes, 25330 AY updates
  and 10126 runtime sector reads match. All 15 dirty-RAM independent boots
  and 14 next-disk/wrong-disk/wrong-series/bootstrap checks pass. Separate
  sequential tests carry actual predecessor EOF RAM through all 14 changes;
  every volume reaches EOF with exact AY and no gaps, duplicates or underruns.
  Screen verification is exhaustive in cold runs; sequential runs additionally
  check native pixel samples and timing. Emulator/controller state restarts
  between snapshot continuations; physical drive swaps are not verified.
- Four nominal misses per full run, identical cold/resumed indices:
  disk 1 frame 1040 -> recovery 1041; disk 3 frame 159 -> 160;
  disk 8 frames 92 -> 93 and 95 -> 96 (zero-based). Each is one field late;
  no accumulated drift or dropped frames. Maximum measured phase is
  70916 T cold / 70915 T resumed; one field is 70908 T, with a few T of
  actual publication instruction variation. Cold publication intervals are
  283622..425457 T, the permitted 4..6-field recovery range with that
  variation. The nominal zero-late gate fails; the authorized one-field
  fallback passes on every complete cold and resumed volume.
- Save as a complete **preview**, preserving the three-disk zero-late
  25/3-fps compatibility set. The image and sound models are those measured
  in the preceding entry; sky colour bands remain visible and no perceptual
  accuracy percentage is claimed. Native hot-path instructions remain
  unchanged from the 10-fps baseline (0 T instruction delta).
- Verification includes 35 relevant unit/regression tests, eight visually
  inspected source/average/physical-dither samples, 544 authenticated final
  artifacts and 268 archived failed-run/probe artifacts. Rechecked every
  archive/raw hash and saved source identity, plus all 39 staged LFS pointers
  for root and archived TRDs. [Final report](toolkit/refined_av_movie_report.json),
  [image samples](toolkit/refined_av_movie_evidence/preview.png),
  [final integrity check](toolkit/refined_av_archive_check.json),
  [attempt integrity check](toolkit/refined_av_attempt_check.json).
- Reproduce from the hashed 10-fps RGB preparation with
  [prepare_refined_av.py](toolkit/prepare_refined_av.py), then
  [build_cb41_cadence_movie.py](toolkit/build_cb41_cadence_movie.py)
  using the ends above with `--volume-cuts`, `--prefix ZX-video-refined`,
  `--verify fuse` and `--verification-timeout 600`.
  [finish_refined_av.py](toolkit/finish_refined_av.py) performs EOF
  continuations, archives the full evidence and publishes only after its
  timing gate; `--allow-fallback` explicitly permits this preview.
  [verify_refined_av_archive.py](toolkit/verify_refined_av_archive.py)
  with `--index` authenticates the saved artifacts and LFS entries.

## 2026-10-01 — full refined A/V preparation and timing-driven disk cuts

- User requested new disks with the joint colour/grain selector and the
  square-aware AY soundtrack, then explicitly authorized extra disks to keep
  these changes and 10 fps. Baseline `2fb8833`; reuse hashed source RGB from
  the completed 10-fps preparation and the authorized no-credits edit.
- Prepared all 5066 frames and 25330 AY50 ticks (506.6 s). Retain the entire
  post-credit scene and original audio EOF; append 120 ms of silence to fill
  the final video slots. Audio uses the generic FFmpeg mono downmix, one
  nominal 3 dB noise attenuation step and +/-50-cent integer-period fitting.
  The new soundtrack intentionally differs from the previous release.
- Full-movie average frame RGB MSE improves 743.069974 -> 692.854994
  (6.76% lower). Every active sample passes the monochrome average/physical
  RGB guards, every cell passes the luma guard, and independent host screen
  expansion agrees. Maximum per-frame row count is 142. This is not a
  perceptual accuracy score; smooth sky colour bands remain visible in the
  inspected difficult samples. Palette history is continuous across disks.
- The initial complete eight-disk Fuse run has exact full screens and AY,
  but 207 missed nominal deadlines. Volumes 4/6/7 violate the one-field
  fallback: 30/153/22 late frames and maximum phase 2694504/7232616/850900 T.
  Volume 6 ends before its late run recovers. Reject that set for publication;
  preserve all evidence instead of hiding the failed attempt.
- A bounded 64-frame probe at global frames [4216,4280), with the planned
  final series identity and both real preceding screens, passes native replay,
  all 442368 Fuse screen bytes, 320 AY ticks and exact nominal deadlines.
  Maximum actual phase is 16 T (instruction-level publication variation).
  This supports finer disk cuts around measured heavy regions; it is not a
  complete-set timing result or a proof of a minimum disk count.
- Added explicit validated cuts and single-volume diagnostic builds. Cuts
  must cover every frame exactly once, include EOF, respect both predictor
  histories, row-table capacity and resident AY memory. A diagnostic volume
  keeps the complete set's identity and is marked as a partial movie.
  Thirty-five relevant unit/regression tests pass. Native renderer/packet
  instructions are unchanged: 0 T instruction delta; the existing 10-fps
  cadence immediate remains `LD DE,5`, 10 T (versus 10 T at `LD DE,6`).
  Fuse disk-call times include ROM, contention, IRQs and emulated latency;
  they are not reported as deterministic decoder CPU costs.
- Reproduction: [preparation](toolkit/prepare_refined_av.py),
  [builder](toolkit/build_cb41_cadence_movie.py),
  [cut tests](toolkit/test_refined_av.py),
  [authenticated failed-run and probe archive](toolkit/refined_av_attempt_report.json).
  The selected complete timing repair is recorded separately after its gate.

## 2026-10-01 — integrate square-aware AY frequency fitting and quieter noise

- User requested slightly less noise, modeling AY's square-wave harmonics,
  flexible accurate frequency selection, and automatic converter integration.
  Baseline `c4a28ec`; generic mono downmix of three eight-second source windows
  at 60/170/430 s, one second of context each side, AY50.
- Rejected an unconstrained volume fit: despite a lower fitting loss, loudness
  correlations dropped to 0.9022/0.8265/0.8917. A subsequent 0.25 dB tone-power
  guard retained dynamics but fixed pitches left the effects-heavy window
  worse spectrally after quieter noise. Both measurement sets are archived.
- Selected joint integer-period/volume search: +/-50 cents by default, two
  coordinate passes, odd 1/h harmonics through 31, <=1 tone-volume step,
  0.001 score hysteresis, one nominal 3.0103 dB noise attenuation step. Preserve
  rests and the existing noise decisions. CLI settings permit noise steps 0/1
  and a tuning radius 0..100 cents. A CLI sine fixture exposed 22 falsely silent
  off-grid ticks in the legacy note analysis; added conservative single-peak
  recovery. Movie-window output is unchanged by that recovery fix.
- Spectral cosine improves 0.8950->0.9084, 0.8676->0.8780, 0.8559->0.8634.
  Chroma and onset proxies improve in all windows; loudness correlation falls
  slightly in two. Noise squared level halves on the same 307/1200 noise ticks.
  These are signal proxies and short-window results, not perceived accuracy.
- AYH1 bytes 2924->5140 (+75.79%). Native instructions/layout unchanged, 0 T
  instruction delta; data-dependent producer/paging/consumer work rises
  3,297,668->4,201,955 T (+904,287 / +27.42%). All 2400 old/new native ticks and
  register values pass with guarded memory and instruction-table checks.
  Initial profiling failed because its formula assumed complete batches;
  adding the explicit 41 T partial-batch EOF path matches measured timing.
- 27 unit/regression tests pass. The actual generic CLI creates a temporary
  independently initialized five-frame/30-tick TRD with complete CPU replay
  and exact screens/AY. No physical delivery/Fuse or full-movie verification;
  root images/prepared movie audio are unchanged. Existing capacity and release
  gates remain mandatory, particularly because audio storage has increased.
- Adopt the host converter change. [Algorithm, limits and reproduction](toolkit/AY_SQUARE_FIT.md),
  [probe script](toolkit/probe_ay_square_fit.py), [native profiler](toolkit/profile_ay_square_fit.py),
  [hashed evidence](toolkit/ay_square_fit_evidence/index.json). Documentation and
  scripts are saved in English as requested.

## 2026-10-01 — jointly select colour and grain against a monochrome reference

- User requested colour plus reselected grain that brings output closer to
  the source. Baseline `756ecd0`; four cached 32-frame windows at movie
  0/704/3392/4288. Search all 56 canonical colour/BRIGHT pairs and five
  per-sample coverages, including normal white, with fixed phase. Guard
  per-sample average RGB and physical RGB error against monochrome; the
  latter assumes each source sample is constant across its 2x2 footprint.
- Initial pointwise luma guard restored little colour in many scenes.
  One targeted follow-up bounds luma error per character cell while keeping
  both pointwise RGB bounds. Objective: RGB + 2*luma + 0.03*pattern variance;
  previous-pair allowance 4/sample, explicit monochrome fallback. Recompute
  density for each tested palette; no contours or global contrast boost.
- All guards pass on 128 frames. Mean RGB MSE: monochrome 1218.566, old
  colour 638.461, joint 584.912 (-52.00% / -8.39%). Luma MSE 372.521 ->
  240.085; physical RGB MSE 12024.326 -> 9605.304. However, cell-boundary
  residual MSE worsens 300.853 -> 493.336 (old colour 466.763). Inspect
  frames 10/714/3402/4298; retain visible-block limitations and both attempts.
- Exact LZSA2 window bytes: monochrome 44018 -> joint 52489 (+19.24%);
  old colour 39467. Row counts 64/105/91/133 fit locally. Native code and
  format unchanged: 0 T instruction delta, book loader 54028 -> 54028 T.
  Output mean 88292.625 -> 93924.086 T (+5631.461 / +6.38%); maxima
  199451 -> 217610 T. Excludes LZSA2/copies/paging/IRQ/ULA/disk latency.
- All 256 native baseline/joint draws, 1769472 screen bytes, timing/guard
  checks, 16 independent-emulator checks and nine tests pass. Save a
  pixel/timeline-checked host GIF, full per-frame metrics and source hashes.
  A final cached rerun only synchronized guarantee documentation/provenance.
- Decision: retain the cell-luma variant as the preferred optional prototype,
  not a default or new TRD. Source-error guards do not ensure perceptual or
  cell-boundary improvement. Next constrain boundary error, then validate
  whole-volume capacity and full playback. Existing root images/AY unchanged.
  [Method, limits and reproduction](toolkit/FAITHFUL_COLOUR.md),
  [evidence index](toolkit/faithful_colour_report.json).

## 2026-10-01 — compare source-derived contours for monochrome objects

- User requested more distinguishable object outlines. Baseline `0cbfa17`;
  reuse three 32-frame windows from the monochrome preview, starting at
  local 0/64/160 (movie 4128/4192/4288). Detect edges in smoothed source RGB
  before grayscale/dither, preserving equal-luma colour boundaries. No
  semantic segmentation, player instruction, format or default change.
- Initial 5x5 sigma-0.9 Canny 60/120, minimum component 6 and full one-shade
  darkening changes 11.25–19.11% of samples. It overtraces foliage and needs
  210/342/282 dictionary rows; two windows exceed 256. The one encodable
  window grows 9563 -> 18810 bytes. Reject and preserve this failed attempt.
- One targeted follow-up: 7x7 sigma-1.4, Canny 100/200, minimum component 12,
  luma reduction capped at 24 before quantization. Mean 2.11% samples change;
  luma MSE 337.197 -> 368.405 (+9.26%). Exact LZSA2 window bytes
  58241 -> 61369 (+5.37%), dictionaries 111/171/140 fit. Inspected three
  static comparisons and saved a decoded-pixel/timing-checked host GIF;
  object recognizability and motion-compensated flicker are not scored.
- All 192 baseline/soft native draws, 1327104 screen bytes and instruction
  timing/guard checks pass; 12 independent-emulator frame checks and eight
  tests pass. Identical native code: 0 T instruction delta, book loader
  54028 -> 54028 T. Data-dependent output mean 113522.833 -> 116020.792 T
  (+2497.958, +2.20%); maxima 203692 -> 204075 T. These exclude LZSA2,
  packet copy, paging, IRQ/ULA and disk latency.
- Decision: retain optional soft prototype and reject strong tracing. No
  new TRD or full-player run; prior root disks are unchanged. Check selected
  whole-volume row capacity and complete playback before disk integration.
  [Method, comparison and reproduction](toolkit/MONOCHROME_CONTOURS.md),
  [evidence index](toolkit/monochrome_contours_report.json),
  [probe](toolkit/probe_monochrome_contours.py).

## 2026-10-01 — build a monochrome comparison disk

- At the user's request, convert the same difficult 10-fps window
  `[4128,4384)` (256 frames / 25.6 s), baseline `1a0c7d0`, to fixed black
  and BRIGHT white. Quantize cached RGB with encoded Rec.709 luma and the
  existing five fixed-phase 2x2 coverages; no contrast stretch. Keep source
  resolution, black bands, progress, frame selection and all 1280 original
  AY ticks. Add explicit `--monochrome` to the prepared-movie builder.
- One selected image: root LFS `ZX-video-monochrome-preview.trd`, 669 used
  sectors / 1875 free, 178 row entries, 159862 video bytes. The colour
  comparison used 618 sectors / 145814 video bytes; grayscale patterns
  cost more despite constant attributes. Do not extrapolate to the movie.
- Complete Fuse checks pass all 1769472 screen bytes, 1280 AY ticks and
  625 runtime sector reads; independent dirty-RAM boot passes. Thirteen
  tests pass and four source/grayscale/rendered samples were inspected.
  Mean grayscale luma MSE 337.807; colour loss is explicitly authorized.
- Exact five-field timing fails on local frames 80 and 115, each one field
  late; recovery on 81 and 116, 4..6-field spacing and no schedule drift.
  Maximum actual OUT deviation 70912 T (one field + 4 T phase); AY remains
  exact with no underruns. The authorized one-field fallback passes.
  Save this as a tested visual preview with disclosed jitter, not a new
  zero-late release. Existing root colour TRDs are unchanged.
- Native renderer/packet listings and cadence metadata match the colour
  window exactly: 0 T instruction delta, `LD DE,5` 10 -> 10 T, codebook
  loading 54028 -> 54028 T. Full measurements include real Fuse TR-DOS,
  emulated disk, IRQ and ULA cost; no physical-drive or full-movie claim.
- [Image, results and reproduction](toolkit/MONOCHROME_PREVIEW.md),
  [authenticated report](toolkit/monochrome_preview_report.json),
  [quantizer](toolkit/monochrome_five_level.py),
  [finalizer and archive gate](toolkit/finalize_monochrome_preview.py).

## 2026-10-01 — diagnose coloured cells and reduced solid black/white coverage

- Baseline `7124c9f`, prepared 10-fps edit; four 32-frame windows starting
  at 0, 704, 3392 and 4288. Reproduced all baseline bytes with original
  four-code palette history. The missing fifth shade shifts endpoint
  thresholds; solid active-image 2x2 black/bright-white coverage changes
  from 9.03/13.59% (four levels) to 7.45/12.78% (five). The old palette
  search also excludes normal white and penalizes attribute changes by
  100000, retaining unsuitable cell colours in some source transitions.
- First tested full five-level palette search, normal white and bounded
  previous-palette retention (64 RGB MSE/component, never worse than the
  baseline cell). Mean RGB MSE 638.461 -> 373.287; compressed window bytes
  39467 -> 46882 (+18.79%). Dark opening colour cast improves, but its
  boundary-residual metric worsens 51.954 -> 93.771. Defer default adoption.
- To address the user's contrast clarification, tested a fixed 12..243
  stretch used only for adjacent-level black/white decisions, alone and
  after palette repair. Endpoint-only solid coverage becomes 11.78/14.41%,
  MSE 665.018 (+4.16%, 115/128 frames worse), bytes 42041 (+6.52%). Some
  shadow detail is lost. Combined result: MSE 410.349, bytes 50693 (+28.44%),
  two frames worse than baseline. Inspect frames 8/710/3398/4318; preserve
  all per-frame measurements and both partially successful alternatives.
- No player/format/AY changes: instruction delta 0 T, book loader
  54028 -> 54028 T. Data-dependent endpoint-only output mean rises from
  84330.070 to 86339.375 T (+2009.305); sample maximum 204903 -> 206222 T.
  All 256 baseline/endpoint native draws and 1769472 screen bytes match;
  every instruction timing/guard passes, plus 16 independent-emulator
  frame checks and 17 unit/regression tests. Fixed a repetition-versus-
  tiling mistake in the initial unit fixture before the passing run.
- Decision: retain reproducible research functions, defer defaults/TRDs.
  Window dictionaries fit, but whole-volume capacity, full LZSA2/I/O timing,
  actual publication, AY and full EOF playback for these candidates are
  unverified. Next consider cell-boundary, temporal and packet-cost terms
  together. No full-movie variants were generated or existing images replaced.
- [Results, limits and reproduction](toolkit/CELL_PALETTE_QUALITY.md),
  [hashed evidence index](toolkit/cell_palette_quality_report.json),
  [probe](toolkit/probe_cell_palette_quality.py),
  [native profile](toolkit/profile_cell_palette_quality.py).

## 2026-10-01 — isolate 10-fps development on its own branch

- At the user's request, moved the two unpublished 10-fps commits
  (`5ae85fc`, `d2d7e1b`) onto `codex/cb41-10fps` and selected that branch
  in the existing checkout. Local `main` returns to `a878583`, retaining
  the verified 25/3-fps implementation and read-only cadence assessment.
- Verified the remote main still points to `d751ce8`; no published history
  was rewritten. All experiment commits, LFS fixtures, preparation caches
  and unrelated untracked files are preserved. No runtime code, stream,
  image or timing result changed; validation consists of branch ancestry,
  references and the working-tree diff. Further 10-fps work belongs on the
  new branch. The movie capacity decision remains unresolved.

## 2026-10-01 — verify a sustained 10-fps window; reject oversized movie partition

- Baseline `5ae85fc`; requested 10 fps with unchanged resolution, five levels
  and original AY. Resampled the source through EOF to **5066 frames**,
  retaining the authorized credit cut and post-credit scene. All 25326 old
  AY states remain byte-exact; four silent ticks complete the final frame.
  Independently checked all host screens (35016192 bytes), audio prefix and
  source identity. Inspected nine sample pictures. Same-palette mean RGB
  error: four levels 834.069, five levels 743.070, no frame worsened; this
  does not measure perceptual fidelity or eliminate 24-to-10-fps judder.
- Sustained window `[4128,4384)`: **256 frames, 1280 AY ticks, 570 real Fuse
  sector reads**, every nominal five-field deadline met, zero audio gaps or
  underruns, all 1769472 screen bytes exact. Actual OUT phase range 0..18 T.
  Dirty cold boot passes. Native kernel/packet listings remain identical;
  deadline operand costs 10 -> 10 T, delta 0. Save the passing window TRD
  with LFS and complete trace/capture evidence.
- Full movie planning used **159 local 32-frame windows**, 26529 cut pairs
  and 424 row-valid candidates. Selected `[0,1808,3408,5066]`; AY banks need
  13117/13611/13756 bytes. No full-image variant sweep. The first actual
  stream is 692152 bytes / 2704 video sectors; startup/audio bring it to
  **2782 sectors**, exceeding 2544 by **238 sectors / 60928 bytes**.
  The builder rejected the volume without emitting a truncated TRD. The
  other volumes were not encoded and full-movie 10-fps timing is unverified.
- Decision: preserve the verified root 25/3-fps set and all prepared inputs.
  The selected three-volume attempt is rejected, not a proof that every
  three-volume encoding must fail. Asked the user to prioritize four disks
  at unchanged quality/10 fps, the old three-disk rate, or more compression.
  Twelve affected planner/cadence tests pass; full trace and failed-capacity
  archives are authenticated. The existing dark-opening palette artifact
  remains outside this cadence change.
- [Results and reproduction](toolkit/CB41_10FPS.md),
  [window evidence](toolkit/cb41_10fps_window.json),
  [full preparation and failed capacity](toolkit/cb41_10fps_movie_attempt.json).

## 2026-10-01 — add a five-field CB41 mode with independent 50-Hz AY

- Objective: implement the requested 10 fps without accelerating the source
  or sound. Baseline `a878583`; retain the verified 25/3-fps compatibility mode.
- `convert_video.py --video-codec cb41 --fps 10` resamples the source and
  builds five real AY ticks per video frame. A build-only six-record envelope
  preserves legacy checkpoint assembly; its empty padding is never played.
  The native deadline operand changes 6 to 5: `LD DE,nn`, **10 -> 10 T (0 T)**.
  CB41/LZSA2 syntax, drawing, memory, paging and disk routines stay identical.
- Complete Fuse fixtures: single, portrait, colour/sound over three disks,
  anamorphic and audio tail. **23 frames, 115 AY ticks, 158976 screen bytes,
  seven independent disks**, zero nominal misses or audio gaps/underruns.
  Cold dirty-RAM checks, both prompt transitions, 19 regression tests and
  three new cadence/audio tests pass. Actual streams/traces/disks are saved;
  the archiver verifies hashes and unchanged native kernel/packet listings.
- Decision: keep the opt-in mode and continue full-movie resampling/window
  tests. Short fixtures do not prove sustained movie playback or disk count.
  The original is 24 fps: 10-fps selection has alternating 2/3-frame steps;
  exact display deadlines are distinct from source-sampling motion judder.
  No interpolation experiment is included. Root release images are unchanged.
- [Implementation, cycles and limits](toolkit/CB41_10FPS.md),
  [fixture results](toolkit/cb41_10fps_fixtures.json),
  [reproduction](toolkit/check_generic_cb41.py),
  [archive checks](toolkit/summarize_cb41_cadence.py).

## 2026-10-01 — assess maximum frame rate from saved complete CB41 traces

- **Objective/input:** answer the maximum-fps question from baseline `d751ce8`,
  reusing all three unchanged movie TRDs and their full Fuse traces. No new
  codec/player or candidate disk set is built.
- **Method/results:** authenticate root images, archives, debugger scripts and
  traces; recover native-ready timestamps and cross-check every publication.
  All 4221 frames / 4218 intra-disk intervals are covered. Previous OUT to
  native-ready is 30.448 ms mean, 105.171 ms max; minimum readiness margin
  is 14.828 ms. Comparing the existing trace with 120/100/80/60/40-ms budgets
  gives 0/2/18/187/956 exceeding intervals. These are not faster-rate replays.
  The two above 100 ms are frames 3506/3615 on disk 3. Disk read service
  averages 8.74..8.75 ms per sector, max 43.93 ms, including ROM/CPU/IRQ/drive.
- **Coverage/decision:** current 8 1/3 fps remains the only complete confirmed
  rate; 10 fps is a useful next test, not a promised maximum. Readiness slack
  can contain packet/prefetch work, so its reciprocal cannot estimate a
  sustainable rate. Higher-fps source sampling and AY scheduling need a
  separate verified candidate. Player/root images unchanged, **0 T code delta**.
- **Initial failure:** trace parser rejected abbreviated `com`/`pr` commands;
  extended parsing to match the archived scripts, then verified full counts
  and publication identities. No partial result accepted. See
  [analysis](toolkit/CB41_CADENCE_HEADROOM.md),
  [script](toolkit/assess_cb41_cadence.py) and
  [report](toolkit/cb41_cadence_headroom.json).

## 2026-10-01 — connect the verified five-level player to generic video input

- **Objective/input:** baseline `9885483`; integrate CB41 into
  `convert_video.py` without movie-specific paths/cuts or changing the passing
  root set. Preserve generic aspect ratio, EOF/audio handling and all five
  levels. Existing FAP3 remains the default; select `--video-codec cb41`.
- **Implementation:** reuse palette conversion and exact five-level refinement;
  use exact row/cell books, both cold histories and deterministic padding for
  books with fewer than 256 observed patterns. Automatically select the
  verified native profile, measure 32-frame windows for partition costs, check
  row/AY limits and build one chosen disk set. Reject native/capacity limits
  explicitly without reducing quality or dropping frames. Actual disk size
  remains a gate; a failed estimate can require a smaller frame cap on retry.
- **Measured verification:** five generated inputs cover single-frame silence,
  portrait, moving colour plus sound across three disks, non-square pixels
  and an audio tail. All **20 frames / 120 AY ticks / seven independent TRDs**
  pass full Fuse playback with **zero late nominal deadlines**, no AY gaps,
  duplicates or underruns, exact sectors and **138240 full screen bytes**.
  Both prompt/identity/bootstrap transitions pass with modeled ROM. Colour
  exercises every level 0..4. Native dirty boots/full CPU screens pass; 19
  host/planner/legacy unit tests pass. Reviewed the colour reference preview.
- **Reuse/cycles:** the generic representation reproduces every saved CB41 byte
  and all host screen hashes for the **4221-frame** movie. All three root LFS
  images retain their hashes. Kernel and packet listings are identical.
  LZSA2 retains identical instructions and absolute T-state tables, **0 T
  instruction delta**; smaller scaffold tables can relocate its core within
  uncontended bank 2. Both placements are reassembled and compared exactly.
  Complete prior movie disk/AY/publication evidence remains applicable.
- **Failed attempts/fixes:** a sandboxed unit run could not access installed
  OpenCV; the same local dependencies passed with access enabled. The first
  one-frame build exposed an incorrect inherited host guard: the unused
  playback loop retains a reconstruction call. Corrected the expected set;
  no Z80 opcode change. An initial archive check demanded identical LZSA2
  address operands and stopped; corrected it to validate exact reassembly
  and instruction timings at each placement. No failed check was accepted.
- **Decision/limits:** adopt opt-in generic CB41. Short fixtures prove generic
  input integration, not sustained delivery or universal cadence. The full
  movie proves sustained 25/3 fps on three disks. Arbitrary videos require
  their own complete Fuse gate; physical drive swaps were not measured.
  Test TRDs are Git LFS files; root movie images are unchanged. See
  [instructions](toolkit/GENERIC_CB41.md), [reproducer](toolkit/check_generic_cb41.py),
  [report](toolkit/generic_cb41_profile.json) and
  [archived evidence](toolkit/generic_cb41_evidence/).

## 2026-09-30 — verify the entire five-level movie on three balanced CB41 disks

- **Objective/input:** baseline `2a1686d`; same 4221 prepared frames and AY.
  Move the 95-sector excess off volume 3 without any pixel/audio/FPS change.
  Reuse saved packet/block costs, exact row unions and startup overhead.
- **Selection:** evaluate 1089 nearby cut pairs via prefix counts and cost
  estimates; 502 satisfy row limits. Select 1504/2832, verify seven local
  windows (368 frames), reproduce old full raw streams exactly, and require
  identical host screens. Window LZSA2 179881 -> 179421 bytes. Encode/build
  only that chosen complete partition. Estimated sectors 2474/2505/2518;
  actual **2475/2505/2511**, free **69/39/33**. Actual capacity, not estimates,
  passes. Video 1840522 -> **1839554 bytes** (-968), 7187 sectors/185 blocks.
- **Native/timing:** kernel and packet instruction listings match the prior
  192-frame player exactly, **0 T instruction delta**. All three independently
  booted images finish real Fuse playback: **4221 frames, zero nominal late
  frames**, all 4218 intra-disk intervals six fields, actual OUT phase -3..21 T,
  no fallback late runs or drift. All **25326 AY ticks** exact, no gaps,
  duplicates or underruns. All 7187 runtime sectors exact, zero retries.
  Elapsed bootstrap+runtime **666188838 / 594940974 / 620929017 T** includes
  CPU/ROM/disk/IRQ/ULA, not BASIC loading PLAYER or human swap time.
- **Complete images:** a new read-only Fuse verifier exports 1536-byte slices
  at the shared native draw return in five full passes per volume, avoiding
  thousands of emulator restarts and Windows' command-line limit. It makes
  no debugger memory/paging/PC changes. All **29175552 screen bytes** match,
  including BRIGHT, black fields and progress. Actual OUT/AY timing is checked
  independently on the same image hashes. Existing full source quality and
  visual review remain valid; no quantization or phase change is introduced.
- **Disk transitions:** real prompt/selection/bootstrap opcodes with modeled
  ROM verify both wrong-disk and wrong-series rejection and next-bank images.
  A separate complete Fuse sequence resumes from actual predecessor EOF RAM
  through SZX with other banks poisoned. Both next disks are accepted and all
  subsequent frames/AY meet deadlines. The emulator/controller restart between
  volumes; physical swapping is not claimed. All disks also cold boot alone.
- **Decision:** install root `ZX-video-five-level_part01..03.trd` in Git LFS,
  retain previous evidence and record the full-movie playback milestone as
  verified. Overall converter goal stays active for generic integration;
  preserve this passing fixture. [Scripts, audit, traces and disk links](toolkit/CELL_CODEBOOK_BALANCED.md).

## 2026-09-30 — prepare the full five-level edit and measure CB41 volume limits

- **Objective/input:** baseline `2a9fa05`; extend the passing 192-frame CB41
  fixture to the entire source-identified 4221-frame authorized edit, existing
  AY50 and unchanged resolution/25:3 fps. Preserve source frames 0..4085 and
  4836..4970, including the post-credit scene and EOF.
- **Preparation:** original quantizer, penalty 100000, center zoom 1.25,
  continuous palette history, five-level refinement then fixed-phase dither.
  Hashed sequential 64-frame caches avoid repeated conversion. All 4221
  frame-level errors/hashes retained; no refinement increases same-palette
  RGB error. Mean MSE 834.5453 -> 743.7552 (-10.879%), not a perceptual score.
- **Attempts/corrections:** plain FPS-to-EOF produced 4970 source frames and
  was rejected. Restored the original ceil-to-six-fields final hold: 4971
  source frames, 0.058333 s extension, identical unextended prefix. A duplicate
  `ticks` field initially stopped the audio-report helper; fixed before saved
  measurements. Equal thirds need 245/259/244 rows and fail the middle table.
  Prefix counts check 64 nearby boundary pairs, 19 fit; choose 1472/2752.
  Only this selected partition is encoded, without a full-image search.
- **Measurements:** dictionaries 249/256/246 rows; resident AY including code
  and trees 12681/13297/14467 bytes. Raw CB41 2906209 -> LZSA2 1840522 bytes,
  7190 video sectors, 185 independent blocks. Exact occupied sectors including
  startup/player/AY are **2425/2433/2639**: third exceeds its limit by **95
  sectors / 24320 bytes**. Aggregate spare capacity 135 sectors does not prove
  a feasible three-volume partition.
- **Verification:** independent fixed-phase host raster matches all 4221
  full screens / 29175552 bytes. Six source RGB samples agree with the old
  fixture. All 25326 original AY states, edit mapping/join/EOF, host block
  round trips and overlap proofs pass. First two fitting candidate images
  pass dirty-RAM cold bootstrap; no third image is written. Native hot-path
  opcodes unchanged, 0 T instruction delta. No new full-movie native timing,
  actual IRQ/disk/publication or disk-swap check; no fps success claim.
- **Review/decision:** inspected difficult scenes, post-credit action and
  worst-error opening fade; existing Spectrum palette/colour-cell limitations
  remain visible. Retain preparation and streams, reject this capacity split,
  leave root TRDs unchanged. Next rebalance cuts using bounded windows and
  saved frame costs, then verify one complete set through actual playback.
  [Scripts, report, preview and archived evidence](toolkit/CELL_CODEBOOK_MOVIE.md).

## 2026-09-30 — sustain exact CB41 playback across all 192 saved frames

- **Objective/input:** baseline `4006665`, all three original 64-frame scenes,
  same five-level states/AY as the earlier 7.683025-fps fixture. One dictionary
  and continuous producer across all scenes, including frame zero.
- **Change:** explicit black-row/first-attribute checkpoints before frame
  zero; support arbitrary selected fixture lengths without another codec
  sweep. Share startup semantics across encoder, host decoder, builder and
  CPU check. Generalize evidence archiving and add source/Fuse preview script.
- **Results:** real Fuse **8.3333331 fps**, **zero late deadlines**, all
  six-field intervals, no late runs; exact 1152 AY records without gaps,
  duplicates or underruns. Video **154956 -> 134349 bytes (-13.30%)**, sectors
  **606 -> 525**, total file sectors 572. **392 sectors** read during playback;
  133 before first publication. All 192 full screens match (1327104 bytes).
- **CPU/codec:** unchanged native opcodes, delta 0 per instruction. Decoder
  19412006 -> 12698715 T (-34.58%), producer 1058423 -> 855775 T; 12 blocks
  versus 21. Native draw 24524522 T, packet/wrappers 70740 T, startup book
  54028 T. Actual timing separately includes ROM/disk/IRQ/ULA. Old frame
  reconstruction/output cost 43760146 T has a different ownership scope.
- **Coverage:** dirty cold boot, all CPU frames/progress, all runtime sectors,
  host/author overlap proofs and independent full-flags slices pass; 121
  synthetic interrupts, none unavailable. 22 boundaries and new start-0/1,
  future-history independence tests pass. Previous 64-frame raw/stream hashes
  reproduce exactly. Visually inspect frames 31/95/159/191 against saved RGB.
  Preview initially used a states-only NPZ without RGB; use the full cache
  after verifying the identical state hash. No player change was needed.
- **Decision/limits:** update root LFS `ZX-video-cb41-test.trd` to this 192-frame
  experiment; preserve old evidence/Git version. Next prepare the full 4221-
  frame edit, row-book/capacity plan and independently bootable volumes, then
  integrate the generic converter. The full goal and three-disk fit remain
  unproven. [Report, preview, scripts and evidence](toolkit/CELL_CODEBOOK_SUSTAINED.md).

## 2026-09-30 — integrate CB41 and verify an independent 64-frame TRD

- **Objective/input:** baseline `d77b8ad`, saved frames 128..191 (source
  3855..3918), exact same 59396-byte CB41 stream, LZSA2 unchanged. Test actual
  delivery, screen publication and AY instead of extrapolating component CPU.
- **Change:** connect direct back-screen renderer to the existing disk/queue,
  AY50 and six-field ISR; load the book once from the stream. Retire compact
  reconstruction and extra-packet lookahead. Include both initial screens
  and AY checkpoint for independent cold boot. Remap four IRQ operands to
  fixed screen-state bytes, 13 -> 13 T each. No screen paging during drawing.
- **Results:** full real-Fuse EOF, **8.3333324 fps**, **zero late frames**, all
  six-field intervals, OUT phase 0..16 T, no late runs. Exact 384 AY ticks,
  zero gaps/duplicates/underruns. All 166 sectors verified; stream 42303 bytes,
  total file sectors 218. All 64 full published screens match (442368 bytes),
  including attributes and progress. Dirty boot and integrated CPU checks pass.
  Native draw remains 7910734 T; packet/wrapper instructions 23636 T, startup
  transposition 54028 T. ROM/disk/IRQ/ULA are separate in actual elapsed time.
- **Attempts:** first CPU video checks passed, but inspection found progress
  code removed with the retired region. Restore it before Fuse, guard its
  boundary and add all-progress-step checks. Do not distribute that image.
  Remove unnecessary OpenCV imports from the archive script after a missing-
  dependency attempt. These fixes and final full evidence are retained.
- **Decision/limits:** retain separate LFS `ZX-video-cb41-test.trd`. This is
  a 64-frame experiment: 130/166 video sectors arrive before first publication.
  Next run all 192 saved frames without pipeline resets, then the full edited
  movie and generic converter/volume integration. Full goal and three-disk
  capacity remain unproven. Older root images are unchanged.
  [Implementation, exact timings, reproduction and evidence](toolkit/CELL_CODEBOOK_PLAYER.md).

## 2026-09-30 — implement and verify native CB41 cell output

- **Objective/input:** baseline `d1f32d3`, unchanged saved frames 128..191,
  both prior screens, exact CB41 payloads and standard LZSA2 bytes. Implement
  native cell output without changing brightness-before-dither ordering.
- **Change:** 335-byte Z80 book renderer, masks/attributes, exact row fallback,
  alternate registers and an eight-page planar book. Book/popcount provisionally
  replace obsolete compact-frame RAM; full player integration remains pending.
  Native 2048-byte book transposition costs 54028 T once.
- **Results:** book draw 7910734 T versus old frame component 14295892 T,
  -6385158 T (-44.66%). Literal-only draw 7198585 T; book output adds 712149 T,
  but separate decoder/producer savings exceed that by 779470 T. Means are
  112477.89/123605.22 T, maxima 180208/191369 T for literal/book. The old
  component includes different reconstruction/ownership/paging; new draw
  assumes supplied payload and mapped target, so this is not delivery time.
- **Interrupted attempt:** the first book run stopped at unsupported SCF in
  the small banked CPU. SRL of the exhausted sentinel already sets carry;
  remove the redundant SCF, saving 4 T per refill (9768 T derived over this
  window) and one code byte. Final full-flags independent checks pass.
- **Verification:** both full screens on all 64 frames, all 22 native boundary
  variants, guarded read/write regions, preserved input/code/tables, IX/IY/SP,
  paging and exact per-instruction/independent-core timings pass. Synthetic
  IM1 checks inject 106 interrupts, zero unavailable events. Maximum synthetic
  draw 240190 T. Source/payload identities and instruction histograms retained.
- **Decision/limits:** keep component and proceed to one independently
  bootable timing-test disk. Copies, caller paging/publication, actual AY/IRQ,
  ULA, ROM/disk and startup integration remain unmeasured. No new TRD or fps
  claim; root image stays at last measured 7.683025 fps, goal incomplete.
  [Implementation, cycle accounting, scripts and evidence](toolkit/CELL_CODEBOOK.md).

## 2026-09-30 — exact 4x4 logical-cell codebook feasibility

- **Objective/input:** baseline `63947dd`, saved frames 128..191 (64 frames,
  source 3855..3918), retaining both prior screen states and exact five-level
  output. Test ready cells with exact fallback, not approximate DCT.
- **Change:** experimental CB41 direct back-screen cell deltas, bitmap and
  attribute masks, 256 observed exact patterns, one-bit mode selection and
  four-row-index fallback. Reconstruct brightness before fixed dithering.
  A literal-only direct-cell control isolates the dictionary contribution.
- **Results:** current/control/book raw bytes 105999/88788/59396; LZSA2 bytes
  51022/42675/42303, including the book's complete 2048-byte table and metadata.
  Sectors 200/167/166. The book covers 11294 of 19303 changed cells (58.51%).
  Decoder T 6353724/5393835/3923387; producer T 350445/294260/273089. Versus
  current, -17.09% bytes, -38.25% decoder CPU, -2507693 decoder/producer T.
  Maximum slice rises 19190 -> 21530 T; realtime scheduling remains untested.
- **Verification:** both representations restore all 64 complete host
  screens and retained other screens exactly. 22 edge variants cover every
  book index, full fallback, BRIGHT and mode-mask boundaries. All 17 blocks
  pass author/host overlap, guarded banked sector/EOF/timing and independent
  per-slice checks, with 60/53/37 synthetic interrupts. Largest synthetic
  packet is 3096 bytes, window maximum 1333 bytes.
- **Decision/limits:** promote to native cell-output implementation. No
  player, disk, actual fps or cold-boot/full-movie capacity claim: fresh
  window compression and supplied prior history are explicit. Common AY,
  row table and existing player are outside the comparison. Root TRD stays
  unchanged at last measured 7.683025 fps; goal remains incomplete.
  [Format, exact checks, scripts and evidence](toolkit/CELL_CODEBOOK.md).

## 2026-09-30 — test bounded LZSA2 reset placement and correct copy profiling

- **Objective/input:** baseline `8b03511`, same 192-frame five-level stream.
  Change only the last five blocks (69988 raw bytes, frames 151..191), keeping
  the prefix, 21-block count, native decoder and original LZSA2 syntax.
- **Parameters:** greedily align feasible cuts to packet starts; follow up
  with 4686 bytes of initial slack to vary reset phase within the same tail.
  Keep every output block <=15872 bytes; no full-disk or codec sweep.
- **Results:** aligned 154956 -> 155007 bytes, 606 sectors unchanged;
  decoder +9263 T, copies -7046 T, producer +64 T, frames +112 T, net
  **+2393 T**. Shifted 154883 bytes (-73), 606 sectors; decoder +12882 T,
  copies +2454 T. Shifted producer/frame/playback effects are unmeasured.
- **Verifier fix:** replace hardcoded offset/15872 calculations with
  validated metadata block bounds. Every old copy case, including 45 edges,
  reproduces exactly. New native copy cases pass for both layouts.
- **Coverage:** all ten changed blocks pass original-author/host/native,
  overlap proofs and 40 synthetic interrupts per candidate. Aligned also
  passes full banked sector/EOF/cursor/timing checks and all 192 exact compact
  frames/both native screens. No real disk, AY cadence or Fuse candidate run.
- **Decision:** reject both heuristic placements as production changes;
  preserve scripts/reports and the corrected verifier. Root TRD unchanged;
  last measured 7.683025 fps still fails the goal. Next bounded feasibility
  check: ready 4x4 logical block dictionary with exact fallback and the
  confirmed brightness-before-dither ordering.
  [Method, cycle accounting and evidence](toolkit/LZSA2_RESET_PLACEMENT.md).

## 2026-09-30 — clarify brightness-before-dither ordering

- User clarification applied to the transform proposal: reconstruct
  brightness, quantize to five levels, then apply fixed-phase dithering.
  A fused table must reproduce that order; independently dithered basis
  contributions must not be summed. Documentation only, no new measurement
  or player/image change. The clarification preserves the proposed quality
  gate and is recorded in the [plan](toolkit/LZSA2_COMPRESSION_PLAN.md#quality-and-compatibility-constraints).

## 2026-09-30 — assess table-driven inverse transforms for the video layer

- **Objective/scope:** answer whether a simplified table-driven IDCT could
  help; baseline `a977f1d`, existing five-level 128x96 logical image and
  512-byte row dictionary. Design analysis only, no new codec experiment.
- **Proposal:** distinguish basis-contribution tables (runtime accumulation)
  from 256 complete 4x4 logical / 8x8 physical patterns (2048 bitmap bytes,
  one-byte index before metadata). The latter moves reconstruction and
  dithering to the PC; it is a codebook, not a general IDCT decoder.
- **Estimates/limits:** a naive DC + three-AC direct sum needs 48 additions
  per block, 405504 T for additions alone on a full 768-block redraw using
  11-T 16-bit additions. This is neither a native measurement nor a lower
  bound for factored/table-index algorithms. No size, quality or fps gain
  has been measured. A complete-pattern index replaces four literal row
  indices only where suitable; dictionary, fallback and LZSA2 costs matter.
- **Decision:** retain as a separate video-format candidate with exact
  fallback, fixed dither phase, attribute preservation and independent disk
  initialization. LZSA2 syntax can stay unchanged, but new video commands
  require decoder support. Main implementation/root TRDs remain unchanged;
  do not displace the current reset-placement task without a measured result.
  [Feasibility, estimates and verification plan](toolkit/LZSA2_COMPRESSION_PLAN.md#separate-video-layer-proposal-table-driven-inverse-transforms).

## 2026-09-30 — test exact fixed-command LZSA2 distance selection

- **Objective/input:** follow the short-reset speed example on complete
  block 11 of the same 192-frame/21-block fixture, baseline `ca95df5`.
  Preserve LZSA2 format, literal/match positions and lengths, and byte budget.
- **Change:** host DP over previous offset and used nibbles, exhaustive
  canonical source distances, backward size bound and native token-cost
  table. No beam/candidate cap; 2194 commands, 75520 distance alternatives,
  peak 370 states. No production decoder/converter integration.
- **Results:** payload 7165 -> 7165 bytes; exact minimum 14329 nibbles.
  Candidate uses 14330 nibbles and changes 320 offsets, mostly cost-neutral.
  Block decoder 944426 -> 944318 T (-108); full stream decoder 19412006 ->
  19411898 T. Producer stays 1058423 T, stream 154956 bytes / 606 sectors.
- **Verification:** 3214 direct native cost boundary cases; 187 fixed layouts
  versus 2716 exhaustive serialized alternatives. All 21 author round trips,
  guarded banked overlap/cursor/sector/EOF/short-read checks and independent
  per-slice timings pass; 184 synthetic interrupts. Root TRD hash unchanged.
  No new Fuse, actual AY cadence or full-movie release run.
- **Decision:** reject integration/expansion of this distance-only pass:
  zero capacity benefit and only 0.00056% less stream decoder CPU. Preserve
  scripts/evidence, close this hypothesis, and next test a few reset positions
  on one window. Overall five-level 25/3-fps goal remains incomplete;
  last actual run is still 7.683025 fps with 118 missed nominal deadlines.
  [Implementation, cycle accounting and evidence](toolkit/LZSA2_DISTANCE_SELECTION.md).

## 2026-09-30 — bound LZSA2 parser losses with an exact short-input oracle

- **Objective/input:** continue toward smooth five-level 25/3 fps after
  table expansion proved ineffective. Baseline `a63043a`; unchanged format,
  native decoder and 21-block/192-frame saved video. One finite oracle corpus.
- **Change:** exact host DP retaining position, previous offset and pending
  literal length; exhaustive valid matches, shared nibble costs and upstream
  EOD. Separate canonical serializer and local wrapper around the unmodified
  author library. No production player or converter integration.
- **Results:** no byte-size improvement on 1341 inputs (1022 exhaustive
  binary, 256 seeded mutations and 63 video excerpts). All match the exact
  minimum within this tested scope. Of 232 different equal-sized parses,
  20 are faster, 24 slower and 188 equal on the unchanged decoder. Seven
  faster cases are video excerpts; one 128-byte example costs 8784 -> 8304 T
  (-480). Best-of 2786 T across standalone cases is not a full-stream saving.
- **Verification:** separate complete-command enumeration on 126 inputs;
  original-author/host round trips for all cases and 30 serializer boundaries;
  DLL reproduces all 21 full baseline payloads. 531 native banked cases pass
  byte/cursor/overlap/sector/EOF and short-read checks, with independent
  full-flags agreement on every slice. Pinned upstream checkout stays clean;
  root TRD hash unchanged. No new IRQ cadence, disk/Fuse or full-movie run.
- **Decision:** retain oracle as a verifier; no default parser replacement
  or broader constant sweep. Next test lower-cycle match-distance choices
  on one complete block with real last-offset/nibble state and unchanged
  byte budget, retaining the baseline fallback. The overall goal remains
  active; existing 7.683025 fps / 118 late frames does not meet it.
- **Reproduction:** [method and limits](toolkit/LZSA2_EXACT_ORACLE.md),
  [oracle](toolkit/lzsa2_oracle.py), [comparison](toolkit/probe_lzsa2_oracle.py),
  [summary](toolkit/lzsa2_oracle_profile.json),
  [evidence](toolkit/lzsa2_oracle_evidence).

## 2026-09-30 — test stronger search with the unchanged LZSA2 format

- **Objective/input:** analyze a stronger compatible compressor and larger
  dictionaries/search tables; baseline `c3d1125`, pinned upstream `15ee2df`,
  same 21 independent 15872-byte-or-smaller blocks / 192 five-level frames,
  323940 decoded bytes. Existing `--prefer-ratio` already active.
- **First attempt:** candidate matches 64 -> 128; first/final arrival
  limits 32/64 -> 128/256 with matching index shifts. Host-only structures;
  unchanged standard writer and C/Z80 decoders. Stream 154956 -> 154954
  bytes (-2), still 606 sectors; decoder 19412006 -> 19412144 T (+138).
  Observed sequential PC compression 6.92 -> 30.26 s; not a rigorous benchmark.
- **Evidence-driven follow-up:** remaining supplement ceilings 15/46/63 ->
  63/95/127, two insertion caps 12 -> 48 and match-length limits 16 -> 64.
  Stream 154944 bytes (-12, 0.00774%), still 606 sectors; decoder 19412766 T
  (+760). Ten blocks improve, one worsens by a byte. Observed PC compression
  10.06 -> 40.60 s. Main host table allocations about 112 -> 416 MiB, source
  estimate rather than measured working set. Size-only best-of estimate saves
  13 bytes; not a new built stream or disk.
- **Verification:** all baseline recompressions byte-identical; both 21-block
  streams exact in original-author, host, guarded banked and independent
  full-flags Z80 decoders. Input-cursor/overlap/bank/sector/EOF checks pass,
  every independent slice agrees, 184 synthetic IM1 interrupts per candidate.
  Deeper variant passes 27 native non-video edges. Player code and root TRD
  unchanged. No real disk/ULA/AY schedule, Fuse or full-movie release test.
- **Decision:** reject these increases as production defaults; retain
  reproducible compatible prototypes. Next build a small exact parse oracle
  to expose actual pruning losses, then test a stronger parser in a bounded
  window. Plan separates host tables, runtime history and video dictionaries;
  includes compatible block-boundary selection and a guarded history study.
- **Reproduction:** [analysis and plan](toolkit/LZSA2_COMPRESSION_PLAN.md),
  [probe/build script](toolkit/probe_lzsa2_search.py),
  [summary](toolkit/lzsa2_search_profile.json),
  [evidence](toolkit/lzsa2_search_evidence).

## 2026-09-30 — analyze and specialize LZ4 short-run decoding

- **Objective/input:** user-requested LZ4 improvement analysis; baseline
  `e681055`, same 21 saved LZ4-HC12 blocks / 192 exact five-level frames,
  323940 decoded bytes. One generic implementation and one fast candidate.
- **Change:** resumable standard LZ4 ASM, guarded host overlap parser and
  component profiler. Inline 1..14-byte literals and 4..18-byte matches;
  avoid two `EX (SP),HL` operations for short matches. Keep 256-byte quota
  checks on long copies, existing slot banks and unchanged stream bytes.
- **Measured results:** decoder 19847554 -> 15657014 T (-4190540, -21.11%),
  code/state 267 -> 280 bytes, maximum video slice 20126 -> 15338 T. Paths
  save exactly 58/101 T on short literals/matches and add 19/22 on extended
  paths; run counts reproduce the aggregate delta exactly. Versus LZSA2,
  decoder/producer saves 3598927 T but adds 28492 bytes / 111 sectors.
- **Analysis:** prioritize bounded codec selection and Z80-aware host
  parsing. Ideal LDIR-repeat removal is limited to 1366050 T before new
  overhead. Reject simple one-or-three-byte offsets: +18092 bytes estimated
  from actual distances. No measured alternative-offset decoder or fps.
- **Verification:** both variants pass all 21 banked/native blocks and 46
  edges each, independent full-flags per-slice cycles, author LZ4 decoding,
  overlap/cursor/bank/sector/EOF checks, nine malformed host cases and
  synthetic IM1 runs (183/143 video interrupts). Initial assembler fixes,
  a synthetic interrupt acceptance assumption and overlapping flat-test
  input placement were corrected; affected checks reran successfully.
- **Decision:** retain verified component experiment and plan; defer
  production adoption pending actual disk/queue/publication timing. Current
  TRD hash unchanged. No new boot, AY cadence, Fuse or full-movie release.
- **Reproduction:** [analysis and commands](toolkit/LZ4_OPTIMIZATION.md),
  [decoder](toolkit/resumable_lz4.py), [profile](toolkit/row_lz4_profile.json),
  [evidence](toolkit/row_lz4_evidence).

## 2026-09-30 — test compiled COPY/FILL row output

- **Objective/input:** reduce native pixel-output work toward smooth
  five-level 25/3 fps; baseline `42bcc0f`, retained borrowed-literal disk,
  same 192 frames and 172-entry row dictionary. One command-layout probe.
- **Change:** host-generated row COPY, patterned FILL and solid FILL runs;
  execute real unrolled Z80 suffixes, verify both screen histories, append
  the proposed command bytes to video packets and measure LZSA2 transport.
  A single DP policy charges native work plus 81 T per command byte.
- **Measurements:** native bitmap commands 16931839 T; optimistic complete
  output 20246890 -> 17743885 T (-2503005). Commands total 153935 bytes,
  with 3231675 T of LDIR copy work. LZSA2/producer grows by 8975251 T;
  component regression 9703921 T before new helper/queue costs. Video grows
  154956 -> 211907 bytes and 606 -> 828 sectors. No inferred playback rate.
- **Verification:** all 192 bitmaps/both histories, unchanged input/code/
  tables, all native instruction timings, 1152 suffix/address-boundary cases,
  31 native LZSA2 blocks with overlap/cursor/sector checks. Other packet
  fields reproduce the originals. Maximum packet 3632 bytes. Initial import
  and cache-directory setup failures were fixed before completed results.
- **Decision:** reject integration; retain the current TRD (hash checked).
  No boot/IRQ/physical-disk/Fuse run or full-movie result for this format.
  Next measure a selective fast outer decoder on saved blocks, charging its
  disk cost; do not repeat this command expansion or the host codec sweep.
- **Reproduction:** [method and commands](toolkit/COMPILED_ROW_OUTPUT.md),
  [native probe](toolkit/probe_compiled_row_output.py),
  [summary](toolkit/compiled_row_output_profile.json),
  [evidence](toolkit/compiled_row_output_evidence).

## 2026-09-30 — test motion on whole five-level dictionary symbols

- **Objective/input:** test whether proper motion can reduce input work on
  the smooth-five-level goal; baseline `d0e4731`, unchanged 192-frame windows
  at 629/2857/3855, 172 row symbols, resolution and 1152 AY records.
- **Change:** experimental `row_aligned_motion=True` restricts prediction
  to 27 whole-symbol offsets, excludes spatial/sub-byte shifts, and removes
  the 16-byte fragment allowance only for motion comparisons. One candidate;
  default encoding is byte-identical. No native implementation change.
- **Results:** 6540 motion commands; cache active in 191/192 frames. Decoded
  volume 323940 -> 261389 bytes; LZSA2 154956 -> 151643 bytes (606 -> 593
  sectors); decoder 19412006 -> 14216558 T. Frame stages grow 41965760 ->
  63715325 T (+21749565), including 8753180 cache and 5481126 motion T.
  With the stated copy lower bound, the candidate component model exceeds
  the latest borrowed-literal baseline by 16933120 T. No elapsed fps claim.
- **Verification:** default encoding exact; independent frame/AY round
  trips, all 192 full compact and both native-screen CPU checks, all 17
  native LZSA2 blocks with timing/cursor/sector/overlap checks; four targeted
  and eleven existing converter tests pass. Current root TRD hash unchanged.
- **Decision:** reject realtime adoption of this byte-count selector; keep
  its opt-in reproduction and evidence. Avoid another disk build for this
  clear CPU regression. Motion needs explicit cache/patch costs or a cheaper
  reference buffer. Return to native output on the retained faster image.
  This is a component experiment, not a playback or full-movie release.
- **Reproduction:** [method and commands](toolkit/ROW_ALIGNED_MOTION.md),
  [probe](toolkit/probe_row_aligned_motion.py),
  [summary](toolkit/row_aligned_motion_profile.json) and
  [saved evidence](toolkit/row_aligned_motion_evidence).

## 2026-09-30 — consume literal suffixes directly from retained LZSA2 slots

- **Objective/input:** continue toward smooth five-level 25/3-fps playback;
  baseline `dacb24f`, same 192 frames/21 blocks, fragment allowance 16,
  172-entry row table, original 50-Hz AY. One transport candidate.
- **Change:** optional `--borrow-literals` keeps metadata/Huffman in fixed
  RAM and borrows a retained slot's literal suffix. Crossing/released-slot
  packets keep normal copying. Host validation excludes motion/spatial
  commands before reusing their code RAM. No format, compressed video,
  slot/buffer size or native pixel changes; 243 bytes of new code/state.
- **Measured CPU:** 171 borrowed packets avoid 226819 copied bytes. Copy
  bridges 5511858 -> 1950856 T (-3561002); frame stages 41965760 -> 43760146 T
  (+1794386 for bridges/paging), net component -1766616 T. Every new
  executed instruction is checked against its timing row. CPU fixture
  excludes ROM/disk/IRQ/ULA and does not replay the real producer schedule.
- **Real delivery:** full Fuse span 90549516 -> 88138641 elapsed T, fps
  7.478465 -> 7.683025; missed deadlines 134 -> 118, maximum 133 -> 99 fields.
  Invalid fallback intervals remain 24. Late runs 43 and 67 recover on the
  next frames; 76..191 remains late. Video stays 154956 bytes / 606 sectors,
  disk stays 653 occupied sectors. Read/seek windows measured separately.
- **Verification:** all 192 compact/both native frames and input/cursor/
  bank/stack guards; 45 native copy edge cases; five host contract tests
  including eight rejected vectors; dirty-RAM cold boot/priming; actual EOF,
  all sectors, 1152 exact AY ticks, 80 pixel samples per frame and six full
  captures (41472 exact bytes). No full-movie/hardware timing claim.
- **Rejected setup attempts:** memory guards rejected helpers at 7800h
  (resident initializer/producer) and DF00h (disk driver) before native
  execution. Final code uses host-excluded motion RAM. Verifier setup fixed
  a block-list/count mismatch and host-write guard state; retained results
  follow the fixes. No changes to the successfully built native candidate.
- **Decision:** adopt as optional validated mode and update the existing
  LFS test disk. Both release timing gates still fail; continue with native
  pixel output. [Details](toolkit/BORROWED_LITERALS.md),
  [CPU verifier](toolkit/verify_borrowed_literals.py),
  [summary/evidence](toolkit/borrowed_literals_profile.json).

## 2026-09-30 — reprofile current LZSA2 playback stages

- **Objective/input:** user-requested bottleneck comparison, baseline
  `de0a50d`; unchanged optional LZSA2 TRD, 192 frames (source windows
  629/2857/3855), 21 blocks, 154956 bytes / 606 runtime sectors, original AY.
- **Method/change:** fresh deterministic frame and decoder/producer probes,
  plus real Fuse pipeline tracing through EOF. No native or stream change:
  absolute instruction counts below, delta 0 T and 0 compressed bytes.
- **Measured:** elapsed foreground interval 91220166 T: transfer 38845163
  (42.58%), output 20858966 (22.87%), reconstruction 20133887 (22.07%),
  metadata 3313930 (3.63%), mixed control/prefetch/wait 8068220 (8.84%).
  Separately, CPU output 20246890 T, LZSA2 19412006 T, fragments 9090556 T;
  packet LDI copies cost at least 5183040 T. Motion/spatial/cache handlers
  consume 0 T on this fixture. Queue empty at 153/192 packet starts; worst
  transfer 1249405 T. Disk windows are nested, never added to stage totals.
- **Coverage/result:** all 21 guarded decoder blocks, 192 full compact/both
  native screens in CPU model; complete Fuse EOF, 606 sectors, 1152 exact
  AY ticks, 80 pixel samples/frame. Publication span repeats 90549516 T,
  7.478465 fps, 134 missed deadlines, max 133 fields, 24 invalid fallback
  intervals; late run 67..191 remains unrecovered. No full-movie/hardware
  verification. Prior full captures remain valid for this unchanged image.
- **Decision:** prioritize avoiding decoded-packet copies, then screen
  writes and decoder parsing. Ideal removal of all LDIR repeat overhead
  saves at most 995975 T before replacement overhead, far below packet-copy
  cost. Do not optimize motion for this fixture or launch another codec sweep.
  [Analysis](toolkit/LZSA2_STAGE_PROFILE.md),
  [reproducer](toolkit/profile_lzsa2_stages.py),
  [report/evidence index](toolkit/lzsa2_stage_profile.json).

## 2026-09-30 — accelerate LZSA2 flag dispatch without changing the stream

- **Objective/input:** user-requested decoder acceleration, baseline
  `afc18fc`; reuse the archived 192-frame/21-block row-video fixture and
  original 50-Hz AY. Keep identical resolution, pixels and compression.
- **Change:** restore upstream `JP PE` token selection and sign-flag offset
  checks; the earlier port had used slower comparisons for its limited
  test CPU. Extend only the verifier's logical S/P flag flow. Core shrinks
  257 -> 250 bytes in uncontended bank 2; total prefix/core/state 391 -> 384.
- **Measured:** 19844626 -> 19412006 decoder T (-432620, -2.1800%), exactly
  predicted by 19683 short-literal tokens saving 20 T and 4870 extended
  tokens saving 8 T; no-literal dispatch is unchanged at 54 T. Producer
  stays 1058423 T, runtime stream 154956 bytes / 606 sectors, disk 653 sectors.
  Full Fuse span 90904059 -> 90549516 T; mean 7.449298 -> 7.478465 fps.
  Missed nominal deadlines 135 -> 134, maximum lateness 137 -> 133 fields,
  bad fallback intervals 27 -> 24. Final late run 67..191 remains unrecovered.
- **Verification:** all 21 guarded blocks and 27 edge cases pass. Independent
  full-flags native Z80 execution matches every old/new slice and all bytes;
  separate IM1 runs pass with 185/184 injections. All 256 sign/parity token
  inputs checked. Cold boot/priming, 192-frame EOF, 606 runtime sectors,
  1152 exact AY ticks and 80 pixel samples/frame pass. Six full Fuse captures
  match all 41472 bytes. Deterministic CPU is separate from disk/ROM/IRQ/ULA.
- **Rejected setup attempt:** a changed temporary FAP3 file produced a
  different 115271-byte video stream. Discarded before playback comparison;
  retain its build record and rebuild from archived data. Added explicit
  expected raw/video hash checks. Initial missing Python dependency was
  resolved using the existing local packages, without installing new tools.
- **Decision:** adopt the measurable CPU and full-delivery improvement;
  update `ZX-video-five-level-lzsa2-test.trd` in LFS. No full-movie/physical
  drive claim; both release timing gates still fail. Next: packet copies.
  [Analysis and reproduction](toolkit/LZSA2_DISPATCH.md),
  [hashed evidence](toolkit/lzsa2_dispatch.json),
  [independent verifier](toolkit/verify_lzsa2_dispatch.py),
  [capture/archive script](toolkit/summarize_lzsa2_dispatch.py).

## 2026-09-30 — attempt requested multi-engine compiler upload

- **Objective/input:** user-authorized web antivirus check of the compiled
  tool. Actual artifact: source-built Linux/WSL `z88dk-zsdcc`, 25538352 bytes,
  with its SHA-256 recorded in [the security assessment](toolkit/Z88DK_SECURITY_CHECK.md).
  No Windows z88dk EXE was built; its downloaded ZIP remains quarantined.
- **Attempt/result:** VirusTotal's upload page opened, but three supported
  browser file-chooser paths timed out. No file was submitted, no scanner
  result exists, and this cannot support a malware-free or false-positive
  conclusion. Preserve the local Defender findings separately.
- **Decision:** record the technical blocker and the exact local artifact
  for manual upload. Do not restore the quarantined archive or claim that
  opening the upload page completed the requested verification.

## 2026-09-30 — compare native C decoder toolchains

- **Objective/input:** user-requested HI-TECH, SDCC and z88dk comparison;
  baseline `3608253`, same 21 LZMA1 blocks / 192-frame fixture, no re-encoding.
- **Parameters:** one portable C decoder, `lc=lp=0, pb=2`; optimize for
  speed with SDCC 4.6.0, HI-TECH C 3.09-21 and source-built z88dk 2.4 /
  ZSDCC 4.5.0. Scripts pin downloads, preserve flags and save generated code.
- **Measured:** SDCC 6286416196 T / 2443 code bytes; HI-TECH 8213010715 T /
  2638 bytes; z88dk 5359269651 T / 2344 bytes. z88dk saves 927146545 T
  (-14.7484%) versus SDCC, but adds 3053431283 T versus specialized fast
  ASM. Compression remains 133084 bytes / 520 sectors. C scalar/model
  storage is 29/3886 bytes; observed stacks are 69/87/70 bytes respectively.
- **Verification:** all 63 video block decodes exact, plus six data and
  24 malformed cases per compiler, memory guards and ABI checks. Complete
  instruction timing audits on a 14-byte sample agree with continuous runs.
  Completed SDCC/HI-TECH results were reused only after identity checks.
- **Unsuccessful setup attempts:** SourceForge returned an HTML landing
  page; NSIS extraction lacked the expected cc1.exe filename; HI-TECH
  rejected unsupported C syntax; a misplaced ORG gap stalled initial ZXCC
  bootstrap; shell quoting interrupted the first z88dk invocation; stepping
  a DD prefix separately caused a bounded timing-audit mismatch. Fixed
  reproducing scripts and reran affected checks. The separate Defender
  quarantine investigation is recorded below.
- **Decision/limits:** z88dk is best among these tested C configurations,
  but remains 270.06x the LZSA2 decoder CPU. Reject realtime C LZMA
  integration. Player hot-path delta 0 T; no production RAM/IRQ/AY/disk/ULA
  or TRD release claim. Return to packet-copy reduction. See
  [assessment and reproduction](toolkit/Z80_C_COMPILERS.md),
  [benchmark](toolkit/z80_c_compiler_benchmark.json),
  [build script](toolkit/build_z80_c_decoders.py) and
  [guarded harness](toolkit/benchmark_z80_c_compilers.py).

## 2026-09-30 — investigate z88dk Defender detection

- **Objective/input:** inspect the user-reported alert during the requested
  compiler comparison. The Windows ZIP came from the official z88dk v2.4
  GitHub release, not a third-party download site.
- **Observed:** Defender detected `Trojan:Win32/Qwexlafiba!rfn` at 17:17:13
  UTC+02:00 and successfully quarantined the ZIP at 17:17:35. Extraction
  failed with zero files; no executable from that archive ran.
- **Checks:** updated signatures to 1.459.485.0; completed custom scans of
  the source archive and the source-built Linux tool tree, with both scan
  IDs matched to completion events. No new threats detected. The source
  archive SHA-256 matches the official release API. Exclusions could not
  be inspected with this process's Windows privileges; VirusTotal lookup
  was unavailable. HTTPS verification of the extra upstream SDCC source
  dependency failed; its observed HTTP download hash is only a local pin.
- **Decision:** leave the Windows archive quarantined; do not label the
  alert a false positive. Continue the bounded compiler experiment with
  the scanned source build. No antivirus exceptions or security bypass.
  See [assessment](toolkit/Z88DK_SECURITY_CHECK.md),
  [scan script](toolkit/scan_z88dk.ps1) and
  [saved evidence](toolkit/z88dk_security_check.json).

## 2026-09-30 — implement and optimize native Z80 LZMA1

- **Objective/input:** user-requested optimized Z80 assembly decoder, based
  on `08cd640` and the unchanged 21 LZMA1 blocks / 323940 raw video bytes /
  192 frames archived by the modern-codec probe. No new video encoding.
- **Parameters/change:** raw LZMA1 `lc=0, lp=0, pb=2`, 16-KiB dictionary
  limit, output blocks <=15872 bytes, mandatory EOS. Specialize probability
  storage to 3886 bytes; use direct/HL access, EXX for 32-bit arithmetic,
  validated LDIR matches and an eleven-bit unrolled multiplication.
- **Measured:** loop baseline 2901892750 T -> optimized 2305838368 T:
  -596054382 T (-20.5402%). Exact saving is 462 T per adaptive bit;
  multiplication is 1060+29h -> 598+29h T (h=probability popcount).
  Code grows 1345 -> 1464 bytes (+119), scalar state is 64 bytes.
  Compression stays 133084 bytes / 520 sectors. Native LZMA still takes
  116.19x the existing LZSA2 decoder CPU; player hot-path change is 0 T.
- **Verification:** all 42 native video block decodes exact; each variant
  also passes 17 boundary/data cases, 27 malformed/truncated cases, 64
  corrupted-stream checks, 8188 multiplication/product/timing checks,
  nonaligned buffers and synthetic register-preserving IM1 interrupts.
  Independently audit 1044897 executed instructions against the Zilog table.
  Guard code/input/other RAM and uninitialized history; verify ABI on errors.
- **Coverage/decision:** retain the working assembly as a standalone
  experiment; reject this implementation for realtime playback. Flat RAM
  placement uses the screen area, has no paging/yield integration, and the
  synthetic IRQ is not a 50-Hz AY/IM2 test. No new TRD, physical disk/ULA
  timing, full 128-KiB player allocation or release gate is claimed. Return
  to the existing packet-copy work rather than another codec sweep.
- **Reproduce/evidence:** [assembly](toolkit/lzma_z80.asm),
  [benchmark](toolkit/benchmark_lzma_z80.py),
  [report](toolkit/lzma_z80_benchmark.json),
  [ABI, timing derivation and assessment](toolkit/LZMA_Z80.md).

## 2026-09-30 — compare requested LZW and LZH

- **Objective/input:** user-requested follow-up to `e394688`; same exact
  323940 video bytes, 192-frame montage and 21 blocks of at most 15872 bytes.
- **Parameters:** GIF-compatible LZW with 10/11/12-bit table limits and
  early full-table clears; standard ncompress `.Z` with 16-bit limit; LZH
  LH5 with 8-KiB dictionary, using pinned libdragon/LHa encoder code.
- **Measured:** versus 148971-byte ZX0, bounded LZW is 185256/173571/166730
  bytes (+24.36%/+16.51%/+11.92%). Standard LZW is 162770 (+9.26%).
  LH5 is 145725 (-2.18%), 570 sectors: 12 fewer than ZX0, 36 fewer than
  LZSA2. Count block headers; exclude temporary GIF/LHA oracle wrappers.
- **Verification:** 105 video block round trips with independent Pillow,
  7-Zip or lhafile decoders; 30 additional LZW boundary checks and 3 LH5
  cases. Saved source/binary hashes and all compressed candidates. MSVC
  host adaptation completes existing forward array sizes without changing
  the compression algorithm. No player change (0 T), TRD, native timing,
  in-place proof, full memory map or playback/cadence claim.
- **Decision:** reject these LZW variants for capacity; retain LH5's small
  storage gain as unverified for speed. Keep packet-copy work as the next
  implementation priority rather than adopting a new decoder on size alone.
- **Reproduce/evidence:** [assessment](toolkit/LZW_LZH_ASSESSMENT.md),
  [comparison script](toolkit/probe_lzw_lzh.py),
  [results](toolkit/lzw_lzh_probe.json),
  [candidate streams](toolkit/lzw_lzh_evidence).

## 2026-09-30 — compare requested LZMA, bzip2 and modern outer codecs

- **Objective/input:** user-requested codec comparison after `11778ed`,
  allowing expensive PC encoding. Reuse the exact 192-frame video-only
  stream (323940 bytes), all 21 existing blocks and fixed boundaries.
- **Parameters:** LZMA1 presets 0/9-extreme with lc=3 and lc=0, LZMA2
  extreme lc=0; bzip2 1/9, DEFLATE 1/9, LZ4 default/HC12, Zstd 1/19,
  Brotli 1/11. Limit history/window to 16 KiB where configurable.
- **Measured:** ZX0 baseline 148971 bytes. LZMA1 fast 147096 (-1.26%),
  extreme lc=0 133084 (-10.66%); bzip2 both levels 146779 (-1.47%);
  DEFLATE-9 144862 (-2.76%), LZ4-HC12 183448 (+23.14%), Zstd-19
  137607 (-7.63%), Brotli-11 132043 (-11.36%). Include all block headers;
  exclude unimplemented decoder/bootstrap overhead.
- **Coverage:** 294 new exact PC block round trips, input/output hashes and
  archived candidates. Native player remains unchanged (0 T delta); no
  new TRD, Z80 speed, overlap proof, memory map or cadence result. PC decode
  times are not Z80 estimates. Official decoder sources inform RAM analysis.
- **Decision:** defer heavy-decoder integration. LZMA lc=0 merits a future
  bounded native cost probe (5504-byte SDK probability array plus history
  and other state), but 32-bit arithmetic may consume disk savings. Reject
  bzip2's standard 350-KB minimum allocation and tiny saving, and LZ4's size
  increase, for this player. Continue the known packet-copy bottleneck first.
- **Evidence/reproduce:** [assessment](toolkit/MODERN_CODEC_ASSESSMENT.md),
  [script](toolkit/probe_modern_codecs.py),
  [all results](toolkit/modern_codec_probe.json),
  [candidate streams](toolkit/modern_codec_evidence).

## 2026-09-30 — measure faster LZSA2 transport for five-level video

- **Objective/baseline:** reduce transport cost after `c6b8475` on its same
  192-frame montage and exact AY/pixels. No full-movie parameter sweep.
- **Profile:** Fast ZX0 uses 25185674 decoder T plus 1024996 producer T;
  packet-copy LDI alone has a 5183040-T lower bound. Disk/ROM/ULA timing is
  recorded separately from deterministic CPU counts.
- **Change:** optional resumable LZSA2 in the same bank regions and 15872-byte
  slots. Preserve the spare nibble in AF', verify in-place overlap, remap
  known operands, retain ZX0 bootstrap and independent cold boot.
- **Corrected attempt:** the first 192-frame run passed content checks, but
  a synthetic 257-byte match exposed skipped EOD after quota overshoot.
  Fix the block-end yield guard; also accept a first repeat-offset EOD in
  the independent host parser. Keep preliminary reports; repeat affected
  CPU, build and complete Fuse checks after the fix.
- **Final measurements:** decoder 19844626 T (-5341048 / -21.21%), producer
  1058423 T (+33427), total transport CPU -5307621 T. Compressed video
  148971 -> 154956 bytes (+4.02%), runtime sectors 582 -> 606, occupied
  disk sectors 633 -> 653. Real mean fps 7.126866 -> 7.449298. Missed
  deadlines 145 -> 135, maximum delay 194 -> 137 fields, invalid intervals
  28 -> 27. Late runs 43..49 and 56..58 recover; 67..191 does not.
- **Coverage:** all 21 native blocks and instruction costs; 27 boundary cases;
  dirty-RAM cold boot/priming; all 192 real-Fuse frames to EOF, 606 sectors,
  1152 exact AY ticks with no underruns/gaps/duplicates. Six complete screen
  captures match all 41472 bytes. Existing reconstruction evidence is reused
  only for identical FAP3 bytes and dictionary. Physical hardware untested.
- **Decision:** keep a faster optional experiment and root LFS image
  `ZX-video-five-level-lzsa2-test.trd`; leave the generic default unchanged.
  Both timing gates still fail. Neither full-movie capacity nor smooth
  8 1/3 fps is achieved. Next inspect packet copies on this saved fixture.
- **Reproduce:** [transport report and scripts](toolkit/ROW_LZSA_TRANSPORT.md),
  [summary](toolkit/row_lzsa_optimization.json),
  [archived evidence](toolkit/row_lzsa_evidence).

## 2026-09-30 — speed up row-index reconstruction with bounded fragments

- **Objective/baseline:** improve playback after `78541a5`, limiting work to
  its exact 192-frame five-level montage and saved AY. Reuse current CPU and
  Fuse profilers; no re-quantization or movie-wide parameter search.
- **Profile:** real reconstruction occupies 53877513 elapsed T; deterministic
  frame work is 75788625 T. Huffman, cache and prediction dominate the latter.
  Unlike packed pixels, row indices do not have meaningful two-bit subpixels.
- **First attempt:** permit two extra local bytes to select an existing
  fragment handler. CPU 75788625 -> 74872229 T (-916396); ZX0 112364 ->
  113178 bytes. Actual fps 6.7491 -> 6.7875, late frames 174 -> 172, invalid
  intervals 39 -> 40. Preserve this weak result rather than promote it.
- **Follow-up:** the small saving justified one stronger allowance, 16 bytes,
  first checked as a raw/ZX0/CPU window probe without another disk. It saves
  **33822865 T**, reaching **41965760 T (-44.63%)**, with exact frames.
  ZX0 grows to **148971 bytes (+32.58%)**. Only then build the final test.
- **Full actual result:** **7.1269 fps (+5.60%)**, 145 missed deadlines, maximum
  194 fields / 3.88 s late, 28 invalid fallback intervals. Runs 43..53 and
  57..62 recover at 54 and 63; run 64..191 does not recover. All 192 frames,
  582 runtime sectors and 1152 AY records verified; no audio field gaps,
  duplicates or underruns. Both timing gates and A/V synchronization still fail.
- **Quality/CPU checks:** every compact frame and both native screens checked
  in the instruction-timed CPU harness; six real-Fuse full screens match all
  41472 bytes. Eleven converter tests pass. Default raw encoding is identical;
  no Z80 opcode changes, 0 T per-instruction delta. Elapsed transfer now
  dominates (45170386 T); do not confuse it with CPU-only or disk-only time.
- **Decision:** retain an opt-in speed experiment, keep the compact default.
  Save `ZX-video-five-level-fast-test.trd` in LFS (633 used file sectors),
  scripts, traces, both attempts and hashes. Not a whole-movie release.
  [Analysis/reproduction](toolkit/ROW_FRAGMENT_SPEED.md),
  [measurements](toolkit/row_fragment_optimization.json).

## 2026-09-30 — build and measure one five-level test TRD

- **Objective/input:** user requested one image, actual frame cadence and
  sampled picture quality. Three fresh 64-frame windows at 629/2857/3855,
  original RGB, existing corresponding 50-Hz AY, fixed zoom 1.25 and 2x2
  dither. This is a 192-frame montage, not a complete-movie release.
- **Implementation:** one full-volume 172-row dictionary fits the existing
  512-byte renderer tables. Preserve all quantized five-level pixels; retain
  FAP3 motion/Huffman, Fast ZX0 and independent startup. No renderer opcode
  changes, 0 T instruction delta. Startup tables use direct ZX0 compression.
- **Build attempts:** the initial reference validator passed a NumPy view
  where bytes were required; corrected and rerun. The next attempt lacked
  the required format-specific series fingerprint; supplied a deterministic
  raw-derived fingerprint. A subsequent native build exposed the fixed ZX0
  placement assumption, repaired in the separate entry below. No failed
  build is presented as a verified artifact.
- **Capacity:** `ZX-video-five-level-test.trd` is 655360 bytes, independently
  bootable, tracked in LFS. Files occupy 489 sectors / 125184 bytes; 2055
  sectors remain free. Video is 112364 bytes in 439 padded sectors.
- **Real-Fuse result:** whole test disk reaches EOF and 100% progress;
  192 publications and all runtime sectors verified. **Timing fails:**
  mean 6.7491 fps, 174 missed nominal deadlines, maximum 269 fields / 5.38 s
  cumulative delay, 39 intervals outside fallback. Late run 14..57 recovers
  at 58; run 62..191 does not recover. AY's 1152 records are exact with zero
  missed/duplicate fields or underruns, but delayed video breaks A/V sync.
- **Quality:** 80 offsets sampled on every frame without errors. Six full
  screens from separate real-Fuse runs, covering both banks and hard cuts,
  match all 41472 bytes including progress. All 192 host frames match the
  independent five-level reference. Mean active-image RGB MSE improves by
  10.016%, 1.196%, 7.494% versus four-code references; no frame worsens.
  Visually inspected the contact sheet; palette/texture limits remain.
- **Verification/decision:** thirteen decoder/dictionary tests, dirty-RAM
  boot and prime checks pass. Preserve one visual prototype, reports and
  reproduction scripts; reject promotion to playback default because both
  timing gates fail. Do not extrapolate whole-movie capacity or fidelity.
  [Report and commands](toolkit/FIVE_LEVEL_TEST_TRD.md),
  [measurements](toolkit/five_level_test_summary.json),
  [preview](toolkit/five_level_test_preview.png).

## 2026-09-30 — place Fast ZX0 from actual Huffman code bounds

- **Objective/baseline:** build a newly trained FAP3 test after `a7cdf98`.
  The first native build stopped with `retired patch-body bounds differ`:
  its nine-context Huffman code places the retired body at 8DE0..8EF6,
  eighteen bytes earlier than the retained 8DF2..8F08 layout.
- **Change:** derive the fixed-bank decoder placement from the assembled
  inline redirect and retained attribute RET. Carry these bounds through
  in-place and Fast installation; retain range, size, operand and live-branch
  validation. The original placement remains the standalone default.
- **Timing:** only absolute addresses change, in uncontended bank 2. Every
  instruction retains its timing-table cost (for example CALL 17 T, JP 10 T,
  LD HL,(nn) 16 T). Real guarded Z80 execution of the same 15872-byte match
  fixture takes **347057 -> 347057 T**, and the 2100-byte literal fixture
  **46904 -> 46904 T**: both **0 T delta**, identical producer costs/sectors.
  No compressed stream or buffer changes. ROM latency is outside this test.
- **Verification/decision:** eleven decoder tests pass, covering old-layout
  regression, byte-exact relocation, bounds, suspension, shared carry and AY
  interrupts. Keep the fix; it removes a content-specific build assumption.
  Reproduce with [test_dynamic_zx0_placement.py](toolkit/test_dynamic_zx0_placement.py),
  `test_bank2_zx0.py` and `test_faster_zx0.py` via `python -m unittest`.

## 2026-09-30 — improve five-level symbols without extra lookup work

- **Objective/baseline:** investigate compression without slowing decoding,
  after `37578d8`. Reuse verified five-level/hybrid packet caches for the
  same three 32-frame windows; no RGB requantization or whole-set search.
- **Rejected attempt:** top-256 native whole-cell dictionaries hit only
  44.36–54.24% of changed cells. Including 2050-byte books, ZX0 bytes grow
  68648→77866 despite less isolated decoder CPU. Reject for this objective.
- **Follow-up:** dictionary of four-sample rows. Only 114/93/112 different
  changed rows occur; two 256-byte lookup pages cover all transmitted cells.
  Include each book in the compressed stream; retain five-byte escapes.
  Window bytes become 24536/21769/19222 versus 26926/21536/20186.
- **Selection/results:** keep hybrid in window 2857. Offline chosen totals
  are 68648→65294 bytes (-4.886%), Fast ZX0 11380407→11181994 T (-1.743%),
  mocked producer 481172→452965 T, sector reads 270→257. No book-install,
  packet-dispatch, seed-recoding, IRQ/ULA or physical disk timing is included.
- **Native check:** unchanged renderer opcodes with learned tables match
  nine dense/sparse fixtures on both output banks. Dense 154684→154684 T,
  sparse fixture 27101→27101 T, delta 0 T. Four dictionary tests pass;
  all 625 row words and measured packets/ZX0 blocks round trip. Correct
  an initial byte-column error in the host audit reference and rerun it.
- **Decision:** prioritize row-table integration with stable dictionary
  lifetime, exact seed/n-2 handling and full delivery-cost gating. Further
  ideas: complete-book fixed-width mode, partial-row updates, host-only
  stable symbol selection. These remain proposals; no new player or TRDs.
  [Plan, assumptions, scripts and reports](toolkit/FIVE_LEVEL_COMPRESSION_PLAN.md).

## 2026-09-30 — retain all five levels with the established 2x2 pattern

- **Objective/baseline:** follow the user's request to keep the previous
  dither scale and all five coverages after the 4x4 experiment. Use the
  existing host prototypes and the same original-RGB windows 629, 2857 and
  3855, 32 frames plus a seed each, on `codex/dither-4x4` after `b7604ab`.
- **Parameters:** retain colour pairs and BRIGHT; introduce the missing
  quarter shade only on lower squared RGB error. Compare fixed four-code,
  uniform five-level, adaptive four/five-byte cells with endpoint orientation,
  and the pending explicit canonical three-mode representation. Keep the
  phase-aligned 2x2 pattern, logical resolution and FLASH=0.
- **Results:** total ZX0 control bytes are 56146 / 82500 / 68648 / 69887
  respectively. Adaptive hybrid adds 22.27% over four-code input and saves
  16.79% versus uniform-five; canonical adds 1.80% over hybrid. Mean RGB
  error falls 16.14%, 1.16% and 6.81% by window, with no worse frame among
  the 96 measured. Five-byte cells average 6.05%, 1.06% and 3.16%.
- **Coverage:** ten host tests pass, including previous 2x2 pattern identity,
  all five levels in one cell, stable phase across representations, all 625
  row words and per-sample error monotonicity. All window packets/ZX0 blocks
  round trip; inspect frames 630/2876/3886. Reuse cached original RGB and
  exact compressed blocks. Earlier retained-palette control hashes match.
- **Historical attempts:** preserve both previously uncommitted reports;
  their source hashes predate canonical mode. The broader palette-search
  report was not rerun: four of 96 frames had increased error, so retain
  the colour-pair-preserving policy. Do not infer its execution date.
- **Decision/limits:** retain adaptive hybrid as the five-level compression
  reference, canonical as a measured size alternative for native profiling.
  Neither is a verified player format; no native RAM/timing, full playback
  or TRDs. Existing player delta is 0 T. The prior 4x4 +56.19% used a
  different percentage baseline (uniform five-level), not four-code input.
  [Method, current/historical evidence and next step](toolkit/HYBRID_FIVE_LEVEL.md).

## 2026-09-30 — test adaptive 4x4 dithering on a separate branch

- **Objective/baseline:** test the requested spatial pattern on branch
  `codex/dither-4x4` from `a3b4e4e`, preserving the 128x96 logical grid.
  Compare with nearest five-level coverage using the same colour pairs;
  original RGB windows 629, 2857 and 3855, 32 frames plus a seed each.
- **Parameters:** fixed 4x4 Bayer phase, eight target dot counts, RGB range
  <=32 and strictly lower 4x4 mean error to select a tile. Host-generated
  native cells escape from five-byte to eight-byte payloads; attributes,
  BRIGHT and FLASH=0 are retained. No temporal alternation.
- **Results:** aligned tone error falls 18.75–30.68%, sliding tone error
  15.35–23.87%; logical 2x2 error rises 30.35–37.90%, grain 2.70–3.28x,
  temporal residual error 29.28–52.64%. ZX0 cell streams total
  82500→128856 bytes (+56.19%); equal-layout native XOR control also grows
  99215→139074 bytes. These are bounded controls, not release-size estimates.
- **Coverage:** seven tests pass, 96 movie frames plus three seeds decode
  exactly, all compressed blocks round trip. Inspect three movie examples
  and synthetic ramp/bars/edge. Fix an initial border assertion and unsigned
  edge-metric subtraction; regenerate the saved report with caches. No
  native consumer/RAM/timing verification, full playback or TRDs; existing
  player change 0 T.
- **Decision:** retain the experiment, reject enabling this candidate by
  default because texture and size costs outweigh regional tone accuracy.
  [Method, reproduction and evidence](toolkit/SPATIAL_DITHER.md).

## 2026-09-30 — assess eight-level spatial display options

- **Objective/baseline:** assess the user's eight-level quality proposal
  against the current 128x96 logical grid, unchanged 25/3 fps and 50 Hz AY.
- **Analysis:** fixed two-colour 2x2 cells provide five dot-count averages;
  4x4 spatial patterns provide seventeen on uniform regions. Three-bit
  codes would increase full-frame pattern storage 3072→4608 bytes and
  total state 3840→5376 bytes; these are arithmetic, not ZX0 measurements.
- **Decision:** prefer a bounded comparison of adaptive host-generated
  spatial dithering with stable phase against the five-level reference.
  Eight-level precision is regional, not independent in every 2x2 sample.
  Keep temporal alternation and uniform three-bit storage out of defaults.
- **Coverage/limits:** reviewed current format/table definitions and the
  original hardware manual; checked storage arithmetic and documentation
  diff. No codec change, compression run, native timing or new TRDs;
  runtime delta 0 T. [Assessment and next step](toolkit/EIGHT_LEVEL_ASSESSMENT.md).

## 2026-09-30 — scope optimization work to reduce repeated model work

- **Objective:** reduce token consumption while preserving engineering and
  release checks, following the user's request for a more efficient task.
- **Change:** add [a focused task brief](TASK_BRIEF.md) and an agent-rule
  pointer. Define one deliverable, evidence reuse, bounded comparisons,
  targeted tool output and risk-based verification. Scope the next technical
  milestone to a five-level feasibility decision using existing work.
- **Coverage/decision:** reviewed the documentation diff and starting state.
  Mark older uncommitted five-level reports as preceding the latest source
  changes. No technical experiments, player changes or TRDs in this change;
  no measured token-saving claim. Keep full EOF release checks mandatory.

## 2026-09-28 — implement and measure optional native phase correction

- **Objective/input:** implement the accepted phase correction without
  changing compact colour coverage; current 4221-frame edited movie/FAP3.
- **Change:** guarded self-modified dense page operands, separate sparse
  Gray paths, 128-byte phase lookup and 490-byte bank-7 helper. Main code
  shrinks by 19 bytes; net extra code/table memory 599 bytes. Regenerate
  native update maps including attribute-only orientation changes.
- **Results:** 251 raw bytes change on 108 frames, packet sizes unchanged.
  Three optimal ZX0 windows: 27191→27191, 41794→41794, 26684→26677 bytes.
  Isolated 18-band/full-attribute formula over all masks: 370074484→467859829
  T (+97785345), maximum 137426→193819 T. Formula excludes attribute-group
  savings, atomic paging, external calls, IRQ/ULA/TR-DOS and disk latency.
- **Coverage:** 15 renderer/phase tests pass, including all 128×256
  attribute/packed-byte pairs, sparse n-2 changes, guarded writes and AY
  interrupts after every instruction. 96 real movie frames plus six seeds
  match the native reference; exact instruction timing checked. Default
  renderer bytes unchanged; no integrated RAM/cold-boot proof or full EOF.
- **Decision:** retain as optional correctness/cost baseline, not default:
  about 26.4% extra isolated output CPU is material. Compare with adaptive
  five-level rendering/cheaper phase preparation. F900 helper conflicts with
  the separate resumable-packet experiment. No new TRDs or release claim.
  [Implementation/cycles](toolkit/PHASE_RENDERER.md),
  [reproducer](toolkit/audit_phase_renderer.py),
  [report](toolkit/phase_renderer_audit.json).

## 2026-09-28 — retain BRIGHT and forbid FLASH in video attributes

- **Objective/input:** clarify the user's six/seven-bit attribute proposal;
  audit all 4221 no-credits states and the current volume-1 FAP3 source.
- **Change:** explicitly require FLASH=0 in the generic encoder while
  preserving INK, PAPER and BRIGHT. Keep existing sparse n-1 XOR/Huffman
  corrections, dense raw-attribute escape and outer ZX0 unchanged.
- **Results:** zero FLASH occurrences, 2351219 BRIGHT occurrences, 32135
  changes after frame zero; 98.6780% of active attribute positions unchanged
  between frames. 1763 frames have no attribute changes; 41 packets use
  absolute attributes. No compressed-byte saving is claimed by these counts.
- **Verification:** ten generic-converter tests pass, including exact
  round-trip of a BRIGHT-only change and rejection of FLASH. The audit
  checks states and packet flags, not a fresh full stream decode. Z80 delta
  **0 T**; valid format bytes unchanged; no TRDs or playback run.
- **Decision:** adopt the validation rule. Keep seven-bit dense packing as
  a bounded measurement candidate; do not discard BRIGHT or temporal deltas.
  [Format and command](toolkit/ATTRIBUTE_FORMAT.md),
  [audit script](toolkit/audit_attributes.py),
  [report](toolkit/attribute_format_audit.json).

## 2026-09-28 — measure the per-cell brightness-offset proposal

- **Objective/input:** evaluate the user's new proposal before implementing
  the native phase correction. All **4221** no-credits compact frames; same
  resolution, palette endpoints and AY. Interpret the selector as
  **0/25/50/75%** versus **25/50/75/100%**; separately verify that the existing
  format already provides the endpoint-preserving alternative.
- **Parameters/change:** minimize per-cell squared mean-colour error by
  moving the less common endpoint one coverage step, retaining selectors
  over temporal ties. Encode the selection in INK/PAPER orientation:
  **0 extra bytes**, versus **96** for an explicit bit per full-frame cell.
  Host frame size stays **3840 bytes**. There are still four selectable
  values per cell; a shared bit does not permit all five inside one cell.
- **Quality/results:** **106275** active cell occurrences have both extremes,
  across **4136** frames. **231527** logical samples change, mean
  **0.59517%** and worst frame **2.63672%**; mean native-pixel changes
  **0.14879%**. Mean averaged-RGB MSE **23.47648**, maximum **107.01090**,
  relative to phase-aligned compact frames, not original movie RGB.
- **Compression controls:** same three **32-frame** windows, carried n-1
  XOR predictors, optimal ZX0, **15872-byte** block cap and four-byte block
  headers. Sizes **33827→35065**, **48338→48692**, **32330→32719** bytes.
  All blocks round-trip; these **0.7..3.7%** increases exclude the full
  FAP3/AY pipeline and cannot predict disk count or frame delivery.
- **Coverage:** all frames round-trip and satisfy the chosen error minimum;
  five new tests, plus eleven existing phase/five-level tests. All non-FLASH
  attributes and packed bytes exercised. Worst MSE frames **3634/221/222**
  visually inspected; some high-contrast details acquire extra stippling.
- **Decision/limits:** keep the measured host experiment, do not switch
  defaults: these controls add distortion without a size benefit. The
  endpoint-preserving sets are already encoded by existing orientation;
  native phase correction remains the next implementation step. Runtime
  instruction delta **0 T**, no new native-consumer timing, no TRDs generated,
  no complete playback or physical-drive verification. Goal remains unmet.
- **Evidence:** [findings and commands](toolkit/DITHER_OFFSET.md),
  [script](toolkit/probe_dither_offset.py), [tests](toolkit/test_dither_offset.py),
  [report](toolkit/dither_offset_probe.json),
  [comparison](toolkit/dither_offset_comparison.png).

## 2026-09-28 — reproduce opposite dither phase and prototype five-level cells

- **Objective/input:** investigate the user's reversed-dither blocks and
  subsequent request for all five 2x2 coverages within every 8x8 cell. Audit
  all 4221 current no-credits compact frames, unchanged resolution/AY.
- **Diagnosis:** the same half-tone code produces complementary checkerboards
  after an INK/PAPER reversal. Found **549212** matching half-tone boundary
  samples across **4121** frames and **4204** temporal half-tone reversals
  across **448** frames. These are phase opportunities, not perceptual scores.
  Actual unchanged renderer opcodes reproduce frames **3478/3479/4063**;
  forced dense output costs **154684 T** each, excluding IRQ/ULA/ROM/disk.
- **Parameters/implementation:** add an explicit host reference that swaps
  top/bottom pattern rows for darker INK. Preserve every 2x2 colour sum.
  Regenerate n-2 native maps: **321** newly required cells on **108** frames
  would otherwise be omitted after accounting for old dense-band promotion.
  Add a separate five-level RGB quantizer and radix-5 packing prototype:
  four samples in **10 bits**, patterns **3072→3840 bytes**, complete compact
  frame **3840→4608 bytes**, proposed tables **512→2048 bytes**. All five
  shades can coexist inside one attribute cell.
- **Bounded storage results:** three **32-frame** XOR n-1 controls with carried
  preceding predictors and optimal ZX0 blocks up to **15872 bytes**, including
  four-byte block headers: **33827→45071** (629..661), **48338→62106**
  (2857..2889), **32330→41874** (3855..3887). Every block round-trips. These
  controls exclude FAP3 motion/Huffman/AY and do not estimate disk counts.
- **Coverage:** eleven tests; all non-FLASH attributes, 256 packed patterns,
  625 radix-5 words, five-level RGB selection, colour-sum equality and
  alternating-screen replay. All 4221 transformed frames match the aligned
  host reference. Three difficult before/after frames visually inspected.
- **Decision/limits:** retain the reproduced defect, corrected host reference
  and experimental format; implement/profile native phase correction first.
  Fixed 10-bit packing increases storage in these controls and is not adopted
  by default. Five-level native consumer and RAM placement remain unimplemented;
  its Z80 cost is unmeasured. Production opcode delta **0 T**, no TRDs built,
  replaced or promoted; no full playback/physical-drive verification. Original
  movie RGB has not been requantized. Exact user-observed TRD/scene is unknown.
- **Evidence/reproduction:** [findings and plan](toolkit/DITHER_PHASE.md),
  [audit script](toolkit/audit_dither_phase.py), [report](toolkit/dither_phase_audit.json),
  [comparison](toolkit/dither_phase_comparison.png),
  [five-level prototype](toolkit/five_level_dither.py),
  [phase tests](toolkit/test_dither_phase.py), [format tests](toolkit/test_five_level_dither.py).

## 2026-09-28 — calibrate foreground costs without another image-set search

- **Objective/input:** explain the optimistic 64-frame-window estimates
  before selecting another final set. Use the archived Fast baseline and
  four previously measured token selections, all 4221 frames each. No new
  TRDs, Fuse runs, pixels or AY records; runtime instruction delta **0 T**.
- **Changes/parameters:** move metadata expansion into packet acquisition,
  matching actual parser order. Fit transport from 2710 nonwaiting baseline
  transfers: **20.885080 T/byte + 3129.767723 T**, mean absolute residual
  **1848.42 T**. Charge baseline mean entry gaps **3901 T before prepare**
  (4215 observations), **5618 T before draw** (1483 observations). These
  elapsed quantities include unseparated ULA/IRQ/service effects; they are
  not deterministic instruction costs. Candidate publication labels are
  excluded from fitting. Preserve carried state and original deadlines.
- **Results:** baseline predicted lateness **653→903**, actual **1239**.
  Held-out predictions: unweighted **641→835** / actual **1149**; pressure-4
  **622→815** / **1111**; pressure-16 **622→819** / **1105**; window-selected
  **595→825** / **1186**. Aggregate absolute publication error on the four
  held-out sets **17273310436→11184085840 T (-35.25%)**. These are prediction
  errors, not CPU savings. Per-window errors and false timing classifications
  are saved. Metadata relocation alone slightly worsens error; retain that
  intermediate control and the transport-only control in the report.
- **Coverage:** source/input/manifest hashes, complete archived publication
  coverage, four regression tests, saved-report regeneration and readback.
  Calibration uses existing observations; it is not new emulator or hardware
  validation. No candidate TRD set is selected or promoted by this experiment.
- **Decision:** keep the correction as a separate model; it still
  underestimates lateness. Measure queue-step control, background AY service
  and variable decoder demand costs in bounded windows next. Do not declare
  a timing pass or repeat full-set evaluation using this incomplete model.
  Current generic-media integration and deeper prepared-command queue remain
  unfinished. During this work the user's loading-screen request was handled
  separately in the preceding focused change below.
- **Evidence/reproduction:** [analysis and commands](toolkit/WINDOWED_MODEL_CALIBRATION.md),
  [calibrated model](toolkit/calibrated_windowed_model.py),
  [calibration script](toolkit/calibrate_windowed_model.py),
  [report](toolkit/windowed_model_calibration.json),
  [tests](toolkit/test_calibrated_windowed_model.py).

## 2026-09-28 — hide compressed screen staging during startup

- **Objective/input:** implement the user's request that initial screen-RAM
  staging be invisible. Use the current three Fast volumes (`2881667` payload,
  4221 frames); retain every sector except the four-sector PLAYER bootstrap.
- **Implementation:** the shared generator clears all 768 shadow attributes
  to INK 0 / PAPER 0 / FLASH 0 and selects that display while bank 5 contains
  compressed input. Normal staging can occupy 6912 bytes, including its
  attributes, so clearing bank-5 attributes alone would not suffice. Forward
  shadow restoration writes the valid bitmap before revealing its attributes.
  Restore normal display/bank-7 mapping before runtime. Automatically active
  for full player layouts; no new buffer or converter flag.
- **Cost:** added startup code **20 bytes**, within existing 1024-byte PLAYER
  padding, and **16171 T = 29 + 40 + 21*767 - 5**. Native boot costs
  **3094770→3110941 / 3214643→3230814 / 3303161→3319332 T**. Runtime opcode
  delta **0 T**, disk-sector delta **0**. Video, AY and quality are unchanged.
- **Coverage:** three new unit tests, nine generic-converter tests and two
  integrated-bootstrap tests pass. Native dirty-RAM boots guard every
  staging write and all 6144 shadow bitmap writes per disk. Final RAM,
  first native/second compact frames, AY bank and both mocked disk swaps pass.
  Real Fuse/TR-DOS startup checks all 768 attributes and **91/92/94** read
  entry/return page pairs without debugger memory writes. Actual startup
  elapsed costs **19682980/19882186/20789220 T**, including ROM/disk/IRQ/ULA.
  Evidence archival and readback audit pass.
- **Decision/limits:** use this in subsequent generated disks. Keep existing
  root previews and timing evidence unchanged. This verifies complete startup
  only; it does not rerun the full movie or satisfy its video timing gates.
  No physical-drive test. Historical evidence retains original source copies.
- **Reproduction/evidence:** [design and commands](toolkit/HIDDEN_BOOTSTRAP.md),
  [native checker](toolkit/check_hidden_bootstrap.py),
  [Fuse checker](toolkit/measure_hidden_bootstrap_fuse.py),
  [summary](toolkit/hidden_bootstrap_summary.json),
  [archive](toolkit/hidden_bootstrap_evidence/manifest.json),
  [auditor](toolkit/audit_hidden_bootstrap.py).

## 2026-09-28 — automatic selection over a carried 64-frame window

- **Objective/input:** implement the user's bounded-window search instead
  of evaluating multiple complete image sets. Reuse measured candidates
  and profiles for Fast `2881667`: 4221 frames, 188 blocks, three independent
  volumes and unchanged video/AY. This is prepared-stream automation;
  integration with the generic video-file frontend remains pending.
- **Parameters/workflow:** a 64-frame / 7.68-second horizon, at most two
  local block choices, carried slot/producer/consumer/packet/schedule state,
  and reserved space for all future blocks. Initial three blocks remain
  size-first. Use 125 disk T/byte, 7 producer T/byte, measured 256-byte decode
  slices scaled by 51/50, and a four-sector capacity margin. **6198 local
  comparisons in 3.215 seconds** with cached costs; no alternative TRD builds
  or complete Fuse runs. The automatic script builds one selected set and
  performs exactly three final cold-start EOF runs.
- **CPU/size:** instruction substitutions **0 T**; decoder
  **183122436→171302085 T (-11820351)**, producer
  **11831304→12083942 T (+252638)**, combined
  **194953740→183386027 T (-11567713)**. Compressed video
  **1818909→1866452 bytes**, sectors **7106→7292**. Occupied/free sectors
  **2493/51, 2542/2, 2540/4**. Native costs exclude ROM/disk/IRQ/ULA.
- **Actual final playback:** **1186** late frames (**89/382/715**) versus
  Fast **1239**, unweighted **1149** and earlier pressure control **1105**.
  Invalid fallback intervals **665**; maximum lateness **56/214/213 fields**;
  actual maximum deviations **3970853/15174312/15103422 T**. Recovery
  **3/3, 10/11, 5/5**; disk 2 remains late at EOF. Both video gates fail.
  Summed publication span **1809713979 T**; read/seek elapsed service
  **226573372/5110379 T**, including ROM/disk/IRQ/contention. All **25326 AY
  records** remain exact at 50 Hz without gaps, duplicates or underruns.
- **Model limitation:** baseline estimates **47/179/427** late frames versus
  observed **86/404/749**; selected estimates **45/148/402** versus actual
  **89/382/715**. The model underestimates lateness and cannot pass a timing
  gate. Do not confuse cached-cost planning time with media conversion,
  native candidate measurement or the final complete playback check.
- **Coverage:** four model tests check bounded trials, capacity, carried
  partial work and recovery to original deadlines. All selected native
  blocks pass byte/overlap/cursor/protected-RAM checks and instruction-table
  sums. Dirty-RAM boot, exact prime state and mocked-ROM swap checks pass.
  All three final Fuse runs reach EOF and check all frames/AY/sectors plus
  80 pixel samples per frame. No full-screen Fuse or physical-drive test.
  The archived-evidence audit passes both write and independent readback.
- **Decision:** retain the bounded automatic mechanism as an experiment;
  calibrate windows against actual traces before another final-set run.
  It does not yet outperform the best earlier control and disk 1 regresses
  by three late frames. Root images and release remain unchanged.
- **Evidence/reproduction:** [method and commands](toolkit/WINDOWED_OPTIMIZATION.md),
  [planner](toolkit/windowed_zx0_planner.py),
  [prepared-stream runner](toolkit/optimize_prepared_player.py),
  [planning report](toolkit/windowed_tokens_plan.json),
  [final summary](toolkit/windowed_player_summary.json),
  [archive](toolkit/windowed_player_evidence/manifest.json),
  [auditor](toolkit/audit_windowed_player.py).

## 2026-09-28 — reserve-pressure control measurements and windowed-search requirement

- **Objective/input:** spend lossless ZX0 expansion where reserve depletion
  affects playback. Full `2881667` input, 4221 frames/188 blocks, compared
  with unweighted token selection at `02e08b1`.
- **Parameters:** Q8 empty-slot pressure from each block and the next two
  with 1/2 and 1/4 decay; strength 4/16, 125-T/byte charge and four-sector
  byte margin. Strength zero reproduces the old choices. No player opcode
  changes (**0 T substitution delta**) or decoded video/AY changes.
- **Results:** strength 4/16 combined native producer+decoder costs
  **176082284 / 177156271 T**, versus Fast **194953740 T** and unweighted
  **173275504 T**. Video **1880056 / 1880043 bytes**, 7344 reads; all three
  disks use 2542 sectors with two free. Late frames **1111 / 1105**, versus
  unweighted 1149; bad intervals **638 / 640**, versus 680. Publication spans
  **1809997611 / 1810068518 T**, versus 1811203044 T. These are complete
  observed runs, not matched-phase CPU attribution.
- **Timing/recovery:** maximum lateness **58/218/205** and **57/219/206
  fields**; recovery **3/3,9/10,5/5** and **3/3,8/9,5/5**. Each disk-2 run
  stays late at EOF. All 25326 AY records remain exact at 50 Hz without
  underruns/gaps/duplicates. Both video gates fail. Each missed frame and
  actual OUT deviation is retained in the comparison.
- **Coverage:** all selected blocks rerun through guarded native decoding
  and real producer with ROM mocked; instruction sums, overlap, cursor,
  output, protected RAM and sector order pass. Dirty-RAM startup and swap
  code pass. Each disk cold-boots and completes in Fuse with all frames,
  AY and sectors checked plus 80 pixel samples/frame. No hardware or full
  Fuse pixel comparison; unchanged frame code/data retain their CPU proof.
- **Correction:** initial selection stopped before writing evidence at a
  one-element `max` boundary. List-based maximum fixes the final block;
  subsequent zero-weight control and full runs pass.
- **Decision/user clarification:** keep these completed comparisons as
  control evidence. The user requires automatic optimization using a
  **sliding time window**, not repeated complete image-set evaluation.
  Carry memory/space/schedule state across windows and validate one final
  selected set through EOF. Existing root TRDs are unchanged; no release.
- **Evidence/reproduction:** [method and results](toolkit/PRESSURE_TOKEN_SELECTION.md),
  [selector](toolkit/pressure_zx0_tokens.py), [choices](toolkit/pressure_zx0_tokens.json),
  [builder](toolkit/build_pressure_token_player.py),
  [summary](toolkit/pressure_token_summary.json),
  [auditor](toolkit/summarize_pressure_token_player.py),
  [strength-4 archive](toolkit/pressure_token_evidence/weight4/manifest.json),
  [strength-16 archive](toolkit/pressure_token_evidence/weight16/manifest.json).

## 2026-09-28 — lossless Fast ZX0 token selection for faster reserve refill

- **Objective/input:** fill the existing decoded reservoir faster. Compare
  the `2881667` Fast preview across all 4221 frames / 188 blocks / three
  independently bootable disks. Decoded video and AY stay byte-exact.
- **Parameters:** per-block minimum-match thresholds 0/2/3/4/5/6/8;
  replace short references with merged literals. All 1316 candidates execute
  natively with 256-byte output demands and pass all 256 overlap placements.
  A one-block-per-volume smoke run and two existing test groups pass first.
  Select measured CPU plus a 125-T/byte disk-service heuristic under capacity,
  subtracting a four-sector byte margin. No player instructions change:
  substitution delta **0 T**, with different execution counts.
- **Size/CPU:** **1818909→1880042 bytes (+61133 / 3.361%)**, **7106→7344
  video sectors (+238)**; all disks occupy **2542 sectors, two free** after
  physical interleave. Every selected block matches its measured candidate.
  Decoder **183122436→161110234 T (-22012202 / 12.0205%)**; producer
  **11831304→12165270 T (+333966)**; combined **194953740→173275504 T
  (-21678236 / 11.1197%)**. ROM/IRQ/ULA/physical disk costs are excluded
  from those CPU totals. Carry copying remains 96256 bytes.
- **Complete Fuse outcome:** late frames **1239→1149**, per disk **87/348/714**;
  bad fallback intervals **744→680**, per disk **42/203/435**. AY remains
  exact at 50 Hz: all **25326 records**, zero underruns/gaps/duplicates.
  All frames and progress reach EOF. Summed publication span falls
  **1812124850→1811203044 T (-921806 / 0.0509%)**. Actual read service
  rises **7403381 T**, seek service **129770 T**; these elapsed measurements
  must not be added again to overlapping stage durations.
- **Recovery/reserve:** maximum lateness **65/235/214 fields**, maximum
  actual deviations **4609027/16663380/15174309 T**; recovery **2/2,
  10/11, 5/5** runs. Disk 2 remains late at EOF. Median ready bytes become
  **30243/12278/10**, near-empty packet starts **95/313/561**. Faster refill
  helps the reserve but neither nominal nor fallback video gate passes.
- **Coverage:** all selected bytes/cursors, protected RAM, overlap and native
  instruction sums; dirty-RAM boots, exact prime frames and immutable AY;
  actual disk-swap code with ROM mocked. Independent complete Fuse boots
  check every publication/sector/AY and 80 pixel samples per frame, without
  RAM patches or fast-read retries. Prior unchanged full-frame CPU proof
  remains applicable. No hardware, interactive replacement or full Fuse
  pixel comparison; initial drive/IRQ phases were not matched.
- **Decision:** retain as an optional measured experiment, not a new default
  or root preview. Disk 1 regresses by one late frame and one bad interval,
  with only two free sectors per disk. Prioritize useful reserve before hard
  runs and assess the deeper prepared-command queue separately. Existing
  root TRDs remain unchanged. No claim of smooth 8⅓-fps playback.
- **Evidence/reproduction:** [report and commands](toolkit/FAST_TOKEN_PLAYER.md),
  [candidate probe](toolkit/probe_fast_zx0_tokens.py),
  [candidate measurements](toolkit/fast_zx0_tokens_probe.json),
  [builder](toolkit/build_fast_token_player.py),
  [build proof](toolkit/fast_token_player_build.json),
  [native benchmark](toolkit/benchmark_fast_token_player.py),
  [native results](toolkit/fast_token_player_cpu.json),
  [auditor](toolkit/summarize_fast_token_player.py),
  [summary](toolkit/fast_token_player_summary.json),
  [full source/metadata/traces](toolkit/fast_token_player_evidence/manifest.json).

## 2026-09-28 — audit advance frame preparation in the current Fast reservoir

- **Objective/input:** answer whether difficult-frame changes can be prepared
  before publication. Reanalyze all 4221 frames of the `2881667` Fast preview,
  using its committed TRDs, complete archived Fuse events and prior full-frame
  CPU evidence. This is analysis, not another emulator or player run.
- **Method:** reconstruct packet/block byte positions and check every queue
  observation against slot ownership and the 47616-byte decoded capacity.
  Measure packet/compact readiness relative to original nominal deadlines.
  The two-byte Huffman cache and the larger packet reserve are kept distinct.
- **Results:** median reserve **30148/9840/4 bytes**, median available complete
  packets **50/11/0** (including the requested packet when it fits). Packet
  starts with at most six ready bytes: **99/478/740**. Compact preparation
  already finishes at least a frame period early for **1497/826/524 frames**.
  The hardest 32-frame windows on disks 2/3 request **63230/52483 bytes** and
  have **0..6 bytes** ready at every packet start. Advance work exists, but
  sustained depletion remains. Player instruction/stream deltas **0 T / 0 B**.
- **Decision:** retain advance preparation; prioritize faster refill, then
  separately assess a deeper queue of resolved patch commands. Account for
  predictor dependencies, all 128 KiB, enlarged commands and added copies.
  No changed quality, TRDs or timing claim. The hypothetical free-input
  sensitivity remains explicitly unimplemented and cannot pass a release.
- **Evidence/reproduction:** [proposal and findings](toolkit/FRAME_PREPARATION_RESERVE.md),
  [analyzer](toolkit/profile_fast_reservoir.py),
  [per-frame report](toolkit/fast_reservoir_profile.json).

## 2026-09-27 — apply adapted Fast ZX0 to all three independent disks

- **Objective/input:** integrate the unchanged-stream Fast decoder from
  `3aa3e4b` into the retained `a84451d` periodic-drive player. Full authorized
  4221-frame edit, three independent disks, existing resolution and AY data.
- **Implementation:** the new Fast builder installs exactly the measured
  401-byte core/helpers/state, remaps 22 known external instruction operands,
  updates the cold bridge overlay and verifies the producer against a fresh
  assembly. Existing buffers, queue policy and drive maintenance remain.
  All substitutions keep their absolute instruction cost, delta **0 T**.
  Ten cold-loaded queue-control paths also retain **75/109/172/96/169/302/
  562/764/808/1240 T**, excluding callee bodies.
- **CPU baseline:** installed code matches the complete 188-block Fast
  proof: **189,573,555→183,122,436 decoder T (-6,451,119 / 3.403%)**.
  Producer+decoder saving remains 3.203%; this is separate from elapsed
  playback. Code/state grows **314→401 bytes**, without shrinking buffers.
- **Compression/capacity:** all video/AY bytes and stream hashes match;
  **1,818,909 compressed bytes, 7106 video sectors**. Bootstrap changes add
  no occupied sectors: **2462/2463/2462 used, 82/81/82 free**, with unchanged
  video start sectors 107/108/109. Root `ZX-video-fast-preview_part01..03.trd`
  are the measured images, staged through Git LFS with a preview manifest.
- **Complete Fuse results:** all **4221 frames / 25326 AY records** reach
  EOF. Late frames **1321→1239**, bad fallback intervals **783→744**;
  per-volume late counts **86/404/749**, bad intervals **41/230/473**.
  AY remains exact at 50 Hz with zero underruns, record gaps or duplicates.
  Effective fps **8.333333 / 8.075773 / 8.333333**. Summed publication span
  **1,812,975,750→1,812,124,850 T (-850,900 / 0.0469%)**. This is not whole
  startup/playback time or a matched initial disk/IRQ-phase comparison.
- **Deadline recovery:** maximum lateness **62/248/244 fields**, actual
  maximum deviations **4,396,302 / 17,585,184 / 17,301,569 T**. Late runs
  recover **3/3, 13/14, 3/3**; disk 2 ends with one unrecovered run. Both
  nominal and one-field-fallback video gates still fail.
- **Coverage:** dirty-RAM cold boots, exact first native/second compact
  frames, immutable audio bank, all-block byte verification and cold-reference
  checks pass. Prompt/next-disk acceptance and wrong-disk/series rejection
  execute actual code with ROM reads mocked. Each disk also cold-boots and
  completes separately in Fuse without RAM patches or fast-read retries.
  Fuse verifies every publication, AY record and sector, plus 80 screen
  bytes per frame; the unchanged frame code retains its prior full-screen
  CPU proof. No actual interactive disk replacement or hardware run.
- **Packaging correction:** the first export refused before copying files
  because the in-memory audit used numeric dictionary keys while saved JSON
  uses strings. Normalize the audit through JSON before comparison; export
  then passed. This did not change player bytes or playback measurements.
- **Decision:** apply Fast as the next experimental baseline; retain Turbo
  for comparisons and keep the verified release. CPU gains and fewer late
  frames justify the change, but smooth 8⅓-fps playback remains unfinished.
- **Reproduction/evidence:** [integration report](toolkit/FAST_ZX0_PLAYER.md),
  [builder](toolkit/build_fast_zx0_player.py),
  [installer](toolkit/fast_zx0_player.py),
  [queue comparison](toolkit/measure_fast_zx0_queue.py),
  [build](toolkit/fast_zx0_player_build.json),
  [summary/audit](toolkit/summarize_fast_zx0_player.py),
  [saved summary](toolkit/fast_zx0_player_summary.json),
  [full source/metadata/traces](toolkit/fast_zx0_player_evidence/manifest.json),
  [preview packager](toolkit/package_fast_zx0_preview.py),
  [root image manifest](toolkit/fast_zx0_preview.json).

## 2026-09-27 — faster ZX0 prototypes preserve every compressed byte

- **Objective/input:** test whether the decoder can be accelerated without
  reducing compression after the `9f14ad9` profile. Use retained `a84451d`
  data: all 188 blocks, 2965011 decoded bytes, three independent streams,
  1818909 compressed bytes including headers and 7106 video sectors.
- **Variants:** tuned Turbo simplifies non-wrapping C000h..FDFFh boundary
  checks and synchronization. Adapt upstream spke/uniabis Fast with inline
  token-boundary suspension, no persistent IX continuation and a shared
  literal-copy entry. Keep the pinned original assembly and its notice;
  identify the altered emitter explicitly. Existing defaults are unchanged.
- **Fresh paired measurements:** 564 complete native block executions.
  Decoder CPU **189,573,555 → 187,272,946 T** for tuned Turbo
  (**-2,300,609 T / 1.214%**) and **→ 183,122,436 T** for Fast
  (**-6,451,119 T / 3.403%**). Producer cost remains **11,831,304 T**;
  Fast producer+decoder saves **3.203%**. Fast per-volume savings are
  **1,845,707 / 2,210,048 / 2,395,364 T**. Every block improves in both
  candidates. Of 11584 calls, Fast has 62 slower calls, by at most 69 T;
  tuned Turbo has no slower calls. These are CPU, not elapsed playback gains.
- **Compression/memory:** stream delta **0 bytes**, sector-read delta **0**,
  carry-copy delta **0 bytes**. Fast code/state grows **314→401 bytes**;
  tuned Turbo shrinks to **291 bytes**. Helpers/state reuse retired bank-5
  RAM, hot cores fit the existing bank-2 reservation, private stack/buffers
  are unchanged. Fast leaves three bytes before the preserved frame return.
  Bank-5 decoder instruction totals grow **2,253,636→4,530,562 T**;
  actual contention and compressed-bootstrap size are not measured.
- **Path counts:** high-byte-below-target path **31→29 T**; equal-high /
  lower-low path **56→57 T**; equal/greater-low suspend **75→74 T**;
  greater-high suspend **55→58 T**. Synchronization **139→86/112 T**
  (tuned/Fast). Absolute counts and exclusions are saved in the path probe;
  full executed histograms use Zilog timing-table validation.
- **Coverage:** four test groups pass for both variants: sector/header
  edges, bank rotation/carry/retry, 90 synthetic gamma/offset sequences,
  real AY IRQ code after every instruction, and unaligned/repeated demands
  with caller-register clobbering. Full replay verifies every output byte,
  input cursor/overlap digest, protected bank, stack and sector order.
  Saved-data audit and regenerated code match. A control-flow readability
  cleanup in the demand test was followed by rerunning that test successfully.
- **Decision/limits:** retain Fast as the leading unchanged-stream CPU
  candidate and tuned Turbo as a smaller comparison. Real TRD integration,
  absolute references/cold overlays, independent boot/swap, bootstrap
  sectors and complete Fuse nominal/fallback/AY gates remain to be tested.
  No changed TRD or physical-drive measurement; no claim of smooth 8⅓ fps.
  Preserve the current release and disk baseline.
- **Reproduction/evidence:** [report and commands](toolkit/FASTER_ZX0.md),
  [prototype emitter](toolkit/faster_zx0.py),
  [benchmark](toolkit/benchmark_faster_zx0.py),
  [tests](toolkit/test_faster_zx0.py),
  [all blocks](toolkit/faster_zx0_cpu.json),
  [summary](toolkit/faster_zx0_summary.json),
  [path probe](toolkit/probe_faster_zx0_paths.py),
  [path counts](toolkit/faster_zx0_paths.json),
  [auditor](toolkit/audit_faster_zx0.py).

## 2026-09-27 — complete instruction profiles and seven-player delivery comparison

- **Objective/input:** locate the largest CPU costs and elapsed stalls at
  repository `f701c54`. Use all 4221 authorized no-credits frames, original
  checkpoints/pixels, the retained `a84451d` TRDs and all seven archived
  complete three-volume Fuse configurations. No player code, stream, image
  or release change: deterministic instruction delta **0 T**, stream delta
  **0 bytes**. Maintain separate CPU and elapsed-time scopes.
- **Fresh frame execution:** every instruction, compact byte and both
  complete native screens match. Total **1,017,445,008 T**, mean
  **241,043.59 T**, p99 **363,553 T**, maximum **378,448 T/frame**.
  Reconstruction is **59.96%**, output **33.19%**, metadata **6.25%**.
  Dense/sparse pixel work costs **217,109,804 T**, Huffman **125,825,146 T**,
  cache filling **112,146,097 T**. Remaining indexed memory loads are
  **9,586,716 T (0.94%)**. Restore the previously proven 604233-T motion
  delta to reconstruct retained-player frame costs; this is not a second
  fresh execution or a changed TRD.
- **Fresh packet execution:** actual cold-loaded required parser/queue,
  all 4221 exact packets and 7106 mocked sector reads, every payload byte
  written once. Total **340,877,648 T**, including ZX0 **190,422,888 T**,
  packet copying **50,177,846 T**, queue control **11,366,156 T** and
  metadata **63,590,055 T**. Metadata is shared with the frame fixture and
  must not be added twice. The frozen-clock, no-prefill workload excludes
  real disk latency, ULA and ongoing AY/IRQ consumption.
- **New bottleneck detail:** ZX0 LDIR transfers are only **58,959,456 T**
  (30.96% of decoder cost); remaining parsing/setup/boundary work is
  **131,463,432 T**. Match/literal runs average **4.2901/4.8065 bytes**.
  Packet copying already uses unrolled LDI, **16 T × 2965011 bytes**.
  Prioritize short-run decoding and sustained delivery before assuming
  long-copy unrolling or small register substitutions will solve cadence.
- **Elapsed comparison:** re-audit complete archived playback, not new
  Fuse runs. Disjoint retained-player publication contexts total
  **1,812,975,750 T**: reconstruction 35.69%, output 19.07%, disk service
  11.85%, transfer outside disk 9.94%, metadata 4.33%, unclassified
  background/control/wait 19.13%. Do not label the last bin entirely idle.
  Suspended transfers in resumable variants overlap other frame stages;
  the new sweep excludes that duplication. Peak packet transfer is
  **1,884,022 T (~531.4 ms)** against a nominal 120-ms frame period.
- **Coverage/decision:** all per-instruction/stage/frame sums and earlier
  256-packet prefixes agree; three-volume CPU replay and saved-data audit
  pass. Seven configurations retain exact 50-Hz AY; all fail both video
  gates. Fast fragments have the fewest late frames, **1237**, but add
  151 sector reads and worsen disk 1's peak. Keep the retained baseline,
  current release and disabled experimental options unchanged. Next target
  short-run ZX0/input delivery, pixel conversion and cache/Huffman paths;
  instrument background/audio/wait entry/exit to resolve the remaining
  elapsed bin. Physical drives and new playback are unmeasured.
- **Reproduction/evidence:** [report and commands](toolkit/PLAYER_PROFILING.md),
  [updated plan](toolkit/DECODE_SPEED_PLAN.md),
  [frame profiler](toolkit/profile_current_frame.py),
  [frame report](toolkit/current_frame_profile.json),
  [packet profiler](toolkit/profile_packet_cpu.py),
  [packet report](toolkit/packet_cpu_profile.json),
  [comparison/auditor](toolkit/profile_player_comparison.py),
  [comparison report](toolkit/player_comparison_profile.json).

## 2026-09-27 — direct alternate-HL motion target loads confirmed in CPU tests

- **Objective/input:** verify the planned 45-to-24-T pointer setup against
  repository `5856133` and the complete two-byte Huffman-cache CPU baseline.
  Use all 4221 authorized no-credits frames, original three table sets/raw
  inputs and saved states. Compressed movie-stream delta is **0 bytes**.
- **Change:** move the common `LD HL,(target)` into phase zero; use
  `EXX; LD HL,(target); EXX` for phases 2/4/6. Save **21 T/entry**;
  phase zero/clear paths have **0 T delta**. Add **3 bytes** of fixed code,
  relocate the affected code/state references, and remove the two-byte
  temporary stack transfer. No buffer, dictionary or new state allocation.
- **Measured result:** **28,773** entries; setup **1,294,785→690,552 T**.
  All frame stages total **1,018,049,241→1,017,445,008 T**, a saving of
  **604,233 T (0.059352%)**. Per-volume savings: **283,542 / 173,712 /
  146,979 T**. There are **3352 faster frames**, maximum **819 T/frame**,
  and **zero slower frames**. The earlier executed motion histogram agrees.
- **Coverage:** five specialized tests pass, including 1312 paired
  vector/position cases, mixed complete frames, real AY IRQs after each
  instruction, and both publication IRQ handlers at every new setup
  boundary. Full movie CPU execution checks exact compact data, both
  complete native screens, input/cursors/paging and every frame's delta.
  The saved-report auditor passes; instruction costs were checked against
  Zilog UM008011-0816. No changed TRD or full Fuse run was made.
- **Corrections during verification:** an initial test import was fixed;
  an overstrict register comparison exposed that primary HL differs after
  phases 2/6. It is dead at current callers, which immediately reload it;
  the prototype now rejects an unverified caller contract. The standalone
  evidence auditor initially imported an unnecessary OpenCV dependency;
  it now uses standard-library SHA-256 and runs without conversion packages.
- **Decision:** hypothesis confirmed; retain as an optional CPU prototype.
  Reconstruction ends at **8FBBh**, five bytes below the lookahead helper.
  Disk integration must move bank-2 ZX0's reused region to
  **8DF5h..8F0Ch**, rebuild references/boot metadata, measure compressed
  bootstrap size and verify independent boot plus complete delivery.
  IRQ cadence, ULA, ROM/physical disk latency and actual publication timing
  are outside the CPU result. The retained disk baseline/release is unchanged.
- **Reproduction/evidence:** [implementation and commands](toolkit/DIRECT_MOTION_TARGET.md),
  [benchmark](toolkit/benchmark_direct_motion_target.py),
  [tests](toolkit/test_direct_motion_target.py),
  [frame report](toolkit/direct_motion_target_cpu.json),
  [auditor](toolkit/audit_direct_motion_target.py),
  [summary](toolkit/direct_motion_target_summary.json).

## 2026-09-27 — complete reservoir traces identify sustained input depletion

- **Objective/input:** identify why the retained `a84451d` player remains
  late after read-ahead routing experiments. Reuse all 4221 frames/25326 AY
  records of archived playback and exact current video blocks. No runtime
  code, stream or pixel change; player instruction delta **0 T**.
- **Method:** independently reconstruct absolute packet positions, completed
  blocks and active decoded prefixes. All packet starts agree with traced
  queue count, slot ownership, cursor and the 47616-byte capacity. Keep
  deterministic frame CPU separate from elapsed stages and disk service.
- **Results:** median decoded reserve is **30092/9263/4 bytes**; starts with
  at most six bytes ready are **104/509/757**. Worst 32-frame work windows
  **642..674 / 2870..2902 / 3887..3919** (exclusive ends) exceed their
  13,614,336-T budget by **4,270,251/10,322,669/9,303,856 T**. Transfer
  contributes **7,190,928/12,706,585/11,643,401 T**, including disk service
  **2,667,757/4,877,724/4,886,539 T**. The last two windows have no completed
  slot at any packet start and at most six decoded bytes ready.
- **Decision:** target sustained acquisition/decode/copy cost and useful
  advance work. Revisit faster ZX0 tokenizations with the new 82/81/82-sector
  headroom; the old adaptive test had only 275/58/746 spare bytes. Measure
  native CPU/overlap, extra sectors and full selected delivery before adoption.
  A frozen-duration projection with free input has zero late frames, but is
  explicitly hypothetical and proves no release or feasible schedule.
- **Coverage/limitations:** full saved trace/packet coverage; physical drives
  and changed playback remain unverified. The first analysis rejected the
  resident packet minimum using an old 294-byte mux assumption; it now reads
  the actual 288-byte contract from metadata. See [analysis](toolkit/LATE_RESERVOIR.md),
  [reproducer/auditor](toolkit/profile_late_reservoir.py) and
  [all frame/block results](toolkit/late_reservoir_profile.json).

## 2026-09-27 — separate optional consumer removes global checks but still misses cadence

- **Objective/baseline:** remove mandatory queue overhead from `25780a9`
  while preserving resumable read-ahead. Compare with retained `a84451d`,
  all 4221 authorized frames and 25326 AY records, unchanged pixels/audio.
- **Implementation:** duplicate the consumer in unused bank 7, sharing
  existing queue state and bridges. A 324-byte F900..FA43 helper replaces
  162 bytes; no extra stack or data buffer. Required consumer opcodes are
  unchanged. Optional calls yield at existing sector/256-byte ZX0 boundaries;
  parser dispatch occurs per length/body transfer. No dynamic code routing.
  Host builds now reuse checked SHA-keyed ZX0 caches. Deadlines/AY unchanged.
- **Capacity/content:** three independent TRDs, **2462/2463/2462 sectors**,
  **82/81/82 free**, video starts **107/109/110**. Video **1,818,909 bytes /
  188 blocks / 7106 reads**, identical to baseline; all video/AY hashes match.
  Dirty-RAM boots, initial full native/compact frames and both swaps pass.
- **CPU:** required count read **13 -> 13 T**, demand jump **10 -> 10 T**;
  optional gate **13 -> 40 T**, down from global-gate 94 T. Transfer selector
  costs 27/37 T required/optional; direct fresh parser overhead is **245 T**
  per packet, plus separately measured placement effects **0/-92/-113 T**
  in the first 256 packets/volume. Required prefixes save **78,192/86,265/
  98,955 T** against global gating; forced-resume saves **97,280/105,054/
  128,555 T**. Exact packet bytes and single writes pass through 584 forced
  pauses; split-header/EOF and IRQ cases pass **4976 AY-handler injections**.
  These are prefix CPU counts with mocked ROM, excluding IRQ/ULA latency.
- **Full Fuse:** all volumes reach EOF, all AY records exact at 50 Hz,
  zero underruns, IRQ gaps/duplicates or read retries. Late frames
  **89/474/766 = 1329**, versus original 1321/global-gate 1337. Bad intervals
  **45/254/491 = 790**, versus 783/797. Maximum lateness **64/263/269 fields**,
  actual OUT deviation **4,538,121/18,648,804/19,074,250 T**. Recovered runs
  **2/10/3**, volume 2 unrecovered at local **1237..1296**. Publication span
  **1,813,188,468 T**, 212,724 better than global gating, 212,718 worse than
  original. Both video timing gates fail. Traces verify 35 earlier draws;
  those response intervals are not exclusive CPU savings.
- **Decision:** retain as an experiment; do not enable by default. Required
  overhead removal works but does not establish smooth delivery. Next work
  must reduce or prepare the difficult-scene workload. No root release or
  converter default changes. Fuse samples 80 screen bytes/frame; physical
  disks, complete integrated CPU and matched initial disk/IRQ phases remain
  unverified. The first auditor stopped because old evidence had no TRDs;
  it now archives verified baseline bank-7 payloads and checks original and
  cloned opcodes directly. No player/test rerun was needed for that fix.
- **Evidence:** [report and commands](toolkit/OPTIONAL_PACKET.md),
  [implementation](toolkit/optional_packet_player.py),
  [builder](toolkit/build_optional_packet.py), [CPU test](toolkit/test_optional_packet.py),
  [auditor](toolkit/summarize_optional_packet.py), [summary](toolkit/optional_packet_summary.json).
  All 51 archived files are hash-checked; three experimental `.trd.gz`
  images use Git LFS. This is a verified experiment, not a verified release.

## 2026-09-27 — resumable optional packet reads preserve size but worsen cadence

- **Objective/baseline:** remove read-ahead calls that keep a prepared compact
  frame waiting after screen publication. Compare with `a84451d`, all 4221
  authorized frames, resident AY and three 15872-byte in-place ZX0 slots.
- **Implementation:** a 162-byte bank-7 helper at F900..F9A1 includes two
  parser state bytes. Optional reads yield at queue boundaries and resume
  the same length/body; required reads retain demand decoding. Optional
  reads consume available output or one 256-byte decode/input quantum.
  No extra packet/frame buffer, repeated prefix copy or private stack;
  the gate uses two extra stack bytes. Screen deadlines and AY IRQ unchanged.
- **Capacity/content:** compressed video **1,818,909 B**, 188 blocks and
  **7106 reads**, all byte-identical to the baseline. AY hashes also match.
  Occupied sectors remain **2462/2463/2462**, free **82/81/82**. Video starts
  at **107/109/110**, versus **107/108/109**. Dirty-RAM boots, initial complete
  native/compact frames, resident audio and both disk swaps pass.
- **CPU verification:** first 256 packets per volume in baseline, required
  and forced-resume modes; 584 forced pauses across 768 packets. All packet
  bytes are exact and written once, including continuation after register
  clobber. Additional real-IRQ and split-length/final-slot cases pass, with
  **4066 IRQ injections**. Required CPU totals: **15,749,661 -> 15,890,573 /
  19,024,975 -> 19,173,868 / 27,631,846 -> 27,793,408 T**. The instruction
  formula matches each prefix, separately accounting for **0/-92/-113 T**
  of producer/disk CPU changes due to placement. Queue count read **13 ->
  67 T (+54)** in required mode and **13 -> 94 T (+81)** in optional mode;
  required demand dispatch **10 -> 37 T (+27)**. This is prefix CPU evidence,
  with mocked ROM and excluding IRQ/ULA/physical latency, not full-movie CPU.
- **Complete Fuse:** all disks reach EOF; all **25326 AY records** remain
  exact at 50 Hz, zero underruns, IRQ gaps/duplicates or read retries.
  Late frames **89/481/767 = 1337**, versus 1321; invalid intervals
  **43/261/493 = 797**, versus 783. Maximum lateness **64/266/271 fields**,
  actual OUT deviation **4,538,126/18,861,528/19,216,070 T**. Recovered runs
  **2/11/3**, volume 2 unrecovered at local frames **1237..1296**. Summed
  publication span **1,813,401,192 T (+425,442)**. Both video gates fail.
- **Scheduling evidence/decision:** 33 native draws start before the
  interrupted packet finishes. This responsiveness improvement does not
  translate to sustained playback: late counts and total span worsen.
  **Keep experimental; do not enable by default.** A next variant must
  remove checks from mandatory reads and count optional setup/restoration.
  Root releases and converter defaults stay unchanged. Fuse checks 80
  pixels/frame, not complete screens; physical hardware and matched initial
  disk/IRQ phases remain unverified. Suspended transfer intervals overlap
  other drawing and must not be summed as exclusive CPU work.
- **Incomplete attempts and audit:** initial test runs exposed a stale
  relocated instruction listing and missing SCF support in the Python CPU;
  both failure reports are saved. A later test reached disk 3 before its
  build finished, exited on FileNotFoundError, and retained completed cases.
  The resume script executed only missing cases; the audit checks unchanged
  prior results. No player change was needed for these instrumentation
  fixes. The completed archive verifies actual bootstrap helper bytes,
  compressed streams, source/report hashes and complete traces. Experimental
  `.trd.gz` evidence images are in Git LFS. See [report and commands](toolkit/RESUMABLE_PACKET.md),
  [implementation](toolkit/resumable_packet_player.py),
  [builder](toolkit/build_resumable_packet.py), [tests](toolkit/test_resumable_packet.py),
  [resume script](toolkit/resume_resumable_packet_tests.py),
  [auditor](toolkit/summarize_resumable_packet.py), and
  [complete summary](toolkit/resumable_packet_summary.json).

## 2026-09-27 — CPU-optimal native masks fit but do not improve total delivery

- **Objective/baseline:** remeasure the older capacity-rejected `gray_optimal`
  native-map rule with `a84451d`, resident AY and 15872-byte in-place ZX0
  blocks. All 4221 authorized frames, resolution, pixel values, AY records,
  25/3-fps deadlines and independently bootable volumes are retained.
- **Parameters:** choose existing exact sparse or full output on the host.
  Variable band cost is **5853 + 4*parity T** for full output versus
  **261*marked_cells - 136*zero_groups T** for sparse output. No new Z80
  instruction, dispatch test or memory allocation. Change only native-map
  bytes: 9126 bands in 2230 frames; all other packet fields invert exactly.
  The four later-volume cold maps retain their mandatory full redraw.
- **Capacity:** all 188 blocks round-trip and satisfy sector-aligned in-place
  safety. ZX0 grows **1,818,909 -> 1,846,953 B (+28,044)**, reads **7106 ->
  7216 (+110)**. Actual occupied sectors **2495/2506/2496**, free **49/38/48**.
  Total occupied growth is also 110 sectors, after bootstrap/placement changes.
- **CPU evidence:** all 4221 compact frames and both full native screens
  match. Each delta matches the output formula and historical projection,
  adjusted for independent cold maps. Frame stages **1,018,049,241 ->
  1,011,675,434 T (-6,373,807)**; no slower frame-stage cases. Producer/ZX0
  **201,404,859 -> 203,179,328 T (+1,774,469)**. Measured components save
  **4,599,338 T (~0.377%)**, excluding queue/AY/IRQ/ULA/ROM/disk elapsed time.
  The 481 baseline over-budget frames save 1,247,998 frame T, versus
  5,125,809 T on the other 3740. Histograms/instruction timings are checked.
- **Complete Fuse result:** every volume reaches EOF, all 25326 AY records
  remain exact at 50 Hz, zero underruns, missing/duplicate IRQ fields or
  read retries. Late frames **87/420/761 = 1268**, versus 1321; invalid
  intervals **41/238/482 = 761**, versus 783. Maximum lateness **63/262/261
  fields**, actual deviation **4,467,209/18,577,896/18,506,994 T**. Recovered
  runs **2/12/4**, with volume 2's unrecovered tail at local frames 1239..1296.
  Total publication span **1,813,117,560 T (+141,810)**. Both video gates fail.
- **Coverage/decision:** three focused tests, dirty-RAM boots, initial frames,
  immutable AY, both swaps, full native frame/block execution and all Fuse
  traces. Fuse samples 80 pixels/frame; physical hardware is untested and
  initial disk/IRQ phases are not matched. The self-contained archive audit
  passes with 81 gzip files, full source pixel/AY replay and exact inverses.
  **Do not adopt the global mask policy:** extra sectors and worse total
  span/volume-2 maximum deviation outweigh this small CPU saving. Preserve
  the roomier baseline and separate fragment candidate; release/defaults stay
  unchanged. The old capacity rejection is superseded, not erased.
- **Next delivery question:** trace analysis finds 64 baseline optional
  packet reads spanning publication while the following compact frame is
  prepared; 16 are followed by a late frame, maximum transfer tail 1,542,815 T.
  The mask variant has 63/12 calls and maximum 1,519,170 T. These are blocking
  observations, not saved CPU. Plan a resumable optional reader at safe
  sector/ZX0/copy boundaries, preserving partial packets, queue ownership,
  original deadlines and exact mandatory-read completion. It is not implemented.
  See [report and commands](toolkit/NATIVE_MASK_SELECTION.md),
  [rewriter](toolkit/native_mask_selection.py),
  [probe](toolkit/probe_native_mask_selection.py),
  [tests](toolkit/test_native_mask_selection.py),
  [builder](toolkit/build_native_mask_selection.py),
  [archive/trace audit](toolkit/summarize_native_mask_selection.py), and
  [complete results](toolkit/native_mask_selection_summary.json).

## 2026-09-27 — cost-selected fragments fit the current three-disk layout

- **Objective/baseline:** revisit the September 25 capacity-rejected selector
  using retained player `a84451d`, resident AY and 15872-byte in-place ZX0
  blocks. Cover all 4221 authorized frames, unchanged pixels/resolution/AY,
  25/3-fps deadlines and independent boot on all three disks.
- **Parameters:** existing fragment modes 85..88, local allowance 64 bits,
  estimated gain at least 400 T; 16051 tiles in 3261 frames selected. The
  historical 150-T/symbol heuristic is not a bound for today's 134-T short
  decoder. No player opcode template or RAM allocation changes. Volume 3
  reproduces the old allowance-64 raw candidate byte-for-byte.
- **Capacity/content:** complete scalar video/AY replay and 193 exact,
  in-place-safe ZX0 blocks. Raw video grows 67125 B; final ZX0 grows
  **1,818,909 -> 1,857,591 B (+38,682)**. Reads **7106 -> 7257 (+151)**.
  Actual occupied sectors **2525/2510/2507**, free **19/34/37**; total
  occupied growth is 155 sectors including bootstrap/layout effects.
- **CPU evidence:** all 4221 compact frames and both complete native screens
  match; no frame-stage regression. Frame stages **1,018,049,241 ->
  988,604,338 T (-29,444,903)**. Producer/ZX0 **201,404,859 -> 213,186,508 T
  (+11,781,649)**; measured components together save **17,663,254 T (~1.45%)**.
  Instruction timing/histograms are checked; these totals exclude integrated
  queue/AY/IRQ/ULA/ROM/disk time. The 481 baseline over-budget frames save
  **3,444,876 frame T**; the other 3740 save **26,000,027 T**.
- **Complete Fuse result:** all three disks reach EOF; all 25326 AY records
  match at 50 Hz, with zero underruns, missing/duplicate IRQ fields or retries.
  Late frames **73/432/732 = 1237**, versus 1321; invalid intervals
  **36/239/472 = 747**, versus 783. Maximum lateness **72/247/238 fields**;
  actual deviations **5,105,374/17,514,276/16,876,119 T**. Recovered runs
  **2/8/4**; volume 2 has an unrecovered tail at local frames 1238..1296.
  Total publication span **1,812,053,940 T (-921,810)**. Volume 1's maximum
  deviation worsens despite fewer late frames. Both video gates still fail.
- **Verification/decision:** dirty-RAM boots, initial frames, immutable AY,
  both disk swaps, native block/frame execution and full Fuse traces pass
  their content checks; Fuse samples 80 pixels/frame, not all pixels.
  Physical hardware is untested and initial disk/IRQ phases are not matched.
  The first build/frame processes disappeared for an unknown reason; their
  incomplete reports were saved before replay, and the 101-frame prefix
  matches exactly. The self-contained archive audit passes with 82 gzip files.
  Keep this as a measured optional data variant and retain the roomier
  `a84451d` comparison; release TRDs and converter defaults are unchanged.
  Next compare exact sparse/full native masks chosen by the host, including
  final ZX0 sectors and expensive delivery windows. Large block-acquisition
  bursts remain; neither aggregate CPU savings nor publication waits alone
  establish the requested smooth cadence.
  See [report and reproduction](toolkit/RESIDENT_FRAGMENTS.md),
  [selector probe](toolkit/probe_resident_fragments.py),
  [frame CPU](toolkit/benchmark_resident_fragments.py),
  [delivery CPU](toolkit/benchmark_resident_delivery.py),
  [builder](toolkit/build_resident_fragments.py),
  [archive audit](toolkit/summarize_resident_fragments.py), and
  [saved results](toolkit/resident_fragments_summary.json).

## 2026-09-27 — positional no-op tags save CPU mainly on already-fast frames

- **Objective/baseline:** remove repeated unchanged-tile scanning from the
  retained `a84451d` player, using its larger remaining capacity. Preserve
  all 4221 authorized frames, every pixel, resolution, original AY records,
  25/3-fps deadlines and three independent boots. This revisits September
  19's older FAP5 experiment under explicitly changed dispatch/buffer limits.
- **Parameters:** tag maximal interior runs of at least four tiles, keeping
  vector positions, masks and packet lengths. Exclude the static edge stripes.
  A 44-byte helper at 7C31 reuses the fast-fragment CALL, adding no test on
  ordinary motion/intra tiles. Existing fragments add **17 T**. Tagged runs
  take **308/318 T**, versus **74*k+192 / 74*k+258 T** for stripe-end/continue
  cases. Sixteen tiles to stripe end cost **1376 -> 308 T (-1068)**. Other
  thresholds are host CPU estimates only; minimum four is fully measured.
- **Capacity/content:** exact inverse for every original video packet and
  unchanged AY. All 188 blocks pass ZX0 and in-place overlap checks. Video
  grows **1,818,909 -> 1,862,543 B (+43,634)**; reads **7106 -> 7278 (+172)**.
  Actual TRDs use **2537/2512/2512 sectors**, leaving **7/32/32**. Bootstrap
  and layout make occupied-sector growth 174. Root release images are unchanged.
- **CPU evidence:** all 4221 compact frames and both complete native screens
  match. Frame stages **1,018,049,241 -> 1,004,328,597 T (-13,720,644)**;
  producer/ZX0 **201,404,859 -> 207,760,466 T (+6,355,607)**, with separately
  checked instruction histograms. Combined measured components save
  **7,365,037 T (about 0.604%)**; this excludes integrated queue/IRQ/ULA/ROM
  and physical disk time. Critically, the **481 baseline over-budget frames
  add 173,339 frame-stage T**; the other 3740 save 13,893,983 T. In all,
  573 frames get slower. Grouping uses baseline elapsed foreground work.
- **Complete Fuse result:** all three disks reach EOF; 25326 exact AY records
  retain 50 Hz, with zero underruns, missing/duplicate IRQ fields or retries.
  Late frames **90/465/760 = 1315 versus 1321**; bad intervals **44/252/490 =
  786 versus 783**. Maximum lateness **67/259/259 fields**; actual deviations
  **4,750,839/18,365,172/18,365,173 T**. Recovered runs **2/10/4**; volume 2
  retains an unrecovered tail at local frames 1240..1296. Total publication
  span falls only **70,914 T**. Both video timing gates still fail.
- **Coverage/decision:** four boundary/mixed-frame/actual-IRQ tests, full
  native frame and block execution, dirty-RAM boots, priming, handoffs and
  full Fuse traces with 80 pixels/frame. Physical hardware and all-pixel Fuse
  comparison remain unverified; initial disk/IRQ phases are not matched.
  Development checks caught an unsupported verifier JP P opcode, synthetic
  cache/RAM fixture setup, omitted cold maps in the first host probe and an
  FPS-string audit comparison; each was corrected before final evidence.
  **Do not adopt**: negligible deadline benefit, worse fallback intervals,
  and substantially less disk headroom. Retain `a84451d`. Next remeasure
  the previously capacity-rejected fast-fragment selection against today's
  block/layout budget, prioritizing expensive frames and final ZX0 size.
  See [report and commands](toolkit/TAGGED_NOOP_RUNS.md),
  [CPU benchmark](toolkit/benchmark_tagged_noop_runs.py),
  [producer benchmark](toolkit/benchmark_tagged_noop_delivery.py),
  [size probe](toolkit/probe_tagged_noop_runs.py) and
  [complete evidence audit](toolkit/summarize_tagged_noop_runs.py).

## 2026-09-27 — sector-streaming in-place ZX0 is exact but slower overall

- **Objective/baseline:** remove full-block acquisition bursts from `a84451d`
  while preserving all 4221 authorized frames, resolution, exact video/AY
  payloads, 25/3-fps deadlines and three independent boots.
- **Parameters/implementation:** reuse the input-page-suspending ZX0 core
  with C000 output and the same 15872-byte blocks in banks 0/1/3. Add a
  49-byte prefix wrapper; decoder grows 314 -> 462 bytes. Queue phase 3
  supplies a missing sector, and explicit EOF governs release. Preserve
  three-slot rotation, all AY/drive hooks and cold bridge overlays. Check
  loaded-input limits, every output byte, and future-sector overwrite safety.
- **CPU evidence:** all 188 paired blocks match. Producer **11,831,304 ->
  12,970,065 T**; decoder **189,573,555 -> 208,485,649 T**; combined
  **201,404,859 -> 221,455,714 T (+20,050,855, about 9.96%)**. Both read
  7106 sectors and copy 96256 carry bytes. All blocks produce early output;
  6915 input waits occur. Instruction-table histograms and isolated actual
  queue-control paths are measured separately; no full integrated CPU total
  is claimed. The final measurement uses actual old/new disk starts.
- **Full Fuse result:** 91/532/834 late frames, **1457 total versus 1321**;
  bad fallback intervals **943 versus 783**. All 25326 AY records meet 50 Hz,
  with zero underruns, missing/duplicate record fields or read retries.
  Maximum lateness is 63/306/345 fields, with 2/8/2 recovered runs; disks
  1/2 have unrecovered tails. Actual publication span rises by **3,687,220 T**.
  Every disk reaches EOF. Occupancy remains 2462/2463/2462 sectors; video
  remains 1,818,909 bytes. Neither video timing gate passes.
- **Coverage/decision:** five boundary/IRQ tests, every full native block,
  dirty-RAM boots, first full native/second compact frames, handoffs and
  complete Fuse traces with 80 pixels/frame. Physical hardware and an
  all-pixel Fuse run are unverified. An initial synthetic test-only wait-count
  expectation was corrected; no decoding mismatch occurred. Smaller peak
  transfer stalls do not offset the sustained CPU overhead. **Reject as the
  default**, retain `a84451d` as the experimental baseline and preserve the
  implementation/evidence for a cheaper future input guard. Root release
  images stay unchanged. See [report and commands](toolkit/INPLACE_STREAMING.md),
  [native benchmark](toolkit/benchmark_inplace_streaming.py),
  [queue measurements](toolkit/measure_inplace_streaming_queue.py) and
  [full evidence audit](toolkit/summarize_inplace_streaming.py).

## 2026-09-27 — periodic drive maintenance restores 50-Hz AY delivery

- **Objective/baseline:** remove the remaining idle-drive delays from the
  larger-slot player at `1d3ac46`. Keep all 4221 authorized frames, resolution,
  25/3-fps deadlines, exact video/AY packets and independent volume boots.
- **Parameters/implementation:** check the shared 16-bit service clock at
  five queue/foreground/audio-drain checkpoints. At 64 fields, issue the
  existing ROM 5.03 SEEK/HLD for the current cached cylinder; do not read a
  sector or advance stream/side/slot state. Preserve both register sets,
  main registers, paging, stack and IRQ contract. Reuse 115 bytes at 7E70
  and a six-byte bank-7 wrapper; allocate no new state or video buffer.
  Existing pre-read recovery remains. All five CALL patches cost 17 -> 17 T.
- **CPU costs:** new helper paths (including RET, excluding ROM/IRQ/ULA)
  are **252/709/709/688/158/128 T** for recent/due/wrap/long/uninitialized-or-
  invalidated/EOF cases. Including the extra wrapper they add
  **279/736/736/715/185/155 T** over the previous zero periodic-check cost.
  Per-instruction histograms are saved. Skipped-hook frequency is not
  replayed, so a complete integrated-player CPU delta is not claimed.
- **Capacity/content:** video remains **1818909 B / 7106 runtime sectors**.
  Actual disks use **2462/2463/2462 sectors**, leaving **82/81/82**; disk 1
  gains one occupied sector from bootstrap/placement changes. All video and
  AY bytes match the previous attempt exactly.
- **Complete Fuse result:** **zero AY underruns**, zero record-field gaps or
  duplicates, zero missing/duplicate IRQ fields and zero direct-read retries.
  All **25326 AY records pass 50-Hz delivery**. Maximum sector-read time is
  **155717/155736/155756 T** (about 43.9 ms), versus the previous 2259050-T
  maximum. **69/60/56 maintenance calls**, 185 total, consume **76670 elapsed
  ROM-service T** across all disks, separate from their CPU wrappers.
- **Video timing:** late frames **137/553/806 -> 90/465/766**, total
  **1496 -> 1321 (-175)**; invalid intervals **914 -> 783 (-131)**. Effective
  fps **8.333333/8.063713/8.333333**. Summed publication span changes
  **1815953880 -> 1812975750 T (-2978130)**. Maximum lateness remains
  **64/260/265 fields**; actual OUT deviations are **4538116/18436083/18790630
  T**. Recovered runs **3/15/3**; disk 2 ends unrecovered at local frames
  1238..1296. All missed frames and recoveries are saved. Both video gates
  fail; initial disk/IRQ phases were not matched.
- **Verification:** three tests cover all 160 current tracks, a different
  next track, threshold/wrap/long idle/EOF, adversarial ROM register clobber
  and real AY IRQ after every maintenance instruction. All three dirty-RAM
  boots, first full native/second compact frames, soundtrack immutability,
  both swaps and wrong-volume/series rejection pass. Full Fuse EOF runs
  verify all frames (80 screen bytes each), all AY writes/sectors/progress
  and actual publication/IRQ timing. Prior full-byte frame/block CPU evidence
  is reused for unchanged code/data. Physical hardware remains untested.
- **Decision/next:** retain the maintenance hook for the larger-slot
  experiment, keeping root releases unchanged. Remaining packet transfers
  reach about 1.9 million T with short individual reads; investigate block
  acquisition and reserve scheduling next, including safely consuming input
  before a whole compressed block arrives. Preserve overlap/AY correctness
  and compare against the earlier streaming-input regression.
- **Evidence:** [implementation and reproduction](toolkit/INPLACE_KEEPALIVE.md),
  [native CPU cases](toolkit/inplace_keepalive_cpu.json),
  [build](toolkit/inplace_keepalive_build.json),
  [full comparison](toolkit/inplace_keepalive_summary.json),
  [saved sources and complete traces](toolkit/inplace_keepalive_evidence/manifest.json),
  [auditor](toolkit/summarize_inplace_keepalive.py).

## 2026-09-27 — integrate larger ZX0 slots and measure idle-drive limits

- **Objective/baseline:** turn the `1ab9c2c` overlap proof into an actual
  player using the smaller foreground resident-AY baseline at `da369e6`.
  Retain all 4221 authorized frames, resolution, video packets, 25326 AY
  records and independent boots. Increase prepared-packet capacity without
  a full compressed-block copy or reduced frame rate.
- **Implementation:** 15872-byte output/history slots at C000 in banks
  0/1/3; total **24576 -> 47616 bytes**. Read split headers through BC00,
  top-align body sectors, save the shared final sector before overlap,
  retain history until EOF/consumption, and update six queue constants and
  four bridge calls. Corrected the earlier adapter assumption: only the old
  producer enforces E000; disk-region advance occurs at FFFF/0000.
- **Actual capacity:** video **1832196 -> 1818909 B**, reads **7158 -> 7106**,
  188 blocks. New independently bootable disks use **2461/2463/2462 sectors**,
  leaving **83/81/82**. Every decoded video and AY byte matches the baseline.
  This replaces the earlier conditional capacity estimate with actual builds.
- **First complete attempt, rejected:** larger reserves create longer idle
  gaps. There are **10/4/1 failed direct reads**, fallback waits up to about
  1.50 seconds, **170/68/14 AY underruns**, **436/616/762 late frames** and
  **229/337/491 invalid intervals**. Full source/build/TRD-metadata and Fuse
  traces are preserved under `inplace_slot_evidence/initial`. A build-wrapper
  source-hash collection error was corrected and the full build checks rerun.
- **Second complete attempt:** a 16-bit 64-field pre-read idle check forces
  cached SEEK/HLD, preserving the special uninitialized-drive path. Read
  retries fall to **zero**, but successful reads still reach about 0.64 s.
  Late frames become **137/553/806 (1496 total, baseline 1745)**; invalid
  intervals **87/293/534 (914, baseline 1047)**. AY underruns remain **12/0/12**.
  All records are exact, but 24 record-field gaps fail AY cadence. IRQ fields
  have no missing/duplicates. Effective fps is **8.333333/8.021788/8.333333**;
  maximum lateness **68/302/291 fields**. Recovered runs **8/10/6**; disk 2
  has an unrecovered final run at local frames 1016..1296. Both timing gates
  fail; all missed frames and actual OUT deviations are retained.
- **CPU/memory:** producer **12248310 -> 11831396 T (-416914)**; resumable
  ZX0 **187756600 -> 189573555 T (+1816955)**; combined measured stages
  **200004910 -> 201404951 T (+1400041, 0.700%)**. These are all-block,
  fixed-256-byte-quota counts with the idle clock frozen, separate from
  ROM/IRQ/ULA/physical latency and actual queue behavior. Carry copying falls
  **185088 -> 96256 B**. Final producer is **468 versus 368 bytes (+100)** in
  existing retired space. All eleven operand substitutions retain T-states.
  Added idle-check paths cost **128/177/161/153 T** including CALL; absolute
  instruction listings and assumptions are saved.
- **Verification:** six boundary/IRQ tests; all 364 old and 188 new blocks
  execute with exact input/output traces and protected banks; dirty-RAM boots,
  complete first native/second compact frames, resident-audio immutability,
  wrong-disk/series rejection and both swaps pass. Both Fuse attempts cover
  complete EOF on all three disks, all AY records and sector order, 80 screen
  bytes per frame, progress, IRQ and actual publication timing. The unchanged
  renderer reuses prior full-frame CPU evidence; this is not full-screen Fuse
  comparison or physical-drive verification.
- **Decision:** retain the optional larger reservoir for further work;
  keep the root release unchanged. Add periodic SEEK/HLD while the queue is
  full, before drive shutdown, then repeat full playback. Pre-read recovery
  alone is insufficient; neither attempt qualifies as an accepted release.
- **Evidence/reproduction:** [implementation, costs and commands](toolkit/INPLACE_SLOT_PLAYER.md),
  [native benchmark](toolkit/benchmark_inplace_slot.py),
  [build](toolkit/inplace_slot_player_build.json),
  [CPU report](toolkit/inplace_slot_cpu.json),
  [audited full comparison](toolkit/inplace_slot_summary.json),
  [auditor](toolkit/summarize_inplace_slot.py), and
  [updated plan](toolkit/DECODE_SPEED_PLAN.md).

## 2026-09-27 — in-place ZX0: prove a larger decoded-packet reservoir

- **Objective/baseline:** investigate a larger prepared-video reserve in the
  three resident-AY banks without another full compressed-input copy. Use
  the foreground resident variant at `da369e6`, retained through `d0aea1a`:
  all 4221 frames, 2965011 video packet bytes, independent volume boundaries,
  unchanged video fields and audio. Existing video slots provide 24576 decoded
  bytes. No player hot path or root disk image changes in this experiment.
- **Parameters/method:** optimal ZX0 at 8192/12288/15872/16384 output bytes
  per block. Trace every input read/output write, including buffered bits,
  literals, LZ history and EOF. Compute the exact overlap gap, then place
  complete header/body sectors against the bank top. A shared final sector
  must be saved in the existing 256-byte carry buffer before decoding.
  Actual header acquisition/sector producer execution remains unimplemented.
- **Full host result:** the 15872-byte variant safely fits all **188 blocks**,
  giving **47616 decoded bytes (+23040, 93.75%)**, with smallest sector-aligned
  margins **255/257/255 B**. Video changes **1832196→1818909 B (−13287)** and
  runtime sectors **7158→7106 (−52)**. Whole packet streams compare exactly.
  With the existing bootstrap and interleave held fixed, occupied sectors
  would be **2461/2462/2461**, leaving **83/82/83**. These are conditional
  estimates, not measured new TRDs. Three initial blocks contain 91/76/41
  complete packets versus 52/31/15; these are not pre-rendered screen counts.
- **Rejected limit:** full 16384-byte output fails for **180/183 blocks**, even
  without sector-alignment padding. Required footprints reach 16388/16389/
  16388 B. The three shorter final blocks fit. Its 1817544-B stream would save
  another 1365 B but cannot use the tested overlap layout. The intermediate
  12288-byte variant fits all 243 blocks at 1823215 B / 7124 sectors.
- **Native verification/CPU:** all **364 baseline and 188 candidate blocks**
  pass both separate and overlapping memory layouts using actual 126-byte
  turbo-decoder opcodes: 1104 runs, 11860044 guarded output writes. Every
  write's input cursor matches the independent host trace. Identical blocks
  have **zero layout T-state delta**. Larger blocks increase uninterrupted
  decoder CPU **160653056→162913389 T (+2260333, 1.407%)**. This excludes the
  resumable wrapper, queue, carry traffic, IRQ, ULA, ROM and disk latency.
  Six boundary/native tests pass, including deliberately unsafe placement,
  EOF, literal tails, new offsets, all header alignments and pointer wrap.
- **Decision:** retain 15872 bytes as a measured integration candidate, not
  an accepted speed improvement or release. Implement the C000 output base,
  larger length bounds, header/sector placement and queue ownership next;
  then build and run all disks through EOF with exact frame deadlines and
  AY at 50 Hz. Buffer size and fewer sectors cannot establish cadence alone.
- **Evidence/reproduction:** [proof, layout, CPU counts and commands](toolkit/INPLACE_ZX0_RESERVOIR.md),
  [storage probe](toolkit/probe_inplace_zx0.py),
  [native benchmark](toolkit/benchmark_inplace_zx0.py),
  [saved probe and archive hashes](toolkit/inplace_zx0_probe.json),
  [CPU report](toolkit/inplace_zx0_cpu.json), and
  [auditor](toolkit/audit_inplace_zx0.py). All 12 compressed streams are archived
  in the repository (7153056 packed bytes); no source frames are changed.

## 2026-09-27 — uncontended half-row body: no playback gain

- **Objective/baseline:** test whether removing opcode contention from the
  half-row cache copier at `0c674b6` improves delivery. Scope remains all
  4221 frames, original pixel fields and 25326 AY records on three independent
  disks, with unchanged resolution and nominal six-field deadlines.
- **Change:** move sixteen LDIs plus RET into 33 of the 38 unused bank-2
  selector bytes at 877C; replace the body with CALL and repack the bank-5
  controller from 80 to 51 bytes. Active code grows by four bytes and nested
  stack use by two. Body CPU cost increases **256→283 T (+27)** per copied
  half-row, **+108 T** per partial four-row group. Parser, compressed video
  and resident audio bytes are unchanged. Full frame-stage CPU grows
  **1002069238→1004729062 T (+2659824)**, exactly matching the cache-copy
  change **96166094→98825918 T**; 3421 frames are slower, 800 unchanged.
  IRQ, ULA, ROM and disk latency are separate.
- **Capacity/boot:** occupied sectors remain **2491/2492/2491**, free sectors
  **53/52/53**, video **1839779 B / 7188 sectors**. Cold dirty-RAM boot,
  first full native/second compact frame, immutable AY bank and both mocked
  disk swaps pass. Startup compression saves 1411 mocked CPU T per disk,
  outside playback. No release disk image is replaced.
- **Full Fuse result:** every disk reaches EOF with all AY records exact at
  50 Hz, zero gaps/underruns, all runtime sectors exact and no retries. All
  80 sampled bytes per native frame match. Late frames **206/660/874→
  206/661/874**, total **1740→1741**; invalid fallback intervals **1043→1048**.
  Maximum lateness remains **97/287/282 fields**. Recovered late runs change
  **5/3/6→5/2/6**; disks 1/2 still end with unrecovered runs 1609..1623 and
  994..1296. Every publication span is unchanged, totaling **1816379328 T**.
  Reconstruction elapsed time changes **640812368→640903384 T (+91016)**.
  These totals include contention/IRQ and unmatched startup phases, not
  isolated ROM/ULA costs. Both video timing gates still fail.
- **Verification:** four instruction/bounds/IRQ tests pass. All 4221 compact
  frames and both complete native screens match in the CPU fixture, and each
  frame's cycle delta matches the independent formula. These full pixel
  checks are separate from sampled Fuse pixels. The snapshot contains 30 pinned archives
  (6195397 packed bytes), with all raw traces and generator sources. Full
  integrated deterministic CPU totals and physical-drive checks remain open.
- **Decision:** reject this placement as a speed improvement; retain its
  implementation/evidence as an optional failed experiment. Continue from
  the smaller resident-AY baseline or the prior half-row variant. Next prove
  the input/output safety margin before attempting a larger bank-local ZX0
  prepared reservoir. Do not assume that uncontended opcode placement alone
  repays call overhead.
- **Reproduction:** [layout, formulas and commands](toolkit/UNCONTENDED_HALF_COPY.md),
  [CPU benchmark](toolkit/benchmark_uncontended_half_copy.py),
  [TRD builder](toolkit/build_uncontended_half_player.py),
  [evidence manifest](toolkit/uncontended_half_player_evidence/manifest.json),
  and [summary/auditor](toolkit/summarize_uncontended_half_player.py).

## 2026-09-27 — half-row motion cache: full CPU saving, small delivery gain

- **Objective/baseline:** use the spare capacity of `da369e6` to copy fewer
  motion-cache bytes, retaining all 4221 frames, exact picture fields and
  25326 AY records, independent disks and the original nominal deadlines.
- **Change:** widen each cache map from 3 to 6 bytes, selecting halves of
  four-row groups. Retain the paired whole-row helper for full groups.
  New 62/80-byte helpers use retired bank-5 code space; the old bank-2
  selector becomes a jump and a map-copy helper. Screens, video slots,
  AY bank/FIFO and stack allocations remain. This code placement is subject
  to ULA contention; deterministic savings are not elapsed-time savings.
- **CPU:** all compact frames and both complete native screens match for
  all 4221 frames. Frame stages change **1018049241→1002069238 T
  (−15980003)**; 124 frames are slower. Map-copy instructions change
  **68→147 T/frame (+79)**, adding **333459 T**, for a net **−15646544 T**
  in the accounted regions. Every per-frame delta matches the independent
  copy formula. Three new tests pass, including every group/pair position,
  untouched memory, wrapping, exact instruction counts and real AY IRQ
  after every copy instruction. Full integrated CPU totals remain unmeasured.
- **Actual capacity:** optimal ZX0 adds **7583 B**, runtime sectors
  **7158→7188 (+30)** and occupied sectors **7434→7474 (+40)** including
  startup/interleave padding. Disks use **2491/2492/2491 sectors**, leaving
  **53/52/53**. Reversible map expansion checks all original video fields.
  Dirty boot, full prime frames, immutable audio bank and both mocked swaps
  pass. All helpers fit the existing RAM map.
- **Full playback:** all three cold Fuse runs reach EOF; all 25326 AY ticks
  remain exact at 50 Hz with zero gaps/underruns. All sectors and 80 pixel
  samples/frame match. Late frames change **213/654/878→206/660/874**,
  total **1745→1740**; maximum delays **103/291/291→97/287/282 fields**.
  Fallback violations change **1047→1043**. Late runs recover 5/3/6 times,
  but disks 1/2 end with unrecovered runs 1609..1623 and 994..1296. Summed
  publication span changes **1816733868→1816379328 elapsed T (−354540)**:
  only five fields. Disk/IRQ phases differ; this is not isolated CPU timing.
- **Decision:** retain an optional measured variant, without changing the
  smaller resident baseline or root release TRDs. It does not solve video
  cadence. Next measure the hot 16-LDI body in unused uncontended selector
  space, and investigate a larger prepared reservoir only after proving
  overlap safety for every compressed input byte. Preserve this result
  even if another placement or format supersedes it.
- **Evidence/reproduction:** [implementation, formulas and commands](toolkit/HALF_ROW_PLAYER.md),
  [frame CPU benchmark](toolkit/benchmark_half_row_cache.py),
  [real TRD builder](toolkit/build_half_row_player.py),
  [complete evidence](toolkit/half_row_player_evidence/manifest.json), and
  [summary/auditor](toolkit/summarize_half_row_player.py).

## 2026-09-27 — foreground resident AY service: sound cadence fixed

- **Objective/baseline:** correct audio starvation in the complete queue-only
  resident-AY attempt below, keeping all 4221 frames and 25326 AY records,
  resolution, nominal six-field deadlines and independent disks unchanged.
- **Change:** service audio before packet acquisition, reconstruction and
  native drawing as well as producer steps/drain; increase the maximum
  batch from 6 to 31. Below 24 queued records, fill available FIFO space
  without waiting. The old IRQ consumer is unchanged. Each additional
  foreground hook adds 27 T plus service; a skipped refill adds 130 T.
  These two parameter changes were tested together, not separately.
- **Result:** complete cold Fuse playback of all three volumes has **zero AY
  underruns, field gaps or duplicates**, with all records exact. Actual
  capacity remains **2476/2479/2479 sectors**, leaving **68/65/65**. The
  corrected build reads **91/92/93** boot sectors. Video remains late on
  **213/654/878** frames, maximum **103/291/291 fields**; **98/365/584**
  intervals fail the fallback. Late runs recover **5/3/6** times; final
  runs on disks 1/2 do not recover. Average fps is **8.314549/8.032726/
  8.333333**; the third average conceals temporary delays.
- **Comparison:** versus the prior muxed two-byte-cache player, video reads
  fall **7501→7158**, late frames **3066→1745**, AY underruns **845→0**, and
  summed publication spans **1851904234→1816733868 elapsed T (−35170366)**.
  Fallback interval violations increase **644→1047**. This is a combined
  delivery measurement with changed disk/IRQ phases, not a CPU-only saving.
- **Verification:** **24 tests pass**. Dirty boot, both mocked-ROM disk swaps,
  all video packet fields, first complete native/second compact frames,
  31 prepared audio records and immutable audio-bank bytes pass. Full Fuse
  traces check all EOFs, actual OUT timing, 80 pixels/frame, audio and all
  runtime sectors without retries or missing IRQ fields. Full new integrated
  CPU/pixel replay and physical-drive tests remain unverified. The packet
  verifier was corrected to account for existing later-disk native-mask
  initialization; this required no player or data change.
- **Decision:** retain as the next experimental baseline: capacity and audio
  cadence pass; nominal/fallback video timing both fail. Preserve root
  release images. Use the new spare sectors to reevaluate lossless faster
  representations, measuring total delivery rather than decoder CPU alone.
- **Evidence/reproduction:** [implementation, cycles and commands](toolkit/RESIDENT_AUDIO_PLAYER.md),
  [builder](toolkit/build_resident_audio_player.py),
  [verifier](toolkit/verify_resident_audio_player.py),
  [saved complete evidence](toolkit/resident_audio_player_evidence/foreground/manifest.json),
  [priming report](toolkit/resident_audio_player_prime.json), and
  [reproducible summary/auditor](toolkit/summarize_resident_audio_player.py).

## 2026-09-27 — first resident-AY TRDs: capacity passes, sound service fails

- **Objective/baseline:** integrate the `8a49d3c` resident decoder into the
  three-disk player. Separate audio from video packets; retain every encoded
  video field, original AY record and independent checkpoint for all 4221
  frames. Reduce ready video/history from four slots to banks 0/1/3 and
  store the full per-volume audio bank in bank 4.
- **Implementation/cycles:** allocate fixed guard/bridges in retired code,
  add bounded audio startup sections, service only before producer steps
  and during drain with batch limit 6. Guard costs **103 T** when skipped,
  or **108 T + 436-T bridge + actual decode** on refill. Producer/drain
  hook costs **13→160 T (+147)** when skipped; three-slot cursor changes
  **11→39/47 T (+28/+36)**. Packet dispatch changes **17→10 T (−7)**,
  excluding removed enqueue work. Full old/new instruction paths are linked
  in [the integration report](toolkit/RESIDENT_AUDIO_PLAYER.md).
- **Storage/result:** actual independently bootable TRDs use **2476/2479/2479
  sectors**. Audio-bank images are **14230/13215/13037 B**. The video-only
  stream is **1832196 B**, with **7158 video sectors**. Cold RAM, startup
  sections and mocked swaps pass. Complete Fuse playback reaches all EOFs
  with exact AY records and sampled pixels, but produces **537/1409/1884
  AY underruns**, **203/546/847 late frames**, and **89/317/553 invalid
  fallback intervals**. Maximum lateness is **97/273/270 fields**.
- **Decision:** reject queue-only audio service. The trace and call graph
  motivate foreground service and a larger refill batch; neither capacity
  nor exact records alone proves cadence. Preserve this failed attempt's
  original sources/build/metadata/raw traces in
  [the queue-only archive](toolkit/resident_audio_player_evidence/queue-only/manifest.json).
  Both attempts are independently auditable in
  [the combined summary](toolkit/resident_audio_player_summary.json).

## 2026-09-27 — portable source pins for the resident AY measurement

- **Objective/baseline:** reproduce the `ac427ab` CPU report from the root
  checkout after its complete worktree run and fast-forward to main.
- **Failure:** the root audit rejected `validate_streaming_player.py`.
  Root had LF and the worktree had CRLF; all source content matched after
  newline normalization. No decoder, input or generated machine code differed.
- **Change/result:** use an explicit `source_sha256_lf` field for normalized
  Python source hashes. Keep input/report/image hashes byte-exact. Regenerate
  the full 25326-record report and verify both checkouts; producer cost stays
  **52600652 T**, delta **+43450049 T**, and minimum bank spare **2154 B**.
- **Decision:** retain this source-pin policy for this report without
  changing historical source files or their previous evidence hashes.
  [Generator](toolkit/benchmark_resident_audio_z80.py),
  [auditor](toolkit/audit_resident_audio_z80.py), and
  [scope](toolkit/RESIDENT_AUDIO_Z80.md). Playback integration remains pending.

## 2026-09-27 — resident AY Z80 decoder, complete records and bank fit

- **Objective/baseline:** implement the `1cdb5f1` AYH1 storage prototype on
  Z80 without changing its 25326 records, initial states, video data or
  existing AY interrupt consumer. Prepare the resident-audio route toward
  three independent disks with exact 25/3-fps delivery; no new TRDs yet.
- **Implementation:** compile canonical tables into compact binary trees
  and decode directly into the existing 31-record FIFO. Publish only a
  complete record; return immediately on full/EOF; cap each call at six
  records. Use AF' for the pair count. A 35-byte fixed-RAM bridge preserves
  both register sets and restores the previous RAM bank using the existing
  IRQ-safe paging helper. Its fixture address is not a player allocation.
- **Memory:** the full bank-4 code/state/tables/payload images occupy
  **14230/13215/13037 B**, leaving **2154/3169/3347 B**. This includes
  407 B of code and 976/980/988 B of tree nodes. It excludes the fixed
  bridge, existing FIFO, ISR and stack; the full three-slot layout is pending.
- **CPU:** all original AY writes and states match. With one call per six
  records, producer cost including preservation and two paging calls is
  **9150603→52600652 T (+43450049)**. Bank-local decoding costs 50760296 T;
  the bridge adds 436 T/call. Maximum six-record call: **22413 T**; mapped
  initialization: **1056 T/volume**. Counts include RET and exclude the outer
  CALL, IRQ/ULA, ROM and disk latency. This is more costly than enqueueing
  already decoded records, not a net speedup claim. Reduced video ZX0/copy
  work and independent audio availability still need combined measurement.
- **Verification:** all 25326 records execute with memory guards and exact
  bit consumption; every payload byte is read once. Every instruction and
  an independent aggregate T-state formula agree. **20 tests pass**, including
  nine new tests covering every mask/value, 24-bit codes, full-bank input
  wrap, FIFO bounds, real fast AY IRQ after each instruction, and screen
  publication during every paging instruction across all banks/screens.
  Dirty-RAM fixture initialization is not a TR-DOS cold-boot test; manual
  FIFO draining is not 50-Hz cadence evidence.
- **Decision:** retain for integration. Allocate the fixed bridges, load
  the audio bank in bounded bootstrap sections, remove audio from video
  packets and reduce the video queue to three slots before a full Fuse run.
  Actual disk capacity, sustained three-slot delivery and all release timing
  gates remain unverified. Root release images are unchanged.
- **Evidence/reproduction:** [implementation and cycle formulas](toolkit/RESIDENT_AUDIO_Z80.md),
  [generator](toolkit/resident_audio_z80.py),
  [full Z80 benchmark](toolkit/benchmark_resident_audio_z80.py),
  [saved-result auditor](toolkit/audit_resident_audio_z80.py),
  [tests](toolkit/test_resident_audio_z80.py), and
  [complete CPU/RAM results](toolkit/resident_audio_z80.json).

## 2026-09-27 — resident AY format and complete lossless storage probe

- **Objective/baseline:** investigate audio starvation and a longer
  preparation horizon after the complete `8bc6a09` three-disk run. Preserve
  all 4221 frames, 25326 50-Hz ticks and independently initialized volumes.
- **Trace experiment:** reconstruct produced-byte bounds from all 25955
  queue calls. Of 845 AY underruns, the next record is definitely decoded
  for **178**; **667** occur inside its producing call, where exact readiness
  is unknown. A zero-cost foreground FIFO model with the original producer
  times fixed still has **75/324/446** underruns for every tested capacity
  12/18/31/63/127/255. This does not test a rescheduled producer. The initial
  interpretation that most records were certainly not decoded was too
  strong: the refined start/end bounds prove no such case. Preserve the
  distinction between definite readiness and an active-call uncertainty.
- **New host format:** AYH1 codes two register-mask bytes and eleven value
  contexts with static canonical Huffman tables; constants use no bits.
  Every empty tick, noise update, original register/value pair and each
  disk's explicit initial state is retained. No LZ history or quality loss.
  AY data plus serialized tables/state is **13279/12262/12080 B**, versus
  **42450/37928/37986 B** in original records. Minimum free bank space before
  executable code/expanded lookup tables is **3105 B**; runtime fit unproven.
- **Complete storage:** remove only AY records from video packets, adjust
  lengths, and recompress with optimal ZX0 v2 in <=8192-B blocks. All **364
  blocks** decode exactly; recombining video and sound restores every old
  FAP3 packet byte. Combined size **1919945→1869817 B (-50128)**, with
  per-volume savings **17684/16766/15678 B**. Separately rounded data plus
  the old fixed overhead estimates **2473/2478/2481** used sectors and
  **71/66/63** free; this excludes the new player/bootstrap changes.
- **Verification:** six format/model tests pass; all actual AY records and
  packets round-trip; saved-source hashes, input archives, compressed block
  hashes, initial states and storage arithmetic pass the independent audit.
  Compressed blocks and audio bytes are saved for reproduction without
  running the encoder again. Cache publication is atomic for parallel jobs.
- **Decision:** pursue a resident decoder in bank 4 and video slots 0/1/3.
  Measure executable Z80, IRQ safety and the reduced 24-KiB video history
  before integrating. Current player delta **0 T**; no new Z80 decoder,
  TRDs, full disk run or timing success is claimed. Existing releases remain
  unchanged; exact nominal deadlines, fallback recovery and AY continuity
  are still required. The new data-size margin may also fund faster lossless
  video choices, but no such choices were changed in this experiment.
- **Evidence/reproduction:** [report and implementation plan](toolkit/RESIDENT_AUDIO.md),
  [AY codec](toolkit/ay_huffman_stream.py),
  [trace profiler](toolkit/profile_audio_lookahead.py),
  [audio probe](toolkit/probe_resident_audio.py),
  [storage probe](toolkit/probe_resident_audio_storage.py),
  [saved-result audit](toolkit/audit_resident_audio.py), and
  [compact summary](toolkit/resident_audio_summary.json).

## 2026-09-27 — integrate the two-byte cache and measure all three disks

- **Objective/baseline:** carry the `2995503` CPU prototype into real cold
  TRDs and compare complete playback with compact cursor at `7a1d5de`.
  Same 4221 frames, resolution, 25/3 fps schedule and 50 Hz AY data.
- **Change:** optional `--cached-huffman-lookahead`, installed before inline
  Huffman generation. Reserve two readable guards by lowering FAP3 payload
  capacity **4703→4702 B** within the existing 4704-B window. Only a length
  check immediate changes: **10→10 T**, full accepted range check **94 T**.
  No extra stream byte, copy or guard write. The second guard is read-only
  and may be arbitrary. Oversized optional configurations are rejected.
- **CPU/size:** retain the complete prototype comparison:
  **1023364329→1018049241 T (-5315088)** for frame stages; packet-parser
  delta **0 T**. Shared short symbols **145/169→134/162 T**, long symbols
  **+18 T**, setup **19→65 T**. The helper occupies 7 B at 8FC0; bank-6 inline
  code remains 875 B. Compressed stream **1919945 B**, 7501 video sectors,
  **2542/2543/2542** used sectors and starts **53/58/60** are unchanged.
- **Verification:** four integration tests pass, including old/new executed
  boundary checks, in-place pixels/AY/parser cycles, empty input with four
  second-guard values, and host rejection at 4703 B. All disks independently
  boot from dirty RAM. Mocked-ROM swaps and wrong disk/series rejection pass.
  Cold-installed cache/motion regions match the full CPU prototype; all
  inline bytes are independently regenerated and checked.
- **Full Fuse:** all three volumes reach EOF without RAM patches, with all
  25326 AY records exact, all frame samples exact, and no missing physical
  IRQ fields. Fuse samples 80 bytes/frame; the separate CPU fixture compares
  compact data and both complete screens. Fps changes
  **8.284839/7.986197/7.889942→8.287377/7.995065/7.901460**. Summed publication
  span **1853606028→1851904234 T (-1701794)**; initial IRQ/disk phases are
  not matched, so this is an elapsed measurement, not predicted CPU saving.
  Every actual queue call replays exactly: **25955** calls, with queue plus
  full AY-wait CPU **289460171→289570034 T (+109863)**. Thirteen new gzip
  archives preserve the raw evidence; CPU and elapsed disk service stay
  separate. Saved-result hashes, coverage and arithmetic pass the audit.
- **Remaining failures:** late frames **3070→3066**, AY underruns **869→845**,
  invalid fallback intervals **662→644** (disk 1 alone worsens 120→121).
  Maximum late fields **79/329/451**; actual deviations
  **5601733/23328729/31979514 T**. Late-run recoveries **0/3/2**, with final
  runs from local frames **640/478/56** unrecovered through EOF.
- **Decision:** retain this optional, lossless integrated improvement for
  further measured work. Capacity passes; nominal deadlines, fallback
  recovery and continuous AY still fail. Root release images are unchanged.
  No physical-drive or unrelated-video playback claim.
- **Evidence/reproduction:** [report and commands](toolkit/LOOKAHEAD_PLAYER.md),
  [installer](toolkit/lookahead_player.py), [tests](toolkit/test_lookahead_player.py),
  [build](toolkit/lookahead_player_build.json),
  [cold-code verifier](toolkit/verify_integrated_bootstrap.py),
  [summary](toolkit/lookahead_player_summary.json), and
  [saved-evidence auditor](toolkit/summarize_lookahead_player.py).

## 2026-09-27 — two-byte Huffman cache in alternate registers, CPU prototype

- **Objective/baseline:** remove repeated indexed lookahead reads without
  changing the compressed stream. Compare against the compact-cursor
  configuration at `cb94632`, using the same 4221 states and raw volumes.
- **Change:** retain current/next bytes in B'/E' and bit position in C';
  move the motion output cursor from DE' to HL' with 117 equal-cost opcode
  substitutions. Use AF' to hold the short symbol/initial long-code rank.
  Shared bitmap short paths **145/169→134/162 T (-11/-7)**; long paths
  **+18 T**; frame setup **19→65 T (+46)**. The fixed helper adds **7 bytes**
  at 8FC0, with two extra setup stack bytes. The 875-byte inline body retains
  its size. Stream delta **0 bytes**; no default builder behavior changes.
- **Complete CPU:** all compact data and both full native screens match for
  **4221 frames**. Frame stages **1023364329→1018049241 T (-5315088)**,
  **0.5194%** less work. Per-volume savings **1921526/1756135/1637427 T**.
  Actual symbol counts reproduce every frame's delta. **55 frames** are
  slower, by at most **50 T**; they remain included in the totals.
- **Coverage:** five boundary/mixed-frame/actual-IRQ tests pass. Exhaustive
  actual-volume tables pass **68712 paired code/bit-offset cases**, including
  arbitrary A5/3C guards, exact cursors, cached bytes and instruction counts.
  A six-frame smoke passed at **1487678→1481612 T (-6066)** before the full run.
  Source/reference hashes and saved-result arithmetic pass the audit.
- **Input-contract finding:** two readable lookahead bytes are required;
  a one-guard boundary test fails as intended. The CPU stage already has
  two guards, but the integrated FAP3 parser guarantees only one. All actual
  packet maxima **2638/2921/3645 B** fit a proposed **4702 B** payload limit
  in the existing 4704-B window. There are 2635 packets without literals
  and 44 without coded values. Integration remains required.
- **Corrected attempts:** placement at 8FB0 was rejected against the actual
  8FB8 code/state end; helpers moved to 8FC0. An initial long-path trampoline
  measured **+42 T**, contradicting a **+32 T** estimate because an extra
  jump was omitted. Cycle tests and the partial movie smoke caught this.
  Equal-size PUSH AF rank saving replaces that trampoline: final **+18 T**.
- **Decision/limits:** retain the CPU prototype for integration. It excludes
  ZX0, queue/copy work, AY/IRQ cadence, ULA, ROM and disk latency. No new
  TRDs, capacity claim or disk playback result; release images are unchanged.
  Exact nominal deadlines, fallback recovery and continuous AY remain open.
- **Reproduction/evidence:** [report and commands](toolkit/CACHED_HUFFMAN_LOOKAHEAD.md),
  [implementation](toolkit/cached_huffman_lookahead.py),
  [tests](toolkit/test_cached_huffman_lookahead.py),
  [full-frame runner](toolkit/benchmark_cached_huffman_lookahead.py),
  [complete CPU report](toolkit/cached_huffman_lookahead_cpu.json),
  [case/packet auditor](toolkit/audit_cached_huffman_lookahead.py),
  [case report](toolkit/cached_huffman_lookahead_cases.json),
  [saved-evidence audit](toolkit/summarize_cached_huffman_lookahead.py),
  [summary](toolkit/cached_huffman_lookahead_summary.json).

## 2026-09-27 — reject whole-row fill tests using complete frame evidence

- **Objective/baseline:** find a larger native-output saving without changing
  compression or pixels. Sources start at `7a1d5de`; use the same 4221
  compact states, archived native masks and executed HL-reader CPU profile.
  The later compact-cursor option leaves this output stage unchanged.
- **Parameters:** two runtime tests before each dense-row pixel body:
  whole-row zero and whole-row uniform. Failed tests retain normal output.
  Count only the first failed test and assume all successful fills, further
  tests and later failures cost zero to obtain optimistic lower bounds.
- **Result:** among **83652** dense rows, only **90** are zero and **332**
  uniform. Immediate failures cost **21 / 32 T**. Baseline row **1632 T**;
  movie pixel bodies **136520064 T**. Optimistic candidate totals are
  **137834196 / 137542880 T**, deltas **+1314132 / +1022816 T**.
- **Verification:** every frame's dense-row count reproduces its previously
  executed pixel-stage T-states, including independent-volume warmup. State
  and source hashes, histograms, per-frame and per-volume counts are saved.
  This is an input profile and instruction bound, not execution of a new
  renderer. No new IRQ, disk, ULA, audio or playback check is claimed.
- **Decision:** reject both whole-row dispatch strategies before allocating
  code space. Actual CPU/stream change **0 T / 0 bytes**. Other fill methods
  remain untested; existing release images and timing failures are unchanged.
- **Reproduction/evidence:** [profiler](toolkit/profile_flat_dense_rows.py),
  [complete report](toolkit/flat_dense_rows_profile.json),
  [calculation and command](toolkit/FLAT_DENSE_ROWS.md).

## 2026-09-27 — compact cursor byte updates, full CPU and disk playback

- **Objective/baseline:** reduce repeated reconstruction bookkeeping without
  changing compression. Sources start at `b3f33fc`; complete playback is
  compared with HL-reader `074e1e7` on the same 4221 frames and three streams.
- **Change:** replace full-address updates within a compact stripe with
  low-byte operations. Normal tile **40→33 T (-7)**; no-op run
  **62→42 T (-20)**. The stripe transition still handles full addresses.
  Code-region lengths, labels, extra RAM/stack and compressed bytes are
  unchanged. Added `--compact-cursor`, disabled by default.
- **Complete CPU:** all 4221 compact frames and both full screens match.
  Frame stages **1027719624→1023364329 T (-4355295)**, with per-frame
  instruction-formula checks. All **25677 real queue calls** replay exactly;
  queue/full-AY-wait CPU **289401696→289460171 T (+58475)**.
- **Complete Fuse:** three EOFs, late frames **3073→3070**, AY underruns
  **883→869**, summed publication span **1854669649→1853606028 T**
  (**-1063621 T**). Intervals outside 5..7 fields **660→662**; the third
  disk worsens on this metric. Maximum lateness **83/338/463 fields**;
  recovered runs **0/3/2**, with the final run on each disk unrecovered at EOF.
  Actual maximum deviations **5885379/23966904/32830408 T** and individual
  nominal-deadline misses are saved separately from fallback results.
- **Capacity/data:** independently bootable images use **2542/2543/2542**
  sectors. The 1919945-B stream, 7501 video sectors and their start positions
  are unchanged. All 25326 AY records are exact, but have **78/333/458**
  field gaps; no duplicate records or missed physical IRQ fields. All 7498
  direct ROM returns preserve IM2/I/vector. Runtime sectors are read once.
- **Coverage/limits:** four boundary/mixed-frame/IRQ tests pass; a six-frame
  smoke precedes full CPU replay. Dirty-RAM cold boots, regenerated installed
  bytes and mocked-ROM disk swaps pass. Fuse has no debugger RAM patches
  and checks 80 screen bytes per frame; full screen comparison belongs to
  the separate CPU fixture. IRQ/disk starting phases are not matched.
  No new source video or physical drive was tested.
- **Decision:** retain the option and both comparison runs. CPU savings are
  exact; measured delivery improvement is modest and not uniform. Nominal
  deadlines, fallback and AY continuity still fail; root release TRDs remain
  unchanged. Continue with larger remaining reconstruction/output costs.
- **Reproduction/evidence:** [report and commands](toolkit/COMPACT_CURSOR.md),
  [implementation](toolkit/compact_cursor.py),
  [tests](toolkit/test_compact_cursor.py),
  [full CPU script](toolkit/benchmark_compact_cursor.py),
  [CPU data](toolkit/compact_cursor_cpu.json),
  [build](toolkit/compact_cursor_build.json),
  [playback audit](toolkit/summarize_compact_cursor.py),
  [summary and archive index](toolkit/compact_cursor_summary.json).

## 2026-09-27 — complete frame CPU profile and rejected dense-output probes

- **Objective/baseline:** locate remaining decoder/output costs without
  changing compression. Profile the HL-reader configuration `074e1e7` using
  the same 4221 frame states and three raw volumes as the inline-Huffman
  fixture. Tooling added after `8da95ed`; streaming input remains disabled.
- **Change:** bank-aware instruction/stage counters, a full frame replay,
  two analytical output probes and a saved-evidence auditor. No player
  hot-path or stream change: **0 T / 0 bytes delta**.
- **Measurement:** all 4221 compact frames and both complete native screens
  match. CPU totals **388574871 / 329687365 / 309457388 T**, total
  **1027719624 T**. Every frame equals the earlier baseline minus the already
  verified 499-T HL-reader saving. Reconstruction is 60.36%, native output
  32.85%, metadata 6.19% of this profile. Remaining indexed memory loads:
  1203077 executions, 22858463 T; a hypothetical 19-to-7-T replacement has
  a 14436924-T gross saving before setup/preservation, not a measured gain.
- **Rejected parameters/results:** 36 nonzero one/two-bit constants in a
  nearly-full-band test admit no new dense bands and each add an estimated
  **531846 T**. The encoder already rounds bands with at least 18 changed
  cells to full bands. A proposed eight-cell helper (2264→1919 T/group)
  needs a 17-T test on all 148104 nonzero groups but helps only 4237 groups:
  estimated **+1056003 T**. Neither candidate was implemented.
- **Verification:** a two-frame-per-volume smoke run preceded the complete
  CPU replay. Input/source hashes, per-frame/stage/instruction totals and
  probe arithmetic are checked by the saved-evidence audit. The native-map
  probe reads all 378 archived ZX0 blocks and 4221 packets. This profile
  excludes ZX0/queue/copy/AY/IRQ/ULA/ROM/disk time; there is no new Fuse or
  physical-drive run and it does not qualify a release.
- **Decision:** retain the HL-reader baseline, reject both extra dispatch
  tests, and prioritize complete register/address sequences using measured
  frequencies. Save the current plan and index-access method in English.
  Root release TRDs are unchanged.
- **Reproduction/evidence:** [profile report](toolkit/FRAME_HOTSPOTS.md),
  [profiler](toolkit/profile_frame_hotspots.py),
  [full data](toolkit/frame_hotspot_profile.json),
  [dense probe](toolkit/profile_dense_band_threshold.py),
  [dense data](toolkit/dense_band_threshold_profile.json),
  [auditor](toolkit/audit_frame_hotspots.py),
  [summary](toolkit/frame_hotspot_summary.json),
  [current plan](toolkit/DECODE_SPEED_PLAN.md).

## 2026-09-27 — завершена проверка плеера с частичной загрузкой ZX0

- **Цель/база:** сократить остановки на загрузке полного блока, сохранив
  4221 кадр, разрешение, AY и 1919945 B сжатого потока. Исходники `f962cac`,
  сравнение с полным HL-reader `074e1e7`. Реализация/Fuse выполнены
  26 сентября; CPU replay, повтор тестов и архивная проверка — 27 сентября.
- **Изменение:** `--streaming-input`, встроенная проверка literal,
  split-размещение горячего ядра в bank 2, входные паузы очереди и
  явное завершение EOF. Новых выходных копий нет; максимум сектор на шаг.
- **CPU:** короткий literal −47 T против первого прототипа. Все 378 блоков:
  234355282→221438324 T; против прежнего незащищённого ядра 201086097 T
  это +20352227 T. Реальные очередь/AY wait: **289401696→313656360 T**.
- **Полный Fuse:** все три EOF; AY underruns **883→1006**, late **3073→3062**,
  интервалы вне допуска **660→777**, publication span **+9076225 T**.
  Пропущенных IRQ 0, все 25326 AY-записей и 7501 сектор точны;
  между AY-записями есть пропуски полей. Фазы/размещение диска различаются.
  Первое опустошение AY на томе 2 позже (157→481), на томе 3 раньше (56→43).
- **Ёмкость/охват:** 2543/2543/2542 сектора, самостоятельные загрузки,
  грязная RAM и смена томов с mock ROM. 26622 вызова очереди повторены
  с проверкой каждого байта/состояния/тактов; 15 тестов проходят.
  Fuse сверяет 80 экранных байтов на кадр, полного нового pixel/physical-drive
  теста нет. Все пропущенные сроки, серии и восстановления сохранены.
- **Исправленные попытки:** отсутствие поля `phase` в установщике;
  нулевой LDI после потребления выхода до EOF; чрезмерное условие EOF-теста;
  сравнение строковых/целочисленных ключей в архивном анализаторе.
  Подробности и охват — в отчёте, исходные трассы не исправлялись.
- **Решение:** сохранить как выключенный эксперимент, не заменять
  корневой выпуск. Продолжить от HL-reader с инструкционным профилем
  реконструкции/вывода; одна более короткая дисковая пауза не доказывает
  ускорения всего фильма. Цель плавных трёх дискет остаётся открытой.

[Отчёт/воспроизведение](toolkit/STREAMING_PLAYER_ru.md),
[сводка и хеши](toolkit/streaming_player_summary.json),
[CPU ядра](toolkit/streaming_inline_zx0_cpu.json),
[CPU replay](toolkit/replay_streaming_queue.py),
[аудитор архивов](toolkit/summarize_streaming_player.py).

## 2026-09-26 — ZX0 приостанавливается перед недогруженным сектором

- **Цель/база:** убрать обязательное ожидание целого сжатого блока; код от
  `d4f31df`, точные TRD HL-reader `074e1e7`, 4221 кадр/378 блоков. Это
  отдельный Z80 CPU-прототип, без интеграции плеера и нового Fuse.
- **Изменение:** вход остаётся в слоте, без промежуточного копирования;
  граница страницы проверяется после чтения метаданных и части literal.
  `input_needed` приостанавливает ядро. Отдельный `finished` не позволяет
  спутать полный выход с ещё не прочитанным EOF. Хост подаёт страницы
  непосредственно в слот; дисковый producer в этом опыте не исполняется.
- **CPU/память:** **201086097→234355282 T, +33269185 (+16,54%)**;
  по томам +10815449/+11083572/+11370164 T. На обычном продвижении входа
  6→14 T, коротком literal внутри страницы +80 T. Код/состояние
  314→480 B, состояние 15→21 B, максимум частного стека реальных блоков
  16 B без IRQ. Тестовый адрес пересекает служебный код плеера и ещё
  требует переразмещения. Формат и сжатые данные не меняются.
- **Результат:** все 3083375 выходных байтов точны при физически
  незагруженных/запрещённых поздних страницах; 7492 входные паузы.
  377 из 378 блоков дают выход до полной загрузки. Для тех же двух
  запросов, что совпали с первой недогрузкой AY, нужны **3/3 новых
  сектора вместо 20/22**. Остальные сектора нужны позже; нового общего
  расписания и дисковой задержки это не доказывает.
- **Проверки:** пять тестов границ, длинных токенов, EOF, нулевой цели
  старта, сохранения регистров/стека и AY IRQ после каждой инструкции
  выбранной последовательности. Первоначальный произвольный порог
  2000 IRQ-инъекций упал при 1808; заменён точным подсчётом покрытия.
  Все 378 пар исполнены на настоящих входах, сохранены гистограммы,
  проверены такты каждой инструкции, хеши кода/данных и архив входов.
  Повторное исполнение всех 378 пар непосредственно из архива совпало
  побайтно и по абсолютным тактам с исходным отчётом.
- **Решение:** продолжить кандидат; сначала вернуть встроенный быстрый
  literal-путь и разместить ядро, затем связать с очередью/producer и
  полностью измерить реальные TRD. Выпуск пока не меняется, достижение
  8⅓ кадра/с и непрерывного AY этим стендом не подтверждено.

[Описание/команды](toolkit/STREAMING_ZX0_INPUT_ru.md),
[ядро](toolkit/streaming_local_zx0.py),
[CPU-отчёт](toolkit/streaming_zx0_input_cpu.json),
[аудитор и повтор CPU из архива](toolkit/verify_streaming_zx0_input.py).

## 2026-09-26 — профиль повторно нулевых масок и первых дисковых пауз

- **Цель/база:** оценить следующий шаг после `074e1e7`; точные три TRD
  HL-reader, 4221 кадр/378 блоков, прежние 1919945 B/7501 сектор и AY 50 Гц.
- **Опыт:** история нулей сбрасывается на каждом диске; моделируются
  пропуск отдельных групп и выровненных блоков по 4/8 групп. Все 480 байтов
  масок каждого кадра точны, исходная CPU-стоимость совпала с архивом.
- **Результат:** 112299 повторно нулевых групп; компонент удаляемых записей
  6288744 T, в среднем 1382..1558 T/кадр **до расходов на проверку/историю**.
  Нового кода Z80 нет, изменение действующего CPU/потока — 0 T/0 B.
- **Причина смены приоритета:** первая недогрузка AY на дисках 2/3 находится
  внутри `take` с 20/22 секторами; producer ждёт всего сжатого блока перед
  ZX0. В этих стадиях диск/ROM занимает 733320/772126 T. На диске 1 первая
  недогрузка приходится на ZX0/копирование без дискового чтения. Полная
  AY-очередь возникает позже первой недогрузки на всех дисках. Время пакета
  содержит ожидание AY и предзагрузку; среднее 446580 T не является чистым
  CPU-бюджетом кадра или доказательством неизбежного дефицита.
- **Проверки:** хеши действительных TRD, metadata, архивных трасс/CPU,
  извлечение всех пакетов и повторный аудит сохранённых масок. Первое
  добавление AY-статистики остановилось на `Reader.u8()`; исправлено на
  `take(1)[0]`, все три диска пересчитаны. Нового Fuse и нового выпуска нет.
- **Решение:** нулевые маски отложить до расчёта всей обвязки; следующий
  кандидат — ZX0 по загруженному префиксу с доказанной безопасностью
  входа. Это не готовая оптимизация и не прогноз времени воспроизведения.

[Описание/команды](toolkit/ZERO_MASK_HISTORY_ru.md),
[скрипт](toolkit/profile_zero_mask_history.py),
[покадровый отчёт](toolkit/zero_mask_history_profile.json).

## 2026-09-26 — сохранён общий метод замены индексных обращений

- **Цель/база:** по просьбе пользователя закрепить метод ускорения для
  дальнейших изменений; база `074e1e7`, существующий опыт HL′/EXX.
- **Изменение:** в [плане ускорения](toolkit/DECODE_SPEED_PLAN_ru.md)
  записан порядок поиска IX/IY в машинном коде, сравнения с HL, прямым
  адресом и регистром, расчёта полного пути и проверки IRQ/банков/границ.
  Уточнено, что 68 индексных чтений масок относятся к исходному варианту.
- **Проверка/решение:** только документация; новых замеров CPU и прогонов
  нет. Метод сохранён для повторного применения с обязательной проверкой
  общей скорости и неизменности сжатия; результаты прежнего опыта ниже.

## 2026-09-26 — HL′/EXX вместо индексного курсора масок

- **Цель/база:** сократить CPU без изменения данных; работа от `1d69dbf`,
  сравнение с полными TRD `a758f8c`, 4221 кадр/378 блоков, прежние
  разрешение, AY и поток. Оба packet guard выключены.
- **Изменение:** `--hl-mask-reader`, курсор флагов в HL′ через EXX,
  основные HL/DE/BC остаются на своих местах; HL′ сохранён на стеке.
  Чтение **29→21 T**, 68 раз/кадр, обвязка **158→203 T**: итог
  **−499 T/кадр**. +7 B кода, +2 B стека, новых буферов нет.
- **CPU:** обе версии исполнены для масок всех реальных TRD-пакетов,
  все 480 байтов/кадр и курсоры точны. **65696334→63590055 T**,
  −2106279. Все 25475 вызовов очереди повторены; queue + AY wait отдельно
  **289281136→289401696 T**, +120560. Это не полный CPU фильма.
- **Проверки:** 10 тестов, все 256 шаблонов, сохранение регистров и IRQ
  между инструкциями, оба обработчика с AY/публикацией. Cold boot с
  грязной RAM, смены 1→2→3 с mocked ROM; полные три независимых Fuse.
  Точны 25326 AY-записей, 7501 сектор, 80 байтов экрана/кадр;
  retries=0, progress=100%, debugger writes=0, пропусков IRQ=0.
- **Результат Fuse:** fps **8,282302 / 7,980296 / 7,884195**, late по
  счётчику и actual OUT **3077→3073**, AY underruns **896→883**,
  плохие интервалы **683→660**; на диске 1 отдельно **119→122**.
  Publication span **1855520541→1854669649 T**, −850892. Максимальные
  actual отклонения 6098093/24392352/33184949 T; восстановлено 0/4/2
  поздних серии, последние не восстановились. Начальные фазы не выровнены.
- **Решение:** полезную замену сохранить для следующих опытов. Сжатые
  байты, размещение runtime-секторов и занятое место **2542/2543/2542**
  прежние. Все диски самостоятельны. На третьем томе работа четырёх
  стадий в среднем 446580 T против бюджета 425448 T; сроки/fallback/AY
  не пройдены. Далее оценить пропуск повторной записи уже нулевых масок.
  Полных пикселей нового Fuse, другого видео и физического привода нет;
  корневые образы выпуска не заменены.

[Описание/команды](toolkit/HL_MASK_READER_ru.md),
[CPU метаданных](toolkit/hl_mask_reader_cpu.json),
[сводка и архивы](toolkit/hl_mask_reader_summary.json),
[сборка](toolkit/hl_mask_reader_build.json).

## 2026-09-26 — фактическая длина optional-пакета и готовый префикс

- **Цель/база:** исключить длинную блокировку готового кадра чтением
  следующего пакета. База `a758f8c`, прежние 4221 кадр/378 блоков,
  разрешение и AY. Опция `--packet-prefix-guard` проверяет фактическую
  длину, доступный префикс завершённого/активного слота и шесть AY-мест.
- **Ресурсы/такты:** 143 B в освобождённых 7C31..7CBF, новых буферов нет,
  дополнительный стек максимум 4 B. Принятый путь: **24→790 T** для
  завершённого слота, **24→774 T** для активного, ещё +4 T для слотов 2/3;
  без parser/IRQ/ULA/ROM. Все 1085 проверок стоят 826362 T; относительно
  того же числа старых обвязок +800322 T. Queue + AY wait CPU отдельно
  **289281136→289184261 T, −96875 T**. Это не полный CPU фильма.
- **Проверки:** 11 тестов, холодная загрузка с грязной RAM, смены 1→2→3
  с mocked ROM и все реальные Fuse-диски до EOF. Точны 25326 AY-записей,
  7501 сектор и 80 байтов экрана/кадр; retries=0, progress=100%, debugger
  writes=0. Все 25162 вызова очереди повторены побайтно. В 978 принятых
  optional-пакетах нет ZX0/диска/ожидания полной AY-очереди; 12 пакетов
  взяты из активного префикса. Тест позиции 8191 сначала уменьшал массив
  банка пустым срезом; стенд исправлен до полного прогона.
- **Результат:** fps **8,277234 / 7,974403 / 7,874636**, поздних кадров
  по счётчику и actual OUT **3077→3080**, AY underruns **896→906**,
  плохих интервалов **683→687**; publication span **+709083 T**.
  Пропущенных физических IRQ 0; восстановлено 0/3/2 поздних серии,
  последние не восстановились до EOF. Максимальные actual отклонения
  6452633/24817800/33964931 T. Фазы и размещение секторов не выровнены.
- **Ёмкость/решение:** поток прежний, занято **2543/2543/2542** сектора
  вместо 2542/2543/2542. Все диски самостоятельны. Ускорения нет, опция
  остаётся выключенной. Кадр 640 первого тома теперь вовремя, но первый
  поздний лишь сдвинулся на 641. На третьем томе работа 447150 T против
  бюджета 425448 T. Следующий опыт — HL'/EXX вместо IX в compiled masks,
  с подсчётом всей обвязки и полным Fuse. Полных пикселей нового Fuse,
  другого видео и физического привода нет; выпуск не заменён.

[Описание/команды](toolkit/PACKET_PREFIX_GUARD_ru.md),
[сводка и архивы](toolkit/packet_prefix_guard_summary.json),
[сборка](toolkit/packet_prefix_guard_build.json).

## 2026-09-26 — успешное чтение больше не отключает IM2 повторно

- **Цель/база:** исправить обнаруженный в `4b48ad0` пропуск физического
  IRQ. Пара с TRD `347f995`, прежние 4221 кадр, 378 блоков, разрешение,
  AY 50 Гц. Guard 4705 B выключен. На всех 7498 прямых возвратах ROM
  подтверждены I=BE, IM2, fast-вектор, IFF1=1 и полные 256 B.
- **Изменение:** `--fast-return-irq` меняет адрес успешного JP Z, обходя
  58 T повторной настройки. Возврат до курсора **115→57 T**, полный
  адаптер одной дорожки **911→853 T**. C=5 **856→856**, короткое чтение
  с повтором **1038→1038 T**. Размер, RAM, стек и сжатые данные прежние.
  Фиксированная экономия 7498×58 = **434884 T**, без ROM/IRQ/ULA/диска.
- **Проверки:** 18 тестов, cold/swaps с mocked ROM и проверка установленных
  байтов прошли. Все три реальных Fuse до EOF: 4221 кадр, 25326 точных
  AY-записей, 7501 сектор ровно один раз, retries=0, progress=100%,
  debugger writes=0, 80 экранных байтов/кадр. Занято **2542/2543/2542**
  сектора. Все 25250 фактических вызовов очереди опыта повторены в CPU.
- **Полная новая пара:** пропущенные IRQ **4→0**, actual late >64 T
  **3659→3077**, late по счётчику **3078→3077**, AY underruns **899→896**.
  fps **8,280612 / 7,977348 / 7,877502**. Publication span
  **1856016897→1855520541 T**, −496356; queue + AY waits
  **289709960→289281136 T**, −428824. Фазы не выровнены; плохие интервалы
  **665→683**, общего выигрыша плавности по всем показателям нет.
  Max actual **6239907/24605076/33752214 T**, восстановлено 0/2/2 серии;
  последние серии не восстановились. Сроки, fallback и AY не пройдены.
- **Ошибки первых проверок:** заглушка портила I/IM не только после C=5,
  но и после прямого чтения; ограничена реальным CALL 3D13. Сборка сначала
  остановилась из-за ROM-контракта, заполнявшегося после `ram()`;
  контракт передан установщику раньше. Проверки сохранены.
- **Решение/следующий шаг:** сохранить исправление опцией для следующих
  опытов. Реальная причина дальнейшей нехватки скорости остаётся:
  третий том в среднем 447086 T четырёх стадий при бюджете 425448 T;
  optional packet 641 занимает 699464 T и задерживает compact 640.
  Проверить actual-length peek и готовые частичные слоты. Полных пикселей
  нового Fuse, другого видео и физического привода нет; выпуск не заменён.

[Описание/команды](toolkit/FAST_RETURN_IRQ_ru.md),
[сводка и CPU/IRQ архивы](toolkit/fast_return_irq_summary.json),
[сборка](toolkit/fast_return_irq_build.json).

## 2026-09-26 — ограниченное чтение следующего пакета и потерянные IRQ

- **Цель/база:** не задерживать готовый compact необязательным чтением.
  База `347f995`, прежние 4221 кадр/378 блоков на трёх самостоятельных TRD.
- **Изменение:** опция `--ready-packet-guard`: читать заранее только при
  наличии ≥4705 B в текущем завершённом слоте и ≥6 свободных AY-записей.
  Helper 60 B в 7C31..7C6C, дополнительные 2 B стека, новых буферов нет.
  При успехе обвязка **24→291 T, +267 T** без parser/IRQ/ULA/диска;
  при отказе 66/213/271 T, чтение отложено. Исходные сжатые байты прежние.
- **Проверки:** 11 тестов прошли; исходные три ручные суммы были на 1 T
  меньше — арифметика исправлена по инструкциям. Cold boot/смена дисков
  с mocked ROM, байты установленного кода и все реальные Fuse-диски до EOF
  проверены. 25326 AY-записей и 7501 сектор точны, retries=0, progress=100%,
  debugger writes=0; 80 байтов экрана/кадр. Занято **2542/2543/2542** сектора.
  Все 25192 фактических вызова очереди повторены в CPU-модели побайтно.
- **Результат:** fps **8,275546 / 7,973422 / 7,873682**, AY underruns
  **899→908**, плохие интервалы **661→688**, publication span
  **1855945989→1856513253 T**, +567264. Queue + AY waits
  **289707284→289646116 T**; отдельно guard **258552 T**.
  Поздних кадров по счётчику **3078→3080**, actual OUT >64 T **3659→3080**.
  Фазы не выровнены; последнее уменьшение не доказывает ускорение.
  Максимальные actual отклонения **6665355/24888708/34035839 T**;
  восстановлено 0/3/2 серии, последние остаются поздними до EOF.
- **Диагностика:** отдельная полная трасса базы диска 1 доказала пропуск
  IRQ в физических полях 922/7885: IFF=0 внутри `disk_finish`, повторной
  настройки IM2 после прямого чтения. Первый сдвиг кадра 59 по actual OUT
  скрывается нулевым `late_fields`. Новый guard не устраняет причину.
- **Решение:** ограничение оставить выключенной экспериментальной опцией,
  следующий приоритет — безопасный обход лишней настройки IRQ после
  успешного прямого чтения. Все сроки/непрерывность AY не пройдены.
  Полного сравнения всех пикселей нового Fuse, другого видео и физического
  привода нет. Корневые LFS-образы выпуска не заменены.

[Описание/команды](toolkit/READY_PACKET_GUARD_ru.md),
[сводка](toolkit/ready_packet_guard_summary.json),
[CPU](toolkit/ready_packet_guard_cpu.json),
[аудит IRQ](toolkit/ready_packet_guard_irq_baseline.json).

## 2026-09-26 — реальные вызовы очереди и предзагрузка в ожиданиях AY

- **Цель/база:** отделить CPU передач от задержек на трёх TRD `5749312`;
  неизменные 4221 кадр, 378 блоков, разрешение и AY. Первое наблюдение
  вызовов обнаружило неучтённые паузы; второй полный прогон подтвердил
  HALT при полной AY-очереди. В CPU повторены все реальные запросы,
  байты, состояния и порядок секторов, с mocked ROM.
- **Изменение:** helper 14 B в освободившихся 7C23..7C30 выполняет один
  `queue.step` при полной AY-очереди, сохраняет HL; без работы остаётся
  HALT. Нужен bank-2 ZX0; опция выключена по умолчанию. Дополнительный
  стек 2 B, новых банков/буферов нет. Обвязка **18→62 T + step** при
  работе и **18→80 T + step** без работы, без HALT wait/IRQ/ULA/ROM.
  Полная сумма queue/ожиданий **287067517→289707284 T**, +2639767 T.
- **Полный Fuse:** 4221 кадр до EOF, 25326 точных AY-записей, 7501 сектор
  ровно по одному разу, retries=0, progress=100%, 80 байтов/кадр,
  debugger writes=0. Занято прежние **2542/2543/2542** сектора.
  fps **8,278923 / 7,976366 / 7,874636**, AY underruns **1404→899**,
  плохие интервалы **1110→661**; publication span
  **1893456327→1855945989 T, −1,981051%**. Фазы не выровнены.
- **Сроки:** 3078 поздних кадров по счётчику в обоих вариантах;
  по actual OUT, с измерительным допуском 64 T, — 3659 в обоих.
  Максимальные отставания по полям **191/499/728→88/348/478**,
  actual отклонения 6381722/24675984/33964931 T. Восстановлено 0/2/2
  серии, последние не восстановлены. Главный срок, fallback и AY
  без недогрузок **не пройдены**, выпуск не заменён.
- **Проверки/неудачные пробы:** 14 тестов прошли, в том числе полная
  кольцевая AY-очередь с потреблением внутри prefetch. Новый тест сначала
  использовал чужой фиксированный SP и несовместимый word-helper;
  исправлен стенд. Первичная проверка full-снимка не учла IRQ между
  CP/JP и наблюдением: 5 снимков имели уже 30 записей вместо 31;
  проверка уточнена, данные не подгонялись. Cold/swaps с mocked ROM
  и реальные cold boots прошли. Все пиксели нового Fuse, другое видео
  и физический привод не проверены.
- **Следующие причины:** actual OUT первого диска с кадра 59 сдвинут
  на поле при нулевом `late_fields`; нужны IRQ-наблюдения. Также долгое
  optional read пакета 641 задерживает уже готовый compact 640.
  Следующий опыт — ограничить optional prefetch доступными данными/AY.

[Отчёт и команды](toolkit/AUDIO_WAIT_PREFETCH_ru.md),
[CPU базы](toolkit/transfer_cpu_profile.json), [CPU опыта](toolkit/audio_wait_prefetch_cpu.json),
[полная сводка и архивы](toolkit/audio_wait_prefetch_summary.json).

## 2026-09-26 — основной ZX0 перенесён в bank 2

- **Цель/база:** убрать ожидания ULA при исполнении ZX0. Исходники
  `19942a9`, сравнение с интегрированными TRD `b94c9ed`; те же 4221 кадр,
  378 блоков и все AY-данные. Разрешение/сжатые байты неизменны.
- **Изменение:** 279 B кода и состояния 7C23..7D39 → 8DF2..8F08;
  35 B входа, JP inline Huffman, RET пустой маски и приватный стек сохранены.
  Перенесены внутренние операнды и 22 внешние ссылки. Новых банков нет;
  fallback при отсутствии inline Huffman. Без опции все три старых TRD
  воспроизведены побайтно. Метаданные стенда учитывают итоговые адреса.
- **CPU/загрузка:** 12 тестов, включая IRQ между инструкциями и границы;
  все блоки/префиксы точны, **201086097→201086097 T (Δ0)** для квот 256 B.
  Cold boot с грязной RAM и swaps прошли с mocked ROM; по 844 проверки
  операндов (84 относительных перехода) на том. Занято **2542/2543/2542**
  сектора, видео по-прежнему 7501 сектор. Повторная сборка после LF точна.
- **Полный Fuse:** все 4221 кадр до EOF, 25326 точных AY-записей,
  retries=0, progress=100%, 80 экранных байтов/кадр, debugger writes=0.
  fps **8,172205 / 7,830816 / 7,643874**; late **3088→3077**,
  AY underruns **1612→1403**, плохие интервалы **1161→1112**.
  Publication span **1908134283→1893385416 T, −0,772947%**.
  Начальные фазы диска/IRQ не совпадают, отдельный ULA-выигрыш не заявлен.
- **Ограничения/решение:** максимальные опоздания 191/499/728 полей,
  восстановлено 0/2/2 серии; последние серии не восстановились до EOF.
  Сроки видео, fallback и непрерывный AY 50 Гц **не пройдены**. Полного
  сравнения всех пикселей нового Fuse, другого видео и физического прогона
  нет. Перенос сохранён как экспериментальная опция; корневой выпуск прежний.
  Новый профиль третьего тома: transfer 209370 T, вся работа 460812 T
  при бюджете 425448 T; следующий шаг — CPU-профиль фактических передач.

[Отчёт и воспроизведение](toolkit/BANK2_ZX0_ru.md),
[сборка](toolkit/bank2_zx0_build.json), [CPU](toolkit/bank2_zx0_cpu.json),
[полный Fuse](toolkit/bank2_zx0_summary.json), [профиль](toolkit/bank2_zx0_profile.json).

## 2026-09-26 — полный профиль задержек интегрированного плеера

- **Цель/база:** найти следующий существенный источник задержек.
  `b94c9ed`, те же три реальные TRD и 4221 кадр. Добавлены только
  debugger-наблюдения окончания передачи, prepare и draw; Z80/поток
  не менялись, Δ детерминированных T = 0.
- **Охват:** все тома до EOF, семь границ стадий для каждого кадра;
  последовательность и неперекрытие проверены. Все 25326 AY-записей,
  7501 сектор, progress 100%, 80 экранных байтов/кадр точны, retries=0.
  Late 984/851/1253, AY underruns 220/570/821; различия с прошлым запуском
  того же TRD не считать ускорением — начальные фазы не закреплены.
- **Результат:** третий том запрашивает 1269 из 1300 пакетов при отсутствии
  полностью готовых слотов. Средний transfer 215016 T, четыре стадии
  вместе 466433 T (131,56 мс) при бюджете 425448 T. Native, готовых
  за ≥1000 T до срока, но опубликованных поздно, нет. Disk/seek service
  отдельно пересечён со стадиями; остаток не назван чистым CPU.
- **Решение:** повысить приоритет переноса ZX0 из contended bank 5.
  Проверены точные размеры: 35 B входа остаются в 7C00, основной код
  и состояние **279 B** помещаются в старое тело поправок **8DF2..8F08**.
  Его предыдущий CPU-охват — 99,24% тактов ZX0, не процент ускорения.
  Сохранить JP в 8DEF и RET в 8F09; обновить все ссылки/возвраты и
  сохранить fallback при отсутствии inline Huffman. План дополнен.
- **Ограничения:** перенос ещё не реализован; выигрыша ULA/ёмкости нового
  bootstrap пока нет. Полного Fuse-сравнения каждого пикселя и физического
  прогона нет. Основной срок, резервный допуск и AY 50 Гц пока не пройдены.

[Профиль и команды](toolkit/INTEGRATED_TIMING_PROFILE_ru.md),
[покадровые данные и следующий вариант RAM](toolkit/integrated_timing_profile.json).

## 2026-09-26 — три самостоятельных TRD со всеми текущими ускорениями

- **Цель/база:** перенести CPU-прототип `4ccd740` в настоящий bootstrap.
  Те же 4221 кадр/378 ZX0-блоков, границы трёх томов, пиксели и AY 50 Гц.
- **Изменение:** очередь/compiled masks, inline literals, demand decode,
  bank-2 compact/cache и inline Huffman загружаются с TRD, без debugger patch.
  Убраны старый preload 256 секторов и стартовые копии checkpoint
  (102194 T). INIT хранит секции вплотную; четыре общих сектора повторяются
  только при загрузке. Установщик 10812 T проверен; новый выход bootstrap
  **5415→10826 T, +5411 T** один раз. Адрес входа ZX0 **10→10 T**.
- **Ёмкость:** **2543/2543/2542 сектора**, свободно 1/1/2. Поток видео
  побайтно прежний. Cold boot на испорченной RAM, промпт, отказы неверным
  дискам и переходы 1→2→3 прошли с mocked ROM. Шесть тестов прошли;
  старый bootstrap побайтно прежний, установленный runtime совпадает
  с измеренными прототипами (включая 875 inline-байтов bank 6).
- **Неудачи/измерения упаковки:** DB00 оказался старым reader, который
  выведен из употребления. Первые сборки 2545/2553/2543 и
  2544/2553/2543 не помещались. Фильтрация таблиц без фильтрации inline-кода
  экономила 62/63/63 B, но не секторы; не применена. Промежуточный том 1
  полностью проигран, затем после плотной упаковки повторены все тома.
- **Полный Fuse:** 4221 кадр до EOF, 25326 AY-записей и 7501 сектор точны,
  retries=0, 80 экранных байтов/кадр, debugger writes=0. FPS
  **8,144320 / 7,758621 / 7,557598**. Против `a6bbbb0`: late
  **3099→3088**, AY underruns **1665→1612**, плохие интервалы **1189→1161**;
  publication span **1911892404→1908134283 T (−0,197%)**.
  Фазы и размещение секторов не выровнены; это итог всего тракта.
- **Ограничения/решение:** максимальные опоздания 226/576/825 полей,
  восстановлено 0/5/2 поздних серии; последние серии до EOF не восстановлены.
  Основной срок, fallback и AY по каждому полю **не пройдены**. Нового
  полного пиксельного CPU-прогона из этих TRD и физического прогона нет.
  Сохранить экспериментальный сборщик для следующей оптимизации ожиданий
  пакетов/копий. Конвертер по умолчанию и корневой выпуск не заменять.

[Отчёт и команды](toolkit/INTEGRATED_BOOTSTRAP_ru.md),
[сборка](toolkit/integrated_bootstrap_build.json),
[полный Fuse и архивы](toolkit/integrated_bootstrap_summary.json).

## 2026-09-25 — CPU-прототип встроенных коротких поправок Хаффмана

- **Цель/база:** уменьшить обвязку CALL/RET без изменения сжатия.
  `a6bbbb0`, 4221 кадр трёх самостоятельных томов, cached Huffman,
  compiled masks и compact/cache в bank 2; точность прежняя.
- **Изменение:** 16 коротких bitmap lookup встроены в обработчик
  temporal-поправок, общий длинный путь сохранён. Новый код **875 B**,
  `EC00..EF6A` bank 6, остаток до shift pages 149 B. Вход через JP;
  стек/переменные/сжатые данные прежние. Обвязка короткого кода
  **34→10 T**, длинного **39→47 T**, вход tile **16→26 T**.
- **CPU:** все compact frame и оба native screen точны;
  **1040190921→1029825903 T, −10365018 (−0,99645%)**. Проверены все
  покадровые дельты: `10×211907−24×530886+8×32147`. Кадров с
  ухудшением CPU-стоимости — 0. Три теста прошли, включая коды на
  всех битовых смещениях, банковые совпадения PC и IRQ между инструкциями.
- **Неудачи/частичная проверка:** первичный Python smoke имел повторный
  аргумент; исправлен до Z80. Старый профиль 4971 кадра оставляет лишь
  93 B, поэтому его деревья проверены группами; таблицы нынешних томов
  помещаются целиком. Конфигурационные пробы Fuse завершались через
  тайм-аут 15 с; тот же probe через argv успешно вернул 77/314159.
  Исправлен разбор шестнадцатеричного вывода. Скрипт и оба результата
  сохранены; config route ещё не является рабочим способом запуска.
- **Решение:** сохранить CPU-прототип и продолжить интеграцию bank-6
  кода. **Нового полного Fuse-прогона, измерения fps/AY/диска и проверки
  вместимости bootstrap нет.** Конвертер и корневые TRD прежние;
  относительное ускорение CPU-стадии не выдаётся за ускорение всего плеера.

[Отчёт и команды](toolkit/INLINE_HUFFMAN_PATCHES_ru.md),
[полные покадровые результаты](toolkit/inline_huffman_patches_cpu.json),
[проверка отчёта](toolkit/verify_inline_huffman_patches.py).

## 2026-09-25 — совместный перенос кадра и compiled masks в новом тракте

- **Цель/база:** сократить итоговое время без роста потока. `1d85e6e`,
  три самостоятельных cached-Huffman TRD, compiled masks, inline
  literals и demand decode; 4221 кадр. Разрешение, пиксели и AY прежние.
- **Изменение:** включить runtime compiled masks в перенос compact/cache
  в bank 2; пакет переезжает в bank 5. 52 операнда и таблица строк,
  74 изменённых байта; Δ кода/RAM/сжатого потока — 0. `LD DE,MASKS`
  **10→10 T**, остальные исправленные инструкции тоже Δ0.
- **CPU:** все 4221 compact frame и оба native screen побайтно точны,
  покадровые такты совпали; **1040190921→1040190921 T**. Четыре теста
  прошли, включая 256 шаблонов масок и AY после каждой инструкции.
  Пересборка патчей повторяет измеренный вариант; исходный demand-decode
  режим побайтно не изменён. Копии checkpoint до начала показа — 102194 T.
- **Fuse:** все три тома до EOF, все 25326 AY-записей и 7501 сектор точны,
  retries=0, проверены 80 байтов/кадр. Publication span
  **1922315880→1911892404 T (−0,5422%)**, начальные фазы не выровнены.
  Скорость **8,135338 / 7,742861 / 7,535677 fps**. Late **3169→3099**,
  AY underruns **1812→1665**, неверные интервалы **1207→1189**.
  На первом диске late **983→984**. Последние поздние серии до EOF,
  основные сроки и fallback не пройдены; физического прогона нет.
- **Неудачные запуски стенда:** команды Windows 33968/34028/32800
  символов были отклонены до запуска Fuse. Убрана необязательная трасса
  очереди, сохранены прежние 80 проверяемых экранных байтов. Временный
  установщик до воспроизведения переведён на ZX0 standard: 185→127 B.
  Его байты и обе копии проверены CPU; рабочий ZX0 остаётся прежним.
- **Решение:** сохранить совместный режим как опцию следующего опыта.
  Следующий шаг — сокращение расходов вызовов Huffman. Интеграция в
  настоящий bootstrap и проверка его вместимости ещё впереди;
  конвертер и корневые LFS TRD не менялись. Это прогресс, не выпуск.

[Отчёт и команды](toolkit/COMBINED_UNCONTENDED_ru.md),
[CPU](toolkit/combined_uncontended_cpu.json),
[Fuse и проверяемые трассы](toolkit/combined_uncontended_summary.json).

## 2026-09-25 — распаковка до конца запроса без дробления копий

- **Цель/база:** ранняя выдача нужного префикса без повторных маленьких
  копий. `673b794`, те же три cached-Huffman TRD, inline literals,
  compiled masks, 4221 кадр/378 блоков. Сжатый поток/качество прежние.
- **Изменение:** при пустой очереди decode до
  `min(position+pending,block_length)`, затем одна копия диапазона.
  Фоновые 256 байт и история до EOF сохранены. Основная очередь
  345→360 байт плюс helper 67 байтов в E200, без новых переменных/буферов.
  Нулевой/удержанный завершённый путь Δ0 T, освобождение +27 T;
  абсолютные цены новых ветвей и листинг сохранены.
- **CPU:** полный парный прогон **291496329→285995601 T,
  −5500728 (−1,887%)**. Decode-вызовы 11430→7767, копии **8817→8817**.
  Все 3083375 байтов точны, запрет чтения неготовых байтов проверен;
  7501 сектор в прежнем порядке, каждый один раз.
- **Fuse:** все диски до EOF, 25326 AY-записей точны, retries=0.
  Late **3323→3169**, AY underruns **2043→1812**; publication span
  **1938270175→1922315880 T (−0,823%)**, начальные фазы не выровнены.
  Скорость 8,110134/7,665011/7,508671 fps. На третьем диске неверных
  интервалов стало **521 вместо 510**. Основные сроки, fallback и AY
  по каждому полю не пройдены; последние поздние серии идут до EOF.
- **Охват:** 12 тестов прошли. Fuse сверяет 80 байтов/кадр; нового
  полного пиксельного CPU-прогона нет, все пакеты проверены. Очередь
  устанавливается стендом после независимой загрузки; вместимость
  итогового bootstrap не проверена. TRD и media→TRD конвертер прежние.
- **Решение:** сохранить опцию для следующего совмещённого опыта;
  продолжить сокращать стоимость реконструкции и совмещать bank 2
  с compiled masks. Чтение длины прямо из слота ещё не реализовано.

[Подробности и команды](toolkit/DEMAND_DECODE_ru.md),
[CPU](toolkit/demand_decode_cpu.json),
[Fuse и проверяемые трассы](toolkit/demand_decode_summary.json).

## 2026-09-25 — литеральные серии ZX0 без CALL/RET

- **Цель/база:** следующий этап ускорения без изменения сжатого потока.
  `89a56ed`, три самостоятельных cached-Huffman TRD, 4221 кадр,
  378 блоков; очередь/compiled masks прежние, partial slots выключены.
- **Изменение:** перенос literal-копировщика внутрь ZX0; −27 T на серию.
  Текущий producer подаёт только ZX0, поэтому новая опция также убирает
  stored-dispatch (27→10 T на блок). Общий stored-режим сохранён.
  Декодер **330→314 байт**; данные, переменные и таблицы прежние.
- **CPU:** полный парный прогон всех пакетов и копируемых байтов;
  **298791567→291496329 T, −7295238 (−2,44%)** для очереди/ZX0.
  Сам ZX0 214766480→207471242 T. Измеренная дельта точно равна
  −27×269956−17×378. 3083375 байтов точны, 7501 сектор в прежнем порядке.
- **Fuse:** все три диска до EOF; все 25326 AY-записей и 7501 чтение точны,
  retries=0. Late **3386→3323**, AY underruns **2115→2043**.
  Publication span **1943446461→1938270175 T (−0,266%)**, начальные
  IRQ/дисковые фазы не выровнены. Сроки и fallback не пройдены,
  последние серии опозданий остаются до EOF. В Fuse 80 байтов/кадр;
  нового полного пиксельного CPU-прогона нет, все пакеты точны.
- **Охват:** 14 тестов прошли, включая IRQ после каждой инструкции,
  границы входа/выхода, очереди и прежние stored/banked режимы.
  Очередь и декодер установлены стендом после независимой загрузки.
  Вместимость нового общего bootstrap не проверена; TRD не менялись.
- **Решение:** сохранить отключённую по умолчанию опцию и применять
  в следующем опыте. Далее — decode до конца запроса с одним копированием.
  Это прогресс, но не выпуск с ровными 25/3 fps и AY по каждому полю.

[Отчёт и команды](toolkit/INLINE_LITERALS_ru.md),
[CPU](toolkit/inline_literals_cpu.json),
[сводка Fuse](toolkit/inline_literals_summary.json).

## 2026-09-25 — кэш текущего байта вместо повторного индексного чтения

- **Цель/база:** ускорить декодирование без потери сжатия. `ab76fa1`,
  три самостоятельных TRD `register-fragments`, 4221 кадр, 378 блоков.
  Сжатые байты, все пиксели и AY прежние. Очередь и compiled masks —
  прежний стенд, частичная выдача слота выключена.
- **Реализация:** `LD L,(IX+0)` 19 T → `LD L,B` 4 T; обновление B на
  байтовой границе/после длинного кода. Короткая ветвь 160→145 T,
  пересечение 165→169 T, длинная +4 T, инициализация +19 T/кадр.
  Реконструктор 4017→4024 байта; таблицы/стек прежние.
- **CPU:** все 4221 кадр, compact и оба полных экрана точны;
  1043633091→1040190921 T (**−3442170, −0,330%**), 51 кадр дороже.
  Все коды на восьми смещениях и IRQ после каждой инструкции проверены.
- **Сборка:** кэш встроен в bootstrap; **2543/2544/2543 сектора**, прежние
  1919945 байтов видео. Холодное восстановление секций и обе смены
  дисков проверены с mocked ROM. Вместимость конечного bootstrap вместе
  с очередью/compiled masks ещё не подтверждена.
- **Fuse:** до EOF всех дисков, 25326 AY-записей точны, 7501 чтение,
  retries=0. Late **3404→3386**, AY underruns **2141→2115**.
  Publication span −0,095% при невыровненных начальных фазах.
  Сроки и fallback не пройдены; последняя поздняя серия остаётся до EOF.
  В Fuse 80 экранных байтов/кадр, полный экран проверен отдельно CPU.
- **Generic:** шесть источников, 68 кадров/8 дисков/408 AY ticks,
  полный CPU-прогон. 11 тестов декодера/расписания прошли.
  Добавлена опция `--cached-huffman-byte`, требуется
  `--carry-huffman`; по умолчанию выключена.
- **Неудачи/исправления:** debugger-патчи не поместились (6278 байт
  при 4096); переход на настоящий bootstrap устранил ограничение.
  Generic первоначально выявил потерю классовых параметров контроля
  памяти при копировании CPU; исправлено, полный повтор прошёл.
- **Решение:** сохранить измеренную опцию, включать в следующий опыт;
  ускорения недостаточно для выпуска. Дальше literal CALL/RET ZX0.
  Корневые релизные TRD прежние.

[Отчёт и команды](toolkit/CACHED_HUFFMAN_BYTE_ru.md),
[CPU](toolkit/cached_huffman_byte_cpu.json),
[сборка](toolkit/cached_huffman_byte_build.json),
[Fuse и трассы](toolkit/cached_huffman_byte_summary.json),
[generic](toolkit/cached_huffman_byte_generic.json).

## 2026-09-25 — аудит и план ускорения без потери сжатия

- **Запрос/база:** изучить исходники, машинный код и формат; отдельно
  сохранить замену индексных обращений через HL/прямые адреса/регистры.
  База `4706e96` и опыт `e620bf4`, три точных TRD `register-fragments`,
  4221 кадр, 378 блоков, 1919945 сжатых / 3083375 распакованных байтов.
- **Аудит:** отдельный парсер сверил все ZX0-токены, поля всех пакетов
  учтены, код заново собран с реальными параметрами томов; сохранены
  листинги байтов/меток, SHA и статистика. 269956 литеральных серий ещё
  используют CALL/RET; 94,2% из 746050 символов Хаффмана — короткие.
  Запас около реконструктора 79 байт, около ZX0 6, в хвосте bank 6
  1100/1112/1133. Полный второй уровень Huffman сюда не помещается.
- **Предложения:** кэш текущего байта в B вместо повторного `(IX+0)`;
  встраивание ZX0 literal-copy; декодирование до конца запроса с одним
  копированием; сокращение обвязки поправок; выборочные вторичные таблицы;
  совместить ранее раздельно проверенные маски и размещение compact/cache.
- **Расчёты, не новые замеры:** кэш байта −3442170 T при сохранении B,
  устранение literal CALL/RET до −7288812 T данного участка; изменения
  соседних ветвей/инициализации проверяются отдельно. Для каждой замены
  индекса учитывать настройку адреса и сохранение регистров. Разворачивание
  всех LDIR понижено в приоритете: 96,4% серий короче 16 байт.
- **Охват/решение:** сохранить поэтапный план с проверкой всего пути кадра,
  памяти, bootstrap и независимого старта. Прогон аудита полный, нового
  исполнения Z80/Fuse нет; семантика символов опирается на прежний
  CPU-отчёт с проверкой его входных SHA. Плеер/поток этим изменением
  не меняются, Δ0 T/байт; обещания достижения сроков отсутствуют.

План: [DECODE_SPEED_PLAN_ru.md](toolkit/DECODE_SPEED_PLAN_ru.md).
Воспроизведение: [audit_decode_speed.py](toolkit/audit_decode_speed.py).
Данные: [decode_speed_audit.json](toolkit/decode_speed_audit.json),
[листинг](toolkit/decode_speed_listings/part01.txt).

## 2026-09-25 — частичное чтение активного слота ZX0

- **Цель/база:** выдавать готовый префикс, не ожидая EOF всего блока.
  База `4706e96`, точные три самостоятельных TRD, 4221 кадр, 378 блоков,
  3083375 байтов. Поток и качество не изменены, квота decode 256 байт.
- **Изменение:** +36 байт к очереди, +0 переменных; история остаётся до EOF.
  Включается только явно. Добавлена трассировка ожиданий и фаз конвейера.
  Завершённый удерживаемый слот Δ0 T, освобождение +27 T, новые ветви и
  полные формулы приведены в отчёте; до генератора масок осталось 3 байта.
- **CPU:** полный парный прогон без фонового refill между пакетами,
  298791567→310392501 T (**+3,883%**). Все байты точны, чтение
  непроизведённого префикса запрещено проверкой каждой инструкции копирования.
- **Fuse:** оба варианта до EOF всех дисков; late 3404→3240, AY underruns
  2141→2081, все 25326 AY-записей точны, прежние 7501 чтение без retries.
  Сумма publication span −0,197%, фазы старта не выровнены. На третьем диске
  неверных фактических интервалов стало 549 вместо 510. Сроки и fallback
  не пройдены, поздние серии остаются до EOF. Проверено 80 экранных байтов
  на кадр, не все пиксели; новая вместимость bootstrap не проверялась.
- **Решение:** сохранить выключенный эксперимент. Ранний доступ уменьшает
  отдельные остановки, но дробит копирование и paging. Следующая гипотеза —
  один decode до конца запроса и одно копирование. 7 тестов и верификатор
  отчётов прошли. Пилот и окончательная пара сохранены; корневые TRD прежние.

Подробности, команды и доказательства: [PARTIAL_SLOTS_ru.md](toolkit/PARTIAL_SLOTS_ru.md),
[CPU](toolkit/partial_slots_cpu.json), [полная сводка](toolkit/partial_slots_summary.json),
[скрипты CPU](toolkit/benchmark_partial_slots.py) и [Fuse](toolkit/measure_partial_slots.py).

## 2026-09-25 — адаптивные кодеки на точных трёх дисках

- **Цель/база:** проверить предложение выбирать сжатие по содержимому.
  База `0145557`, точные independently bootable TRD `register-fragments`,
  границы 1624/2921/4221, 378 блоков/3083375 исходных байтов. Вход включает
  cold-start исправления каждого диска. Разрешение, кадры и AY побайтно прежние.
- **Параметры:** исходный ZX0, удаления совпадений короче 2/3/4, ZX1,
  LZSA2 raw prefer-ratio, greedy byte RLE, stored и отдельно raw DEFLATE
  level 9/window 8 КиБ. Считаются заголовки, варианты меток, округление до
  секторов и дыры перемежения. CLI-хеши, ревизии и ключи кеша сохранены.
- **Размер:** все **3402 PC round trips** точны. Лёгкие альтернативы
  не меньше ZX0 ни на одном блоке: выбор по размеру сохраняет ZX0 на всех
  378 блоках. Смесь с DEFLATE экономит **9208 байт (0,480%)** с явной
  однобайтовой меткой; без новой цены bootstrap это −26 занятых секторов.
  Z80-DEFLATE и смешанный контейнер не реализованы, скорости нет.
  Метка без выигрыша сжатия сама переполняет второй диск на сектор.
- **CPU-подбор:** выполнены 837 допустимых ZX0-вариантов, точный поиск
  минимизирует сумму decoder T в бюджете каждого диска, **275/58/746 байт**.
  Прежний Z80-код, Δ инструкций 0 T. Полная ёмкость меняет 5 блоков,
  поток **1919945 → 1920962 байт (+1017)**. Декодер
  **208381335 → 207839136 T (−542199)**; producer/paging/адаптер
  **13247871 → 13225849 T (−22022)**. Сумма
  **221629206 → 221064985 T (−564221; −0,255%)**.
  Прочитанных секторов **7501 → 7504**, занятых **7630 → 7632**.
- **Другой бюджет:** при прежнем занятом месте меняются 3 блока, +496 байт,
  −263588 T суммарного CPU, но +1 читаемый сектор из-за заполнения дыры
  перемежения. Уменьшение занимаемого места и числа чтений — разные метрики.
- **Проверки:** семь различных полных потоков, 888 блоков через Z80 producer
  и декодер с ROM stub, точные байты/память/порядок секторов; 8 unit tests.
  Поиск сверяется с полным перебором малых задач, сохранённые отчёты —
  отдельным верификатором. IRQ/ULA/TR-DOS ROM/физическая задержка и кадры
  в Fuse не измерялись. CPU-выбор ещё не учитывает deadline каждого кадра.
- **Решение:** сохранить экспериментальный PC-подбор, не подключать его
  к основному builder без проверки общего расписания. Лёгкое смешивание
  не уменьшает эти потоки, CPU-выигрыш мал; новые внешние декодеры пока
  не обоснованы. Следующий поиск должен учитывать сроки и конечный размер
  режимов плиток после ZX0. Основной плеер и корневые LFS TRD не изменены.

Подробности и команды: [ADAPTIVE_CODECS_RESULTS_ru.md](toolkit/ADAPTIVE_CODECS_RESULTS_ru.md).
Код: [PC-кодеки](toolkit/probe_adaptive_block_codecs.py),
[CPU-подбор](toolkit/benchmark_adaptive_zx0.py),
[тесты](toolkit/test_adaptive_block_codecs.py).
Данные: [размеры](toolkit/adaptive_block_codecs_storage.json),
[CPU](toolkit/adaptive_zx0_cpu.json),
[верификатор](toolkit/summarize_adaptive_codecs.py).

## 2026-09-25 — план адаптивного выбора методов сжатия

- **Запрос:** выбирать лучший способ сжатия динамически по содержимому.
- **Аудит:** внутри FAP3 уже есть несколько режимов плиток; внешний слой
  текущей трёхдисковой сборки по-прежнему ZX0 для каждого блока.
  Поле stored старых декодеров не является готовым смешанным форматом.
- **Решение:** поиск вариантов на PC, метка и простой dispatch на Spectrum.
  Выбирать минимальный общий объём среди вариантов с допустимыми сроками,
  RAM и дисковым бюджетом; считать конечный ZX0, сектора и весь путь кадра.
  Сначала проверить точные блоки трёх дисков, затем реализовывать дополнительные
  декодеры только при обоснованном выигрыше. Все диски сохраняют холодный старт.
- **Охват:** проверены текущие `Builder.stream`, producer, режимы плиток и
  прежние отчёты. На старом FAP2 ZX1/LZSA2 не выигрывали по размеру ни на
  одном из 380 блоков; этот результат не переносится на новый поток и
  не доказывает скорость Z80. Новых измерений/selector/выпуска здесь нет,
  изменение действующего плеера по плану **0 T**.

Сохранён [план адаптивного сжатия](toolkit/ADAPTIVE_COMPRESSION_PLAN_ru.md)
с этапами, критериями отбора и полной проверкой сроков/трёх TRD.

## 2026-09-25 — пропуск масок пустых полос в RAM: отклонено

- **Цель и база:** исключить запись 32 нулевых масок и обход 16 плиток
  пустой полосы. Три независимых TRD, 4221 кадр без титров, границы
  1624/2921/4221, база `8c6c9f6` со скомпилированными масками и очередью.
  FAP3/ZX0, разрешение и AY-байты побайтно прежние; размер потока Δ0.
- **Параметры:** новый metadata-код 133 байта в bank 7, 12 flags в fixed RAM;
  полосы пропускаются лишь при нулевых масках и векторах. Стек, четыре
  слота, экраны и словари не сокращаются. Для пустой внутренней полосы
  реконструкция 1460 → 204 T, но активная полоса платит за поиск пустоты.
  Полные абсолютные формулы metadata и реконструктора — в связанном отчёте.
- **Первая попытка, прервана:** flag=1, dispatch 13 байтов/52 T. Сохранены
  1001 CPU-кадр первого диска: 241081990 → 241541239 T (+459249).
  Отладочный установщик превысил лимит таблицы из-за сдвига остального
  кода. Flag=FFh и AND сократили dispatch до 12 байтов/48 T и сохранили
  адреса следующих процедур; Fuse для первой попытки не запускался.
- **Окончательный CPU-охват, частичный:** 1825 кадров, все compact-байты
  и оба экрана совпали; старые маски намеренно отравлены, их чтение/запись
  запрещены. 447065811 → 448095223 T, **+1029412**. Первый диск проверен
  полностью: **+895277 T**. После отрицательного полного Fuse-прогона
  дальнейшее выполнение CPU намеренно остановлено; отчёт не выдаётся за
  полную проверку фильма. Прошли 4 новых и 25 прежних тестов.
- **Fuse полностью:** три холодных старта, 4221 публикация, 25326 AY ticks,
  7501 точный сектор, 80 адресов на кадр, 0 retries. Поздние кадры
  **3403 → 3409**, AY underruns **2140 → 2164**. fps теперь
  **8,057790 / 7,537513 / 7,390760**. Максимальное отставание
  **338 / 821 / 1019 полей**; восстановлены 0/1, 0/1, 2/3 серий опозданий,
  последние серии не восстановлены. Сумма publication spans +1630884 T.
  Ни точные сроки, ни fallback не пройдены; фазы диска/IRQ не уравнивались.
- **Стенд:** ограничения Windows преодолены сокращённым синтаксисом и
  выгрузкой только используемых 80 значений экрана на дисках 2/3.
  Объём проверок пикселей/AY/секторов сохранён. Прототип остаётся opt-in,
  корневые LFS TRD и настройки выпуска не изменены.
- **Решение:** отклонить общий поиск пустых полос: активных слишком много,
  а неподвижные края уже быстро пропускались. Отрицательная проверка полных
  сроков достаточна для отказа; физический дисковод и новый bootstrap не
  проверялись. Следующий выбор методов должен учитывать суммарные CPU и I/O.

Описание: [IDLE_MASKS_ru.md](toolkit/IDLE_MASKS_ru.md).
Код: [idle_masks_z80.py](toolkit/idle_masks_z80.py),
[CPU-стенд](toolkit/benchmark_idle_masks.py),
[тесты](toolkit/test_idle_masks_z80.py).
Доказательства: [итог](toolkit/idle_masks_summary.json),
[частичный CPU](toolkit/idle_masks_cpu_partial.json),
[первая попытка](toolkit/idle_masks_v1_partial.json),
[полные трассы](toolkit/idle_masks_evidence),
[проверка хешей](toolkit/summarize_idle_masks.py).

## 2026-09-25 — Полный первый блок и 32 КиБ готовых данных на старте

- **Цель/база:** после `2d2da5e` проверить гипотезу о начальном запасе
  очереди; прежние три независимых тома, все 4221 кадр и AY без изменений.
  Полный runtime сравнивается с `94c2e6f`. Сетка выбирается по началу
  тома, **4813/335/1725**, первые четыре блока дают **32768 байт** вместо
  **27955/32433/31043**. Размер RAM очереди и opcodes не менялись.
- **Реализация:** отдельный выбор `--selection start-aligned` в builder;
  сводка/верификатор поддерживают именованные наборы доказательств.
  Основной выбор не переключён. Использован сохранённый точный перебор
  ZX0; исходные TRD перед изменением сетки пересобраны побайтово.
- **Ёмкость/загрузка:** **1919945 → 1919978 байт (+33)**,
  логические секторы **7501 → 7502**, физические **7630 → 7630**.
  Использовано **2543/2544/2543**, свободно два сектора; padding нового
  комплекта нулевой. Независимое восстановление таблиц и обе смены
  диска прошли CPU-проверки с ROM stub, включая неверный диск/серию.
- **CPU:** все **4221 пакет / 3083375 байт / 378 блоков** точны.
  Очередь/ZX0/копирование/paging/адаптер **298559272 → 298565164 T**,
  **+5892 T (+0,002%)**. По томам **96151683→96219955 (+68272)**,
  **98935478→98900547 (−34931)**, **103472111→103444662 (−27449)**.
  Кадры/IRQ/ULA/ROM/физическая задержка диска исключены. Сохранены
  покадровые суммы, стадии и гистограммы инструкций.
- **Полный Fuse:** **4221 публикация / 25326 точных AY-записей /
  7502 точных runtime-сектора**, retries=0, progress=100% каждого тома.
  Изображение — 80 адресов на кадр, не новый полный попиксельный прогон.
  FPS **8,063394/7,548928/7,393284 → 8,056190/7,548049/7,397494**.
  Publication spans **1945219164 → 1945573704 T (+354540 / +0,018%)**.
- **Сроки:** late **3403→3398**, AY underrun **2140→2143**;
  max late **338/809/1011 полей**, actual OUT deviation
  **23966907/57364583/71687988 T**; actual OUT >1 поля на
  **987/1147/1264** кадрах. Интервалы вне 5..7 полей ±64 T:
  **397/473/519**; восстановлены **1/2, 0/1, 3/4** серий, последние
  не восстановлены до EOF. Оба критерия времени провалены.
  Чтение **235659555→235671756 T**, seek/side **5186440→5193416 T**
  включают ROM/IRQ/ULA/контроллер; начальные фазы не выровнены.
- **Решение:** не включать вариант по умолчанию. Больше данных на старте
  не дало нужной скорости; это не чистое выделение эффекта prefill,
  поскольку изменились все границы и распределение CPU. Простой перебор
  сетки больше не основной путь. Следующее направление — уменьшение
  промежуточных записей при разборе масок и подготовке тяжёлых кадров.
  Простое сокращение входного буфера даёт только 1058 байт в худшем томе
  (максимальный packet 3647 байт), недостаточно для второго compact-кадра.
  Иная раскладка 128 КиБ не исключена. Корневые TRD не заменены; размер
  release-bootstrap нового runtime ещё не проверен, цель не достигнута.
- **Материалы/проверки:** [описание и команды](toolkit/ZX0_START_ALIGNED_ru.md),
  [раскладка](toolkit/zx0_start_aligned_build.json),
  [CPU](toolkit/zx0_start_aligned_cpu.json),
  [сводка/хеши](toolkit/zx0_start_aligned_summary.json),
  [верификатор](toolkit/verify_zx0_block_phase.py). Новый и предыдущий
  полные наборы доказательств прошли проверку.

## 2026-09-25 — Полная проверка смещения блоков ZX0

- **Цель/база:** продолжить checkpoint `28fb1a9`; прежние 4221 кадр без
  титров, три независимых тома, границы 1624/2921/4221. Внешнее сжатие
  на базе `5bad85f`, полный runtime для сравнения — `94c2e6f` (очередь
  четырёх блоков и compiled masks). Пиксели, AY и FAP3-пакеты неизменны.
- **Параметры/размер:** девять смещений сетки на том, **27 вариантов**;
  ZX0 optimal, блоки до 8192 байт. Минимальный размер выбирает
  **5120/4096/0**, поток **1919945 → 1919263 байта (−682)**.
  Каждый вариант проверен обратной распаковкой, phase=0 побайтово
  воспроизводит исходный сжатый поток. Исходные три TRD также
  пересобраны побайтово с полным набором bootstrap-параметров.
- **Реальная раскладка:** **2543/2544/2543 → 2543/2543/2543 сектора**,
  свободно **2 → 3 сектора** во всём комплекте. Логическое чтение
  **7501 → 7499 секторов**; на первом томе выигрыш поглощён padding.
  Холодное восстановление таблиц и обе смены дисков прошли CPU-проверку
  с подменённой ROM, включая приглашение и отказы для чужой серии/диска.
  Размер отдельного release-bootstrap очереди/compiled masks не проверен.
- **CPU:** все **4221 пакет / 3083375 байт / 380 блоков** точны.
  Очередь с распаковкой, копированием, paging и адаптером:
  **298559272 → 298476806 T, −82466 T (−0,028%)**.
  По томам: **96151683→96216372 (+64689)**,
  **98935478→98788323 (−147155)**, **103472111→103472111 (0)**.
  Новых opcodes нет; кадры/IRQ/ULA/ROM/физический диск исключены.
  Сохранены покадровые суммы, стадии и гистограммы инструкций.
- **Полный Fuse:** все **4221 публикация / 25326 точных AY-записей /
  7499 точных runtime-секторов**, retries=0, progress=100% каждого тома.
  Изображение — 80 проверяемых адресов на кадр, не новый полный
  попиксельный прогон. FPS **8,063394/7,548928/7,393284 →
  8,064196/7,513915/7,393284**. Publication spans
  **1945219164 → 1947984577 T (+2765413 / +0,142%)**.
- **Сроки:** late **3403 → 3385**, AY underrun **2140 → 2179**;
  максимальное опоздание **330/848/1015 полей**, actual OUT deviation
  **23399638/60129984/71971622 T**. Actual OUT >1 поля на
  **986/1111/1272** кадрах; интервалы вне 5..7 полей ±64 T —
  **392/468/513**. Восстановлены **1/2, 3/4, 2/3** серий; последние
  серии до EOF не восстановлены. Оба критерия времени провалены.
  Чтение **235659555→235648361 T**, seek/side **5186440→5190440 T**
  включают ROM/IRQ/ULA/контроллер; начальные фазы не выровнены.
- **Решение:** не включать минимизацию размера по смещению в основной
  вариант: экономия одного сектора сопровождается ухудшением темпа.
  На старте четырёхблочная очередь содержит на **3072/4096/0 байт**
  меньше данных; это гипотеза о части эффекта, не доказанная причина.
  Следующий отбор должен учитывать запас готовых данных и CPU вместе
  с физическими секторами. Корневые TRD не заменены, цель не достигнута.
- **Материалы/проверки:** [описание и команды](toolkit/ZX0_BLOCK_PHASE_ru.md),
  [перебор](toolkit/zx0_block_phase_probe.json),
  [сборка](toolkit/build_zx0_block_phase.py),
  [раскладки](toolkit/zx0_block_phase_build.json),
  [CPU](toolkit/zx0_block_phase_cpu.json),
  [полная сводка и хеши трасс](toolkit/zx0_block_phase_summary.json),
  [верификатор](toolkit/verify_zx0_block_phase.py). Два теста границ
  прошли в checkpoint; полный новый набор доказательств проверен.

## 2026-09-25 — Промежуточный снимок подбора границ ZX0

- **Цель/база:** `5bad85f`, уменьшить внешний поток ZX0 без изменения
  пакетов FAP3, пикселей и AY. Три независимых тома, границы кадров
  1624/2921/4221, исходные raw и TRD из эксперимента register fragments.
- **Параметры:** блоки до 8192 байт, смещение сетки 0..7168 с шагом 1024
  и дополнительное выравнивание по началу каждого тома. Новые инструкции
  проигрывателя не вводятся; это отдельный экспериментальный builder.
- **Сохранённый результат:** весь первый том, 1624 кадра, шесть завершённых
  вариантов со смещениями 0/1024/2048/3072/4096/4813. Размеры потока
  **641005/640871/640806/640812/640794/640778 байт**: лучшая измеренная
  экономия **227 байт**, пока **2504 логических сектора** у каждого.
  Это не итог всех вариантов или трёхдискового комплекта.
- **Проверка:** все блоки этих вариантов обратно распакованы и дают
  прежние байты пакетов, включая начальные независимые native maps.
  Смещение 0 побайтово воспроизводит исходный сжатый поток. Два теста
  границ прошли, проверены суммы блоков и размеры сохранённого отчёта.
  Полный CPU, фактическое чтение с дискеты, Fuse и сроки кадров ещё
  не измерялись; отсутствие изменений opcodes не означает равную цену
  распаковки разных потоков.
- **Решение:** по запросу пользователя сохранить текущий прогресс отдельным
  коммитом. Замер продолжает работать; стабильный checkpoint отделён от
  обновляемого отчёта. Кандидат не включён по умолчанию и не является
  выпуском; новые TRD в этом снимке не создавались.
- **Материалы:** [команды и ограничения](toolkit/ZX0_BLOCK_PHASE_ru.md),
  [подбор](toolkit/probe_zx0_block_phase.py),
  [builder](toolkit/zx0_block_phase.py),
  [промежуточный отчёт](toolkit/zx0_block_phase_checkpoint.json),
  [тесты](toolkit/test_zx0_block_phase.py).

## 2026-09-25 — Lossless-выбор быстрых фрагментов по локальной цене

- **Цель/база:** `94c2e6f`, разгрузить тяжёлые кадры без изменений пикселей
  и AY. Текущий ролик без титров, 4221 кадр, таблицы тома 3; выбор меняет
  только весь третий том, кадры 2921..4220 (1300 кадров). Существующая
  подготовка следующего кадра и очередь не устраняют все опоздания.
- **Параметры:** замена motion/Huffman плиток готовыми режимами 85..88,
  допуски 0/16/64 бита локального роста, эвристическая экономия ≥400 T.
  Скалярный decoder проверил все 4221 состояния и AY для каждого варианта;
  контрольная пересборка побайтово равна исходному FAP3. Качество,
  разрешение, таблицы, native maps и машинные инструкции прежние.
- **Optimal ZX0, третий том:** база **638742 байта**, варианты
  **638789/639650/650358**, разница **+47/+908/+11616 байт**.
  Заменены **50/1413/4843** плитки на **36/429/917** кадрах.
  Все блоки проверены обратной распаковкой. Вариант 0 уменьшил raw на
  32 байта, но увеличил ZX0: локальные размеры не гарантируют внешний размер.
- **Реальная раскладка:** прежний независимый bootstrap с исходными
  настройками; база и вариант 0 занимают **2543/2544** сектора,
  варианты 16/64 — **2545/2589**, переполнение **1/45 секторов**.
  У варианта 16 логический рост +3 сектора, физический +2 из-за padding;
  переразбиение трёх томов не измерено. Отдельный новый bootstrap очереди
  и compiled masks этим размером не подтверждён; TRD не опубликованы.
- **CPU варианта 64:** исполнены все 1300 кадров тома; каждый compact-байт
  и оба полных экрана совпали. **318721798 → 309822828 T**,
  **−8898970 T / −2,79% стадии**, более медленных кадров 0.
  База — сохранённое полное исполнение с равной ценой инструкций,
  повторного старого CPU-прогона нет. Новых opcodes 0; обычные metadata,
  carry Huffman и register fragments. ZX0/reader/queue/IRQ/ULA/ROM/диск
  в эту сумму не входят; это не измерение полной скорости воспроизведения.
- **Попытки/проверки:** первый capacity-вызов остановлен несовпадением
  контроля: были пропущены параметры deferred=248, keepalive=64 и frame
  service. Их восстановили, исправленный контроль совпал, все четыре
  раскладки завершены. Тест выбора/границ и сохранности изображения/AY
  прошёл; хеши, покадровые суммы и раскладки проверяет сохранённый скрипт.
  Fuse не запускался, кандидат с измеренным выигрышем не помещается.
- **Решение:** политику по умолчанию не включать. Широкие замены не дают
  необходимого баланса скорости и места; вариант 0 слишком мал для цели.
  Для дальнейшего отбора нужна фактическая цена блоков ZX0, включая их
  границы, вместе с ценой CPU. Это ограничение измеренной политики,
  не доказательство невозможности остальных форматов.
- **Материалы:** [описание/команды](toolkit/FRAGMENT_COST_SELECTION_ru.md),
  [отбор и ZX0](toolkit/probe_fragment_cost_selection.py),
  [ZX0-отчёт](toolkit/fragment_cost_selection_probe.json),
  [CPU-прогон](toolkit/fragment_cost_selection_cpu.json),
  [раскладки](toolkit/fragment_cost_selection_capacity.json),
  [проверка отчётов](toolkit/verify_fragment_selection.py).

## 2026-09-25 — Скомпилированные маски в полном проигрывателе

- **Цель/база:** ускорить метаданные без изменения сжатого потока.
  Прототип `5b2175f`; полный baseline — очередь `30de92c`, те же три
  независимых TRD, все 4221 кадр, границы 1624/2921/4221, прежние AY/пиксели.
- **Изменение:** генератор подключён перед prefill, parser вызывает новый
  decoder в банке 7. Код 73+97 байт, таблица/подпрограммы 5376 байт
  E400..F8FF; четыре слота ZX0, экраны, IRQ и TR-DOS не сокращены.
  Сочетание с переносом compact/cache пока явно не разрешено стендом.
  Общий POP BC с полным путём убирает ещё 4 байта и 10 T на частичную
  группу относительно сохранённого прототипа.
- **CPU:** реально исполнены старый/новый декодеры всех кадров, проверены
  все 480 байт масок, padding, вход/указатель, записи, стек и инструкции.
  **80531227 → 65696334 T**, −14834893 T (−18,42% стадии).
  Частичная группа: `370+8*k → 276+5*k-2*b`, разница `-94-3*k-2*b` T;
  нулевая/полная 161/227 T, дельта 0. Общая обвязка 158 T, начальная
  генерация 201509 T. IRQ/ULA/диск в эти CPU-суммы не входят.
- **Полный Fuse:** все 4221 публикация, 25326 AY-записей и 7501 сектор
  точны; retries=0, progress=100% всех дисков. Проверяется 80 адресов
  изображения на кадр; полного попиксельного прогона здесь нет.
  Late **990/1146/1272 → 989/1142/1272**, всего **3408 → 3403**;
  AY underruns **354/848/1050 → 326/803/1011**, всего **2252 → 2140**.
  fps **8,0410/7,5096/7,3606 → 8,0634/7,5489/7,3933**.
  Сумма publication spans **1953160861 → 1945219164 T**, −7941697 T.
- **Сроки/диск:** max late 331/808/1015 полей, actual OUT deviation
  23470546/57293676/71971622 T. Восстановления 1/2, 3/4, 2/3 серий,
  последние серии до EOF не восстановились. Интервалы вне 5..7 полей
  ±64 T ухудшились с 381/463/509 до 407/468/509. Оба временных критерия
  провалены. Чтение **235674104 → 235659555 T**, seek/side
  **5190634 → 5186440 T**, включая ROM/IRQ/ULA/контроллер. Начальные
  фазы диска/IRQ не выровнены, это не изолированный замер экономии CPU.
- **Проверки/попытки:** **15 тестов прошли**, включая AY IRQ после каждой
  инструкции генератора и шести шаблонов decoder, все 256 шаблонов без
  IRQ, прежние queue/paging/диск-тесты. Первая полная серия Fuse завершена
  без повторов. Архивы трасс, команд, nonce и хеши сохранены и проверены.
- **Решение:** сохранить отдельным вариантом `--compiled-masks`, по
  умолчанию не включать. Есть измеренный выигрыш, но плавность не достигнута;
  новый bootstrap/его ёмкость и физический дисковод не проверены.
  Выпускные TRD остаются прежними.
- **Материалы:** [описание/команды](toolkit/COMPILED_MASKS_ru.md),
  [полный CPU-бенчмарк](toolkit/benchmark_compiled_masks.py),
  [CPU-отчёт](toolkit/compiled_masks_cpu.json),
  [сводка](toolkit/compiled_masks_summary.json),
  [архивы свидетельств](toolkit/compiled_masks_evidence),
  [проверка архивов](toolkit/verify_compiled_masks_evidence.py).

## 2026-09-25 — Контрольная точка прототипа скомпилированных масок

- **Цель/база:** сохранить текущий прогресс по запросу пользователя.
  База `cb92c3e`; прототип ускоряет существующую двухуровневую распаковку
  480 байт масок без изменения формата потока. В проигрыватель пока не подключён.
- **Изменение:** Z80 при инициализации создаёт 256 коротких подпрограмм
  копирования/заполнения нулями. Для частичной маски выбирается готовая
  подпрограмма; отдельные быстрые пути нулевой и полной масок сохранены.
  Генератор — 71 байт в E180, декодер — 101 байт в E300. Таблица адресов
  и тела занимают 5376 байт E400..F8FF банка 7 и создаются в RAM.
  Во время исполнения банк 7 должен оставаться подключённым.
- **Такты CPU:** прежняя частичная группа `370 + 8*k` T, новая
  `286 + 5*k - 2*b` T, разница `-84 - 3*k - 2*b` T,
  где `k` — число установленных битов, `b` — младший бит маски.
  Нулевая/полная группы: 161/227 T, дельта 0 T. Цены включают одну
  итерацию цикла, исключают завершающий RET помощника. На весь декодер
  добавляется 158 T общей обвязки. Инициализация исполняется за
  **201509 T** без внешнего CALL; IRQ, ULA и диск не включены.
- **Проверка:** два CPU-теста прошли. Реально исполнены генератор и
  декодер для всех 256 повторяющихся шаблонов присутствия; проверены
  сгенерированные байты, все 480 выходных байтов, четыре нулевых байта
  padding, входной указатель, сохранность входа, стек и допустимые адреса
  записи. Такты каждой инструкции и итоговая формула совпали с моделью.
  Воспроизведение: `PYTHONPATH=toolkit python -m unittest
  toolkit/test_compiled_masks_z80.py -v` (нужны зависимости проекта).
- **Ограничения/решение:** сохранить как незавершённый эксперимент.
  Проверок IRQ, полного мультфильма, интеграции с очередью, Fuse и нового
  bootstrap пока нет; выигрыш скорости воспроизведения и итоговая дисковая
  ёмкость не измерены. Основной проигрыватель и TRD не изменены.
- **Материалы:** [прототип](toolkit/compiled_masks_z80.py),
  [воспроизводимые CPU-тесты](toolkit/test_compiled_masks_z80.py).

## 2026-09-25 — Compact/cache в фиксированном банке без задержек ULA

- **Цель/база:** `30de92c`, ускорить восстановление и вывод без новых
  секторов, меняя размещение рабочих данных. Те же три независимых TRD,
  все 4221 кадр, границы 1624/2921/4221, прежние пиксели, Huffman, ZX0 и AY.
- **Изменение:** compact 6400..72FF → A800..B6FF, кэш 7400..77FF →
  A400..A7FF, маски A4C0..A69F → B700..B8DF. Пакет перемещён в
  6400..765F, сохраняет 4704 байта с guard. Экраны, код, стек, AY,
  TR-DOS и четыре слота ZX0 не расширены; дополнительной runtime RAM нет.
  В горячем коде меняются лишь адресные операнды и таблица строк кэша.
- **CPU:** полное исполнение нового варианта проверило каждый compact-байт
  и оба полных экрана на всех кадрах. **1058467984 T**, совпадает с прежней
  моделью стадий для трёх наборов таблиц; дельта **0 T** на каждом кадре.
  Это не повторное полное исполнение старого варианта; базой служит
  ранее проверенная модель. Парные исполнения смешанных тестовых кадров
  тоже совпали. Хост подаёт пакеты, IRQ/ULA/ZX0/диск исключены.
  В отчёте записаны абсолютные/относительные цены каждого изменённого
  операнда: LD rr,nn 10→10 T, CP/OR n 7→7 T.
- **Cold boot:** отладочный установщик переносит уже загруженные 3840
  и 1024 байта checkpoint, **102194 CPU T** до старта драйвера.
  Копирование исполнено и побайтово проверено на Z80. Это временный
  стенд; нового bootstrap и его дисковой ёмкости пока нет.
- **Проверка модели Fuse:** после настоящего TRD boot три цикла чтения
  A800 дали ровно **310000 T** каждый. При чтении 6400 окончательный
  повтор дал **312600/312639/312865 T**. Отдельные сырые frame/tstate
  счётчики подтвердили поле **70908 T** и реальную задержку банка 5.
  Повтор для сохранения LF-трасс дал другую начальную фазу; первый
  замер был 312637/312601/312826 T, с тем же результатом проверки.
- **Полный Fuse:** 4221 публикация, 25326 AY-записей в правильном порядке,
  7501 точный сектор, retries=0, progress=100% на всех дисках.
  Fuse проверяет 80 адресов каждого кадра; полные экраны — CPU-стенд.
  Late **990/1146/1272 → 989/1125/1273**, всего **3408 → 3387**.
  AY underruns **354/848/1050 → 325/813/1019**, всего **2252 → 2157**.
  fps между реальными OUT: **8,0410/7,5096/7,3606 →
  8,0642/7,5393/7,3866**. Разница суммы трёх publication spans:
  **1953160861 → 1946495507 T**, −6665354 T.
- **Нарушения сроков:** максимум 330/819/1024 поля;
  actual OUT deviation 23470545/58073654/72609796 T. Восстановились
  1 из 2, 5 из 6, 2 из 3 серий, последняя серия каждого диска — нет.
  Интервалы вне 5..7 полей ±64 T ухудшились с **381/463/509** до
  **403/469/510**. Фактических OUT за пределом поля:
  **990/1146/1272 → 1091/1118/1272**. Оба критерия времени провалены;
  точные AY-данные не означают своевременное звучание при underrun.
- **Диск/ограничения сравнения:** служба чтения 235674104→235724411 T,
  seek/side 5190634→5191609 T. Включены ROM/IRQ/ULA/контроллер.
  Начальные фазы IRQ/вращения не выровнены; разницу полных прогонов
  нельзя целиком приписывать ULA. Физический дисковод не проверен.
- **Попытки/проверки:** ранний CPU smoke — 9 кадров, не полный результат.
  Первая попытка Fuse остановлена до эмуляции лимитом командной строки;
  документированные сокращения команд и равноценные более короткие
  выражения сохранили всё покрытие. **10 тестов прошли**, включая 256
  масок, смешанные предикторы/фрагменты и AY после каждой инструкции,
  прежние тесты очереди и paging. Трассы, nonce и контрольные суммы сохранены.
- **Решение:** оставить как отдельный воспроизводимый вариант. Выигрыш
  средней скорости лишь 0,3–0,4%, часть метрик интервалов хуже; по умолчанию
  не включать. Для цели нужен более крупный выигрыш тяжёлых кадров или
  их предварительной подготовки. Корневые TRD и конвертер не заменены.
- **Материалы:** [описание/команды](toolkit/UNCONTENDED_FRAME_ru.md),
  [перенос](toolkit/uncontended_frame.py),
  [полный CPU-бенчмарк](toolkit/benchmark_uncontended_frame.py),
  [CPU-результат](toolkit/uncontended_frame_cpu.json),
  [аудит Fuse](toolkit/audit_fuse_memory.py),
  [проверка памяти/поля](toolkit/uncontended_frame_machine.json),
  [сводка](toolkit/uncontended_frame_summary.json),
  [архиватор](toolkit/summarize_uncontended_frame.py),
  [полные свидетельства](toolkit/uncontended_frame_evidence).

## 2026-09-25 — Четыре слота ZX0 в полном кадровом проигрывателе

- **Цель/база:** `248db65`, подключить прямой секторный producer к
  кадровому потребителю и измерить весь ролик. Те же три TRD, все 4221
  кадр, границы 1624/2921/4221, прежние пиксели, Huffman и AY-данные.
- **Изменение:** исполняемая Z80-очередь в банке 7 управляет четырьмя
  слотами 0/1/3/4; `take` освобождает слот только после потребления
  последнего байта. Первые четыре блока готовы до старта; затем шаг
  producer читает сектор или исполняет ZX0 quantum +256 байт между
  токенами. При нехватке готового блока чтение синхронно ждёт producer.
  Копируется только пакет, окончательный экран строится в скрытом банке.
- **RAM:** до 32 КиБ распакованных данных, без отдельного дискового
  кольца; queue/state **345 байт**, fixed bridge **131 байт**.
  Bridge 6100..6182 заменяет deferred-reader; queue E000..E158 банка 7
  занимает прежнюю историю ZX0. Экраны, compact/cache, AY, IRQ, стек,
  Huffman и TR-DOS workspace остаются на прежних местах.
- **CPU, весь материал:** все 4221 пакет / **3083375 байт** точны.
  Прежний reader **323484229 T**, очередь с producer/bridge/copy/paging
  **298559272 T**, разница **−24924957 T**. В каждом варианте два
  запроса на кадр; новая очередь заполняется перед каждым пакетом.
  Это CPU-сравнение, не расписание: старое дисковое кольцо идеальное,
  новый ROM замокан, IRQ/ULA/диск/реконструкция исключены.
- **Другие такты:** copy-ядро `48+16N+18ceil(N/32)` T; новый bridge
  с paging/RET `349+16N+18ceil(N/32)` T (+4 T для регионов 2/3),
  внешний CALL +17 T. Удалённая запись ISR в старый `history_page`
  экономит **33 T/публикацию**; fast IRQ без AY/paging-restart
  **775 → 742 T**. Проверка ready перед HALT без lookahead добавляет
  **27 T** после idle-helper, предотвращая ожидание лишнего поля.
- **Настоящий Fuse, финальный полный прогон:** 4221 OUT-публикация,
  **25326 точных AY-записей**, все **7501 сектор** точны, retries 0,
  progress=100% на каждом диске. Проверены 80 адресов каждого кадра,
  не полное изображение. Каждый исходный TRD cold-boot, затем отладчик
  устанавливает новый код; старые 256 preload-секторов на диск
  отбрасываются. Runtime 7501 против 6733 объясняется этой разницей
  границ измерения, поток не увеличен.
- **Реальные сроки:** late **1062/1195/1297 → 990/1146/1272**,
  всего **3554 → 3408**. AY underruns **366/930/1088 → 354/848/1050**,
  всего **2384 → 2252**. Частота между первым и последним OUT:
  **8,0267/7,4389/7,3290 → 8,0410/7,5096/7,3606 fps**.
  Максимум **359/853/1054 поля**, фактический OUT deviation
  **25455969/60484531/74737038 T**. Восстановление серий: 0 из 1,
  0 из 1, 2 из 3; последняя серия каждого диска не восстановилась.
  Интервалы вне проверяемого окна 5..7 полей ±64 T: **381/463/509**.
  И номинальные сроки, и fallback провалены; точность AY-данных не
  означает правильную частоту их подачи при underrun.
- **ROM/диск:** служба чтения **235674104 T**, seek/side **5190634 T**,
  прежние **207615458/4658306 T** с другой границей preload.
  Включены controller/ROM/ULA/IRQ; это не отдельный замер физической
  задержки дискеты. Новый замер до `disk_finish` также включает проверку
  успешного быстрого чтения: +57 CPU T после `fast_disk_return`, где
  останавливался старый замер. Реальный дисковод не проверялся.
- **Непринятые/промежуточные попытки:** до эмуляции превышен лимит
  командной строки (38721, затем 33777 символов); временный установщик
  сжат ZX0, повторный экспорт того же сектора объединён, покрытие
  сохранено. Первый исполнившийся вариант остановился после 7 кадров:
  IRQ ещё писал в старый history-адрес, теперь попавший в producer.
  Удалена эта запись нового формата, регрессионный тест добавлен.
  Первый полный прогон и повтор после ready-проверки имеют одинаковые
  late/underrun; финальные фазы OUT отличаются и сохранены отдельно.
- **Проверки:** **24 теста прошли**; полное CPU-сравнение всех пакетов,
  все три Fuse-диска до EOF, свежесть трасс по nonce, полные секторные
  байты, AY-порядок, защита слотов, EOF/границы и paging/IRQ.
- **Решение:** сохранить очередь как проверенный эксперимент для
  дальнейшего удешевления тяжёлых кадров и улучшения подготовки заранее.
  Выпуском не считать. Новый bootstrap/его ёмкость ещё не собраны,
  универсальный конвертер этот режим не выбирает. Корневые TRD прежние.
- **Материалы:** [описание/команды](toolkit/SLOT_QUEUE_ru.md),
  [очередь](toolkit/slot_queue_z80.py),
  [подключение](toolkit/slot_queue_player.py),
  [CPU-измеритель](toolkit/benchmark_slot_queue.py),
  [CPU-отчёт](toolkit/slot_queue_cpu.json),
  [сводка/индексы пропущенных сроков](toolkit/slot_queue_summary.json),
  [полные отчёты и трассы](toolkit/slot_queue_evidence).

## 2026-09-25 — Прямая загрузка секторов в банк распаковки ZX0

- **Цель/база:** `03013e3`, убрать две полные пересылки сжатого блока,
  сохранив прежние три самостоятельных TRD и их потоки. Все 378 блоков,
  3083375 выходных байт, границы 1624/2921/4221; пиксели/AY не перекодируются.
- **Изменение:** исполняемый Z80 producer читает сектор прямо в нижние
  8 КиБ выбранного банка 0/1/3/4; верхние 8 КиБ — выход ZX0. Между слотами
  через BC00 переносится только общий крайний сектор. Заголовки на границе
  секторов, линейный первый трек и дальнейшее чередование разбираются Z80.
  Один `step` выполняет не более одного успешного секторного чтения.
- **CPU/такты:** переменный вход ядра добавляет ровно **6 T/блок**,
  всего **2268 T**, и 2 байта состояния. По умолчанию машинные байты
  существующих декодеров прежние. Пересылка сектора **4235 T**, с CALL
  **4252 T**. Выполнена 751 пересылка: **192256 байт** вместо 3836866
  байт двух полных пересылок из предыдущей гипотезы. Все инструкции
  producer/paging/adapter/seek проверяются по таблице тактов.
- **CPU-метрика на полном материале:** прежнее banked-ядро
  **265376220 T**; новое ядро **208381335 T**, весь новый producer
  **13247871 T**, вместе **221629206 T**, разница **−43747014 T**.
  Это явно различные границы сравнения: слева не добавлены прежние
  adapter/header costs; справа включены новые parsing/copy/paging и
  CALL/JP к ROM-заглушкам. ROM/IRQ/ULA/диск и внешние запросы host
  исключены. Это не замер ускорения всего плеера.
- **RAM:** четыре слота в банках 0/1/3/4, 32 КиБ входа + 32 КиБ выхода,
  отдельного дискового кольца нет. Сектор BC00..BCFF прежний. Код ядра
  7C00..7D49 (330 байт), producer 7D50..7EBF (368 байт). Последние
  48 байт перекрывают начало прежнего stream reader: для подключения
  нужен новый reader очереди. Стек, оба экрана, compact/cache, таблицы,
  AY/IRQ/TR-DOS остаются на прежних местах. Владение слотами пока
  обеспечивает стенд; sustained delivery с кадровым потребителем не доказана.
- **CPU-покрытие:** 7501 сектор в исходном порядке, без повторов,
  все блоки побайтно точны. 7879 шагов producer, максимум **5258 CPU T**
  за шаг без ROM/IRQ/ULA; проверены 200 реальных смещений входа.
  **12 тестов прошли:** пограничные заголовки, курсор диска, общие сектора,
  четыре слота, screen bit, short-read fallback, неверные длины,
  совместимость старых байтов и AY IRQ после каждой инструкции ядра,
  включая переменный вход.
- **Полный Fuse-компонент:** исходные TRD независимо cold-boot,
  затем до штатного драйвера отладчик устанавливает опытный цикл.
  После bootstrap заново прочитан весь поток; его исходные 256 секторов
  предзагрузки находятся вне измеренного прохода. Проверены все **7501
  сектор и 3083375 выходных байт**, **0 retries**. IRQ включены,
  входы/счётчики совпали **2368/2427/2486**, AY и видео отключены.
  Producer **255823357 T**, ядро с драйвером **257735572 T** реального
  времени; служба чтения **234422717 T**, seek/side **5181626 T**
  являются вложенными частями, их нельзя прибавлять второй раз.
  Эти суммы включают ROM/controller/ULA/IRQ; разница с CPU не названа
  физической задержкой дискеты. Вспомогательный экспорт байтов исключён.
- **Непринятые запуски:** первый debugger script превысил внутренний
  лимит длины команды; выражения с адресом сектора сокращены общей
  переменной. Следующий запуск завершился ошибкой получения stdout,
  первопричина не установлена; добавлены сохранение stderr и проверка
  свежего nonce. После этого все три потока полностью проверены; затем
  полный прогон дополнен регистрацией IRQ. Неудачные попытки не засчитаны.
- **Решение:** сохранить прямой producer как компонент для интеграции
  очереди: проблема полной пересылки устранена без роста потока/секторов.
  Reader слотов, кадровый планировщик, AY и фактические публикации ещё
  не объединены; 8⅓ кадра/с и fallback не подтверждены. Основной
  проигрыватель, корневые TRD и статус выпуска не изменены.
- **Материалы:** [описание/команды](toolkit/DIRECT_SLOT_INPUT_ru.md),
  [producer](toolkit/direct_slot_input_z80.py),
  [CPU-скрипт](toolkit/benchmark_direct_slot_input.py),
  [CPU-отчёт](toolkit/direct_slot_input_cpu.json),
  [Fuse-скрипт](toolkit/measure_direct_slot_fuse.py),
  [сводка с хешами](toolkit/direct_slot_input_summary.json),
  [полные отчёты и сжатые трассы](toolkit/direct_slot_input_evidence).

## 2026-09-25 — ZX0 в одном банке: измерено ядро и обновлена модель очереди

- **Цель/база:** `a562c4d`; подготовка тяжёлых кадров заранее, без
  копирования полного экрана. Прежние три самостоятельных TRD,
  границы 1624/2921/4221, пиксели, разрешение и AY не изменены.
- **Изменение:** отдельное экспериментальное ядро с входом C000..DFFF
  и выходом E000..FFFF одного банка 1/3/4. Сохраняется остановка между
  копированиями ZX0 и частный стек; вход целого блока заранее в слоте.
  Основной плеер/конвертер и корневые TRD не изменены.
- **Измерено на всех блоках настоящих TRD:** 378 блоков, 3083375 выходных
  байт, 1918433 байта ZX0 (1919945 с заголовками). Два декодера побайтно
  восстановили все блоки при одинаковых запросах по 256 выходных байт.
  Ядро **265376220 → 208379067 T (−56997153)**; код **651 → 328 байт**.
  Самый долгий вызов в этом наборе — **39104 T**, не универсальный предел.
  База включает обычный OUT/refill, но не runtime-helper безопасного
  paging; внешний CALL/descriptor setup/IRQ/ULA/ROM/диск исключены.
- **Стоимость доставки:** для двух LDI-пересылок сжатого входа через
  фиксированную память только копирование добавляет **61389856 T**.
  Итого минимум **269768923 T**, то есть **+4392703 T** к измеренной базе;
  циклы/управление/новый paging ещё сверху. Это нижняя оценка выбранного
  пути с LDI, а не всех возможных способов доставки.
- **RAM:** рассматриваются кольцо 16 КиБ в банке 0 и три слота по
  8 КиБ входа + 8 КиБ выхода в банках 1/3/4. Код 7C00..7D47,
  стек 7B70..7BDF, банки 2/5/6/7 сохраняют прежние назначения.
  Размещение queue/control и доставка диском в уменьшенное кольцо
  не реализованы. Четыре и семь слотов в модели — только чувствительность.
- **Новая модель:** все 4221 кадр с текущими таблицами каждого тома,
  холодные первые два кадра, формулы AY и стоимости копирования пакета.
  При 3 слотах и бесплатном входе равномерная свободно останавливаемая
  распаковка даёт **24/54/107 = 185** поздних кадров; с 32 T/байт
  входа — **45/99/175 = 319**. Измеренные неделимые вызовы дают
  **33/66/117 = 216** и **86/222/350 = 658** соответственно. Во втором
  варианте весь перенос блока сгруппирован с первым вызовом, а не
  распределён по секторам; это отдельное ограничение политики модели.
  В первом сценарии худшие дефициты **377633,215 / 6356673 / 3016336,628 T**;
  на диске 2 одна серия задержек не восстанавливается до EOF.
- **Покрытие:** шесть тестов границ, сохранности, AY IRQ после каждой
  инструкции и учёта работы/ёмкости очереди прошли. На **93 выбранных
  кадрах** исполняемый Z80 подтвердил точную стоимость рассчитанной
  стадии, весь compact-кадр и оба native-экрана, включая холодные старты
  и тяжёлые места. Это частичная проверка новой композиции; исходная
  стадия с таблицами тома 1 ранее исполнялась полностью. Фактические OUT,
  fallback-джиттер, новый полный плеер и диск в этом опыте не проверялись.
- **Прерванная попытка:** первый расчёт очереди и его синтетическая
  диагностика остановлены после обнаружения бесконечного цикла на
  исчезающе малом остатке float-бюджета. Убрано повторное округление
  остатка, добавлен тест; полный расчёт выполнен заново. У прерванной
  попытки нет принятых численных результатов.
- **Решение:** путь «отдельное кольцо + две пересылки входа» не внедрять:
  общая цена выше, а очередь сама не выполняет сроки. Сохранить ядро и
  измерения для совместного исследования доставки с меньшим копированием
  и удешевления подготовки тяжёлых серий. Это не доказательство
  невозможности других очередей и не новый выпуск.
- **Воспроизведение:** [описание и команды](toolkit/BANK_LOCAL_RESERVOIR_ru.md),
  [ядро](toolkit/bank_local_zx0.py), [замер](toolkit/benchmark_bank_local_zx0.py),
  [CPU-данные](toolkit/bank_local_zx0_cpu.json),
  [модель](toolkit/probe_bank_local_reservoir.py),
  [все результаты](toolkit/bank_local_reservoir.json),
  [проверка стадий](toolkit/check_reservoir_stage_projection.py),
  [93 исполнения](toolkit/bank_local_reservoir_stage_checks.json).

## 2026-09-25 — Прямая запись повторяемых фрагментов из регистров

- **Цель/база:** `7152e10`, прежние 4221 кадр / 25 326 AY и границы
  1624/2921/4221. Убрать лишние пересылки при восстановлении кадра;
  разрешение, пиксели и потоки FAP3/ZX0 сохраняются.
- **Изменение:** необязательный `--register-fragments`. После сохранения
  литерального курсора назначение хранится в HL; пары байтов пишутся
  прямо из BC/DE, без промежуточного A. Убраны ненужная загрузка адреса
  и перенос пары через стек. Произвольные 16-байтовые фрагменты прежние.
- **Абсолютные такты FAP3:** raw **492→492 T**; повтор пары
  **487→419 T (−68)**; две пары **764+10z→655+10z T (−109)**;
  заливка **459→423 T (−36)**, где z — число нулевых битов селектора.
  Учтены вся подпрограмма и RET; внешний CALL/обход, ZX0/IRQ/ULA/диск
  исключены. Для старого совмещённого входа добавляются 54 T к обеим
  версиям и ещё 10 T при выравнивании неполного байта.
- **RAM:** код −53 байта, конец **8FE6h→8FB1h**, перед renderer свободно
  79 байтов. Новых буферов и запретов IRQ нет, дополнительной глубины
  стека нет; кольцо диска 64 КиБ и остальное размещение 128 КиБ прежние.
- **Проверки:** 3108 парных случаев примитива, все 256 селекторов,
  два варианта каналов, смещения 0/3/7 и крайние адреса плиток.
  Смешанные кадры и AY IRQ после каждой инструкции; **34 теста прошли**.
  Полная стадия CPU проверила 4221 кадр, все compact/native-байты и
  точную покадровую разность: **1 063 006 286→1 062 161 744 T (−844 542)**,
  замедленных кадров нет. Отдельный полный плеер на трёх диапазонах
  по восемь кадров дал −4639 / 0 / −2788 T. Тяжёлый диапазон сохраняет
  три поздних публикации у обеих версий даже при идеальном диске.
- **Полный Fuse:** три самостоятельных холодных запуска до EOF,
  **4221 публикация / 25 326 точных AY / 6733 точных сектора**,
  без повторов чтения. Стартовые таблицы точны, два перехода и отказ
  чужим дискам проверены с подменённой ROM. В Fuse — 80 экранных
  байтов на кадр; физический привод не проверен.
- **Размер и время:** прежние **2543/2544/2543 сектора**, запас 512 байтов.
  FPS **8,028514→8,030102 / 7,441164→7,442018 / 7,328012→7,332146**.
  Пропуски полей AY **2392→2384**. Номинальные промахи выросли
  **3553→3554** (1062/1195/1297); оба критерия плавности провалены.
  Playback **554,896994→554,742471 с (−0,154523)**. Восстановленные
  фактические серии 4/1/0; по одной на том остаётся до EOF. Максимальные
  отклонения **7,436854 / 18,692092 / 21,850749 с**. Все пропущенные поля
  AY соответствуют пустой очереди; других потерянных полей нет.
- **Универсальный конвертер:** шесть входов / 68 кадров / 408 AY /
  восемь TRD, полный CPU/Fuse и два перехода. Пять простых входов
  проходят сроки; шумовой — нет (492 пропущенных поля AY, 78 чтений).
- **Уточнение следующего шага:** в изолированной полной стадии с таблицами
  тома 1 остаётся один кадр сверх бюджета 425448 T: индекс 3506,
  425659 T (+211). Раньше таких кадров два, максимум +2382 T. Окна
  2/4/8/16/32/64/128 укладываются в сумму бюджетов этой стадии; ZX0,
  IRQ/ULA/диск здесь исключены. Следующий резерв — предварительная
  распаковка/подача пакетов с проверкой реальной RAM и стоимости очереди;
  её выполнимость текущий расчёт не доказывает.
- **Решение:** сохранить как небольшое ускорение и освобождение места
  под код. **Не релиз**, точные 8⅓ кадра/с не достигнуты; корневые TRD
  этим опытом не заменены. Все фактические OUT и промахи сохранены.
- **Материалы:** [такты/команды](toolkit/REGISTER_FRAGMENTS_ru.md),
  [полная стадия и парные случаи](toolkit/register_fragments_pipeline.json),
  [локальный полный CPU](toolkit/register_fragments_frame_cpu.json),
  [полный Fuse](toolkit/register_fragments_fuse.json),
  [сводка](toolkit/register_fragments_summary.json),
  [бюджеты стадии](toolkit/register_fragments_deadlines.json),
  [трассы](toolkit/register_fragments_evidence/index.json),
  [универсальные входы](toolkit/register_fragments_generic.json).

## 2026-09-25 — Два способа ускорить декодирование Huffman

- **Цель/база:** `0cf64be`, 4221 прежний кадр и 25 326 AY-записей,
  три самостоятельных тома с границами 1624/2921/4221. Сократить CPU
  декодера без изменения разрешения, пикселей и сжатого видеопотока.
- **Отклонённая попытка:** читать только один байт, если код помещается
  в нём. Выигрыш −50 T на таком символе, но +58 T для короткого кода
  на границе / +47 T для длинного. Код 235→256 байтов. Сумма по всем
  символам **143 755 145→149 564 861 T (+5 809 716)**, замедлены 3762
  кадра. Оставлена только в отдельном стенде для воспроизведения.
- **Сохранённая опция:** `--carry-huffman` представляет битовую позицию
  как F8h..FFh; carry заменяет отдельный BIT. Короткий bitmap-код
  **168→160 T**, при переходе байта **173→165 T**; атрибут на 1 T дешевле
  у обеих версий. Длинный невыровненный код +8 T, выровненный прежний.
  Абсолютная формула всех длинных путей приведена в документации.
- **Подсчёт символов:** реальные таблицы трёх томов,
  **143 755 145→138 434 657 T (−5 320 488)**; 22 904 парных Z80-случая
  на каждом наборе таблиц, все используемые символы на восьми смещениях.
  Это расчёт стоимости примитива, без ZX0/IRQ/ULA/диска.
- **RAM:** код примитива прежние 235 байтов, реконструкция заканчивается
  на 8FE6h. Восемь маркеров перемещены BAF0h→BAF8h; страницы сдвигов
  прежние. Дополнительных буферов и глубины стека нет, дисковое кольцо
  64 КиБ и прочее размещение 128 КиБ сохраняются.
- **Проверки:** 32 теста прошли, включая все смещения кодов, lookahead,
  IRQ на каждой инструкции и регрессии плеера/конвертера. Полная стадия
  CPU с таблицами тома 1 проверила все 4221 compact и оба native-экрана:
  **1 068 194 934→1 063 006 286 T (−5 188 648)**, замедленных кадров нет.
  Это стадия без ZX0/IRQ/диска. Парные диапазоны
  полного CPU по восемь кадров дали −14088/−1664/−2694 T; первый диапазон
  всё ещё имеет три поздних кадра даже при идеальном диске.
- **Полный Fuse:** три холодных старта до EOF, 4221 публикация /
  25 326 точных AY / 6733 точных сектора, без повторов чтения.
  Стартовые таблицы точны, два перехода проверены с подменённой ROM.
  Fuse сверяет 80 байтов экрана/кадр; физический привод не проверен.
- **Размер и сроки:** прежние 2543/2544/2543 сектора, запас 512 байтов.
  FPS **8,019790→8,028514 / 7,428374→7,441164 / 7,318932→7,328012**.
  Номинальные промахи **3557→3553** (1063/1194/1296), пропуски полей AY
  **2430→2392** (368/931/1093). Основной и резервный критерии плавности
  не выполнены. Playback **555,638697→554,896994 с (−0,741703)**.
  Фактические серии OUT восстановились 5/1/0 раз; по одной серии
  остаётся до EOF. Максимальные отклонения **7,476837 / 18,712080 /
  21,950713 с**. Все события сохранены в сводке и полных трассах.
- **Универсальный конвертер:** шесть входов, 68 кадров / 408 AY / восемь
  самостоятельных TRD, полные CPU/Fuse-прогоны и два перехода. Пять
  простых входов проходят сроки, шумовой — нет (492 пропущенных поля
  AY, 78 runtime-чтений).
- **Решение:** сохранить опциональный carry-вариант и обе попытки.
  **Не релиз**, цель точных 8⅓ кадра/с ещё не выполнена; корневые TRD
  этим экспериментом не заменены.
- **Материалы:** [расчёты и команды](toolkit/CARRY_HUFFMAN_ru.md),
  [отклонённый вариант](toolkit/single_byte_huffman_cpu.json),
  [символы carry](toolkit/carry_huffman_symbols.json),
  [полная стадия CPU](toolkit/carry_huffman_pipeline.json),
  [парные кадры](toolkit/carry_huffman_frame_cpu.json),
  [полный Fuse](toolkit/carry_huffman_fuse.json),
  [сводка](toolkit/carry_huffman_summary.json),
  [трассы](toolkit/carry_huffman_evidence/index.json),
  [универсальные входы](toolkit/carry_huffman_generic.json).

## 2026-09-25 — Пропуск виртуальных строк кеша у неподвижных краёв

- **Цель/база:** `6e724f4`, прежние 4221 кадр и 25 326 AY-записей,
  границы 1624/2921/4221. Убрать лишнюю очистку кеша движения без
  изменения разрешения, пикселей, формата и сжатого видеопотока.
- **Изменение:** необязательный `--static-cache-borders`. Проверенный
  нулевой маркер крайней полосы разрешает пропустить обнуление её
  виртуальных строк. При активном крае прежний путь сохранён. Опция
  добавлена в сборщик и универсальный конвертер; новых буферов нет.
- **Инструкции:** верхний участок **1644→37 T (−1607)**, нижний
  **1634→49 T (−1585)**, вместе −3192 T при включённом кеше и двух
  неподвижных краях. Активные края добавляют 37/45 T; отключённый кеш
  не меняется. IRQ/ULA/ROM/диск исключены. Код +22 байта, конец 8FE6h;
  дисковое кольцо 64 КиБ, стеки и всё размещение RAM прежние.
- **Полная стадия CPU:** 4221 кадр с таблицами Huffman тома 1,
  побайтно точны все compact и оба native-экрана. Стоимость стадии
  **1 079 267 982→1 068 194 934 T (−11 073 048 / −1,026%)**;
  ускорены 3469 кадров, остальные 752 прежние. ZX0/IRQ/ULA/диск здесь
  не исполняются. Парные тесты проверили ветви с активными краями,
  испорченный кеш, IRQ на каждой границе инструкций и прежний код
  с выключенной опцией; всего с регрессиями прошли 22 отдельных теста.
- **Полный Fuse:** три самостоятельных холодных запуска до EOF,
  **4221 публикация / 25 326 точных AY / 6733 точных сектора**, без
  повторов чтения. Все стартовые таблицы точны; два перехода и отказ
  чужим дискам проверены с подменённой ROM. Fuse сравнивает 80 байтов
  экрана/кадр, физический привод не проверен.
- **Размер и время:** прежние **2543/2544/2543 сектора**, запас 512 байтов.
  FPS **8,000033→8,019790 / 7,402080→7,428374 / 7,299200→7,318932**;
  длительность **557,221170→555,638697 с (−1,582472)**. Пропущенные поля
  AY **2510→2430**. Максимальные фактические отклонения уменьшились до
  **7,696744 / 19,011956 / 22,170615 с**, но номинальные промахи выросли
  **3555→3557** (1065/1195/1297). Оба критерия плавности не выполнены.
  Фактические серии OUT восстановились 4/1/0 раз; по одной серии
  на каждом томе остаётся невосстановленной до EOF.
- **Локальный полный CPU:** три парных диапазона по восемь кадров,
  48 исполнений / 288 точных AY, полные compact/native-экраны.
  Экономия −6384/−19152/−6384 T; тяжёлый диапазон сохраняет три поздних
  публикации у обеих версий даже при идеальном диске. Это не полный фильм.
- **Универсальные входы:** шесть видео / 68 кадров / 408 AY / восемь
  TRD, полный CPU/Fuse и два перехода. Пять простых входов проходят
  сроки; шумовой — нет (499 пропущенных полей AY, 78 чтений).
- **Уточнения проверки:** парный тест выявил +5 T в первоначальной
  ручной сумме cache_zero; исправлена цена невыполненного JR. Первый
  искусственный seed нарушал область вывода renderer, исправлен сам
  вход стенда со штатными чёрными полями; проверки пикселей сохранены.
- **Решение:** сохранить опцию и измерения. Это небольшой выигрыш CPU,
  **не релиз** и не выполнение цели точных 8⅓ кадра/с; корневые TRD прежние.
  Следующий резерв нужно искать в стоимости подготовки тяжёлых сцен.
- **Материалы:** [расчёты/команды](toolkit/STATIC_CACHE_BORDERS_ru.md),
  [полная стадия CPU](toolkit/static_cache_borders_cpu.json),
  [парные кадры CPU](toolkit/static_cache_borders_frame_cpu.json),
  [полный Fuse](toolkit/static_cache_borders_fuse.json),
  [сводка](toolkit/static_cache_borders_summary.json),
  [трассы](toolkit/static_cache_borders_evidence/index.json),
  [универсальный конвертер](toolkit/static_cache_borders_generic.json).

## 2026-09-25 — Совместные ускорения ZX0 и диска в трёх самостоятельных томах

- **Цель/база:** `3356730`, прежние 4221 кадр и 25 326 AY-записей.
  Совместить ранее измеренные inline-копии ZX0 и отложенное чтение с
  актуальными сканером/IRQ-safe paging; качество и разрешение прежние.
- **Параметры:** `inline_matches=True`; отложенное чтение с лимитом 248,
  обслуживанием после кадра и интервалом поддержания активности 64 поля.
  Новых инструкций плеера нет, расширены инструменты проверки сочетаний.
- **Первая попытка размера:** старые границы 1625/2921/4221 дают
  2545/2543/2543 сектора с отложенным чтением — первый том не помещается.
  Перенос одного кадра на второй том: **1624/2921/4221**, теперь
  **2543/2544/2543 сектора**, запас **512 байт**. Контроль на тех же
  границах занимает 2543/2543/2542. Каждый том самостоятельно загружается.
- **Полные проверки:** пять новых комплектов, **15 холодных запусков /
  21 105 публикаций / 126 630 точных AY / 33 665 точных runtime-секторов**,
  без повторов чтения. Все стартовые таблицы точны; десять переходов
  проверены с подменённой ROM. Fuse сверяет 80 байтов экрана/кадр;
  физический привод не проверен.
- **Парное сравнение на новых границах:** контроль → оба ускорения:
  fps **7,935907→8,000033 / 7,387740→7,402080 / 7,188569→7,299200**.
  Промахи номинальных сроков **3962→3555**, AY-пропуски **2746→2510**;
  воспроизведение **562,135527→557,221170 с**, −4,914358 с. Вторая часть
  по средней fps быстрее с одним inline (7,432632), но сроков нарушено
  меньше при комбинации. Отдельная пара на старых границах сохранена.
- **Сроки ещё не пройдены:** у комбинации номинальные промахи
  **1064/1195/1296**, реальные восстановления OUT **4/1/0**, по одной
  невосстановленной серии на том; максимум **8,196531/19,631692/22,630428 с**.
  Пустая очередь AY **405/976/1127**, поля без её посещения **0/1/1**.
  Резервный допуск одного поля также не выполнен.
- **CPU/RAM:** ZX0 сохраняет проверенные −27 T на совпадение и +39 T
  на синхронизацию цели. С IRQ-safe paging обычное чтение **911 T**,
  принудительное отложенное **1043 (+132)**; чтение в ожидании **1131 T**,
  проверка обслуживания без чтения **154 T** с CALL. ROM/IRQ/ULA/механика
  исключены из этих сумм. Кольцо 64 КиБ, новых буферов нет; прежние
  31 байт inline-кода, 256 байтов overlay и три байта состояния deferred.
  12 сценариев кольца проверили 2 764 800 байтов; 641 случай обслуживания
  и отдельное чтение после срока. 26 регрессионных тестов прошли.
- **CPU кадров:** три парных диапазона по восемь кадров: полные экраны,
  компактные данные и 288 AY точны в 48 исполнениях; **7 533 687→7 426 885 T**.
  Даже с идеальным диском тяжёлый диапазон имеет три поздних публикации
  в каждой версии. Это частичная CPU-проверка, не полный фильм.
- **Универсальные входы:** шесть видео / 68 кадров / 408 AY / восемь
  TRD, полные CPU/Fuse и два перехода с inline/сканером/IRQ-safe paging.
  FAP3 прежние; пять простых входов проходят сроки, шумовой — нет:
  501 AY-пропуск, 78 чтений. Deferred в общий CLI пока не добавлен.
- **Уточнение измерения:** первое сравнение физической секции ошибочно
  считало её независимой от позиции первого сектора. Исправлено на
  сравнение логического потока после interleave: **1 919 945 байтов**
  одинаковы на одинаковых границах. В дисковом CPU-профиле исправлен
  выбор старого paging-helper при включённом IRQ-safe: учтены +4 T/вызов.
- **Решение:** сохранить сочетание для дальнейшей оптимизации тяжёлых
  сцен. Это **не релиз**, цель точных 8⅓ кадра/с ещё не достигнута,
  корневые TRD прежние. Самого переноса дискового чтения недостаточно.
- **Материалы:** [описание/команды](toolkit/COMBINED_DELIVERY_ru.md),
  [размещение](toolkit/combined_delivery_storage.json),
  [границы томов](toolkit/combined_delivery_partition.json),
  [полная сводка](toolkit/combined_delivery_summary.json),
  [трассы](toolkit/combined_delivery_evidence/index.json),
  [дисковый CPU](toolkit/combined_delivery_disk_cpu.json),
  [кадровый CPU](toolkit/combined_delivery_frame_cpu.json),
  [универсальные видео](toolkit/combined_delivery_generic.json).

## 2026-09-25 — Переключение банков без DI и полный прогон доставки IRQ

- **Цель/база:** `00fb0fd`, прежние 4221 кадр/AY, три независимых тома
  1625/2921/4221. Уменьшить потери IRQ при переключении банков без
  изменения видео, звука, размера кольца и дополнительных секторов.
- **Диагностика:** два полных прогона первого старого диска дали 11/12
  полей без входа в IRQ. Все 12 адресно прослеженных пропусков покрыты
  окном DI..EI/RET. Фаза диагностических прогонов отличается от базовой
  с 14 пропусками; эти временные отметки не смешиваются при сравнении.
- **Изменение:** необязательный `--irq-safe-paging`. Помощник допускает
  IRQ, а обработчик после публикации OUT при необходимости возвращает
  исполнение на объединение банка с актуальным битом экрана. Учтены
  быстрый и ROM-совместимый стек; по умолчанию опция выключена.
- **CPU/память:** переключение **88→92 T (+4)**, повтор **0..52 T**.
  IRQ с публикацией при PC вне страницы 97h: **686→775 T (+89)**,
  ROM-совместимый **754→851 T (+97)**; максимум при повторе
  **686→829 (+143) / 754→905 (+151)**. Пути без публикации прежние;
  задержка OUT внутри IRQ прежняя. Полная таблица вариантов в описании.
  Код +37 байт, новых буферов/стека нет, кольцо 64 КиБ. CPU-суммы
  исключают ULA/ROM/диск; задержки полного тракта измерены отдельно.
- **Полный Fuse:** все три диска независимо до EOF, **4221 публикация /
  25 326 точных AY / 6733 точных runtime-сектора**, без повторов чтения.
  Все стартовые таблицы точны, два перехода проверены с подменённой ROM.
  Размер **2544/2542/2542 сектора**, запас 1024 байта; физические секции
  видео побайтно прежние. Fuse проверяет 80 байтов экрана/кадр;
  полного CPU-сравнения всех 4221 кадров нового варианта нет.
- **Результат:** поля без посещения обработчика AY **14/7/8→1/1/0**,
  суммарно **29→2**. Кадров/с **7,926850→7,933817 / 7,388775→7,387933 /
  7,186184→7,187774**. Пропуски AY **499/992/1268→490/993/1266**;
  опустошения очереди **485/985/1260→489/992/1266**. Причина оставшихся
  двух потерь IRQ пока не установлена.
- **Сроки не пройдены:** промахи **1573/1292/1298→1372/1292/1298**.
  Фактических восстановлений графика OUT **0/0/0→7/0/0**, остаётся по
  одной невосстановленной серии на том. Максимальные отклонения
  **9,895811 / 19,951558 / 25,409251 с**. Резервный допуск также не
  пройден; физический привод не проверен.
- **Проверки:** 18 тестов, включая 2304 сочетания банков/экранов/
  обработчиков/границ инструкций с AY. Шесть универсальных видео:
  68 кадров/408 AY/восемь TRD, полный CPU/Fuse и два перехода; FAP3
  прежние. Пять простых входов проходят сроки, шумовой — нет, 501
  пустая очередь/пропуск AY и 78 чтений.
- **Исправленные попытки:** начальный CPU-стенд ошибочно полагался на
  EI старого помощника; исправлено моделирование включения IRQ драйвером.
  Первая сводка диагностики не учла DI через границу поля и неверно
  спарила соседние вызовы; исправлены границы/пары и длительность
  импульса Spectrum 128 (36 T). Исправлен агрегатный признак изменённого
  кода в generic-отчёте; исходные значения записаны, времена сохранены.
  Повторный профиль CLI теперь переносит опции проигрывателя из метаданных.
- **Решение:** сохранить опциональный эксперимент; корневые TRD не
  заменены, это **не релиз** и не достижение 8⅓ кадра/с. Дальше требуется
  исследовать оставшиеся IRQ-окна и подготовку данных до срока.
- **Материалы:** [описание/команды](toolkit/IRQ_SAFE_PAGING_ru.md),
  [тесты](toolkit/test_irq_safe_paging.py),
  [такты](toolkit/irq_safe_cpu.json), [Fuse](toolkit/irq_safe_fuse.json),
  [сравнение и диагностика](toolkit/irq_safe_comparison.json),
  [фактические сроки](toolkit/irq_safe_timing.json),
  [полные трассы](toolkit/irq_safe_evidence/index.json),
  [универсальные входы](toolkit/irq_safe_generic.json).

## 2026-09-25 — Исполнение объединённого сканера плиток и полный трёхдисковый прогон

- **Цель/база:** `491db7b`, прежние 4221 кадр и AY, три независимых тома
  на границах 1625/2921/4221. Уменьшить CPU без дополнительных секторов,
  копирования, изменений изображения и звука.
- **Реализация:** необязательный `--fast-noop-scan` в сборщике и
  универсальном конвертере. Объединены проверки вектора/маски, младший
  байт адреса используется только для чётных пар масок. Сканер **88→84
  байта**, дополнительных таблиц, буферов и стека нет; кольцо 64 КиБ.
  При выключенной опции старые байты сканера подтверждены SHA-тестом.
- **Уточнения прежнего расчёта:** в реальном zero-copy пути векторы
  находятся в пакете и могут пересекать страницу. Поэтому оставлен
  `INC DE`, экономия от предполагаемого `INC E` исключена. Первый полный
  CPU-прогон остановлен на кадре 11: проверка абсолютных тактов обнаружила
  ещё 6 T, пропущенные в базовой сумме накладных расходов плитки с
  коррекцией. Формула исправлена и отдельно проверена опкодами; ошибки
  пикселей при этом не было. Прежняя запись/отчёт сохранены как история.
- **Формулы CPU:** серия `k` до конца полосы **92k+200→74k+212 T**;
  перед ненулевым вектором **92k+236→74k+278 T**; перед коррекцией
  **92k+282→74k+278 T**. Отдельная нулевая плитка с коррекцией:
  **257→251 T**, с CALL и без тела процедуры. Полные допущения и
  границы измерения — в связанном описании. IRQ/ULA/ROM/диск исключены.
- **Полный CPU:** все **4221 компактных кадра и оба нативных экрана**
  совпали. Сканер **81 343 425→74 830 741 T**, **−6 512 684 T (−8,01%)**;
  весь измеряемый этап **1 085 780 666→1 079 267 982 T**. Базовые суммы
  вычислены по проверенной парным исполнением разнице; новые абсолютные
  такты сверены с гистограммой каждого кадра. В этом прогоне используется
  полный `volume-1.raw` со своими таблицами; ZX0/IRQ/диск исключены.
  **38 кадров** дороже, максимум **+114 T**. Проверены 30 различных
  регрессионных тестов, включая 11 776 пар выравниваний/серий и IRQ.
- **Размер/запуск:** **2544/2542/2542 сектора**, всего 7628/7632,
  запас прежний — **1024 байта**. Все три TRD загружены отдельно до EOF;
  физические секции видео всех трёх дисков побайтно прежние.
  Два перехода проверены с подменённой ROM, включая чужой диск/серию
  и равенство RAM холодному запуску. Все байты стартовых таблиц точны.
- **Полный Fuse:** **4221 публикация / 25 326 точных AY-записей / 6733
  точных runtime-сектора**, повторов чтения нет. Кадров/с до→после:
  **7,916807→7,926850 / 7,373636→7,388775 / 7,177453→7,186184**.
  Пропуски полей AY **512/1010/1279→499/992/1268**, опустошения очереди
  **493/994/1265→485/985/1260**. Fuse сравнивает 80 байтов экрана/кадр,
  физический привод не проверен.
- **Сроки не пройдены:** номинальные промахи **1564/1292/1298→
  1573/1292/1298**. На первом диске стало больше промахов, несмотря на
  небольшое улучшение средней скорости. Максимальные отклонения после:
  **10,075735 / 19,931567 / 25,449237 с**, фактических восстановлений
  **0/0/0**, по одной невосстановленной серии на диск. Резервный допуск
  также не пройден; пять восстановлений IRQ-счётчика первого диска не
  являются восстановлением реального графика OUT.
- **Общие входы:** шесть видео, 68 кадров / 408 AY / восемь TRD;
  полный CPU и Fuse, два перехода. Все шесть FAP3 прежние. Пять простых
  входов проходят сроки; шумовой — нет, 501 AY-пропуск и 78 чтений.
- **Решение:** сохранить как небольшой необязательный вариант, по
  умолчанию выключен; корневые TRD не заменены. Это **не релиз** и не
  достижение точных 8⅓ кадра/с. Дальше нужно сокращать задержки полного
  тракта и готовить пакеты/AY заранее; одной процедурой цель не решена.
- **Материалы:** [описание и команды](toolkit/FAST_NOOP_SCAN_ru.md),
  [парные тесты](toolkit/test_fast_noop_scan.py),
  [все кадры CPU](toolkit/fast_noop_cpu.json),
  [Fuse](toolkit/fast_noop_fuse.json),
  [сравнение комплектов](toolkit/fast_noop_comparison.json),
  [фактические сроки](toolkit/fast_noop_timing.json),
  [полные трассы](toolkit/fast_noop_evidence/index.json),
  [универсальные входы](toolkit/fast_noop_generic.json).

## 2026-09-25 — Предварительная оценка ускорения пропуска плиток и разбор задержек AY

- **Цель/база:** `042f9ce`, трёхдисковый эксперимент с самостоятельным
  запуском. Проанализирован полный FAP3 `volume-1.raw`, SHA-256
  `9404fc8b57b5445c88c3c877021c613be24f91cf777c3221ea08822d67c511b3`,
  4221 кадр, и сохранённые полные трассы Fuse всех трёх дисков. Требования
  по срокам остаются невыполненными; здесь нового прогона проигрывателя нет.
- **Предложение:** объединить проверку вектора и двух байтов маски,
  использовать младшие байты адресов там, где размещение это допускает.
  Векторы находятся в одной странице A400..A4BF, пары масок начинаются
  с чётного адреса A4C0..A63F. Чёрные крайние полосы пропускаются прежним
  способом. Код проигрывателя, поток, изображения, звук и TRD не изменены.
- **Расчёт CPU:** для серии из `k` пустых плиток, от входа `tile` до
  перехода к следующей плитке/полосе: конец полосы **92k+200 → 72k+212 T**
  (Δ12−20k), следующий ненулевой вектор **92k+236 → 72k+278 T**
  (Δ42−20k), следующая плитка с коррекцией **92k+282 → 72k+278 T**
  (Δ−4−20k). Накладные расходы отдельной плитки с нулевым вектором и
  коррекцией **251 → 243 T** (−8), без тела процедуры коррекции, с CALL.
  IRQ, ULA, ROM и физическая задержка диска исключены.
- **Исправление предварительного расчёта:** замена `DEC HL` на `DEC L`
  после итогового OR уничтожала бы флаг Z перед условным переходом.
  Сохраняем `DEC HL`. Первоначальная оценка −8 224 230 T / 17 замедленных
  кадров была ошибочной; пересчитано **−7 570 756 T**, **20 кадров** могут
  стать медленнее. Найдено 175 669 отдельных плиток с коррекцией. Это
  арифметическая оценка по инструкциям, пока без исполнения нового Z80-кода.
- **AY по существующим трассам:** 493/994/1265 посещений ISR с пустой
  очередью объясняют большую часть 512/1010/1279 полей без новой AY-записи.
  Ещё 19/16/14 физических полей не содержат ни записи, ни отмеченного
  посещения пустой очереди. Начала этих полей не попадают в сохранённые
  интервалы чтения секторов. Точных меток входа IRQ и поиска дорожек здесь
  нет; причина оставшихся пропусков не установлена.
- **Проверка/решение:** скрипт повторно обработал все 4221 пакета до EOF
  и три полные трассы; сохранены гистограмма серий, покадровые оценки,
  абсолютные формулы и ограничения. Эксперимент сохранён на стадии
  расчёта, **не принят в проигрыватель и не является релизом**. Следующий
  шаг — парное исполнение Z80, проверки флагов/границ/IRQ, затем полный
  тракт с диском; расчёт сам по себе не доказывает соблюдения сроков.
- **Материалы:** [скрипт](toolkit/probe_fast_noop_scan.py),
  [отчёт](toolkit/fast_noop_probe.json),
  [исходные трассы](toolkit/volume_huffman_evidence/index.json).
  Из корня репозитория с подготовленным входом предыдущего эксперимента:
  `python toolkit/probe_fast_noop_scan.py --raw .worktree/volume-huffman/.tmp/probe/volume-1.raw --evidence toolkit/volume_huffman_evidence --output toolkit/fast_noop_probe.json`.

## 2026-09-24 — Три самостоятельных TRD с индивидуальными таблицами Хаффмана

- **Цель/база:** `53d7a1e`, тот же FAP3 `1aff3a304635025c…`, 4221 кадр
  после разрешённого удаления титров, 25 326 AY. Сохранить независимый
  запуск каждого диска и уменьшить размер без новых изменений пикселей.
  Сначала границы 1614/2920/4221; затем ограниченный поиск соседних границ.
- **Параметры:** исходные 16 контекстов bitmap + атрибуты, прежняя карта
  предикторов. Частоты считаются только по реально кодируемым символам;
  сравниваются общая и индивидуальные настройки. Все символы фильма
  сохранены с минимальной частотой; длина ограничена исходными 17 битами.
  Векторы, маски, литералы, карты экрана и AY побайтно сохранены. Повтор
  старых таблиц воспроизводит весь исходный FAP3, пять полных потоков
  прошли независимый скалярный декодер всех кадров и AY.
- **Размер на прежних границах:** исходные **7687 секторов**, новые общие
  **7651**, индивидуальные **7638**, при ёмкости 7632. Видео ZX0:
  1 929 800 → 1 922 282 / 1 920 009 байт. Банк таблиц после разностей/ZX0:
  4120 → 3448 / 3247,3207,3210 байт. Общая настройка и исходное разбиение
  сами по себе не дают три помещающихся диска.
- **Разбиение:** 27 реальных раскладок. Границы **1625/2921/4221** дали
  **1625/1296/1300 кадров**, **2544/2542/2542 сектора**. Все три настоящих
  TRD помещаются, запас **4 сектора / 1024 байта**, видео **1 919 959 байт**.
  Секции включают собственные таблицы, код, экраны, предыдущий компактный
  кадр и AY. Передача RAM от предыдущего диска не требуется.
- **Такты:** обычный Huffman минимизирует биты, но оказался дороже на Z80.
  Изолированный декодер на исходных границах: **139 063 076 T →
  143 626 621 T** (общие, +4 563 545) / **143 760 027 T** (индивидуальные,
  +4 696 951, +3,38%). Кодов длиннее 8 бит стало 32 040 → 42 306 / 43 329,
  хотя максимум уменьшился 17 → 16 / 15. Проверены **114 520 реальных
  случаев исполнения**: каждый используемый контекст/символ при восьми
  битовых позициях, пять наборов таблиц. Формулы, абсолютные значения и
  допущения сохранены; они исключают ZX0, вывод, IRQ/ULA, ROM и диск.
- **Идентификатор комплекта:** отпечаток всех трёх исходных потоков,
  состояний кадров, границ и настроек. Изменены только две 16-байтовые
  константы каждого TRD; прочие байты проверены. Исполняемые инструкции
  этой замены прежние, Δ0 T. Два перехода проверены опкодами с подменённой
  ROM: надпись, отказ чужому диску/серии, принятие следующего, RAM как
  после отдельного холодного запуска. Это не проверка физической смены.
- **Полный Fuse:** каждый диск отдельно от холодного запуска до EOF,
  **4221 кадр / 25 326 точных AY-записей / 6733 точных runtime-сектора**,
  без повторов чтения. В Fuse — 80 байтов экрана/кадр; все пиксели целиком
  проверены скалярно, банки таблиц — целиком после Z80-bootstrap с
  подменённой ROM. Физический привод не проверялся.
- **Сроки не пройдены:** **7,916807 / 7,373636 / 7,177453 кадра/с**;
  **1564/1292/1298** промахов номинальных сроков, **512/1010/1279** пропусков
  полей AY; всего 2752 опустошения очереди AY. Максимальное фактическое
  отклонение **10,335625 / 20,291415 / 25,669137 с**. Резервное одно поле
  также не пройдено. IRQ-счётчик показывает пять восстановлений на первом
  диске, но реальные OUT не возвращаются к графику: на каждом диске одна
  невосстановленная серия, фактических восстановлений **0/0/0**.
- **Решение:** сохраняем способ получить три самостоятельно запускаемых
  диска как проверенный по ёмкости эксперимент. Это **не релиз** и не
  доказательство ускорения полного тракта; корневые TRD и настройки
  конвертера не заменены. Дальше нужны таблицы с учётом стоимости длинной
  ветви и решение задержек полного тракта, особенно реальных IRQ/диска.
- **Материалы:** [описание, формулы и команды](toolkit/VOLUME_HUFFMAN_ru.md),
  [перекодирование](toolkit/probe_volume_huffman.py),
  [изолированные такты](toolkit/profile_volume_huffman.py),
  [поиск границ](toolkit/rebalance_volume_huffman.py),
  [сборка и полный прогон](toolkit/measure_volume_huffman.py),
  [фактические сроки](toolkit/summarize_volume_huffman.py),
  [размеры](toolkit/volume_huffman_probe.json),
  [CPU](toolkit/volume_huffman_cpu.json),
  [разбиение](toolkit/volume_huffman_rebalance.json),
  [Fuse](toolkit/volume_huffman_fuse.json),
  [восстановление сроков](toolkit/volume_huffman_timing.json),
  [полные трассы](toolkit/volume_huffman_evidence/index.json).

## 2026-09-24 — Сжатие стартовых таблиц с независимым запуском каждой дискеты

- **Цель/база:** `b77a756`, тот же фильм FAP3 `1aff3a304635025c…`, 4221
  кадр / 25 326 AY. После уточнения пользователя сохраняем самостоятельную
  загрузку каждого тома. Сравнены 20 представлений 16-КиБ таблиц банка 6;
  все имеют точное обратное преобразование. Большинство XOR/перестановок
  хуже. Канонические длины дали 2476 байт, но пока только на хосте,
  без размера/времени ещё не написанного Z80-генератора.
- **Реализация:** `--startup-delta` в сборщике и универсальном конвертере.
  Разности соседних байтов до ZX0, накопление суммы один раз при старте.
  Включается для секции только при экономии целых секторов. Таблицы
  **5483→4120 байт, 22→17 секторов**. Исходный банк восстановлен побайтно.
  Никаких новых изменений кадров/звука; видеопоток четырёх томов
  **1 929 627 байт**, все четыре SHA прежние внутри пар.
- **Такты/RAM:** 17 байт процедуры + 3 CALL внутри bootstrap, новых
  постоянных буферов нет, кольцо 64 КиБ прежнее. Проход **0→541 426 T**
  вместе с CALL, до начала показа. Полный детерминированный bootstrap
  дороже на 538 451..538 938 T; ROM/диск/IRQ/ULA исключены из этих чисел.
  Горячий путь кадра/AY/чтения неизменён, Δ0 T.
- **Размеры:** четыре самостоятельных тома **7759→7724 сектора**,
  −35 / **8960 байт**, с учётом последних дорожек. Три тома на границах
  1614/2920/4221: **7701→7687** при 7632 доступных, ещё **55 секторов /
  14 080 байт сверх ёмкости**. Это не поиск оптимального разбиения.
- **Полный Fuse:** обе пары по четыре тома, **8442 кадра / 50 652 AY**,
  **13 030 точных runtime-секторов**, без повторов. Каждый диск загружен
  отдельно. Экран проверен по 80 байтам/кадр; таблицы целиком — в CPU
  bootstrap. Реальный запуск быстрее на первых двух томах примерно на
  0,85 с, медленнее на следующих примерно на 1,73 с. Фаза/раскладка диска
  меняется, поэтому меньше секторов не означает меньшую задержку.
- **Сроки:** номинальные промахи **4097→4133**, пропуски полей AY
  **2936→2946**; fps до/после сохранены в отчёте. После изменения
  восстановлены 5/7/0/1 поздних серий, по одной остаётся невосстановленной.
  Максимальное отставание 8,616/10,695/21,951/17,992 с. Резервный допуск
  также не пройден, физический привод не проверялся.
- **Другие проверки:** 20 тестов; три перехода опорных дисков с подменённой
  ROM. Шесть универсальных входов, 68 кадров / 408 AY, восемь TRD: полный
  CPU и Fuse, прежние SHA всех FAP3, два перехода. Пять простых входов
  проходят сроки; шумовой — нет (501 AY-пропуск, 78 чтений). Проверка
  обнаружила несовместимость нового warm-ограничения с прежней тестовой
  моделью разбиения без этого поля; совместимость восстановлена.
- **Решение:** сохранить необязательную оптимизацию независимого старта,
  по умолчанию оставить выключенной из-за отсутствия выигрыша по срокам.
  Корневые TRD не заменены. Дальше проверять компактное описание таблиц,
  упаковку стартовых секций и частичных дорожек; три дискеты и точные
  8⅓ кадра/с пока не достигнуты.
- **Материалы:** [описание и команды](toolkit/STARTUP_TABLE_DELTA_ru.md),
  [20 вариантов](toolkit/startup_tables_probe.json),
  [сводка](toolkit/startup_delta_summary.json),
  [полные пары Fuse](toolkit/startup_delta_fuse.json),
  [покадровые отчёты](toolkit/startup_delta_evidence/index.json),
  [универсальные входы](toolkit/startup_delta_generic.json).

## 2026-09-24 — Три последовательных тома с сохранением RAM; основным форматом не принят

- **Цель/база:** `e356874`, FAP3 `1aff3a304635025c…`, 4221 кадр / 25 326 AY.
  Уменьшить загрузочные данные; исходная трёхтомная cold-bitmap сборка
  занимала 7702 сектора при ёмкости 7632, превышение 70 секторов.
- **Изменение:** эксперимент `warm_continuation`, по умолчанию выключен.
  На следующих томах сохраняются таблицы банка 6, неизменяемый фиксированный
  код и compact n−1. Изменяемые состояния/кэши/стеки сбрасываются списком
  из 13 диапазонов: 2312 байт до ZX0, 190 после. Кольцо 64 КиБ прежнее;
  временный список помещается в экран. Холодный запуск продолжения сообщает
  `START WITH DISK 1`; отдельный fingerprint исключает смешивание серий.
- **Размер:** перебор 98 ближайших границ дал 1614/1306/1301 кадров,
  **2543/2543/2526 секторов**, свободно 1/1/18. Все три настоящих TRD
  вмещаются. Пакеты проверены целиком: меняются только начальные native-map,
  изображение и AY прежние. Это результат размера, не допуск к выпуску.
- **Такты:** горячий путь прежний, Δ0 T. Дополнительный scatter-reset при
  запуске: 0→48 400 T, включая LD HL/CALL; исключены полные загрузки кода.
  Абсолютные затраты ROM/диска отдельно измерены в полном Fuse.
- **Проверка:** два перехода с испорченными изменяемыми областями прошли
  настоящий Z80 bootstrap с подменённой ROM. Полный Fuse: **4221 кадр,
  25 326 точных AY-записей, 6771 точный runtime-сектор**, без повторов.
  Реальные банки 5/2/6 после EOF проверены и перенесены через SZX в
  ожидание следующего тома, другие банки заполнены A5. Обе смены серии
  приняты, все тома достигают конца. Контроллер между запусками сбрасывается;
  физический привод/смена диска в одном процессе не проверены. В Fuse
  проверены 80 байт на кадр, не полный экран.
- **Время:** fps **7,9390/7,3785/7,1830**, номинальные промахи
  **1560/1300/1299**, пропуски полей AY **482/1011/1273**. Максимальное
  отставание 9,716/20,331/25,489 с; восстановленных поздних серий 6/0/0,
  по одной невосстановленной на том. Резервный допуск также не пройден.
- **Решение/уточнение пользователя:** каждая дискета должна запускаться
  независимо. Требование записано в AGENTS.md; warm-вариант остаётся только
  экспериментом, корневые TRD прежние. Основная работа возвращается к
  компактным стартовым данным для самостоятельного запуска каждого тома.
- **Регрессии:** 23 теста bootstrap, ZX0, checkpoint и универсального
  конвертера прошли. Первоначальный запуск общей команды ошибся в именах
  двух тестовых модулей; повтор с существующими модулями успешен.
- **Материалы:** [описание, память, такты и команды](toolkit/WARM_CONTINUATION_ru.md),
  [размеры](toolkit/warm_continuation_size.json),
  [полный Fuse](toolkit/warm_continuation_fuse.json),
  [покадровые отчёты](toolkit/warm_continuation_evidence/index.json),
  [переходы](toolkit/warm_continuation_swaps.json).

## 2026-09-24 — ZX0 без CALL/RET совпадений: −4,16% тактов, сроки ещё нарушаются

- **Цель/база:** `80ab9d9`, тот же FAP3 SHA `1aff3a304635025c…`, 4221 кадр
  без титров / 25 326 AY-записей. Ускорить горячий путь без увеличения
  видеопотока и новых изменений пикселей. В тяжёлом восьмикадровом
  CPU-префиксе ZX0 занимал 35,4% переднего плана.
- **Изменение:** необязательный `--inline-matches` вставляет ограниченный
  копировщик совпадений в тело Turbo ZX0. Литералы и сохранение/продолжение
  остаются прежними; два набора операндов цели синхронизируются вместе.
  Опция доступна также в универсальном конвертере, по умолчанию выключена.
- **Такты:** CALL 17 T + RET 10 T устранены на каждом совпадении;
  синхронизация цели **100/108 → 139/147 T**, +39. Измеренные примеры
  копирования **116→89**, **141→114**, **106→79 T**. Весь поток, 379 блоков:
  **278 252 736 → 266 673 453 T**, **−11 579 283 (4,1614%)**, замедлившихся
  блоков нет. 446 343 совпадения и 12 102 синхронизации точно объясняют
  разницу по формуле `39*Nsync − 27*Nmatch`. Это отдельный CPU-замер
  без кадрового потребителя, IRQ, ULA, ROM и диска.
- **RAM/данные:** +31 байт кода, новых буферов/состояния нет. Реальный
  декодер занимает 656 байт до `7E90`, где начинается загрузчик; добавлен
  контроль пересечения. Раскладка 128 КиБ, кольцо 64 КиБ и стеки прежние.
  Видеопоток четырёх томов **1 929 884 байта**, число секторов прежнее.
- **Кадровые CPU-пары:** восемь диапазонов по 32 кадра, полный compact и
  оба экрана, AY; **93 339 260 → 92 527 268 T**, −811 992 (около 0,87%).
  Всего проверено 512 кадров / 3072 AY-записи в двух вариантах. Тяжёлые
  диапазоны сохраняют 27 и 12 поздних публикаций даже при идеальном диске.
- **Полный Fuse:** два набора по четыре диска, **8442 кадра / 50 652 AY**,
  **13 032 точных runtime-сектора**, без повторов. Средняя fps повышается
  на каждом диске: с отложенным чтением 248 **8,0389/7,7629/6,9150/7,3624 →
  8,0912/7,7970/6,9643/7,3996**. Но основной критерий ухудшается:
  нарушенные номинальные сроки **3873 → 4043**; без отложения **4096 → 4087**.
  AY-пропуски **2686→2527** и **2939→2801**. Все записи точны, физические
  50 Гц не соблюдены. У каждого диска остаётся невосстановленная поздняя
  серия; резервный допуск также не пройден. Изображение в Fuse проверяется
  по 80 байтам на кадр, не целиком; физический привод не проверялся.
- **Другие проверки:** 32 итоговых теста интеграции/нового варианта и
  десять прежних banked/token-boundary тестов прошли, в том числе IRQ после
  каждой инструкции и прежние машинные байты без опции. Три перехода томов
  прошли с подменённой ROM. Универсальный конвертер: шесть входов,
  **68 кадров / 408 AY**, восемь полных CPU/Fuse-томов; FAP3 всех входов
  прежний. Первые пять входов проходят сроки, шумовой тест их не проходит
  и выполняет 78 runtime-чтений.
- **Решение:** сохранить измеренную опцию ускорения. Автоматически не
  включать из-за регрессии точных сроков с отложенным чтением. Корневые
  TRD прежние; три дискеты и плавные 8⅓ fps не достигнуты. Следующий выбор
  должен учитывать расписание чтения и тяжёлые кадры, а не только среднюю fps.
- **Материалы:** [изменение, такты, память, ограничения, команды](toolkit/INLINE_ZX0_MATCHES_ru.md),
  [сводка](toolkit/inline_matches_summary.json),
  [все ZX0-блоки](toolkit/inline_matches_banked_cpu.json),
  [кадровый CPU](toolkit/inline_matches_frames_cpu.json),
  [полный Fuse](toolkit/inline_matches_disk_summary.json),
  [покадровые свидетельства](toolkit/inline_matches_evidence/index.json),
  [универсальные входы](toolkit/inline_matches_generic.json).

## 2026-09-24 — Пустые начальные bitmap: −12 КиБ, три дискеты пока не вмещаются

- **Цель/база:** `e3cb024`, прежний FAP3 SHA `1aff3a304635025c…`, весь
  монтаж 4221 кадр / 25 326 AY-записей. Убрать bitmap-части двух экранных
  снимков следующих дискет и строить первые два экрана полным выводом.
  Компактный n−1 и атрибуты n−1/n−2 сохраняются; новых пиксельных ошибок нет.
- **Изменение:** экспериментальный `--cold-bitmaps` в сборщике, выключен
  по умолчанию. Формат и Z80-процедуры прежние. Диски независимо загружаются;
  весь поток проверяется побайтно, кроме явно заменённых карт вывода.
- **Размер:** прежние четыре границы `[1269,2334,3195,4221]`:
  **7807 → 7759 секторов**, −48 = **12 288 байт** с учётом загрузки,
  секторного округления и interleave. Видеопоток −257 байт.
  Попытка трёх томов `[1619,2919,4221]`: **7734 → 7702** при ёмкости
  7632; превышение 14/27/29 секторов, всего **17 920 байт**.
  Это одно разбиение, не доказанный минимум; переполненные TRD не записаны.
- **CPU/RAM:** новых инструкций и RAM нет. На первых восьми кадрах каждого
  следующего четырёхтомного начала: **3 144 513 → 3 215 463 T**,
  **2 804 168 → 2 890 739 T**, **1 104 168 → 1 300 521 T**.
  Эти суммы включают предварительный `prime`, но исключают IRQ, ULA и ROM/диск.
  В трёхтомном начале 2919 обе версии опаздывают на 3/5/8 полей уже
  с идеальным диском: нужна также оптимизация декодирования/вывода.
- **Полный Fuse:** 4221 кадр, 25 326 точных AY-записей, 6515 точных
  runtime-секторов. Диск 1 переиспользует прежний полный замер после
  проверки SHA заново собранного TRD; 2–4 прогнаны заново. По 80 байтов
  изображения на кадр, не полный экран. fps **7,9194 / 7,7156 / 6,9072 /
  7,2933**. Нарушений номинальных сроков **4096 → 4135**, физических
  пропусков AY-полей 2939; на каждом диске остаётся невосстановленная серия.
  Ни точные сроки, ни резервный джиттер не проходят. Чистая механика
  отдельно от ROM/IRQ/ULA не оценивалась, физического дисковода не было.
- **Проверки:** 24 теста, 80 кадров полного компактного/двойного экранного
  CPU-сравнения, 480 AY-записей в этих коротких прогонах, все ZX0-блоки,
  три перехода между дисками с подменённой ROM. Исправлена первоначальная
  команда тестов, содержавшая имя несуществующего модуля.
- **Решение:** сохранить как выключенный эксперимент экономии хранения;
  устойчивого ускорения не получено. Корневые TRD и настройки конвертера
  прежние. Следующие резервы — общие таблицы/код и тяжёлые кадры.
- **Материалы:** [метод, такты, ограничения и команды](toolkit/LEAN_CHECKPOINTS_ru.md),
  [четыре тома](toolkit/lean_checkpoints_four.json),
  [три тома](toolkit/lean_checkpoints_three.json),
  [полный Fuse и индексы свидетельств](toolkit/lean_checkpoints_fuse.json),
  [смена дисков](toolkit/lean_checkpoints_swaps.json).

## 2026-09-24 — Ограниченное упрощение строк: −3540 байт после ZX0

- **Цель/база:** `3e0db88`, прежний FAP3 SHA `1aff3a304635025c…`,
  весь монтаж без титров, 4221 кадр и 25 326 AY-записей. Проверить замену
  сложных блоков повторением одной/двух строк. Ограничения считаются от
  исходного Spectrum-эталона, включая уже внесённые ошибки: ≤2 точки на
  знакоместо, ≤1 четверти заполнения на точку, RMSE ≤24, ≤128 точек на
  кадр, ≤3 неточных кадров подряд. Разрешение и атрибуты не меняются.
- **Изменения:** поиск 36 пар строк на ПК; повторное кодирование прежними
  векторами/таблицами с пересчётом причинных поправок и карты вывода n−2.
  Существующие fast-фрагменты сохраняются; дополнительные простые команды
  разрешены, если их битовая цена не выше масок и Huffman. Два варианта:
  все сложные блоки (35 519 замен) и только текущие raw-литералы (2321).
- **Результат/неудача:** широкий вариант увеличил FAP3 на **24 328 байт**,
  ZX0 **1 929 729 → 1 976 621**, +46 892. У raw-варианта FAP3 уменьшился
  на **22 899**, но ZX0 только **1 929 729 → 1 926 189**, **−3540 (0,1834%)**.
  Секторы общего потока **7539 → 7525**, без bootstrap/границ/interleave.
  Уменьшение литералов частично съедают новые межкадровые поправки и уже
  имевшееся сжатие повторений ZX0. Три готовых TRD не собраны.
- **Качество:** весь активный экран каждого кадра проверен. Средний SSIM
  базы/широкого/raw **0,988507 / 0,987995 / 0,988494**; минимальный
  **0,965053 / 0,962698 / 0,965053**. Изменённых RGB-пикселей raw-варианта
  в среднем 0,27209%, максимум 0,34722%. Дополнительно повторённых кадров
  нет. Просмотрены полосы по пять кадров около событий 62/3838/2159 обоих
  вариантов; отдельные точки, сохранены формы/цвета. Полного просмотра
  в движении не было; SSIM не выдаётся за процент качества.
- **Такты/память:** код Z80 не менялся, Δ инструкций **0 T**, новой RAM 0.
  По прежней проверенной формуле на 61 862 общих fast-плитках:
  **31 931 046 → 32 547 284 T**, +616 238 для raw-варианта. Две строки
  стоят 774..834 T против 492 у прямого raw. Это проекция только тел,
  без остальных стадий/IRQ/ULA/ROM/диска, не замер полного проигрывателя.
- **Проверки:** четыре теста ограничений прошли. Два побайтных контроля
  пересборки базы; оба новых потока независимо восстановили все **8442
  кадра / 50 652 AY-записи**. Каждый ZX0-блок проверен. Новых полных
  CPU/Fuse-прогонов, подтверждения 8⅓ fps или физических 50 Гц здесь нет.
- **Решение:** широкий фильтр отклонить, raw-фильтр сохранить как малый
  офлайн-кандидат, пока не переносить в конвертер/выпуск. Требуется выбирать
  изменения с учётом соседних кадров и полной цены доставки. Цель трёх
  дискет и нулевых опозданий сохраняется, корневой комплект прежний.
- **Материалы:** [методика, расчёты, скрипты и команды](toolkit/BOUNDED_FRAGMENTS_ru.md),
  [широкий ZX0](toolkit/bounded_fragments_zx0.json),
  [raw ZX0](toolkit/bounded_fragments_raw_only_zx0.json),
  [покадровое качество](toolkit/bounded_fragments_raw_only_quality.json),
  [байты и тела Z80](toolkit/bounded_fragments_raw_only_costs.json).

## 2026-09-24 — Отложенное чтение FAP3: ускорение с обслуживанием после кадра

- **Цель/база:** `7aca091`, прежние 4221 кадр монтажа без титров,
  25 326 AY-записей, четыре фиксированных тома. Вход FAP3 SHA начинается
  `1aff3a304635025c`; разрешение, компактные кадры и данные AY прежние.
  Перенести дисковое чтение из критического пути подготовки в ожидание кадра.
- **Изменения:** очередь освобождённых секторов, принудительное чтение при
  лимите 64/248; существующее кольцо 64 КиБ сохраняется. Код занимает
  отработавший bootstrap `6100..61FF`, новых буферов нет, 3 байта счётчиков.
  После 64 полей без обслуживания — чтение очередного сектора либо SEEK
  текущего цилиндра; в итоговом варианте проверка также после каждого кадра.
- **Неудачные этапы:** очередь сама по себе добавила 4/7 повторных чтений
  за полный ролик и снизила FPS; обнаружен промежуток без обслуживания
  около 4,17 с. Проверка только во время свободного ожидания не исправила
  это на тяжёлых сценах. С проверкой после кадра повторных чтений **0**
  для обоих лимитов во всех частях. Первоначальная ошибка ROM mock из-за
  незаданного кэша дорожки исправлена; её не включали в результаты плеера.
- **Измерения:** лучший общий вариант, лимит 248, повысил FPS частей
  **7,9194/7,7212/6,9072/7,2891 → 8,0389/7,7629/6,9150/7,3624**.
  Пропущенных физических AY-полей **2939 → 2686**, кадров вне номинального
  срока **4096 → 3873**. В каждой части остаётся невосстановленная серия
  опозданий; ни точные сроки, ни допуск 20 мс не соблюдены. В третьей части
  лимит 64 чуть быстрее 248. Все потоки томов — прежние **1 929 884 байта**;
  новый загрузочный код добавил один занятый сектор четвёртого тома.
- **Такты:** обычный адаптер чтения 907 T; принудительный новый 1039 T,
  **+132 T**, включая отметку времени. Постановка в очередь 124 T;
  последующее чтение в ожидании 1123 + 31 T. Проверка после кадра без
  обслуживания **137 + 17 = 154 T**. Стартовое копирование **5401 T**.
  Это инструкции без тел ROM/IRQ/ULA/механики; полное время Fuse учитывает
  их совместно. Перенос I/O полезен, хотя служебных CPU-тактов больше.
- **Покрытие:** семь вариантов полностью, **29 547 кадров, 177 282 AY-записи,
  45 612 успешных runtime-секторов**. AY и секторы сверены полностью,
  видео в Fuse — 80 байтов каждого кадра, не весь экран. 12 тестовых
  сочетаний кольца ×230 400 байт, 641 сочетание обслуживания и отдельное
  обслуживание очереди прошли. Все 18 прежних тестов прошли; три перехода
  между дисками проверены с ROM mock. Физического привода в проверках нет.
- **Решение:** оставить опциональным экспериментом, общий конвертер и
  корневые TRD не переключать. Всё ещё четыре дискеты и поздние кадры;
  требуется дальнейшее уменьшение CPU-затрат и размера потока.
- **Материалы:** [подробности, такты и команды](toolkit/FAP3_DEFERRED_DISK_ru.md),
  [сборка/замер](toolkit/run_deferred_disk.py),
  [CPU-стенд](toolkit/benchmark_deferred_disk.py),
  [итоговая сводка](toolkit/fap3_deferred_frame_service_summary.json),
  полные архивы [очереди](toolkit/fap3_deferred_evidence/initial/index.json),
  [ожидания](toolkit/fap3_deferred_evidence/idle-keepalive/index.json) и
  [проверки после кадра](toolkit/fap3_deferred_evidence/frame-service/index.json).

## 2026-09-24 — H.263 и точные двухуровневые маски: выигрыш до ZX0 исчез

- **Цель/база:** оценить простой блочный метод по запросу о H.263;
  `f7b4547`, прежние 4221 кадр монтажа без титров и 25 326 AY-записей.
  Источник FAP3 SHA начинается `1aff3a304635025c`; выбор движения/Huffman/
  фрагментов фиксирован. Ещё два входа общего конвертера — 48 кадров шума
  и 9 цветных кадров. Разрешение, кадры, атрибуты и звук не менялись.
- **Изменения:** экспериментальный F2L1, только на PC: raw-тайл 8×8,
  содержащий ровно два уровня, хранится как палитра + 64-битная маска,
  9 вместо 16 байтов. Полный разбор H.263, принципов Video 1 и Cinepak
  сохранён с первичными источниками. Совместимый H.263/Z80 не реализовывался.
- **Результат:** 8455 замен в 1083 кадрах; файл **3 097 959 → 3 038 774**
  (−59 185). Но пакетный ZX0-поток с заголовками **1 929 729 → 1 932 946**,
  **+3217 байт, +0,167%**, округление общего потока **7539 → 7551** секторов.
  Это глобальное измерение, без bootstrap, границ томов и interleave.
  На обоих дополнительных входах нет замен, потоки ZX0 побайтно прежние.
- **Коррекция опыта:** первый последовательный замер был прерван во время
  сжатия базы: он включал таблицы FAP3 в ZX0. В итоговом варианте таблицы
  исключены, границы соответствуют `Builder.stream`; замер повторён до EOF.
  Четыре независимых процесса ускоряют PC-сжатие; кэш проверяется распаковкой.
- **Проверки/такты:** все **4278 кадров/25 668 AY-записей** трёх входов
  восстановлены в исходный FAP3 побайтно; каждый ZX0-блок проверен отдельно.
  Четыре теста масок/палитр и блочных границ прошли. Горячий путь плеера не изменён: **Δ 0 T**.
  Абсолютные такты нового режима и задержки диска не измерялись, поскольку
  нативного декодера нет. TRD не собирались, выпуск/плавность не заявляются.
- **Решение:** конкретную замену литералов не переносить в плеер — после
  ZX0 данные больше. Простые блочные методы остаются кандидатами; следующий
  вариант должен выбирать маску совместно с движением/Huffman, затем пройти
  CPU/RAM/дисковый и полный временной контроль. Этот опыт не доказывает
  непригодность любого палитрового кодека.
- **Материалы:** [разбор и команды](toolkit/LIGHT_VIDEO_CODECS_ru.md),
  [скрипт](toolkit/probe_two_level_fragments.py),
  [тесты](toolkit/test_two_level_fragments.py),
  [мультфильм](toolkit/two_level_movie.json),
  [шум](toolkit/two_level_noise.json), [цвет](toolkit/two_level_colour.json).

## 2026-09-24 — Универсальное видео → FAP3/ZX0/TRD и полный учёт времени

- **Цель/база:** плеер `00313d3`; убрать зависимость сборки от конкретного
  мультфильма. Реализация и измерения выполнены 21 сентября; оформление
  завершено 24 сентября. Входные видео для проверок сгенерированы скриптом,
  формат/размер/длительность задаются входным файлом, а не эталонным монтажом.
- **Изменения:** [`convert_video.py`](toolkit/convert_video.py), новый общий
  FAP3-энкодер, сохранение пропорций/SAR, EOF, короткие ролики, mono и тишина,
  обучение Huffman на данном видео, автоматические границы TRD по реальным
  ZX0-данным и startup/checkpoint. Сохраняются 256×192/активные 256×144,
  целевые 25/3 кадра/с и AY 50 Гц. Дополнительных потерь от сжатия нет;
  перевод исходника в палитру Spectrum и синтез AY имеют отдельные метрики.
- **Память/счётчики:** прежний 128-КиБ профиль; общие параметры сборщика и
  CPU-стенда. Проверка размера таблиц и native-кода, кадры серии u32,
  максимум 10922 кадра на TRD из-за AY u16. Старые fingerprints сохраняются.
- **Такты:** новый [`profile_fap3.py`](toolkit/profile_fap3.py) считает каждую
  исполненную инструкцию собственных алгоритмов, этапы, paging, IRQ и ожидание
  с идеальной подачей данных; отдельно считает дисковый адаптер. Полный Fuse
  измеряет bootstrap/playback, фактические OUT, все AY-записи, каждый runtime-
  сектор, чтение и seek. Интервалы ROM/механики внутри вызовов совместные;
  их нельзя складывать с независимым CPU-прогоном. Пропуски сроков, допуск
  20 мс, восстановление и AY-поля отражаются раздельно. Неполный прогон не проходит.
- **Обнаруженные неудачи:** первый короткий AVI отвергался старым bootstrap
  из-за наложения кода при неполном 64-КиБ preload. Исправлен переходом
  `JP nn` за 6000..60FF: **10 T** только при короткой загрузке; прежний
  полный bootstrap побайтно совпадает в обоих порядках секторов. Горячий
  путь плеера не изменён, **Δ 0 T**. Затем CPU-стенд остановился на AY-underrun
  после 24 записей шумового ролика. Добавлен режим регистрации нарушения
  с продолжением до EOF; строгий режим прежних тестов сохранён.
- **Проверки:** 18 тестов; шесть файлов MP4/MKV/AVI/MOV, 68 кадров/408 AY,
  восемь TRD. Полное сравнение compact/native в CPU, в Fuse — все кадры,
  80 экранных байтов/кадр и точные AY-записи. Простые пять файлов прошли
  сроки. На 48 кадрах шума: **54 530 431 T foreground**, из них реконструкция
  40 258 562 T; 78 runtime-секторов, чтение **2 277 182 T**, seek **44 252 T**;
  46 поздних кадров, максимум 36 588 529 T, 501 пропущенное поле AY,
  серия до EOF не восстановилась. Это успешная проверка данных, провал времени.
- **Вместимость:** 384 кадра шума автоматически разделились на **353+31**,
  свободно **86/2259 секторов**. Все 384 кадра/2304 AY восстановлены, проверены
  2160 runtime-секторов; foreground **398 529 442/34 998 912 T**, чтение первой
  части **66 364 794 T**, seek **1 507 810 T**. Поздних **351/29**, максимальное
  отставание **337 592 977/21 768 756 T**, пропуски AY **4747/292**: время не прошло.
  Три перехода между дисками проверены на реальных Z80-инструкциях с ROM mock:
  правильная серия принимается, неверная отклоняется, RAM совпадает с cold boot.
- **Решение:** общий конвертер принят, ограничения времени видимы в отчёте;
  плавность любого исходника и выпуск ≤3 TRD для мультфильма не объявляются.
  Просмотрены исходные/готовые цветные тестовые кадры, включая наибольшую ошибку.
  Корневые TRD не заменялись. [Инструкция](toolkit/GENERIC_CONVERTER_ru.md),
  [скрипт воспроизведения](toolkit/check_generic_converter.py),
  [шесть входов](toolkit/generic_converter_checks.json),
  [деление по вместимости](toolkit/generic_converter_capacity.json).

## 2026-09-21 — FAP3: порядок секторов 1,9,2,10,…

- **Цель/база:** `5ddc5a0`, cached seek с состоянием из bootstrap,
  прежние 4221 кадр/25 326 AY-записей и границы четырёх частей.
  Уменьшить ожидание диска без изменения логического сжатого потока.
- **Изменения:** опция `--interleaved`; переставлены полные видеодорожки,
  согласованы bootstrap/runtime и верификатор физических адресов.
  Первый частичный трек линейный; размер учитывает пустоты последнего.
  Курсор XOR 8 без таблицы: код 227 → 235 байтов, конец 60EBh, новая RAM
  и стек — ноль. Курсор 22 → 33/54 T, граница 33 → 62; весь адаптер
  896 → 907/928 T, граница 907 → 936. ROM/IRQ/ULA/диск исключены.
- **Размер:** сжатые байты прежние; +6/4/7/0 физических секторов,
  всего +4352 байта. Количество runtime-чтений прежнее — 6516.
- **Полный Fuse:** окна чтения 34,14–34,42 → 14,11–14,23 с на часть;
  средняя скорость 7,299/6,936/6,027/6,501 → 7,912/7,717/6,903/7,289.
  Максимальное фактическое отставание 22,00/26,06/40,06/35,16 →
  8,58/10,54/21,96/18,12 с. Номинально поздних 1025/928/843/865,
  OUT за полем 1208/1001/843/936, восстановленных серий 5/5/0/1;
  по одной конечной невосстановленной серии в каждой части.
  Полей без очередной AY-записи 425/523/1093/901 — непрерывности ещё нет.
- **Проверки:** 10240 CPU-комбинаций; семь прежних тестов; все сжатые
  потоки побайтно равны базе, все начальные кольца/дорожки проверены CPU.
  Fuse проверил все кадры/AY/runtime-сектора и прогресс, по 80 байтов
  изображения на кадр. Три mocked-перехода и три EOF-ожидания прошли.
  Полные пиксели в Fuse, реальная замена носителя и физический привод
  не проверены; каждый отдельный срок и серия сохранены в отчётах.
- **Решение:** сохранить опцию — небольшой рост места окупается общим
  ускорением. Корневые образы прежние; цель трёх дискет/плавности не достигнута.
  Далее — перенос подкачки из критического пути в доступное время с резервом.
- **Материалы:** [описание/команды](toolkit/FAP3_INTERLEAVED_ru.md),
  [CPU](toolkit/benchmark_fap3_interleaved.py),
  [проверка потока/кольца](toolkit/verify_fap3_layout.py),
  [сводка и полные времена](toolkit/fap3_interleaved/summary.json),
  [архивирование](toolkit/summarize_fap3_interleaved.py).

## 2026-09-21 — FAP3: cached seek и передача дорожки из загрузчика

- **Цель/база:** `9db8954`, быстрый читатель одной дорожки; убрать оставшиеся
  полные C=5. Те же 4221 кадр, 25 326 записей AY и границы четырёх частей.
  Три варианта: прежний читатель, cached seek с первым C=5, cached seek
  с дорожкой последнего bootstrap-чтения; каждый проверен до EOF.
- **Параметры:** прямые ROM-процедуры выбора стороны/SEEK с настроенной
  скоростью шага; повтор короткого чтения сохранён. Адаптер 215 → 227 байтов,
  дополнительная процедура 89 байтов в 9A90h–9AE8h. Кольцо 64 КиБ,
  таблицы/экраны/AY прежние; +0 байтов видео, +0 занятых секторов частей.
- **CPU:** та же дорожка 896 → 896 T; холодный вызов 804 → 841 (+37);
  смена нечётной/чётной дорожки 804 → 1351/1341 (+547/+537).
  Вызовы включены, ROM/диск/IRQ/ULA исключены. Инициализация состояния
  из bootstrap меняет только байт, новых инструкций нет.
- **Полный Fuse:** скорость базы 6,360/5,914/5,084/5,574 →
  7,299/6,936/6,027/6,501 кадра/с. Окна дисковых операций около
  61,2–61,7 → 34,5–34,7 с на часть; полный C=5 во время показа — ноль.
  Все сектора/записи AY точны, 80 байтов каждого кадра совпадают,
  прогресс 100%. Номинально поздних 1222/1059/851/916; фактических
  OUT за полем 1220/1059/851/969, максимум 22,00/26,06/40,06/35,16 с.
  В каждой части конечная серия опозданий не восстановилась.
- **AY:** добавлены реальные времена записей; пропуски полей между
  первой/последней записью 2380/2624/3322/3064 → 1098/1299/1998/1753.
  Счётчик пустой очереди этих пропусков целиком не отражает; AY 50 Гц
  пока не выдержан. Холодный контроль и повторный базовый замер сохранены.
- **Проверки:** 2560 сочетаний дорожек/приводов/банков, короткие чтения,
  четыре прежних теста, три mocked-перехода и три ожидания диска в Fuse.
  Первая проверка неверно ожидала нулевые A/B у процедуры выбора стороны;
  исправлена фикстура, полный запуск прошёл. Полные пиксели в Fuse,
  реальная смена носителя и физический привод не проверялись.
- **Решение:** принять опцию как основу дальнейших опытов, корневые
  TRD прежние. Следующий резерв — interleaved-сектора и расписание
  пополнения кольца. Требования трёх дискет и точного темпа не выполнены.
- **Материалы:** [описание/команды](toolkit/FAP3_CACHED_SEEK_ru.md),
  [CPU-измеритель](toolkit/benchmark_fap3_cached_seek.py),
  [сводка и полные отчёты](toolkit/fap3_cached_seek/summary.json),
  [скрипт сводки](toolkit/summarize_fap3_cached_seek.py).

## 2026-09-21 — Аудит переноса прежних оптимизаций

- **Задача/база:** по просьбе пользователя найти забытые оптимизации;
  `main` на `63cc07d`, все рабочие деревья, локальные ветки и обновлённые
  refs `origin`, затем эксперимент `5063985`.
- **Результат:** отдельные растровые коммиты не потеряны. Только
  `30de3df` (векторные контуры) намеренно не входит в основное направление.
  Неперенесённые механизмы находятся внутри уже сохранённого старого кода:
  cached seek, interleaved-сектора, отложенная подкачка с резервом,
  поддержание мотора, прямой вход ZX0 и полный перенос кода из bank 5.
  Прямое чтение одной дорожки перенесено отдельным экспериментом выше.
- **Проверка:** сопоставлены сборщики и вложенные параметры генераторов;
  перечислены включённые ускорения и причины отключения отрицательных
  опытов. Это аудит конфигурации, не новый замер скорости и не выпуск.
- **Решение:** первым продолжать cached seek, затем раскладку секторов
  и расписание подкачки; прямой вход и перенос кода требуют переразметки RAM.
  [Матрица переноса, ограничения и команды](toolkit/OPTIMIZATION_PORT_AUDIT_ru.md).

## 2026-09-21 — Перенос быстрого чтения одной дорожки в FAP3

- **Цель/база:** `63cc07d`; проверить оставшийся в старом проигрывателе
  прямой вход TR-DOS 5.03. Те же 4221 кадр, 25 326 записей AY и границы
  четырёх частей 1269/2334/3195/4221; пиксели, звук и сжатый поток прежние.
- **Изменение:** необязательный `--fast-disk`; первая/новая дорожка через
  C=5, остальные секторы через 3F17h с IRQ; короткое чтение повторяется C=5.
  Требуется проверенный SHA ROM. Адаптер 155 → 215 байтов, конец 60D7h;
  прежняя RAM, 64-КиБ кольцо, +0 секторов на каждой части.
- **CPU:** та же дорожка 739 → 896 T (+157), холодная/новая 739 → 804
  (+65), короткое чтение с повтором 1023 T. Таблица инструкций проверена;
  ROM/диск/IRQ/ULA исключены, полный расчёт в документации.
- **Fuse:** все четыре части до EOF, все 6516 runtime-секторов и AY точны,
  80 байтов каждого кадра совпадают, прогресс 100%. Средняя скорость
  6,054/5,682/4,955/5,402 → 6,360/5,915/5,085/5,574 кадра/с.
  Номинально поздних 1223/1063/851/931; фактических OUT за 20 мс
  1263/1064/851/1017, максимум 47,46/52,54/66,52/61,40 с.
  Во всех частях есть невосстановленная конечная серия опозданий.
  Недогрузки AY 1300/1551/2254/2002; обычный C=5 пропускал больше IRQ,
  поэтому меньшее прежнее число не доказывает более точный звук.
- **Проверки:** 1280 CPU-комбинаций, повреждённое короткое чтение,
  четыре прежних теста, три смены диска с mocked ROM и три EOF-ожидания
  в Fuse. Полные пиксели в Fuse и физический привод не проверены.
- **Решение:** сохранить опцию и результаты; не включать по умолчанию
  и не менять корневые образы: темп и AY не выдержаны. Оставшиеся C=5
  занимают около 31 с на часть; нужен перенос cached seek и проверка
  раскладки секторов. Это не выпуск на три дискеты.
- **Материалы:** [описание и команды](toolkit/FAP3_FAST_DISK_ru.md),
  [расчёт CPU](toolkit/benchmark_fap3_disk.py),
  [сохранённые измерения](toolkit/fap3_fast_disk/summary.json),
  [скрипт сводки](toolkit/summarize_fap3_fast_disk.py).

## 2026-09-21 — TRD текущего FAP3 и автоматическая смена дисков

**Задача и база.** По просьбе пользователя создать образы текущей оптимизации
(`2e95b6d`), затем показывать `INSERT NEXT DISK` и продолжать после вставки
следующего диска. Векторный вариант отложен. Вход — разрешённый монтаж
`movie_no_credits.json`, все 4221 кадр, прежние разрешение и пиксели,
25 326 неизменённых записей AY. FAP3 SHA-256
`1aff3a304635025c25cc8b20d066b6044f2767b02c99d2490c9f9ae1613ac2ab`.

**Что сделано.** Добавлены [сборщик](toolkit/build_fap3_trd.py),
[TR-DOS адаптер и загрузчик](toolkit/fap3_disk_z80.py),
[измерение Fuse](toolkit/measure_fap3_fuse.py),
[тесты Z80](toolkit/test_fap3_disk.py),
[проверка ожидания диска в Fuse](toolkit/verify_fap3_prompt_fuse.py) и
[упаковщик экспериментального комплекта](toolkit/package_fap3_preview.py).
Сохранены все текущие ускорения, Huffman/FAP3, ZX0-блоки до 8192 байтов,
кольцо сжатых данных 64 КиБ, подготовка кадров заранее и вывод сразу в
переключаемые экраны. Изменяется ZX0-упаковка только блоков на границах частей;
пакеты, пиксели и записи звука не меняются.

Каждая дискета содержит загрузчик, сжатые код/таблицы и состояние перед её
первым кадром; поэтому возможна и отдельная загрузка частей. При окончании
части 1–3 звук выключается, обеим экранным страницам добавляется английская
надпись, затем опрашивается служебный сектор 15. Проверяются номер следующей
части и идентификатор фильма **с границами всех частей**, чтобы не принять
другой комплект того же фильма. После распознавания загружается новый PLAYER
и восстанавливаются его состояние изображения/AY и прогресс. На последней
части запроса нет. Смена диска начинает отдельную шкалу времени новой части;
она не маскирует отклонения, измеренные внутри частей.

**Попытки и исправления этого этапа.**

- Первая сборка на три части (границы 1618/2919/4221), ещё до запроса смены
  диска, потребовала 2551/2580/2585 секторов при доступных 2544 на диск.
  Превышение суммарно **84 сектора / 21 504 байта**. Это фактический размер
  с загрузочными файлами, но непроигрываемые переполненные образы не создавались.
  Принято собрать отдельные четыре экспериментальных TRD для просмотра;
  цель максимум трёх дискет не объявлена выполненной.
- В первой интеграции область 9E00 ошибочно принята за свободную: она содержит
  таблицы дизеринга. Порча проявилась с кадра 11. Первый полный прогон этой
  попытки остановлен обработчиком ошибки на публикации 124, после 724 AY ticks
  и 18 опустошений очереди. Адаптер перенесён в 6000..60FF поверх уже ненужного
  начала загрузчика; при сборке теперь проверяются все неизменяемые таблицы.
  Код следующей загрузки размещён в свободной части 9A60..9AFF, а стек ROM —
  ниже 9C00, отдельно от стека возобновляемого ZX0 и основной программы.
- Реальные задержки диска также выявили переполнение AY при догоняющем видео.
  Для дискового варианта добавлено ожидание освобождения слота через IRQ,
  вместо аварийной остановки. Ни одна запись не выбрасывается. Это обеспечивает
  завершение, **но не исправляет ритм звука или видео**.
- Первая команда диагностики Fuse использовала неподдерживаемые выражения
  для чтения банков; процесс был остановлен. Выборка экранов перенесена на
  возврат из отрисовки, когда bank 7 заведомо подключён. Ложное срабатывание
  точки останова на старом содержимом 6043 при загрузке устранено включением
  измерения только после входа в runtime. Повторные проверки проведены с
  исправленным инструментом. Хеширование целой секции сразу после загрузки
  уточнено: A6A0 служит временным буфером; продолжение сравнивается с отдельной
  холодной загрузкой той же части, включая конечное содержимое этого буфера.

**Измерение CPU (по таблице Zilog UM0080, без ROM, диска, IRQ и ULA).**
Ранее источник заменял прочитанные сектора на стороне теста без затрат Z80.
Теперь код заполняет только полностью освобождённые 256-байтовые области.
Для запроса 4 байтов полный `refill` вырос **810 → 855 T (+45)**; для 256 байтов
с чтением сектора **4961 → 5717 T (+756)**. Новый CALL стоит 17 T, проверка без
освобождения сектора 28 T, выход после EOF 74 T. Чтение: тело адаптера 739 T,
добавочно +4 T для банков 3/4, +11 при переходе дорожки, +44 при переходе
банка кольца. Эти 739 T включают сам CALL TR-DOS (17 T), но не его исполнение.
Обычная постановка AY имеет **Δ0 T**; повтор проверки заполненной очереди
73 T плюс ожидание HALT и ISR. Четыре теста проверяют инструкции, сохранение
основных/альтернативных регистров и IX/IY, границы кольца и очередь.
RAM остаётся в 128 КиБ; все четыре банка кольца сохранены. Нового копирования
полного кадра при воспроизведении нет.

**Итоговые измеренные образы.** Все части проверены целиком, отдельно,
Fuse 1.9.0 / Spectrum 128 / TR-DOS 5.03. Границы 1269/2334/3195/4221.

| Часть | Кадров | Сжатый поток, байт | Свободно секторов | Средний фактический fps | Поздних по счётчику | AY underruns |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 1269 | 480419 | 620 | 6,054 | 1090 | 370 |
| 2 | 1065 | 483039 | 584 | 5,682 | 952 | 453 |
| 3 | 861 | 483625 | 590 | 4,955 | 844 | 994 |
| 4 | 1026 | 482801 | 592 | 5,402 | 864 | 814 |

Все **4221 публикация, 25 326 AY-записей, 6516 runtime-секторов** проверены.
На каждом кадре совпали 80 выбранных байтов изображения; полного сравнения
всех байтов экранов именно в Fuse нет. На каждой части проверены обе строки
прогресса обоих экранов при 100%. В трёх переходах Z80 с подменёнными ROM-
чтениями проверены текст, отказ неверному диску/комплекту, принятие следующей
части и точное совпадение загруженной RAM с её холодным стартом. Дополнительно
реальный Fuse прошёл до запроса и дважды отверг оставленную прежнюю дискету
на каждой из частей 1–3. Физическая замена носителя не проверена.

Итоговая точка измерения поставлена **после выполнения OUT**, чтобы включить
фактическую задержку порта ULA, а не прибавлять условные 12 T к началу команды.
После уточнения повторены все четыре полных прогона; таблица относится к ним.

**Проверка времени провалена.** 3750 кадров поздние по счётчику; по настоящему
`OUT 7FFD` **4209** кадров превышают запас одного поля относительно исходной
шкалы. Максимальное фактическое отклонение по частям 57,32 / 59,92 / 70,94 /
67,22 с; на каждой части остаётся невосстановленная поздняя серия. Все серии,
их восстановления и публикации сохранены в отчётах. ROM теряет часть 50-Гц
прерываний; полевая метрика существенно занижает реальное отставание.
Внутри TR-DOS суммарно около 63 с на часть, среднее чтение около 137 тысяч T,
максимальное около 1,42 миллиона T; эти задержки отделены от CPU адаптера.
AY-регистры совпадают в порядке записей, но непрерывность 50 Гц не достигнута.

**Решение.** Сохранить четыре TRD в корне как **Git LFS, experimental preview**,
с [инструкцией](ZX-video-optimized-preview.md) и
[полными отчётами](toolkit/fap3_preview/summary.json). Проверенный комплект
из 14 дискет не заменён. Это позволяет увидеть текущую реконструкцию и
проверить смену дисков, но не является выпуском по требованиям проекта.
Следующая работа — сокращение затрат настоящего дискового ввода и потерь IRQ,
затем повторная проверка всей временной шкалы и сокращение до трёх дискет.

## Как добавлять попытку

Для каждой существенной попытки записывать:

1. Дату, цель, исходную версию и проверенный фрагмент/полный фильм.
2. Что изменили: алгоритм, параметры и границы частей.
3. Результаты относительно базы: объём, число дискет, время CPU,
   интервалы видео/AY и качество — какие показатели действительно измерены.
4. Объём проверки: полностью, частично или только расчёт.
5. Решение: принято, отклонено, заменено другой попыткой или не завершено;
   причину и следующий вывод.
6. Ссылки на скрипты, отчёты и коммит, когда они доступны.

Число образов само по себе не подтверждает работоспособность. CPU T-states
учитываются отдельно от IRQ, ULA, ROM и диска. Измерения Fuse не считаются
проверкой физического дисковода. Старые записи сохраняются при новых попытках.

## 2026-09-20 — Ранний выход после последней bitmap-поправки

- **Цель/база:** `a8f28c2`, прежний FAP3 без титров, 4221 кадр.
  Продолжить основной растровый путь; векторный формат отложен по
  указанию пользователя. Разрешение, пиксели/атрибуты и AY прежние.
- **Параметры:** `--sparse-patches` использует флаг Z после `SLA B`
  для выхода после последней поправки. Курсор HL: загрузка 20 → 16 T;
  два перехода строк каждой половины 15 → 12 T. Код 4052 → **4084 байта**,
  +32, конец **8FF4h**. Новые таблицы/буферы/стек — 0; кольцо диска 64 КиБ.
- **Расчёт:** 136856 одиночных поправок и 523 полных маски среди 423814
  половин. Тело `patches_nonzero` без Huffman и внешнего чтения масок
  **98952892 → 83764305 T**. Не реализованная модель проверки после
  Huffman давала −10940513 T; флаг сдвига экономит ещё 4248074 T.
  Поток **1932429 байт ZX0**, +0 байт / +0 секторов потока; программы
  и границы трёх томов ещё не собраны. 29 кадров дороже, максимум +394 T.
- **Полная стадия:** новый Z80 проверил **4221 из 4221 кадров**, точные
  compact/оба экрана, metadata/курсоры/входные данные, paging и TR-DOS;
  terminal exit 0. Patch с чтением масок **103162272 → 87973685 T**,
  −15188587 / −14,72%; вся реконструкция **668355367 → 653166780 T**,
  −2,27%. Metadata+реконструкция+вывод **1092619757 → 1077431170 T**.
  ZX0/AY/IRQ/ULA/ROM/диск исключены. База сверена с прежней гистограммой
  полного Z80 и покадровыми измеренными дельтами cache/attribute flags.
  Обе версии исполняются в парных тестах; старый полный прогон не повторялся.
- **Общий таймер:** запрошены все 4221, IRQ 70908 T, идеальные секторы.
  Проверены **623 compact/native/packet/publish и 3738 AY ticks**;
  terminal exit 1, прежняя `scheduled AY underrun, 3738`. Поздних
  **17 → 14**, максимум **5 → 4 поля**, первый индекс 411. Вне одного
  поля 12 → 10; OUT за 20 мс 13 → 10; интервалы вне 5..7 по счётчикам
  5 → 4. Фаза своевременных OUT −13..30 → −13..45 T. Серии 411..420
  и 577..578 восстановились на 421/579; 621..622 не восстановилась.
  Все отдельные сроки сохранены. Номинальный и резервный темп не пройдены.
- **Тесты:** четыре новых прошли (17,579 с): 256 масок обеих половин,
  все позиции блока, битовые курсоры, оба экрана, AY IRQ между новыми
  инструкциями, default и отказ неправильных опций. Прежний тест
  сохранённого машинного кода прошёл (0,281 с), дополнение с SHA
  генератора `a8f28c2` — 0,009 с. Первый запуск случайно включил старый
  импортированный TestCase: два теста прошли, третий прерван; импорт
  исправлен, целевой запуск выполнен полностью. Прерванный набор не зачтён.
- **Решение:** сохранить опцию для следующих растровых опытов: точность,
  уменьшение работы и улучшение таймера подтверждены. Нехватка скорости
  на тяжёлых сценах остаётся; это не выпуск. Корневые TRD прежние.
- **Материалы:** [описание](toolkit/SPARSE_BITMAP_PATCHES_ru.md),
  [Z80](toolkit/causal_tile_z80.py), [тесты](toolkit/test_sparse_patches.py),
  [расчёт](toolkit/probe_sparse_patch_masks.py),
  [измеритель](toolkit/benchmark_sparse_patches.py),
  [полная стадия](toolkit/sparse_patches_cpu.json),
  [таймер](toolkit/sparse_patches_idle_cpu.json),
  [сводка](toolkit/sparse_patches_summary.json).

## 2026-09-20 — Общая доставка плотных масок и раннее чтение AY

- **Цель/база:** `c829610`, весь FAP3 без титров, 4221 кадр. Проверить,
  сохраняет ли общую скорость экономия `compact_16` в 15526 байт,
  и устранить зависимость подачи AY от получения всего видеопакета.
  Разрешение, все значения пикселей/атрибутов и AY прежние.
- **Плотные маски:** фактический общий CPU с прежним ZX0 v2/8192,
  новым Gray-выводом и прежними оптимизациями. На одинаковых 623
  публикациях поздних **17 → 19**, максимум пять полей, первый 411.
  Остановка AY по-прежнему на 3738. Native-вывод этого префикса
  **46933560 → 48177007 T**, +1243447. Экономия **1932429 → 1916903**
  байт / **−61 сектор** не превращена в утверждение о скорости дисковода.
- **Ранний AY:** опция `--early-ay` читает первые 138 байт payload,
  ставит шесть записей в очередь, затем дочитывает хвост на прежнее место.
  Одиннадцать регистров на tick, без изменения звука/формата/числа копий.
  Прямой изменённый участок parser **94 → 177 T, +83 T/кадр**;
  CALL включены, тела reader/enqueue отдельно. Код **206 → 222 байта**,
  +16, конец DCDEh, до progress DCE0h два байта. Стек временно +2 байта,
  нового состояния/буфера нет, раскладка 128 КиБ и дисковое кольцо прежние.
- **Полная парная стадия:** все **4221 пакета** Z80+ZX0, оба пути,
  точные payload/маски/векторы/карты/курсоры/EOF, экраны/TR-DOS нетронуты.
  **25326 AY ticks** проверены вручную, это не доказательство 50 Гц.
  Чтение/ZX0/metadata/enqueue/paging **431284140 → 438327822 T**,
  **+7043682 / +1,63%**. Из них parser +350343, reader +2693968,
  ZX0 +3999371; остальные стадии прежние. Новые точки возобновления
  дороже, хотя сжатые байты те же. Реконструкция/вывод/IRQ/ULA/ROM/диск
  в эту таблицу не включены.
- **Общие таймеры:** запрошены все 4221, IRQ каждые 70908 T, идеальный
  источник. Три новые попытки завершились terminal exit 1 по недогрузке AY.
  Ранний AY отдельно и с масками 16 проверил **624 compact/packet,
  623 native/publish и 3744 AY ticks**, затем остановился уже в выводе.
  Оба дают 19 поздних кадров; максимум **5 / 6 полей**. На общем
  префиксе 623 публикаций база/маски16/раннийAY/оба имеют вне поля
  **12/15/14/16** кадров, OUT за 20 мс **13/15/18/19**, интервалы вне
  5..7 полей **5/4/3/6**. Все отдельные сроки и точные OUT сохранены.
  У новых вариантов серии 411..422 и 576..579 восстановились на 423/580;
  620..622 до остановки не восстановилась. Номинальный и резервный
  критерии нарушены; ULA/ROM/физическая подача и весь фильм не проверены.
- **Тесты:** три новых плюс прежний default-code проходят: максимум/ноль/
  смешанные AY, границы блоков/банков, точные курсоры/данные/+83 T,
  небольшие тома 1/2/3/8 кадров при настоящем 50-Гц IRQ с прогрессом,
  EOF/оба экрана, отказ повреждённых count/длин. Default-код прежний.
- **Решение:** сохранить опции/отчёты как отрицательные эксперименты,
  не включать их в основную конфигурацию как доказанное ускорение.
  Ранний AY даёт только шесть дополнительных ticks и не новую публикацию;
  нужен меньший объём работы тяжёлых сцен. Корневые TRD не изменены,
  цель трёх рабочих дисков и равномерных 120 мс остаётся открытой.
- **Материалы:** [расчёт/команды](toolkit/DENSITY_DELIVERY_ru.md),
  [Z80](toolkit/bulk_frame_z80.py), [тесты](toolkit/test_early_ay.py),
  [полный измеритель](toolkit/benchmark_early_ay_packet.py),
  [парный CPU](toolkit/early_ay_packet_cpu.json),
  [маски 16](toolkit/density_16_idle_cpu.json),
  [ранний AY](toolkit/early_ay_idle_cpu.json),
  [оба](toolkit/density_16_early_ay_cpu.json),
  [сводка](toolkit/density_delivery_summary.json),
  [её скрипт](toolkit/summarize_density_delivery.py).

## 2026-09-20 — Повторная модель очереди ZX0 с последними ускорениями

- **Цель/база:** `c829610`, полный FAP3 без титров, 4221 кадр. Проверить,
  стала ли очередь после ZX0 достаточной после ускорений кэша, атрибутов
  и адресов знакомест. Дисковый поток/пиксели/AY прежние, 1932429 байт.
- **Метод:** к прежней модели добавлены полные покадровые измерения четырёх
  оптимизаций: **−66271597 T** суммарно. Foreground без ZX0 в модели
  **1230336515 → 1164064918 T**. Для каждого кадра сверена точная сумма
  замены стадий; все SHA одинаковые, прежние пять сценариев воспроизведены.
- **Результат модели, не Z80-проигрывание:** при 8/24/32/40/56 КиБ число
  поздних кадров **1166/722/518/401/283**, прежде 1425/882/748/625/382.
  Первые новые индексы **410/642/649/656/2887**. При 32 КиБ худшая задержка
  на 3009 около **16087030 T**, больше допустимого поля 70908 T.
  Записаны 15 сценариев, включая условные +5000/+10000 T на кадр.
- **Ограничения:** бесплатная приостановка ZX0, равномерная работа по байтам,
  мгновенный источник, без нового транспорта/paging, ULA, ROM и диска.
  Старые AY/IRQ затраты включены. Это очередь после ZX0, не B2;
  фактические OUT, восстановление серий и размещение всей RAM не проверены.
  40/56 КиБ не объявлены готовой раскладкой Spectrum 128.
- **Исправление скрипта:** первый запуск выявил неверное имя поля `slots`;
  использовано `decoded_blocks`, затем проверено полное воспроизведение
  старых результатов. Нового кода проигрывателя и новых TRD нет: **0 T**.
- **Решение:** одних последних ускорений и увеличения очереди недостаточно.
  Дисковое кольцо пока не уменьшать; продолжать уменьшать работу тяжёлых
  сцен, прежде чем тратить RAM и внедрять транспорт новой очереди.
- **Материалы:** [допущения и результаты](toolkit/UPDATED_RESERVOIR_ru.md),
  [скрипт](toolkit/probe_updated_reservoir.py),
  [полные данные модели](toolkit/updated_reservoir.json).

## 2026-09-20 — Быстрые адреса знакомест и цена плотных масок

- **Цель/база:** `dcfb953`, прежний FAP3 без титров, 4221 кадр и AY.
  Сократить native-вывод без потерь и дополнительных копий кадра;
  отдельно измерить выбор целой полосы вместо отдельных знакомест.
- **Код:** `--gray-cells` посещает компактные строки 0,1,3,2 и меняет
  адреса SET/RES. Sparse-подпрограмма **289 → 254 T, −35 T/знакоместо**;
  добавочная цена с условным CALL 296 → 261. Плотные/пустые пути прежние.
  По умолчанию код побайтно прежний. Renderer **−10 байт**, общий вариант
  853 → 843, конец 934Bh. Новых буферов нет, раскладка 128 КиБ прежняя.
- **Весь native-вывод:** **353965494 → 337553609 T**, −16411885 /
  **−4,64% стадии**, 468911 отдельных знакомест. Ни один кадр не дороже.
  Реальный новый Z80 на всех 4221 кадре: оба экрана, пиксели, атрибуты,
  compact и TR-DOS workspace точны; записи в чёрные поля отсутствуют.
  База — прежняя формула инструкций, обе версии исполняются в парных
  тестах. Полная реконструкция/ZX0 стадийным прогоном не проверялись.
- **Тесты:** четыре новых прошли (все значения масок/пикселей, столбцы,
  оба банка/n−2, sparse/dense/empty, общий pipeline, IRQ после каждой
  инструкции и отказ недопустимого режима). Прежняя проверка масок и
  побайтной генерации тоже прошла. Поток **1932429 байт, +0 секторов**.
- **Общий проигрыватель:** запрошены 4221, IRQ 50 Гц, идеальный диск;
  проверены **623 compact/native/packet/publish, 3738 AY ticks**. Затем
  `scheduled AY underrun, 3738`, exit 1, как в базе. На этом префиксе
  поздних **19 → 17**, максимум по пять полей, первый индекс 411.
  Вне одного поля **15 → 12**, фактический OUT за 20 мс **16 → 13**.
  Интервалов вне 5..7 по счётчикам **4 → 5**, по точным OUT <5/>7:
  **2/6 → 4/5**. У своевременных по полям OUT −13..30 T в обеих версиях.
  Новые серии 411..421 и 577..579 восстановились на 422/580,
  620..622 до остановки не восстановилась. Каждый пропуск сохранён.
  Foreground 202321384 → 199462876 T, IRQ 3268010 → 3274308 T;
  предварительно выполненная будущая работа может различаться.
- **Две попытки масок:** изменены только активные 72 байта карты n−2;
  PC-проверка всех 4221 пакетов/экранов, остальные поля/AY точны.
  `gray_optimal` минимизирует формульную цену native: **−6383320 T**,
  но ZX0 **1960688 (+28259)** байт, **+110** секторов. `compact_16`
  выбирает плотную полосу от 16 знакомест: **1916903 (−15526)** байт,
  **−61** сектор, но проекция native **+7753634 T**, 2098 кадров дороже,
  максимум +14764 T. Это только проекция вывода, без нового ZX0 CPU/диска.
  Optimal ZX0 v2/8192 реально выполнен, все 758 блоков независимо сверены.
- **Решение:** сохранить ускоренный renderer как опцию. `gray_optimal`
  отклонить для нынешнего бюджета; `compact_16` пока кандидат, общий
  таймер с ним не проверен. Качество lossless, но три TRD и 120 мс
  не подтверждены, резервный джиттер также нарушен. ULA/ROM/физический
  диск не измерены. Релизные образы не менять. Следующий шаг — измерить
  всю доставку `compact_16`, учитывая новые ZX0-токены и чтение секторов.
- **Материалы:** [расчёт/команды](toolkit/GRAY_CELL_OUTPUT_ru.md),
  [Z80](toolkit/cell_screen_z80.py), [тесты](toolkit/test_gray_cells.py),
  [полный измеритель](toolkit/benchmark_gray_cells.py),
  [полная стадия](toolkit/gray_cells_cpu.json),
  [частичный таймер](toolkit/gray_cells_idle_cpu.json),
  [варианты масок](toolkit/probe_native_density.py),
  [покадровые проекции](toolkit/native_density_probe.json),
  [ZX0 gray_optimal](toolkit/native_density_gray_optimal_zx0.json),
  [ZX0 compact_16](toolkit/native_density_compact_16_zx0.json),
  [сводка](toolkit/gray_cells_summary.json),
  [её скрипт](toolkit/summarize_gray_cells.py).

## 2026-09-20 — Пропуск пустых масок при реконструкции атрибутов

- **Цель/база:** `6dbb142`, FAP3 без титров, 4221 кадр и прежний AY.
  Убрать повторный обход пустых атрибутных масок, используя уже распакованные
  флаги метаданных. Требования трёх TRD, разрешения и 25/3 fps прежние.
- **Параметры:** опция `--attribute-flags` пропускает восемь пустых масок
  одним блоком; непустые применяет прежним Huffman-путём. Все 96 масок
  учитываются, raw-атрибуты без изменений. Формат/ZX0/границы блоков/AY
  прежние: **1932429 байт, +0 байт, +0 секторов**. Нового буфера нет.
- **Полное измерение стадии:** **38721106 → 20201726 T**, −18519380 /
  **−47,83%**, включая неизменные 4328552 T атрибутного Huffman.
  Обход/применение: 34392554 → 15873174 T. Разность для coded-кадра
  `−5551 + 530*непустые_флаги + 50*непустые_маски`, для raw ноль.
  Все пустые маски 7278 → 1727 T. На 100 кадрах есть проигрыш, максимум
  +1799 T; среднее улучшение не выдано за гарантию по каждому кадру.
- **RAM:** основной код 4081 → 4052 байта, конец 8FD4; helper 71 байт
  по 9360..93A6, чистый прирост +42. Renderer заканчивается на 9355,
  до AY 9400 остаётся 89 байт после helper. Банки, кольцо диска, два
  экрана, compact, стеки, AY/IRQ, таблицы и TR-DOS workspace прежние.
- **Проверки:** реальные инструкции обеих версий на всех 4221 хвосте
  атрибутов; совпали 768 атрибутов, курсоры битов/литералов/масок и
  неизменённая память. Bitmap-декодирование всего фильма этим стадийным
  стендом не проверено. Три новых теста прошли: 3072 рисунка флагов,
  пустые/полные/raw случаи, четыре кадра общего pipeline с двумя экранами,
  AY IRQ после каждой инструкции с длинными 18-битовыми кодами и проверкой
  регистров/paging/стека. Пять прежних проверок тоже прошли.
- **Попытка общего проигрывания:** запрошены все 4221 кадр, IRQ 50 Гц,
  идеальный диск, прежние lookahead/idle-пакеты/ускоренные копии/списки
  вывода. Проверено **623 compact/native/packet/publish и 3738 AY ticks**
  против 416/2496 базы. Затем `scheduled AY underrun, 3738`, terminal exit 1.
  Первый поздний индекс остаётся 411; общий префикс 416 публикаций имеет
  по пять поздних кадров, максимум по пять полей. Во всём новом фрагменте
  **19 пропущенных номинальных сроков**, 15 кадров вне одного поля,
  16 превышений 20 мс по точным OUT. Счётчики: один интервал 4 поля,
  три по 8; точные OUT: два ниже 5 полей, шесть выше 7. Фаза OUT
  своевременных по счётчику кадров −13..30 T. Серии 411..422 и 576..579
  восстановились на 423/580; серия 620..622 не восстановилась до остановки.
  Каждый пропущенный срок и точные T сохранены в сводке. IRQ отдельно,
  ULA/ROM/реальный диск и полное воспроизведение не подтверждены.
- **Решение:** сохранить ускоренный вариант как опцию, по умолчанию код
  прежний. Цель трёх рабочих TRD с ровными 120 мс не достигнута, новые
  TRD не выпускать по частичному прогону. Следующий резерв — bitmap-
  реконструкция и подготовка тяжёлых сцен; экономить полную доставку.
- **Материалы:** [расчёт и команды](toolkit/ATTRIBUTE_MASK_SKIP_ru.md),
  [контроллер Z80](toolkit/attribute_mask_z80.py),
  [измеритель](toolkit/benchmark_attribute_masks.py),
  [тесты](toolkit/test_attribute_masks.py),
  [полная стадия](toolkit/attribute_masks_cpu.json),
  [частичный проигрыватель](toolkit/attribute_masks_idle_cpu.json),
  [сводка](toolkit/attribute_masks_summary.json),
  [скрипт сводки](toolkit/summarize_attribute_masks.py).

## 2026-09-20 — Списки изменений цвета: прежний поток, меньше записей

- **Цель/база:** `a4a3f82`, FAP3 без титров, все 4221 кадр. Между n−1/n
  меняется в среднем 7,61 байта атрибутов, между n−2/n — 14,29, но renderer
  копирует 576 байт каждый кадр. Разрешение, пиксели и AY сохранены.
- **Попытки формата:** FAC1 хранит прямые изменения относительно n−2,
  FAC2 — n−1 плюс два списка групп для вывода. Для обоих полный Python-
  проход проверяет атрибуты обоих экранов, прежние bitmap-поля и AY.
  Optimal ZX0 8192 с независимой распаковкой: **1969468 / 1949955** байт,
  против 1932429, то есть **+37039 / +17526** и +145/+69 секторов потока.
  Оба превышают предварительный трёхтомный бюджет, в Z80 не внедрены.
- **Вариант с прежним потоком:** Z80 строит два списка восьмибайтовых
  групп по уже распакованным маскам атрибутов n−1. Вывод копирует текущие
  значения групп обоих списков, что точно обновляет скрытый экран n−2.
  Compact-атрибуты и дисковый поток неизменны. Чёрные поля не записываются.
- **Первый полный прогон стадии:** подготовка+вывод+новый CALL
  **41272938 → 14745931 T**, −26527007 / −64,27%. Но 312 кадров дороже,
  максимум +33882 T. Отчёт и машинный код первой попытки сохранены.
- **Исправленный полный прогон:** при ≥34 группах применяется прежняя
  пересылка 576 байт; count=72 — маркер без заполнения индексов.
  Итог **13399394 T**, −27873544 / **−67,53% стадии**. Из них подготовка
  4575574, вывод 8752063, CALL 71757. 315 кадров дороже, но максимум
  +3086 T. Формулы и гистограммы учитывают выбор режима и все новые записи.
- **RAM/код:** два списка по 73 байта, 9C20h/9C80h; helper со состоянием
  139 байт в 9CD0h..9D5Ah, до резерва стека 53 байта. Renderer с atomic
  paging 772→853 байта, конец 9355h; wrapper +3 байта. Кольцо диска,
  экраны, compact-состояние, AY и TR-DOS не перемещались, поток +0 байт.
- **Проверки:** все 4221 пары native-атрибутов точны в Z80-стенде новой
  стадии; bitmap-области остаются нетронутыми. Четыре теста прошли:
  все 256 рисунков десяти байтов флагов, края, raw-маркер/вытеснение,
  общий pipeline на составных кадрах и 920 реальных AY IRQ после каждой
  допустимой инструкции sparse/full-опыта. Сверены регистры, paging, стек,
  звук и точные такты. Renderer по умолчанию побайтно совпадает с базой.
- **Исправления стенда:** первая общая попытка остановлена защитой на
  записи 9D5Fh: новый тип стадии не был подключён к существующей проверке
  разрешённых областей. Добавлен этот маршрут проверки с точными адресами
  состояния/списков. В IRQ-тесте произвольный порог числа вызовов заменён
  точным равенством числу пройденных инструкций, а не ослаблением проверок.
- **Запрошен весь проигрыватель:** прежние lookahead/idle/парные копии,
  реальный IRQ каждые 70908 T, идеальный диск. Проверены **416 compact,
  native и публикаций**, **2496 AY ticks**, затем недогрузка AY. База имела
  415 compact/native, 414 публикаций, 2490 ticks. На общем префиксе 414
  публикаций поздних кадров 4→3, максимум 5→4 поля. Первый пропущенный
  срок 410→411. Все новые опоздания: индексы 411..415 на 2/3/4/5/5 полей,
  фактические OUT +141811/212717/283630/354529/354536 T. Серия до остановки
  не восстановилась. Весь фильм, ULA/ROM/физический диск не проверены.
- **Решение:** сохранить `--attribute-groups` как кандидат с прежним
  потоком. Это выигрыш стадии и небольшое улучшение общего префикса,
  не достижение 25/3 fps на всём фильме. Цель трёх TRD остаётся открытой,
  новых образов нет. Следующий резерв — реконструкция и подготовка тяжёлых
  кадров заранее. По умолчанию остаётся прежний режим.
- **Материалы:** [описание/команды](toolkit/ATTRIBUTE_GROUPS_ru.md),
  [конвертер FAC1/FAC2](toolkit/attribute_update_stream.py),
  [FAC1](toolkit/attribute_updates_stream.json), [FAC2](toolkit/attribute_previous_stream.json),
  [ZX0 FAC1](toolkit/attribute_updates_zx0.json), [ZX0 FAC2](toolkit/attribute_previous_zx0.json),
  [Z80](toolkit/attribute_groups_z80.py), [стенд](toolkit/benchmark_attribute_groups.py),
  [первый прогон](toolkit/attribute_groups_initial_cpu.json),
  [итог стадии](toolkit/attribute_groups_cpu.json),
  [проигрыватель](toolkit/attribute_groups_idle_cpu.json),
  [сводка](toolkit/attribute_groups_summary.json), [её скрипт](toolkit/summarize_attribute_groups.py).

## 2026-09-20 — Половинки кэша движения и пересылка по две строки

- **Цель/база:** `4b62e52`, FAP3 без титров, все 4221 кадр, прежние
  состояния и AY. После опыта с кольцом исследована дорогая реконструкция:
  690341535 T, из них кэш 126783065 T. Требования 120 мс и трёх TRD прежние.
- **Формат:** вместо карты 24 групп 4×32 проверены карты 4×16/4×8,
  6/12 байт вместо 3. Полные обратные FAP3-пакеты точны, по 1039272
  чтения motion-предсказателя проверены независимо. Копирование уменьшается
  с 5689088 до 4112896/2702240 байт. Пиксели/атрибуты/AY не перекодировались.
- **Настоящий ZX0:** optimal v2, блоки 8192, обратная проверка всех блоков.
  Половинки **1939630 (+7201)**, четвертинки **1951555 (+19126)** против
  1932429 байт. Это +28/+75 секторов непрерывного потока, не готовая раскладка
  дискет. Половинки превышают прежний предварительный трёхтомный бюджет
  на 1966 байт; доставка новых секторов/парсер/ZX0 CPU ещё не измерены.
- **Две Z80-альтернативы:** половинки и прежняя карта с парной пересылкой.
  Копировщик на всех картах: база **115612885 T**, половинки **97438146 T**
  (−18174739, −15,72%), пары **112146097 T** (−3466788, −3,00%). Это только
  вызовы копирования; неизменные setup/очистка краёв не включены. Формулы,
  инструкции и гистограммы сохранены. Пары: helper 2318 → 2240 T, −78 T
  на отмеченную группу, +0 байт/секторов потока. По умолчанию код прежний.
- **Отвергнутая первая реализация:** развёртка сразу четырёх строк дала
  108457079 T, но с настоящими Huffman-таблицами конец 906Fh перекрывает
  renderer 9000h. Первые половинки заканчиваются на 900Dh. Начальный
  стенд проверял копирование с короткими искусственными таблицами; полная
  сборка остановлена проверкой пересечения. Этот отчёт сохранён с пометкой
  ошибки размещения. Перешли к двум строкам, сократили код половинок.
  У промежуточной формулы правой половинки исправлено сложение на 10 T.
- **RAM итоговых вариантов:** с таблицами фильма база заканчивается на
  8FA9h; пары на 8FF1h (+72 байта, запас 15); половинки ровно на 9000h
  (+87, запаса нет). Кэш/экраны/стек/дисковое кольцо/AY/TR-DOS прежние.
  Код проверен на всех 4221 картах заново; после каждого префетча проверены
  записи и нетронутая память, курсоры, BC и стек. Четыре итоговых теста
  прошли, включая реальные IRQ после каждой инструкции и совпадение
  реконструкции/двух экранов на составных кадрах; три старых теста тоже прошли.
- **Попытка всего проигрывателя с парами:** запрошены все 4221 кадр,
  идеальный диск, настоящий IRQ 50 Гц, idle-предвыборка и прежний FAP3.
  Проверены **415 compact/native, 414 публикаций, 2490 AY ticks**, затем
  та же недогрузка AY. Индексы 410/411/412/413 поздние на 1/3/3/5 полей,
  фактические OUT отклонены на 70903/212718/212719/354536 T. Три кадра
  вне 20 мс, два интервала по 8 полей; серия не восстановилась до остановки.
  У своевременных по счётчику кадров фаза OUT −9..11 T (база −9..48).
  Foreground фрагмента 133980068 → 133645470 T, IRQ отдельно
  2152456 → 2152550 T. ULA/ROM/физический диск не проверены.
- **Решение:** сохранить пары как опцию дальнейшего сравнения, половинки
  как кандидата после компенсации размера и измерения полной доставки.
  Четвертинки пока не реализовывать на Z80. Плавность всего фильма не
  подтверждена, цель не достигнута; новых TRD нет. Не выдавать этот
  частичный прогон за выпуск. Следующий существенный резерв — Huffman/
  реконструкция и ранняя подготовка тяжёлых кадров, а не новые копии экранов.
- **Материалы:** [описание и команды](toolkit/CACHE_COLUMNS_ru.md),
  [профиль](toolkit/reconstruction_baseline_profile.json),
  [карты/качество](toolkit/probe_cache_columns.py),
  [размеры](toolkit/cache_columns_probe.json),
  [ZX0 16](toolkit/cache_columns_16_zx0.json), [ZX0 8](toolkit/cache_columns_8_zx0.json),
  [Z80-стенд](toolkit/benchmark_cache_columns.py),
  [первый опыт](toolkit/cache_columns_initial_cpu.json),
  [полные карты](toolkit/cache_columns_cpu.json),
  [публикации](toolkit/cache_unrolled_idle_cpu.json),
  [сводка](toolkit/cache_columns_summary.json),
  [её скрипт](toolkit/summarize_cache_columns.py).

## 2026-09-20 — Z80-потребитель подготовленных знакомест: два полных прогона

- **Цель/база:** `2b3b4ce`, полный поток без титров, 4221 кадр и прежний
  ZX0 1932429 байт. Проверить гипотезу B после отрицательного векторного
  опыта `30de3df` в отдельной ветке. Приоритет — общая цена и точные 120 мс,
  а не сам факт переноса реконструкции в очередь.
- **Реализация:** B2 хранит маску n−2, 18 длин полос, 576 атрибутов и
  compact-значения; плотные полосы построчные. К раннему B добавлено
  18 байт/кадр только в RAM. Кольцо 30 КиБ в банках 3/4, резерв 2 КиБ,
  staging 128 байт по 7300; прямой доступ к экрану 5, staging для 7 и
  разрывов банка. Готовый native-экран строится прямо в скрытом банке.
- **Первая попытка / такты:** consumer со штатным LDIR прошёл все кадры.
  База вывода с копией карты и двумя atomic-page вызовами — **387271475 T**;
  B2 — **501796331 T**, +114524856 / +29,57%. Producer сюда не включён.
- **Вторая попытка / такты:** staging через 32 LDI с входом в неполную
  группу. Все кадры проверены заново: **489730549 T**, −12065782 к первой
  попытке, но +102459074 / +26,46% к базе. Банк 5 +7,43%, банк 7 +45,46%.
  Sparse-процедура знакоместа 289 → 253 T; LDIR `21*n−5` заменён на
  `75+16*n+18*ceil(n/32)` с CALL/RET. Полные гистограммы учитывают короткие
  дорогие хвосты, staging, paging и все записи, отдельно от IRQ/ROM/диска.
- **RAM:** код/состояние 771 байт у базы, 768/852 у кандидатов; конец
  ускоренной версии 9354, до AY 172 байта. Карта BF20..BF79, больше прежней
  на 10 байт. Записи в RAM — суммарно 7486916, среднее 1773,73 байта.
  Вариант предлагает уменьшить дисковое кольцо до 32 КиБ; физическая подача
  не проверена. Готового размещения producer/scheduler ещё нет.
- **Качество/проверки:** после каждого из 4221 кадров сверены оба экрана
  по 6912 байт; все точны. Сторож записи проверяет видимый экран, чёрные
  поля, таблицы/состояние, очередь и стек. Семь тестов прошли: все значения
  масок, плотные/пустые полосы, n−2, границы 3/4 и кольца, разрывы данных;
  IRQ после каждой допустимой инструкции с учётом DI/EI сохраняет AY,
  основные/альтернативные регистры и paging. Полного AY 50 Гц и публикаций
  в этом потребителе нет; это полный прогон стадии, не полный проигрыватель.
- **Исправления при проверке:** CPU поймал неправильную поправку за
  atomic_page: +206 → +186 T/кадр. Первый полный запуск отклонил внешние
  биты исходной карты; B2 исправлен на пропуск чёрных полос, как у базы.
  Проверки картинки/границ не ослаблены, оба итоговых прогона полные.
- **Модель:** 30 КиБ, два готовых native-экрана и одно ожидающее compact-
  состояние, идеальный диск, бесплатные паузы/управление/IRQ и нулевая
  добавленная цена producer. Даже лучший consumer даёт **906 поздних
  кадров**, первый 648, максимум 294 поля; 893 за пределом 20 мс и
  564 интервала вне 5..7 полей. Все шесть серий восстанавливаются к исходной
  сетке, максимум 351 поздний кадр подряд. Это оценка, не измерение сроков
  публикаций; модели с добавкой 20/40/60 тысяч T ещё хуже.
- **Решение:** сохранить прежний renderer. Этот B2 не внедрять без
  уменьшения реконструкции/банкового транспорта. Отрицательный результат
  не доказывает невозможность других очередей. Следующий приоритет —
  реконструкция (690341535 T в полном базовом профиле). Основной hot path
  не изменён, delta 0 T; дисковый поток +0 байт/секторов, новых TRD нет.
  Цель трёх дискет с точным темпом остаётся не выполненной.
- **Материалы:** [устройство, такты и ограничения](toolkit/PREPARED_CELL_CONSUMER_ru.md),
  [код Z80](toolkit/prepared_cells_z80.py), [защищённый стенд](toolkit/prepared_cells_harness.py),
  [полный измеритель](toolkit/benchmark_prepared_cells.py),
  [LDIR-прогон](toolkit/prepared_cells_cpu.json),
  [LDI-прогон](toolkit/prepared_cells_unrolled_cpu.json),
  [модель](toolkit/probe_prepared_schedule.py),
  [сроки в модели](toolkit/prepared_cells_unrolled_schedule.json),
  [сводка](toolkit/prepared_cells_summary.json).

## 2026-09-20 — гипотеза кольца предраспаковки с прямым выводом в скрытый экран

- **Цель/база:** предложение пользователя, `fa7cfb7`, 4221 кадр без титров,
  прежние состояния/AY и ZX0 1932429 байт. Держать примерно 30 КиБ частично
  подготовленных данных и минимизировать копии. Готовый native-кадр строить
  сразу в переключаемом скрытом банке; FIFO полных экранов не вводить.
- **Размеры:** пакет после ZX0 в среднем 732,80 байта, максимум 3647;
  в 30 КиБ средняя оценка 41,92 кадра, минимум реального окна 14.
  Новый пробный RAM-формат B: шесть AY ticks, маска 72 байта, 576 атрибутов,
  четыре compact-байта на изменённое знакоместо. Среднее 1755,73, максимум
  3028, запас в 30 КиБ — около 17,50 кадра, минимум 10. На диск B не пишется.
- **Проверка данных:** Python-потребитель B восстановил все 4221 активных
  кадра/атрибуты по дельте n−2 и все 25326 AY ticks без изменений. Это
  проверка представления, не исполняемый Z80 и не проверка темпа.
- **RAM/копии:** предложено дисковое кольцо 32 КиБ (банки 0/1), очередь
  30 КиБ + резерв 2 КиБ (3/4), остальные банки прежние. Предусмотреть
  только необходимую короткую пересылку при конфликте банков кольца,
  Huffman и экрана 7; полную копию готового экрана исключить. Реальная
  устойчивость уменьшенного дискового кольца пока не подтверждена.
- **Оценка времени:** обновлённая приближённая модель только ZX0 с
  подтверждённой экономией LDI даёт для 32 КиБ 748 поздних кадров,
  первое 646; даже 56 КиБ — 382, первое 674. 15 сценариев проверили EOF,
  ёмкость и сумму работы. Новый scheduler/банковый транспорт/ROM/ULA/диск
  не включены; модель не оценивает более глубокую подготовку B.
- **Ошибки/решение:** два начальных запуска неверно требовали ключ ZX0 у
  нулевой стадии кадра/заголовка; исправлен анализ. Сохранить B как следующую
  гипотезу: сначала Z80-потребитель прямо в экран и цена producer, затем
  полный темп/диск. По уточнению пользователя победителя не выбирать
  теоретически: сохранить базу, сравнить полные расходы producer/очереди/
  consumer и опоздания; оставить прежний вариант, если он эффективнее.
  Hot path не менялся, измеренная разница 0 T, прирост
  потока 0 байт; новый выпуск и новые TRD не созданы.
- **Материалы:** [план и ограничения копирования](toolkit/PREDECODE_RING_PLAN_ru.md),
  [расчёт](toolkit/probe_predecode_reservoir.py), [покадровый отчёт](toolkit/predecode_reservoir.json).

## 2026-09-20 — копирование распакованных пакетов группами LDI

- **Цель/база:** `0e8acec`, packet-ahead idle, FAP3 без титров, 4221 кадр;
  ускорить читатель без изменения пикселей/AY и ZX0 1932429 байт.
- **Изменения:** 32 LDI с входом в первую неполную группу через изменяемый
  JR. Код читателя 132 → 210 байт (+78), до DC00 остаются 46 байт.
  Буферы/кольцо прежние, нет нового DI/paging; +0 байт/секторов потока.
- **Такты:** участок LDIR `21*n−5` → `48+16*n+18*ceil(n/32)`;
  256 байт 5371 → 4288 T (−1083). Короткие длины 1/2 дороже на 66/61 T.
  Для всех пакетов копия **64911966 → 51764600 T**, экономия **13147366 T
  (20,25% этой стадии)**. Весь reader 70149814 → 57002448; ZX0 прежние
  278862405 T. Заголовок запуска исключён из сумм, проверен отдельно.
- **Полнота:** все 3097959 байт/379 блоков/8442 пакетных запроса и EOF
  точны в исполняемом Z80-читателе. Старые/новые формулы совпали с CPU
  гистограммами. 12 тестов прошли, включая IRQ после каждой инструкции.
- **Видео:** отдельный прогон показал 414 кадров, подготовил 415;
  AY underrun 2484 → 2490, первое опоздание осталось 410, максимум пять
  полей, серия не восстановлена. Пиксели и сыгранные AY точны, но сроки
  и допуск 20 мс не пройдены. Полная проверка чтения не является полной
  проверкой видео. ROM/ULA/физический диск и три TRD ещё не проверены.
- **Решение:** сохранить опциональное ускорение; перейти к более тяжёлым
  стадиям реконструкции/вывода. Корневые образы остаются прежними.
- **Материалы:** [такты/память/команды](toolkit/UNROLLED_STREAM_COPY_ru.md),
  [полное чтение](toolkit/unrolled_packet_copy_cpu.json),
  [расписание](toolkit/unrolled_copy_idle_cpu.json), [сводка](toolkit/unrolled_copy_summary.json),
  [измеритель](toolkit/benchmark_packet_copy.py), [тесты](toolkit/test_unrolled_stream_copy.py).

## 2026-09-19–20 — ещё один пакет/AY наперёд, два порядка чтения

- **Цель/база:** `a50aa55`, 4221 кадр без титров, прежние пиксели/AY,
  ZX0 1932429 байт. Сохранить native-маску и читать следующий пакет раньше.
- **Изменения:** прежняя копия 80 байт перенесена в конец реконструкции,
  используется тот же BF20. Режим always читает безусловно; idle отдаёт
  приоритет готовому кадру, если прошлый уже опубликован. Кольцо прежнее,
  +0 байт потока; код/состояние +22/+49 байт. Опции выключены по умолчанию.
- **Такты:** маска 1316 → 1343 T (+27); обычная ветвь scheduler без тел
  CALL 129 → 186/287 T. С учётом убранного CALL парсера обвязка +67/+168 T.
  Расчёт, хвосты и динамические гистограммы сохранены отдельно от IRQ/диска.
- **Результат:** база/always/idle — 411/415/414 публикаций; первое опоздание
  408/408/410; AY underrun 2466/2496/2484. Максимум 4/8/5 полей, последние
  серии не восстановились. Оба новых варианта не проходят даже запас 20 мс.
  На общем префиксе 411 кадров idle уменьшает число опозданий с 3 до 1.
- **Покрытие:** все проверенные compact/native, маски, курсоры, память,
  регистры при IRQ и прозвучавшие AY точны. Короткие тома 1/2/3/8 кадров
  проверяют EOF, drain и 100% полоски; 30 тестов прошли. Идеальная подача кольца; ROM/ULA/диск,
  полный фильм, загрузчик и три TRD не проверены. Корневые образы прежние.
- **Прерывание/ошибка:** 19 сентября работа остановлена пользователем
  после always и тестов idle; 20 сентября выполнен реальный idle-прогон.
  В первом тесте исправлена инициализация target_bank стенда до первого
  draw; машинный код этим исправлением не изменён.
- **Решение:** сохранить необязательные варианты и отрицательный результат.
  Перестановка не устраняет перегрузку; далее ускорять копирование данных.
- **Материалы:** [такты/команды](toolkit/PACKET_AHEAD_ru.md),
  [сводка](toolkit/packet_ahead_summary.json),
  [always](toolkit/packet_ahead_cpu.json), [idle](toolkit/packet_ahead_idle_cpu.json),
  [скрипт](toolkit/summarize_packet_ahead.py), [тесты](toolkit/test_packet_ahead.py).

## 2026-09-19 — компактный кадр наперёд и публикация из IM2

- **Цель/база:** `1f58971`, FAP3 без титров, 4221 кадр, прежние пиксели,
  AY и ZX0 1932429 байт. Разделить реконструкцию и native-вывод, готовить
  следующий компактный кадр, пока готовый экран ждёт шестого поля.
- **Реализация:** публикация из IRQ до AY, абсолютные сроки +6, общий
  atomic paging против возврата старого screen bit после прерывания.
  Кольцо 64 КиБ и все буферы прежние. Код/состояние +164 байта, +0 байт
  видеопотока; сектора загрузчика пока не измерены. Полоска текущего тома
  вызывается основным кодом после подтверждённой публикации.
- **Такты:** OUT 12 → CALL/helper 105 T (+93); video IRQ добавляет
  75/102/196/495 T по ветви. Основная обвязка +361 T/кадр без scheduler,
  ZX0 paging и IRQ. На 411 кадрах реконструкция прежняя 63116719 T,
  native-стадия 35171769 → 35175879 (+4110), helper учитывается отдельно.
- **Темп:** общий префикс 407 кадров: **27 → 0 опозданий**, фаза
  −13..+12 T. Новый прогон показал 411 кадров, первые 408 вовремя;
  затем опоздания 2/3/4 поля и AY underrun на tick 2466 при чтении
  пакета 411. Прежний срыв был на tick 2442. Последняя серия не
  восстановлена; допуск 20 мс и полный фильм не пройдены.
- **Проверки:** 411 compact/native состояний, данные/курсоры/таблицы,
  сохранность памяти/регистров при IRQ и прозвучавшие AY ticks точны.
  Публикация исполнена при всех рабочих банках, в том числе внутри ZX0
  и реконструкции. Виртуальный том 128 кадров с полоской завершён:
  **768 AY ticks с drain**, 100% на последнем кадре, ноль опозданий.
  22 теста прошли, включая старые регионы кода побайтно.
- **Промежуточные ошибки:** тяжёлый случайный тест исчерпал AY на tick 18;
  функциональную проверку отделили от измерения реального фильма.
  Сумму helper 98 исправили на 88 T. Первый реальный запуск остановила
  проверка курсора, читавшая банк 7 через отображённый банк 6; исправлен
  стенд, код проигрывателя не менялся. Все итоговые ограничения сохранены.
- **Решение:** оставить необязательный исполняемый pipeline. Участок
  [395,421) в прежнем полном CPU-прогоне требует 453438 T/кадр в среднем
  без IRQ/ULA/диска при бюджете 425448. Следующий шаг — ускорять тяжёлые
  стадии и чтение пакета/AY наперёд. TRD прежние; три настоящих тома,
  загрузчик, физическая подача и ULA ещё не проверены.
- **Материалы:** [раскладка/такты/команды](toolkit/PIPELINED_FRAME_ru.md),
  [сводка](toolkit/pipelined_frame_summary.json),
  [прогон до срыва](toolkit/pipelined_frame_cpu.json),
  [виртуальный том](toolkit/pipelined_progress_cpu.json),
  [измеритель](toolkit/benchmark_pipelined_frame.py),
  [тесты](toolkit/test_pipelined_frame.py).

## 2026-09-19 — порционный ZX0 с остановкой между копиями

- **Цель/база:** `81779ce`, 4221 кадр FAP3/379 блоков. Останавливать
  распаковку после достижения минимума перед следующей копией, сохраняя
  дополнительно готовые байты в прежней 8-КиБ истории. Кольцо 64 КиБ,
  пиксели/AY и поток ZX0 1932429 байт прежние, +0 секторов.
- **Полный замер распаковки:** при фиксированных запросах по 256 байт
  прежний путь 297104550 T; первый target−1 295072503 (−2032047);
  сохранение старшего байта обычной цели — **278252736 (−18851814)**.
  Все блоки побайтно точны, ни один не замедлился в этом стенде. Код
  649→620 байт, −29; буферы и состояние прежние. Первый вариант 609
  байт тоже сохранён и воспроизводится опцией `decrement`.
- **Инструкции/задержка:** обычная короткая проверка копии с RET
  60+LDIR(n) → 41+LDIR(n), −19 T; при совпавшем старшем байте −23 T.
  Синхронизация цели 60→100/108 T. Проверены все 720269 границ
  копирования, максимальная оценка шага +256 — 49010 T; с обвязкой
  и максимальным AY IRQ — 50813 T без ULA/ROM/диска. Полный аудит
  повторён с payload FFF4 после заголовка вместо стендового FFF0.
  Синтетическая копия 8191 байт занимает 172854 T: для другого потока
  эту оценку применять нельзя.
- **Проверки:** 10 тестов прошли, включая байты трёх генераторов,
  границы/EOF/кольцо, реальные AY IRQ после каждой инструкции,
  оба экрана/индикатор/звук и оценку задержки на длинных совпадениях.
  Полный общий прогон **всех 4221 кадров** завершён: экраны/compact,
  25326 AY ticks, курсоры, EOF, память и гистограмма точны. Foreground
  1522346286 T против проекции прежнего 1544239948, **−21893662 T**;
  из них ZX0 −21885374, читатель −8288, остальные стадии прежние.
  Среднее 360660,101 T, максимум 766061 на 3686, выше 425448 остаются
  1227 кадров. IRQ 16591971 T отдельно; ручной режим не проверяет темп.
- **Фактический таймер:** на общем префиксе 406 кадров foreground
  −1193405 T, опоздания **39→26**, первая серия восстановлена на 77
  вместо 87, максимум фазы 338555→283121 T. На полном новом префиксе
  407 кадров 27 опозданий; срыв AY на 407/tick 2442 вместо 406/2436.
  Первый target−1 на общем префиксе на 23333 T дешевле итогового:
  ускорение отдельного распаковщика не переносится прямо на расписание.
- **Решение:** сохранить необязательные воспроизводимые варианты;
  плавность и допуск по-прежнему не обеспечены, TRD не заменены.
  Дальше требуется подготовка кадра наперёд и безопасная публикация
  из IRQ, а также проверка диска/ULA и фактического размещения томов.
- **Материалы:** [описание/команды/такты](toolkit/TOKEN_BOUNDARY_ZX0_ru.md),
  [сводка](toolkit/token_boundary_summary.json),
  [CPU всех блоков](toolkit/token_boundary_fast_banked_cpu.json),
  [полный общий тракт](toolkit/token_boundary_fast_cpu.json),
  [задержка в раскладке FAP3](toolkit/token_boundary_stream_latency.json),
  [таймер](toolkit/token_boundary_fast_clock_cpu.json),
  [аудит сроков](toolkit/token_boundary_timing.json),
  [скрипт задержки](toolkit/audit_token_boundary_latency.py),
  [тесты](toolkit/test_token_boundary_zx0.py).

## 2026-09-19 — обычный ZX0 Turbo: полный CPU-прогон и оценка очереди

- **Цель/база:** измерения FAP3 на `a9f359f`, модель после `f28a6b9`,
  все 4221 кадр/379 блоков. Проверить, насколько быстрее распаковка
  без нынешнего банкового транспорта и помогает ли очередь 24 КиБ.
- **Измерено:** обычное ядро Turbo побайтно восстановило все блоки,
  **172907828 T** против **301439210 T** банкового пути с header phase.
  Разница −128531382 T исключает transport/остановки и не является
  экономией интегрированного проигрывателя. Максимум блока 634454 T
  превышает кадр 425448 T; максимум входа 6168 байт. Размер потока,
  пиксели, AY и код ядра прежние, ZX0 с заголовками 1932429 байт.
- **Модель памяти/темпа:** 16 КиБ дискового кольца + три банка, каждый
  с 8 КиБ входа и 8 КиБ выхода. При идеальной бесплатной прерываемости
  3 слота дают 460 поздних кадров; с 16 T копии на сжатый байт — 555.
  Простая политика непорционных блоков — 1121/1468. Это офлайн-модель
  с реконструкцией на кадр вперёд, не исполненный новый проигрыватель;
  4..7 слотов проверены только как чувствительность к объёму памяти.
- **Проверки:** все 379 блоков точны; 112 сценариев контролируют EOF,
  вместимость и полную сумму работы. Старый FAP2 расчёт после обобщения
  скрипта повторён, JSON побайтно совпал. Контроль с бесплатным полным
  predecode даёт ноль опозданий, но требует 379 слотов.
- **Решение:** не принимать обычный Turbo/16-КиБ кольцо как исправление
  темпа. Результат сохранён для дальнейшего ускорения транспорта и
  тяжёлых кадров. Реальная подача TR-DOS, ULA, IRQ-публикация и новая
  раскладка ещё не реализованы/не проверены; TRD прежние.
- **Материалы:** [описание](toolkit/TURBO_QUEUE_ru.md),
  [полные CPU-измерения](toolkit/lean_frame_turbo_cpu.json),
  [расчёт](toolkit/turbo_queue_schedule.json),
  [скрипт](toolkit/probe_turbo_queue_schedule.py).

## 2026-09-19 — пропуск крайних полос без увеличения потока

- **Цель/база:** `a9f359f`, FAP3, все 4221 кадр. Заменить сканирование
  пустых крайних полос коротким переходом. Проверка всех пакетов
  разрешает этот путь; ненулевой первый вектор сохраняет полную
  обработку, включая fill и литералы склейки на кадре 4086.
- **Результат:** размер ZX0 прежний — 1932429 байт, +0 секторов потока,
  пиксели/AY прежние. Код +46 байт, буферы/состояния прежние. Верхняя
  пустая полоса 1692 → 207 T, нижняя 1692 → 221 T; внутренние проверки
  +440 T/кадр. Итого −2516 T, кроме 4086 (+588). Полная проекция
  реконструкции 700958467 → 690341535 T, −10616932.
- **Проверки:** все обещания входа; семь изолированных реальных кадров,
  включая 4052 и 4085..4087: оба экрана, compact, кэш, курсоры и такты
  совпали. Три новых теста и шесть тестов индикатора/полей прошли.
  Первая команда регрессии указала отсутствующий модуль; исправлено
  имя на `test_noop_runs_z80`, ещё три теста прошли (всего 12).
- **Расписание:** прежний срыв AY на кадре 406/tick 2436. На 406
  публикациях CPU −1020354 T, опоздания 43 → 39, максимум фазы
  359193 → 338555 T; первая серия восстанавливается на 87 вместо 88.
  Точный темп и допуск одного поля всё ещё не соблюдены.
- **Решение:** сохранить необязательную оптимизацию для проверенного
  входа. Это частичный прогон и полная проекция T, не новый выпуск;
  ULA/ROM/диск и итоговое размещение загрузчика не проверены, TRD прежние.
- **Материалы:** [описание/такты](toolkit/STATIC_STRIPES_ru.md),
  [аудит](toolkit/static_stripe_summary.json),
  [таймер](toolkit/static_stripe_clock_cpu.json),
  [скрипт](toolkit/audit_static_stripes.py), [тесты](toolkit/test_static_stripes.py).

## 2026-09-19 — готовые длины пустых серий: ускорение с ростом ZX0

- **Цель/база:** `2f8535e`, все 4221 кадр без титров, прежние пиксели
  и AY. Профиль выявил 95142825 T в сканировании пустых серий. Добавлены
  исполняемые FAP4 (команды подряд) и FAP5 (сохранены позиции векторов),
  теги серий 1..16. Маски, литералы, AY, длины пакетов прежние.
- **Полный размер:** каждый из 379 блоков каждого варианта независимо
  распакован. База FAP3 1932429 байт; FAP4 2028827 (+96398), FAP5
  от 1 — 2039563 (+107134), от 4 — 1979717 (+47288), только 16 —
  1937561 (+5132 / 20 секторов). У последнего лишь 103 байта от
  предварительного бюджета трёх дискет, готовое размещение не проверено.
- **CPU:** сканируемая полоса 16 плиток 1672 → 256 T (−1416) у FAP5
  со сканером коротких серий. Обычные ненулевые векторы +17 T.
  Полная проекция реконструкции 700958467 → 688393023 (−12565444),
  код +49 байт, состояние/буферы прежние. Вариант без сканера коротких
  серий, напротив, +19985751 T и 3495 замедлившихся кадров — отклонён.
- **Исполнение/проверки:** 5 тестов прошли: все длины, края, смешанные
  предикторы, оба экрана/индикатор, курсоры, AY, прерывания и формулы T.
  Счётчик команд FAP5 исправлен: раньше учитывал позиции; raw-хеши не
  изменились. Таймер проверил 406 кадров: foreground −1211972 T,
  опоздания 43 → 39, максимальная фаза 359193 → 344012 T. AY всё ещё
  срывается на кадре 406/tick 2436. Точные сроки и допуск не пройдены.
- **Решение:** не заменять FAP3 в выпуске: рост данных не решает
  расписание. Сохранить воспроизводимый опыт и необязательные пути.
  Текущая база и TRD прежние. Следующий кандидат — пропуск неизменных
  крайних компактных полос с сохранением исключений без тегов в потоке;
  аудит нашёл в каждой лишь 16 fill-векторов на **кадре 4086**, а не на
  первом, как сначала предполагалось; поправок ноль. Чтение литералов
  этой склейки необходимо сохранить. Это пока направление, не внедрённая
  экономия. ULA/ROM/диск не измерены.
- **Материалы:** [полное описание](toolkit/VECTOR_RUNS_ru.md),
  [профиль CPU](toolkit/lean_frame_profile.json),
  [сводка/покадровые проекции](toolkit/vector_runs_summary.json),
  [Z80-таймер](toolkit/vector_inplace16_clock_cpu.json),
  [аудит сроков](toolkit/vector_inplace16_timing.json),
  [кодировщик](toolkit/vector_run_stream.py), [тесты](toolkit/test_vector_runs.py).

## 2026-09-19 — дешёвый индикатор текущей дискеты в нижнем поле

- **Запрос/база:** `7608922`; пользователь запросил минимальную нагрузку
  и уточнил, что 100% относится к видео **текущей дискеты**. Полоска
  256×2 в y=184/185, 64 шага. Счётчик увеличивает заполнение только при
  публикации кадра; последняя ступень на последнем кадре тома. Для нового
  тома таблица строится по его длине, полоска/счётчик сбрасываются.
- **Реализация/такты:** 244 байта в свободном промежутке банка 7 и 6
  байт в мосте, состояние 7 байт, +0 байт покадрового потока. Запись
  4 экранных байтов на шаг; между шагами только счётчик. До изменения
  работы индикатора не было, теперь +77 T на обычный кадр, +327/+341 T
  при шаге, +286 T на последнем. Reset +4298 T один раз. Для 1000
  кадров среднее **93,393 T**, около 0,022% бюджета, всего +93393 T.
- **Промежуточная попытка:** первый проверенный вариант писал также
  атрибуты на каждом шаге: 254 байта, 96145 T/1000 кадров. Атрибуты
  перенесены в reset, получено −10 байт и −2752 T на диск. Принят
  вариант без повторной записи цвета; переключений страниц не добавлено.
- **Проверки:** 7 тестов прошли. Все кадры 10 синтетических длин диска
  (1..16320, включая смену 1000/4221/16320/999) сверены на обоих
  экранах, проверены reset/EOF и такты каждой инструкции. Настоящий AY
  ISR не портит состояние при прерывании каждой инструкции индикатора.
  На первых 128 кадрах фильма с **тестовой** границей тома N=128 общий
  CPU 44267453 → 44293702 T, +26249; compact/native и 763 AY ticks
  совпали. Просмотрен PNG из экранной RAM, полоска только в нижнем поле.
- **Расписание/решение:** прежние 26 опозданий остались, первое 62,
  восстановление на 88; максимальная фаза 257797 → 259859 T. Сохранить
  индикатор в исполняемом кандидате. Это частичный прогон, а тестовые
  длины не являются новым разбиением фильма на TRD. Корневые образы
  прежние; точный темп, размер загрузчика в секторах, ULA/ROM/диск и
  смена реальных томов ещё требуют проверки при сборке выпуска.
- **Материалы:** [описание и расчёт](toolkit/DISK_PROGRESS_ru.md),
  [Z80](toolkit/disk_progress_z80.py), [тесты](toolkit/test_disk_progress.py),
  [полный счётчик](toolkit/disk_progress_cpu.json),
  [скрипт измерения](toolkit/benchmark_disk_progress.py),
  [общий тракт](toolkit/disk_progress_clock_cpu.json),
  [расписание](toolkit/disk_progress_timing.json).

## 2026-09-19 — чёрные поля исключены из покадрового вывода

- **Запрос/база:** `3d91f10`, пользователь подтвердил, что чёрные поля
  сверху и снизу обновлять не надо. Опция выводит только 18 рядов
  знакомест; оба поля очищаются один раз вместе с экранами. Масштаб
  и активная область 256×144 сохранены, FAP3/ZX0/AY прежние.
- **Полный аудит качества:** 0 изменённых активных пикселей и атрибутов;
  удалено 488 точек в полях на 269 кадрах, максимум 10. Визуально
  просмотрены 25/1638/1417/1637, изменения только в чёрном поле.
  Первая генерация PNG упала на NumPy/PIL типе; исправлена и повторена.
- **Такты:** при пустых краях **23464 → 22244 T, −1220/кадр**;
  на данном входе диапазон −1220..−3860, сумма **−5371308 T**.
  Вместе с постоянными атрибутами полная проекция вывода
  **405533717 → 386486369 T**. Горячий код 769 байт, +0 байт потока.
- **Проверки/решение:** четыре теста прошли. Реальный IRQ-таймер проверил
  406 кадров: 43 опоздания, первое 62, AY underrun на 406/tick 2436;
  максимум фазы 359193 T. Опцию сохранить, точное расписание ещё не
  обеспечено. Проекция не заменяет полный прогон, диск/ULA не измерены;
  корневые TRD не обновлялись.
- **Материалы:** [описание](toolkit/BLACK_BORDERS_ru.md),
  [качество/такты по кадрам](toolkit/black_border_quality.json),
  [таймер](toolkit/black_border_clock_cpu.json), [аудит](toolkit/black_border_timing.json),
  [воспроизведение качества](toolkit/audit_black_border_output.py).

## 2026-09-19 — FAP3: завершён полный Z80-прогон 4221 кадра

- **Дополнение к попытке `469402c`:** полный общий CPU-тракт FAP3
  zero-copy/no-op (без последующей опции постоянных атрибутов) завершён.
  Все экраны/compact/25326 AY-записей, курсоры и защищённые области
  совпали; гистограмма инструкций сошлась. Проверены также 44 пустых
  coded-канала и 2635 пустых каналов литералов.
- **Измерено:** foreground **1577064563 → 1573904228 T**, **−3160335
  (0,2004%)**. Из этого packet −168840, чтение −178247, ZX0 −2813248;
  остальные стадии прежние. Среднее 372874,728; максимум 853547,
  кадр 4052. Кадров выше 425448 T стало 1370 вместо 1365: меньшая
  сумма не означает соблюдение каждого срока. Ручной ISR — 16591971 T.
- **Отдельная проекция `1962628`:** постоянные атрибуты дают ещё
  −13676040 T, всего 1560228188 T, среднее 369634,728. Это формула
  по проверенной −3240/кадр, не полный прогон ускоренного варианта.
- **Решение/пределы:** сохранить FAP3 как меньший/немного более быстрый
  поток. Полное совпадение данных не отменяет прежние срывы таймера
  на кадре 405. Трёхдискетный выпуск и точный темп пока не достигнуты;
  ULA/ROM/физическая доставка остаются отдельными проверками.
- **Материалы:** [полный CPU](toolkit/lean_frame_cpu.json),
  [сводка FAP3](toolkit/lean_frame_summary.json),
  [сводка атрибутов](toolkit/constant_attribute_summary.json),
  [сравнение FAP3](toolkit/summarize_lean_frames.py),
  [расчёт атрибутов](toolkit/summarize_constant_attributes.py).

## 2026-09-19 — проверка выравнивания внешних границ по знакоместам

- **Предложение/база:** `1962628`, пользователь предложил масштабировать
  ролик для совпадения вертикальных краёв с сеткой знакомест и уменьшения
  частичных обновлений. Проверены конвертер, renderer и все 4221 состояния.
- **Результат:** активная область **256×144**, x=[0,256), y=[24,168):
  все границы уже кратны 8. Native renderer обновляет целые 8×8 ячейки;
  `partial` означает разреженный набор ячеек, не обрезанные знакоместа.
  Блок восстановления 16×16 — отдельная сетка; его верх/низ не выровнены.
- **Дополнительный результат:** в полях вне номинальной области всего
  **488 ненулевых логических пикселей / 440 compact-байтов**, в 269 кадрах
  (первый 25). Поэтому точный native вывод сейчас захватывает 20 полос.
- **Решение:** масштабирование ради сетки 8×8 не требуется. Следующий
  кандидат — строго чёрные поля и вывод 18 полос без изменения активной
  картинки, с отдельными проверками качества/тактов/расписания. В этой
  попытке только аудит: **0 T и 0 байт изменений**, экономия кандидата
  не измерялась, исходное видео и TRD не менялись.
- **Материалы:** [разбор](toolkit/VIDEO_CELL_ALIGNMENT_ru.md),
  [полный отчёт](toolkit/video_cell_alignment.json),
  [скрипт](toolkit/audit_video_cell_alignment.py).

## 2026-09-19 — неизменные строки атрибутов: −3240 T на каждый кадр

- **Цель/база:** `469402c`, FAP3 zero-copy/no-op, прежние 4221 кадр и AY.
  Сократить работу вывода без ухудшения картинки и увеличения потока.
- **Полный профиль:** 192 атрибута (первые/последние 96) во всех кадрах
  равны 1. В cold-init обе страницы получают атрибуты 1; затем renderer
  копирует только средние 576. Компактный кадр и первый дельта-кадр
  декодируются как прежде; вход проверяется на постоянство краёв.
- **Такты/память:** стадия атрибутов **13018 → 9778 T**, **−3240/кадр**;
  cold-init **397967 → 430251 T**, +32284 один раз и +26 байт кода,
  ниже стека ZX0 `7B70`. Новых буферов нет. FAP3/ZX0 побайтно прежние,
  0 дополнительных секторов данных. За весь фильм формула даёт
  −13676040 T; отдельный полный прогон с опцией этим не подменяется.
- **Проверки:** 10 тестов общего тракта/пакетов и отдельный новый тест
  ISR прошли. Холодный запуск, оба экрана, compact/AY, блоки 509 байт,
  кольцо FFFF и точная разница тактов проверены. Частичный таймер:
  **44 опоздания из 405 вместо 49**, первое на кадре 62 вместо 61,
  максимум фазы **284794 T**; AY underrun остался на кадре 405/tick 2430.
- **Решение:** опцию сохранить как уменьшение постоянных затрат;
  точный темп и резервный допуск пока не обеспечены. Диск, ULA и ROM
  не включены; новый выпуск/TRD не создавались.
- **Материалы:** [описание и команды](toolkit/CONSTANT_ATTRIBUTE_BORDERS_ru.md),
  [профиль](toolkit/constant_attributes_profile.json),
  [таймер](toolkit/constant_attribute_clock_cpu.json),
  [аудит](toolkit/constant_attribute_timing.json),
  [профилирующий скрипт](toolkit/profile_constant_attributes.py).

## 2026-09-19 — FAP3 без двух нулей в пакете: меньше данных, сроки не выдержаны

- **Цель/база:** `17f079c`, FAP2 zero-copy/no-op; все 4221 кадр age3
  без титров, разрешение и 25326 AY-записей прежние. Уменьшить поток и
  подготовку кадров без изменения их содержимого.
- **Изменение:** FAP3 убирает два хранимых защитных нуля. Первый
  литерал служит lookahead Huffman, последний ноль создаётся в RAM.
  Резервируется один байт окна; допустимый пакет 294..4703, реальный
  максимум 3645. FAP2 остаётся вариантом по умолчанию.
- **Размер/такты:** raw 3106401 → 3097959; actual optimal ZX0 со всеми
  заголовками 1935757 → **1932429 байт**, **−3328 / −13 секторов**.
  Изменённый участок Z80 **54 → 14 T, −40 T/кадр**. Чтение/ZX0 из-за
  новых границ требуют отдельного полного замера, он ещё выполняется.
- **Проверки:** полный PC round-trip потока и независимая распаковка
  всех 379 блоков; 16 тестов Z80/формата/Huffman прошли, включая все
  значения lookahead, битовые смещения, границы RAM/кольца и точную
  разницу тактов. Таймер 50 Гц проверил 405 кадров: **49 опозданий**,
  первое на кадре 61, сбой AY на кадре 405/tick 2430; максимум фазы
  **316677 T**. Даже при бесплатной доставке и без ULA сроки не выдержаны.
- **Решение:** опцию сохранить ради меньшего размера; задача точного
  темпа этим не решена. Это частичная проверка исполнения полного
  фильма, не выпуск. Предварительный запас трёх TRD — 5235 байт,
  фактический диск/загрузчик не проверены; корневые образы прежние.
- **Материалы:** [описание и команды](toolkit/LEAN_FRAME_Z80_ru.md),
  [поток](toolkit/lean_frame_stream.json), [ZX0](toolkit/lean_frame_zx0.json),
  [таймер](toolkit/lean_frame_clock_cpu.json), [аудит](toolkit/lean_frame_timing.json).

## 2026-09-19 — точная публикация каждого кадра имеет приоритет над допуском

- **Уточнение пользователя/база:** `6bb2122`; избегать задержанных кадров
  и выводить каждый точно в своё время. Основная цель — 120/120/120 мс,
  ноль опозданий. Допуск 20 мс с компенсацией сохранён как резервный
  предел; намеренно сдвигать кадры ради этого допуска нельзя.
- **Изменение:** требования и документ обновлены; аудит отдельно считает
  все поздние/ранние публикации, первый пропущенный плановый срок и
  прохождение номинального графика по полям. Прохождение резервного
  допуска не приравнивается к достижению основной цели.
- **Результат/проверки:** повторная оценка прежних частичных записей:
  FAP2 с копированием — 5 опозданий из 65, zero-copy — 16 из 66,
  no-op — **50 из 406**, включая 9 в пределах одного поля. Все три не
  достигают основной цели. Шесть тестов прошли, включая точный график
  и восстановление после задержки. Счётчики не заменяют проверку точных
  моментов переключения; полный прогон расписания/диска ещё требуется.
- **Решение/границы:** принять приоритет точных сроков для дальнейшей
  оптимизации. Это изменение требований и аудита; Z80-код, поток и TRD
  не менялись, **0 T изменения**. Старые записи опытов сохранены.
- **Материалы:** [правило](toolkit/FRAME_JITTER_POLICY_ru.md),
  [аудит с новым приоритетом](toolkit/frame_timing_priority.json),
  [скрипт](toolkit/assess_frame_jitter.py).

## 2026-09-19 — разрешён джиттер 20 мс с возвратом к исходным срокам

- **Уточнение пользователя:** допустимо отклонение видео до 1/50 секунды;
  на следующих кадрах оно должно выравниваться. В `AGENTS.md` закреплены
  средние 25/3 fps, сроки от исходного начала, компенсация ближайшим
  готовым кадром, интервалы 5..7 полей, без пропусков и накопления сдвига.
  AY сохраняет равномерные 50 Гц.
- **Изменение проверки:** отдельный аудит трёх существующих частичных
  записей, гистограммы сроков/интервалов и начала/длины/восстановления
  поздних серий. Дополнительно измеряются точные T переключений: счётчик
  одного позднего поля не доказывает задержку не более 20 мс.
- **Результат:** в no-op-записи 406 публикаций, 41 превышает одно поле
  по счётчику, 49 превышают 20 мс по относительным T; максимум 349137 T
  (~98,48 мс). Затем AY underrun на 406. Даже новый допуск не выполнен.
- **Проверки/решение:** 5 тестов прошли, включая компенсацию и отказ при
  накоплении сдвига. Критерий принят; текущий таймер уже хранит исходную
  сетку сроков. CPU-код/TRD не менялись: **0 T изменения**. Полный релиз
  требует фактической проверки публикаций, AY и дисковой доставки.
- **Материалы:** [правило и примеры](toolkit/FRAME_JITTER_POLICY_ru.md),
  [аудит](toolkit/frame_jitter_1field.json), [скрипт](toolkit/assess_frame_jitter.py).

## 2026-09-19 — оценка очереди до 56 КиБ: одной перестановки RAM недостаточно

- **Цель/база:** полный FAP2 zero-copy/no-op, расчёт по CPU-базе `8390053`;
  использовать простаивающее время и всю память 128 КиБ без копирования
  готовых кадров. Натуральный кадр i ждёт публикации, компактный i+1
  реконструируется заранее; публикация предполагалась из IRQ.
- **Параметры:** 1..7 распакованных слотов по 8192, предельная раскладка —
  raw-кольцо 16 КиБ в банке 0, шесть слотов в 1/3/4 и прежний слот в 7.
  Новый Z80-код, реальные переключения страниц и producer не написаны.
- **Расчёт/отрицательный результат:** даже при бесплатном входе и идеальной
  прерываемости ZX0 семь слотов дают **708 поздних кадров**, первый 659,
  максимум **18527887,52 T** на 3009. Перераспределение работы помогает,
  но длинные тяжёлые серии всё ещё превышают доступный запас. Условная
  предварительная распаковка всего файла даёт 0 опозданий, но требует
  380 слотов. Доплаты 5000/10000/20000 T — чувствительность, не замер диска.
- **Проверки/границы:** проверены лимит слотов, EOF, сохранение суммы ZX0 T
  и контроль неограниченной очереди. Первый запуск остановился из-за
  ошибки модели освобождения слота; исправлена, полный расчёт повторён.
  Работа ZX0 распределена по байтам приближённо, фазы IRQ/новое управление/
  ULA/ROM/диск исключены. CPU-путь не менялся: **0 измеренных T экономии**.
- **Решение:** пока не переносить уменьшенное кольцо в проигрыватель;
  сначала уменьшить стоимость тяжёлых серий. Устойчивость 16-КиБ кольца
  не подтверждена. Сохранить расчёт, не считать его релизом.
- **Материалы:** [модель и команды](toolkit/FRAME_PIPELINE_ESTIMATE_ru.md),
  [разделение стадий](toolkit/frame_pipeline_schedule.json),
  [ограниченная очередь](toolkit/decoded_queue_schedule.json).

## 2026-09-19 — серии неизменившихся блоков: точное ускорение без новых данных

- **Цель/база:** `8390053`, весь FAP2 без титров; убрать повторную обработку
  нулевых векторов с пустой bitmap-маской, сохранив кэш/атрибуты/вывод.
- **Изменения:** сканер 88 байт 7A00..7A57, основной код 3994→3997 байт,
  без нового состояния и без изменения дискового потока. Для серии k
  старое время **260k T**, новое **92k+200/236/282 T** по типу выхода.
  Полная пустая полоса **4160→1672 T (−2488)**; короткие серии могут
  проигрывать. Все доплаты +7/+10/+14 T непустых путей включены в расчёт.
- **Полный прогон:** все 4221 кадр/оба экрана/25326 AY-записей/курсоры и
  защищённые области совпали; все T совпали с покадровой формулой,
  гистограмма сходится. Реконструкция **751710764→700958467 T**,
  **−50752297 T**. Вместе с zero-copy foreground **1577064563 T**,
  среднее **373623,445**, максимум **857794**, 1365 кадров выше 425448 T
  до IRQ/ULA/диска. Ручные ISR отдельно **16591971 T**; частоту не доказывают.
- **Таймер/неудача:** 406 кадров полностью проверены, 50 поздних публикаций,
  первая на кадре 61, максимум 4 поля по счётчику. Остановка на кадре
  **406 / AY tick 2436**; прежний zero-copy останавливался на 66.
  Это прогресс точности/скорости, но не доказательство плавного участка.
- **Проверки:** три новых теста, включая 32 случая серий 1..16, смешанные
  motion/intra/fragments/raw attrs/cache и ISR на границах инструкций.
  Исправлены два тестовых допущения: пиксели за пределами отображаемых
  полос и произвольный завышенный порог числа IRQ; детали в документе.
- **Решение:** сохранить ускорение; расписание непригодно для выпуска.
  ZX0/сектора прежние (1935757 байт), producer идеальный, ULA/ROM/диск
  отсутствуют; стартовые таблицы задаёт host. Корневые TRD прежние.
- **Материалы:** [код, T и команды](toolkit/NOOP_RUNS_Z80_ru.md),
  [сводка](toolkit/noop_runs_summary.json),
  [полный CPU](toolkit/bulk_frame_noop_cpu.json),
  [таймер](toolkit/bulk_frame_noop_clock_cpu.json).

## 2026-09-19 — LZSA2/ZX1 на полном FAP2: объём хуже ZX0

- **Цель/база:** `8390053`, одинаковые 3106401 байт FAP2 без титров,
  380 блоков по 8192. Выполнить пункт сохранённого плана сравнения
  форматов с простой распаковкой, прежде чем писать новый Z80-декодер.
- **Параметры:** ZX1 v1.5 optimal, авторские Windows-компрессор/декодер;
  LZSA2 v1.4.1 raw/prefer-ratio, сборка неизменённых исходников MSVC.
  Git-ревизии, SHA инструментов и флаги сохранены в отчётах.
- **Результат:** ZX1 **1971445 байт (+35688)**, LZSA2 **2010361 (+74604)**
  против **1935757 ZX0**, везде включено по 4 байта на блок. Ни один
  из 380 блоков новых кодеков не меньше ZX0. Превышение предварительного
  бюджета трёх дискет: 33781 и 72697 байт соответственно.
- **Проверки/границы:** все блоки обоих кодеков побайтно восстановлены
  авторским PC-декодером. Это не независимое исполнение Z80; скорость,
  IRQ/ULA/ROM/дисковод и переключение кодеков не измерены/не реализованы.
  Код проигрывателя прежний: **0 измеренных T экономии**.
- **Решение:** не заменять весь поток в текущей сборке; размер мешает
  трём TRD, выигрыш времени ещё неизвестен. Сохранить инструменты опыта.
- **Материалы:** [описание и воспроизведение](toolkit/CLI_CODECS_FAP2_ru.md),
  [скрипт](toolkit/probe_cli_codec_storage.py),
  [ZX1](toolkit/bulk_zx1_storage.json), [LZSA2](toolkit/bulk_lzsa2_storage.json).

## 2026-09-19 — целые пакеты FAP2: меньше времени CPU, больше секторов

- **Цель/база:** `a875d18`, все 4221 кадр без титров; уменьшить расходы
  частых коротких обращений к банковому ZX0 без изменения видео и AY.
- **Изменения:** общий пакет с длиной и двумя нулевыми разделителями,
  чтение одним запросом в прежние 4704 байта; максимум пакета 3647.
  Разборщик 408 байт; обвязка **373→379 T (+6)**. Вариант zero-copy
  векторов/карты: разборщик 212 байт, обвязка 391 T; заменяемые операции
  **4587→106 T**, суммарно **−4481 T/кадр**.
- **Полный результат:** побайтный PC round-trip FAP1 и полный Z80-прогон
  FAP2 с копированием: все кадры/экраны, 25326 AY-записей, курсоры и
  защищённая память точны. **1646731161 T**, **−57779696 T** к FAP1;
  среднее **390128,207**, максимум **864972**, 1573 кадра выше 425448 T
  без IRQ/ULA/диска. Ручные ISR отдельно 16591971 T.
- **Размер:** сырой поток **3106401 байт (+8442)**; полный optimal ZX0,
  380 блоков по 8192, **1935757 байт (+7416 / 29 секторов)**. Остаток
  предварительного бюджета трёх дискет 1907 байт; реальная сборка и
  стоимость дополнительной доставки ещё не проверены.
- **Неудачные/частичные опыты:** реальный таймер с опережением остановился
  на кадре **65 / AY 390**; zero-copy — **66 / AY 396**, до 5 полей
  опоздания. Полного zero-copy-прогона здесь нет: его итоговые CPU-цифры
  в сводке — проекция постоянной разницы, не измерение всего фильма.
- **Проверки/решение:** 9 тестов прошли. Сохранить общий пакет/zero-copy
  для дальнейшей работы; расписание отвергнуть для выпуска. Профиль
  выявил 488407/810432 неизменившихся блоков (60,26%), без изменения кода
  и без заявленной экономии; это следующий резерв. Producer пока идеальный,
  ULA/ROM/диск, стартовые таблицы и тома не реализованы. TRD прежние.
- **Материалы:** [формат, RAM, T и команды](toolkit/BULK_FRAME_Z80_ru.md),
  [сводка](toolkit/bulk_frame_summary.json), [CPU](toolkit/bulk_frame_cpu.json),
  [ZX0](toolkit/bulk_frame_zx0.json), [профиль](toolkit/frame_control_profile.json).

## 2026-09-19 — весь FAP1 на одном Z80: данные точны, расписание не выдержано

- **Цель/база:** `1963bab`, все 4221 кадр без титров. Соединить банковый
  ZX0, разбор FAP1, очередь AY, маски, реконструкцию и вывод в общей RAM.
- **Изменения:** разборщик 193 байта DC00..DCC0, банковые переходы 31 байт
  7F00..7F1E, заголовок BA50..BA56. Подготовка и публикация разделены;
  прежняя обвязка **363→373 T (+10)**. Разбор/переходы **1743 T/кадр**,
  ранее host без учтённых T. AY enqueue **1705+42N T** прежний. Добавлены
  два варианта шестиполевого таймера: 58 байт и 123 байта с опережением.
- **Полный результат:** все 4221 компактный/нативный кадр, обе экранные
  страницы и 25326 AY-записей совпали; таблицы/TR-DOS workspace сохранены.
  **1704510857 T** foreground, **+465202926** к прежним **1239307931 T**
  видео. Маски/реконструкция/вывод покадрово прежние. Среднее **403816,834 T**,
  максимум **862649 T** (кадр 4052), **1751 кадр** выше 425448 T без
  IRQ/ULA/диска. Ручные IRQ отдельно **16591971 T**; стартовый заголовок
  отдельно **793898 T**. Полная гистограмма сходится.
- **Расписание/неудачные попытки:** идеальное кольцо, период 70908 T,
  настоящий ISR, EI/HALT и сохранение регистров. Оба варианта опоздали
  впервые на кадре **49**, дошли до задержки **5 полей**, остановились
  на кадре **62** перед AY-тактом **378**. Проверены полностью 0..61.
  Опережение по 256 байт ускоряет отдельные кадры, но не устраняет
  непрерывную тяжёлую серию в пределах одной 8-КиБ истории.
- **Проверки:** 17 тестов прошли; исправлены три ошибки тестовой обвязки,
  описанные в документе. Полный прогон данных завершён; два прогона
  расписания сохранены как неуспешные частичные, а не как релизы.
- **Решение/границы:** принять общий тракт и стенд как проверенную основу,
  отвергнуть нынешнее расписание для выпуска. Частые короткие запросы
  дали больше расходов, чем раздельные измерения: требуется укрупнять
  подачу данных и пересмотреть запас распакованного входа. Таблицы при
  старте пока устанавливает host; producer бесплатный, ULA/ROM/диск и
  смена томов не проверены. Корневые TRD остаются прежними.
- **Материалы:** [код/RAM/команды](toolkit/FRAME_STREAM_Z80_ru.md),
  [сводка](toolkit/frame_stream_summary.json),
  [весь CPU](toolkit/frame_stream_cpu.json),
  [таймер](toolkit/frame_stream_clock_cpu.json),
  [таймер с опережением](toolkit/frame_stream_clock_ahead_cpu.json).

## 2026-09-19 — повторная проверка выбора плотных полос: дополнительной экономии нет

- **Цель/база:** `1963bab`, все 4221 кадров FAP1. Проверить, можно ли
  ускорить вывод дополнительными битами карты без изменения пикселей:
  заменять частичную полосу полной, если новая формула Z80 даёт меньшие T.
- **Параметры/результат:** сравнить `296P−136Z` и `5853+4×parity` на каждой
  полосе. **0 изменённых полос/кадров, 0 байт, 0 T экономии**; прежние
  **405533717 T** вывода. SHA256 входа и результата совпали. Существующий
  `probe_cell_output_masks.py` уже заполняет полосы при ≥18 клетках;
  дополнительное заполнение ничего не даёт.
- **Проверка/решение:** полный разбор/обратная проверка FAP1, неизменность
  данных вне карт и сохранение обязательных битов. Повторный ZX0-прогон
  остановлен после сообщения о 101/379 блоке: при одинаковом SHA он
  избыточен. Частичный отчёт сохранён; размер того же входа **1928341 байт**
  уже измерен в `frame_packet_zx0.json`. Ветку оптимизации отклонить;
  скрипт оставить как воспроизводимую проверку. TRD не менялись.
- **Материалы:** [скрипт](toolkit/optimize_native_bands.py),
  [полный расчёт](toolkit/native_bands.json),
  [прерванный повтор ZX0](toolkit/native_bands_zx0.json).

## 2026-09-19 — заголовки блоков и непрерывный вход перенесены на Z80

- **Цель/база:** `a0c73d7`, полный FAP1 без титров, 4221 кадр. Устранить
  host-разбор блоков и host-копирование распакованного входа перед интеграцией.
- **Изменения:** reader 132 байта в DB00..DB83, загрузчик 104 байта
  в 7E90..7EF7; остальная RAM и ZX0 прежние. Добавлен отсутствовавший
  RES в узкий CPU-стенд, с проверкой всех 64 форм и сохранения флагов.
- **Измерение:** все 3097959 байт / 379 блоков, 12102 запроса по ≤256 байт:
  **369471422 T**, из них ZX0 **297311182**, reader **72160240**.
  Для этой новой стадии прежний host-стенд учитывал 0 Z80 T; добавлено
  **72160240 T** прежде исключённой работы, это не замедление релиза.
  Максимальный запрос 68874 T; гистограмма инструкций сходится.
- **Проверки:** пять тестов прошли, включая AY IRQ после каждой инструкции,
  кольцо >64 КиБ, межблочные запросы и опережающую распаковку. Исправлены
  три ошибки тестовой обвязки; детали сохранены в документе ниже.
- **Решение/границы:** принять для общего разборщика кадров. Сырые данные
  кольца пока подаются бесплатно; FAP1/AY/вывод/ULA/ROM/диск и внешняя
  установка запроса исключены. Выпуск и 25/3 кадра/с не подтверждены.
- **Материалы:** [код, RAM, циклы, команды](toolkit/STREAM_READER_Z80_ru.md),
  [полный отчёт](toolkit/frame_packet_reader_cpu.json),
  [скрипт](toolkit/benchmark_stream_reader.py).

## 2026-09-19 — выборочный кэш исполняется Z80: ещё 75,36 млн тактов с учётом ZX0

- **Цель/база:** `73a1879`, все 4221 кадр SC04 без титров, прежние пиксели
  и AY. Пропускать неиспользуемые группы четырёх строк в реальном кэше.
- **Путь/RAM:** карта BA40..BA42; прежний кэш 7400..77FF и кольцо 64 КиБ.
  Реконструктор **3928→3994 байта**, конец 8F9A; обвязка перенесена с
  8F60 на 7900, прежние 363 T. Экраны, таблицы и стеки не перекрываются.
- **Циклы:** прежние 96 копируемых строк **55572 T**; новые
  **3795+2305N T**, плюс **46 T** установки карты. Полная дельта активного
  кадра **3589−2305(24−N)**, неактивного 0. Нулевые граничные строки прежние.
  Первый тест остановился на неподдержанном стендом SCF; он оказался
  избыточным и удалён с экономией ещё 12 T/активный кадр. Полного прогона
  той предварительной версии не было.
- **Полный общий Z80:** **1239307931 T**, **−77006809**; среднее
  **293605,290 T**, максимум **390083 T** на кадре 3686. Для каждого
  кадра разница совпадает с формулой, другие стадии неизменны; замедлившихся
  кадров нет, 752 неактивных неизменны. Все экраны/входы/кэш/таблицы проверены.
- **Полный ZX0:** все 381 блок; обычный turbo **173653789 T**,
  банковый **298144497 T (+1646686)**. Чистая экономия двух стадий
  **75360123 T** за **9672 байта / 38 секторов**. Средний расчётный порог
  окупаемости дополнительного сектора 559,362 мс, не измерение дисковода.
- **Проверки/решение:** три новых Z80-теста (24 бита/границы/формула/IRQ),
  две проверки старого машинного кода и два PC-теста карт прошли. Все полные
  прогоны завершены. Принять для интеграции; раздельное среднее теперь
  **364238,907 T**, остаток **61209,093 T** до входных копий/AY/ULA/диска.
  Скорость и выпуск не подтверждены; далее общий FAP1-разбор, банковый ZX0
  и AY, затем расписание/диск. SC04-замеры не относятся к FAP1. TRD прежние.
- **Материалы:** [RAM, формулы и команды](toolkit/SELECTIVE_CACHE_Z80_ru.md),
  [полный общий CPU](toolkit/selective_cache_pipeline_cpu.json),
  [сводка](toolkit/selective_cache_summary.json).

## 2026-09-19 — явные длины пакета для будущего общего разбора

- **Цель/база:** `73a1879`, весь SC04 без титров. Убрать необходимость
  вычислять длину литералов по 192 векторам при чтении каждого пакета.
- **Формат:** FAP1, заголовок **11→7 байт** с явными длинами масок,
  Huffman и литералов. Постоянные n=1/vectors=192 исключены; остаток
  значащих битов сохранён в свободных битах flags. AY/карты/значения прежние.
- **Полный результат:** сырые данные **3114843→3097959 (−16884)**,
  ZX0 **1927647→1928341 (+694)**. Изменение заголовков и границ блоков
  немного ухудшило сжатие. Доплата 3 сектора, предварительный запас
  трёх TRD **9323 байта**. Окно значений максимум 3319 из 4704 байт.
- **Проверки:** все 4221 пакета, точный обратный SC04/FSA2/AY, все
  379 ZX0-блоков независимым PC-декодером. Тест смешанных атрибутов,
  длины, флага, обрыва и лишних данных прошёл. Прерванных прогонов нет.
- **Решение/ограничение:** выбрать для следующей реализации разборщика,
  подтвердить стоимость всей подачи на Z80. Новый горячий путь ещё не
  реализован (**0 T изменения**); экономия CPU и скорость не заявляются.
  Прежние CPU-замеры SC04 не относятся к новому порядку/блокам FAP1.
  Корневые TRD прежние. [Формат, команды и план интеграции](toolkit/FRAME_PACKET_STREAM_ru.md),
  [пакеты](toolkit/frame_packet_stream.json), [ZX0](toolkit/frame_packet_zx0.json).

## 2026-09-19 — быстрый обход пустых экранных ячеек

- **Цель/база:** `1ebb4ec`, все 4221 кадр FSC2 без титров. Сократить
  вывод без новых байтов, таблиц или изменений изображения/AY.
- **Путь:** восемь развёрнутых ADD/CALL C, маска сохраняется в AF';
  нулевая маска пропускает сразу восемь столбцов. Плотные полосы прежние.
  Код/состояние **724→769 байт**, конец 9301 перед AY 9400.
- **Такты по Zilog:** маска **498+277P→233+296P T** для ненулевой,
  **498→97 T** для нуля. Полный вывод
  **58784+4793D+4O+277P → 37584+5853D+4O+296P−136Z**;
  D/O — плотные/нечётные плотные полосы, P/Z — ячейки/нулевые маски остальных.
  Пустой кадр **58784→26704 T**. Все ветви сверены по инструкциям.
- **Полный общий Z80-прогон:** вывод **478315535→405533717 T**, **−15,216%**;
  маски + восстановление + вывод + обвязка **1316314740 T**, **−72781818**.
  Среднее **311849,026 T**, максимум **390083 T** (прежде 393291, кадр 3686).
  Для каждого кадра разница совпала с формулой, другие стадии неизменны.
- **Проверки:** все экраны/входы/таблицы/TR-DOS guard/стек, девять тестов
  включая 256 масок, n−2 и реальный AY IRQ после каждой инструкции.
  Код без опции побайтно прежний. В сводке уточнена проверка обвязки:
  её инструкции прежние, адреса состояния вывода перемещены. Прерванных
  полных прогонов нет. Сжатый поток остаётся **1917975 байт**.
- **Решение:** принять для интеграции. Раздельная сумма с банковым ZX0
  **1612812551 T**, среднее **382092,526**, остаток **43355,474 T** до
  пакетного входа/AY/ULA/диска. Плавность и новые TRD ещё не проверены;
  тяжёлые плотные кадры требуют следующей оптимизации кэша.
- **Материалы:** [расчёты и команды](toolkit/FAST_CELL_DISPATCH_ru.md),
  [полный прогон](toolkit/fast_cell_dispatch_pipeline_cpu.json),
  [покадровые разницы](toolkit/fast_cell_dispatch_summary.json).

## 2026-09-19 — выборочный кэш: подробные карты слишком велики, группы строк помещаются

- **Цель/база:** `1ebb4ec`, FSA2 без титров, все 4221 кадр, прежние
  пиксели/AY. Кэш базы требует **203949448 T**; старые строки полностью
  копируются в 3469 кадрах. Найти карту пропуска ненужных копий.
- **Параметры:** покрытие источников всех временных векторов; 48 байт
  карты для восьмибайтовых участков, 12 для строк, 3 для групп четырёх строк.
  Перед каждым исходным пакетом после AY вставляется карта; содержание
  исходного FSA2 сохраняется. Optimal ZX0, блок 8192 байта.
- **Полные результаты:** база **1917975**; участки **1982062 (+64087)**,
  строки **1938711 (+20736)** — оба выше предварительного бюджета.
  Группы четырёх строк **1927647 (+9672)**, запас **10017**. Копии старого
  кадра сокращаются **10656768→5689088 байт**, −46,62%; это **не** процент
  ускорения. Добавленные 9672 байта — 38 секторов при округлении разницы.
- **Проверки:** все кадры и 1039272 чтения в каждом причинном кольцевом
  кэше; исходный FSA2/AY побайтно возвращён независимым разбором. Все
  **404/385/381 ZX0-блоков** проверены PC. Два теста покрывают все временные
  векторы/границы, повреждённую карту и обрыв/лишние данные.
- **Решение:** подробные карты оставить контрольными; группы четырёх строк
  проверить на Z80 следующими. В этой попытке новый горячий путь ещё не
  реализован (**0 T изменения кода**); CPU, IRQ, дисковая доставка и итоговая
  вместимость с новым PLAYER не проверены. Прерванных запусков нет.
  Корневые TRD не меняются. [Расчёты и команды](toolkit/SPARSE_MOTION_CACHE_ru.md),
  [скрипт](toolkit/probe_sparse_motion_cache.py),
  [покадровый SC04](toolkit/sparse_motion_cache_quads.json),
  [ZX0](toolkit/sparse_motion_cache_quads_zx0.json).

## 2026-09-19 — банковый ZX0: точная память, но недостаточный запас скорости

- **Цель/база:** `9e4c6c0`, 379 блоков FSA2, все 4221 кадр без титров
  и прежний AY. Совместить вход из кольца 64 КиБ с историей ZX0 в банке 7.
- **Изменение:** окно BC00..BCFF, история E000..FFFF, код 7C00,
  частный стек 7B70..7BDF. Выход ограничен порциями 256 байт; проверены
  конец 0000, смена банков и оборот кольца. Объём остаётся **1917975 байт**.
- **Первый полный прогон:** **319378688 T**, против обычного turbo
  **172816320**, то есть **+146562368 T**. Код 567 байт, максимум
  порции 62005 T. Корректность памяти подтверждена; для скорости слишком дорого.
- **Ускоренный полный прогон:** короткая проверка литералов и LDI-группы
  пополнения: **296497811 T**, **−22880877 T** от первого варианта,
  но **+123681491 T** к turbo. Код 649 байт, максимум порции **59818 T**.
  Локальные пути: помещающийся литерал **107→51 T (−56)**, полная копия
  256 байт **5381→4361 T (−1020)**. Полные ветви и границы учтены по Zilog.
- **Проверки:** все блоки, байты/порядок входа, точные остановки, стек,
  обе экранные области и таблицы; 4 теста включая AY IRQ после каждой
  инструкции и побайтную совместимость прежних генераторов. Первичная
  отрицательная проверка исправлена для обёртки RuntimeError CPU-стенда;
  ошибки данных уже обнаруживались. Прерванных полных прогонов нет.
- **Решение/границы:** механизм оставить для интеграции, **не считать
  достижением скорости**. Сумма с прежним общим CPU-путём **1685594369 T**,
  среднее **399335,316 T**, остаток **26112,684 T/кадр** до номинального
  бюджета. Хост ещё пишет дескрипторы/цели и подаёт пакеты; AY, ULA,
  ROM/диск и полное расписание не включены. Следующий резерв — пустые
  ячейки при выводе. TRD не заменены, выпуск не заявляется.
- **Материалы:** [расчёты, RAM и команды](toolkit/BANKED_ZX0_ru.md),
  [сводка](toolkit/banked_zx0_summary.json),
  [декодер](toolkit/banked_zx0.py), [стенд](toolkit/benchmark_banked_zx0.py).

## 2026-09-19 — прямые атрибуты убирают пики; маски исполняются Z80

- **Цель/база:** `11dc864`, все 4221 кадр без титров, прежние пиксели age3,
  разрешение, целевые 25⁄3 кадра/с и AY 50 Гц. Ускорить тяжёлые атрибуты
  и включить развёртку масок в фактически исполненный CPU-путь.
- **Формат/параметры:** FSC2/FSA2, бит 6 флагов выбирает 768 абсолютных
  атрибутов в конце литералов; их Huffman-коды исключены, маски нулевые.
  Порог ≥128 изменённых атрибутов выбрал **41 кадр**, включая прежние пики
  3375, 3685 и склейку 4086. Остальные кадры используют прежние коррекции.
- **Объём/качество:** +22372 сырых байта, но **1917975 ZX0** с заголовками,
  **−573** относительно базы. 379 блоков ≤8192 байт проверены PC и Z80.
  Предварительный запас трёх TRD **19689**. Все кадры восстановлены новым
  скалярным декодером и Z80; все 25326 AY-состояний R0..R10 проверены.
  Вход кадра максимум **3319** байт с защитой против окна 4704.
- **Циклы атрибутов:** прямой проход **16209 T** от входа до RET,
  обвязка **337 → 363 T**. Невыбранный кадр **+55 T** (29 T проверки,
  26 T передачи флага); для выбранного разница равна
  16209 − прежний проход атрибутов + 26. Все 4221 кадр проверены:
  **1308565331 T**, **−2137534** от базы, среднее **310013,109 T**,
  максимум **372793 T** вместо 405873. Прежняя генерация кода без опции
  сохранена; отдельный тест сверяет SHA машинного кода из `11dc864`.
- **Маски на Z80:** код с 7800, промежуточные флаги BF80..BFBF,
  конечные 480 масок A4C0..A69F. Полный проход по таблице инструкций:
  158 + сумма по 8 верхним и 60 нижним флагам; стоимость группы
  161 T для нуля, 227 T для FF, иначе 370+8×popcount. Внешние
  LD HL/CALL (27 T) пока хостовые и не включены.
- **Полный прогон с масками:** **1389096558 T**, среднее **329091,817 T**,
  максимум **393291 T**. Развёртка добавила **80531227 T**, максимум
  **23643 T/кадр**, прежде эта работа выполнялась хостом. Для каждого
  кадра разница двух прогонов точно равна стоимости масок. Проверены
  оба экрана, TR-DOS guard, таблицы, стек и курсоры; готовые маски хост
  в память не записывает. Заголовки/векторы/остальной вход подаёт хост.
- **ZX0 и весь учтённый CPU:** отдельно **172816320 T**, **+1055208 T**
  от базы; максимальный блок 631504 T. Сумма измеренных стадий
  **1561912878 T**, среднее **370033,849 T**, средний остаток
  55414,151 T до номинального бюджета. Копирование/подача данных,
  полный разбор пакета, AY, ULA/ROM/диск ещё не входят.
- **Проверки/решение:** 9 разных тестов прошли, включая все 256 вариантов
  флага, mixed raw/coded кадры, точные CPU-разницы, FSA2/AY framing,
  сохранение старой генерации и AY IRQ после каждой инструкции нового
  пути. Оба полных CPU-прогона и все блоки завершены; прерванных запусков
  в этой попытке нет. Принять для следующей интеграции, **не считать выпуском**.
- **Следующее ограничение:** история ZX0 в банке 7 не может одновременно
  отображаться с входом из другого банка кольца. Максимальный сжатый
  блок 6134 байта больше окна 4704. Проверить 256-байтовый промежуточный
  вход BC00..BCFF, переключения и конец E000+8192=0000; затем соединить
  разбор FSA2, AY, диск и переключение через шесть полей. TRD не заменены.
- **Скрипты/результаты:** [описание и команды](toolkit/RAW_ATTRIBUTES_ru.md),
  [покадровая сводка](toolkit/raw_attributes_summary.json),
  [полный общий CPU](toolkit/raw_attributes_128_metadata_cpu.json),
  [ZX0 CPU](toolkit/raw_attributes_128_zx0_cpu.json),
  [новый формат](toolkit/raw_attribute_stream.py),
  [Z80-маски](toolkit/frame_metadata_z80.py).

## 2026-09-19 — адаптивные фрагменты, общий Z80-путь и сжатие AY с видео

- **Цель/база:** `6103e11`, все 4221 кадр монтажа без титров, прежние
  разрешение/25⁄3 кадра/с/AY 50 Гц. Ускорить тяжёлые кадры с учётом времени
  вывода, проверить реальную общую память и вернуть данные в бюджет трёх TRD.
- **Параметры:** индивидуальный лимит реконструкции = 375000 либо
  385000 − 8000 поправки модели − измеренное время вывода. Учитывается
  отключение кэша движения (60398 T). Однокадровые группы, прежний
  независимый кадр склейки 4086. Ни одного дополнительного изменения пикселей.
- **Не прошедший по объёму вариант:** ориентир 375000, 61862 быстрых
  фрагмента. Видео 1833006 байт ZX0, с несжатым AY **1951370**:
  превышение предварительного бюджета **13706 байт**. Вариант 385000
  (56892 фрагмента): видео 1814845, с AY **1933209**, запас лишь **4455**.
  Для обоих восстановлены все кадры PC и все блоки оптимального ZX0;
  вариант 385000 не проходил полный Z80-прогон. Сохранён как контроль,
  запас недостаточен для уверенного выбора перед окончательной сборкой.
- **Общий Z80-путь 375000:** реальные очистка, восстановление кадра,
  вывод в задний экран и публикация 7FFD. Хост поставляет метаданные и
  входные значения, не готовые кадры. Вход A6A0..B8FF (4704 байта),
  максимум 2802. Все **4221 кадр**, оба физических экрана и TR-DOS guard
  проверены. Код восстановления/вывода прежний; новая обвязка **337 T**
  на кадр вместо хостовой работы, разовая очистка **397967 T**.
- **CPU результат:** восстановление + вывод + обвязка **1310702865 T**
  против 1403831746, **−93128881 T**; среднее **310519,513 T**.
  Максимум **405873 T**, прежде 450831; число кадров >425448: **939 → 0**.
  Однако три кадра >375000, худший 3375 оставляет лишь 19575 T на остальные
  стадии. В четырёх кадрах сама модель выбора не достигла заданного лимита;
  результат не скрыт и не назван гарантией полного времени доставки.
- **Принятый для дальнейшей интеграции формат FSA1:** перед каждым кадром
  шесть неизменённых записей очереди AY, общая история ZX0. **1918548 байт**
  с заголовками, 376 блоков; экономия **32822** против отдельного несжатого
  AY, предварительный запас трёх TRD **19116**. Видео/AY побайтно восстановлены,
  все **25326 AY-состояний** проверены по R0..R10. Дополнительной потери нет.
- **ZX0 на Z80:** все блоки точны; **171761112 T**, максимум блока 633994.
  Сумма измеренных стадий **1482463977 T**, среднее **351211,556 T**.
  От прежнего варианта с раздельными потоками: +161996 байт/633 сектора
  за −46458607 T; средний порог окупаемости сектора **20,701 мс**, только
  расчёт. Чтение диска, ROM и ULA не измерены, полного расписания нет.
- **Проверки/решение:** 7 тестов общего пути, IRQ после каждой инструкции,
  индивидуальных лимитов, framing и ошибочных AY-записей прошли. CPU считает
  каждую инструкцию по Zilog, сверяет гистограмму и стек. Метаданные ещё
  разворачивает хост; общий Z80-разбор FSA1/ZX0/AY, ожидание шести полей,
  независимые старты дискет и Fuse остаются следующими шагами. Сначала
  проверить быстрые атрибуты тяжёлых кадров. **Не выпуск**, TRD не изменены.
- **Воспроизведение:** [подробности и команды](toolkit/DELIVERY_BUDGET_ru.md),
  [общая сводка](toolkit/delivery_budget_summary.json),
  [покадровый Z80](toolkit/delivery_budget_375_pipeline_cpu.json),
  [ZX0 CPU](toolkit/delivery_budget_375_audio_zx0_cpu.json),
  [выбор](toolkit/probe_delivery_budget.py),
  [общий стенд](toolkit/frame_output_pipeline.py),
  [A/V-поток](toolkit/cell_audio_stream.py).

## 2026-09-19 — карты ячеек ускоряют вывод; однокадровый вход помещается в RAM

- **Цель/база:** `4f92850`, весь монтаж без титров — 4221 кадр age3,
  прежние разрешение, 25/3 кадра/с и AY 50 Гц. Сократить время вывода
  с учётом дополнительных данных для диска. Все сохраняемые экраны прежние.
- **Отклонённая попытка:** описание изменений n−2 горизонтальными
  отрезками пар байтов, объединение разрыва ≤1 пары. Полный PC replay
  точен, но 1068012 сырых байт требуют **619994 ZX0** с заголовками,
  больше имеющегося запаса 345044. Z80-путь не реализован. Сохранены
  [скрипт](toolkit/probe_output_spans.py) и [замер](toolkit/output_spans_zx0.json).
- **Выбор:** 80 байт битов ячеек 8×8 на кадр, сравнение с n−2;
  ≥18 изменённых ячеек полосы означают линейный вывод всей полосы.
  Предварительный порог 24 дал DEFLATE 199841 и был заменён по формуле
  путей; отдельные CPU/ZX0 измерения 24 не заявляются. Итоговые карты
  **337680→163932 байта ZX0**, 42 блока, PC/Z80 round-trip всех блоков.
- **Горячий путь:** точная формула `58784+4793*D+4*O+277*P` включает
  копирование карты, bitmap, все атрибуты, paging и RET. D — плотные
  полосы, O — нечётные из них, P — отдельные ячейки остальных полос.
  Все 4221 кадр исполнены и оба экрана проверены: **650409669→478315535 T**,
  −172094134; среднее **154089→113318,061**, максимум нового **146202**.
  Код **405→720**, состояние **3→4**, таблицы **672→512 байт**, карта 80.
  IRQ/ULA/внешний вызов/подготовка аргументов/диск не включены. Три теста,
  в том числе AY IRQ после каждой инструкции, прошли.
- **Цена новых данных:** ZX0 карт **19064798 T**; чистая экономия CPU
  **153029336 T / 36254,285 на кадр**. Отдельные видео+карты+AY
  **1756552 байта**, предварительный запас трёх TRD **181112**.
  Минимум 641 дополнительный сектор: CPU-выигрыш допускает в среднем
  до 67,337 мс добавленной задержки на сектор. Это расчёт порога,
  не измерение TR-DOS/диска; признание выигрыша доставки отложено.
- **Полный контроль монтажа:** реконструкция прежних групп ≤8 повторно
  проверена на всех 4221 кадрах: **925516211 T**, максимум **305737**.
  С новым выводом максимум **450831**, **939 кадров >425448** без ZX0
  и прочих стадий. Оптимистическая очередь двух стадий требует 5 кадров.
  Оба отдельные ZX0 тоже проверены полностью; сумма четырёх стадий
  **1528922584 T**, среднее **362218,096**. Общего PLAYER/очереди нет,
  средний запас не доказывает плавность.
- **Подготовка интеграции:** добавлен предел группы 1..8 (по умолчанию
  8 без изменения прежних форматов) и FSC1 с картами перед значениями.
  Однокадровый вариант полностью восстановлен PC, framing протестирован;
  максимум значений с защитой **2424**, метаданные **672 байта**.
  Предложены окно A6A0..B8FF (4704), метаданные A400..A69F, карта
  7300..734F. Поток **2640025→1708995 ZX0**, с AY **1827359**,
  предварительный запас **110305**. Проверены все 323 блока PC.
  CPU цифры групп 8 не перенесены на группы 1; совместная память/ROM
  ещё не проверены. Кольцо диска и корневые TRD прежние.
- **Решение:** сохранить частичный вывод и однокадровый формат как
  проверенные компоненты/вход для интеграции. Следующий шаг — выбирать
  ускоренные фрагменты с учётом конкретного времени вывода, устранить
  серии превышений бюджета, затем общий декодер/диск и выпуск ≤3 TRD.
  [Формулы и команды](toolkit/CELL_OUTPUT_ru.md),
  [сводка](toolkit/cell_output_summary.json),
  [вывод Z80](toolkit/cell_screen_z80.py),
  [формат FSC1](toolkit/cell_output_stream.py).

## 2026-09-19 — удаление титров: −90 с, −531178 байт видео ZX0

- **Цель/база:** по новому разрешению пользователя удалить титры, сохранив
  всю историю и сцену после титров. База `f4a3d85`, полный age3, 4971 кадр,
  прежний AY 50 Гц. Исходные и ZX-кадры осмотрены около обеих границ.
- **Параметры:** вырезан `[490,32;580,32)` с, кадры `[4086;4836)` и
  AY-такты `[24516;29016)` с нуля. Осталось **4221 кадр / 506,52 с /
  25326 AY-тактов**, включая исходный последний кадр 4970. Каждый
  сохранённый экран и AY-состояние побайтно совпадает с выбранной базой.
  Разрешение, 25/3 кадра/с и AY 50 Гц сохранены. Монтаж зафиксирован
  в `movie_no_credits.json`; AGENTS и действующий план обновлены.
- **Упаковка:** на склейке пересчитаны дельты и атрибуты; FSF1 использует
  полные фрагменты, не ссылается на удалённый предшественник. Таблицы
  Huffman не менялись. FSF1 **2980664→2258014 байт**; 276 блоков ZX0
  по ≤8192: **2005434→1474256 байт** с заголовками (−531178 / 26,49%).
  AY измерен заново: **118364 байта несжатых команд регистров**, итого
  **1592620**. Предварительный запас трёх TRD **345044**, для двух
  недостаёт **300844**. Не включены старты дискет, рост PLAYER,
  округление секторов/interleave; прежняя оценка AY 77696 не подставлялась.
- **Проверка:** полностью восстановлены оба видеопредставления всех 4221
  кадров и каждый блок ZX0, переиграны регистры всех 25326 AY-тактов;
  четыре теста границ/EOF/дельт/FSF1 прошли. На Z80 отдельно исполнены
  реконструкция и вывод **24 кадров 4072..4095**. Инструкции прежние,
  изменение горячего пути **0 T**; кадр склейки **395018 T**, максимум
  выборки **453613 T** до ZX0/IRQ/ULA/ROM/диска. Полный прогон новой
  последовательности и совместный проигрыватель пока не проверены.
- **Решение:** монтаж принят как вход следующей сборки; качество оставшегося
  материала не снижено. Подготовлены совместимые входы прежнего сборщика,
  FSF1 и PC-предпросмотр концовки. Запас данных позволяет продолжить работу
  над тремя дискетами, но новый выпуск и плавность ещё не подтверждены.
  Корневые TRD не заменялись. Далее — частичный вывод, общий декодер и
  проверенная подача диска, затем упаковка релиза через LFS.
- **Материалы:** [описание и команды](toolkit/NO_CREDITS_ru.md),
  [сводка](toolkit/no_credits_summary.json),
  [скрипт монтажа](toolkit/prepare_edited_movie.py),
  [FSF1](toolkit/repack_edited_fragments.py),
  [CPU склейки](toolkit/no_credits_join_cpu.json).

## 2026-09-19 — отложенный опыт с редкими крайними строками

- **Цель/база:** `f4a3d85`, полный age3, ускорить вывод 8..87 без
  изменения изображения или данных на диске. Подготовлен необязательный
  путь с OR-проверкой строк 8..11 и 84..87 и историей отдельно для банков
  5/7; история нужна и для стирания старого изображения через два кадра.
- **Расчёт, не измерение:** база 154089 T; черновая формула
  `143252 + 10*(bank==7) + 7122*(upper+lower) + 4*lower`, где upper/lower
  означают ненулевые байты текущего либо старого заднего экрана. Без краёв
  143252/143262 T (−10837/−10827); с обоими 157500/157510 T
  (+3411/+3421). IRQ/ULA/ROM/диск не включены. Формула требует проверки
  исполнения каждой ветки; стенд и тесты нового пути ещё не закончены.
- **Решение/проверка:** опыт прерван при переходе к разрешённому пользователем
  удалению титров. Вариант по умолчанию побайтно совпал с прежним кодом
  в проверке склейки; новый путь не проверен и в PLAYER не включён.
  Генератор восстановлен. Незавершённая реализация сохранена как
  [патч](toolkit/experiments/sparse_edges_unverified.patch), применимый к
  `f4a3d85`, чтобы продолжить опыт после смены монтажной последовательности.

## 2026-09-19 — полный вывод Z80: 154089 T/кадр, нужен частичный вывод

- **Цель/база:** `d4f2b15`, все 4971 кадр age3. Измерить недостающую
  развёртку компактных данных в чередующиеся физические экраны. Пиксели,
  атрибуты, FSF1/ZX0 и AY прежние; это новая отдельная стадия, не выпуск.
- **Остановленная попытка:** диапазон 12..83 отклонён на кадре 25
  (с нуля), поскольку вне центральных 72 строк есть ненулевые байты.
  Аудит нашёл 830 таких байтов в 466 кадрах. Сохранённый checkpoint
  содержал только первый кадр. Полный новый прогон использует все
  строки с ненулевыми данными, **8..87**; остальные везде нулевые.
- **Горячий путь новой процедуры:** чередовать порядок верхней/нижней
  строки в паре байтов, **59→51 T/байт**; атрибуты LDIR→16 LDI в цикле,
  **16123→12967 T** (−3156). С адресацией/paging/RET **177725→154089 T**
  (−23636); весь фильм **883470975→765976419 T** (−117494556).
  Формула `−256*R−3156`, R=80, в связанном отчёте. База — прямой вариант
  этой процедуры, не выпускной PLAYER. Код **433→405 байт**, состояние 3,
  таблицы 672; конец 9198h. IRQ/ULA/ROM/диск и внешний CALL не включены.
- **Проверка:** все 4971 кадр выведены Z80 и оба экрана сверены побайтно.
  Проверены paging без смены видимого экрана, сохранение источника/стека,
  допустимые записи, гистограмма тактов. Три теста: все строки/значения,
  оба банка, границы, запрет обрезания и AY IRQ после каждой инструкции,
  включая повторения LDIR. Отдельный PC-аудит признаков n−2 доказал
  покрытие всех изменений: в среднем 96,366 плитки и 13,859 атрибута,
  максимум 160 плиток; генерация признаков на Z80 ещё не измерена.
- **Результат для сроков:** сумма раздельных реконструкции/вывода
  **1894252942 T**, максимум **463775**, **1684 кадра >425448**. Даже
  оптимистичная очередь требует 27 компактных кадров (103680 байт).
  С отдельным ZX0 среднее **411119,442 T**, остаётся всего 14328,558
  до номинального бюджета на неучтённые стадии. Полная развёртка сама
  по себе не подтверждает плавность.
- **Решение:** сохранить как плотный режим и базу сравнения; реализовать
  частичный вывод с историей n−2, начиная с редких крайних строк. Затем
  нужны общий парсер/окна/ZX0 и измеренная подача диска. Карта входа
  прежнего CPU-стенда ещё перекрывает экран; кольцо не уменьшалось.
  Видео+AY **2083130 байт**, недостача до предварительных трёх TRD
  **145466**, новые служебные байты ещё не размещены. PLAYER/TRD прежние.
- **Материалы:** [формулы, границы и команды](toolkit/COMPACT_SCREEN_Z80_ru.md),
  [генератор](toolkit/compact_screen_z80.py), [CPU](toolkit/compact_screen_cpu.json),
  [сводка](toolkit/compact_screen_summary.json),
  [признаки n−2](toolkit/native_dirty_tiles.json).

## 2026-09-19 — выбор FSF1 с ценой кэша: ещё −14844 байта

- **Цель/база:** `1659579`, все 4971 кадр age3. Сохранить пиксели,
  атрибуты, разрешение и AY; выбирать готовые фрагменты с учётом
  возможности полностью отключить кэш движения в кадре.
- **Параметры:** для каждого кадра конкурируют обычный выбор и замена
  всех временных векторов 1..80. Оценочный лимит 300000 T. Стоимость
  кэша измерена на одинаковом нулевом кадре: **59231→119629 T**,
  разница **60398** (58792 копирование +1606 управление).
- **Выбор/объём:** второй вариант выиграл 165 кадров. Готовых фрагментов
  **55846→51248**, кадров с кэшем **4807→4648** относительно прежнего
  FSF1. Байты до ZX0 **3022350→2980664** (−41686); actual optimal ZX0
  с заголовками **2020278→2005434** (−14844), 364 блока вместо 369.
  С AY **2083130**; недостача до предварительных трёх TRD **145466**.
- **Проверка данных:** независимый причинный PC-декодер восстановил все
  кадры и промежуточный FHF1 байт в байт. Все блоки проверены PC и Z80;
  ZX0 **149421805 T** (−6128705), максимум блока **718426**.
  Один тест выбора проверяет конкурирующие варианты с разной ценой
  байтов/CPU и кадр без движения. Повторное кодирование совпало по SHA.
- **Полностью Z80:** 4971 кадр /640 групп, реконструкция **1128276523 T**
  (+3540180), максимум **309686** (+6958), худший кадр 4582. Две стадии
  вместе **1277698328 T** (−2588525). Кадров >425448 — 0, но **465**
  выше оценочного порога 300000; максимум выше него на 9686 T.
  Проверены гистограмма инструкций, 1083493 значения Хаффмана, режимы
  фрагментов и побайтное совпадение кода/таблиц с прежним FSF1.
- **Границы:** машинный код и карта CPU-стенда прежние, дельта инструкций
  **0 T**. Меняется частота ветвей. Максимум входа группы с двумя
  защитными нулями — 9069 байт. Размещение входа всё ещё перекрывает
  экран/TR-DOS; метаданные, окна, вывод, paging, IRQ/ULA/ROM и диск
  не включены в CPU-суммы. Кольцо чтения не уменьшалось, TRD прежние.
- **Решение:** сохранить более компактный исследовательский кандидат:
  две стадии суммарно быстрее, хотя максимум реконструкции вырос.
  Далее измерить развёртку в два экрана и полный путь доставки;
  оценка 300000 T и размер отдельно не доказывают плавные 25/3 кадра/с.
- **Материалы:** [отчёт и команды](toolkit/CACHE_AWARE_FRAGMENTS_ru.md),
  [скрипт](toolkit/probe_cache_aware_fragments.py),
  [выбор](toolkit/cache_aware_fragments.json),
  [ZX0](toolkit/cache_aware_fragments_zx0.json),
  [сводка CPU/размера](toolkit/cache_aware_fragments_summary.json).

## 2026-09-19 — FSF1: отдельный канал фрагментов, −23529 байт и −4978358 T

- **Цель/база:** `6c5c818`, FHF1 после перевыбора быстрых плиток,
  полный age3, 4971 кадр. Разделить готовые байты и биты Хаффмана,
  сохранив все пиксели, режимы, маски, таблицы, группы и AY.
- **Формат:** внутри прежней группы Хаффман идёт перед фрагментами;
  длина фрагментов выводится из векторов. Удалено 69918 бит выравнивания.
  Независимый причинный декодер восстановил все экраны и исходный FHF1
  байт в байт. Исходные байты **3031081→3022350** (−8731).
- **Фактический ZX0:** все 369 блоков, **2043807→2020278 байт** с
  заголовками (−23529). С AY **2097974**, недостача до предварительного
  бюджета трёх TRD **160310**; раскладка новых томов не включена.
- **Горячий путь:** отдельный указатель убирает выравнивание и перенос
  IX. Тела 85/86/88 **546/541/513→492/487/459 T**, режим 87
  **898−10p→844−10p T**. Разница **−54−10u T**, u — прежнее
  невыровненное чтение. Формулы проверены на всех 55846 фрагментах.
- **Полностью Z80:** реконструкция **1124736343 T** (−3103551),
  максимум **302728** (−5907), 0 кадров >425448. Фрагменты −3189544 T,
  Хаффман +85993 T из-за битовых позиций; остальные стадии идентичны.
  ZX0 **155550510 T** (−1874807), две стадии **1280286853 T** (−4978358).
  Проверены 4971 кадр/641 группа, 1038625 значений и все ZX0-блоки.
- **RAM/проверки:** код **3893→3881**, состояние **23→25** байт.
  Три новых и десять прежних тестов, включая каждую границу AY IRQ;
  выключенная опция даёт прежний бинарник. Два входных участка пока
  непрерывны в CPU-стенде и перекрывают экран/TR-DOS. Парсер метаданных,
  окна, вывод, paging, IRQ/ULA/ROM и диск не входят в CPU-суммы.
- **Решение:** новая исследовательская база — одновременно меньше и
  быстрее. Три готовых TRD и плавность полного пути не заявляются.
  Следующий выбор учитывает стоимость кэша на весь кадр; далее нужна
  реальная карта 128 КиБ и проверка доставки/вывода в Fuse.
- **Материалы:** [формат/такты/команды](toolkit/FRAGMENT_CHANNELS_ru.md),
  [скрипт](toolkit/probe_fragment_channels.py),
  [сводка](toolkit/fragment_channels_summary.json),
  [CPU](toolkit/fragment_channels_cpu.json).

## 2026-09-19 — переобучение оставшихся поправок: −3258 байт, но +6048333 T

- **Цель/база:** опыт начат 18 сентября; FHF1 из `6c5c818` и FHC1,
  все 4971 кадр age3. Исключить готовые фрагменты из обучения Хаффмана;
  геометрия, пиксели, атрибуты, выбранные режимы и AY прежние.
- **Параметры:** прежнее распределение контекстов и новая кластеризация
  в 16 групп, отдельные атрибуты; optimal ZX0 v2, блоки 8192 байта.
- **Размеры:** FHF1 fixed/clustered16 **2040815/2040549** байт с заголовками
  (−2992/−3258 к 2043807); FHC1 **2046844/2046168** (−4600/−5276
  к 2051444), оба всё ещё больше базового FHF1. Все четыре PC-потока
  восстановили 4971 кадр, все **1471** ZX0-блоков проверены.
- **CPU лучшего FHF1:** все кадры **1133996268 T** (+6156374), максимум
  **319497** (+10862), 0 кадров >425448; 370 блоков ZX0 **157317276 T**
  (−108041). Две стадии **1291313544 T**, разница **+6048333**.
  Длинных кодов стало 72642 вместо 59056. Другие стадии, кроме
  Хаффмана/выравнивания, совпали на каждом кадре. Для трёх остальных
  вариантов CPU не заявляется. Бинарный код всех вариантов прежний.
- **RAM/решение:** лучший набор таблиц со сдвигами занимает 15830 байт
  вместо 16208; кольцо диска прежнее. Не заменять базу: выигрыш места
  мал, CPU вырос. С AY 2118245 байт, не хватает 180581 до предварительных
  трёх TRD. Вывод/окно/метаданные/paging/IRQ/ULA/ROM/диск не измерены;
  PLAYER/TRD прежние. Следующая проверка — отдельный канал фрагментов.
- **Материалы:** [отчёт/команды](toolkit/RETUNED_FRAGMENT_CONTEXTS_ru.md),
  [скрипт](toolkit/retune_fragment_contexts.py),
  [полная сводка](toolkit/retuned_fragment_contexts_summary.json),
  [CPU](toolkit/retuned_contexts_fhf_clustered16_cpu.json).

## 2026-09-19 — FHC1: прямые пространственные поправки быстрее на плитке, но поток больше

- **Цель/база:** опыт начат 18 сентября от `eea5d62`; полный age3,
  4971 кадр. Не вычислять предсказание для непосредственно переданного
  байта. Пиксели, разрешение, атрибуты и AY не менялись.
- **Изменение:** FHC1 разрешает старший бит у предикторов 82..84,
  передаёт только отмеченные байты без Хаффмана. Выбор конкурирует
  с целыми FHF1-фрагментами при оценочном лимите 300000 T/кадр.
- **Такты:** тело прямой плитки `693+d+39n+ΣR(неотмеченных)+10u`,
  прежнее `629+d+25n+ΣR(всех)+H`. Формулы и допущения в отчёте.
  Проверенный пример 16 поправок: **4301→1351 T**, с диспетчером
  **4362→1403 T** (−2959). Сохранённые intra/fast получают +18/+28 T,
  временные плитки +0 T; код **3893→5086 байт**, состояние прежние 23.
- **Полный размер:** 19718 прямых плиток, 133420 байтов, целых плиток
  55846→44857. Исходный поток **3031081→2994638**, но actual optimal
  ZX0 8192 с заголовками **2043807→2051444** (+7637). С AY 2129140,
  до предварительных трёх TRD не хватает 191476 байт.
- **Полностью Z80:** реконструкция **1128357323 T** (+517429),
  максимум **308528** (−107), 0 кадров >425448. Все 366 блоков ZX0:
  **154979731 T** (−2445586). Две стадии **1283337054 T** (−1928157).
  Меньшее время CPU не компенсирует автоматически рост секторного потока;
  вывод/окно/метаданные/paging/IRQ/ULA/ROM/диск здесь не измерены.
- **Прерванная попытка:** 19 сентября процесс первого CPU-прогона
  отсутствовал; файл сохранил 3605 кадров/451 группу, 795251303 T,
  максимум 301770. Повторный полный прогон совпал с этим префиксом.
  Добавлены совместимые контрольные точки с кадром/гистограммой;
  продолжение 608→616 проверено против непрерывного исполнения.
- **Проверки:** 4971 кадр на PC и Z80, 366 блоков, точные формулы;
  пять новых и 16 прежних тестов, включая AY после каждой инструкции.
  Выключенная опция сохраняет прежние бинарные варианты.
- **Решение:** сохранить эксперимент, не принимать текущий выбор как
  улучшение упаковки. PLAYER/TRD прежние; проверяется переобучение таблиц
  и организация готовых фрагментов. Достижение трёх TRD не заявляется.
- **Материалы:** [описание и команды](toolkit/RAW_INTRA_ru.md),
  [сводка](toolkit/raw_intra_summary.json), [код выбора](toolkit/probe_raw_intra.py),
  [CPU](toolkit/raw_intra_cpu.json), [проверка продолжения](toolkit/raw_intra_checkpoint_check.json).

## 2026-09-18 — завершена CPU-проверка перевыбора fast-плиток

- **Цель/база:** закрыть незавершённый полный прогон из `eea5d62`;
  4971 кадр age3, FHF1 `target_300000` после развёртывания движения.
  Настройки, пиксели, атрибуты, AY и поток больше не менялись.
- **Измерено:** реконструкция **1127839894 T**, максимум **308635**,
  худший кадр 4588; кадров >425448 — 0. Относительно прежнего
  FHF1 с тем же ускоренным движением: **+11949539 T**, максимум +5803.
  Все 371 блока Z80 turbo ZX0: **157425317 T**, максимум блока 690282;
  разница −4729574. Сумма стадий **1285265211 T**, разница **+7219965**.
- **Покрытие:** все 4971 кадр и 641 группа, 1038625 значений Хаффмана,
  55846 fast-плиток; все 3031081 исходных байтов ZX0. Сводка проверяет
  SHA, полный охват, формулы стадий и сумму гистограммы инструкций.
  Никаких новых тактов горячего пути: код и вход этого опыта неизменны.
- **Размер/решение:** ранее измеренные **2043807 байт** ZX0 с заголовками
  (−22919), с AY 2121503; недостача до предварительных трёх TRD 183839.
  Сохранить как проверенную CPU-базу для следующего опыта. Сумма CPU
  немного выросла; выигрыш общей доставки ещё не доказан. Вывод, окно,
  метаданные, paging, IRQ/ULA/ROM/диск исключены. PLAYER/TRD прежние.
- **Материалы:** [результаты и команды](toolkit/UNROLLED_MOTION_ru.md),
  [сводка](toolkit/unrolled_motion_summary.json),
  [скрипт](toolkit/summarize_unrolled_motion.py),
  [кадры Z80](toolkit/unrolled_fast_cpu.json),
  [блоки ZX0 Z80](toolkit/unrolled_fast_zx0_cpu.json).

## 2026-09-18 — развёрнутое движение: −42563542/−30051325 T без новых байтов видео

- **Цель/база:** сократить CPU предсказаний перед новым выбором быстрых
  плиток; `d17f2ab`, полный лучший FHS1 и прежний FHF1 `target_300000`,
  по 4971 кадру age3. Потоки, пиксели, атрибуты и AY неизменны.
- **Изменение:** восемь строк без DJNZ; выходной указатель DE′ снимает
  стековые сохранения на каждой строке, C′/IX сохраняют вход Хаффмана.
  Фазы 2/6 используют вращения/маску, фаза 4 — прежние таблицы.
  Удалён ненужный последний переход строки; нулевой вектор развёрнут.
- **Такты плитки:** фазы 0/2/4/6 — **995/2076/2093/2103 →
  826/1616/1713/1643 +21q T**, q=1 при dy не кратном четырём;
  нулевой вектор **445→324 T**. Формулы по таблице инструкций Zilog.
- **Полностью на Z80:** FHS1 **1344619738→1302056196 T** (−42563542),
  максимум 842114→834816, кадров >425448: 583→524. FHF1
  **1145941680→1115890355 T** (−30051325), максимум 307645→302832,
  кадров >425448 по-прежнему 0. Разница каждого кадра ровно равна
  разнице стадии движения; все другие стадии и входы ZX0 совпали.
  Восстановление+прежний ZX0: **1404235760/1278045246 T**.
- **Перевыбор плиток:** по новым CPU-временам быстрых плиток 61225→55846,
  исходных байтов 3076050→3031081. Все 4971 кадр проверены на PC,
  все 371 блок optimal ZX0 проверены: **2066726→2043807 байт** (−22919).
  С AY 2121503, не хватает 183839 до предварительного бюджета трёх TRD.
  Полный CPU-прогон этого нового потока ещё не включён в сводку;
  скорость выбора остаётся оценкой, отдельная проверка запущена.
- **RAM/код:** +1106 байт, FHS1 3423 / FHF1 3893, состояние 23.
  Кадр, кэш, таблицы и кольцо диска не выросли. Рост кода в выпускных
  томах ещё не размещён. Выключенная опция сохраняет прежние бинарники.
- **Проверки:** все 9942 кадра двух серий, все формулы и инструкции;
  три новых теста всех векторов/границ/RLCA/RRCA/AY IRQ и 35 прежних.
  С двумя тестами отдельного словарного опыта — 40 уникальных тестов.
  Вывод/окно/метаданные/paging/IRQ/ULA/ROM/диск не измерены в CPU-суммах.
- **Решение:** сохранить ускорение; оно не делает выпуск готовым.
  Компактный поток ещё медленный, быстрый ещё велик для трёх TRD.
  Следующий шаг — завершить CPU-проверку нового выбора, затем
  проверить объединение предсказания с прямыми поправками, пропуская
  вычисления заменяемых байтов. PLAYER/TRD пока прежние.
- **Материалы:** [изменения, формулы и команды](toolkit/UNROLLED_MOTION_ru.md),
  [сводка](toolkit/unrolled_motion_summary.json),
  [скрипт проверки](toolkit/summarize_unrolled_motion.py).

## 2026-09-18 — словарь строк FHD1: уменьшил исходные данные, ухудшил ZX0

- **Цель/база:** сократить быстрый поток FHF1 `target_300000` до трёх
  TRD; `d17f2ab`, все 4971 кадр age3. Выбор fast-плиток, пиксели,
  атрибуты и AY неизменны.
- **Параметры:** словарь 255/1023/2047/4095 двухбайтовых строк,
  индексы 8/10/11/12 бит, escape и локальный выбор только при payload
  короче 16 байт. Словарь полностью включён в новый FHD1. Для 9 бит
  посчитан только предварительный профиль, полного ZX0 нет.
- **Полные результаты:** исходные 3076050 байт уменьшились до
  2973055/2954553/2949106/2956536. Но optimal ZX0 8192 +заголовки:
  **2079841/2083967/2091288/2085573**, то есть **+13115/+17241/
  +24562/+18847** к FHF1. Лучший из этих вариантов с AY 2157537,
  на 219873 больше предварительного бюджета трёх TRD.
- **Проверки:** все четыре потока независимо восстановили 4971 кадр
  на PC; все **1445 блока ZX0** распакованы и проверены. Два новых
  теста всех ширин/escape/причинных соседей/повреждений; 35 прежних
  регрессионных тестов прошли в рабочем дереве. Новый Z80-режим не
  реализован, CPU/RAM/paging/диск не измерялись; горячий путь 0 T.
- **Решение:** отклонить эти варианты для выпуска, сохранить скрипты
  и полные отчёты. Уменьшать дисковый буфер ради этого словаря нет
  оснований. PLAYER/TRD прежние. Сокращение до ZX0 не даёт основания
  считать поток более компактным после него.
- **Материалы:** [формат, результаты и команды](toolkit/FRAGMENT_DICTIONARY_ru.md),
  [сводка](toolkit/fragment_dictionary_summary.json),
  [кодировщик](toolkit/probe_fragment_dictionary.py),
  [скрипт проверки](toolkit/summarize_fragment_dictionary.py).

## 2026-09-18 — быстрые фрагменты: максимум кадра 307645 T, но +217850 байт видео

- **Цель/база:** ускорить тяжёлые сцены лучшего FHS1 без новых изменений
  изображения; `15b5638`, весь кандидат age3, 4971 кадр. Разрешение,
  четыре двухбитных значения, атрибуты и AY 50 Гц прежние.
- **Параметры:** FHF1 добавляет сырую плитку 16 байт, повтор строки,
  выбор из двух строк и заливку байтом. Четыре глобальных допуска
  0/16/32/64 добавочных бит и два выбора только для тяжёлых кадров
  с целями 300000/250000 T; таблицы Хаффмана не переобучаются.
  Контроль и шесть вариантов полностью восстановлены на PC.
- **ZX0 полностью:** optimal v2, блок 8192 +4 байта заголовка;
  допуски 16/64 — **1864355/2017307** байт, к FHS1 +15479/+168431.
  Цель 300000 — **2066726** (+217850); с AY 2144422, на 206758 больше
  предварительного бюджета трёх TRD. Проверены 1054 новых блока PC.
  Для остальных вариантов есть только исходный размер/DEFLATE-отбор,
  они не выдаются за измерение ZX0.
- **Z80 полностью, цель 300000:** 4971 кадр/643 группы/1018254 значения/
  11836577 бит совпали. Восстановление **1344619738→1145941680 T**
  (−198678058), максимум **842114→307645 T**; кадров >425448: 583→0.
  Все 376 блоков ZX0: **102179564→162154891 T** (+59975327).
  Обе стадии **1446799302→1308096571 T**, экономия **138702731 T**.
  Худшее окно 200 кадров в среднем 722141,805→304886,93 T.
- **Машинные изменения:** код 2317→2787 (+470), состояние 23 байта;
  память кадра/кэша/таблиц прежняя. Тела быстрых режимов
  546/541/[818+10×(8−popcount)]/513 T, +10 T при выравнивании.
  Диспетчеризация сохранившихся intra +27 T/плитку; временные пути
  прежние. В выключенном режиме прежний код/метки/листинг/таблицы
  побайтно совпали. Точные формулы проверены на всех быстрых плитках.
- **Проверки:** 35 тестов, включая AY IRQ после каждой инструкции
  смешанных кадров и AF′-селектор. Полный CPU не включает вывод,
  метаданные, окно ввода, paging, IRQ/ULA/ROM/диск; плавность всего
  плеера ещё не доказана. Для иных вариантов CPU пока оценочный.
- **Дополнительный профиль:** словарь 255 двухбайтовых строк дал
  103434 байта потенциальной экономии payload (102924 после словаря),
  до метаданных/выравнивания/ZX0; машинного режима и замера ZX0 нет.
- **Решение:** сохранить проверенные быстрые режимы для дальнейшей
  оптимизации, отклонить этот поток как выпуск на трёх TRD из-за размера.
  Дисковое кольцо не уменьшалось, выпускные PLAYER/TRD не заменены.
- **Материалы:** [такты, результаты и команды](toolkit/FAST_FRAGMENTS_ru.md),
  [сводка](toolkit/fast_fragments_summary.json),
  [кодировщик](toolkit/probe_fast_fragments.py),
  [профиль словаря](toolkit/fast_fragment_words_profile.json),
  [скрипт профиля](toolkit/profile_fragment_words.py).

## 2026-09-18 — четырёхбитные хвосты Хаффмана: полные таблицы не входят в банк

- **Цель/база:** ускорить длинные коды без новых байтов видео; `15b5638`,
  лучший FHS1, все 4971 кадр age3. Поток/пиксели/атрибуты/AY не менялись.
- **Параметры:** точные канонические деревья 17 контекстов, узлы по
  четыре бита, объединение одинаковых поддеревьев; отдельно ограниченный
  набор первых узлов для листьев 9..12 бит с прежним fallback.
- **Измерено:** 137055 длинных значений, 292272 однобитных шага против
  145190 четырёхбитных обращений (не тактов). 736 узлов по 32 байта:
  корни+узлы+сдвиги **36352 байта**, ещё без адресных таблиц 1472 байта.
  Размер предполагает дополнительную упаковку старших битов ID узлов.
  Частичные наборы 512/1024/2048/4096 байт охватывают
  11798/21553/37657/64564 значения, без цены перенаправления и адресации.
- **Проверки:** все длинные коды и хвостовое дополнение независимо
  пройдены по таблицам; частоты полного фильма сверены с CPU-базой.
  Машинная реализация/такты/доставка с диска не проверялись. Изменение
  горячего пути 0 T, выпускные PLAYER/TRD прежние.
- **Решение:** не переносить полные таблицы в существующий 16-КиБ банк;
  частичный вариант оставить для отдельного расчёта RAM и тактов.
  Уменьшение дискового буфера не принималось.
- **Материалы:** [описание и команда](toolkit/HUFFMAN_TAIL_PROFILE_ru.md),
  [скрипт](toolkit/profile_huffman_tail_tables.py),
  [профиль](toolkit/huffman_tail_tables_profile.json).

## 2026-09-18 — ZX0 16 КиБ: −5062 байта, +1175947 T

- **Цель/база:** поиск запаса места для быстрых режимов плотных сцен;
  лучший полный FHS1 из `7dea054`, чей Z80-прогон сохранён в `a86f9ae`.
  Весь фильм 4971 кадр; пиксели, атрибуты и звук неизменны.
- **Параметры:** optimal ZX0 v2, блок 8192→16384 байта, прежний
  turbo-декодер 126 байт. Новый CPU-стенд выводит в банк 0 C000–FFFF;
  он не является картой интегрированного плеера.
- **Измерено полностью:** 323→162 блока, **1848876→1843814 байт**
  видео с заголовками (−5062, около 0,274%). Видео+AY — 1921510,
  предварительный запас трёх TRD 16154 байта. Плотная упаковка
  цельного видео 7223→7203 сектора, не раскладка готовых томов.
  ZX0 CPU **102179564→103355511 T** (+1175947); максимум блока
  548379→899126 T. Код декодера совпадает; изменение реализации 0 T.
- **Проверки:** все новые блоки независимо восстановлены на PC и Z80,
  сводка проверяет SHA/покрытие/суммы обеих полных серий. Вывод/IRQ/ULA,
  переключения банков, ROM и физическая доставка с диска не измерены.
- **Решение:** сохранить резервным опытом. Ради малого выигрыша и
  более дорогой распаковки меньший дисковый буфер пока не принимается;
  16-КиБ история требует новой раскладки RAM. Основное ограничение —
  тяжёлые кадры — этот опыт не снимает. Выпускные PLAYER/TRD прежние.
- **Материалы:** [результаты и команды](toolkit/SPATIAL_ZX0_16K_ru.md),
  [сводка](toolkit/spatial_extended_block_sizes.json),
  [проверяющий скрипт](toolkit/compare_zx0_block_sizes.py).

## 2026-09-18 — лучший FHS1 полностью восстановлен тремя предсказаниями Z80

- **Цель/база:** перенести лучший пространственный поток на Z80;
  `7dea054`, все 4971 кадр age3. Неизменённый FHS1 первого прохода
  трёх предсказаний, 1848876 байт после ZX0 8192 +заголовки.
  Новых потерь пикселей/атрибутов/AY нет.
- **Изменение:** к верхнему предсказанию добавлены левое и через строку,
  с причинным применением поправок. Второй байт левой пары уже находится
  в A. Код 1639→2317 байт (+678), состояние 23. Память кадра/кэша/таблиц
  не выросла, дисковое кольцо не уменьшалось. IRQ-стенд перенесён в 9200h.
- **CPU полностью:** все кадры, 622 группы, 1473262 значения,
  7461276 бит совпали. Восстановление **1344619738 T**, к верхнему
  варианту **−14159325 T**; максимум **842114 T** вместо 861629.
  ZX0 всех 323 блоков **102179564 T**, −1191608. Две стадии вместе
  **1446799302 T**, −15350933 к верхнему варианту и −91833769 к FHT1 age3.
  Формулы intra, инструкция/такты, гистограммы, память и указатели сверены.
- **Проверки:** 30 тестов (6 пространственных +24 регрессионных),
  AY IRQ после каждой инструкции новых направлений. Старый верхний
  код/метки/листинг/таблицы совпали побайтно. Просмотрены 15 кадров
  сцен 3683–3687, 4583–4587, 4650–4654: отличия от эталона точечные,
  плотная структура присутствует и в эталоне. Полный просмотр движения
  по-прежнему не выполнен; все новые декодированные пиксели точны к age3.
- **Решение:** принять машинные предсказания для дальнейшей работы,
  не объявлять выпуск. 583 кадра дороже 425448 T; 200 кадров с №4481
  в среднем **722141,805 T** без экрана/окна/метаданных/IRQ/ULA/ROM/диска.
  Идеальная очередь 152 кадра требует 583680 байт и не помещается в 128K.
  Следующий шаг — быстрые режимы целых фрагментов для плотных сцен
  с учётом цены хранения. Выпускные PLAYER/TRD прежние.
- **Материалы:** [результаты и точные такты](toolkit/SPATIAL_EXTENDED_Z80_ru.md),
  [CPU-сводка](toolkit/spatial_extended_summary.json),
  [проверяющий скрипт](toolkit/summarize_spatial_extended.py),
  [сцены](toolkit/spatial_extended_scenes.png),
  [скрипт просмотра](toolkit/render_cpu_scenes.py).

## 2026-09-18 — проверка четырёх уровней: формат уже двухбитный

- **Цель/база:** проверить предложение ограничить видео четырьмя
  градациями; `ec7f240`, полный исходный Spectrum-поток и кандидат age3,
  по 4971 кадру. Разрешение/частоты/звук не менялись.
- **Проверка:** прочитаны упаковка конвертера и таблицы плеера;
  сохранён скрипт аудита фактических кодов и палитры обеих версий.
  Посчитаны все пиксели полного кадра и активной области, атрибуты
  и используемые аппаратные цвета. SHA совпали с исходными отчётами.
- **Результат:** уже 2 бита/логический пиксель и четыре покрытия INK
  **0/25/50/100%**; все четыре кода используются. До сжатия — 3072
  байта рисунка +768 атрибутов. По фильму 49 байтов атрибутов и 14
  аппаратных цветов в обеих версиях: это не глобальная серая палитра.
- **Решение:** сохранить существующее представление. Повторное сведение
  к тем же четырём значениям не даёт экономии; новые уровни потерь
  не вводились. PLAYER/TRD не изменены, горячий путь **0 T** разницы.
  Новый размер ZX0 и скорость в этом аудите не измерялись.
- **Материалы:** [объяснение и команда](toolkit/VIDEO_LEVELS_ru.md),
  [скрипт](toolkit/audit_video_levels.py), [отчёт](toolkit/video_levels_audit.json).

## 2026-09-18 — пространственные предсказания: −139277 байт, CPU ещё медленный

- **Цель/база:** приблизить весь фильм к трём TRD; `e7727cd`, 4971 кадр
  кандидата age3. Разрешение, 25/3 fps, атрибуты и AY 50 Гц сохранены.
  Все новые потоки побайтно восстанавливают этот кандидат, новых потерь нет.
- **Параметры:** восемь моделей контекста ×16/32/64 групп; затем FHS1
  с предсказанием текущей плитки сверху, слева, через строку. Выбор на PC
  по байтовой цене или длинам Хаффмана, две итерации переобучения.
  optimal ZX0 v2, блоки 8192 байта +4 байта заголовка.
- **Хранение полностью:** девять потоков независимо восстановили все
  кадры; проверены **2934 блока ZX0**. Лучший — три предсказания,
  битовая цена, итерация 1: **1988153→1848876 байт**, −139277 (7,0053%).
  С прежним AY 77696 получается **1926572**, запас **11092 байта**
  до ориентира 1937664. В нём уже вычтены прежние boot/PLAYER;
  рост нового кода, загрузка таблиц и фактическое разделение томов
  ещё не размещены. Итерация 2 оказалась на 354 байта хуже и отклонена.
- **CPU полностью, другой вариант:** верхнее предсказание с байтовой
  ценой (1866890 байт), оба прогона на тех же age3-кадрах. Восстановление
  **1428953317→1358779063 T**, −70174254; максимум 1008630→861629 T.
  ZX0 всех 340/325 блоков: 109679754→103371172 T, −6308582.
  Две стадии вместе −76482836 T. Код 1388→1639 байт, состояние 23.
  Intra-плитка 1057/1099 +25×поправки T; расчёт по таблице Zilog,
  формулы, листинг и гистограммы проверены на полном фильме.
- **Проверки:** пять новых +29 прежних тестов. Первое испытание IRQ
  исчерпало синтетические 65535 тиков; стенд исправлен с учётом
  переполнения, повторные проверки прошли. AY-драйвер не менялся.
  Неудачные модели и размеры всех вариантов сохранены в отчётах.
- **Решение/границы:** это эксперимент, не выпуск. Z80 поддерживает
  только предсказание сверху; лучший по объёму вариант 83/84 ещё не
  исполнялся на Z80. 599 кадров дороже номинальных 425448 T уже без
  экрана/окна/метаданных/IRQ/ULA/ROM/диска. Идеальная очередь 165
  полных кадров требует 633600 байт и не решает задачу на 128 КиБ.
  Дальше — ускорение тяжёлых сцен и интеграция всего пути доставки.
  Выпускные PLAYER/TRD не менялись; плавные 8⅓ fps ещё не доказаны.
- **Материалы:** [результаты, такты и команды](toolkit/SPATIAL_TILES_RESULTS_ru.md),
  [сводка](toolkit/spatial_tiles_summary.json),
  [кодировщик](toolkit/probe_spatial_contexts.py),
  [подбор предсказаний](toolkit/optimize_spatial_tiles.py),
  [Z80-проверка](toolkit/benchmark_spatial_tiles.py).

## 2026-09-18 — ошибка до трёх кадров: −44887 байт, пока кандидат

- **Цель/база:** уменьшить данные при прежних четырёх покрытиях INK
  0/25/50/100%, разрешении и 25/3 fps; `2de2203`, весь фильм 4971 кадр.
  Четыре уровня уже хранятся в двух битах, цветовые атрибуты отдельно.
- **Параметры:** длительность допустимой ошибки ячейки 1→3 кадра
  (до 0,36 с); прежние ≤2 логических пикселей/ячейку, ≤1 четверти
  покрытия, RMSE≤24, ≤128 пикселей/кадр, точные атрибуты и AY.
  Контроль ошибки относительно исходника каждого кадра. Переобучены
  длины FHT1 на прежней карте 16 контекстов; контроль age1 воспроизведён
  побайтно тем же новым скриптом, включая все таблицы/группы.
- **Хранение полностью:** FHT1 2823159→2784318 байт; настоящий
  optimal ZX0 8192 +заголовки **2033040→1988153**, экономия **44887**.
  С прежней оценкой AY 77696 не хватает **128185 байт** до трёх TRD
  ещё без кода/томов. Все 340 ZX0-блоков независимо проверены.
- **Качество полностью:** средний/минимальный SSIM
  0,991185/0,966887→**0,988480/0,965053**. Средняя доля изменённых
  RGB-пикселей 0,204015→0,281715%, максимум прежний 0,347222%.
  Максимальная ошибка пикселя/ячейки держится три кадра; новых
  повторённых кадров нет. SSIM не является процентом точности.
- **Проверки:** все кадры восстановлены из FMR1/FHT1 и сравнены
  с эталоном; сохранён покадровый отчёт. Просмотрен контактный лист
  трёх сложных пятикадровых сцен (60–64, 3836–3840, 4114–4118):
  отдельные изменённые точки, структура сохранена. Полный просмотр
  движения не выполнен. Шесть тестов bounded motion прошли, включая
  новое принудительное восстановление после трёх неточных кадров.
- **Решение:** оставить кандидатом для следующего сочетания методов;
  базу/выпуск не заменять без проверки движения и полного плеера.
  Изображение несколько менее точное, а трёх дискет ещё нет. Таблицы
  помещаются в прежние области RAM; полный CPU/экран/IRQ/ULA/ROM/диск
  нового потока не измерены. PLAYER/TRD прежние, изменение реализации
  горячего пути 0 T; плавные 8⅓ fps этим замером не доказаны.
- **Материалы:** [результаты и команды](toolkit/BOUNDED_MOTION_AGE3_RESULTS_ru.md),
  [кодировщик кандидатов](toolkit/encode_motion_candidate.py),
  [качество каждого кадра](toolkit/bounded_motion_age3_quality.json),
  [ZX0](toolkit/bounded_motion_age3_fht_zx0.json),
  [просмотренные сцены](toolkit/bounded_motion_age3_filmstrip.png).

## 2026-09-18 — байтовые поправки: быстрее CPU, больше секторов

- **Цель/база:** ускорить FHT1 после `2de2203`, все 4971 кадр прежнего
  кандидата без новых изменений пикселей/атрибутов/движения/AY.
- **Параметры:** FHR1, старший бит вектора выбирает выровненные байтовые
  поправки только по маске. Прямые значения с порогами control/64/32/0,
  XOR и частотный алфавит с порогом 0. Остальное — прежний Хаффман.
- **Размер:** optimal ZX0 8192 +заголовки для direct control/64/0,
  XOR0/frequency0 — **2033037/2074002/2387738/2444805/2402284** байта.
  Для direct32 только DEFLATE 2135709, ZX0 не измерен. Все шесть
  потоков полностью восстановлены причинно; все **1948 блоков ZX0**
  пяти вариантов независимо проверены. Крупный DEFLATE — только оценка.
- **CPU полностью:** direct0 — **1120565238 T** восстановления против
  1452380532 у FHT1 (−331815294), максимум 529778 вместо 1012577 T.
  Все 4971 кадр побайтно проверены Z80; формулы/стадии/гистограмма совпали.
  ZX0 для всех 417 блоков: **228128695 T**, +117581397 к базе.
  Две стадии вместе −214233897 T (13,7072%), но +354698 байт /1386
  секторов при округлении цельных потоков. Код 1406→1531, состояние 23.
- **Проверки/ограничения:** 4 новых +25 прежних тестов, включая AY IRQ
  после каждой инструкции смешанных direct/XOR кадров; старый FHT1
  код/метки/листинг совпали. Для других режимов полный CPU только
  по формулам. Экран, окно, метаданные, paging, IRQ/ULA/ROM/диск исключены.
- **Решение:** сохранить как эксперимент, в выпуск не включать: объём
  мешает трём TRD, а 134 кадра ещё дороже 425448 T до остальных стадий.
  Оптимистичные 2 готовых кадра при полном бюджете превращаются в
  41 при 350000 T (157440 байт). Меньший дисковый буфер не принят.
  PLAYER/TRD прежние, интегрированная разница горячего пути 0 T.
- **Материалы:** [результаты/формулы/команды](toolkit/RAW_PATCHES_RESULTS_ru.md),
  [кодек](toolkit/probe_raw_patches.py),
  [полный CPU](toolkit/raw_patches_direct_0_cpu.json),
  [сводка](toolkit/raw_patches_summary.json).

## 2026-09-18 — словарь масок: увеличение потока, не внедрено

- **Цель/база:** сократить метаданные FHT1 `control`, база `a007c09`,
  полный фильм 4971 кадр / 954432 плитки. Пиксели, векторы, кодовые
  значения, группы и AY остаются прежними.
- **Параметры:** FHD1 заменяет разреженные 16-битные маски рисунка
  индексами 16/64/128/255 самых частых шаблонов; FF +полная маска
  для отсутствующих, атрибуты отдельно прежним разреженным методом.
- **Измерения:** DEFLATE 8192 — 2226297/2192129/2171688/2146422 байта.
  Настоящий optimal ZX0 8192 с заголовками измерен для 16 и 255:
  **2164389 / 2109069 байт**, хуже FHT1 (2033040) на **131349 / 76029**.
  Для 64/128 отдельного ZX0 нет. Даже 255 шаблонов оставляют 176467
  полных масок; дефицит лучшего измеренного варианта с прежним AY
  до бюджета трёх TRD — 249101 байт до дополнительных расходов.
- **Проверки:** четыре полных побайтных обратных преобразования в FHT1,
  все 857 ZX0-блоков независимо проверены; один новый тест словаря,
  полного пути, ошибочных индексов/словарей и границ потока прошёл.
  Кадры сохраняют прежний хеш, новых изменений качества нет.
- **Решение:** отклонить этот формат масок по размеру. Не реализовывать
  дополнительный Z80-путь ради такого результата. Его CPU, RAM и
  секторная подача не измерены; PLAYER/TRD прежние, разница горячего
  пути 0 T. Это не общий вывод о любых словарях изображения.
- **Материалы:** [результаты и команды](toolkit/MASK_DICTIONARY_RESULTS_ru.md),
  [скрипт](toolkit/probe_mask_dictionary.py),
  [проверенные размеры](toolkit/mask_dictionary_measurements.json).

## 2026-09-18 — отдельные атрибуты и готовые плитки: ускорение с ценой в байтах

- **Цель/база:** ускорить тяжёлые сцены после `608e57b`; FPD1 direct/16,
  все 4971 кадр. Уточнено: четыре покрытия INK 0/25/50/100% уже занимают
  два бита; нового сокращения градаций/разрешения/кадров/AY нет.
- **Изменение:** FHT1 переносит маски/значения атрибутов в растровый
  проход. Флаг кадра пропускает ненужный кэш. Маркер 82 читает готовую
  16-байтовую плитку из выровненного входа; группы ≤8 кадров / 9215 байт.
  Проверены контроль, пороги 128/96/64 бит и все изменившиеся плитки.
- **Хранение полностью:** optimal ZX0 8192 с заголовками — 2033040,
  2032956, 2036138, 2095319, 3063242 байта. База 2034286. Контроль
  экономит 1246, порог 64 добавляет 61033 и минимум 238 секторов.
  Даже лучшему варианту с прежней оценкой AY недостаёт 172988 байт
  до бюджета трёх TRD, ещё до кода и прочих накладных расходов.
- **Полный Z80:** восстановление базы 1554956121 T; контроль 1452380532
  (−102575589), порог 64 — 1333228809 (−221727312). Максимумы
  1034409 → 1012577 / 688115 T. Код 1262 → 1406 байт, состояние 22 → 23.
  Отдельный ZX0: 110188648 → 110547298 / 131251481 T. Суммарный выигрыш
  двух измеренных стадий −102216939 (6,139%) / −200664479 (12,051%).
  Метаданные, окно, экран, paging, IRQ/ULA/ROM/диск в эту сумму не входят.
- **Проверки:** пять независимых полных восстановлений, два полных Z80,
  2320 независимо проверенных ZX0-блоков, CPU ZX0 для 704. Формулы
  управления/масок/атрибутов/литералов/кэша/Хаффмана совпали по каждому
  кадру. Четыре новых +21 существующий тест: в том числе сохранение
  старого машинного кода и AY IRQ после каждой инструкции смешанного
  трёхкадрового теста. Исходные пиксели кандидата/атрибуты/AY сохранены.
- **Решение:** сохранить отдельный проход/условный кэш как базу; готовые
  плитки остаются экспериментом. У порога 64 ещё 603 кадра дороже
  425448 T; оптимистичная очередь полных кадров — 54 вместо 180,
  но это 207360 байт. Плавные 8⅓ fps и три TRD не доказаны.
  Вариант всех изменившихся плиток отклонён по размеру. Нового выпуска
  нет, PLAYER/TRD прежние, интегрированная разница горячего пути 0 T.
- **Материалы:** [результаты и команды](toolkit/HYBRID_TILES_RESULTS_ru.md),
  [кодировщик/декодер](toolkit/probe_hybrid_tiles.py),
  [CPU-стенд](toolkit/benchmark_hybrid_tiles.py),
  [проверяемая сводка](toolkit/hybrid_tiles_summary.json).

## 2026-09-18 — причинный кадр Z80, кэш строк и пропуск пустых масок

- **Цель/база:** уйти от готовых пар предсказаний в CPU-стенде; `2f3ce3f`,
  тот же FPD1 direct/16, все 4971 кадр. Теперь Z80 сам исполняет обход,
  сохранение исходных строк, движение ±4, нулевой предиктор, маски,
  Хаффман и запись результата/XOR атрибутов. Хост больше не подставляет
  предсказания или историю между кадрами. Контейнерные метаданные
  пока разворачиваются хостом; вывода в физический экран/диска ещё нет.
- **Память:** один компактный кадр 3840 + кэш 16 строк с полями 1024 =
  **4864 байта**, на 2816 меньше двух компактных кадров. Нулевые векторы
  у 754605 из 954432 плиток (79,063%); для них предсказание не копируется.
  Код базовой версии 1230, оптимизированной 1262 байта; состояние 22.
- **Полный CPU:** обе версии восстановили все кадры/1688733 значения/
  8715932 бита; Хаффман на каждом кадре совпал с предыдущим замером.
  Пропуск пустых половин растра и масок атрибутов: 1651609123 →
  **1554956121 T**, −96653002 (−5,852%); стадия масок −19,069%.
  Среднее 332248,868 → 312805,496; максимум 1035182 → 1034409 T.
  Независимая формула по маскам совпала с разницей каждого кадра;
  постоянный кэш 58792 T/кадр также проверен по инструкциям Zilog.
- **Проверки:** пять новых тестов + 16 существующих прошли; все векторы
  на краях, нулевые значения, пустые маски, группы/битовые границы,
  LDI 16 T и реальный AY IRQ после каждой инструкции обеих версий.
  Два полных Z80-прогона, защита записи кода/таблиц/нулевых полей кэша.
  Пиксели и AY не менялись, FPD1/ZX0 размеры остались прежними.
- **Ограничение/решение:** 806 кадров превышают 425448 T ещё до ZX0,
  экрана и диска. Только Хаффман кадра 3685 — 544854 T. Оптимистичный
  буфер полного восстановления требует 180 кадров вместо 190; это
  691200 байт. Такой путь не принимается для плавного выпуска.
  Сохранить точную причинную базу и пропуск пустых масок; дальше
  отдельный проход атрибутов и более быстрые режимы плотных сцен.
  В документе сохранена предполагаемая карта всех 128 КиБ, но сокращение
  кольца до 64 КиБ/подача/вывод ещё не проверены. PLAYER/TRD не менялись,
  интегрированный горячий путь **0 T разницы**, новой сборки нет.
- **Материалы:** [результаты, RAM и следующие шаги](toolkit/CAUSAL_TILES_RESULTS_ru.md),
  [генератор](toolkit/causal_tile_z80.py), [стенд](toolkit/benchmark_causal_tiles.py),
  [сводка с формулами и очередью](toolkit/causal_tiles_summary.json).

## 2026-09-18 — разделение метаданных и битов: малый выигрыш, не внедрено

- **Цель/база:** проверить загрязнение словаря ZX0 битами Хаффмана;
  `2f3ce3f`, FPD1 direct/16, весь фильм 4971 кадр. MDV1 отделяет
  векторы/маски/длины от неизменённых битов изображения.
- **Измерения:** точное восстановление полного FPD1; optimal ZX0 8192,
  212 блоков метаданных + 134 блока значений независимо проверены.
  Размеры с заголовками 946906 + 1082894 = **2029800 байт**,
  всего −4486 к FPD1 (2034286), без физического чередования потоков.
  Предварительный DEFLATE обещал −57934; реальный ZX0 это не подтвердил.
  Несжатые значения + ZX0 метаданных дают **2036676**, хуже на 2390.
- **Проверки/решение:** один новый тест — обратимость, короткая группа,
  повреждения; пиксели/AY не меняются. Даже меньшая оценка со звуком
  превышает бюджет трёх TRD на 169832 байта. Пока не внедрять ради
  малого выигрыша: новый последовательный контейнер, читатель,
  память двух потоков и дисковая подача не измерены. PLAYER/TRD прежние,
  интегрированная разница горячего пути **0 T**.
- **Материалы:** [результаты и команды](toolkit/SPLIT_METADATA_RESULTS_ru.md),
  [скрипт](toolkit/probe_split_metadata.py), [сводка](toolkit/split_metadata_measurements.json).

## 2026-09-18 — восьмибитный декодер: −34,618% стадии чтения значений

- **Цель/база:** заменить дорогой побитный Хаффман; CPU `4ade226`,
  хранение `fbf351e`, готовые байты `1983327`, все 4971 кадр.
  Частотные 64+1 контекста заменены на готовые 16+1 с восьмибитным
  префиксом и каноническим хвостом. Это разные кодовые потоки тех же
  кадров/масок, не изолированное сравнение декодеров на одном входе.
- **CPU полностью:** 1688733 значения, 8715932 бита, 622 группы,
  55184 вызова. Примитив 649319871 → **353050579 T**; с обвязкой
  855816292 → **559547000 T**, −296269292 (−34,618%). Максимум кадра
  1281988 → 813948, максимум вызова 23928 → 18972 T.
  Код 404 → 338 байт, состояние 3, таблицы 16888 → 16938 байт.
  Формулы, листинг и гистограмма инструкций согласованы с Zilog UM0080.
- **ZX0/размер:** файл больше на 29448 байт, но отдельная стадия ZX0
  на всех 345 блоках 110592540 → 110188648 T (−403892); максимум
  788526 → 546160 T. Физическая цена дополнительных секторов не измерена.
  Отдельный расчёт убираемой частотной процедуры: 1652491 × 117 T,
  без внешних CALL/настройки; к измеренному Хаффману не прибавляется.
- **Проверки:** 22 теста прошли; все коды при всех смещениях, нулевые
  значения, границы, сохранение состояния при AY IRQ после каждой
  инструкции. Добавлен DEC IX 10 T без изменения Z/C. Полный CPU-прогон
  сверил каждое значение/бит и все блоки ZX0; новые пиксели не менялись.
- **Ограничение/решение:** стадия с обвязкой всё ещё превышает бюджет
  425448 T у 278 кадров. Даже без остального конвейера нужна очередь
  минимум 24 полных кадра (92160 байт); со служебной памятью она не
  помещается. Сохранить быстрый примитив, отклонить текущую обвязку
  как основу выпуска; дальше интегрировать чтение прямо в цикл плиток.
  Табличный банк 16 КиБ + 554 байта фиксированной памяти проверены
  отдельно, меньший дисковый буфер/общая карта/paging ещё не приняты.
  PLAYER/TRD прежние, интегрированный горячий путь **0 T разницы**;
  новая дисковая/Fuse подача и 8⅓ fps не подтверждены.
- **Материалы:** [результаты, RAM и команды](toolkit/PREFIX_HUFFMAN_RESULTS_ru.md),
  [генератор](toolkit/prefix_huffman_z80.py), [CPU-стенд](toolkit/benchmark_prefix_huffman.py),
  [сводка с очередью](toolkit/prefix_huffman_cpu_summary.json).

## 2026-09-18 — XOR и готовые значения в контекстах предсказания

- **Цель/база:** уменьшить размер и убрать дорогое восстановление частотных
  поправок; `fbf351e`, 4971 кадр, прежние векторы, групповые маски,
  разрешённый фильтр `p2/b128/a1/e24`, AY без изменений.
- **Параметры:** FPD1 с тремя алфавитами: частотный, XOR, готовый байт
  рисунка (включая ноль); атрибуты всегда XOR. Профиль 16/32/64/128
  контекстов для каждого алфавита. Сериализованы и причинно восстановлены
  пять потоков: frequency/64, xor/64, direct/16, /32, /64.
- **Результат:** optimal ZX0 8192, с заголовками: контроль 2004846;
  XOR/64 **1999921** (−4917 к FPC3); direct/64 2000167 (−4671);
  direct/32 2013880 (+9042); direct/16 2034286 (+29448).
  Контроль оболочки отличается от FPC3 на +8 байт. Лучший дефицит
  трёх TRD с прежней оценкой AY — **139953 байта**, без новых накладных
  расходов. Числа 128 контекстов — только профиль, ZX0 не запускался.
- **Проверки:** пять полных восстановлений исходного FPR1 и всех кадров;
  все **1712 блоков** ZX0 независимо декодированы. Два новых теста
  проверяют алфавиты, нулевые готовые значения, неполную группу и
  повреждения; старые тесты контекстов/предсказаний прошли. Ни одного
  нового изменения пикселей; повторного субъективного просмотра нет.
- **CPU/память/решение:** PLAYER не менялся, разница горячего пути **0 T**.
  direct/64 стоит всего +246 байт к XOR/64 и позволяет убрать отдельное
  восстановление рисунка. direct/16 требует больше места, но быстрые
  таблицы могут занять один банк; выбран для отдельного CPU-опыта.
  Ни сокращение кольца, ни весь конвейер/дисковая подача пока не приняты.
  Исправлена устаревшая шапка toolkit README: текущий выпуск — 14 TRD.
- **Материалы:** [результаты и команды](toolkit/DIRECT_VALUES_RESULTS_ru.md),
  [профиль](toolkit/profile_direct_values.py), [кодек](toolkit/probe_direct_values.py),
  [сводка](toolkit/direct_values_summary.json). Новый выпуск не заявлен.

## 2026-09-18 — отдельные маски растра/цвета: ещё 83095 байт экономии

- **Цель/база:** убрать лишние данные без нового ухудшения;
  FPC2 из `8e0812b`, все 4971 кадр, контексты 64+1, прежние пиксели/AY.
  Разделяются маски 16 байтов растра и четырёх атрибутов каждой плитки.
- **Перебор:** семь перестановок, во всех побайтно восстановлен весь
  исходный FPC2. Битовые плоскости по кадру/8 плиткам и порядок по времени
  не продвигались после оценки DEFLATE. Четыре варианта измерены optimal
  ZX0 8 КиБ, все **1379 блоков** независимо восстановлены точно.
- **Размер с заголовками:** прежний FPC2 2087933; контроль FPC3 2087964;
  разделение по кадрам 2007337; по группе **2004838**; отдельные старшие/
  младшие байты маски 2006603. Лучший выигрыш **83095 байт (3,980%)**.
  Со старой оценкой звука 77696 — 2082534 байта; дефицит трёх TRD
  **144870 байт** до кода/томов/копий таблиц/выравнивания.
- **CPU:** те же инструкции ZX0 на всех 342 блоках: 121478238 →
  110592540 T (−10885698), максимум 788767 → 788526 T. Формула ранее
  проверенного примитива масок: 144824628 → 144079388 T (−745240),
  335543 пакета, без настройки/внешних CALL. Это расчёт масок, не
  исполнение всего их читателя; ZX0 замерен реально на CPU-модели.
- **Проверки/границы:** два новых теста — известные позиции, все режимы
  с 1/3/8 кадрами, неполная последняя группа, повреждённый контейнер.
  Никаких новых пиксельных изменений; субъективный просмотр не повторялся.
  Развёрнутые маски/векторы остаются 5376 байт на восемь кадров.
  Нового читателя масок Z80, карты RAM, IRQ/дисковой/Fuse проверки нет.
  PLAYER не менялся: до/после тот же горячий путь, **0 T разницы**.
- **Решение:** групповой вариант сохранить основным кандидатом масок.
  Экономятся и объём, и стадия ZX0. Проблема скорости побитного Хаффмана
  остаётся; его нужно заменить быстрым табличным путём. Цель не достигнута,
  выпускные 14 TRD в LFS не заменялись.
- **Материалы:** [отчёт и команды](toolkit/CONTEXT_MASKS_RESULTS_ru.md),
  [преобразователь](toolkit/probe_context_masks.py),
  [сводка](toolkit/context_masks_summary.json),
  [CPU ZX0](toolkit/context_masks_group_split_zx0_cpu_measurements.json).

## 2026-09-18 — Z80-декодер контекстов: ускорен, но побитный путь отклонён

- **Цель/база:** проверить цену контекстного сжатия по скорости;
  `8e0812b`, полный FPC2 с 64 группами, 4971 кадр, 1688733 поправки.
- **Реализация:** канонические счётчики листьев с 8-битным рангом,
  компактный цикл и прямые указатели с развёрнутыми шагами. Обёртка
  выдаёт до 32 поправок, хранит состояние в трёх байтах. Пары прогноза
  подаёт ПК; создание прогноза/разбор масок/диск не входят в CPU-замер.
- **Полные CPU-прогоны:** 957658332 → 855816292 T, **−101842040 T**
  (10,634%); среднее 192649,031 → 172161,797 T/кадр; максимум порции
  27080 → 23928 T. Все поправки и 8418269 входных бит проверены.
  Код 105 → 404 байта, таблицы 16250 → 16888 (15864 в банке +1024
  в фиксированной RAM). Внешние CALL обёртки добавили бы 938128 T.
- **Проблема скорости:** 430 кадров превышают даже полный номинальный
  бюджет 425448 T только на этой стадии; худший требует 1281988 T.
  Идеальная очередь готовых кадров потребовала бы 138 кадров, без прочих
  расходов. Это модель конкретной очереди, не предел всех способов подачи.
- **ZX0:** все 353 блока FPC2 исполнены прежним turbo, 121478238 T
  против 126825689 T FPM1, −5347451 T; пик блока 448927 → 788767 T.
  Непрерывный стенд исключает окна/банки/IRQ/ULA/ROM/диск.
- **Проверки:** все коды всех 65 таблиц и входы карты для трёх вариантов,
  усечение/пустые порции/порча регистров; существующий AY IRQ после каждой
  инструкции на коротком примере; исчерпывающий тест SLA в CPU-модели.
  Шесть новых и десять связанных прежних тестов пройдены. PLAYER и
  дисковое кольцо не менялись; горячий путь до/после одинаков, **0 T**.
- **Решение:** побитный основной путь для выпуска **не принят**.
  Сохранить как проверенный резерв для длинных кодов и основу сравнения;
  нужен быстрый выбор сразу по нескольким битам. Плавные 25/3 fps этим
  опытом не подтверждены, TRD не менялись.
- **Материалы:** [отчёт, такты и команды](toolkit/CONTEXT_HUFFMAN_CPU_RESULTS_ru.md),
  [Z80](toolkit/context_huffman_z80.py), [полный стенд](toolkit/benchmark_context_huffman.py),
  [машинная сводка](toolkit/context_huffman_cpu_summary.json).

## 2026-09-18 — контекстные таблицы поправок: ещё 206315 байт экономии

- **Цель/база:** уменьшить объём без новых изменений пикселей;
  `8b3f83f`, все 4971 кадр, FPR1 частотного алфавита, прежний ограниченный
  фильтр p2/b128/a1/e24, звук неизменён. Разрешение и кадры сохранены.
- **Перебор:** семь моделей из масок/векторов/предыдущих поправок —
  полный точный обратный FPR1. Шесть моделей предсказанного содержимого,
  фиксированные/адаптивные префиксные палитры и слияние распределений
  до 4–64 групп — битовые оценки. Фиксированные палитры хуже общего
  Хаффмана; адаптивные уступают группировке и не реализованы далее.
- **Реальный ZX0 8 КиБ:** контроль FPC1 2294210 байт (38 байт выигрыша
  от контейнера); плотность/движение 2250376; 8/16/32/64 групп прогноза
  2181521/2137952/2108904/2087933 байта. Прежний FPM1 2294248.
  Лучший результат −206315 байт (8,993%). Со старой оценкой AY 77696
  остаётся дефицит трёх TRD **227965 байт** до дополнительных расходов.
- **Обратимость:** четыре FPC2 декодера полного фильма строили прогноз
  только из собственных предыдущих кадров, без кеша кодировщика.
  Все 4971 кадр и весь FPR1 совпали точно. Все 2183 ZX0-блока шести
  прогонов независимо проверены. Максимальный сжатый блок 8220 байт.
  Покадровое качество равно исходному отфильтрованному кандидату;
  нового субъективного просмотра не было. Пройдены новые и связанные
  прежние тесты; команды/охват приведены в отчёте.
- **Память/CPU:** обычное дерево для 64 групп требует 41726 байт,
  канонические счётчики — 15080 с картой/указателями. Проверены все
  коды и 8-битный ранг/индекс; это размер таблиц, не полная карта RAM.
  Нового Z80-кода/подсчёта его T-states/замеров IRQ/диска/Fuse нет.
  PLAYER тот же до и после: изменение горячего пути **0 T**.
- **Решение:** продолжить с этим представлением, измерив новый
  декодер и весь конвейер. Старый декодер с минимумом 4 бита неприменим
  к новым кодам 1–18 бит. Размер не доказывает плавные 25/3 кадра/с.
  Цель пока не достигнута; 14 выпускных TRD в LFS не заменялись.
- **Воспроизведение:** [полный отчёт и команды](toolkit/CONTEXT_VALUES_RESULTS_ru.md),
  [FPC1](toolkit/probe_context_values.py), [профили](toolkit/profile_prediction_contexts.py),
  [причинный FPC2](toolkit/probe_prediction_values.py),
  [таблицы памяти](toolkit/profile_context_tree_memory.py),
  [машинная сводка](toolkit/context_values_summary.json).

## 2026-09-18 — увеличение истории ZX0 до 16–32 КиБ

- **Цель/база:** проверить обмен памяти на объём; `539110d`, полный
  FPM1 из 4971 кадра, 3101943 исходных байта, те же пиксели/звук.
  Меняется только размер независимого оптимального ZX0-блока.
- **Размер:** 8 КиБ — 2294248 байт; 16 КиБ — 2287768 (−6480, 0,282%);
  32 КиБ — 2283014 (−11234, 0,490%). Все размеры с заголовками блоков.
  Даже последний вариант со звуком превышает бюджет трёх TRD на 423046
  байт до дополнительных расходов. Новые 190+95 блоков восстановлены точно.
- **CPU 16 КиБ:** все 190 блоков реально исполнены тем же 126-байтовым
  turbo-кодом. 126825689 → 128619118 T (+1793429), максимум блока
  448927 → 843236 T. Измерены только CPU-инструкции декодера, без
  ввода/порций/банков/IRQ/ULA/ROM/диска. Карта стенда перекрывает экран
  входом и не является картой выпуска. Для 32 КиБ Z80-время не измерялось.
- **История:** в варианте 16 КиБ ссылки дальше 8192 копируют 35255 байт,
  максимум смещения 16214. В 32 КиБ максимум 31941, дальше 16 КиБ
  копируется 25951 байт. Сжатый блок до 30897 байт требует подачи порциями;
  в 8-КиБ варианте тоже есть расширившийся блок 8215 байт.
- **Проверка:** трассировка всех 379+190+95 блоков, точное восстановление
  и покрытие литералами/ссылками; 3 новых и 3 прежних теста прошли.
  Дополнительные наблюдатели декодера ПК не меняют машинный код.
- **Решение:** увеличение истории для этого потока не продвигать: выигрыш
  менее 0,5% не оправдывает переделку памяти и подачи, 16 КиБ уже медленнее.
  Основным остаётся 8 КиБ; цель трёх дискет не достигнута. PLAYER/TRD и
  горячий путь выпуска не изменены (0 T), меньший дисковый буфер не принят.
- **Файлы:** [отчёт и воспроизведение](toolkit/LARGE_HISTORY_RESULTS_ru.md),
  [анализатор ссылок](toolkit/summarize_large_history.py),
  [полная статистика](toolkit/large_history_measurements.json).

## 2026-09-18 — разреженные маски и перестановка векторов

- **Цель/база:** уменьшить оставшийся дефицит трёх TRD без новых изменений
  пикселей; `821005a`, весь FPE1, 4971 кадр / 622 группы, прежний AY.
- **Опыт:** десять обратимых вариантов FPM1: XOR по времени/соседу,
  перестановки, один/два уровня признаков ненулевых масок и серии.
  Предварительный DEFLATE отобрал перестановку векторов с двумя уровнями
  масок; дополнительно измерен более простой одноуровневый вариант.
- **Размер ZX0:** прежние 2339165 → **2294248 байт** (−44917, 1,920%).
  Один уровень 2302626 байт (−36539). В лучшем варианте с прежней оценкой
  звука получается 2371944 байта: дефицит трёх TRD **434280** до кода,
  таблиц, границ томов и выравнивания. DEFLATE предсказывал больший выигрыш;
  он не принят вместо результата ZX0.
- **CPU:** 14-байтовый примитив выдаёт 8 масок за `412+8*n` T, где n —
  число ненулевых значений; все 512 случаев исполнены и проверены на Z80.
  По формуле для всего фильма два уровня требуют 144824628 T против
  50118876 T копирования (+94705752). Все 379 новых ZX0-блоков реально
  исполнены: 191504507 → 126825689 T (−64678818). Сумма этих стадий
  растёт на 30026934 T, +6040,421 T/кадр без вызывающего кода/векторов.
- **Проверка:** все десять потоков восстанавливают исходный FPE1 побайтно;
  все 390+379 новых ZX0-блоков независимо распакованы, 3 теста прошли.
  Метрики качества наследуются через точную обратимость. Полный новый
  читатель FPM1, чередование ZX0/Хаффмана, карта RAM и подача диска ещё
  не проверены. Размер и сумма отдельных стадий не доказывают 8⅓ fps.
- **Решение:** сохранить совмещённый вариант как лучший по размеру,
  одноуровневый — как более простой кандидат; пока не выпускать TRD.
  PLAYER/горячий путь не менялись (0 T), новых IRQ/ULA/ROM/Fuse-замеров нет.
  Три дискеты пока не достигнуты.
- **Файлы:** [отчёт и команды](toolkit/MOTION_METADATA_RESULTS_ru.md),
  [преобразования](toolkit/probe_motion_metadata.py),
  [примитив Z80](toolkit/benchmark_metadata_z80.py),
  [результаты отбора](toolkit/motion_metadata_measurements.json).

## 2026-09-18 — Хаффман с приостановкой между порциями ZX0

- **Цель/база:** устранить длинные непрерывные участки и группы больше
  истории 8 КиБ; `a111b58`, весь фильм 4971 кадр, тот же FPE1 без новой
  ошибки изображения и без изменений AY.
- **Опыт:** Хаффман выдаёт до 32 поправок, состояние 13 байт; ZX0 выдаёт
  по 128 байт. Оба декодера исполняются поочерёдно на одном Z80 с настоящими
  переключениями банков 0/6. Таблица 12288 байт, код Хаффмана 314 байт.
- **Измерено:** все 622 группы / 1688733 поправки и 565 ZX0-блоков точны.
  Хаффман 362673773 → 437826228 T (+75152455); максимальная порция
  12394 T. ZX0 с приостановками/банковыми обёртками 191504507 →
  270730491 T (+79225984), максимум 21253 T. Сумма двух стадий
  554178280 → 708556719 T; +31055,812 T/кадр в среднем. Это не полный
  проигрыватель; внешние CALL и работа вызывающего кода сюда не входят.
- **Размер:** прежние 2339165 байт видео; со звуком дефицит трёх дискет
  остаётся 479197 байт до накладных расходов. Уровней яркости уже четыре,
  2 бита на логический пиксель; повторная квантизация здесь не нужна.
- **Проверка:** 13 тестов прошли, включая IRQ/AY после каждой инструкции
  тестового потока Хаффмана, разрывы входа и порчу регистров между вызовами.
  Исправлены недостающая метка стенда и ложное превышение лимита шагов,
  когда тот учитывал инструкции ISR. Полный CPU-прогон был без IRQ/ULA/ROM;
  расписание звука и физический диск этим тестом не проверены.
- **Решение:** сохранить механизм ограниченной предварительной распаковки;
  выросшую цену CPU учитывать при интеграции. Общая RAM/дисковая очередь,
  отрисовка, сроки кадров и Fuse пока не проверены. PLAYER/TRD не менялись,
  встроенный горячий путь 0 T. Три дискеты ещё не достигнуты.
- **Файлы:** [отчёт и воспроизведение](toolkit/INCREMENTAL_HUFFMAN_RESULTS_ru.md),
  [генератор](toolkit/incremental_huffman.py),
  [полный Z80-стенд](toolkit/benchmark_incremental_huffman.py),
  [измерения](toolkit/incremental_huffman_measurements.json).

## 2026-09-18 — весь Хаффман и ZX0 исполнены на Z80

- **Цель/база:** проверить CPU/RAM кандидата `f3f5390`, весь фильм
  4971 кадр, 1688733 поправки; новых изменений изображения/звука нет.
- **Опыт:** автомат переходов по 4 битам, 254 состояния, таблица 12288
  байт и код 76 байт. Контроль — копирование тех же поправок через LDIR.
  Отдельно измерены все ZX0-блоки потоков до/после Хаффмана.
- **Измерено:** выдача поправок 35474591 → 362673773 T, +65821,602 T
  в среднем на кадр. ZX0 291270807 → 191504507 T. Сумма отдельных
  стадий 326745398 → 554178280 T, +45751,938 T/кадр; это не время
  полного проигрывателя. Размер прежний 2339165 байт видео, дефицит
  трёх TRD со звуком 479197 байт до накладных расходов.
- **Ограничение:** шесть кадров требуют >425448 T только на Хаффман,
  максимум 554488 T. Самая тяжёлая группа: 9425 байт входа, 10551
  результата, 2603037 T. Целая группа не помещается в историю ZX0 8 КиБ.
- **Проверка:** 622 группы Хаффмана и 615+565 блоков ZX0 побайтно;
  формула T совпала для каждой группы. 11 тестов прошли, включая SET
  (32768 команд), регрессии IRQ/времени прежнего проигрывателя. Стенд
  использует отдельную карту RAM; совместная карта выпуска не проверена.
- **Решение:** синхронную распаковку перед показом кадра не интегрировать.
  Нужны ограниченная предварительная распаковка, переходы блоков, очередь
  и более быстрый разбор. PLAYER/TRD не менялись, встроенный горячий путь
  0 T; новые ROM/ULA/диск/Fuse не измерены. Цель ещё не достигнута.
- **Файлы:** [отчёт, формулы, RAM и команды](toolkit/HUFFMAN_Z80_RESULTS_ru.md),
  [декодер/полный прогон](toolkit/benchmark_huffman_z80.py),
  [измерение ZX0](toolkit/benchmark_zx0_storage.py),
  [сводка](toolkit/summarize_huffman_transport.py).

## 2026-09-18 — короткие коды поправок и Хаффман перед ZX0

- **Цель/база:** уменьшить объём без новой ошибки; `cb7031f`, весь фильм
  частотного алфавита, 4971 кадр, прежние разрешение, 25/3 fps и AY.
- **Опыт:** короткие коды 2/3/4/5/6 бит с выходом на редкие байты,
  канонический Хаффман и обычные байты в контрольном FPE1. Обрабатываются
  1688733 поправки; векторы, маски и кадры полностью сохраняются.
- **Измерено:** оптимальный ZX0 8192: контроль 2472168 → Хаффман
  2339165 байт, −133003 (5,380%). Прежний лучший FPR1 2470635 улучшен
  на 131470 байт. С AY 2416861, дефицит трёх TRD 479197 байт до
  служебных расходов. Хаффман хуже на DEFLATE, но лучше на ZX0;
  пять кодов с выходом пока имеют только DEFLATE-измерения.
- **Проверка:** 7 полных обратных преобразований сериализованного потока,
  615+565 блоков ZX0, 22 теста движения. При добавлении статистики длин
  повторены те же 7 потоков с неизменными SHA. Коды Хаффмана 4–14 бит,
  84,7665% поправок укладываются в 8. Z80-декодер битов ещё не реализован.
  PLAYER/TRD не менялись, встроенный горячий путь 0 T. Скорость 8⅓ fps
  нового формата, RAM, Fuse/ROM/ULA/диск ещё не проверены.
- **Решение:** новый лучший кандидат хранения, не выпуск. Далее нужны
  битовый декодер и измерение худших кадров/полной доставки; для объёма —
  исследование контекстов масок и поправок. Три дискеты пока не достигнуты.
- **Файлы:** [отчёт и команды](toolkit/MOTION_ENTROPY_RESULTS_ru.md),
  [кодер и независимый декодер](toolkit/probe_motion_entropy.py).

## 2026-09-18 — битовые формулы вместо таблицы яркости

- **Цель/база:** уменьшить CPU/RAM точного частотного алфавита `cb7031f`,
  все 65536 сочетаний байтов, частоты поправок полного фильма.
- **Опыт:** две реализации логических формул над четырьмя пикселями
  одновременно. Первая требует дополнительных E/H, вторая сохраняет
  B/C/E/H как прежний табличный примитив.
- **Измерено:** прежние 148 T → 116 T (первый вариант) → 117 T с прежним
  набором сохраняемых регистров. Для последнего −31 T, код 35→28 байт,
  таблица 256→0 байт. Оценка экономии операций по поправкам фильма:
  средняя 10305,214 T/кадр, максимум 61504 T; это не время полного кадра.
- **Проверка:** 196608 исполнений примитивов. В интерпретатор добавлены
  CPL и циклические вращения регистров/`(HL)`; 2 теста с 9216 отдельными
  командами и 5 прежних тестов проигрывателя прошли. Встроенный горячий
  путь PLAYER не менялся, 0 T. Новых Fuse/ROM/ULA/дисковых замеров нет.
- **Решение:** сохранить вариант 117 T для будущего декодера. Время
  Хаффмана и полная доставка ещё не измерены; выпуск не обновлён.
- **Файлы:** [формулы, времена и команды](toolkit/FREQUENCY_LOGIC_RESULTS_ru.md),
  [машинный код и исчерпывающая проверка](toolkit/benchmark_frequency_logic.py).

## 2026-09-18 — алфавит поправок по предсказанной яркости

- **Цель/база:** сократить точный остаток `8dd09de`, полный фильм с прежним
  лимитом 128; дополнительной ошибки изображения нет, маски совпадают.
- **Опыт:** четыре перестановки кодов для каждого предсказанного уровня:
  XOR, частотная, ближайшая по покрытию, циклическая. Нулевой код всегда
  сохраняет предсказание; атрибуты XOR, группы/плитки 8, обёртка FPR1.
- **Измерено:** оптимальный ZX0 8192, частотная таблица 2470635 байт
  против 2509863 контроля в FPR1, −39228 (1,563%). Прежний лучший
  результат 2509819 улучшен на 39184 байта. С AY 2548331, дефицит
  трёх TRD 610667 байт до служебных расходов. Остальные два варианта
  имеют только измерения DEFLATE, они хуже частотного.
- **Проверка:** 4 полных восстановления кадров, 615+615 блоков ZX0,
  18 тестов движения. Табличный Z80-примитив 148 T против XOR 18 T,
  +130 T на исправленный байт; 327680 исчерпывающих исполнений.
  Расчётная добавка только этих операций в среднем 43215,415 T/кадр,
  максимум 257920 T. Полного декодера/Fuse/дискового замера нет.
  PLAYER/TRD не менялись, встроенный горячий путь 0 T.
- **Решение:** лучший измеренный кандидат хранения, пока не выпуск.
  Дополнительное CPU-время и дефицит трёх дискет остаются. Далее проверить
  короткие коды и ускорение частых поправок; их эффект пока не измерен.
- **Файлы:** [отчёт и команды](toolkit/MOTION_ALPHABET_RESULTS_ru.md),
  [кодер/декодер](toolkit/probe_motion_alphabet.py),
  [времена Z80](toolkit/benchmark_motion_alphabet.py).

## 2026-09-18 — половинное движение четырёх уровней без потерь

- **Цель/база:** проверить табличное промежуточное предсказание; `8dd09de`,
  полный исходный фильм 4971 кадр, прежние разрешение, 25/3 fps и AY.
- **Опыт:** 81 целочисленный и 120 половинных векторов, плитки 8×8,
  группы 8, округление смешанного покрытия вверх/вниз; точные поправки.
- **Измерено:** оптимальный ZX0 8192, целочисленный контроль 2656092 →
  половинный верхний 2628420 байт, −27672 (1,042%). С прежним AY дефицит
  трёх TRD 768452 байта до служебных расходов. Нижний вариант проверен
  только DEFLATE. Это точное исходное изображение, не вариант лимита 128.
- **Проверка:** 3 полных независимых восстановления, 638+628 блоков ZX0,
  5 тестов. Z80-примитив смешивания: 148 T против 14 T выбора готового
  байта, +134 T, без загрузки/выравнивания/записи/циклов/CALL; 196608
  исчерпывающих исполнений трёх примитивов. PLAYER/TRD не менялись,
  встроенный горячий путь 0 T; полного Z80/Fuse/дискового замера нет.
- **Решение:** сохранить, пока не интегрировать: выигрыш около 1%,
  дополнительная CPU-работа и незакрытый дефицит. Проверить алфавит
  поправок, зависящий от предсказанного уровня. Три TRD не получены.
- **Файлы:** [отчёт, времена и команды](toolkit/HALFPEL_RESULTS_ru.md),
  [кодер/независимый декодер](toolkit/probe_halfpel_motion.py),
  [Z80-примитив](toolkit/benchmark_two_bit_lookup.py).

## 2026-09-18 — порядок поправок по плиткам без дополнительной ошибки

- **Цель/база:** уменьшить остаток без дополнительных изменений пикселей;
  `45a7385`, вариант 128, и точный контроль группы 8 из `a5a49f9`.
- **Опыт:** маски и значения поправок FMR1 переставлены по плиткам
  4/8/16 с атрибутами каждой плитки; векторы и кадры остаются прежними.
  6 полных вариантов; дополнительной потери качества нет.
- **Измерено:** плитки 8×8, оптимальный ZX0 8192 для варианта 128:
  2537085 → 2509819 байт (−27266, 1,075%). С прежним AY 2587515 байт,
  превышение бюджета трёх TRD 649851 байт до служебных расходов.
- **Проверка:** 6 обратных преобразований всего сериализованного потока
  побайтно, 615 блоков ZX0, 2 теста адресов/неполных групп/усечения.
  Кадры совпадают с проверенными в предыдущем опыте. PLAYER/TRD не менялись,
  горячий путь 0 T; новых Z80/Fuse, ROM/ULA/дисковых измерений нет.
- **Решение:** сохранить плитки 8×8 как базу дальнейшего опыта. Три TRD
  пока не получены, скорость нового декодера не проверена. Проверить табличное
  предсказание промежуточного положения пикселей с точными поправками;
  эта следующая идея ещё не измерена.
- **Файлы:** [дополнение с данными и командами](toolkit/BOUNDED_MOTION_RESULTS_ru.md),
  [перестановка и обратная проверка](toolkit/probe_motion_residual_order.py).

## 2026-09-18 — ограниченные поправки поверх компенсации движения

- **Цель/база:** уменьшить поток при прежнем разрешении и 25/3 fps,
  база `66257b4`, все 4971 кадр, атрибуты и AY без изменений.
- **Опыт:** поиск движения с отменой отдельных байтов поправок. Максимум
  2 логических пикселя на ячейку, четверть заполнения на пиксель, RMSE ≤24,
  один последовательный неточный кадр ячейки; бюджеты 64/128/256 на кадр,
  группы масок 8/16. Во всех случаях ошибка сравнивается с исходным кадром.
- **Измерено:** выбран 128 / группа 8, оптимальный ZX0 8192:
  2679898 → 2537085 байт (−142813, 5,33%). Средняя/максимальная доля
  изменённых физических RGB-пикселей 0,204015%/0,347222%; SSIM
  средний/минимальный 0,991185/0,966887. В среднем пропущено 71,879
  исходных и добавлено 75,506 пиксельных изменений на переход кадра.
- **Проверка:** 6 полных восстановлений, 615 блоков ZX0, 5 тестов;
  SSIM, переходы и длительность ошибки проверены по всем кадрам 3 вариантов.
  Настоящий рендер подтвердил максимум 1 последовательный неточный кадр
  ячейки. Просмотрены короткие полосы худших сцен 64/128, не весь фильм
  в движении. PLAYER/TRD не менялись, горячий путь 0 T; новых Z80/Fuse нет.
- **Решение:** не выпускать — с прежним замером AY превышение бюджета
  трёх TRD ещё 677117 байт до служебных расходов. Лимит 256 не выбран:
  лишь 10335 байт дополнительной экономии DEFLATE при удвоении худшей
  доли изменённых пикселей. Продолжить сокращать остаток и проверять качество.
- **Файлы:** [отчёт и команды](toolkit/BOUNDED_MOTION_RESULTS_ru.md),
  [кодер](toolkit/probe_bounded_motion.py),
  [временные метрики и полосы кадров](toolkit/review_motion_quality.py).

## 2026-09-18 — уменьшение буфера точной компенсации движения

- **Цель/база:** сократить RAM нового формата; `66257b4`, все 4971 кадр,
  точные пиксели/атрибуты, прежние разрешение, 25/3 fps и AY.
- **Параметр:** группы FMR1 по 8 кадров вместо 16; остальной поиск движения
  и оптимальный ZX0 с блоками 8192 оставлены прежними.
  База отчёта теперь задаётся через `--baseline-commit`; у этой серии
  исправлена унаследованная метка `a13c3fe` на фактическую `66257b4`.
  Измеренные байты и хеши от исправления метки не менялись.
- **Измерено:** буфер векторов/масок 10752 → 5376 байт; поток
  2660953 → 2679898 байт (+18945, 0,712%). С двумя компактными историями
  требуется 13056 байт до остальных частей проигрывателя.
- **Проверка:** полное побайтное восстановление, 638 блоков ZX0. Кодер
  и PLAYER не менялись; горячий путь 0 T. Новых Z80/Fuse и замеров
  доставки с меньшим кольцом нет; карта памяти ещё не реализована.
- **Решение:** сохранить как контроль с меньшим буфером. Три TRD пока
  не достигаются; 80-КБ кольцо текущего выпуска не уменьшать по одной
  арифметической оценке RAM.
- **Файлы:** [дополнение с командами](toolkit/FINE_MOTION_RESULTS_ru.md),
  [метаданные ZX0](toolkit/fine_motion_groups8_zx0_measurements.json).

## 2026-09-18 — точная компенсация движения с шагом в один пиксель

- **Цель/база:** уменьшить остаток без изменения изображения; база
  `a13c3fe`, контроль масок `2e4b23a`, полный фильм 4971 кадр.
- **Опыт:** смещения ±4 с шагом 1 логический пиксель, 81 вектор и нулевой
  предиктор; блоки 4/8/16, группы 16, точные XOR-поправки и атрибуты.
- **Измерено:** оптимальный ZX0 блоками 8192, блок изображения 8×8:
  2920696 → 2660953 байта, экономия 259743 (8,89%) к контролю того же
  семейства. На 233723 байта (8,07%) меньше прежнего лучшего точного
  офлайн-замера. Видео + прежний замер AY: 2738649 байт до прочих расходов.
- **Проверка:** три полных независимых восстановления побайтно,
  638 блоков ZX0 и 4 теста пройдены. Гистограмма остатка сохранена;
  расчёт простого 4-битного прекода отмечен как оценка сырых данных.
  PLAYER/TRD не менялись, горячий путь 0 T; новых Z80/Fuse и ROM/дисковых
  измерений нет. Буфер векторов/масок лучшего варианта — 10752 байта,
  без экранов, компактных историй, ZX0, кода, AY/IRQ и TR-DOS.
- **Решение:** принять как базу следующего опыта, не как выпуск:
  с AY остаётся превышение бюджета трёх TRD на 800985 байт до загрузчика,
  границ томов и дискового размещения. Проверить ограниченную ошибку
  поверх движения, кодирование остатка и уменьшение групп масок.
- **Файлы:** [отчёт и команды](toolkit/FINE_MOTION_RESULTS_ru.md),
  [кодер/декодер](toolkit/probe_fine_motion.py),
  [анализ остатка](toolkit/analyze_fine_motion_residuals.py).

## 2026-09-18 — ограниченное удержание и маски групп кадров

- **Цель/база:** уменьшить поток при прежнем разрешении и 25/3 fps;
  база `a13c3fe`, полный фильм 4971 кадр, атрибуты и AY без изменений.
- **Опыт:** XOR n−1/n−2, маски отдельно от поправок в группах 8/16 кадров;
  без потерь, прежний словарь и удержание ячейки с ошибкой максимум
  1/2 пикселя на 1/2/неограниченное число кадров. 32 полных варианта.
- **Измерено:** оптимальный ZX0, 8192 байта: контроль 2920696 →
  2853363 байта при максимуме 2 пикселя и 1 неточного удержания;
  экономия 67333 байта (2,31%). Средняя/худшая доля изменённых физических
  пикселей 0,084185%/0,420464%; SSIM средний/минимальный 0,995884/0,973526.
- **Проверка:** 32 независимых восстановления всех кадров, 1207 блоков
  ZX0, 5 тестов формата и ограничений, SSIM всего фильма; просмотрены
  6 худших статичных кадров. Полной проверки движения и Z80/Fuse нет.
  PLAYER/TRD не менялись, горячий путь 0 T.
- **Решение:** не выпускать — видео превышает бюджет трёх TRD на
  915699 байт до звука и служебных данных. Неограниченное удержание
  отклонено: отдельная неточная ячейка сохранялась до 162 кадров (19,44 с).
  Сохранить ограниченный по памяти формат масок как контроль для движения.
- **Файлы:** [отчёт, данные и команды](toolkit/TEMPORAL_RESIDUAL_RESULTS_ru.md),
  [кодер/декодер](toolkit/probe_temporal_residuals.py),
  [тесты](toolkit/test_temporal_residuals.py).

## 2026-09-18 — словарь с контролем ошибки и раздельными атрибутами

- **Цель/база:** приблизиться к трём TRD при прежнем разрешении и 25/3 fps;
  база `24a819a`, все 4971 кадр. Пользователь разрешил только малозаметные
  изменения пикселей; звук сохраняется. Подтверждено: четыре уровня по
  2 бита на логический пиксель уже используются.
- **Опыт:** словарь 4-байтовых рисунков отдельно от точных атрибутов;
  предсказание n−2, группы 512 кадров, ограничения ошибки и числа
  изменённых пикселей. 18 полных вариантов, включая контроль без потерь
  и более грубые серии, не принятые по качеству.
- **Измерено:** ZX0 quick блоками 6144: 3260255 → 3000927 байт видео,
  экономия 259328 байт (7,95%). 256 рисунков, максимум 2 логических
  изменения на ячейку, RMSE ≤24. Меняется в среднем 0,164755% физических
  RGB-пикселей активной области; средний/минимальный SSIM 0,992374/0,966330.
- **Проверка:** 18 независимых восстановлений, 1535 блоков ZX0,
  шесть тестов, SSIM всех кадров; просмотрены шесть худших статичных кадров.
  Проверки движения и Z80/Fuse для нового формата ещё нет. PLAYER/TRD
  не менялись, горячий путь 0 T.
- **Решение:** в выпуск не включать — одно видео всё ещё на 1063263 байта
  больше прежнего бюджета трёх TRD, без звука и прочих расходов. Качество
  не считать полностью принятым по одним статичным сравнениям. Далее
  исследовать предикторы и точные поправки, сохранив этот результат как базу.
- **Файлы:** [отчёт и команды](toolkit/BOUNDED_DICTIONARY_RESULTS_ru.md),
  [кодер/декодер](toolkit/probe_bounded_dictionary.py),
  [проверка изображения](toolkit/review_bounded_dictionary.py).

## 2026-09-17 — Bad Apple, все 128 КБ и размер словаря

- **Цель/база:** проверить приёмы Bad Apple и обмен дискового буфера на
  словарь; база `27d2c92`, все 4971 экрана выпуска `69754f3`.
- **Уточнение:** «bdple» означало Bad Apple. Найдено авторское описание
  Techno Lab, отличены версии 512К/128К. Разрешение перераспределять все
  128 КБ, включая уменьшение кольца, сохранено в `AGENTS.md`.
- **Опыт:** точные ячейки 8×8 с атрибутами, skip/index/literal, таблицы
  0–4096 записей на 64/256/1024 кадра, фиксированные и короткие частые
  индексы. 29 полных вариантов проверены побайтно; отбор DEFLATE,
  затем ZX0 v2 quick блоками 6144 байта для трёх вариантов.
- **Измерено:** 256/2048/4096 записей дали 3301039/3296554/3301676 байт
  видео с заголовками ZX0. 2048 сэкономили 4485 байт (0,136%) относительно
  256, требуя 10240/18432 байта компактной/развёрнутой таблицы.
- **Проверка:** независимая распаковка 2115 блоков ZX0, четыре теста
  формата пройдены. Это офлайн-опыт, без нового Z80/CPU/Fuse-прогона;
  скорость и число дискет не получены. Горячий путь выпуска изменён на 0 T.
- **Решение:** уменьшение кольца ради этого варианта пока не принимать;
  проверить словари поправок и учесть n−2 заднего экрана. Старые TRD
  сохранены, цель двух дискет ещё не достигнута.
- **Файлы:** [разбор и карта RAM](toolkit/BAD_APPLE_AND_128K_ru.md),
  [результаты и команды](toolkit/EXACT_DICTIONARY_RESULTS_ru.md),
  [скрипт](toolkit/probe_exact_dictionary.py).

## 2026-09-17 — поиск кодеков с простой распаковкой

- **Цель/база:** найти дальнейшее сжатие без сложных вычислений на Z80;
  база `a725228`, проверенные 14 TRD выпуска `69754f3`.
- **Сделано:** проверены текущие дельты/RLE/сдвиги и прежние опыты с масками,
  плитками и перестановкой времени; изучены первичные описания LZSA,
  ZX1/ZX5, LZ4, BPE и отдельных приёмов AV1/WebP lossless.
- **Решение:** сначала сравнить LZSA2/ZX1 с нашим ускоренным ZX0, затем
  проверить точный словарь блоков/фраз и выбор кодирования по размеру
  и CPU-времени. Предыдущая плиточная компенсация движения учитывается
  как база; повтор её результата не считать новым выигрышем.
- **Проверка/ограничения:** это исследование, не замер новых кодеков на
  фильме. PLAYER и TRD не изменены, горячий путь 0 T. От лучших прежних
  раздельных потоков видео+AY до бюджета двух TRD всё ещё нужно убрать
  56,54% до дополнительных накладных расходов. «bdple» требует уточнения;
  BPE рассмотрен условно, точное соответствие названию не установлено.
- **Отчёт и следующий опыт:** [сравнение методов, источники и порядок замеров](toolkit/LOW_COST_CODECS_RESEARCH_ru.md).

## 2026-09-17 — возвращение плотности почти 1000 кадров на дискете

**Цель:** увеличить длину частей относительно выпуска на 19 TRD, сохранив
все изображения, разрешение, AY и плавные 25/3 кадра/с.
**База:** `9a43f0f`; весь фильм — 4971 кадр / 29826 состояний AY.
Приёмка: каждый показ через шесть полей, отклонение интервала ≤1 мс,
отсутствие недогрузок, побайтная проверка экранов и AY.

Ниже имена обозначают каталоги экспериментов, а не опубликованные выпуски.
Кадры нумеруются с нуля. `stored` означает отсутствие внешнего ZX0;
внутренние дельты и RLE сохраняются. Порог совпадения 3 означает замену
совпадений длиной 1–2 байта буквальными последовательностями.

| Попытка | Что меняли | Измерение/проверка | Решение |
|---|---|---|---|
| `priority160` | Приоритет фоновой распаковки при запасе от 160 секторов; 7 TRD обычного ZX0 | Плавность первой длинной части не восстановилась; на третьей опустошалась очередь AY | Отклонено; экспериментальный планировщик удалён |
| Пороги совпадения 2, 3, 4, 6, 8 | Заменяли короткие совпадения ZX0, проверяли контрольный блок кадров 623–625 | При пороге 3: 3927 → 4661 байт; CPU 717856 → 448737 T внутри банка, 842719 → 517908 T через границу | Принят порог 3 для дальнейшей проверки; это замер одного блока, не всего фильма |
| `min3` | Порог 3 для всех блоков; максимум 1000 кадров на том | Получено 7 TRD; первые три части по 870, 766, 790 кадров прошли, максимум 120,158 мс; четвёртая опустошала AY | Отклонено как полный выпуск |
| `adaptive3` | Порог 3 только при пакете кадра >1400 байт; без принудительного stored | 7 TRD; первые 944, 832, 832 кадра прошли. На кадре 2910 — 238,659 мс и пустая AY-очередь. Отдельная проверка хвоста выявила задержки кадров 3375/3685 и сбой около 4500 | Селективное применение сохранено; разбиение отклонено |
| `split2880` | Добавили границу перед кадром 2880 к `adaptive3` | Собраны 8 TRD; полного прогона Fuse нет | Заменено следующей попыткой; работоспособность не заявляется |
| `balanced` | Порог stored 2600 байт, отдельные stored-блоки, границы 2880 и 4470 | 8 TRD; первые четыре части прошли. На кадре 2932 — 215,087 мс, исчерпание резерва чтения и пустая AY-очередь | Отклонено; нужны дополнительные границы тяжёлых сцен |
| `planned128` | Автоматическое разбиение при расчётном запасе менее 128 секторов | Собраны 17 TRD; первая часть только 689 кадров. Полного прогона Fuse нет | Использовано для выбора границ; как выпуск не принято |
| `dense` | Выбранные границы тяжёлых сцен, длинные спокойные части | Все 14 частей завершили Fuse, но кадр 3008 дал 127,281 мс без ROM, кадр 3715 — 151,743 мс с принудительным чтением | Отклонено по плавности; окончание прогона не равно прохождению проверки |
| `final` | Кадр 3008 принудительно stored; граница длинных частей 3740 | 14 TRD; задержка распаковки убрана, но интервалы на кадрах 3708/3711 достигли 163,780/173,175 мс | Отклонено; название каталога не означает готовый выпуск |
| `repacked` | Граница перенесена с 3740 на 3700 | Проверенные части по 700 и 769 кадров: максимум 120,113/120,161 мс. Всего 15 TRD, одна часть содержит всего 3 кадра | Плавность двух изменённых частей подтверждена; лишняя граница 4472 удалена в следующей попытке |
| `release_disks` | Параметры `repacked` без границы 4472 | Полностью проверены 14 TRD: 4971 экран, 29826 состояний AY, 4957 переключений через шесть полей, отклонение ≤0,264 мс; 124 теста | Принято и опубликовано: `69754f3` |

### Итог принятой попытки

- Первые части: **944, 829, 827 кадров** вместо прежнего ограничения 512.
- Полный фильм: **19 → 14 TRD**. В тяжёлых сценах остаются короткие части.
- Поток с заголовками: **4366047 → 4185622 байта**, экономия 180425 байт.
- PLAYER совпадает с выпуском на 19 TRD: изменение инструкций **0 T**.
  Средняя общая CPU-подготовка выросла 201948,196 → 206423,045 T из-за
  большей доли ZX0; все сроки доставки при этом соблюдены.
- Изображения и исходные AY-байты сохранены. Приближённый синтез по времени
  Fuse: chroma 95,604217%, динамика 98,750218%, F1 атак 80,649926%.
  Это разные технические показатели, не «процент сходства на слух».
- TRD сохранены в корне через LFS; прежние части 15–19 удалены.

Реализация: `cb2e16a` (короткие совпадения), `109effe` (трассы и диагностика),
`5f1283f` (выбор stored для отдельного кадра), `69754f3` (выпуск).

Подробности: [ZX0 и стоимость распаковки](toolkit/ZX0_SPEED_RESULTS_ru.md),
[итог полного фильма](toolkit/FULL_MOVIE_RESULTS_ru.md),
[метрики и хеши](toolkit/full_movie_measurements.json),
[параметры сборки](toolkit/FULL_MOVIE_BUILD_ru.md).
Скрипты: [упаковщик](toolkit/build_fast_sparse_trd.py),
[замер ZX0](toolkit/benchmark_zx0_speed.py),
[Fuse](toolkit/measure_fuse.py), [плавность](toolkit/inspect_frame_cadence.py),
[проверка CPU](toolkit/validate_fast_sparse.py),
[сравнение звука](toolkit/compare_ay_trace.py).

## Предшествующие этапы — восстановлено по сохранённым отчётам

Эти результаты относятся к разным исходным наборам и критериям.
Проверку первых 120 секунд нельзя переносить на весь фильм.

| Попытка | Результат и принятое решение | Подробности |
|---|---|---|
| Анализ мелодии и адаптивный шум AY | На 120 с chroma выросла 85,76% → 94,78%, спектральное сходство 66,28% → 83,08%. Шум добавлен; цель 95% для всех показателей не достигнута | [Сравнение тона/шума](toolkit/AUDIO_FIDELITY_RESULTS_ru.md) |
| Обновление AY 8⅓, 25 и 50 Гц | На 120 с выбран режим 50 Гц от IRQ: chroma 95,652%, динамика 99,324%, F1 атак 75,601%. Применяются только изменения регистров | [Частоты](toolkit/AUDIO_RATE_RESULTS_ru.md), [прерывание](toolkit/AY_INTERRUPT_RESULTS_ru.md) |
| Усиление штрафа за смену нот | F1 атак вырос до 77,592%, но спектральное сходство упало до 84,719%; не принято как однозначное улучшение звука | [Устойчивость нот](toolkit/AUDIO_RATE_RESULTS_ru.md) |
| Блоки ZX0 8192 / 6144 / 4096 байт | На 1000 кадрах вариант 8192 дал 128,549 мс и три интервала >125 мс. Выбраны 6144 байта: 124,641 мс, 979+21 кадр на двух дисках. Это прежний, менее строгий критерий плавности | [Размер блоков](toolkit/AY_BLOCK_SIZE_RESULTS_ru.md) |
| Полный фильм с обычным ZX0; mixed1800; mixed1400 без запаса | Сбои AY перед кадрами 2101, 2903 и 2928 соответственно; варианты отклонены | [Первоначальная полная сборка](toolkit/FULL_MOVIE_BUILD_ru.md) |
| Первый проверенный полный выпуск | Сохранены весь фильм и титры на 30 TRD; упаковка принята по действовавшей тогда проверке | Коммит `aa67ce4`, [сборка и первоначальные параметры](toolkit/FULL_MOVIE_BUILD_ru.md) |
| Эквивалентное представление ячеек для двух TRD | RGB всех 4971 кадров совпали; изменено 1645088 представлений ячеек. Уже 379 из 747 блоков требуют 2121066 байт при бюджете 1291776. Этот вариант остановлен по бюджету; сжатие всего фильма не завершено | [План и ограничение опыта](toolkit/TWO_DISK_ZX0_PLAN_ru.md), [частичный замер](toolkit/equivalent_cells_budget.json) |
| Вывод дельт атрибутов через регистры | На кадре 3375: 138664 → 48266 T, экономия 90398 T. Полный выпуск уменьшен 30 → 19 TRD; каждое переключение через шесть полей, отклонение ≤0,240 мс | Коммиты `4b336be`, `9a43f0f`; [расчёты и полный прогон](toolkit/SMOOTH_CADENCE_RESULTS_ru.md) |
| Плотные 7 и 10 TRD с ускоренным PLAYER | Обычный ZX0 на первых двух томах давал до 144,130 мс, затем пустую AY-очередь; mixed1400 на 10 TRD также опустошал AY. Оба варианта отклонены | [Повторные проверки](toolkit/SMOOTH_CADENCE_RESULTS_ru.md) |

Более ранние оптимизации проигрывателя и их отдельные замеры:
[план скорости](toolkit/PLAYBACK_SPEED_PLAN_ru.md),
[план сжатия](toolkit/COMPRESSION_IMPROVEMENT_PLAN_ru.md),
[потоковый вывод](toolkit/STREAM_DRAWING_RESULTS_ru.md),
[инкрементальная распаковка](toolkit/INCREMENTAL_PLAYBACK_RESULTS_ru.md),
[подготовка следующего пакета](toolkit/PACKET_LOOKAHEAD_RESULTS_ru.md),
[прямой вход из кольцевого буфера](toolkit/DIRECT_INPUT_RESULTS_ru.md),
[переход между банками](toolkit/WRAPPED_INPUT_RESULTS_ru.md).
