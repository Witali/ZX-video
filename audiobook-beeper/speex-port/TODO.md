# Speex optimization worklist

Authorized on 2026-10-04. Continue in `codex/speex-port`. Preserve the
`bbb7ebd` exact decoder and its evidence as the baseline. Complete each
item with a focused commit and a report under `rounds/` before continuing.

- [x] **1. Excitation arithmetic.** Remove the common factor 128; use signed
  8x16 products and bounded 24-bit arithmetic. Preserve PCM16/PCM8 exactly.
  Completed: [round 01](rounds/01/REPORT.md), 4128347261 T, delta -407824784 T.
- [x] **2. Innovation tables.** Build and cache the two exact energy tables
  with additions; include construction time and RAM in the measurement.
  Completed: [round 02](rounds/02/REPORT.md), 3936652302 T, delta -191694959 T.
- [x] **3. Synthesis multiplication.** Compare a register-based multiplier
  with per-coefficient nibble tables, including preparation costs. Select
  the faster complete decoder within the 16-KiB table allocation.
  Completed: [round 03](rounds/03/REPORT.md), 3089519959 T, delta -847132343 T.
- [x] **4. LPC and interpolation.** Exploit polynomial symmetry and known
  constants, reduce temporary storage, and use exact 16-bit interpolation.
  Completed: [round 04](rounds/04/REPORT.md), 2759257254 T, delta -330262705 T.
- [x] **5. Final verification.** Compare the entire speech stream and
  additional fixtures with the independent reference; verify arithmetic,
  RAM boundaries, actual OUT timing and instruction-table cycle counts.
  Completed: [round 05](rounds/05/REPORT.md), 1074400 PCM samples plus arithmetic
  and instruction checks; no mismatches.
- [x] **6. Real-time decision.** Reconcile the complete profile against
  437.5 T/sample and 70000 T/frame. Record an explicit pass/fail and assess
  the next approximate-synthesis experiment if the exact decoder still fails.
  Completed: [round 06](rounds/06/REPORT.md). Select `pure-r4`: 1.644x faster,
  identical audio, but 33.75x over the real-time CPU budget. Real-time FAIL.

Each report must identify its input and binary, changes, full-stream T-states
and delta, code/state/table bytes, checks and limitations, rejected variants,
and the decision. Do not count a proposed optimization as a measured result.
Do not substitute offline PCM expansion for decoding on the Z80. Approximate
speech synthesis is a separate result and cannot pass an exact-decoder check.

Baseline: 186880 samples, 4536172045 T, 24273.181 T/sample, 12658 table bytes,
10122 code bytes and 1885 state bytes. ULA/disk/hardware time is excluded.

All six items are complete. This closes the requested optimization worklist;
it does not claim the original real-time playback objective was achieved.
The default build now selects `pure-r4`; every earlier variant remains
reproducible. Approximate synthesis is documented as a separate next
experiment, not silently substituted for exact Speex decoding.
