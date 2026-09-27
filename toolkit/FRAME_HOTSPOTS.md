# Full-frame CPU profile and rejected output shortcuts

Date: 2026-09-27. **Measurement and analytical probes only; no player change.**
The working baseline is the HL-reader experiment at `074e1e7`, with the
uncontended compact/cache layout and inline Huffman patches. The later
streaming-input experiment remains disabled because its complete playback
was slower overall. The current profiling tools were added after `8da95ed`.

## Coverage and evidence

[The profiler](profile_frame_hotspots.py) executed all **4221 frames** across
three independently initialized volume fixtures: 1624 / 1297 / 1300 frames.
It checked every compact byte and both complete 6912-byte native screens
against the saved frame states, plus the existing cursor, cache, paging and
workspace checks. Every executed instruction was checked against the timing
in its generated listing. Instruction addresses include the RAM bank, so
bank-6 Huffman code and bank-7 metadata code cannot be confused.

Every frame's CPU total equals its earlier
[inline-Huffman baseline](inline_huffman_patches_cpu.json) minus the already
verified **499 T** for the HL metadata reader. The totals below do not claim
an additional saving. Player CPU delta: **0 T**; compressed stream delta:
**0 bytes**.

Packets are supplied by the host. ZX0, packet copying, queue work, AY/IRQ,
ULA contention, TR-DOS execution and physical disk latency are excluded.
This is a complete CPU-stage profile, **not a new playback or release check**.
The generated listings are not an independent disassembly or hardware trace.

- [Full per-frame and per-instruction profile](frame_hotspot_profile.json)
- [Compact audited summary](frame_hotspot_summary.json)
- [Saved-evidence auditor](audit_frame_hotspots.py): source hashes, frame
  order, per-frame baseline, stage totals, instruction totals and probe
  arithmetic; it does not repeat Z80 execution or pixel comparisons.

## Measured CPU distribution

| Stage | T-states | Share of this profile |
|---|---:|---:|
| Reconstruction | 620,300,899 | 60.36% |
| Native output | 337,654,716 | 32.85% |
| Compiled metadata | 63,590,055 | 6.19% |
| Attribute-group preparation | 4,569,974 | 0.44% |
| Handoff | 1,603,980 | 0.16% |
| **Total** | **1,027,719,624** | **100%** |

Per-volume totals are **388,574,871 / 329,687,365 / 309,457,388 T**.
The earlier total was 1,029,825,903 T; its difference of 2,106,279 T is
exactly `4221 * 499`, already attributed to the HL reader.

The largest individual stage labels are dense pixel output (136,520,064 T),
Huffman (131,131,792 T), cache maintenance (112,146,097 T), sparse pixel
output (80,589,740 T), patch application (80,521,194 T), no-op traversal
(74,830,741 T), motion (66,883,657 T) and general reconstruction control
(66,807,315 T). A stage's total includes useful work; it is not an estimate
of removable overhead.

The remaining indexed memory loads execute **1,203,077 times**, costing
22,858,463 T. Replacing each 19-T load with a 7-T `(HL)` load would save
14,436,924 T **before any address setup, cursor work or register saves**.
This is an optimistic bound for those loads alone, not an implementation or
a bound for all possible register-allocation changes. Huffman already uses
HL for table lookup; replacing IX everywhere is not free.

## Rejected probe: nearly full bands

[The probe](profile_dense_band_threshold.py) parses the exact archived
compressed streams from all three TRDs: 378 ZX0 blocks, 4221 packets and
75,978 visible native-map bands. It verifies stream/archive hashes and
records every band's common bits, marked-cell count and parity in
[the report](dense_band_threshold_profile.json).

Candidate: insert `OR constant` before the existing all-FF band test, allowing
some unchanged cells to be redrawn from the exact reconstructed frame.
The scan covers zero, all eight single-bit constants and all 28 two-bit
constants. A nonzero constant costs **7 T per band = 126 T per frame**.
For a newly dense band, the existing renderer formula gives:

```text
additional T = 5853 + 4 * band_parity - 261 * marked_cells
```

This formula assumes no zero mask byte; accepting only bands with at least
24 marked cells under these bit tests guarantees that condition.

**Result:** none of the 36 nonzero constants accepts a single additional
band. Each adds **531,846 T** over the movie. The actual stream contains
bands with 0..17 or 32 marked cells, never 18..31. The encoder already rounds
bands with at least 18 changed cells to a full band in
[native-mask generation](probe_cell_output_masks.py).

**Decision:** reject the extra test for the current stream. This does not
prove that another encoder density threshold is worse; changing that
threshold needs a separate compression and total-delivery experiment.

## Rejected probe: full groups of eight cells

Candidate: within a partial band, test for a mask byte of FF and draw eight
cells row by row. Existing work for a full group is:

```text
8 * (ADD A,A 4 + CALL 17 + draw_cell 254 + INC L 4 + INC E 4)
= 2264 T
```

The proposed helper is estimated at **1919 T**, including its final jump:
15 T to set an alternate row counter, 32 pixels at 51 T, four 22-T row tests,
three 48-T row advances and 40 T to restore position and exit.
However, `CP FF; JP Z,helper` adds **17 T to every nonzero partial-band group**.
The stream has 4237 full groups among 148,104 nonzero groups:

```text
17 * 148104 - (2264 - 1919) * 4237 = +1056003 T
```

**Decision:** reject this dispatch strategy before implementation. These are
instruction-formula estimates; no new helper was assembled, placed in RAM,
tested under IRQ or measured in Fuse. Other dispatch designs remain untested.

## Reproduction

From the repository root, with the existing Python dependencies available:

```powershell
python toolkit/audit_frame_hotspots.py
python toolkit/profile_dense_band_threshold.py
```

The dense probe uses committed compressed-stream archives. A full CPU rerun
also needs the original raw volumes and the saved conversion states; their
hashes are checked before execution. In the measured worktree:

```powershell
python toolkit/profile_frame_hotspots.py --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz
```

Those local input directories are not bundled by this experiment. A smoke
run with `--limit 2 --output .tmp/frame_hotspot_smoke.json` preceded the full
run and is explicitly marked incomplete. The saved-evidence audit is the
portable check; it cannot substitute for executing the complete CPU fixture.

## Next decision

Use the measured instruction frequencies to evaluate complete sequences in
cache maintenance, reconstruction control and output. Keep the remaining
IX/HL audit, but rank it by net saving after register preservation. Follow
the current [decode-speed plan](DECODE_SPEED_PLAN.md), then validate any
accepted implementation in the full three-volume player. Existing release
TRDs are unchanged; nominal deadlines and continuous AY remain unresolved.
