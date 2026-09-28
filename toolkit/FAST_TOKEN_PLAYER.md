# Faster reservoir refill through lossless ZX0 token selection

Date: 2026-09-28. Baseline: the integrated Fast preview at `2881667`.
The experiment covers all 4221 frames, 188 blocks and three independent
disks. It preserves all decoded video/AY bytes and changes no player
instructions. It is **not a release**: both video timing gates still fail.

## Method and capacity

For every 15872-byte block, test keeping the original ZX0 stream or removing
matches shorter than 2, 3, 4, 5, 6 or 8 bytes. Replaced matches become literal
bytes; adjacent literal runs merge. Longer literal copies avoid some token
dispatch and length/offset decoding. The Fast decoder and its format remain
unchanged. This trades disk space for fewer executed instructions, without
changing a pixel or AY record.

[The probe](probe_fast_zx0_tokens.py) executes all **1316 candidates** with
256-byte output demands and checked instruction timings. Every candidate
also passes overlap placement at all 256 stream offsets. A smoke check used
one block per volume before the full probe. Existing `test_zx0_speed.py`
tests pass, including offset-state and randomized round trips.

The exact multiple-choice size/CPU selector charges **125 T per added byte**,
rounded up from baseline observed read/seek service. This is a ranking
heuristic, not a prediction of actual deadlines. Compare CPU-only and twice
that charge in the saved probe. The unconstrained-to-capacity selections fill
all disks; the actual build subtracts four sectors from byte capacity first.
Physical interleave leaves **two free sectors per disk**, as measured from
the completed images. No buffer is reduced and no persistent state crosses
disks.

| Disk | Video bytes, before → after | Read sectors, before → after | Occupied / free sectors |
|---|---:|---:|---:|
| 1 | 606434 → 626943 | 2369 → 2449 | 2542 / 2 |
| 2 | 606524 → 626686 | 2370 → 2448 | 2542 / 2 |
| 3 | 605951 → 626413 | 2367 → 2447 | 2542 / 2 |

Total stream: **1818909 → 1880042 bytes**, +61133 / **3.361%**.
Read sectors increase **7106 → 7344**, +238. Video starts remain 107/108/109.
The same independent bootstrap, screen buffers, 47616-byte slot reserve,
Huffman tables, disk-swap behavior and 50-Hz audio are retained.

## Deterministic CPU, excluding ROM/IRQ/ULA/disk time

The [selected-stream benchmark](benchmark_fast_token_player.py) reads the
actual three TRDs and runs their entire producer/decoder streams, checking
every output byte, input cursor, overlap and protected RAM. Every block's
decoder count matches its isolated candidate measurement. Actual producer
sector order, boundary carry and all instruction-table totals are checked.

| Component | Baseline T | Selected T | Difference T |
|---|---:|---:|---:|
| Fast ZX0 decoder | 183122436 | 161110234 | -22012202 |
| Sector/carry producer, ROM mocked | 11831304 | 12165270 | +333966 |
| Combined | 194953740 | 173275504 | **-21678236** |

Decoder savings are **12.0205%**, combined **11.1197%**. Carry copies remain
96256 bytes. These percentages apply only to these components, not the
whole player. Per-instruction costs and emitted player instructions do not
change (**0 T substitution delta**); the stream changes execution counts.
Full per-block, per-call and instruction histograms are saved.

## Complete Fuse playback and reserve

All 4221 publications and 25326 AY records reach EOF from independent cold
boots. AY remains exact at 50 Hz with zero underruns, record gaps or
duplicates. No debugger RAM patches or fast-read retries are used.

| Disk | Late frames, before → after | Bad fallback intervals, before → after | Maximum late fields | Recovered late runs |
|---|---:|---:|---:|---:|
| 1 | 86 → 87 | 41 → 42 | 65 | 2/2 |
| 2 | 404 → 348 | 230 → 203 | 235 | 10/11 |
| 3 | 749 → 714 | 473 → 435 | 214 | 5/5 |
| Total | **1239 → 1149** | **744 → 680** | — | — |

