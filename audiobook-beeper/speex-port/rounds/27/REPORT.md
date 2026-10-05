# Round 27: shared pitch-history cursor and subframe dispatch

2026-10-04. Continue from exact round26 on unchanged mode-3 speech.
For pitch >=41 and sample j=0..39, all three indices j-(pitch+1-k) are
negative and adjacent. Initialize IX=e-2*(pitch+1), read the three words
at IX+0/2/4 and advance IX by two bytes per sample. The multiply and clip
preserve IX; shape parsing also leaves it intact.

Select one whole 40-sample loop per subframe. Duplicating the unchanged
clamp/innovation tail avoids testing pitch for every sample. The long-period
loop needs no sample_index increment. The general path retains its original
wrap and skipped-tap logic for periods 17..40. Its final jump skips the new
loop. No extra RAM state or writable code is introduced.

## Exact timing and tradeoff

Each long-period history selection falls from **143 to 38 T**. Across three
terms this saves 315 T; two INC IX instructions cost 20 T, yielding **295 T**
per pitch-sum block. Removing the unused sample_index increment saves another
21 T: **316 T per fast sample**. Dispatch plus cursor setup costs **128 T per
fast subframe**. The general path adds 30 T of selection and a 10-T final
jump, **40 T/subframe or one T/sample**.

There are 3519 fast and 1153 general subframes on the full control. Predicted
and executed saving agree exactly:
`3519*(40*316-128) - 1153*40 = 43983608 T`.
Full speech **1834745357 -> 1790761749 T**, **9582.4152 T/sample**,
**2.397% fewer T**. First frame **1201256 -> 1188864 T** (-12392).
The six-bank silence fixture uses the general path and becomes 786400 T
slower, exactly one T/sample. Accept this small cost because complete speech
and the all-period fixture improve; it is not a universal per-input speedup.

## Verification

For **all 128 pitch periods, all 40 sample positions and 16 gain triples**,
execute the old and new pitch-sum paths with random signed16 history. All
**81920 sample cases per variant** match an independent index/product model.
Read callbacks confirm every history-byte address, including wrap, skipped
taps and the 40/41 threshold. Every fast cursor value, SP/IY preservation,
setup cost and 295/0-T block delta passes. Thirty-two complete instruction
audits cover boundary periods, endpoints and zero/nonzero gains.

An additional **128-frame / 20480-sample** stream replaces only the seven
pitch bits, exercising every pitch in each of the four subframe positions.
Both binaries match upstream fixed-point Speex at every PCM16/PCM8 value;
its total falls **202993232 -> 197792080 T** (-5201152). The complete
standard suite also passes **1074400 samples**: **1094880 complete-stream
samples checked for the selected image** in total. Arithmetic, tables/cache,
controls, guarded RAM/code writes, frame/silence instruction audits and a
fresh default build pass. SHA-256:
`a35ab79ac73565107a98decac334a2884d1f6f37550b54bb3a07905d827f0ccd`.

## Decision and next candidate

Select **pure-r27**. Code **7619 bytes** (+299), state 1041 and reserved
stack 256 unchanged. Tables remain 16010 useful bytes in a 16384-byte arena;
stored speech remains 23360 bytes / 8:1 versus PCM8. Consecutive output has
no pacing. 23.36 seconds of audio takes 511.646 nominal CPU seconds, still
**21.9027x** the average real-time budget. ULA/disk/hardware are unverified.

Next investigate constant pitch-gain multiplication. The mode-3 gain book
has a fixed finite set of multipliers. Generate signed24 shift/add/subtract
routines for those constants and replace the existing 192-byte gain table
with same-size routine-pointer triples. Include indirect-call and setup
costs; retain the generic multiplier for energy arithmetic. This proposed
change is unimplemented and unmeasured. It could exchange additional code
for less repeated multiplication work without growing the table payload.

Reproduce `build.py --skip-host --variant pure-r27`,
`check_round.py --variant pure-r27`, `check_pitch_paths.py`, and
`check_unpaced.py --variant pure-r27 --previous pure-r26 --check-default`.
Retain round26, original speech and the upstream host DLL for comparison.
[Measurements](report.json), [full checks](checks.json),
[all-period/address checks](pitch-path-checks.json),
[unpaced checks](unpaced-checks.json),
[extra packets](all-pitches-input.spxraw.gz),
[upstream PCM16](all-pitches-reference.pcm16.gz),
[transform](../../followup_opt.py), [checker](../../check_pitch_paths.py).
