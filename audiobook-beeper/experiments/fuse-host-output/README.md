# Fuse host-output investigation, 2026-10-04

The user hears no vibration in either short modeled IMA3/IMA4 WAV, but
reports it when playing the TRD in **the Program Files Fuse**. The listening
defect remains unresolved. Stop treating the codec-control SNR difference
as identification of that symptom.

## Two installations, one generated signal

- `C:/Program Files (x86)/Fuse/fuse.exe`: Fuse 1.9.0, native DirectSound.
- `C:/Work/ZX-video/tools/fuse-1.9.0-sdl/fuse.exe`: Fuse 1.9.0, SDL 1.2.14.

Executable hashes are in each run's `report.json`. The reported disk's
SHA-256 remains `ac4b740ebdcf2f9fb538d286b8ac679df6babc53462cf79b18f08cc8b5a2d66d`.
All runs explicitly select Spectrum 128, Beta 128, 100% speed and 16-bit
host sound. No persisted Fuse, Windows or driver settings were changed.
There was one measured Fuse process at a time. An idle native Fuse launched
for UI inspection was stopped before recording; no pre-existing Fuse was
running when inspection began.

The native window could be listed through Computer Use, but capture did
not show the application and activation failed. Continue through the CLI
and read-only APIs. Test windows are hidden; the SDL run also uses the dummy
**video** driver. This does not reproduce the user's foreground rendering
load. Audio uses a real driver in every measured run, with the dummy audio
environment variable removed. No microphone is used: the recorder asserts
that its endpoint is the default speaker's WASAPI loopback.

Capture the first part from a cold disk boot to its exit, with only entry
and exit breakpoints. FMF stores the internally generated PCM. WASAPI stores
what reaches the Windows render endpoint, after host processing. The exit
can discard the driver's queued final tail. The cross-build equality check
and transfer fit use the first 20 seconds of speech. Local delay estimates
extend through second 22; the fixed-gain residual uses the available aligned
capture with 0.1 seconds removed at each end. It is not a new complete
physical-playback qualification. Reuse the prior full native/Fuse TRD proof.

The two 44.1-kHz builds' generated speech, resampled identically to 48 kHz,
is **byte-exact across 950400 PCM16 samples** (19.8 seconds, excluding 0.1 s
at each end of the 20-s comparison). This supports focusing the investigation
on listening/output conditions rather than replacing three-bit encoding.

## Actual-output measurements

Align the speaker capture to the same run's internal PCM. Analyse 100-ms
speech windows at 48 kHz, searching nearby delay and fitting one amplitude
factor. These are transport diagnostics, **not source/codec SNR**.

| Run | Capture warnings | Window-delay range | Fitted fixed-delay residual |
| --- | ---: | ---: | ---: |
| Native 44.1 kHz | 0 | -1..+1 samples, 0.041667 ms | 9.151110 dB |
| SDL 44.1 kHz | 0 | -1..+1 samples, 0.041667 ms | 9.444765 dB |
| Native 48 kHz, enlarged capture buffer | 0 | -1..0 samples, 0.020833 ms | 8.903659 dB |

There are no large persistent timing slips in these valid captures. Coarse
100-ms windows cannot exclude faster modulation or establish absence of
audible vibration. Delay ranges include the estimator's one-sample rounding.
Do not translate these figures into a claim of zero playback jitter.

The Windows waveform differs substantially in frequency balance and level
from the internal PCM. A 257-tap stationary transfer model trained on seconds
1–10 improves residuals on the separate later interval to 18.384191 dB
(native 44.1), 19.710173 dB (SDL), and 19.668173 dB (native 48). This fit is
diagnostic only: no fitted, gain-adjusted or time-stretched audio is delivered
and no codec acceptance filter changes. Similar results in both builds and
no clear gain from 48 kHz do not support declaring either switch a fix.

