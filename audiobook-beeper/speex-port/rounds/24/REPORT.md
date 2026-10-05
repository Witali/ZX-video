# Round 24: add a pre-negated coefficient-table step

2026-10-04. Continue from exact round23-pop on unchanged mode-3 speech.
Keep the table layout, cache, reverse PUSH stores and upper-nibble midpoint.
Negate the 32-bit step once per partial table; replace each 42-T subtraction
with a 34-T ADD/ADC update. The accumulator and saved positive next-group
step remain unchanged. All operations retain exact modulo32 arithmetic.

The initial prototype incorrectly used SBC A,A / SUB D to negate a word
while propagating carry into another word. That sequence obtains the right
low word but loses the outgoing borrow for values such as -32767. The
independent full-domain check rejected the second coefficient before full
stream testing; [failure log](initial-negation-failure.log). Replace it with
LD A,0 / SBC A,D, preserving the low-byte borrow and outgoing high-byte
borrow. No incorrect prototype is selected or claimed as a timing result.

## Timing and arithmetic checks

General negation costs 65 T. In groups shifted by eight/twelve bits, E is
zero, so negating D directly preserves the right outgoing borrow and costs
50 T. Four setups total **230 T**. There are 64 descending updates per
page, each saving eight T: net **64*8-230 = 282 T per changed page**.
An unchanged cache hit remains **976 T**. Typical page-zero change falls
from **8646 to 8364 T**; its first special comparison costs 8692 -> 8410 T.

Execute both builders for **all 65536 signed16 coefficients**: every one
of **4194304 table entries per variant** matches an independent product
formula; every changed-page call saves exactly 282 T. Other nine pages are
write-protected during this sweep, and SP/IX/IY remain intact. Separately
run **262144 step-negation cases**, checking preservation of accumulator
halves and exact 65/50-T costs. All four blocks pass instruction audits.
The full ten-page preparation audit falls **59433 -> 56613 T** (-2820),
with every instruction and table entry checked. The complete first frame
falls **1220113 -> 1214473 T** (-5640).

Complete speech: **1863554410 -> 1850951266 T**, delta **-12603144 T**,
**9904.4909 T/sample**, 0.676% fewer T. The delta corresponds to 44692
changed pages at 282 T each; this page count is inferred from the delta,
not separately instrumented in this round. All **1074400 PCM16/PCM8
samples** remain exact, including signals, full six-bank capacity and 512
random packets. Existing arithmetic, cache, memory, code immutability,
input-control and cached-silence instruction checks pass. A fresh default
build matches SHA-256
`3619271b53cde905473fa1d56f75155f747e16b15f69392c614828677b0d8661`.

## Decision

Select **pure-r24**. Code **7343 bytes** (-68), state 1041 and stack reserve
256 unchanged. Tables still use 16010 useful bytes in the 16384-byte arena;
stored speech remains 23360 bytes / 8:1 versus PCM8. Output remains unpaced.
Average CPU cost still exceeds the real-time budget **22.6388x**. No ULA,
disk or hardware claim; the broader goal remains active.

Next refresh the complete nested profile for the inline filter, separating
its feedback block from its remaining sample work and independently counting
changed coefficient pages. Use current measured costs to choose the next
structural optimization instead of assuming the old callable-product
profile still applies.

Reproduce `build.py --skip-host --variant pure-r24`,
`check_coefficient_steps.py`, `check_round.py --variant pure-r24`, and
`check_unpaced.py --variant pure-r24 --previous pure-r23-pop --check-default`.
Retain the round23-pop binary for the full-domain comparison.
[Measurements](report.json), [full checks](checks.json),
[coefficient/negation checks](coefficient-step-checks.json),
[unpaced checks](unpaced-checks.json), [transform](../../followup_opt.py),
[checker](../../check_coefficient_steps.py).
