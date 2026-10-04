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
- [x] **19. Replace seven-bit excitation shifts.** Inspect the signed24
  rounded sum in L:D:E before `_zx_clip`. Instead of seven arithmetic
  right shifts, save the sign byte, shift the three bytes left once, take
  the upper two bytes as DE and restore sign extension in HL. Proposed
  cost 52 versus 184 T including sign extension, saving 132 T/sample;
  this is an instruction estimate, not yet an executed result. Verify
  signed24 extremes, rounding boundaries and all complete reference streams.
  [Round19](rounds/19/REPORT.md) confirms -132 T/sample: 10795.888 T/sample,
  all 1074400 PCM samples and 396800 isolated signed24 cases pass.
- [x] **20. Register-held innovation table construction.** Keep the signed24
  value, integer increment, fractional remainder and destination in ordinary
  and alternate registers. Scale the 12-bit fraction/remainder by sixteen
  so ADD's carry supplies the quotient increment. Preserve every table byte,
  table caching and all complete-stream output; include setup in timing.
  [Round20](rounds/20/REPORT.md): -28189 T per table, -44482242 T on the
  complete speech, 10557.862 T/sample. All 1074400 PCM samples and every
  innovation entry pass, including complete instruction/guard checks.
- [x] **21. Measure profitable zero shortcuts.** Count actual zero feedback,
  zero pitch gains and zero history words on the complete current input.
  Estimate both skipped work and the extra branch cost on nonzero data;
  prototype only paths with a measured net benefit. Do not sacrifice the
  ordinary nonzero path to optimize synthetic silence alone.
  [Round21](rounds/21/REPORT.md) rejects zero-word and zero-gain guards:
  forecast slowdowns 11.95M T and at least 8.96M T. Observe 3340 zero
  feedback samples; select only the state-copy path for a prototype.
- [x] **22. Zero-feedback state copy and dead-store removal.** Reuse A=H
  after negation for a 14-T zero test. Remove the unread `asm_n` store/state,
  copy the nine following history words and zero the final word when y=0.
  Verify arbitrary nonzero history with zero feedback, every exact stream,
  and both ordinary and zero path T-states. Predicted full saving 11359020 T.
  [Round22](rounds/22/REPORT.md) confirms exactly that saving: 10497.080
  T/sample, achieving the intermediate below-10500 target. All 1074400
  samples and 4650 arbitrary-history checks per variant pass.
- [x] **23. Inline coefficient products with register-held offsets.**
  Count all register saves, nibble setup, products and memory updates before
  implementing. Investigate replacing the per-tap CALL/RET and writable
  immediates with inline products and offsets in spare registers. Preserve
  the input cursor and IX/IY contract; do not use DD-prefixed LD L,IXH as
  though it addressed ordinary L. Verify exact products and full streams.
  Next proposed milestone: below 10000 T/sample on the same full speech,
  with exact PCM and the same 16-KiB table arena. Not yet achieved; this
  candidate alone has not been shown to reach it.
  [Round23](rounds/23/REPORT.md) compares both complete candidates and selects
  inline products with first-part reads via POP. Measured 9971.931 T/sample
  (-5.003%), meeting the below-10000 milestone. All 1074400 samples,
  7719 arbitrary histories and 128 filter calls per variant pass.
- [x] **24. Cheaper coefficient-table recurrence.** Inspect the repeated
  42-T 32-bit subtraction in reverse table construction. Estimate replacing
  it with a 34-T addition of a negated step, accounting for setup and the
  signed high-nibble midpoint. Preserve every table byte, page-cache
  behavior and SP, then compare complete throughput. The 10000-T milestone
  does not complete the average real-time objective.
  [Round24](rounds/24/REPORT.md) saves 282 T/changed page, 12603144 T on
  speech, now 9904.491 T/sample. All 65536 coefficients, 262144 negations
  and 1074400 complete-stream samples pass after correcting a borrow bug.
- [x] **25. Refresh the profile after inlining.** Measure the complete
  unchanged round24 stream. Reconcile nested function times and separately
  bracket the inline feedback block. Count actual changed coefficient pages
  from observed LPC values; account for bypassed zero feedback and unused
  helper calls. Preserve all PCM and every OUT timestamp. Select the next
  structural change from the current measured costs.
  [Round25](rounds/25/REPORT.md): unchanged PCM/OUT timing, full costs
  reconcile. Inline feedback uses 35.880%, decoder body 16.470%, preparation
  13.728%. Independently observe 44692 changed pages and no unused helper
  calls. Select register-held pitch accumulation as the next candidate.
- [ ] **26. Keep the pitch sum in alternate registers.** Replace repeated
  RAM accumulation of the three signed products with alternate HL/C, using
  the real stack for the product-word transfer. Include initialization and
  final writeback: predicted 16205909 fewer T. Check helper preservation of
  alternate registers, skipped taps, modulo24 carries and complete streams.

Each completed experiment needs a report, root CHANGELOG entry and focused
commit. A failed experiment is evidence, not permission to redefine success.
Nominal CPU measurements exclude ULA, disk and physical hardware. The user
has removed uniform sample deadlines as a completion gate, not correctness,
complete-stream timing, input format or the RAM accounting requirement.
