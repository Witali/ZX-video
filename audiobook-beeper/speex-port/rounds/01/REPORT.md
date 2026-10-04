# Round 01: exact excitation arithmetic

2026-10-04. Baseline `pure-fast`, candidate `pure-r1`; the same complete
186880-sample speech input and independent Speex 1.2.1 reference.

Remove the common factor 128 from pitch gains. The resulting signed gains
are -50..97; their maximum absolute sum is 147. Use a signed 8x16 routine
and a 24-bit accumulator. Clamp the unscaled sum at +/-2048000, calculate
innovation as floor(shape*energy/4096), and output
`clip((2*sum + innovation + 64) >> 7)`. The bounded numerator fits signed24.
All rounding and saturation remain exact. The generic synthesis multiplier
and LPC reconstruction are unchanged.

Full-stream cost falls from 4536172045 to **4128347261 T**, delta
**-407824784 T** (8.99% fewer T, 1.099x speedup). Average is 22090.899 T/sample.
Code is 10293 bytes, state 1886 and static tables 12658. No new table RAM.
First-frame instruction audit: 2289590 T versus baseline 2361219 T,
delta -71629 T. Every instruction agrees with the independent timing table.

All speech and seven additional complete fixtures, including maximum
six-bank capacity, match PCM16/PCM8. 12048 signed8x16 cases and all 5056
energy/shape pairs pass. The measured multiplier range is 41..664 T.
All native memory guards pass. The first audit attempt exposed a harness
yield between an index prefix and opcode at an emulator frame boundary;
the audit now finishes that instruction before comparing its full timing.
This was an audit issue, not a decoder mismatch.

Accept the optimization. Real time still fails. CPU results exclude ULA,
disk and hardware. See [report](report.json), [checks](checks.json), and the
saved assembly/image/map in this directory. Reproduce from the worktree:

```powershell
python audiobook-beeper/speex-port/build.py --skip-host --variant pure-r1
python audiobook-beeper/speex-port/check_round.py --variant pure-r1
```
