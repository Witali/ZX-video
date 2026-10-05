# Round 07: specialize product lookup offsets

2026-10-04. Same 1168-packet / 186880-sample speech and upstream reference
as round 04. Patch four `LD L,n` immediate bytes once per sample; reuse
those offsets for ten coefficient products. No opcodes are modified.
The native verifier permits writes to exactly those four bytes and checks
all other code and static tables remain unchanged. RAM code, disabled IRQ
and non-reentrant decoding are explicit requirements already met by entry.

Full speech: **2684505254 T**, delta **-74752000 T**, **14364.861 T/sample**.
The saving is exactly 400 T/sample: `(13+4-7)*4*10`; offset stores retain
their previous 13-T cost. Code 6144 bytes (delta -8), state 1356, tables
unchanged at 16010 useful bytes in a 16384-byte arena. Select this change.

All speech and seven signal/capacity fixtures match PCM16 and PCM8.
12800 table products, 40960 coefficient entries and excitation checks pass.
The complete first-frame instruction audit is 1952616 T, delta -64000 T,
and every instruction matches the independent Zilog timing table.
This remains far outside real time; ULA and physical hardware are excluded.
An early archive command ran before fixture verification finished and found
no checks.json; rerunning after successful completion produced this archive.

Reproduce with `build.py --skip-host --variant pure-r7`, then
`check_round.py --variant pure-r7`. See [report](report.json),
[checks](checks.json), and [transform](../../followup_opt.py).
