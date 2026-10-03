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

## Bounded source compensation: first loop improves, repeat still fails

The [offline probe](precompensate_voice.py) reconstructs the original PCM8
with radius-16 Lanczos interpolation at the measured sample-hold centers,
then re-encodes with the existing beam-32 IMA encoder. The original source
remains the quality reference; the compensated PCM is a separate file. All
186880 samples and 93440 compressed bytes remain present. Freeze the pilot's
25 hot IMA rows to avoid changing the memory layout while compensating.
There are no ASM instruction changes: 423 T/sample, 79056232 T/loop,
zero native timing delta. The source already ends with 128 silence samples;
retain these and verify terminal predictor/index 0/0.

The old-timeline host estimate is **19.5984 dB**. Two full native and cold
Fuse loops again verify every bit, predictor/index, paging, loading UI and
native RAM/timing. The independently measured first loop scores **19.6064
dB**, but the second only **13.8469 dB**. Long-term speed is still within
0.043% of 8 kHz. Compensation works for the calibrated phase, but a loop
does not occupy an integer number of video fields. It restarts at a different
ULA phase, so a first-loop score alone cannot qualify a looping player.

Decision: retain this partial success as evidence, not a root delivery.
Require both-loop clock-aware acceptance. Next fix repeat phase before
spending more effort on small modulation-noise gains. No normal-speed
audible capture or physical measurement was run for this rejected candidate;
its preview WAVs integrate the newly measured Fuse port events.
[Evidence](experiments/ima-direct-precomp/report.json).

```powershell
python audiobook-beeper/precompensate_voice.py --pilot build/ima-direct-weighted --output build/ima-direct-precomp --ffmpeg <ffmpeg.exe> --fuse <fuse.exe>
```

## Stable repeats with a balanced idle tail

The [ASM](direct-player.asm) now optionally emits alternating output levels
in the already silent tail, before the final two source samples. Each pair
costs 52 native T: OUT=12, JP=10, NOP=4, OUT=12, DEC A=4, JP NZ=10.
Both high and low ordinary holds are 26 T. Each group of up to 255 pairs
adds LD A,n=7 T; the final padding uses 4-T NOP and 7-T LD A,n instructions.
A/flags are scratch here; the extracted IMA nibble remains in AF'. No
interrupt, ROM call, extra disk read, or audio pre-expansion is introduced.

The final full-source candidate uses 1274 pairs, five groups and 212 T of
padding: **66495 additional native T/loop**, giving **79122727 T/loop**.
All ordinary decoding remains **423 T/sample**. Full native and cold Fuse
checks pass two loops, **5985257 exact outputs /373760 predictors and
indices**, complete paging/loading checks and native RAM/timing guards.
Actual ULA overhead is 7537450 T across both loops, separate from the
66495-T deterministic increment and preload disk/ROM time.

Both final Fuse loops are **82891452 T =1169 video fields =23.37011249 s**,
with exactly repeated phase. The physical PCM-count equivalent is
7996.5383 Hz (-0.04327%); the compensated speech reference is explicitly
the original **8000-Hz clock**, with zero extension for the silent loop tail.
Do not stretch the original reference across that appended pause. No fitted
phase or gain is used. The two nominal-clock scores are both **18.99410 dB**.
The repeat regression is fixed; **20 dB is still not achieved**.

Windows crossing the appended silence show a 16.55% apparent PCM-clock
slowdown over 0.1 s; this is explicitly reported, not hidden as a passing
window. One-second windows remain within 1.91%. The source compensation
and fixed 8-kHz reference measure voice timing separately from that pause.
Normal-speed Fuse sound capture covers two wraps; physical hardware is
unmeasured. [Report](experiments/ima-direct-locked/report.json) and
[recording](experiments/ima-direct-locked/result-preview.wav).

The first padded assembly used unsupported two-argument DS syntax; change
to pyz80's zero-filled one-argument DS. A 600-pair phase-only probe did not
align the loop. A shorter JR page branch saved 3 T on ordinary pages but
did not improve actual loop phase and was reverted. A 1270-pair/222-T pilot
settled within three T of the first cold phase, then repeated exactly.
Re-encoding changed the endpoint: first/second-loop scores became
18.9942/13.0362 dB until the final 1274/212 calibration above. Therefore a
general converter must recalibrate **after final encoding**, as well as
verify both loops; a saved schedule for another input is insufficient.

Bounded host feedback probes do not justify another layout: beta 0.625
gains only 0.0033 dB over 0.5 on the pre-calibration trace and does not fit
the existing reserve; beta 0.375/0.75 are worse. On the locked trace, extents
0.25/0.375/0.5/0.625 give 18.9867/19.0096/18.9941/18.9542 dB. These are
host estimates, not executed alternate tables. Retain 0.5 for this verified
checkpoint rather than describing a 0.0155-dB host gain as a new release.

The next deliverable is a source-independent converter: accept ordinary
FFmpeg-readable audio, retain its initial fragment that fits one resident
TRD, disclose truncation, and produce previews and measured quality. The
user also requested better compression with real-time memory decoding;
compare that quality/CPU tradeoff before selecting a new default codec.
