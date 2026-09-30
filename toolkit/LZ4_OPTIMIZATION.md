# LZ4 optimization on the Z80

2026-09-30, baseline `e681055`. Reuse the 21 archived LZ4-HC12 blocks of
the exact 192-frame five-level fixture (64 frames at 629/2857/3855).
Decoded data, block boundaries, resolution, brightness patterns and AY
records are unchanged. This is a component analysis, not a playback release.

## Finding and decision

**Short-run specialization works without changing one compressed byte.**
The original generic-copy implementation was slower than LZSA2. The revised
LZ4 decoder saves 4190540 T (21.11%) against that baseline, and 3754992 T
(19.34%) against current LZSA2. Its coroutine code/state grows by 13 bytes.

Keep this verified experimental decoder. Do not replace the current player
solely on these figures: LZ4 needs 111 more video sectors. Actual disk/ROM
latency, queues, ULA contention, AY and publication deadlines were not
measured for this candidate. The current optional TRD is unchanged and its
previously measured 7.683025 fps still fails both deadline gates. No new
candidate fps or full-movie capacity result is claimed.

| Same decoded 323940 bytes | Current LZSA2 | Initial LZ4 | Optimized LZ4 |
| --- | ---: | ---: | ---: |
| Stream bytes, including block headers | 154956 | 183448 | 183448 |
| Video sectors | 606 | 717 | 717 |
| Decoder T | 19412006 | 19847554 | 15657014 |
| Producer T, excluding ROM/disk | 1058423 | 1214488 | 1214488 |
| Component total T | 20470429 | 21062042 | 16871502 |
| LZ4 code and state bytes | — | 267 | 280 |
| Largest measured LZ4 video slice T | — | 20126 | 15338 |

Video storage grows 18.39% versus LZSA2. The component saving of 3598927 T
would pay for an average **32422.77 additional T per extra sector** in a
simple serial additive model. This is only a break-even estimate, not a
disk-latency measurement: sector ordering, track transitions, prefetch and
the changed producer/consumer schedule can change the result substantially.

## What consumed the time

The initial LZ4 profile contains 32142 matches. Of these, **31695 (98.61%)**
have lengths 4..18, requiring no length extension. Of 18588 nonempty literal
runs, **17563 (94.49%)** have lengths 1..14. There are 13575 zero-literal runs.

The generic copy routine repeatedly checks a length already known to fit
in `C`, and introduces `CALL`/`RET` overhead. It also exchanges the input and
match-source pointers using `EX (SP),HL` twice for every match, although only
extended matches need the input pointer to read more length bytes.

The fast implementation in [resumable_lz4.py](resumable_lz4.py):

- Executes short literal copies with an inline `LDIR`.
- Keeps the computed match source in `HL` for short matches and executes
  another inline `LDIR`. The saved input pointer is restored with `POP HL`.
- Uses the original general handler for extended runs. Long copies poll
  the output quota every 256 bytes; short runs poll at sequence boundaries.
- Preserves the existing caller/decoder stack and AF/AF' coroutine ABI.
  It changes neither LZ4 tokens nor the 16-bit positive offset format.

## Exact instruction costs

