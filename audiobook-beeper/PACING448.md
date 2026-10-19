# Optional448-T audio pacing research

2026-10-19. This experiment is complete and **rejected as an unconditional
quality update**. The source-independent audio goal remains active. The
delivered `ZX-music-Sea-Foam-SNR20-RAM-auto.trd` stays at SHA256
`b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e`.
The old449-T defaults, source gain/bandwidth/content and original Python/C
encoders are preserved. Nothing is promoted into the main checkout.

## Mechanism and automatic conversion

An opt-in continuous-player setting shortens Pentagon slot7 by one T state.
Four NOPs16 T become `LD A,R`9 T plus `INC HL`6 T; dead A/F/HL are overwritten
before meaningful use. The six-byte stub and all later addresses stay fixed.
Pentagon ordinary work449 ->448 T; Spectrum128/Scorpion stay423 T. Page extra
14 T and bank extras243/267 T remain. This is not an exactly uniform8-kHz
transport: the sparse page/bank work is still present.

```powershell
python audiobook-beeper/convert_snr_audio.py prepared.wav --prepared-pcm `
  --output output/research448 --pentagon-ordinary-tstates 448 `
  --audio-progress-ui
```

The default is449. `--encoder python` retains the original executable
reference; C and Python448 conversions produce identical complete UI disks.
The legacy quality baseline keeps its own449 clock, rather than being
silently accelerated to448. Invalid settings fail before output creation.
The UI retains its existing short-source guard: more than two live progress
cells per bank handoff is rejected. Do not remove that guard to make a short
test pass; omit the UI explicitly when required by source length.

The causal control deliberately retains the original449-T **table-generation
weights** with beta0.5, extent0.5 and zero PCM origin. The waveform encoder
reoptimizes compressed IMA data on the448 physical schedule using the same
beam32/horizon128/commit64/regularization0.1 settings for every input. This
does not claim that the compressed payload is unchanged or that the table
has become a full second-order sigma-delta modulator.

[Instruction/register/default proof](experiments/song-snr/evidence/pacing448-player/README.md)
includes all literal paths, both tail bits, clone paths and maximum cold load.
[Automatic converter tests](experiments/song-snr/evidence/pacing448-cli/tests.log)
separately verify own-clock baseline scoring and C/Python disk parity.

## Complete corpus results

The nine authenticated original sources and six longer generated controls
use the original uniform8-kHz reference, unchanged continuous f64 listening
filter (70-Hz high-pass and two two-pole4500-Hz low-pass sections),768-kHz
area integration and fixed100-ms edge exclusions. No gain, delay or clock is
fitted to source content. All nine archived449-T scores reproduce exactly.
The common frequencies include counted page/search/commit/bank rates; fits
remain diagnostics and never correct the listening signal or SNR.

| Complete original source |449-T joint SNR,dB|448-T joint SNR,dB|
|---|---:|---:|
|Sea-foam song|20.250316|20.300560|
|Speech|21.692334|21.974302|
|Entertainer|19.445475|19.673120|
|Quiet440|5.185187|5.271277|
|Quiet997|-2.370523|-1.661483|
|Loud3000|8.155355|8.047531|
|Steps|2.616812|3.490545|
|Multitone|17.327370|17.211823|

Silence has no SNR. Short silence worsens0.0154867382 ->0.0167859769 absolute
error RMS. Its strongest line moves3990.97 ->3999.77 Hz; the latter's three
bins contain97.64% of spectral error power. The six longer controls contain
131072 source samples plus512 silent guard samples (16.448 s), covering more
than three bank cycles. Their prefixes match the original generated sources
exactly. All six improve SNR or absolute silence RMS; long silence improves
0.0156580822 ->0.0118114206, with its strongest line near2663.92 Hz.
Neither result proves absence of added background on arbitrary source lengths.

