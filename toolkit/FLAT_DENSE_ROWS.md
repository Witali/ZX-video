# Whole-row fill dispatch: rejected by a complete input profile

Date: 2026-09-27. Baseline sources: `7a1d5de`. **No player change or new
playback run.** This tests two possible additions to the current native
renderer without changing compressed data or pixel values.

## Candidate and result

Before the normal dense-row pixel body, recognize either an entirely zero
compact row or a row of 32 identical compact bytes. A recognized row could
reuse one pair of dither results and fill the two native rows. A rejected
row executes the complete existing pixel body. Common row, page and band
control stays unchanged.

The [profiler](profile_flat_dense_rows.py) covers all **4221 frames** and
three independent-volume starts. There are **83,652 dense compact rows**:
only **90 are zero** and **332 are uniform**, including those zero rows.
Each expands to two 256-pixel native rows. Black borders already omitted
by the player are outside this count. Sparse bands are outside this probe.

| Whole-row candidate | Immediate failures | Successful rows | Optimistic total CPU delta |
|---|---:|---:|---:|
| All zero | 69,572 first bytes are nonzero | 90 | **+1,314,132 T** |
| All equal | 48,895 first pairs differ | 332 | **+1,022,816 T** |

Positive numbers mean slower. These are lower bounds for the stated
dispatch strategies, not measured costs of implemented routines.

## Instruction accounting

The existing generated dense pixel body costs **32 × 51 = 1632 T** per
compact row, excluding its common row control. Across the movie this is
**136,520,064 T**. The probe checks this total separately for every frame
against the previously executed [CPU profile](frame_hotspot_profile.json).

The zero test rejects immediately with:

```text
LD A,(HL)       7
OR A            4
JP NZ,normal   10
               --
               21 T
```

The uniform test's first unequal pair costs:

```text
LD A,(HL)       7
INC L           4
CP (HL)         7
JP Z,scan_more 10
DEC L           4   ; Restore the source cursor and fall into normal output.
               --
               32 T
```

Rows are aligned to 32 bytes, so this first-pair cursor advance cannot cross
a page. Instruction timings use the same
[Zilog table](https://www.zilog.com/docs/z80/um0080.pdf) as the baseline.

To give the candidates an unrealistically favorable bound, charge only
these immediate failures. Make every remaining test and failed scan free.
Make successful fills free too, removing all 1632 T of pixel work:

```text
Zero:    69572 × 21 −  90 × 1632 = +1314132 T
Uniform: 48895 × 32 − 332 × 1632 = +1022816 T
```

Even those optimistic replacement-body totals are **137,834,196** and
**137,542,880 T**, versus **136,520,064 T** today. Real scans, fills and
dispatch placement would add work. This argument does not rule out
partial-row fills, precomputed hints or a different output format.

## Evidence and decision

The [saved report](flat_dense_rows_profile.json) includes state/source/report
hashes, both offset histograms, per-volume results and per-frame candidate
counts. The input states match the full CPU profile's SHA-256. Dense bands
come from the [archived-stream mask profile](dense_band_threshold_profile.json);
their row counts must match the executed pixel-stage T-states on every frame.
This includes the full masks needed at independent disk starts.

**Reject both tests before implementation.** Do not spend fixed RAM or add
bootstrap bytes on them. Actual player CPU delta is **0 T**; stream delta
is **0 bytes**. No new assembly, IRQ, ULA contention, disk delivery, audio,
pixel rendering or release timing has been tested by this probe. Existing
late frames and AY gaps remain unresolved.

Reproduce from the measured worktree:

```powershell
python toolkit/profile_flat_dense_rows.py --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz
```

The saved source states are a local input, not bundled with this experiment.
The probe rejects a different state hash or renderer source. Keep the
[decode-speed plan](DECODE_SPEED_PLAN.md) focused on other remaining costs.
