# CB41 frame-rate headroom from complete movie traces

2026-10-01, baseline `d751ce8`. The current player publishes one frame every
six 50-Hz fields: **25/3 fps**. This is the highest rate actually verified
for the complete movie. The maximum sustainable rate of CB41/LZSA2 on this
input has not been measured; compression alone does not specify one.

## Read-only assessment

[assess_cb41_cadence.py](assess_cb41_cadence.py) checks the root TRD identities
and archived script/trace hashes, parses their actual frame-ready events,
and cross-checks every publication against the saved timing reports. All
4221 frames and 4218 intra-disk intervals are covered; startup priming is
excluded from the interval comparisons. No image, player or schedule changes.

For each frame after the first, measure the time from the previous actual
publication OUT to the native draw return. At the normalized 50-Hz timebase
this is **30.448 ms on average**, **105.171 ms maximum**. The smallest gap
between draw completion and its scheduled publication is **14.828 ms**.
Frame-ready sampling precedes the ready-flag store by a few instructions.

| Candidate rate | Fields/frame | Budget | Observed intervals exceeding that budget |
| --- | ---: | ---: | ---: |
| 8 1/3 fps | 6 | 120 ms | 0 |
| 10 fps | 5 | 100 ms | 2 |
| 12.5 fps | 4 | 80 ms | 18 |
| 16 2/3 fps | 3 | 60 ms | 187 |
| 25 fps | 2 | 40 ms | 956 |

These are **comparisons with the existing six-field trace**, not measured
late-frame counts at the candidate rates. The two intervals exceeding
100 ms are movie frames 3506 and 3615 (zero-based), both on disk 3:
103.842 and 105.171 ms respectively. Their location narrows a future probe.

Disk read service after first publication averages 8.74..8.75 ms per sector;
the maximum is 43.93 ms. These call intervals include CPU/ROM, IRQs and
emulated drive latency. They are neither pure physical latency nor costs
that can be added again to already measured elapsed intervals.

## Interpretation

**8 1/3 fps is confirmed; 10 fps is the next sensible rate to test.**
12.5 fps is not established by this analysis. Native output and transport
work are pipelined: early draw completion does not mean the CPU is idle,
because it can prepare the next packet and refill the reservoir. Do not
invert the 30.448-ms average and claim 32.8 sustainable fps.

A faster schedule changes prefetch, FIFO occupancy, disk rotational phase
and IRQ timing. A true higher-fps conversion also samples more source frames
per second, changing deltas and compressed size. It needs decoupled frame/AY
counts while AY stays at 50 Hz. Merely shortening the current movie's frame
period would accelerate the video instead of preserving duration and sync.
Only a rebuilt candidate with complete timing/pixel/AY/disk checks can prove
a higher rate or its disk count. The current three root images remain valid.

Reproduce: `python toolkit/assess_cb41_cadence.py --output
toolkit/cb41_cadence_headroom.json`. The [report](cb41_cadence_headroom.json)
includes per-disk statistics and the ten slowest intervals. The initial
parser expected full debugger command names; it stopped on the saved `com`/
`pr` abbreviations. Supporting both spellings produced the complete checked
result; no partial parser output was accepted.
