# Round 02: cached exact innovation tables

2026-10-04. Compare cumulative `pure-r2` with `pure-r1` on the same complete
speech control. Build two signed24 tables covering shape values -65..66.
Compute the initial quotient once, then advance quotient/remainder using
additions with exact floor rounding. Reuse both tables until the frame gain
changes. Lookup replaces per-sample Q12 multiplication. Construction and
cache checks are included in all CPU measurements.

Full-stream cost: **3936652302 T**, delta **-191694959 T** (4.64% fewer T,
1.049x speedup). First-frame instruction audit: 2196131 T, delta -93459 T.
Code 10501 bytes, state 1904, static table payload 12658, dynamic table payload
792 in a 1024-byte reserve at 7C00..7FFF. The complete table arena spans
16 KiB, leaving the 2560 bytes at 7200..7BFF free for the next experiment.

All speech samples, all seven additional streams, memory guards, 12048
signed products and 5056 Q12 cases pass. All 8448 entries of every possible
energy table match direct reference arithmetic. Every instruction in the
first frame matches the independent timing table. No decoder mismatch was
encountered. Accept the optimization; real time still fails. ULA, disk and
hardware remain excluded. See [report](report.json) and [checks](checks.json).

```powershell
python audiobook-beeper/speex-port/build.py --skip-host --variant pure-r2
python audiobook-beeper/speex-port/check_round.py --variant pure-r2
```
