# Exact packet feedback endpoint diagnosis

2026-10-14. `audit.py` independently implements the original integral
recurrence with exact fractions, including its positive 1/10^12 epsilon,
floor and clipping. All 2048 original words and successor cells agree with
`probe_feedback_packets.integral_table`; no source audio is opened.

At zero PCM level, the original packets `6AD5` and `952A` correctly derive
the stored cycle 16 -> 17 -> 16. Forced `56AD` from state 17 instead ends
with recent error +0.065214038 and derives successor 17, although the
word-only and zero-mean pair controls retain successor 16. Forced `569A`
from state 16 derives 17 correctly. Every relevant q endpoint rounds to
q-code 8; the discrepancy is in recent-error quantization.

This changes the next experiment: among 424 words with 224 high T states,
238 derive successor 17 from state 16; among 424 words with 225 high T
states, 238 derive successor 16 from state 17. A separate source-free
selector can rank these endpoint-consistent domains with the same periodic
filter objective. The 238-by-238 domain is a hypothesis, not acceptance.

The physical player uses explicit lookup successors and never calculates
these fractions. Its previous exact bit/state/timing proofs remain valid.
This diagnosis does not prove a causal explanation for quality regressions,
equivalence to the original individual decisions, bounded internal history
or improved audio. Forced `569A`, for example, reaches |recent| about 1.556.

`report.json` preserves all six replay cases as numerator/denominator pairs,
the complete permitted word lists and source/script hashes. It supplements
the completed measured control without changing its original artifacts or
manifest. Reproduce:

```powershell
python audiobook-beeper/experiments/song-snr/evidence/feedback-endpoint-audit/audit.py `
  --output .tmp/feedback-endpoint-reproduction.json
```
