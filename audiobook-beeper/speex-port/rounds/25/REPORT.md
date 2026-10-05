# Round 25: separate the inline feedback cost

2026-10-04. Profile the unchanged exact round24 binary and complete
186880-sample speech. All PCM16/PCM8 samples, binary hash, inclusive phase
totals and every saved OUT timestamp match the ordinary execution. Total
remains **1850951266 T**, delta **0 T**. This is a measurement, not another
decoder optimization.

The observer brackets `_filter_feedback_start` through `_filter_emit` with
explicit endpoints, separately from function entry/return profiling. This
handles temporary table SP values without interpreting them as return
addresses. The block has no profiled callees in the inline variant; subtract
its span from the filter's exclusive cost only when presenting the split.
No duration is counted twice.

| Exclusive category | T/sample | Share |
| --- | ---: | ---: |
| Inline filter feedback | 3553.744 | 35.880% |
| Remaining decoder body | 1631.282 | 16.470% |
| Coefficient preparation | 1359.729 | 13.728% |
| Signed 8x16 products | 950.157 | 9.593% |
| General 16x16 products | 893.856 | 9.025% |
| Remaining filter body | 429.914 | 4.341% |

Other categories are recorded in the JSON. All exclusive spans plus
1548592 startup/driver T reconcile exactly to the complete total. Feedback
has 3340 calls at 847 T and 183540 at 3603 T. Standalone coefficient-product
and nibble-split helpers have **zero playback calls**, as expected after
inlining; the profiler no longer assumes ten helper calls per sample.

Observe the incoming ten LPC words at every preparation call and compare
them with the preceding call, forcing all pages on first use. This counts
**44692 changed pages independently**: 4436 calls change ten pages, 36
change nine, one changes eight and 199 change none. There are 4672 calls.
This confirms round24's timing-derived page count and its exact saving.

## Next candidate

Keep the three-term pitch sum in alternate HL/C during each excitation
sample. The present `_mul_s8` and its `neg32` tail use ordinary registers
only. Each active pitch product currently loads/stores a 24-bit sum at a
cost of **89 T** after the multiply. Transfer its low word via the real
stack, switch register sets, ADD and ADC into the alternate accumulator,
then switch back: proposed **52 T**, saving 37 per active term.

Initialization changes 42 -> 25 T; a final writeback costs 41 T/sample.
For the previously observed 559217 active pitch terms, predicted saving is
`559217*37 - 186880*24 = 16205909 T`. This is an instruction estimate, not
an executed candidate. Verify skipped-tap paths, modulo24 carries, helper
alternate-register preservation and every complete stream before selecting.
The average real-time goal remains unmet; do not add output pacing.

Reproduce `profile_throughput.py --variant pure-r24`, retaining round24's
ordinary report and OUT trace for comparison. [Profile](profile.json),
[profiler](../../profile_throughput.py), [observer](../../verify.py),
[unchanged binary](../24/player.ihx). ULA/disk/hardware remain excluded.
