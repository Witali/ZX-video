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

Next intermediate target after round32: **below 8500 T/sample** on the same
complete 186880-sample speech, exact PCM16/PCM8 and unchanged 16-KiB table
arena. Current 8722.182 T/sample needs another 41521442 T saving to reach
8500 (about 2.55%). This is an unachieved target, not a forecast; round33
alone is not expected to close the gap. Real time still needs 437.5 T/sample.

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
- [x] **26. Keep the pitch sum in alternate registers.** Replace repeated
  RAM accumulation of the three signed products with alternate HL/C, using
  the real stack for the product-word transfer. Include initialization and
  final writeback: predicted 16205909 fewer T. Check helper preservation of
  alternate registers, skipped taps, modulo24 carries and complete streams.
  [Round26](rounds/26/REPORT.md) confirms exactly that saving: 9817.773
  T/sample. All 1074400 PCM samples, 200187 sums, 1037 writebacks and
  589824 helper-preservation cases pass. Tables/state unchanged, code -23.
- [x] **27. Share history addressing for pitch >=41.** For all 40 samples
  in these subframes, the three history indices remain negative and adjacent.
  Prototype one advancing IX cursor, preserving the general smaller-pitch
  path. Include dispatch/setup in costs and verify threshold 40/41, all
  pitch values, every frame, register contracts and all complete streams.
  The current input has 3519 eligible subframes out of 4672; speedup is not
  yet measured. Do not add output pacing or change Speex packets.
  [Round27](rounds/27/REPORT.md) dispatches once per subframe and duplicates
  the sample loop: -43983608 T on speech, 9582.415 T/sample (-2.397%).
  All 81920 history cases per variant and 1094880 complete-stream samples
  pass. General subframes cost one extra T/sample; tables/state unchanged.
- [x] **28. Specialize the finite pitch-gain multipliers.** Generate exact
  signed24 constant multiplication routines; compare shift/add/subtract
  chains including indirect-call/setup costs. Consider replacing the existing
  192-byte gain triples with same-size routine-pointer triples. Keep the
  generic energy multiplier, table budget and all input/PCM semantics.
  Verify all constant/word domains, register contracts, memory and full streams
  before selection.
  [Round28](rounds/28/REPORT.md) selects bounded add/subtract chains over
  binary Horner: 9063.774 T/sample, 96923613 fewer T (-5.412%). All 4259840
  products per candidate and 1094880 selected complete-stream samples pass.
  Code +1616, tables/state unchanged; average real-time deficit still 20.717x.
- [x] **29. Return pitch products directly as A:HL.** The accumulator uses
  only signed24, so avoid the constant helper's signed32 conversion and
  subsequent high-byte reload. Keep the ordinary 24-T saving separate from
  zero's proposed 10 T and identity's 4 T. On observed counts the estimate
  is 12883810 T, or 8994.833 T/sample: aim for **below 9000 T/sample** on
  the unchanged full speech. Verify every constant/word, modulo24 sums,
  skipped taps, registers, memory and full streams. The initial estimate
  alone did not pass the milestone or real-time goal.
  [Round29](rounds/29/REPORT.md) confirms 12976212 fewer T, **8994.338
  T/sample**, passing the intermediate target. Zero/identity save 12/8 T,
  better than the original estimate. All 4259840 products, 200187 additions
  and 163840 history cases per variant plus 1094880 full-stream samples pass.
  Code -325, table/state unchanged; average real-time deficit still 20.558x.
- [x] **30. Shorten the synthesis feedback shift.** Replace five signed24
  right shifts after byte discard with three left shifts in sign-extended
  A:E:HL, then select the upper three bytes. Count 93 versus 120 T, saving
  27 T/sample: predicted 8967.338 T/sample on the unchanged full speech.
  Verify signed extrema, every rounding boundary, register/flag assumptions,
  memory and complete streams. Preserve exact Speex and the table budget;
  require an executed result before selection.
  [Round30](rounds/30/REPORT.md) confirms exactly -27 T/sample,
  8967.338 T/sample. Every OUT delta agrees. Both versions pass 393216 shifts,
  1572864 rounding boundaries and 128 filter calls; selected 1094880 complete
  samples pass. Code -12, tables/state unchanged, average deficit 20.497x.
- [x] **31. Compare a faster general signed16x16 product.** The unchanged
  LPC kernel's prior full profile reports 167043802 T / 186880 calls, about
  9.97% of current total CPU. Observe current operands and prototype two
  unsigned8x16 combined-register products with exact combination/sign handling.
  Include zero/byte paths, setup, calls, carries and register preservation.
  Compare instruction costs and complete speech before selecting; retain all
  PCM, memory and complete-stream gates before selection.
  [Round31](rounds/31/REPORT.md) selects two unsigned partials: 40455507 T
  saved (-2.414%), 8750.860 T/sample. All 16777216 unsigned and 2228224 signed
  products, instruction formulas/guards and 1094880 full-stream samples pass.
  All observed operands match; isolated costs reconcile with the total delta.
  Code -39, table/state unchanged. Average real-time deficit still 20.002x.
- [x] **32. Share coefficient preparation inside Q14 multiplication.** The
  two signed16 products in MULT16_32_Q14 use the same coefficient. Reuse the
  archived operand trace to quantify repeated normalization and sign work,
  then prototype a fused path only with a plausible total saving. Preserve
  high-argument signed16 truncation and negative fractional rounding exactly.
  Include argument extraction, scratch/stack, calls and final combination;
  compare complete CPU with unchanged general multiplier and table contracts.
  [Round32](rounds/32/REPORT.md) selects shared normalization: -5359215 T,
  8722.182 T/sample (-0.328%). All 1343488 Q14 cases, 1179648 unsigned
  products and 1094880 complete samples pass. Every checked full fixture
  improves, but 40193 individual speech calls regress. Code +179 bytes;
  table/state unchanged. Average real-time deficit remains 19.936x.
- [ ] **33. Avoid double Q14 sign reversal.** Negative coefficient/negative
  high-part inputs occur 39946 times in the saved trace. The current path
  negates the high product and later negates the combined result. Compare
  a positive high product minus the rounded fractional contribution, with
  all sign/zero/remainder boundaries and setup costs included. Preserve
  truncation, exact PCM, memory and complete-stream gates. This candidate
  is unimplemented; do not claim its saving in advance.

Each completed experiment needs a report, root CHANGELOG entry and focused
commit. A failed experiment is evidence, not permission to redefine success.
Nominal CPU measurements exclude ULA, disk and physical hardware. The user
has removed uniform sample deadlines as a completion gate, not correctness,
complete-stream timing, input format or the RAM accounting requirement.
