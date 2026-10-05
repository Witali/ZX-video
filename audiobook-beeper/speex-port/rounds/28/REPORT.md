# Round 28: exact constant pitch-gain products

2026-10-04. Continue from round27 on the unchanged 186880-sample speech
control. Mode-3 pitch gains use only 65 distinct signed constants (-50..97).
Replace the 192-byte gain book with the same 32x3 word layout of immutable
routine pointers. Existing six-byte gain_current scratch holds those pointers.
Generate constant routines in code; retain generic _mul_s8 for energy math.
Packets, pitch selection, table reservation and PCM16/PCM8 stay unchanged.

## Implemented arithmetic and exact timing

A:HL accumulates modulo24, DE retains the original signed16 word, and B is
its sign extension when needed. Doubling costs 15 T (ADD HL,HL / RLA), adding
the original word costs 15 T (ADD HL,DE / ADC A,B), subtraction costs 23 T
(OR A,A / SBC HL,DE / SBC A,B). Positive initialization costs 20 T, or 24 T
with B; negative initialization costs 49 T and includes the -32768 case.
Final transfer, sign extension and RET cost 30 T. All final products fit
signed24, so wrapping intermediate arithmetic preserves the exact result.
Zero and identity have dedicated 30-T routines. IX/IY, all alternate
registers and the real stack are preserved; ordinary AF/BC are clobbered.

Old caller: LD A,(gain) 13 + CALL 17 T. New caller: LD HL,(target) 16 + CALL
17 + JP (HL) 4 T: **+7 T per product** outside the routine. Include this cost
when comparing the constants with round27's variable-time signed multiplier.
The selected routines cost **30..200 T including RET**, before that caller.

Compare two exact candidates. Binary Horner uses a positive or negative
seed; the selected bounded search permits double, add and subtract steps,
with intermediate coefficients -256..256 and initialization charged once.
It minimizes T then bytes within this recurrence family, not all possible
Z80 implementations. Seventeen constants improve over binary Horner; no
constant becomes slower. The resulting code is also 52 bytes smaller.

| Candidate | Complete speech T | T/sample | Added code |
| --- | ---: | ---: | ---: |
| Round27 | 1790761749 | 9582.4152 | 0 |
| Binary constant chains | 1696343225 | 9077.1791 | 1668 |
| Selected add/subtract chains | 1693838136 | 9063.7743 | 1616 |

Observe all **559217 pitch products** and their actual signed history inputs;
267627 have negative history. Sum old cost minus new cost minus 7 for every
call: **96923613 T saved**, exactly matching the executed full-stream delta,
**5.4124% fewer T**. Binary saves 94418524 T; chains save another 2505089 T.
The remaining 3156 generic calls are energy operations. First complete frame
falls 1188864 -> 1140964 T (-47900), including startup and all output.

## Verification and corrected development attempts

For each candidate, execute **65 * 65536 = 4259840 products** and compare
the full signed32 result with independent integer multiplication. Every cost
matches its instruction-derived plan; SP, IX/IY and all alternate registers
are preserved. Guard all writes except the declared real stack. Check all
96 pointers and emitted routine sizes. Nine signed/carry boundary words per
routine are independently instruction-stepped through JP (HL) and RET;
14229 instructions are audited for the selected chains. Both candidates
also pass the complete speech and round27's 20480-sample upstream all-pitch
fixture, plus an independent first-speech-frame instruction audit.

Selected pure-r28 passes the **1074400-sample standard suite** (speech,
signals, all six input banks and random mode-3 packets), plus that all-pitch
fixture: **1094880 exact complete-stream samples**. Every fixture improves
in CPU time. All-pitch total 197792080 -> 187146244 T (-10645836). Arithmetic,
innovation/coefficient tables and cache, controls, guarded RAM/code writes,
full frame/cached silence audits and fresh default image identity pass.

Initial build failed because the new Python generator was saved at the
worktree root; moving it into the decoder package fixed the import. The first
checker completed binary arithmetic/speech but then used an obsolete profile
key and failed before saving its final result. Corrected the harness to the
existing nested profile schema and reran both candidates to completion.
Neither attempt is counted as final verification; no product/PCM defect was
observed. Binary is retained as a measured comparison, not the selected image;
it did not receive the selected candidate's full standard fixture suite.

## Decision, memory and next target

Select **pure-r28**. Code **9235 bytes** at 8000..A412 (+1616), state 1041
bytes at B000..B410, reserved stack 256 bytes at BF00..BFFF. Tables remain
16010 useful bytes in a 16384-byte arena (12658 static, 3352 dynamic useful;
3584 dynamic reserved). Code/state/input are additional to that table budget.
All playback code stays immutable. Payload remains 23360 bytes, **8:1**
versus mono 8-kHz PCM8. Binary SHA-256:
`c274c5459173c973a1769813ef8f76d7188d7b0a91026d34409e5b3f8ae58466`.

23.36 seconds of speech takes 483.954 nominal CPU seconds: **20.7172x** the
average 437.5-T/sample budget. Output remains consecutive, without pacing.
ULA, disk and physical hardware are unverified. The real-time goal is unmet.

Next intermediate target: **below 9000 T/sample**, exact same full speech,
PCM and table arena. The pitch accumulator consumes only the low 24 bits,
but the constant routines currently return signed32 HL:DE. Investigate
returning A:HL directly and transferring HL through the real stack. For
ordinary constants this could remove 20 T of conversion and 4 T of reloading;
zero could save 10 T, identity 4 T. Current observed calls predict
526693*24 + 18847*10 + 13677*4 = **12883810 T**, or **8994.833 T/sample**.
This is an instruction estimate, not an implemented or executed result.
Recheck zero/identity, carries, skipped pitch taps and register contracts.

Reproduce after restoring the saved fixtures and retaining the round27 build
and report: build.py --skip-host --variant pure-r28-binary and pure-r28;
check_constant_pitch.py checks both; check_round.py --variant pure-r28;
check_unpaced.py --variant pure-r28 --previous pure-r27 --check-default.
Archive with report_round.py --variant pure-r28 --previous pure-r27 --round 28.

[Measurements](report.json), [standard checks](checks.json),
[unpaced checks](unpaced-checks.json), [constant plans](constant-pitch-plan.json),
[exhaustive and all-pitch checks](constant-pitch-checks.json),
[binary comparison](binary/constant-pitch-checks.json),
[generator](../../constant_pitch.py), [checker](../../check_constant_pitch.py).
