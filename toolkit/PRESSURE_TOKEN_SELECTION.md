# Reserve-pressure token selection: control measurements

Date: 2026-09-28. Input: all 4221 frames and 188 blocks of the `2881667`
Fast preview. The previous unweighted selection is `02e08b1`.

These two complete image-set comparisons were already performed before the
user clarified the desired optimizer workflow. **Do not use repeated complete
TRD-set evaluation as the automatic search strategy.** Use a sliding time
window for selection and one final set for complete playback validation.

## Method

Reuse all 1316 native candidate measurements. For each block, take the Q8
fraction of bytes requested without a completed slot. The pressure is the
maximum of its own fraction and the next two fractions divided by two/four.
This covers possible advance production in the three-slot ring. Compare
strengths 4 and 16, with weight `256 + strength * pressure_q8`. Minimize
weighted `(decoder T + 125 * bytes)` within the unchanged four-sector byte
margin. Weights are heuristic scores, not physical T-states. Strength zero
must reproduce the previous selection exactly.

No player instruction changes (substitution delta **0 T**), decoded pixel
changes, AY changes, buffer reductions or cross-disk RAM requirements occur.

| Metric | Fast baseline | Unweighted | Strength 4 | Strength 16 |
|---|---:|---:|---:|---:|
| Decoder T | 183122436 | 161110234 | 163920918 | 164990913 |
| Producer T, ROM mocked | 11831304 | 12165270 | 12161366 | 12165358 |
| Combined native T | 194953740 | 173275504 | 176082284 | 177156271 |
| Video bytes | 1818909 | 1880042 | 1880056 | 1880043 |
| Runtime video reads | 7106 | 7344 | 7344 | 7344 |
| Late frames | 1239 | 1149 | 1111 | 1105 |
| Bad fallback intervals | 744 | 680 | 638 | 640 |
| Summed publication span T | 1812124850 | 1811203044 | 1809997611 | 1810068518 |

Both policies occupy 2542 sectors per disk, leaving two free. Native savings
against Fast are **18871456 / 17797469 T** including the producer. ROM,
IRQ/ULA and drive service are excluded from these deterministic counts.
Carry copying is **96000 / 96256 bytes**. CPU savings alone rank the policies
differently from publication deadlines.

Strength 4 has **86/328/697** late frames and **33/183/422** bad intervals;
strength 16 has **81/326/698** and **30/184/426**. Their maximum lateness is
**58/218/205** and **57/219/206 fields**, actual maximum deviation
**4112664/15457944/14536155** and **4041768/15528852/14607053 T**.
Late-run recovery is **3/3, 9/10, 5/5** and **3/3, 8/9, 5/5**.
Both disk-2 runs remain behind at EOF. Every missed nominal deadline and
every recovery run is saved separately from fallback compliance.

All **25326 AY records remain exact at 50 Hz** with zero underruns/gaps/
duplicates. All 4221 frames reach EOF. Near-empty packet starts (at most six
ready bytes) fall from the unweighted **95/313/561** to **47/217/493** and
**45/215/492**. Median disk-2 reserve rises **12278→15023/15163 bytes**.

Actual read/seek service totals are **228207857 / 5130218 T** and
**228148091 / 5128326 T**. Do not add these again to overlapping stage
elapsed times. Initial disk/IRQ phases were not matched; observed elapsed
differences are not isolated CPU savings.

## Verification, decision and reproduction

Every selected block is rerun with the real sector/carry producer, guarded
native Fast code, all output bytes/cursors, protected RAM and instruction
counts. Dirty-RAM boots, prime screens and mocked-ROM disk swaps pass.
Complete independent Fuse boots check all sectors, publications and AY plus
80 pixel samples per frame, without RAM patches or fast-read retries. No
hardware, interactive disk replacement or full Fuse pixel comparison was
performed. The unchanged frame code/data retain their prior full-screen CPU
proof. Both nominal and fallback video gates **still fail**.

Keep both as control evidence; current root images remain unchanged. The
next automatic selector must work with a bounded moving time horizon,
carrying buffer state and disk-space budget between windows. One final
EOF run validates the selected images. It must never call an estimated
window schedule a release pass.

The initial host selector failed on `max(single_integer)` at the last
block before writing any selection/build report. Passing a list fixes this
one-element boundary; the corrected zero-weight control and both complete
measurements then passed.

Reproduce with [pressure_zx0_tokens.py](pressure_zx0_tokens.py) `--write`,
then [build_pressure_token_player.py](build_pressure_token_player.py)
`--policy weight4` or `--policy weight16` using the same raw/states/ZX0/cache
arguments as [the previous experiment](FAST_TOKEN_PLAYER.md). These commands
are historical controls, not the proposed automatic production workflow.
Run the existing `benchmark_fast_token_player.py`,
`measure_integrated_bootstrap.py` and `snapshot_resident_audio_player.py`
against each separate build folder. The saved build and CPU reports are
`pressure_token_weight{4,16}_{build,cpu}.json`; complete traces and source
snapshots are in `pressure_token_evidence/weight{4,16}`.

Audit all evidence without rerunning the emulator:

```powershell
python toolkit/summarize_pressure_token_player.py
```

[Selection report](pressure_zx0_tokens.json) ·
[Full comparison](pressure_token_summary.json) ·
[Auditor](summarize_pressure_token_player.py).
