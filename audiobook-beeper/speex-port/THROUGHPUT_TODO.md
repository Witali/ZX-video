# Active unpaced Speex throughput work

2026-10-04. The user clarified that samples may be emitted consecutively;
uniform per-sample spacing is not required. The goal is to approach real-time
decoding/output on a nominal 3.5-MHz Z80. Keep the existing worktree and
assembly implementation, complete memory-to-PCM8-port path and 16-KiB table
arena. The previous PVQ timing milestone is closed and does not establish
real-time Speex. Do not spend this milestone on PVQ pacing or ULA scheduling.

Baseline: exact mode-3 Speex `pure-r9`, 2510789186 T for 186880 samples,
13435.302 T/sample, 30.709x the 437.5-T/sample average budget. Samples are
already emitted without pacing. Retain the complete upstream PCM16/PCM8
comparison and report throughput separately from instantaneous OUT gaps.

- [x] **15. Register-based coefficient table construction.** Replace four
  byte stores and repeated step loads with 32-bit register accumulation and
  reverse PUSH writes. Save/restore SP around each changed page; document
  the disabled-interrupt requirement. Check every table entry, signed
  midpoint, page cache, real stack restoration and all complete fixtures.
  Record total CPU, table construction and instruction timing deltas.
  Selected: [round15](rounds/15/REPORT.md), 2235799352 T / 11963.824 T/sample,
  10.952% fewer T; all 1074400 samples remain exact. Still 27.346x over budget.
- [x] **16. Skip guaranteed-zero product bytes.** In partial products shifted
  by eight/twelve bits the low byte is zero. Test eliminating those reads
  and additions while preserving carry into the remaining three bytes.
  Compare the same exact waveform, tables and total CPU against round15.
  Selected: [round16](rounds/16/REPORT.md), exactly -380 T/sample, now
  11583.824 T/sample. All 1074400 samples pass; fresh default image matches.
- [x] **Reassess the measured bottleneck.** Keep the full throughput objective
  active if exact Speex remains over budget. Rank the next changes using
  complete decoding measurements, not faster different-format playback.
  Round16: synthesis/preparation 6051.147 T/sample, LPC 1700.391, remaining
  decode 3832.286. Average deficit is still 26.477x; goal remains active.
- [x] **17. Split the remaining hot-path profile.** Measure coefficient
  preparation, sample products, innovation construction and excitation work
  separately on the complete unchanged input; reconcile their inclusive and
  exclusive times before selecting the next exact optimization. Preserve
  the same average-throughput goal without adding output pacing.
  [Round17](rounds/17/REPORT.md): full trace and PCM unchanged, nested times
  reconcile. Coefficient products cost 23.136%, signed 8x16 products 13.865%.
- [x] **18. Combined-register signed 8x16 multiplication.** Replace separate
  shifts with an A:HL accumulator, compare fixed eight steps with leading-bit
  skipping, and retain the fastest exact complete-stream implementation.
  Preserve signs, -32768 handling, all tables and the PCM8 port contract.
  [Round18](rounds/18/REPORT.md) selects `pure-r18-signed`: 2042203676 T,
  10927.888 T/sample (-5.663%), all 1074400 PCM samples and 589824 additional
  product/cycle cases pass. Average deficit still 24.978x; goal remains active.
- [ ] **19. Replace seven-bit excitation shifts.** Inspect the signed24
  rounded sum in L:D:E before `_zx_clip`. Instead of seven arithmetic
  right shifts, save the sign byte, shift the three bytes left once, take
  the upper two bytes as DE and restore sign extension in HL. Proposed
  cost 52 versus 184 T including sign extension, saving 132 T/sample;
  this is an instruction estimate, not yet an executed result. Verify
  signed24 extremes, rounding boundaries and all complete reference streams.

Each completed experiment needs a report, root CHANGELOG entry and focused
commit. A failed experiment is evidence, not permission to redefine success.
Nominal CPU measurements exclude ULA, disk and physical hardware. The user
has removed uniform sample deadlines as a completion gate, not correctness,
complete-stream timing, input format or the RAM accounting requirement.
