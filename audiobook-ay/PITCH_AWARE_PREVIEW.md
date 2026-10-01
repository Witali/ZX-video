# Pitch-preserving YM2149 speech at 50 Hz

The user pointed out a recognizable vocal exclamation when the rabbit leaves
its burrow in the movie, approximately one third into disk 1, and requested
another attempt at intelligible AY speech. This is **one bounded candidate**,
not a claim that arbitrary speech is now intelligible.

## Listening and disk

- [New 24-second chip-model preview](pitch-preview/candidate-preview.wav).
- [Rejected LPC/formant mapping through the same chip model](pitch-preview/previous-preview.wav).
- [Identical source passage, matched RMS](pitch-preview/original-preview.wav).
- [Root test disk](../ZX-audiobook-YM2149-voice-test.trd).
- [Build report](pitch-preview/report.json) and
  [complete native/Fuse verification](pitch-preview/verification.json).

All excerpts cover audiobook source **[60,84)** seconds. WAVs are 44100 Hz,
16-bit mono, matched in RMS without clipping. No source audio is mixed into
the generated signal. The TRD independently boots on **Spectrum 128 + Beta
Disk/TR-DOS**; mount in drive A and use `RUN "boot"` if needed. It plays once
for 24 seconds, then mutes. Reset to replay. The prior AY and PDM disks remain
unchanged.

## What changed

The previous LPC mapper computed the vocal pitch but never used `pitch_hz`
to generate its tones. It placed three independent square waves at formant
peaks. The movie encoder instead tracks low, middle and high tonal voices,
including fundamental pitches. That difference suggests a testable path;
recognition of one vocal effect does not establish full-sentence intelligibility.

The new offline encoder uses the existing 20-ms LPC analysis and pitch track.
For voiced speech, channel A retains the fundamental, with a small positive
fitting floor. B and C select harmonics of that fundamental by fitting the
source spectrum with **actual integer-period square-wave spectra**. Joint
nonnegative amplitude fitting accounts for the generators' unwanted odd
harmonics; levels use the existing YM2149 DAC table. It does not snap speech
to musical notes. A 32-ms analysis window follows the 20-ms update cadence.
Unvoiced/transient frames use the one shared noise source on B, with its
period selected by spectral matching; silence stays silent.

This remains three tone generators, shared noise and fixed-volume registers
R0..R10 at **50 Hz**, with equal mono mixing. Envelope generation, PCM DAC
playback, extra channels and a native LPC synthesis filter are not used.
The unmodified Ayumi renderer preserves oscillator/noise phase across ticks.
It models the chip; it is not a physical speaker recording or an analogue
model of a particular Spectrum board.

## Movie cue inspection

The first current movie disk lasts 131.2 seconds, putting its first third at
43.73 seconds. Opening source images place the burrow exit in this vicinity.
The saved **[36,52)** comparison is deliberately broader than the approximate
user cue; the exact vocal onset has not been manually labelled.

- [Original movie cue](pitch-preview/movie-cue/movie-original-preview.wav).
- [Exact released movie registers through the YM model](pitch-preview/movie-cue/movie-ay-preview.wav).
- [Authenticated source/register evidence](pitch-preview/movie-cue/report.json).

Render from time zero before taking the slice, retaining generator history.
The 800 states average 2.1825 active tones; 125 states use noise. The median
lowest active tone is 143.39 Hz. This is the combined music/voice soundtrack,
so these statistics alone cannot identify which generator carries the vocal.
No movie register or release image is changed.

## Results and limits

| Same passage and same chip renderer | Previous | New candidate |
|---|---:|---:|
| Spectral cosine | 0.666873 | 0.926218 |
| Chroma cosine | 0.846220 | 0.981201 |
| Loudness correlation | 0.874808 | 0.870788 |
| Onset F1 | 0.757576 | 0.794118 |

The earlier metrics reproduce exactly. The substantial spectral gain and
better onset score support delivering this candidate for listening; loudness
correlation falls slightly. These are signal proxies, **not intelligibility
scores or percentages of preserved speech**. Listener acceptance remains open.

All 1200 ticks /13200 register writes match in an independent Z80 core and a
complete cold Fuse run. No fields are missing/duplicated; the final state is
held for a full field, then muted. There are 52 startup reads, zero runtime
reads, and 96 occupied sectors. First-OUT phases are 150..153 T; intervals
70905..70909 T. The native player is unchanged: **974 deterministic T/tick,
delta 0 T**; IRQ, ULA, ROM and disk timing remain separate. Ten Python tests
and the existing YM tests pass, including nonmusical pitch, register round
trips, silence/noise, synthetic square-component fitting and chip semantics.

## Reproduction

Reuse the authenticated `source.f32` prepared by `probe_lpc2.py`. Its SHA-256
and the saved `detail50` analysis identify the exact input; no LPC re-encoding
or external codec edit is necessary.

```powershell
python audiobook-ay/probe_pitch_aware.py --node "C:/Tools/node.exe" --ffmpeg "C:/Tools/ffmpeg.exe" --source-pcm "audiobook-ay/lpc-probe/source.f32" --output "build/pitch-preview"
python audiobook-ay/verify_preview.py "build/pitch-preview" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python audiobook-ay/inspect_movie_cue.py "C:/Audio/movie.mov" --node "C:/Tools/node.exe" --ffmpeg "C:/Tools/ffmpeg.exe" --output "build/movie-cue"
python -m unittest discover -s audiobook-ay -p "test_*.py"
node audiobook-ay/test_ym2149.js
```

Hardware capabilities: [Yamaha YM2149 manual](https://map.grauw.nl/resources/sound/yamaha_ym2149.pdf).
An independent [AY speech experiment by Nick Bild](https://github.com/nickbild/ay-3-8910)
also uses offline matching of short speech segments to actual tone/noise
outputs. It supports exploring this approach, not a quality claim for our
Russian audiobook. No code or audio from that project is used here.