Read-only endpoint inspection found registered Realtek stream/mode/endpoint
APOs (`RtkAPOSFX`, `RtkAPOMFX`, `RtkAPOEFX`, `RltkAPOU64.dll`); no explicit
Disable_SysFx property was present. Registration/absence of that flag alone
does not prove which effect is active, or that an APO causes the complaint.
[Microsoft documents](https://learn.microsoft.com/en-us/windows/win32/coreaudio/pkey-audioendpoint-disable-sysfx)
how these system effects can modify shared-mode sound. A controlled effects
bypass and the user's listening identification remain outstanding.

## Listening files

- [Eight seconds of actual native-Fuse Windows output](win32-44100/speaker-first8.wav)
- [Matching internal Fuse PCM](win32-44100/internal-first8.wav)

These files preserve captured level and have no extra listening filter.
Replaying a loopback WAV passes it through the user's output chain again;
it is a diagnostic audition, not a measurement of the loudspeaker's acoustic
output. The user has been asked whether the first file contains the same
symptom. No answer has arrived at this checkpoint.

## Rejected attempt and reporting correction

The initial native 48-kHz capture used a 480-frame (10-ms) recorder buffer
and reported repeated `data discontinuity in recording` warnings. Its
apparent 654-ms drift is **invalid as playback evidence**. Retain its capture
report and rejection decision in `rejected-48000-capture/`. Repeating with a
4800-frame (100-ms) recorder buffer has no warnings and the stable alignment
shown above. This changes recording robustness, not Fuse's output buffering.
`analyze.py` now refuses captures carrying such warnings.

Initial trace parsing expected decimal values, while Fuse emitted hexadecimal
markers; accepting both fixes alignment. SDL redirects debugger stdout
beside its executable rather than into the subprocess pipe; the captured
SDL log was recovered there and the script now handles this explicitly.

The older overlap FMF report marked `host_audio_muted: true` after setting
`SDL_AUDIODRIVER=dummy`. Official 1.9.0 `sound/dxsound.c` and the installed
binary's DirectSound diagnostics show that the native driver ignores that
SDL setting. Withdraw that mute claim and correct `record-first-part.py`
to report it as unverified. Preserve the original JSON as historical
evidence; its audio bytes and execution proof remain valid. Earlier commentary
describing every old recording as using a dummy audio device was also
incorrect for the native build. An internal FMF was never a recording of
Windows speaker output, whether the driver was audible or muted.

The old overlap manifest is refreshed only for its updated README and
recording script; old measurement/binary/audio hashes remain untouched.

## Reproduction

Use Windows and the project Python runtime, with `audiobook-beeper`, `toolkit`
and a workspace-local SoundCard 0.4.6 installation on PYTHONPATH. The package
uses the existing NumPy/CFFI dependencies. No emulator installation is needed.
Run from the worktree root; measured output must use a fresh directory.

```powershell
python audiobook-beeper/experiments/fuse-host-output/capture.py --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output build/native-output
python audiobook-beeper/experiments/fuse-host-output/analyze.py build/native-output --ffmpeg path/to/ffmpeg.exe
python audiobook-beeper/experiments/fuse-host-output/fit-transfer.py build/native-output
python audiobook-beeper/experiments/fuse-host-output/audit.py --replay --ffmpeg path/to/ffmpeg.exe
```

Use the `tools` executable for the SDL control, or add `--frequency 48000`
for the sample-rate control. Recording creates FMF, raw loopback PCM, WAVs
and timestamped progress. Scripts affect no saved audio settings. Keep other
applications silent during capture: loopback contains the endpoint mix.
Original source was inspected from the
[official 1.9.0 archive](https://sourceforge.net/projects/fuse-emulator/files/fuse/1.9.0/fuse-1.9.0.tar.gz/download);
its hash is in `findings.json`.

No Z80 hot-path changes: mean **427.375 T/sample, delta 0 T**, page/bank
extras +14/+140 T; payload, RAM use, modulator and TRD are unchanged.
