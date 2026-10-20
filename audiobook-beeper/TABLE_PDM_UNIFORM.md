# Uniform table PDM investigation

On 2026-10-20 the user requested trying faster table output and equal PDM
intervals. The experiment preserves the original sources, IMA disk storage,
original C/Python encoders and delivered disk. It implements new isolated
native components and a common C encoding preset. It does not yet deliver a
replacement bootable player.

## Counted native output

The existing Pentagon player emits sixteen decisions over an ordinary
449-T sample, approximately127714.92 decisions/s at3.584MHz. Its holds are
`36,28,28,31,24,26,22,46,22,26,22,30,31,27,34,16` T; page/bank paths add
14/243 T. The new resident-PCM8 component emits sixteen decisions at exactly
28-T intervals:448 T per sample, exactly8kHz/128kHz on that CPU clock.
The ordinary period changes by-1 T. The main improvement is uniformity;
doubling the decision rate to256kHz is not implemented.

[`table_pdm_uniform16.py`](experiments/song-snr/table_pdm_uniform16.py)
generates the assembly and table image. It keeps the existing integral table
algorithm with64 input levels, beta0.5, extent0.5 and zero-origin input.
Uniform timing closes to six feedback states, with97 FIRST and88 SECOND
patterns. It avoids indexed14-T POP and15-T ADD instructions that cannot fit
the available16/17-T spaces. Cross-register copies to IY explicitly use A;
the prefixed H/L self-copy encodings are not mistaken for those transfers.

Actual native execution verifies all256 PCM8 values times six reachable
states and a16383-sample varied trajectory through63 source-page crossings:
286704 speaker outputs, every hold28 T. Every bit, state, next pointer,
source cursor, register guard and unchanged-RAM check passes. Code8132B,
lookup allocation16384B (2304B used), map256B, total24772B for this component.
The counted packet is189 T in output instructions,139 T useful work and
120 T padding, totaling448. It reads resident PCM8; it omits live IMA decode.
Thus the-1-T period comparison is not a claim of equivalent compressed-player
CPU savings. No16-bit input-precision improvement is claimed.

[Native report and generated timing ledger](experiments/song-snr/evidence/table-pdm-uniform16-component/README.md).

## Paging without stretching speaker intervals

[`table_pdm_uniform16_bank.py`](experiments/song-snr/table_pdm_uniform16_bank.py)
implements a separate counted paging component. A short sequence uses
immediate speaker writes while the alternate port registers prepare7FFD,
then returns to the normal register-output form. The memory-port write is
separate from speaker output; no even-port alias changes border/MIC values.
The physical work is distributed across existing pulse intervals.

2097280 native cases cover all128 seven-bit speaker patterns,256 paging bytes
and64 source high bytes, plus main-port guard cases. All14680960 speaker
writes have28-T spacing;2097280 additional writes target7FFD. The main
register pairs, IX/IY/SP, alternate HL/AF and I survive. Six intervals total
168 T, and the entire standalone fragment including entry output/exit jump
is190 T. These counts do not prove a complete448-T banked sample or dynamic
descriptor reader. The source byte and delta must already be consumed.

The first quick harness stopped on an intermediate emulator frame event;
the failed attempt is retained. The corrected harness resumes those events.
A later manifest audit detected README added after the initial six-artifact
index. The original manifest is preserved and the final index covers README
and that original. No native result was changed by the indexing correction.

[Paging proof](experiments/song-snr/evidence/table-pdm-uniform16-bank-component/README.md),
[initial harness attempt](experiments/song-snr/evidence/table-pdm-uniform16-bank-component-attempt-1/manifest.json).

### Integrated static two-bank component

[`table_pdm_uniform16_paged.py`](experiments/song-snr/table_pdm_uniform16_paged.py)
then integrates static paging with the table output. SECOND variants include
the successor state, reducing records to four bytes. A self-modified jump
replaces the IY pointer copies; only194 documented fixed-RAM operand bytes
may be written. Alternate HL provides the constant speaker value and port
restoration byte, so the source cursor and next lookup remain live during
the bank bridge. IY and IX are preserved. The generated code documents all
slot counts and register lifetimes.

