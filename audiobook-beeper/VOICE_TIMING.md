# Voice flutter: updated quality requirement

On 2026-10-03 the user heard trembling in the voice during the Fuse audio
capture, after requiring playback speed within +/-2%. The direct player
meets the mean and 0.1-second speed checks, but these checks hide periodic
speed variation inside a 50-Hz field. **Do not declare the 20-dB goal met
using the older warped-clock reference.** The goal remains active.

## Verified candidate and the measurement gap

The bounded [table probe](probe_packet_contention.py) reuses the full direct
player's measured output timeline. Mean interval weighting raises the host
estimate to about 19.93 dB. Round those weights to eighth-T units and reduce
the two stored recent-error representatives from +/-0.5 to **+/-0.25**:
the estimate becomes 20.0857 dB. Beta remains 0.5. The 18-state closure is
unchanged, and 122/86 code patterns fit the same resident reserve. A larger
recent extent and other beta values were inferior or required too much RAM.
[Full probe](experiments/ima-direct-weighted/table-probe.json).

The measured model is an opt-in `--measured-model` argument, with the same
complete original PCM8 and IMA bytes. The ASM hot path is unchanged: 423 T
per sample, 79056232 T/loop, **zero timing delta** from the direct baseline.
Full native and cold Fuse checks pass two loops, 5980161 bits and 373760
predictors/indices, paging, protected native RAM and the loading message.
Both cycles pass 20 dB under the old measurement (minimum **20.08555 dB**).
Normal-speed sound capture and independent FFmpeg decoding also pass.

That old measurement lets the reference follow every actual sample
boundary. It isolates modulation/codec error, but removes sample-clock
flutter from the error signal. The user's observation exposes this as an
insufficient end-to-end voice-quality criterion.

## Clock-aware diagnosis

[Analyzer](analyze_voice_jitter.py) uses the full first loop, the same source
and listening filter, and a uniform reference clock at the measured mean
rate. This retains the permitted overall speed offset, while exposing
within-frame acceleration/deceleration. The first sample anchors phase;
there is no audio correlation, fitted phase, fitted gain or audio-dependent
alignment. Both references exclude the established 0.1-second edges.

The candidate has **8.4298 dB** total SNR against that fixed clock, versus
20.0856 dB against its warped clock. Warping the source alone gives 8.5984 dB.
Clock residual ranges from **-0.2614 to +0.2005 ms**, peak-to-peak 0.4618 ms,
standard deviation 0.1057 ms. Its 50-Hz component has 0.0910-ms amplitude.
Five-millisecond windows range from **7657 to 8385 samples/s** even though
the whole-loop mean is 8003.31. This is strong evidence for the reported
flutter, not proof that every audible artifact has the same cause.

[Full diagnostic](experiments/ima-direct-weighted/voice-jitter.json),
[uniform-clock reference](experiments/ima-direct-weighted/uniform-clock-source-preview.wav),
[clock-warped source alone](experiments/ima-direct-weighted/warped-clock-source-preview.wav),
[actual candidate WAV](experiments/ima-direct-weighted/result-preview.wav).

The candidate remains archived, **not promoted to the root TRD**. The
root direct TRD still points to the previous 18.8455-dB experiment, which
also must not be called a flutter-free or accepted final player. No physical
computer was measured. The next work must stabilize effective sample timing
or validate compensation against an independently measured new timeline,
preserving source duration/content and the +/-2% requirement. A host-only
resampling result is not a completed hardware solution.

## Reproduction

```powershell
python audiobook-beeper/build_direct.py --output build/ima-direct-weighted --measured-model --fuse <fuse.exe> --ffmpeg <ffmpeg.exe>
python audiobook-beeper/analyze_voice_jitter.py build/ima-direct-weighted --ffmpeg <ffmpeg.exe>
```

The initial diagnostic probe selected ordinary samples using slot 15 from
the older kernel. Direct playback's page extension is on slot 14. Correct
that filter and rerun the bounded probe. Rounded weights and the selected
candidate remain unchanged; the retained prior probe is marked superseded.