Use the [Zilog instruction timing table](https://www.zilog.com/docs/z80/um0080.pdf),
without wait states, IRQ or ULA contention. For nonzero length `n`,
`LDIR` costs `21*n - 5` T. Full instruction listings and observed costs
are archived; the independent full-flags CPU agrees on every video slice.

| Compared path | Initial T | Optimized T | Difference |
| --- | ---: | ---: | ---: |
| Literal length 1..14, after `CP 15` through copy | `21*n + 65` | `21*n + 7` | -58 |
| Match length 4..18, after source calculation, before `POP HL` | `21*n + 132` | `21*n + 31` | -101 |
| Extended literal, additional dispatch around identical handlers | 17 | 36 | +19 |
| Extended match, dispatch/pointer exchanges around identical handlers | 55 | 77 | +22 |

For short literals, the old path adds 70 T around `LDIR`: conditional
`CALL` not taken 10, ordinary `CALL` 17, B/C/zero checks 33, and `RET` 10.
The new path adds only the taken `JR NZ` (12 T). Short matches additionally
remove two 19-T `EX (SP),HL` operations. Their unchanged count setup is 29 T;
old surrounding work is 108 T, new branch is 7 T.

The aggregate identity is exact:

```text
17563*58 + 31695*101 - 1025*19 - 447*22 = 4190540 T
```

No run-length or suspension-boundary changes explain the saving. Remaining
`LDIR` work is 6549090 T in both versions, now 41.83% of decoder time.

## Further opportunities, in priority order

1. **Choose the codec within a bounded window.** Use LZ4 only where its
   measured decoder saving can pay for extra sectors and the volume budget.
   Keep LZSA2 where bytes matter more. Compare complete delivery deadlines,
   including queue pressure and block carry costs; bytes or decoder T alone
   are insufficient. The two tested cores use the same code address, so a
   mixed runtime needs an explicit placement/dispatch budget first. It is
   not implemented by this experiment.
2. **Optimize the host parse for this Z80 decoder.** Charge each candidate
   match its actual short/extended path, copied bytes and resulting sectors.
   Search for Pareto alternatives in saved difficult-frame windows rather
   than re-encoding whole disk sets. Longer matches can reduce token overhead;
   accepting extra literals can instead increase both disk and copy work.
   Keep standard LZ4 syntax and verify native timing after selection.
   Upstream provides experimental `LZ4_favorDecompressionSpeed` for optimal
   HC levels; its speed preferences must still be measured on Z80, not
   assumed to fit our instruction costs. See the
   [official HC API](https://github.com/lz4/lz4/blob/dev/lib/lz4hc.h).
3. **Test a small unrolled-copy suffix only if its dispatch pays off.**
   Replacing every repeated `LDIR` iteration with `LDI` has an absolute
   upper bound of **1366050 T** on this fixture, before all new tail/loop
   dispatch costs. `LDI` remains overlap-safe. The existing core ends at
   `0x8e72`, leaving 133 bytes to its `0x8ef7` allocation limit. A large jump
   table would compete with other player code. No unroll gain was measured.
4. **Dictionary continuity is a separate memory experiment.** LZ4 can
   reference earlier history, but the current three bank-local slots cannot
   access an arbitrary 64 KiB history at once. Charge bank switching,
   dictionary retention and lost input-buffer capacity. Reset or store all
   required history on each independently bootable disk. Do not infer a
   larger useful contiguous window merely from total 128 KiB RAM.

### Ideas rejected by the current offset statistics

The [standard LZ4 block format](https://github.com/lz4/lz4/blob/dev/doc/lz4_Block_format.md)
uses two bytes for each offset. A proposed nonstandard variant could store
offsets 1..255 in one byte, and larger offsets as `0 + uint16`. But only
7025/32142 offsets fit one byte; 25117 need the escape. With the same token
parse, offset fields alone would **grow by 18092 bytes**, plus any signalling.
Reject that simple change before writing a decoder.

Only 570 offsets repeat the immediately preceding offset within a block;
only 572 are distance one. A repeat-offset opcode could save at most 570
offset bytes if each repeat became one byte, before tag and state costs.
Neither count supports making this the next priority. These are host
statistics and byte estimates, not tested alternative wire formats.

## Verification and limits

- All 21 archived payloads reproduce the same exact bytes in the upstream
  LZ4 decoder, independent host parser, guarded banked CPU and independent
  full-flags Z80 core. Both ASM variants pass.
- Per-write input cursors, overlap protection, bank guards, sector ordering
  and exact EOF pass. No bank-size or disk-buffer change.
- 46 cases per variant cover literal/match thresholds, 255/256-byte copying,
  long extension chains, offset 1 overlap, large offsets, final literals,
  zero-literal sequences, maximum native block size and a short-sector retry.
  Nine malformed host inputs are rejected. Native code trusts the host
  validator; it is not a decoder for arbitrary untrusted byte streams.
- Independent video runs inject 183/143 IM1 interrupts for baseline/fast.
  One initial synthetic event hit an unavailable CPU boundary; the harness
  now records skipped events when the CPU cannot accept an interrupt.
  This checks state preservation, not actual 50-Hz AY scheduling.
- Maximum edge slice is 11763/11794 T; the fast variant is slightly slower
  on long-run dispatch as predicted. Minimum observed private SP on edge
  tests is `0x7bce` (18 bytes below `0x7be0`, excluding IRQ pushes).
  Slice maxima are measurements on these inputs, not universal bounds.
- Initial assembler operand/label mistakes were fixed before successful
  video results. The independent edge harness initially placed a maximum
  input over its own code; input moved to `0x1000` in its flat memory model,
  and an overlap assertion was added. All affected checks then passed.
- No new disk, boot, full frame pipeline, physical disk, actual publication
  or full-movie test. Current TRD hash is checked unchanged by the summary.

## Reproduce

Use the existing project Python environment and its pinned `z80` and `lz4`
packages (author LZ4 binding version 4.4.5). Sources are in this repository;
no compiler download or new executable is needed. Extract
`row_lz4_evidence/video.raw.gz` and `metadata.json.gz` to a work directory,
for example `.tmp/lz4-reproduce`. The compressed stream is already archived
at `modern_codec_evidence/lz4_hc12.stream.gz`.

```powershell
$env:PYTHONPATH='local_tools/python_packages;.tmp/lzma-z80-packages;.tmp/codec-probe-packages;toolkit'
python toolkit/benchmark_row_lz4.py --baseline --raw .tmp/lz4-reproduce/video.raw --metadata .tmp/lz4-reproduce/metadata.json --output .tmp/lz4-reproduce/baseline
python toolkit/benchmark_row_lz4.py --raw .tmp/lz4-reproduce/video.raw --metadata .tmp/lz4-reproduce/metadata.json --output .tmp/lz4-reproduce/fast
python toolkit/verify_row_lz4.py --raw .tmp/lz4-reproduce/video.raw --baseline .tmp/lz4-reproduce/baseline/cpu.json --candidate .tmp/lz4-reproduce/fast/cpu.json --output .tmp/lz4-reproduce/verification.json
python toolkit/summarize_row_lz4.py --baseline .tmp/lz4-reproduce/baseline/cpu.json --candidate .tmp/lz4-reproduce/fast/cpu.json --verification .tmp/lz4-reproduce/verification.json --metadata .tmp/lz4-reproduce/metadata.json --raw .tmp/lz4-reproduce/video.raw --evidence toolkit/row_lz4_evidence --output toolkit/row_lz4_profile.json
```

The [summary](row_lz4_profile.json) records per-block comparison, run counts,
instruction aggregates, source hashes and [archived evidence](row_lz4_evidence).
