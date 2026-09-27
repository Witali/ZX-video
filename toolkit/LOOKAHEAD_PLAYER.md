# Two-byte Huffman cache in the three-disk player

Date: 2026-09-27. Baseline: compact-cursor playback at `7a1d5de`;
integration starts from the CPU prototype at `2995503`.
**Complete experimental disk playback; timing still fails, not a release.**

## Input contract and code installation

The optional `--cached-huffman-lookahead` setting integrates the
[validated register-cache prototype](CACHED_HUFFMAN_LOOKAHEAD.md) before
inline Huffman code is generated. B'/E' cache the current/next input byte;
C' retains the bit position. Motion uses HL' instead of DE'. The same
7-byte helper at 8FC0 and 875-byte bank-6 inline body are installed at cold
boot. No debugger patches are used.

[The installer](lookahead_player.py) enforces a **4702-byte** maximum FAP3
payload in the existing **4704-byte** window. The old maximum was 4703.
It changes only the immediate operand of the length-range check:
**10→10 T, delta 0**, same three-byte instruction length. The complete valid
range-check sequence remains **94 T**. No additional copy, guard write,
stream byte or allocated RAM is needed. The parser still initializes one
zero guard. A second byte is reserved for read-only speculative lookahead;
its value may be arbitrary and cannot affect a valid decoded symbol.

All 4221 actual packets fit; per-volume maximum payloads are
**2638 / 2921 / 3645 bytes**. The host rejects oversized packets before
building this optional configuration, and the runtime range check also
rejects them. Generic converter defaults are unchanged.

The [cold-code verifier](verify_integrated_bootstrap.py) reconstructs the
pre-inline source independently, before bank-2 ZX0 overwrites the retired
fixed patch body. It checks cache regions, labels and motion substitutions
against the complete CPU prototype, regenerates inline code, and compares
that code with actual cold-installed RAM. All three volumes pass.

## Size and deterministic CPU cost

The compressed movie stream remains **1,919,945 bytes**, with unchanged
7501 video sectors. The three disks use **2542 / 2543 / 2542 sectors** out
of 2544; **2 / 1 / 2** remain free. Video starts at sectors **53 / 58 / 60**,
unchanged from compact cursor. Each disk boots independently with dirty RAM.
Mocked-ROM swaps 1→2→3 verify the prompt and reject wrong disks/series.

The full frame-stage comparison remains
**1,023,364,329→1,018,049,241 T (-5,315,088; -0.5194%)**:

- Shared short bitmap symbol: **145/169→134/162 T**, excluding CALL and
  including RET, without/with a byte crossing.
- Long symbols: **+18 T**; absolute case counts are in the prototype report.
- Frame initialization: **19→65 T (+46)**; 55 frames have small net penalties.
- Integrated packet parser: **delta 0 T**.

These frame CPU totals exclude ZX0, queue/copy work, AY/IRQ, ULA, ROM and
disk latency. The separate replay of actual queue calls accounts for its
deterministic CPU. Fuse elapsed disk/seek service remains separate; it is
not presented as instruction cost or a physical-drive measurement.
All **25,955 actual queue calls** replay exactly (10,856 / 7,491 / 7,608).
Queue plus full AY-wait CPU changes **289,460,171→289,570,034 T (+109,863)**:
slightly more background work offsets part of the frame-stage saving.
This cost is included in the saved comparison, not subtracted as idle time.

## Complete Fuse playback

All three independent runs reach EOF. All **25,326 AY records** match,
and every frame's sampled screen bytes match. Full compact-frame and both
6912-byte screen comparisons come from the separate 4221-frame CPU run;
Fuse checks 80 samples per frame and does not replace that full comparison.

| Volume | Frames | Previous fps | New fps | Late frames, before→after | AY underruns, before→after |
|---|---:|---:|---:|---:|---:|
| 1 | 1624 | 8.284839 | 8.287377 | 984→984 | 78→75 |
| 2 | 1297 | 7.986197 | 7.995065 | 837→834 | 333→324 |
| 3 | 1300 | 7.889942 | 7.901460 | 1249→1248 | 458→446 |

The summed publication span changes **1,853,606,028→1,851,904,234 T**,
**-1,701,794 T**. These runs do not match the initial IRQ/disk phase, so the
elapsed difference is an observed comparison, not an instruction-count
prediction. Timing remains substantially outside the acceptance criteria:

- **3066** late nominal frames, versus 3070 previously.
- **845** AY underruns, versus 869; all records eventually play, but cadence
  is not continuous.
- **644** intervals outside the fallback range, versus 662.
- Maximum late fields **79 / 329 / 451**; maximum actual deviations
  **5,601,733 / 23,328,729 / 31,979,514 T**.
- Recovered late runs **0 / 3 / 2**. The final runs beginning at local
  frames **640 / 478 / 56** remain late through each volume's EOF.

**Decision:** retain the optional cache as a measured improvement with the
same disk capacity and pixels. Exact nominal deadlines, one-field fallback
and AY continuity all remain open. Root release images are unchanged.
Prioritize larger reconstruction, output and producer-scheduling costs;
this small cache saving cannot resolve the remaining timing deficit alone.
The pipeline trace identifies **460 / 397 / 619 frames** whose foreground
stages alone exceed six fields. It finds **zero** late frames already
native-ready at least 1000 T before their actual nominal deadline. Merely
changing the publication branch cannot fix these cases. Empty-input waits
total **134,642,123 elapsed T**, including producer work and disk service;
do not treat that entire quantity as removable CPU overhead. Further
lookahead/buffering work must demonstrate that it prepares these expensive
frames earlier without starving AY or increasing sector acquisition.

## Verification and reproduction

[Four integration tests](test_lookahead_player.py) execute both old/new range
checks at boundary lengths, compare in-place packet decoding and parser
cycles, verify pixels/AY, exercise empty input with four arbitrary second
guard values, and reject a 4703-byte optional packet on the host. The
prototype's exhaustive symbol/IRQ evidence remains separately pinned.

Run from the measured worktree with the existing Python dependencies:

```powershell
python -m unittest test_lookahead_player -v
python toolkit/build_integrated_bootstrap.py --directory ../cached-huffman-byte/.tmp/three --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/lookahead-player --report toolkit/lookahead_player_build.json --bank2-zx0 --audio-wait-prefetch --fast-return-irq --hl-mask-reader --compact-cursor --cached-huffman-lookahead
python toolkit/verify_integrated_bootstrap.py --directory .tmp/lookahead-player --baseline-directory ../cached-huffman-byte/.tmp/three --raw-directory ../volume-huffman/.tmp/probe --report toolkit/lookahead_player_build.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/lookahead-player --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/lookahead-player-fuse --trace-pipeline --trace-queue-calls --trace-fields
python toolkit/replay_queue_calls.py --directory .tmp/lookahead-player --trace-directory .tmp/lookahead-player-fuse --output .tmp/lookahead_player_queue_cpu.json
python toolkit/summarize_lookahead_player.py --fuse .tmp/lookahead-player-fuse --directory .tmp/lookahead-player --cpu .tmp/lookahead_player_queue_cpu.json
python toolkit/summarize_lookahead_player.py
```

The [build report](lookahead_player_build.json) and
[audited playback summary](lookahead_player_summary.json) pin source and
evidence hashes. Thirteen new gzip archives retain traces, debugger scripts,
metadata and the complete queue replay (8,539,773 bytes); the older baseline
archives are referenced in place. The last command rechecks saved evidence without rerunning
Fuse. Raw movie fixtures are local inputs, not bundled in this experiment.
