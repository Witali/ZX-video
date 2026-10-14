# Intermittent electronic-tone audit and improvement proposal

2026-10-14, from `38bea3dd`. The user reports periodic "beep/blam" sounds,
prefers the earlier audition and asks to study the source/output and propose
improvements. This is an analysis deliverable, not another production refit.
Direct auditory perception is unavailable in this agent session. Conclusions
below come from PCM, STFTs, exact chip targets and code; no subjective listening
or independently labelled perceptual beep count is claimed.

## Evidence from the complete90-second song

[Saved report](beep-evidence/report.json) authenticates all source/media hashes.
An instrumented replay of the original fitter captures its internal prediction
without changing any arithmetic. All40,500 targets and the fitting gain match
the stored original controls exactly. Source and both real chip WAVs use the
same timeline and prior constant playback gain. Existing auditions remain.

- All nine voices are active throughout the4500 fields. These effects are not
  explained by routinely keying every voice off/on at each frame boundary.
- At TL<=40,14,185 of39,542 active channel transitions (35.873%) jump at least
  three semitones in20 ms;2,658 jump an octave. There are1,050 A/B/A-type
  two-jump returns within40 ms (both jumps>=3 semitones, return within0.5).
  These are control events, not1,050 perceptually confirmed artifacts.
- Splitting a channel trajectory at1-semitone jumps or low level yields22,034
  audible segments;20,808 last<=80 ms, including12,412 above800 Hz. The
  segmentation also splits genuine fast melodic/gliding components.
- A local prominence heuristic finds1,155 field/voice pairs where source
  prominence is<8 dB and synthesized prominence>14 dB, at300..8000 Hz/TL<=40.
  Across those events the mean prominence is4.944 dB source,16.758 dB old,
  16.773 dB pure-sine. The latest version retains this issue essentially intact.
- Median spectral flatness in1.5..4 kHz is0.117821 source,0.026380 old,
  0.019420 pure-sine: the reconstructed texture is much more concentrated
  into isolated lines. Flatness alone is not a perceptual quality score.
- The RMS correction hypothesis is weak here: original per-field template
  correction is median1.04745,p90=1.17745,max1.56655; only three fields exceed
  1.5 and none exceed2. Do not claim that a large normalization boost dominates.
- The full log/level error worsened9.444631 ->9.897613 after purity correction.
  Only72 level targets changed; every frequency/multiplier/key schedule stayed
  the same. The earlier whole-song representation is the recommended baseline.

The strongest candidate spans by exposed-line prominence are12.50..15.50,
22.82..25.82,63.98..66.98 and78.06..81.06 seconds relative to the song.
Each retained WAV contains source0..3 s, silence3..4, old4..7, silence7..8,
pure-sine8..11. Every source/model PCM segment is taken directly from its
authenticated complete WAV, without extra normalization:

| Source interval | Exact comparison | Common-scale spectrogram |
| --- | --- | --- |
|12.50..15.50 | [WAV1](beep-evidence/span-1-source-old-new.wav) | [Figure1](beep-evidence/span-1.png) |
|22.82..25.82 | [WAV2](beep-evidence/span-2-source-old-new.wav) | [Figure2](beep-evidence/span-2.png) |
|63.98..66.98 | [WAV3](beep-evidence/span-3-source-old-new.wav) | [Figure3](beep-evidence/span-3.png) |
|78.06..81.06 | [WAV4](beep-evidence/span-4-source-old-new.wav) | [Figure4](beep-evidence/span-4.png) |

## Likely mechanism

The fitter independently selects nine peaks every20 ms. Its local channel
assignment follows nearby frequency but does not establish persistent source
partials or distinguish a stable tone from a broad/noisy spectral hump.
The inverse-magnitude exponent1 supplies up to40x additional weight for weak
bins, and regional peak proposals deliberately include weaker components.
Short-window random/overlapping peaks can therefore become strong, separate,
rapidly changing synthesized tones. The observed transitions and source versus
model texture support this mechanism; controlled ablations and listening are
still needed to establish which events correspond to the user's exact sounds.

Suppressing a sine oscillator's intrinsic harmonics addressed a different
property. It did not correct these selected trajectories; reducing the diffuse
texture can expose the isolated electronic tones further. The preceding
whole-song score regression and the user's preference should control the next
quality objective, rather than the four held-tone purity numbers.

## Proposed implementation order

1. **Track source partials over time.** Keep the short analysis for attacks;
   use an additional80..120-ms window and60..100-ms lookahead to confirm weak
   tonal candidates. Assign trajectories globally over several frames, with
   frequency/level/acceleration costs and source evidence for births/deaths.
   Require2..3 fields of evidence for a weak new line while allowing an immediate
   strong musical attack. Check A/B/A returns instead of smoothing every genuine
   pitch change. Offline lookahead need not delay the exported soundtrack.
2. **Avoid turning diffuse energy into compulsory notes.** Introduce a
   source-tonality/confidence gate and an explicit inactive-voice option.
   Reduce inverse weighting specifically for unsupported/noisy weak candidates,
   instead of the failed whole-track exponent0/long-window refits. Allow fewer
   than nine tones when another tone would invent a line. Preserve source
   dynamics and measure missing components so quiet real notes are not erased.
3. **Fit musical groups and transient behavior.** Give stable melody/bass
   trajectories priority; compare source-supported harmonic/FM groups with
   the existing mildly modulated baseline. Test source-derived attack/release
   on weak components and proper attenuation/reallocation around major pitch
   jumps. Do not globally force every part to a pure held sine or flatten real
   percussion attacks. There is no proof yet that a specific FM patch solves it.
4. **Judge the actual full chip output.** Add penalties for unsupported
   narrowband bursts, rapid trajectory switching and modulation-envelope
   mismatch alongside the existing multiscale spectral/dynamic measures.
   Keep all original content, clipping and timing checks. Test the four matched
   excerpts first, then the entire90-second stream and exact replay. Compare
   with the original preferred version at one fixed gain. Evaluate100/200-Hz
   target updates only after establishing stable trajectories; changing the
   update rate alone does not resolve erroneous peak selection.

The first useful next experiment is time-coherent source tracking on the
original `4b73f9ea` mildly modulated baseline with the same50-Hz exporter.
This document proposes that experiment; it does not implement or authorize
an automatic new fit, target-rate change, native scheduler or release update.

## Reproduction and verification

With the existing NumPy/Pillow/ymfm-py0.2.0 environment, from the worktree root:

```powershell
$env:PYTHONPATH=(Resolve-Path .tmp/dependencies/ymfm).Path
$env:OPENBLAS_NUM_THREADS='1'
python ay-converter/analysis/ym3812_sea_foam/inspect_beeps.py --output .tmp/new-beep-audit
```

Use a new directory. The runner checks every existing media/source hash,
requires the full4500-field control refit to match, and saves diagnostic arrays,
four source/old/new comparisons and aligned source-scale plots. Verification
compares every archived clip segment with the exact source WAV bytes and all
producer/artifact hashes. No replacement song or player code changes.
