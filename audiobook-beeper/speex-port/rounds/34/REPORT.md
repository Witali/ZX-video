# Round 34: cancel redundant EXX pairs in coefficient preparation

2026-10-04. Continue from round33 on unchanged complete mode-3 speech.
Each table recurrence returned to the lower register set, immediately
followed by another EXX to PUSH the upper product word. Remove those
adjacent EXX/EXX pairs only inside the changed-page builder. There are
64 pairs: four groups of sixteen rows. Each identity pair costs 8 T and
two code bytes, so the predicted reduction is 512 T per changed page and
128 bytes of code. IRQ remains disabled while SP is borrowed for writing.

## Source and instruction evidence

The generator asserts the exact 64-pair count. The checker strips only
comments and confirms that removing those pairs accounts for every changed
instruction in the block; all labels and other instructions match. Decoder
text before/after the block and the entire filter source are unchanged.
Two consecutive EXX operations restore BC/DE/HL and their alternates and
leave AF, flags, memory and SP unchanged. No label or instruction intervenes
in any removed pair.

A recurrence plus row write costs **64 -> 56 T**, saving 8 T across each
of 64 rows. A warm call changing only page zero normally costs
**8364 -> 7852 T**; the first full-domain case takes **8410 -> 7898 T**.
Both save exactly 512 T. A fully cached call remains **976 T**. The
independent ten-page construction audit costs **56613 -> 51493 T**, saving
5120 T, and executes 7226 -> 5946 instructions. Every instruction agrees
with the Z80 timing table, and all 640 entries match the integer reference.

Observe both complete speech runs: all **4672 coefficient arrays** match.
There are **44692 changed pages**, with 199 calls changing none, one changing
eight, 36 changing nine and 4436 changing all ten. The measured preparation
saving and complete playback saving are both exactly **44692*512 = 22882304
T**. Profiling preserves every saved OUT timestamp in both variants.
The observed coefficient arrays are archived for later preparation work.

| Measurement | Round33 | Selected round34 |
| --- | ---: | ---: |
| Preparation T | 254106133 | 231223829 |
| Complete speech T | 1618979214 | 1596096910 |
| T/sample | 8663.2021 | 8540.7583 |
| First complete frame T | 1081400 | 1071160 |
| Code bytes | 9046 | 8918 |

Select the **1.4134% complete CPU saving**, with **9.0050% less preparation
CPU**. All other complete fixtures improve: silence -10240 T, impulses
-235520 T, low tone -30720 T, high tone -144896 T, noise -393216 T, level
jumps -174080 T, six-bank capacity -10240 T, random packets -10463232 T
and all-pitch input -2583040 T. Cached tables explain the small silence/
capacity improvement. No failed candidate, revert or interrupted verification
occurred; the initial complete comparison was followed by the full gates.

## Verification and memory

- Every signed16 coefficient on both binaries: **65536 coefficients and
  4194304 exact table entries per variant**. Cost difference is always
  512 T; input, other pages, code and memory writes are guarded. SP/IX/IY
  remain correct. Final all-cached calls take 976 T on both binaries.
- All **1024 masks** of changed/unchanged pages with randomized coefficients
  and register seeds, plus 1024 immediate cached repeats per variant.
  Verify every table byte, unchanged input, all permitted register outputs
  including AF/flags/alternates, identical BSS, caller SP/IX/IY, and a
  512*changed_pages cost difference. Every unchanged page is write-protected;
  repeated cached calls forbid every table write.
- Standard **1074400** plus all-pitch **20480 complete PCM16/PCM8 samples**
  pass, totalling **1094880 exact samples**. Generic primitives, table/cache
  checks, controls, complete-frame/cached-silence instruction audits and
  protected playback memory pass. Fresh default image identity matches.

Code is 8918 bytes at 8000..A2D5, 128 bytes smaller. State remains 1041
bytes at B000..B410, reserved stack BF00..BFFF. Tables remain 16010 useful
bytes within a 16384-byte arena; code/state/input are additional RAM.
Payload stays 23360 bytes, 8:1 against mono 8-kHz PCM8. All playback code
writes remain forbidden. Selected binary SHA-256:
`11eadd8ba8f47e16c3ff1ba3cff0b7506dbf48653c98fffa71f643681f485cff`.

23.36 seconds of audio needs 456.028 nominal CPU seconds, **19.5217x**
the 437.5-T/sample real-time budget. Output remains unpaced; ULA, disk and
physical hardware are unverified. The average real-time goal remains active.

## Next candidate toward the 8500 target

The below-8500 intermediate target remains unmet: another **7616910 T**
is needed to reach 8500 T/sample, about 0.477% of current complete CPU.
The builder still stores and reloads 16*step through coef_step for each
of its first three groups. BC/BC' are free during those unrolled rows.
Keeping the saved value there predicts **40 T/group**, or **120 T/page**,
from 40+48 T memory save/reload to 24+24 T register copies.

The group-end stack address also uses a general 16-bit addition despite
coef_out always being page-aligned. Setting L for groups 0..2 predicts
43 -> 29 T each; incrementing H for group 3 predicts 43 -> 26 T. Together
that is **59 T/page**, for a combined **179 T/page / 7999868 T** estimate
on the saved changed-page count. Predicted result: **8497.951 T/sample**.
This candidate has not been implemented or executed; the target is not
claimed achieved. Verify all coefficient/table values, page alignment,
cache and caller contracts, and complete decoding before accepting it.

Reproduce with saved fixtures and round33 image/report/OUT trace:

```text
build.py --skip-host --variant pure-r34
verify.py --native-only --restore-fixture --variant pure-r34
check_preparation_exchanges.py
check_round.py --variant pure-r34
check_unpaced.py --variant pure-r34 --previous pure-r33 --check-default
report_round.py --variant pure-r34 --previous pure-r33 --round 34
```

The completed run reused the already verified speech measurement with
check_round.py --skip-speech; all other full fixtures were executed normally.
The optional full repeat above reproduces the same speech evidence.

[Measurements](report.json), [standard checks](checks.json),
[coefficient domains, masks, instruction audits and profiles](preparation-exchange-checks.json),
[observed coefficient arrays](observed-lpc-coefficients.i16.gz),
[unpaced/default checks](unpaced-checks.json),
[generator](../../followup_opt.py), [checker](../../check_preparation_exchanges.py).
