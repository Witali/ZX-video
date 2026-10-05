# Source loudness conditioning

2026-10-05. At the user's request, ordinary audio conversion now defaults to
**gentle dynamic compression followed by peak normalization**. This applies
to IMA3, IMA4 and both mu-law carrier rates. It is independent of the storage
codec: IMA still uses the same packed codes and the same Z80/PDM player.

```powershell
python audiobook-beeper/convert_audio.py input.m4a --codec ima4 --dynamics gentle --output build/normalized --ffmpeg C:/Tools/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

`gentle` is the default. `--dynamics off` retains the previous **peak-only**
normalization, including its exact sample arithmetic. `--prepared-pcm`
always preserves the supplied PCM; neither mode recompresses or renormalizes
it. Existing disk images are not rewritten by this default change.

## Processing order

1. FFmpeg downmixes and resamples to 8-kHz floating-point mono, retaining its
   normal anti-alias filtering.
2. Normalize the selected recording's peak to 109/128 (0.8515625).
3. Apply a downward compressor: threshold 0.125 (about -18 dBFS), ratio 2:1,
   soft knee 2.828427, RMS detection, 5-ms attack and 200-ms release.
4. Guard brief overshoots with a lookahead limiter: ceiling 0.5, 5-ms attack,
   100-ms release, automatic level makeup disabled and latency compensation
   enabled. This prevents isolated short peaks from setting the whole track's
   final gain. No hard PCM clipping is used for loudness adjustment.
5. Apply one final fixed gain to bring the processed peak back to 109/128.
6. Split into resident parts, apply the existing short boundary fades, add
   silent guards, then quantize and encode with the selected codec.

Sequential IMA modes process the **complete selected track continuously before
splitting**. Compressor state and normalization do not reset at disk or RAM
boundaries. The preview processes its retained prefix. Off uses one fixed gain
and skips both compressor and limiter. Silence remains exact silence. The
lookahead is compensated on the PC; sample count and audio duration do not
change. New resume identities include the dynamics mode and helper source.

This reduces contrast between loud and quiet passages. It can make quiet
speech more audible above the PDM noise floor, but it is not a guarantee of
higher RMS on every possible recording or elimination of cyclic noise. A
constant loud tone does not benefit in the same way as a dynamic speech track.
The retained output bandwidth and PDM frequency are unchanged.

## Metadata and implementation

[`audio_dynamics.py`](audio_dynamics.py) is shared by the codecs. Streaming
float32 files keep whole-track processing bounded in memory. The in-memory
preview and streamed implementation produce identical conditioned samples
for the same float32 input. `track.json` and the final series report record
the mode, both normalization gains, exact filter chain, input/output RMS,
sample count and RMS change relative to the old peak-only preparation.

For nonlinear preview preparation, `fixed_gain` is null: the signal no longer
has one overall fixed gain. Series `gain`/`fixed_gain` is specifically the final
scalar applied to the already conditioned cached float32 track; the separate
`dynamics` object describes prior processing. Do not apply the initial gain a
second time to that cache. SNR still uses the prepared reference and does not
count intentional compression as a coding defect; it is not fidelity to the
unprocessed full-band recording.

The supplied complete O. Henry audiobook retains all 5340776 selected PCM
samples (667.597 seconds) during preparation. RMS rises from **0.070617** for
the old peak-only signal to **0.112783**, **+4.067 dB**, with the same 0.8515625
peak. This is a source-level measurement, not a promised 4.067-dB PDM SNR gain.
Only the initial disk-capacity prefix is retained on one TRD, as before.

The [completed normalized IMA4 disk and comparison](experiments/audio-dynamics/README.md)
retain 113.712 seconds and pass complete native/cold Fuse checks. Prepared-source
SNR improves from 10.33..13.53 to 15.14..18.95 dB over its five parts. Periodic
distortion remains; normalization is not a proven flutter fix or a 20-dB result.

`test_audio_dynamics.py` checks actual FFmpeg compression, quiet-passage gain,
reduced contrast, unchanged sample count/polarity/peak, streaming parity,
silence, exact off mode, prepared PCM and public CLI routing. Run with
`TASK_FFMPEG` pointing to the installed executable. No Z80 code changes:
IMA4 ordinary 423 T/sample, page/bank extras 14/140 T, all deltas 0.
