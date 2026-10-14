# Encoder search and clock-image audit

2026-10-14. This independent audit uses the complete generated test sources.
It does not change player instructions or qualify a release. All failed and
partially successful wider-beam controls are retained, rather than selecting
only the best result. The parent milestone records the decision in CHANGELOG.

## Findings

The analytic model and final unchanged FFmpeg measurement agree closely:
steps compensation9.9903/9.9588 dB and joint2.6428/2.6168 dB; loud3000
compensation7.4512/7.4556 dB and joint8.1516/8.1554 dB. The wrapper bit order,
table states and filter transfer are consistent. The pulse-center comparison
interpolates44.1-kHz output linearly; its3-kHz discrepancy includes that
interpolation error and is not a direct estimate of filter mismatch.

The complete steps search scores3.530/3.876 dB at width128/256, against
2.617 at width32. Increasing regularization to1.0 gives8.288 dB, still below
the simple compensation control9.959 dB. The full loud3000 scores remain
near8.23 dB with width128/256. Wider beam alone does not solve the loss.
Keep a measured whole-candidate fallback; a heuristic beam search is not
guaranteed to retain the original feasible path.

An ideal, unquantized and unclipped multilevel DAC on the actual slower clock
reaches only8.193 dB for loud3000 and17.885 dB for multitone. Over99.996% of
the loud3000 error power is above4 kHz, concentrated at the original5000-Hz
ZOH image and its shifted image near4981.57 Hz. Timing-compensated sampling
restores the fundamental but changes the image phase/frequency under the
unchanged4500-Hz listening filter. This control gives26.750 dB for steps and
33.089 dB for quiet440: their remaining error is codec/PDM/search related.
These results suggest clock-level correction or a more flexible timed
waveform mechanism. Narrowing the measurement filter would conceal this
error and would change the established comparison.

## Reproduction

Run from the research worktree root with the existing Python dependencies
and FFmpeg on PATH. `metadata.json` authenticates the producers and inputs.
First produce the four complete generated compensation/joint controls:

```powershell
python audiobook-beeper/experiments/song-snr/clock_control.py `
  audiobook-beeper/experiments/song-snr/evidence `
  --output audiobook-beeper/experiments/song-snr/evidence/clock-compensation `
  --scratch .tmp/clock-compensation --method compensation `
  --source steps --source loud3000 --source silence --source quiet440
python audiobook-beeper/experiments/song-snr/clock_control.py `
  audiobook-beeper/experiments/song-snr/evidence `
  --output audiobook-beeper/experiments/song-snr/evidence/clock-joint `
  --scratch .tmp/clock-joint --method joint `
  --source steps --source loud3000 --source silence --source quiet440
New-Item -ItemType Directory -Force .tmp/audit
python audiobook-beeper/experiments/song-snr/evidence/encoder-audit/check_model.py
python audiobook-beeper/experiments/song-snr/evidence/encoder-audit/bench_width.py
python audiobook-beeper/experiments/song-snr/evidence/encoder-audit/check_ideal_dac.py
```

The scripts write reproduced reports and temporary encoded streams into
`.tmp/audit`. Historical reports are saved here. Width reports include every
attempt and packed-byte identity. Temp encoded streams need not be copied
into Git because the source and complete producer reproduce them. No fitted
gain, time shift or clock is applied to any SNR. All controls use the complete
source except the unchanged fixed100-ms edge exclusion.

## Wider-table residency feasibility

`midpoint_layout.py` computes the universal duration-midpoint dictionary with
18 states, 130 FIRST and 104 SECOND patterns. Its tables end at BC40. Existing
fixed-bank2 startup padding is 694 bytes; moving the 311-byte cache probe
code and 256-byte sector bounce there leaves 127 bytes. Move the remaining
worker to BC40 directly, rather than rounding it to BD00. The existing
executable sequence lengths do not change. All probe/map/restore code and
the bounce remain in fixed bank2, so cold boot and insufficient-RAM refills
can retain the same mechanism without overlays or bank5/TR-DOS conflicts.

For the whole song, the projected worker ends at BF8F; for the maximum
2392 audio sectors it ends at BFBC, leaving 112/67 bytes before the forced
last byte. This is arithmetic feasibility, not assembled or executed proof.
Required implementation checks are saved in `midpoint-layout.json`; update
mutable-bounce guards and fully verify all claimed profiles and refills.

```powershell
python audiobook-beeper/experiments/song-snr/evidence/encoder-audit/midpoint_layout.py
```
