# YM3812 nine-channel speech simulation

Completed 2026-10-13 in `.worktree/ym3812-speech`, branch
`codex/ym3812-speech`, from `86b959f9`. Reuse the exact prepared O. Henry
source[60,90). All preview samples come from real OPL2 register/wait streams
rendered by ymfm-py0.2.0. Source PCM supplies fitting targets only.

- **[Selected 30-second YM3812 audition](evidence/ym3812-preview.wav)**
- **[Six voices 0..30 s, silence, YM3812 31..61 s](evidence/six-versus-ym3812.wav)**
- [Four-waveform alternative](evidence/waveforms-alternative.wav)
- [Two-operator FM alternative](evidence/fm-alternative.wav)
- [Exact prepared source](evidence/reference.wav)
- [VGM commands](evidence/ym3812.vgm), [compressed VGZ](evidence/ym3812.vgz)
- [Complete spectrogram comparison](evidence/spectrogram-full.png)
- [Detail2.56..5.56 seconds](evidence/spectrogram-detail.png)
- [Four-waveform comparison](evidence/waveforms-spectrogram.png)
- [All eight trials, metrics and replay/hash proof](evidence/report.json)
- [Five independent tests](evidence/tests.log)

## Chip constraints and fitting

YM3812 has nine melodic FM channels, each with two operators. These are
controllable voices, not nine fixed filter bands. The operators share a
channel F-number/block; their multipliers set relative frequencies. Four
OPL2 waveforms are sine, positive half sine, absolute sine and alternating
positive quarter sine. Keep nine melodic channels; rhythm, CSM, AM and
vibrato are disabled in this bounded experiment.

Clock3579545 Hz gives a native rate of clock/72=49715.902777... Hz. F-number
1..1023/block0..7 with multiplier1 reaches about6208.79 Hz. The first four
trials use multiplier1. Independent tests expose this limit; four more
trials add legal multiplier2 carriers and double matching modulator ratios
to cover the upper speech band. Tests include an actual approximately
7900-Hz tone and native0.75-dB total-level steps.

The initial fourteen patches contain four carrier shapes with modulator
TL63, and ten sine-carrier FM patches with modulator ratios1/2/3 and TL16..40.
The expanded bank adds fourteen multiplier2 versions. The selected audition
uses nine sine carriers with strongly attenuated modulators; residual
modulation, envelopes, phase and YM3014-style DAC quantization remain in the
emulator output. They are not ideal mathematical sine oscillators. Saved
level64 means key-off; real TL writes remain0..63.

Measure integer-cycle steady chip harmonics, build512-Hann templates and fit
nine components per20-ms target with source-only inverse magnitude weights
and extra speech-band peaks. Exact512-subset channel assignment maintains
nearby frequencies on the same voice. Evaluate full continuous chip audio,
not just template scores. No global optimum is claimed.

Timed VGM writes are two44.1-kHz samples apart (45.35us), covering the
documented12-clock address/84-clock data waits. Silent initialization is
loaded before timed playback and represented by zero-time initial writes.
The experimental4-step TL ramps are real register writes around4 ms, with
serial staggering; there is no PCM interpolation or source addition.

## Results and selection

The log-only winner is `mult1/waveforms`, objective6.593306 dB. However,
10.912983% of its output power lies below50 Hz, and medium/long dominant
cosine worsens versus the six-voice model. Changing positive-waveform means
create low-frequency control DC despite ordinary AC coupling. All waveform/
FM variants have about9..11% sub50-Hz power here.

The initial strict guard requiring both ordinary and root-magnitude cosine
improvements at all scales rejects all eight candidates. Retain that failed
selection attempt. For the requested chip audition, use an explicitly
narrower guard: dominant cosine improves at all scales, level MAE improves,
and sub50-Hz power stays below1%; then select the lowest objective. This
chooses **`mult12/sine`**. Strong partials and dynamics improve, but some quiet
short-window details worsen. Overall spectral superiority is not established.

Actual saved PCM16 results on the identical source/time grid:

| Metric | Accepted six voices | Selected YM3812 |
| --- | ---: | ---: |
| Magnitude cosine512/2048/8192 | 0.899120/0.848475/0.864305 | **0.944152/0.899093/0.903570** |
| Root cosine512/2048/8192 | 0.914079/0.901872/0.920446 | 0.899614/0.920404/0.929875 |
|20-ms level MAE,dB | 0.789174 | **0.304720** |
| Combined log/level objective,dB | **6.771566** | 7.242039 |
| Masked spectral MAE512/2048/8192,dB | 7.137307/6.399630/5.949129 | 9.008251/6.466209/5.931700 |
| Power below50 Hz | 0.137689% | **0.030281%** |

Common-scale plots show dominant partials more clearly, with missing quiet
harmonics and broadband consonant texture. Detail selection comes from the
previous six-voice output. No panel normalization, time/pitch warp or local
PCM gain envelope is applied. More elaborate FM patches and TL ramps did not
improve this bounded balance; the chip's full FM/additive/rhythm/CSM capability
is not exhausted. Listening acceptance/intelligibility grading are pending.

## Verification, storage and reproduction

Selected WAV:1323000 samples, peak0.892415, zero clipping. All eight native
streams have zero chip clipping. Playback uses fixed20-Hz AC coupling and
an8-kHz129-tap fractional sinc filter plus constant gain2.3357702813587116.
This is an explicit playback chain. VGM in another player may need a volume
adjustment and uses that player's filtering.

All8*1500 channel states pass independent VGM audits of frequency, level,
multiplier, key, waveform, FM settings and timing. Every controls-only export
matches its stored VGM; all1491477-native/1323000-output-sample WAV replays
are byte-exact. No PCM/DAC/data-block commands occur. Five tests cover native
frequency/TL steps, multiplier2, four shapes, nine channels, timing/replay
and invalid streams. The61-second comparison contains exact PCM segments.
Source/core/producer/media hashes, all VGZ/controls and the original producer
snapshot are retained.

Selected commands:39128 writes, **161158 VGM bytes /61653 VGZ bytes for30 s**.
Generic VGM command/timing overhead differs from the earlier compact
hypothetical PSG format. This is not an optimized Z80 storage/decoder format.

Dependency: [ymfm-py0.2.0](https://pypi.org/project/ymfm-py/0.2.0/) wrapping
[Aaron Giles' BSD-licensed ymfm](https://github.com/aaronsgiles/ymfm).
Windows CPython3.12 wheel SHA256:
`0835b4e5b0c2c90440d19463704055994a3499276637a05e36069ec8b8ed5a3e`.
The loaded-core hash is in the reports. The core does not promise silicon
pipeline identity. A negative test found that pinned0.2.0 ignores wave-select
disable gating; every exported stream explicitly sets01h=20h, so this unused
limitation does not affect the auditions. Physical-chip playback, native
Z80/DOS delivery and release disks are unqualified. Existing six-voice/native
code remains unchanged; no player hot-path cycle delta applies.

From this worktree with NumPy/Pillow:

```powershell
python -m pip install --no-deps --target .tmp/dependencies/ymfm ymfm-py==0.2.0
$env:PYTHONPATH=(Resolve-Path .tmp/dependencies/ymfm).Path
$env:OPENBLAS_NUM_THREADS='1'
python ay-converter/experimental_ym3812.py ay-converter/analysis/six_voice_spectral/evidence/reference.wav --legacy-sine-transitions --output .tmp/ym3812-reproduction
python -m unittest discover -s ay-converter -p test_experimental_ym3812.py -v
```

Use a new output directory. This regenerates the expanded four trials. The
original archive's producer-hash assertion uses revision `60e8bb3e`; use that
revision for its exact historical provenance. Current sine exports default to
the [subsequent click-reduction experiment](../ym3812_clicks/README.md).
The legacy flag above preserves the original register/audio streams. The
initial producer's exact snapshot is `evidence/trials/mult1/producer.py.gz`;
its hash matches its manifest. Rejected media replay from retained VGZ/gain
using `experimental_ym3812.replay()`/`playback()`. `archive.py` verifies both
stages and creates the auditions/plots. The bounded deliverable is complete.

References: [Yamaha datasheet](https://www.ardent-tool.com/datasheets/Yamaha_YM3812.pdf),
[Yamaha application manual](https://c64.xentax.com/media/Yamaha_YM3812_Application_Manual.pdf),
[VGM1.71 specification](https://github.com/vgmrips/vgmplay-legacy/blob/master/VGMPlay/vgmspec171.txt).