Disk 2 still ends without recovery of its final late run. Maximum actual
publication deviations are **4609027 / 16663380 / 15174309 T**. Effective
rates are **8.333333 / 8.088878 / 8.333333 fps**. Equal average rate does
not establish evenly spaced frames. The summary lists every missed nominal
deadline and all recovery runs, separately from fallback compliance.

Summed first-to-last publication span falls **1812124850 → 1811203044 T**,
only **921806 T / 0.0509%**. Observed read service rises **220795861 →
228199242 T**, and seek service **5000232 → 5130002 T**. These elapsed
measurements include IRQ/ULA/ROM/drive effects and must not be added to
overlapping frame-stage elapsed times. Initial disk/IRQ phases were not
matched; elapsed differences cannot be attributed solely to CPU savings.

| Disk | Median decoded reserve, before → after | Packet starts with ≤6 ready bytes, before → after |
|---|---:|---:|
| 1 | 30148 → 30243 | 99 → 95 |
| 2 | 9840 → 12278 | 478 → 313 |
| 3 | 4 → 10 | 740 → 561 |

Queue positions are checked at every packet against slot ownership and the
47616-byte bound. Faster refill increases useful advance work, but sustained
starvation remains, especially on disk 3. Compact preparation is at least
one nominal frame period early for **1503 / 890 / 568 frames**.

## Decision and coverage limits

Keep this as an optional measured experiment. Do not replace the current
Fast root preview: disk 1 regresses by one late frame and one bad interval,
the free-space reserve shrinks to two sectors, and both timing gates fail.
Further selection should account for where CPU savings build useful reserve
before difficult runs, not merely sum savings over a disk. The deeper
prepared-command queue remains a separate proposal in
[the preparation plan](FRAME_PREPARATION_RESERVE.md).

Dirty-RAM boot, first native/second compact frame, immutable audio bank and
next-disk/wrong-disk code checks pass; disk reads are mocked for those CPU
checks. Fuse separately checks all actual publications, sectors and AY,
plus 80 screen-byte samples per frame. Unchanged decoded frame data and
code retain the prior all-frame full-screen CPU proof. There was no complete
pixel comparison inside Fuse, interactive disk replacement or hardware run.
Generated TRDs remain in the ignored experiment folder; no release images
or existing root previews are replaced.

## Reproduction

Use project Python dependencies and `PYTHONPATH=toolkit`. The probe and
native benchmark refuse to overwrite evidence; use fresh output paths for
another attempt. Original streams are archived in the repository; building
and Fuse additionally use the existing movie states, raw volumes and ZX0
executable/cache.

```powershell
python toolkit/probe_fast_zx0_tokens.py
python toolkit/build_fast_token_player.py --baseline-build toolkit/fast_zx0_player_build.json --probe toolkit/fast_zx0_tokens_probe.json --raw-directory .worktree/volume-huffman/.tmp/probe --states .worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 .worktree/audio-fidelity/.tmp/bin/zx0.exe --read-cache .tmp/fast-zx0-player/zx0 --read-cache .worktree/streaming-zx0-player/.tmp/inplace-keepalive-player/zx0 --read-cache .worktree/streaming-zx0-player/.tmp/inplace-zx0-cache --output .tmp/fast-token-player --report toolkit/fast_token_player_build.json
python toolkit/benchmark_fast_token_player.py --directory .tmp/fast-token-player --build toolkit/fast_token_player_build.json --probe toolkit/fast_zx0_tokens_probe.json --output toolkit/fast_token_player_cpu.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/fast-token-player --raw-directory .worktree/volume-huffman/.tmp/probe --states .worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/fast-token-fuse --trace-pipeline --trace-fields
python toolkit/snapshot_resident_audio_player.py --build toolkit/fast_token_player_build.json --directory .tmp/fast-token-player --fuse .tmp/fast-token-fuse --output toolkit/fast_token_player_evidence
python toolkit/summarize_fast_token_player.py --write
```

Audit existing evidence without rerunning the emulator:

```powershell
python toolkit/summarize_fast_token_player.py
```

Evidence: [all candidates](fast_zx0_tokens_probe.json),
[build](fast_token_player_build.json), [native CPU](fast_token_player_cpu.json),
[summary](fast_token_player_summary.json),
[archived source/metadata/full traces](fast_token_player_evidence/manifest.json).