Across15 whole sources there are two SNR and three RMS regressions,50 AM,
48 delay and25 coherent-line numerical increases, and63 inconclusive
modulation comparisons. These are arithmetic disclosures, not invented
audibility thresholds. Long quiet997 spans enough bank cycles but its phase
tracking remains unreliable; a fitted modulation number is not proof that
flutter is absent. Source-dependent winner parameters were not selected.

The song improves0.050244285 dB over the existing joint preview; its absolute
error RMS improves0.041914 dB. Each own-clock rendering includes its own
endpoint/guard duration, explaining the small difference between these two
figures. The gain versus the authenticated legacy449 baseline-3.085228288 dB
is23.385788460 dB. Passing that scalar target does not waive background,
modulation, generality or complete-execution requirements.

[All15 host controls, diagnostics and source identities](experiments/song-snr/evidence/pacing448-control/report.json),
[independent full-band and ideal-DAC controls](experiments/song-snr/evidence/pacing448-spectrum/report.json).
Even the ideal unquantized multilevel control for loud3000 scores only
7.934648 dB at448 versus8.192982 dB at449; over99.997% of its448 error lies
above4 kHz. This counterfactual isolates remaining clock/reconstruction
images. It is not an executed player or an upper bound on joint error
cancellation. One T of average correction does not remove page/bank timing.

## Complete player execution and limits

[Execution evidence](experiments/song-snr/evidence/pacing448-execution/report.json)
contains12 complete native runs and four independent complete cold installed-
Fuse runs: the whole song on512/1024, and long silence/quiet997 on512. The
native runs check all four memory profiles for those three complete sources.
The short generated controls explicitly omit UI; their rejected UI build is
preserved. The song retains its cartoon cover,92 correct loading phases and
22 exact global-prefix green updates on both Pentagon profiles.

Each full song run checks11,526,111 source pulses and720,382 predictor/index
states. Every timestamp equals an independently counted448-T schedule;
maximum error is0 T. Both actual-clock scores equal20.300560171997017 dB.
Source clock SHA256 is
`0337838e3cb284581afe82d53930e8293c766c8706f8efeb7a65819a90dd72b5`.
Pentagon512/1024 perform no refills or live ROM reads; the longest continuous
hold remains277 T. The average measured rate is7999.387078 Hz. The physical
clock remains nonuniform, with approximately6.90 ms of accumulated drift
over the song. Native128/Scorpion retain three/one explicit insufficient-RAM
refills and do not establish those clones' waveform quality or physical ULA
timing. Actual whole-corpus and real-hardware quality are not claimed.

Research song TRD:
`experiments/song-snr/evidence/pacing448-execution/sea_foam/audio.trd`, SHA256
`ca50e30027921240286d7ecd9624e9d9f53e04e2113e20931420a290fdfbf35e`.
It is a saved rejected control, not a replacement for the delivered image.

Reproduce with the project's installed Python dependencies, C compiler,
FFmpeg and pinned installed Fuse:

```powershell
python audiobook-beeper/experiments/song-snr/pacing448_control.py `
  audiobook-beeper/experiments/song-snr/evidence `
  --output .tmp/reproduce448-host --scratch .tmp/reproduce448-cache
python audiobook-beeper/experiments/song-snr/pacing448_execute.py `
  --inputs .tmp/reproduce448-host --output .tmp/reproduce448-execution `
  --source sea_foam --scratch .tmp/reproduce448-fuse
```

The full host fingerprint and per-source seals reject stale resumes. Raw
unscaled arrays remain an ignored, reproducible cache; saved source PCM,
compressed streams, producer snapshots, complete pulse clocks, reports and
listening WAVs authenticate the experiment. The user's next steering is to
pass the full reconstructed16-bit predictor into SDM, rather than reducing
it to the current64 modulation-input levels. This needs actual lower-bit
influence plus a new CPU/table/RAM proof; a16-bit host container alone does
not implement it. Keep precision, modulation order and remaining clock/idle
error as distinct measured mechanisms. Do not repeat the prior low-gain/
low-precision SD2 port, widen a
beam without a new mechanism, or mark the broader goal complete.
