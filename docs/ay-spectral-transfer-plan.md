# Transfer spectral synthesis techniques to the AY encoder

Started2026-10-13 from `6168ba14`, branch `codex/ay-spectral-transfer`,
worktree `.worktree/ay-spectral-transfer`. This is the user's authorized
implementation and comparison plan, not an automatic background goal.

## Baseline and scope

Use the exact prepared O. Henry[60,90) mono22050-Hz reference and1500 states
from `ay-converter/analysis/o_henry/evidence/compact30`. Its reference SHA256
is `99d8ddbca22dd76037e23d4f545d9452b3c8518061666726d9346d4e0fb3e2bd`.
It is byte-identical to the YM3812 experiment's reference. Replay the current
AY registers, including the running hardware envelope, before modifying them.
Do not compress/normalize prepared PCM a second time. Keep one calibration
gain fixed across comparisons; report any separately calibrated alternative.

The latest user steering requests examination of installed Fuse1.9.0 source
to identify the sound-chip/DAC/envelope model and whether YM2149 is a better
target. Verify the matching release source and record executable/source hashes.
Distinguish Fuse's actual implementation from the chip name and from physical
hardware. Compare AY-3-8910 and YM2149 settings explicitly where relevant.

Add opt-in host fitting; keep the existing default and completed releases.
Three physical tone channels, one shared noise generator/envelope and real
DAC codes remain constraints. No source PCM may enter chip synthesis. Source
samples are analysis targets only. Existing player and movie timing are not
changed by host-only fitting. New player code, if introduced, requires exact
old/new instruction-table T-states and complete native/Fuse qualification.

## Ordered milestones

1. **Direct spectral frequency candidates.** Fit real integer AY periods
   from interpolated peaks and subharmonics, with a three-channel square-wave
   dictionary and actual selected-chip volume curve. Preserve continuous
   chip phases and channel identity. Compare a bounded short/long-window
   choice with the same baseline; synthetic off-note, noise and silence tests.
2. **Quiet detail and frequency-band coverage.** Add source-only inverse
   magnitude weighting with a bounded floor, plus a limited peak budget in
   each frequency region. Run unweighted and weighted/band ablations; do not
   assume that more upper-band energy means better speech.
3. **Transition-aware selection.** Prefer equivalent good fits with smaller
   amplitude/routing/pitch changes. Diagnose command-induced transitions from
   identical emulator state, separate from normal square-wave edges. Compare
   continuity strengths and inspect both spectral and boundary artifacts.
4. **Subframe amplitude ramp probe.** After completing the50-Hz deliverable,
   compare bounded real DAC-register substeps in a separate chip simulation.
   Use actual DAC levels, shared-envelope restrictions and serial write times.
   Record extra writes/storage and quality tradeoffs. This probe does not
   qualify the existing50-Hz player for subframe writes. Only integrate a new
   native scheduler if an admitted quality benefit justifies it; otherwise
   retain the probe and its rejection explicitly.

## Evidence and decisions

For every meaningful experiment keep all tested parameters, register streams,
complete30-second render checks, source/producer/model hashes and elapsed time.
Measure unpooled magnitude/root cosines and log errors with512/2048/8192-sample
Hann windows,20-ms hops, the same source timeline and calibration; also measure
20-ms levels, silence behavior, clipping, subsonic/out-of-band energy and
transition diagnostics. No time/pitch warp, local output gain envelope or
per-image normalization. Provide common-scale figures and exact before/after
audio segments. Add a non-speech/synthetic guard for obvious regressions.

Admit a50-Hz candidate only with lower combined spectral/level error, no
clipping or illegal states, preserved pauses, level MAE within0.2 dB of the
baseline, and no dominant magnitude-cosine regression greater than0.005 on
any scale. Report smaller regressions, root cosines and measured gains too.
If all candidates fail, retain the baseline and record the failed transfer;
do not weaken this guard silently. A transition-only alternative may be kept
for listening with explicit spectral/dynamic tradeoffs; it does not become
the selected candidate through an undisclosed different criterion.

Commit each completed milestone/experiment with its CHANGELOG entry and
reproducing code/evidence. Update TASK_BRIEF as work progresses. Generated
temporary files stay untracked; deliverable WAV/figures use Git LFS. No merge
or push has been requested for this new worktree. Subjective speech quality,
physical-chip playback and a full-film release remain separate evidence.
