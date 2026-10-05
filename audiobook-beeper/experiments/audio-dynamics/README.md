# Gentle source dynamics

2026-10-05. The user requests louder source audio with normalization and mild
compression after reporting vibration in the complete IMA4 disk. The shared
[implementation and controls](../../AUDIO_DYNAMICS.md) now apply by default
to ordinary IMA3, IMA4 and mu-law input. The Spectrum player is unchanged.

## Completed preparation evidence

[`preparation/report.json`](preparation/report.json) authenticates the original
decoded track against the previous full-disk cache and confirms that
`--dynamics off` recreates **all five former prepared PCM streams byte for byte**.
Gentle processing preserves 5340776 decoded samples /667.597 seconds and raises
whole-track RMS by 4.066736 dB at the same 0.8515625 peak. The retained first
five parts' RMS gains are 5.4545, 5.3514, 5.4387, 4.9662 and 5.3177 dB.
These are source-level improvements, not promised output-SNR gains.

- [First eight seconds, previous peak-only source](preparation/before-first8.wav)
- [Same source with gentle dynamics](preparation/gentle-first8.wav)

Both files retain their actual prepared levels; no extra listening gain is
applied. They are pre-IMA source references, not Spectrum output.

Thirty focused tests pass, covering real FFmpeg filtering, compressor
behavior, streaming parity, exact off mode, sample count/polarity/peak/silence,
prepared-PCM bypass, CLI routing and existing series/clock/search contracts.
The initial test incorrectly expected total RMS to increase even for a
sustained high-amplitude tone; the actual requirement is reduced dynamic
contrast and raised quiet passages. Replace that assumption with direct
behavioral checks and separately verify the real audiobook's positive gain.
The CLI harness also now accepts the IMA3 command's successful SystemExit(0).
Neither test adjustment changes the production quality or timing gates.

## New full-disk build

The public converter is being run with one bounded waveform attempt and no
additional clock-refinement pass; existing compensation candidates remain
eligible. No native/Fuse check is skipped:

```powershell
python audiobook-beeper/convert_audio.py "path/to/audiobook.m4a" --codec ima4 --disk-mode single --dynamics gentle --attempts 1 --no-refine-clock --no-recording --output build/ima4-normalized --ffmpeg C:/Tools/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

`precompute.py` can prepare independent later parts through the same public
converter function. Source, tools and producer hashes must match the running
conversion; only fully completed part results can be adopted. This changes
host scheduling, not encoding settings or final-volume verification.
The first compensated part measures 15.884 dB over both complete cold Fuse
loops, versus approximately 11.45 dB for the previous first part. This is a
**partial new-disk result**, not a complete release or a vibration-free claim.
The complete volume and final coverage will be recorded after verification.

Ordinary IMA4 cost remains 423 T/sample, page/bank extras 14/140 T, all deltas 0.
No physical-hardware result, carrier reduction or constant-clock redesign.
