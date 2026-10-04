# Round 15: register-based Speex coefficient preparation

2026-10-04. Resume exact Speex throughput work under the user's clarified
goal: output samples consecutively; no uniform per-sample deadlines are
required. Baseline `pure-r9`, same complete mode-3 packets and independent
fixed-point upstream reference. No pacing, format, precision or quality change.

## Change and instruction accounting

Keep the 32-bit increment in DE/DE' and accumulator in HL/HL'. Write each
four-byte table entry backwards with two PUSH instructions. SP temporarily
points into the coefficient page; save its original value in two state bytes,
make no calls while it is redirected, and restore it before advancing to the
next page. IRQ remains disabled, as required by the existing player. Caller
IX/IY and the actual return stack are preserved. The high-nibble table starts
at -step, reaches -8*step, then negates to +8*step before descending through
7..0. The negation's low byte is known zero because that value is coef<<15.

The old per-entry path costs 100 T for four byte stores and 74 T for the
addition/reloads: 174 T. New entry storage is `EXX/PUSH HL/EXX/PUSH HL`,
30 T; descending 32-bit subtraction takes 42 T. Four final row subtractions
are omitted. Per page these bodies cost 11136 -> 4440 T; additional setup
reduces the net saving to **6153 T per changed coefficient page**.

An independently instruction-audited ten-page preparation call costs
**120963 -> 59433 T**, difference -61530 T; 17686 -> 7366 instructions.
All 640 resulting entries, memory guards and SP/IX/IY pass. Changed single
page calls cost **8646..9474 T**, previously 14799..15627; unchanged whole
sets remain 976 T. Initial implementation passed the bounded table/frame
checks; removing redundant low-zero-byte negation work then saved a further
12 T per changed page before the final complete-stream checks.

## Complete result and verification

Full control speech: **2235799352 T**, down **274989834 T (10.9523%)** from
2510789186. Mean **11963.8236 T/sample**, still **27.3459x** the average
437.5-T budget. Synthesis including preparation drops 1476842692 ->
1201852816 T; LPC remains 317769021 T. The complete delta reconciles with
44692 changed pages * 6153 T, minus 42 T additional state initialization.
First-frame instruction audit: **1861567 -> 1738549 T** (-123018).

All **1074400 PCM16/PCM8 samples** pass: complete speech, six signal fixtures,
full six-bank capacity and 512 random valid mode-3 packets. Also pass 40960
coefficient entries, 12800 products, ten individual cache changes, general
arithmetic/cosine primitives, excitation tables, five input controls and a
two-frame cached-silence instruction audit. Complete execution retains
poisoned initial state, guarded writes, unchanged input/static data and only
the four declared immediate-operand writes.

Code **6945 bytes** (+321), state **1041** (+2), stack reserve 256. Table
payload remains 16010 useful bytes in its 16384-byte arena; no extra table
RAM. Select this exact optimization as the basis for the next throughput
round. Sustained real time remains false even after dropping the historical
per-sample deadline requirement. ULA, disk and hardware remain unmeasured.

Reproduce in order: `build.py --skip-host --variant pure-r15`,
`check_round.py --variant pure-r15`,
`check_unpaced.py --variant pure-r15 --previous pure-r9`, then
`report_round.py --variant pure-r15 --previous pure-r9 --round 15`.
Use the existing saved speech/signal/random fixtures and baseline build.
[Report](report.json), [checks](checks.json), [unpaced checks](unpaced-checks.json),
[generator transform](../../followup_opt.py), [assembly](decoder.s).
