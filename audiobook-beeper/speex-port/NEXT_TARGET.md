# Next decoder target

Authorized 2026-10-04, continuing in the existing `codex/speex-port` worktree.
This milestone concerns the selected PVQ PCM8 player. Exact Speex `pure-r9`
remains a separate decoder; its real-time deficit is not solved by PVQ.

1. **Firm target: unchanged sound, at most 84 T/sample before pacing.**
   Baseline: round12, 186880 samples, 16897348 T / 90.418 T/sample, 80974
   stored bytes, 4614 table bytes, raw PCM8 SNR 23.510 dB. Remove intermediate
   history writes and dead end-of-vector pointer increments. Require every
   PCM8 byte and compressed input to remain unchanged; retain every 437/438-T
   output interval, all bank boundaries and stream tails. Count and audit
   the instructions, preserve memory guards, and archive round13.
2. **Conditional target: about 3:1 versus PCM8 and at most 80 T/sample.**
   Try four-sample vectors with 1024 entries. The control recording would
   occupy 62528 bytes including dictionary/header (2.989:1); this is an
   estimate, not a measured codec result. Retrain and compare against the
   same source. The experiment's selection gate is at most 1 dB raw SNR
   loss versus round12, with no clipping; this is our conservative gate,
   not a user-specified universal quality threshold. Retain the three-sample
   version if the gate fails. Archive round14, including rejected results.

The table ceiling remains 16 KiB. Uniform timing is a nominal 3.5-MHz CPU
claim only; ULA/physical timing remains a later validation target. Faster
decoding increases time available for useful work; the output stays at 8 kHz.
Do not expand this milestone into PDM, TRD release or another Speex rewrite.
Commit each completed change with its report and root CHANGELOG entry.

Target 1 achieved: [round13](rounds/13/REPORT.md), 83.7515 T/sample for the
complete recording, identical data/sound and all 437/438-T output intervals.
The conditional four-sample-vector comparison remains the next experiment.
