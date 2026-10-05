# Round 21: reject unprofitable zero tests before implementation

2026-10-04. Observe the unchanged round20 full speech at `_split_nibbles`
and `_mul_s8`. Read arguments without altering Z80 state. All 186880
PCM16/PCM8 samples, every saved OUT timestamp, binary hash and complete
1973053274-T duration remain unchanged. This is a profile, delta **0 T**.

There are 3340 zero feedback samples out of 186880 (1.787%), 18847 zero
pitch gains out of 559217 actual pitch products, and only 3447 zero-word
products whose multiplier is nonzero. Another 3156 products belong to
energy preparation. The saved counts distinguish these cases so the
existing zero-multiplier return is not charged twice.

For a zero-word guard after the existing zero-multiplier check, account
24 extra T on nonzero words, a 59-T zero return, and the old per-input cost
formula. Predicted **11949481 more T**: reject. A zero-gain guard before
each pitch tap costs 27 T on all 3*186880 attempts. Even crediting maximum
skipped-path work gives **8958975 more T** (lower estimate: 9426639 more):
reject. These are instruction-derived estimates, not executed candidates.

A zero-feedback copy could replace 4122 T of products/state updates with
833 T, including its jump back to output. A conservative 18-T new test
predicts **7621420 fewer T** on the complete speech: prototype this path.
Code inspection then finds the existing A register already holds H for a
14-T test, and `asm_n` is only allocated/written, never read. Removing its
16-T write makes the ordinary path two T cheaper as well. The refined
candidate predicts **11359020 fewer T**; this remains unexecuted here.

Reproduce with `profile_zero_paths.py --variant pure-r20`.
[Observed arguments and forecasts](zero-profile.json),
[script](../../profile_zero_paths.py). No format, RAM, binary or hardware
claim changes. The average real-time goal remains unmet.