1536 forced-bank input/state cases and a32766-sample trajectory across126
ordinary pages plus a real emulated bank0-to-bank1 map change pass. All
647136 speaker writes have28-T spacing; all sample periods are448T. Bits,
states and source order agree with the same table model used by the host.
This kernel is15346B, with97 FIRST/151 specialized SECOND variants. Adding
the existing16-KiB lookup allocation and256B map gives31986B before any
boot/loader/UI/workspace ledger; only1536 lookup bytes contain records.

The first attempt ran the guard throughFFFF and looked ahead beyond the
second bank before EOF. It is preserved. The successful fixture stops with
FFFE as the valid lookahead guard, explicitly leaving real EOF unproved.
There is one static handoff, not a dynamic whole-song descriptor sequence.
[Two-bank native evidence](experiments/song-snr/evidence/table-pdm-uniform16-paged-component/report.json).
An additional1536-case boundary supplement exercises all384 effective
PCM-level/state cells directly at the bank decision, adding122880 checked
speaker outputs. Combined paged coverage is770016 outputs. Its historical
reference to the initial component manifest remains verifiable from the
retained `initial-manifest.json`.
[Boundary supplement](experiments/song-snr/evidence/table-pdm-uniform16-paged-boundaries/report.json).

## Source-clock and host controls

The renderer measures time in3546900 reference ticks/s, while the native
Pentagon uses3584000 CPU T/s. The correct uniform boundaries are
`arange(N+1) * reference_CPU/8000` for PCM and
`arange(16*N+1) * reference_CPU/128000` for PDM. This is a conversion between
known physical clocks, not a source-specific fitted clock.

The first complete nine-source host run incorrectly passed native28/448 T
directly to the renderer, producing7917.1875Hz while labelling it8kHz.
That complete attempt and producer remain under `table-pdm-uniform16-host`
and are invalid for the canonical8k quality claim. Its C decoded samples,
words and states were valid. The corrected `host-8k` run authenticates every
old artifact and reuses identical C outputs, rerendering only at the correct
clock. No encoding is repeated. The corrected frozen-IMA song scores
21.193927344 dB total and28.422342677 dB relative to decoded IMA.

These frozen controls use the canonical uniform8k IMA files from
`general/inputs`, not the old449-clock compensated payloads. Replaying those
compensated payloads on a new clock would be a mismatched control.

[`table_pdm_uniform16_host.c`](experiments/song-snr/table_pdm_uniform16_host.c)
decodes complete IMA and generates table words/states in C. Every decoded
predictor, word and carried state matches the independent Python reference.
The full predictor is retained until the same64-level output quantization.
This C host operation does not prove concurrent IMA decoding by the Z80.

## Matched common C encoding

[`table_pdm_uniform16_encode.py`](experiments/song-snr/table_pdm_uniform16_encode.py)
uses the unchanged standalone C waveform encoder with one frozen preset:
beam32, horizon128, commit64, regularization0.1 and the uniform table above.
All nine whole sources total1195520 samples. Encoding priors exactly equal
the original PCM8 source; no content, gain or bandwidth is changed. Every
stream has zero clipping and finishes with predictor/index0/0. The original
128-sample silent guards remain; they hide no source content. Search-query
grid quantization is at most1.652ns and is distinct from physical clocks.

The whole song keeps360192 IMA bytes and takes35.661 seconds to encode
including model/workset preparation. All nine conversions total65.514s.
These are encoding measurements, not full conversion/bootable-TRD times.

