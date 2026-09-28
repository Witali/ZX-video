# Automatic optimization with a sliding time window

Measured on 2026-09-28. This implements the requested bounded search for
prepared streams. It does not yet replace the media frontend in
`convert_video.py`, and it is not a timing-qualified release.

## Workflow

[`windowed_zx0_planner.py`](windowed_zx0_planner.py) evaluates at most
**64 future frames (7.68 seconds)** for each decision. It commits the next
ZX0 block when the producer can admit it. The following block remains
tentative. With seven lossless token variants, a decision compares at most
49 pairs. It never creates alternative disk images or starts Fuse.

The model carries these values between windows:

- Decoded-slot ownership, consumer position, partially completed producer
  work and the amount of available data.
- Pending packet, reconstruction/drawing stage and absolute six-field
  deadlines. A late frame does not move the schedule origin.
- Committed compressed bytes and space reserved for the remaining blocks.
  Every trial must fit the complete volume, including the byte margin.

The first three blocks use the size-first baseline: they are decoded before
playback starts. An additive CPU/byte allocation reserves capacity for
future choices. Local selection then minimizes predicted accumulated
lateness, late-frame count and maximum lateness, with size as a tie breaker.
No pixels or AY records change. This experiment selects ZX0 tokenization;
it does not yet change the depth of prepared frame commands.

[`optimize_prepared_player.py`](optimize_prepared_player.py) runs planning,
builds **one selected set**, verifies its bytes and native CPU costs, and
performs one complete independent Fuse playback per final disk. It also
checks dirty-RAM startup and the actual swap code with TR-DOS mocked.
Timing failures remain explicit in `timing.json`; successful execution of
the script means the experiment completed, not that playback passed.

## Cost model and limits

The selector reuses cached native measurements for each safe block variant.
It rejects variants without byte-exact decoding and in-place safety at all
256 placement offsets. Candidate measurement and media conversion are
**not included** in the planning time below.

Input acquisition uses an average 125 T per compressed byte plus 7 T of
producer CPU. Input sectors and measured 256-byte decoder slices are atomic
jobs; decoder costs receive a 51/50 elapsed-time multiplier. Frame drawing
and preparation reuse baseline elapsed stage costs after subtracting disk
service. Packet copying is estimated as 16 T/byte + 800 T. The three slots
hold at most 47616 decoded bytes. These constants and every window decision
are saved in the selection report.

This is an approximate scheduler: it does not reproduce ULA/IRQ phase,
rotational disk latency or the player's varying decoder demand sizes. The
baseline calibration predicts **47/179/427** late frames where Fuse measures
**86/404/749**. The selected schedule predicts **45/148/402** but actually
produces **89/382/715**. Neither estimate may satisfy release gates.

## Complete final-set measurement

Input: the same 4221-frame authorized edit, baseline Fast player, 188 blocks,
1624/1297/1300 frames per volume and unchanged 25326 AY records. Planning
took **3.215 seconds**, with **6198 local comparisons**. Search built zero
alternative TRDs and ran zero alternative complete playbacks. The final
check built three TRDs and ran three complete Fuse playbacks through EOF.

| Metric | Fast baseline | Window-selected set |
| --- | ---: | ---: |
| Compressed video bytes | 1818909 | 1866452 |
| Runtime video sectors | 7106 | 7292 |
| Native ZX0 decoder T-states | 183122436 | 171302085 |
| Native producer T-states | 11831304 | 12083942 |
| Combined native T-states | 194953740 | 183386027 |
| Late frames | 1239 | 1186 |
| Invalid fallback intervals | 744 | 665 |
| Summed publication span, T-states | 1812124850 | 1809713979 |
| AY underruns | 0 | 0 |

No player opcode changes: instruction-substitution delta **0 T**. Different
token execution counts save **11820351 decoder T**, add **252638 producer T**
and save **11567713 combined T**. Native totals exclude TR-DOS ROM execution,
disk latency, IRQ and ULA contention. Measured Fuse read service is
**226573372 T** and seek service **5110379 T**; these elapsed intervals
already overlap stage durations and must not be added twice.

| Final disk | Bytes | Occupied/free sectors | Late frames | Bad intervals | Peak lateness, fields | Recovered late runs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 614364 | 2493 / 51 | 89 | 37 | 56 | 3 / 3 |
| 2 | 626496 | 2542 / 2 | 382 | 196 | 214 | 10 / 11 |
| 3 | 625592 | 2540 / 4 | 715 | 432 | 213 | 5 / 5 |

Maximum actual publication deviations are **3970853 / 15174312 / 15103422 T**.
Disk 2 remains late at EOF. All 25326 AY records are exact at 50 Hz, with
zero underruns, missing fields or duplicate fields. Every nominal miss,
actual deviation and recovery run is retained in the
[audited report](windowed_player_summary.json).

All selected compressed blocks execute through guarded native decoding;
instruction-table sums, output, overlap and sector order pass. Whole decoded
video and AY hashes match the baseline. Complete Fuse runs check every
publication and AY record, every runtime sector and 80 pixel samples per
frame. The unchanged frame code retains its earlier full-frame CPU proof.
There is no full-screen comparison inside Fuse or physical-drive test.

**Decision:** retain the windowed mechanism and its evidence as an automatic
experimental path. Keep the existing root images and release unchanged.
Disk 1 regresses by three late frames. The previously completed unweighted
and pressure controls have 1149 and 1105 late frames respectively; the
window model has not surpassed them. Both video timing gates still fail.

## Reproduction

Python dependencies and fixture files are the same as in
[Fast token selection](FAST_TOKEN_PLAYER.md). Run from the repository root:

```powershell
python -m unittest discover -s toolkit -p test_windowed_zx0_planner.py
python toolkit/plan_windowed_tokens.py --window-frames 64 --output .tmp/new-window-plan.json
python toolkit/optimize_prepared_player.py `
  --raw-directory .worktree/volume-huffman/.tmp/probe `
  --states .worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz `
  --zx0 .worktree/audio-fidelity/.tmp/bin/zx0.exe `
  --fuse "C:/Program Files (x86)/Fuse/fuse.exe" `
  --read-cache .tmp/fast-zx0-player/zx0 `
  --read-cache .worktree/streaming-zx0-player/.tmp/inplace-keepalive-player/zx0 `
  --read-cache .worktree/streaming-zx0-player/.tmp/inplace-zx0-cache `
  --window-frames 64 --output .tmp/new-window-player
```

Paths above identify the measured fixture, not a restriction of the planner.
Supply matching `--probe`, `--profile` and `--baseline-build` reports for a
different prepared movie. Output directories must be new. Missing local
media/cache files cannot be reconstructed from the evidence archive alone.
An existing archive audit needs neither Fuse nor original media:

```powershell
python toolkit/audit_windowed_player.py
```

[Planning-only report](windowed_tokens_plan.json) ·
[Final evidence manifest](windowed_player_evidence/manifest.json) ·
[Audit script](audit_windowed_player.py)

## Next work

1. Calibrate local windows against saved actual stage, IRQ and disk events.
   Test difficult intervals with the real entering buffer state; a fresh,
   full reservoir at every window boundary would invalidate the comparison.
2. Generate/cache per-input block costs and frame costs automatically from
   `convert_video.py`, including short clips and independent volume starts.
   The prepared-report adapter is not complete generic media integration.
3. Extend local choices to previously measured fragment/mask strategies and
   prepared-command depth. Preserve predictor dependencies and all RAM costs.
4. Continue using bounded candidate trials and one final selected-set EOF
   check. Improve the model before spending another complete playback on
   an uncalibrated search-policy variation.
