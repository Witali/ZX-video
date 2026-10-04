# Round 03: register multiplier versus coefficient tables

2026-10-04. Compare both candidates with cumulative `pure-r2` on the complete
186880-sample speech control. All setup and cache checks are included.

| Variant | Full-stream T | Delta versus round 02 | Decision |
| --- | ---: | ---: | --- |
| Register-based signed multiplier | 3408073402 | -528578900 | Retain for general arithmetic |
| Register multiplier plus synthesis coefficient tables | 3089519959 | -847132343 | Select for the next round |

The generic multiplier keeps products in registers and skips the first eight
iterations when an operand fits a byte. Synthesis additionally splits its
shared sample operand once, then sums four signed32 nibble-table entries per
tap. Each coefficient has one 256-byte page. Build ten pages once per changed
coefficient set; preserve exact signed upper-nibble and 32-bit wrap semantics.
Table generation keeps its output pointer in the alternate register set.

Selected cost is **16532.106 T/sample**, 21.52% fewer T than round 02.
Code 10824 bytes, state 1940, static tables 12658, coefficient tables 2560,
innovation payload 792 in a 1024-byte reserve. Useful table payload is
16010 bytes and its aligned arena is exactly 16384 bytes.

Startup is a tradeoff: the complete first-frame instruction audit is
2308118 T, versus 1990235 for the register-only candidate and 2196131 for
round 02. Full-stream saving, rather than a startup-only estimate, selects
the table variant. Neither is real time.

Both variants match every speech and extra-fixture PCM16/PCM8 value and
pass memory guards. The general primitive suite checks 65536 unsigned
products, 10400 signed16 products, all 25737 cosine angles and Q14 edges.
Additional coefficient checks cover 40960 table entries and 12800 products,
including -32768 and signed upper-nibble cases. Existing signed8 and energy
checks also pass. No decoder mismatch occurred. Clarify the round 02 guard
metadata names: allowed writes include declared dynamic tables, while the
immutability check covers static tables. Counts and checks are unchanged.

See [selected report](report.json), [checks](checks.json), and the
[register-only result](../03-register/report.json). ULA/disk/hardware time
remains excluded. Reproduce with `build.py --skip-host --variant pure-r3`
and `check_round.py --variant pure-r3`; substitute `pure-r3-register` for
the other candidate.