The matched host quality run uses the unchanged f64 listening filter,
768kHz integration, fixed100ms edges and no fitted gain/delay/clock.
Old449 results below retain their own original instruction-derived clocks;
the new result has the uniform physical8k clock. Each keeps its complete
original source reference. Most old short-source rows are host predictions;
the delivered song's prior20.2503-dB result also has complete player/Fuse proof.
Every new row remains a host counterfactual until integrated execution.

| Complete source | Previous449 SNR, dB | Uniform matched SNR, dB | Change, dB |
| --- | ---: | ---: | ---: |
| Song |20.250316|22.781483|+2.531167|
| Quiet440 |5.185187|5.564858|+0.379672|
| Quiet997 |-2.370523|0.866545|+3.237068|
| Loud3000 |8.155355|19.989988|+11.834633|
| Steps |2.616812|2.100536|-0.516276|
| Multitone |17.327370|21.624793|+4.297423|
| Speech |21.692334|23.817786|+2.125452|
| Entertainer |19.445475|21.567557|+2.122083|

Silence has zero reference power, so no SNR is reported. Absolute filtered
error RMS changes from0.0154867382 to1.86113681e-9 in this flat-clock model.
This scalar does not prove real hardware silence or absence of all artifacts.
Matched song PDM-only SNR is28.561539782 dB. The steps regression and the
remaining weak quiet-tone scores must remain visible; the preset is not an
unconditionally accepted general-source update.

[Matched C encodes](experiments/song-snr/evidence/table-pdm-uniform16-matched/report.json),
[complete matched quality](experiments/song-snr/evidence/table-pdm-uniform16-matched-quality/report.json),
[canonical/native audit](experiments/song-snr/evidence/table-pdm-uniform16-audit/report.json).

The [matched quality audit](experiments/song-snr/evidence/table-pdm-uniform16-quality-audit/README.md)
authenticates171 input artifacts and retains35 audit artifacts. It also compares
canonical frozen IMA against matched IMA on the same uniform clock, using
cached f64 arrays without reencoding or filtering again. Song SNR improves
by1.587556 dB in that separate comparison. All eight non-silent SNR/RMS pairs
improve, but fitted diagnostic indicators have27 AM,21 linearized-delay and
17 coherent-line numerical increases;42 fits are inconclusive. Song alone
has6/3/1 such increases. These are signal-error diagnostics, not proof of CPU
clock jitter or confirmed audible flutter. Quiet440/997 phase tracking is
unreliable because fundamental fractions are only0.7656/0.6477. No artifact
acceptance follows from the SNR or perfect component pulse clocks.

The host wrapper's later `--packed-dir` input option was added after the
canonical controls. Each before/after producer version is retained in its
own archive; those historical snapshots are not silently replaced by the
latest source. The C output algorithm and corrected clock/filter are common.

## Integration limits

The verified resident-PCM8 route requires720384 audio bytes for the song.
It is plausible on Pentagon1024, before a full code/screen/loader/RAM map,
and does not fit fully resident in512K. The compressed IMA disk representation
remains360192B. A general loader/player must preserve the existing per-machine
boot, cover, progress and fallback behavior. Adding the full IMA decoder to
the exact16-gap schedule is not yet proved. Neither the separate paging
primitive, the static two-bank fixture nor the host clock may be substituted
for actual complete playback.

Current delivered disk SHA256 remains
`b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e`.
No new TRD is promoted. The22.7815-dB result is a useful candidate, not a
verified22-dB player or completed noise/artifact goal.

The [final independent audit](experiments/song-snr/evidence/table-pdm-uniform16-final-audit/README.md)
authenticates301 artifacts across13 retained evidence sets, including failed
attempts and historical producers. All384 specialized paged records compose
the same model as the host; the524256 trajectory bits/timestamps and both
1536-case boundary collections are independently replayed from saved inputs,
without repeating native execution, C encoding or filtering. Nine original
C/Python/player files match55b0f007 byte for byte; both main TRDs retain their
baseline LFS identities. This audit does not extend the physical scope of
the native fixtures or turn the host score into a release measurement.
