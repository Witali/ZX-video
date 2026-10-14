# Source-free endpoint-consistent idle pair

2026-10-14. Freeze `endpoint_idle_pair_words=[0x670D,0x969C]` before opening
any corpus input. This separately named mechanism corrects the conceptual
endpoint mismatch diagnosed in the earlier pair; it does not change earlier
helpers or measured artifacts.

For bin32, replay each forced word with exact fractions from q=0 and
recent=-1/2 at state16 or +1/2 at state17. Use duration weights16*hold/449,
beta1/2, the original positive1/10^12 epsilon, floor and clipping. Require
224 high T states and derived successor17 for the first word; require225
and derived16 for the second. Each domain contains238 of424 duty-qualified
words, giving56,644 pairs. No source signal or source-specific setting enters
these constraints.

The selector reuses exactly the prior analytic two-packet periodic filter,
duration-weighted midpoint variance and complement-plus-swap score sharing.
The candidate domains are closed under that symmetry; deterministic ascending
pair ID breaks exact ties. All filtered scores/means/moments equal the earlier
saved full179,776-pair archive. The selected pair ties6963/98F2;670D/969C has
the smaller ID.

Estimated variance is4.337739430296041e-5, RMS0.006586151707. Both packets
have q endpoints+/-8/449; recent endpoints are+0.135812500729 and
-0.405838581339, deriving the unchanged17/16 cycle. The pair's nominal area
is exactly449/898=50%. Independent32-transition periodic propagation agrees
with the quadratic variance within8.81e-20. Nine tests pass in0.715 s,
including every848 exact endpoint derivations, ranking, symmetry, guards,
table immutability and analytic propagation.

`all-pairs.npz` retains every filtered candidate/rank and exact endpoint
strings for all848 duty words. `report.json` records hashes, tie rules,
source-free scope and complete constraints; `select.py` reproduces the
selection in a fresh output directory. Root separately reproduces the same
literal from the prior archive and exact audit's permitted word lists.

Only words[32,16]/[32,17] change, preserving all2046 other words and every
successor. Whole64-bin closure remains18 states; dictionary counts change
138/96 to139/98 (+170 bytes of unrolled pattern code). The independent player
proof is in `../endpoint-idle-pair-player/`.

This is an ordinary-packet analytic estimate. Endpoint consistency is not
equivalence to each original greedy bit decision, bounded internal history,
low measured background, source generality or absence of AM/FM. Page/bank
excursions, full unchanged-filter corpus measurements and actual complete
emulator playback remain separate acceptance requirements.

```powershell
python audiobook-beeper/experiments/song-snr/evidence/endpoint-idle-pair-selection/select.py `
  --output .tmp/reproduce-endpoint-selection
```
