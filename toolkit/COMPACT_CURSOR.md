# Compact tile cursor: byte updates within a stripe

Date: 2026-09-27. Source baseline `b3f33fc`; playback comparison is the
HL-reader configuration at `074e1e7`. **Experimental option, not a release.**

## Change and invariant

[The implementation](compact_cursor.py) replaces two cursor-update sequences
without moving code or changing public labels. A compact stripe starts on
a 256-byte page. Tiles begin at even columns 0..30 and advance to at most
column 32. Neither a normal tile nor a skipped no-op run can carry into the
address's high byte. The existing full-address stripe transition remains.

The ordinary tile uses an accumulator load/add/store on the low byte. The
no-op path loads the address of that byte into HL, adds twice the run length
and writes one byte. Its final jump skips two cleared padding bytes. The
successor paths overwrite temporary registers/flags before using them.
The regular stack stays available for IRQ throughout.

| Sequence | Before | After | Delta |
|---|---:|---:|---:|
| One normal tile advance | 40 T | 33 T | -7 T |
| One no-op run advance | 62 T | 42 T | -20 T |
| Fixed code-region sizes | 8 + 12 bytes | 8 + 12 bytes | 0 bytes |
| Extra RAM / stack / compressed movie bytes | 0 | 0 | 0 |

Counts use the [Zilog timing table](https://www.zilog.com/docs/z80/um0080.pdf),
excluding IRQ, ULA and disk. Exact old/new bytes and instruction listings
are saved in build and CPU metadata. The integrated builder exposes
`--compact-cursor`, disabled by default.

## Completed verification

- Four [tests](test_compact_cursor.py) pass: every ordinary cursor column
  in all twelve compact pages; no-op lengths/starting columns with masks
  and vector-page crossings; four complete mixed frames; both real AY/video
  IRQ paths at every replacement instruction boundary.
- All three images fit and boot from dirty RAM independently. Mocked-ROM
  disk swaps 1→2→3 show the prompt, reject wrong disks/series and accept the
  proper continuation. The regenerated runtime bytes match the cold boots:
  2413 / 2413 / 2418 fixture bytes plus 875 inline-Huffman bytes per disk.
- Used sectors: **2542 / 2543 / 2542**, leaving **2 / 1 / 2** free. Video
  starts at 53 / 58 / 60, unchanged from the HL-reader run. The 1,919,945
  compressed stream bytes and 7501 video sectors are unchanged.
- Complete Fuse playback reaches all three EOFs. It checks every AY record,
  sector and 80 native-screen sample bytes per frame; this is not a full
  pixel comparison in Fuse or a physical-drive test.
- All **4221 frames** pass the CPU replay: every compact byte and both
  complete screens match, and each frame's cycle delta matches its actual
  cursor-call counts. A six-frame smoke run preceded the full run.
- All **25,677 actual queue calls** pass separate Z80 replay, including
  copied bytes, buffer state, sector order and instruction timing.

| Volume | Baseline frame CPU | New frame CPU | Delta |
|---|---:|---:|---:|
| 1 | 388,574,871 T | 386,925,436 T | -1,649,435 T |
| 2 | 329,687,365 T | 328,284,145 T | -1,403,220 T |
| 3 | 309,457,388 T | 308,154,748 T | -1,302,640 T |
| **Total** | **1,027,719,624 T** | **1,023,364,329 T** | **-4,355,295 T** |

There are 322,025 ordinary advances and 105,056 no-op run advances. Their
combined sequence cost is **19,394,472→15,039,177 T**. The full-frame
comparison includes metadata, reconstruction and output, but excludes ZX0,
queue work, copying, AY/IRQ, ULA, ROM and disk latency.

The real queue and full-AY-wait CPU cost is separately measured at
**289,401,696→289,460,171 T**, an increase of 58,475 T as scheduling changes.
The larger frame CPU saving must not be presented as the elapsed playback
saving. [The CPU report](compact_cursor_cpu.json),
[build report](compact_cursor_build.json) and
[archived playback summary](compact_cursor_summary.json) keep these scopes
separate. The [summarizer](summarize_compact_cursor.py) verifies their hashes
and recomputes the playback metrics from saved evidence.

## Complete Fuse observation

| Volume | FPS before → after | Late frames | AY underruns | Maximum late fields | Intervals outside 5..7 fields |
|---|---|---|---|---|---|
| 1 | 8.2823025 → 8.2848392 | 984 → 984 | 81 → 78 | 86 → 83 | 122 → 120 |
| 2 | 7.9802956 → 7.9861967 | 840 → 837 | 338 → 333 | 344 → 338 | 236 → 235 |
| 3 | 7.8841952 → 7.8899417 | 1249 → 1249 | 464 → 458 | 468 → 463 | 302 → 307 |

The summed first-to-last publication spans are
**1,854,669,649→1,853,606,028 T**, a reduction of **1,063,621 T**.
AY underruns fall **883→869**, while bad intervals rise **660→662**.
IRQ and disk starting phases are not aligned, so these are whole-player
observations, not an isolated measurement of the changed instructions.
The third volume's interval count worsens despite its lower mean duration.

All 25,326 AY records and 7501 runtime sectors are exact; sectors are read
once, retries are zero, and all 7498 direct ROM returns preserve IM2/I/vector.
No physical IRQ fields are missed. AY-record field gaps are 78 / 333 / 458,
with no duplicates. Actual maximum publication deviations are
5,885,379 / 23,966,904 / 32,830,408 T. Recovered late runs number 0 / 3 / 2;
the final runs 640..1623 / 478..1296 / 55..1299 remain late through EOF
(local zero-based frame indices). Every missed nominal deadline is retained
separately from the fallback result in the summary.

The exact deadline, fallback and continuous-AY requirements still fail.
Keep root release images unchanged. Retain the option for further measured
work: it reduces deterministic CPU cost without additional code, buffers or
sectors, but its measured whole-player benefit is modest and does not improve
every interval metric. Future comparisons should retain both this run and
the HL-only run to expose scheduling changes.

## Reproduction

Commands assume the same measured local inputs; their hashes are checked.
Raw volumes and conversion states in the referenced worktrees are local
inputs, not newly bundled source assets.

```powershell
python -m unittest test_compact_cursor -v
python toolkit/benchmark_compact_cursor.py --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz
python toolkit/build_integrated_bootstrap.py --directory ../cached-huffman-byte/.tmp/three --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/compact-cursor --report toolkit/compact_cursor_build.json --bank2-zx0 --audio-wait-prefetch --fast-return-irq --hl-mask-reader --compact-cursor
python toolkit/verify_integrated_bootstrap.py --directory .tmp/compact-cursor --baseline-directory ../cached-huffman-byte/.tmp/three --raw-directory ../volume-huffman/.tmp/probe --report toolkit/compact_cursor_build.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/compact-cursor --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/compact-cursor-fuse --trace-pipeline --trace-queue-calls --trace-fields
python toolkit/replay_queue_calls.py --directory .tmp/compact-cursor --trace-directory .tmp/compact-cursor-fuse --output .tmp/compact_cursor_queue_cpu.json
python toolkit/summarize_compact_cursor.py --fuse .tmp/compact-cursor-fuse --directory .tmp/compact-cursor --cpu .tmp/compact_cursor_queue_cpu.json
```

Set `PYTHONPATH` to include `toolkit` and the installed dependencies for the
unit-test command. The summarizer with no arguments checks the committed
archives and recomputes its report. No other source video or physical drive
was tested in this experiment.
