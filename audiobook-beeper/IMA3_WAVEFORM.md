# IMA3 waveform disk: 20.071 dB on both full Fuse loops

Measured 2026-10-03. The user's minimum **20-dB final PDM** requirement is
met on the complete original 186880-sample control excerpt, with the same
8-kHz reference and comparison filter. Both complete cold Fuse 128 loops
measure **20.07106694 dB**, versus 18.171/18.153 dB in the previous IMA3 disk.
There is no fitted gain, delay or reference time stretch. This is an
input-specific emulator result, not physical hardware certification or a
claim that all audible artifacts have disappeared.

## Listen and boot

Use [ZX-audiobook-IMA3-waveform-test.trd](../ZX-audiobook-IMA3-waveform-test.trd)
with Spectrum 128 and Beta Disk/TR-DOS, starting from reset. The disk is
independently bootable. Loading and expansion progress are shown, the
loading message disappears, and the complete 23.36-s source loops without
disk reads during playback. [Normal Fuse audio](experiments/ima-3bit-waveform/result-preview.wav)
contains two complete repeats; [the unchanged source](experiments/ima-3bit-waveform/source-preview.wav)
is available for comparison. The older 18-dB disk remains a historical artifact.

TRD SHA256: `5556a64f54ad932e8b65f96f6f55b4bffafae9e5bbec0ba025463fe0c2b34f89`.
Source PCM8 SHA256: `ea3c0d945a0cc349747664c137c3725aee3fe8cf5e17b991ae3e24f51829a304`.

## Encoding change, unchanged decoder cost

The PC beam search now supports the exact three-bit IMA alphabet
`0,2,4,6,8,10,12,14`. It minimizes filtered PDM waveform error on the pilot's
measured pulse schedule, retaining predictor/index, PDM feedback and filter
state. The selected search uses width 32, 64-sample blocks and regularization
0.1 toward the timing-compensated PCM. The final 128-sample silence guard
uses the same restricted alphabet and ends exactly at predictor/index 0/0.
No source samples are removed, rescaled or replaced for acceptance.

The wider host search was started while the full width-32 disk check was
pending. It is preserved as an **unverified candidate**, not substituted
for a real disk measurement:

| Search | Host score on pilot schedule | New disk, two full cold loops |
|---|---:|---:|
| Width 32, weight 0.1 | 20.208549 dB | **20.071067 / 20.071067 dB** |
| Width 128, weight 0.1 | 20.518986 dB | Not built or executed |

Storage remains 70080 IMA3 audio bytes (70144 after sector padding),
expanded to 93440 resident IMA bytes. This is **5.333:1 audio compression
relative to PCM16**, with all decoder/framing overhead reported separately.
The complete bootable disk occupies 473 file sectors in a standard
655360-byte TRD. All 131072 RAM bytes remain accounted for, with no unused
resident audio capacity and no full PCM or PDM buffer.

Playback is still **423 T per ordinary sample**, +14 T at a page boundary
and +140 T at a bank boundary, all **delta 0 T**. No Z80 player or expansion
instruction is changed. Calibration selects 1273 balanced silent pairs
and a 69-T pad, replacing the previous 67-T pad. Thus the deterministic
native cycle changes **79122530 -> 79122532 T**, delta **+2 T**, entirely
inside the silent boundary. Expansion remains **285 T/eight samples**,
6896434 T total native preload CPU work, delta **0 T** from the earlier disk.

## Completed verification and preparation limit

The user now allows **60 seconds**, superseding the earlier 39.903992-s
limit, and permits subsequent decoder optimization. The verification API
accepts that explicit limit while preserving the original raw128 benchmark.
No favorable relabelling of CPU time as whole startup time is used:

- Cold Fuse expansion: **1.934749 s**; compressed-data ROM reads: **11.045818 s**.
- Preloader entry to player-ready: **18.683671 s**, including later player/table loads.
- Normal-speed capture, reset/boot to first audio: **27.254263 s**, below 60 s.
- Complete Fuse cycle: **82891452 T** in each repeat, exactly 1169 fields.
  Phase deltas are **0/0 T**; mean speed error is **-0.043271%**, within 2%.

Native and cold Fuse playback each verify all **5985253 PDM outputs** and
**373760 predictor/index samples** across both loops. RAM guards, bank
latches, loading display and zero runtime disk reads pass. Separate native
and real-ROM preload checks verify every expanded byte and all 32 steps
of both progress bars. FFmpeg independently verifies every IMA sample.
Normal recording observes both wraps, matching latches and continuous
audio activity. Physical hardware has not been tested.

The comparison retains the established 192-kHz pulse integration and
`highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2` at 44.1 kHz, excluding
the same 0.1-s measurement edges. The margin above 20 dB is only 0.071 dB;
do not round this into a claim of a large margin or transparency.

[Alphabet regression checks](experiments/ima-3bit-waveform/alphabet-check.json)
confirm byte-identical default four-bit behavior on the saved fixtures,
agreement with the independent three-bit recurrence, exact silent settling
from seven nonzero/extreme seeds and rejection of invalid alphabets.
[Completion audit](experiments/ima-3bit-waveform/completion-audit.json),
[full results](experiments/ima-3bit-waveform/report.json), source snapshots,
assembly, timelines, recordings and artifact hashes are saved together.
Large raw trace/capture files remain locally under their recorded hashes.

## Reproduction

Use the project Python dependencies, `audiobook-beeper` and `toolkit` on
PYTHONPATH, OPENBLAS_NUM_THREADS=1, and materialized LFS input files.
Keep output directories separate from the saved evidence.

```powershell
python audiobook-beeper/verify_ima_alphabet.py --pilot audiobook-beeper/experiments/ima-3bit-preload --output build/alphabet-check.json
python audiobook-beeper/ima_waveform_encoder.py --input audiobook-beeper/experiments/ima-3bit-preload --output build/ima3-waveform --ima3 --width 32 --ffmpeg <ffmpeg.exe>
python audiobook-beeper/verify_waveform_disk.py --pilot audiobook-beeper/experiments/ima-3bit-preload --encoded build/ima3-waveform --output build/ima3-waveform-disk --ima3 --maximum-preparation-seconds 60 --fuse <fuse.exe> --ffmpeg <ffmpeg.exe> --record
```

The assembler still compiles the separate listings; Python packages their
binaries. The original four-bit encoder and verifier remain the defaults
when `--ima3` is omitted.
