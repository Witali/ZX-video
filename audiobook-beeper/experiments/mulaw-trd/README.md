# Mu-law resident TRD control, 2026-10-05

The user requests an eight-bit mu-law option in the real TRD generator,
then asks whether second-order sigma-delta improves quality. The compact
format and executable control are complete; the control is **rejected as
a quality upgrade**. IMA3 remains the default. Full usage, memory layout,
instruction counts, limitations and comparison are in
[MULAW_CONVERTER.md](../../MULAW_CONVERTER.md).

Input: first 15.120 s of the original O. Henry audiobook, mono 8 kHz,
fixed gain 1.959790331616458, 80-sample edge fades and 128 silent samples.
PCM16 is encoded directly to ordinary G.711 mu-law; 121088 bytes stay
compact in Spectrum RAM. All 128 KiB are accounted for. The 512-byte
lookup is read during modulation; no whole PCM/PDM expansion occurs.

## Results and evidence

- [Converter report](qualified/report.json), [preparation](qualified/preparation.json)
  and [player layout](qualified/player.json).
- [Native Z80](qualified/native.json): two complete loops, every bit,
  16-bit level and error state; full memory guards. 432 T ordinary sample,
  +4.625 versus IMA3; page/bank extensions 35/116 T.
- [Cold Fuse](qualified/fuse.json): two complete loops, 1937409 checked
  outputs, +0.185958% speed, 64119.013-Hz average PDM. Startup progress,
  message, paging and 473 audio sector reads pass; no runtime disk reads.
- [Quality](qualified/quality.json): minimum total SNR 9.672027 dB,
  codec-only approximately 39 dB. This is a noisy first-order control,
  not the PC SD2 algorithm. Keep both the unsuccessful quality result and
  the successful correctness/timing evidence.
- [Normal-speed capture](qualified/recording/report.json) and
  [Fuse WAV](qualified/recording/fuse-preview.wav). The recording uses
  Fuse's sound generator, not a physical sound-card loopback.
- [PC-only comparison](qualified/pc-comparison.json): second order at
  128 kHz gives 27.185326 dB versus first order 17.130225; at 64 kHz the
  scores are 11.536644 versus 10.053453. Same payload, complete clip and
  filter, no gain/delay fitting. The separate second-order WAV is explicitly
  named `pc-only-sd2-128-preview.wav`; it is not the disk's playback.
- The release copy is [ZX-audiobook-mulaw-test.trd](../../../ZX-audiobook-mulaw-test.trd).
  Its SHA256 is `e5e165410adc3993ea57cce3fe311f99c1d50770f6cbc146dd8ab4671ad857e2`.

Initial assembly integration needed pyz80 macro argument/label fixes.
The first native count assertion caught an arithmetic bookkeeping error
in the bank extension (126 versus the correct 116 T); the executable
instruction sequence was unchanged by that correction. Final compilation
and every native interval pass. These were development fixes, not verified
audio releases. The local `full` development directory is not release evidence.

Seven tests pass (`test_mulaw_player`, `test_g711_codec`), including every
G.711 code through the actual Z80, low-bit PCM16 preservation, RAM holes,
both CLI aliases and unchanged default IMA3 routing. The converter also
exhaustively checks both G.711 tables against FFmpeg before each build.

## Reproduce

Put the project Python dependencies, `audiobook-beeper` and `toolkit` on
PYTHONPATH. Use the recorded FFmpeg/Fuse paths or equivalent installations.
Always choose an empty output directory:

```powershell
python audiobook-beeper/convert_audio.py "source.m4a" --codec mulaw --output "build/mulaw" --ffmpeg "path/to/ffmpeg.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python audiobook-beeper/experiments/mulaw-trd/compare_modulators.py --input "build/mulaw" --ffmpeg "path/to/ffmpeg.exe"
python -m unittest test_mulaw_player test_g711_codec -v
python audiobook-beeper/experiments/mulaw-trd/archive.py --verify
```

For byte-exact audio preparation use the archived `qualified/source-preview.wav`
with `--prepared-pcm`. The assembly, configuration, raw payload, producer
snapshots, full debugger trace/timeline and FMF recording are retained.
No physical Spectrum test, second-order Z80 port, merge or push is claimed.
