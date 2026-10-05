# Five-level TRD: visual prototype and full test playback

Maintenance, 2026-10-05: explicitly unsuccessful TRD payloads from this study were removed at the user's request. Reports, source snapshots and measurements remain historical evidence; [retirement identities and reasons](../docs/maintenance/2026-10-05-retired-trds.md) allow recovery. This does not change the original results.

Measured on 2026-09-30. Image: [ZX-video-five-level-test.trd](https://github.com/Witali/ZX-video/blob/78541a5ecb5bb2f8fba42e9d081a284569d00dc6/ZX-video-five-level-test.trd).
This is one independently bootable **test montage**, with three 64-frame
windows starting at source frames 629, 2857 and 3855. Their corresponding
existing AY states are concatenated. The two hard cuts are intentional.
This does not replace the release or demonstrate whole-movie capacity.

## Result

| Property | Measured value |
| --- | --- |
| Frames / intended duration | 192 / 23.04 s |
| Image file | 655360 bytes (640 KiB), Git LFS |
| File sectors occupied / free | 489 / 2055 (125184 / 526080 bytes) |
| Compressed video | 112364 bytes, 439 padded sectors |
| Native picture / active area | 256x192 / 256x144 |
| Logical picture / active area | 128x96 / 128x72 |
| Dither | Five coverage levels, original fixed 2x2 phase |
| Row dictionary | 172 entries; existing 512-byte lookup allocation |
| Frame target | Six interrupt fields, 25/3 fps at nominal 50 Hz |
| Observed mean frame rate | **6.7491 fps**, first-to-last publication |
| Observed intervals | 60.00 to 640.00 ms; mean 148.17 ms |
| Nominal deadlines missed | **174 / 192** |
| Maximum accumulated delay | **269 fields, 5.38 s** |
| AY verification | All 1152 ticks and register records exact; no field gaps, duplicates or underruns |
| EOF and current-disk progress | All frames delivered; progress reaches 100% |

Cadence uses the actual completed screen-selection OUT, not merely a software
counter. Milliseconds and fps above normalize the measured 70908 T per field
to 50 Hz; the real Spectrum 128 clock's field frequency is slightly different.
Only 55 of 191 intervals are six fields. There are 39 intervals outside the
fallback bounds. Late run 14..57 recovers at frame 58; run 62..191 never
recovers. **Both the exact-deadline and one-field fallback gates fail.**
Video falls behind the unchanged AY clock, so audiovisual synchronization
also fails even though every AY register record is correct. Audio waveform
fidelity against the original soundtrack was not re-evaluated here.

`complete: true` in the reports means the entire short disk was observed;
it does **not** mean its timing passes. All reports retain `release: false`.

## Picture checks

- Every one of the 192 host-generated compact states expands byte-for-byte
  to the independent five-level reference. The FAP3 round trip is exact.
- Real Fuse playback samples 80 screen offsets on each of the 192 frames:
  no pixel or attribute errors. Progress locations are checked separately.
- Separate cold Fuse runs stop immediately after publication of frames
  31, 64, 95, 128, 159 and 191. The six complete physical screens, including
  progress, match all **41472 bytes**. Both physical screen banks are covered.
  These capture runs are separate from the uninterrupted timing run.
- Visual inspection of [the contact sheet](five_level_test_preview.png)
  shows smoother shaded areas on the rabbit and trunk. Spectrum palette
  limitations and visible ordered texture remain, especially in foliage.
  There is no claim of photographic equivalence or 95% visual accuracy.

MSE compares the RGB average of each native 2x2 pattern to freshly scaled
source RGB, over the active image only. It describes tone error, not all
perceptual detail, flicker or motion artifacts.

| Source window | Four-code MSE | Five-level MSE | Reduction |
| --- | ---: | ---: | ---: |
| 629..692 | 792.354 | 712.993 | 10.016% |
| 2857..2920 | 659.666 | 651.776 | 1.196% |
| 3855..3918 | 762.456 | 705.314 | 7.494% |

No individual frame has a higher MSE than its four-code reference. Resolution,
palette endpoints and BRIGHT are preserved; FLASH remains disabled. Border
attributes are normalized to the existing black-border contract.

## Implementation and verification limits

[row_dictionary_video.py](row_dictionary_video.py) assigns a byte index to
each four-sample radix-5 row. One book covers all frames and the startup
checkpoint; index zero is a black row. It is installed in 9E00/9F00 at boot.
The existing alternating-screen renderer and FAP3 consumer use these bytes
without additional runtime lookup instructions. Renderer instruction cost
delta is **0 T**; the earlier dense/sparse audit measured 154684/27101 T
with either table. Those fixture counts are not full frame-delivery costs.

FAP3 still uses its existing motion/residual representation. A row index
does not retain the old two-bit spatial meaning, so this prototype is not
evidence that existing sub-byte motion predictors suit the new symbols.
The size and decoder-only gains from earlier bounded packet probes did not
guarantee the end-to-end result. Before promotion, profile packet handling,
reconstruction and disk production, then measure a format aware of whole
row indices; keep the fixed-phase five-level pixels as the quality reference.

The new Huffman code exposed a fixed-address assumption in Fast ZX0 startup.
The separate placement fix derives actual retired code bounds; identical
CPU fixtures take 347057 and 46904 T at either address, **0 T delta**.
Thirteen relevant decoder/dictionary tests pass. Cold boot from dirty RAM,
installed sections, first full native screen, second compact frame and
immutable AY bank are checked with mocked ROM before the real-Fuse result.

The real run checks all 439 runtime sectors. Observed disk-read windows sum
to 13815629 T; seek/maintenance windows sum to 317514 T. These include ROM,
emulated physical waits and interrupts. They are not pure instruction counts
and should not be subtracted to claim a deterministic decoder CPU profile.
Priming happens before nominal playback deadlines. This test uses the
existing buffer allocation and direct-compressed startup tables.

## Evidence and reproduction

- [Build and per-frame quality](five_level_test_build.json)
- [Cadence, quality and archive hashes](five_level_test_summary.json)
- [Full-screen captures](five_level_test_captures.json)
- [Replay evidence](five_level_test_evidence): metadata, raw FAP3, compact and
  five-level states, uninterrupted Fuse trace, screen dumps, debugger scripts
  and test log. Gzip archives contain the original named file.

All scripts below are checked into the repository. Use Python with NumPy and
Pillow, the existing FFmpeg/ZX0 executables and Fuse with the verified TR-DOS
ROM. Commands run from the repository root with `toolkit` on `PYTHONPATH`.

```powershell
$py = 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:PYTHONPATH = 'toolkit;C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/python_packages'
$env:OPENBLAS_NUM_THREADS = '1'
& $py toolkit/build_five_level_test_trd.py `
  --source C:/Work/HLV-codec/out/sources/big_buck_bunny_1080p_h264/big_buck_bunny_1080p_h264.mov `
  --ffmpeg .worktree/audio-fidelity/.tmp/bin/ffmpeg.exe `
  --zx0 .worktree/audio-fidelity/.tmp/bin/zx0.exe `
  --audio-raw .worktree/volume-huffman/.tmp/probe/volume-1.raw `
  --baseline-build toolkit/fast_zx0_player_build.json `
  --work .tmp/five-level-trd --trd ZX-video-five-level-test.trd `
  --report toolkit/five_level_test_build.json
& $py toolkit/measure_fap3_fuse.py `
  --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --trd ZX-video-five-level-test.trd `
  --metadata .tmp/five-level-trd/metadata.json --raw .tmp/five-level-trd/video.raw `
  --states .tmp/five-level-trd/prepared.npz --output .tmp/five-level-trd/timing.json
& $py toolkit/capture_five_level_fuse.py `
  --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --trd ZX-video-five-level-test.trd `
  --metadata .tmp/five-level-trd/metadata.json --prepared .tmp/five-level-trd/prepared.npz `
  --build-report toolkit/five_level_test_build.json --work .tmp/five-level-trd/captures `
  --output toolkit/five_level_test_captures.json --preview toolkit/five_level_test_preview.png
& $py -m unittest toolkit/test_bank2_zx0.py toolkit/test_faster_zx0.py `
  toolkit/test_dynamic_zx0_placement.py toolkit/test_row_dictionary_video.py -v `
  > .tmp/five-level-trd/tests.txt 2>&1
& $py toolkit/summarize_five_level_test.py --work .tmp/five-level-trd `
  --build toolkit/five_level_test_build.json --captures toolkit/five_level_test_captures.json `
  --evidence toolkit/five_level_test_evidence --output toolkit/five_level_test_summary.json
```

Do not run multiple Fuse instances concurrently: this Windows build may
write its debugger output to a shared `stdout.txt`. For timing replay without
requantization, extract `metadata.json.gz` and `video.raw.gz` from the saved
evidence and pass those plus `states.npz` to `measure_fap3_fuse.py`.
