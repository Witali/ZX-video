# Round 04: compact exact LPC and interpolation

2026-10-04. Candidate `pure-r4` builds on the selected `pure-r3` with unchanged
speech packets and independent reference. LSP codebook values are multiples
of 16, so divide by four before applying the integer interpolation weights.
All intermediates fit signed16 and both reference roundings remain exact.

Each LPC polynomial is palindromic. Keep six signed32 coefficients and
update descending, reflecting the old coefficient index across its midpoint.
Keep Q14 product rounding/truncation unchanged. Replace products involving
the constant 2^20 endpoint with exact shifts. This reduces general Q14 calls
per LPC reconstruction from 50 to 20 and temporary polynomial storage from
624 to 48 bytes; remove two obsolete temporary words as well. No whole-array
clearing is needed because every used coefficient has already been assigned.

Full speech: **2759257254 T**, delta **-330262705 T** (10.69% fewer T,
1.120x speedup), **14764.861 T/sample**. LPC phase drops from 629670182 to
317769021 T. First-frame instruction audit is 2016616 T, delta -291502 T.
Code falls from 10824 to 6152 bytes; state falls from 1940 to 1356. The
aligned table arena remains 16384 bytes, useful payload 16010.

Every speech and seven extra-fixture PCM16/PCM8 value matches. All generic
and specialized arithmetic, table-product checks, memory guards and the
complete first-frame instruction audit pass. No decoder mismatch occurred.
Accept this exact optimization. Full hardware timing is not measured and
the nominal CPU rate still fails real time. See [report](report.json) and
[checks](checks.json).

```powershell
python audiobook-beeper/speex-port/build.py --skip-host --variant pure-r4
python audiobook-beeper/speex-port/check_round.py --variant pure-r4
```
