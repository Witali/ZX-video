# Round 38: read the private Q14 argument without LDIR copying

2026-10-04. Continue from selected round37 on the unchanged full mode-3
speech. The private negative-Q14 helper copies four argument bytes to qarg,
then reloads the high word. Only the low word must survive the first
multiplication. Read both little-endian words directly, save the low word,
and retain the high word in HL for the existing extraction.

## Exact behavior and instruction costs

Both coefficient-sign bodies use the same new sequence. The argument is
read with three INC HL steps, preserving normal page crossings and the
FFFF->0000 wrap of the old LDIR. The LPC argument resides in its polynomial
array, outside Q14 scratch and stack. Keep that nonaliasing contract.

The high word still shifts left twice and combines the low word's top two
bits, exactly reproducing int16(b>>14), including truncation and wrap. The
low product, sign handling and floor/ceiling arithmetic are unchanged.
Preserve IX/IY, all alternate registers and caller SP; ordinary registers
and existing Q14 scratch remain clobbered. qarg+2/+3 are no longer written
by the private path, but remain allocated for the ordinary Q14 entry.

| Replaced region, excluding unchanged coefficient store | T-states |
| --- | ---: |
| EX + LD DE,nn + LD BC,nn + four-byte LDIR + LD HL,(nn) | 4+10+10+(21*3+16)+16 = 119 |
| EX + four LD r,(HL) + three INC HL + LD (nn),DE + EX | 4+7*4+6*3+20+4 = 74 |
| Saving per private call | **45** |

Every affected call is faster by exactly 45 T, independent of signs,
operand values or pointer alignment. The old complete-body formula from
round37 therefore decreases by 45 T; measured domain costs change from
649..2232 T to **604..2187 T**. Two copies of the changed read sequence add
one code byte each. No arithmetic changes, failed native candidates,
reverted attempts or interrupted verification occurred.

| Measurement | Round37 | Selected round38 |
| --- | ---: | ---: |
| Private Q14 T | 155467022 | 151262222 |
| Complete speech T | 1558327641 | 1554122841 |
| T/sample | 8338.6539 | 8316.1539 |
| First complete frame T | 1043840 | 1040240 |
| Code bytes | 9042 | 9044 |

All **93440** observed Q14 operands match the authenticated round32 trace.
The weighted cost and entire saving equal **93440*45 = 4204800 T**, or
**0.26983% less complete CPU**. Each 40-sample subframe runs twenty calls;
every OUT advances by exactly 900 T times the number of preceding subframes.
The profiled execution preserves every uninstrumented OUT timestamp.

Every complete fixture also improves by exactly 22.5 T/sample: each of the
six 3200-sample signals saves 72000 T; six-bank capacity saves 17694000 T;
random packets save 1843200 T; all-pitch input saves 460800 T. PCM and all
payload bytes remain unchanged.

## Verification and memory

- **1343488 arithmetic cases**: every signed16 coefficient against twelve
  boundary arguments; all fourteen-bit fractions against 32 coefficient/
  high-word pairs; 32768 deterministic random signed32 cases. Exact values,
  rounding and instruction formulas pass. Registers/input are preserved;
  all writes are guarded, including both retired upper-argument bytes.
- **18384 pointer/arithmetic cases per binary**, covering 1149 starts around
  every page boundary outside code/state/stack and all three four-byte reads
  crossing FFFF->0000. Both versions preserve every input byte and return
  the same exact result with the expected cost difference.
- **128 pointer-boundary instruction audits per binary**: 16872 old versus
  17128 new instructions, 137920 ->132160 T. Every individual instruction
  matches the Z80 timing table. More short instructions replace slower LDIR.
- **1094880 complete PCM16/PCM8 samples**: 1074400 standard speech/signal/
  capacity/random plus 20480 all-pitch samples. Full playback, code/input
  guards, table/cache controls, ordinary arithmetic helpers and first-frame/
  cached-silence instruction audits pass. A fresh default build has the
  selected image hash. The rest of decoder.s and all filter.s are unchanged
  at source level; final-image checks cover relocation.

Code is **9044 bytes** at 8000..A353 (+2). State remains **1041 bytes** at
B000..B410, stack BF00..BFFF. Useful tables remain **14140 bytes** in the
same 16384-byte arena; code/state/input require additional RAM. Payload is
23360 bytes, 8:1 against mono 8-kHz PCM8. Every playback code write remains
forbidden. Binary SHA-256:
`470dc453454a9fcfe057d10a13e467f03988424e298a87a5f6ca310edbfc786e`.

23.36 seconds of speech needs **444.035 nominal CPU seconds**, still
**19.0084x** the average 437.5-T/sample real-time budget. Output remains
unpaced. The below-8000 intermediate target and the overall real-time goal
remain unmet. ULA, disk and physical hardware timing are unverified.

## Next candidate

The synthesis kernel remains the largest measured phase. Inspect whether
the top feedback nibble is frequently zero. Its operand is n=(-y)&65535,
not y; retain the existing n=0 path. For nonzero n with a zero top nibble,
all ten top-nibble partial products are zero. A specialized kernel could
omit those additions after one sample-level dispatch. First count eligible
samples from the exact feedback values and include dispatch plus code-space
cost before building one candidate. Preserve signed top-nibble semantics,
arbitrary filter history, stack restoration and all stream gates. This
candidate is unimplemented and has no measured saving.

Reproduce with saved fixtures and the round37 build/report/OUT trace:

```text
build.py --skip-host --variant pure-r38
verify.py --native-only --restore-fixture --variant pure-r38
check_q14_argument.py
check_round.py --variant pure-r38
check_unpaced.py --variant pure-r38 --previous pure-r37 --check-default
report_round.py --variant pure-r38 --previous pure-r37 --round 38
```

The completed check_round run used --skip-speech to reuse the verified
speech measurement; every other full fixture was executed normally.

[Measurements](report.json), [standard checks](checks.json),
[arithmetic, pointer/cycle and OUT proofs](q14-argument-checks.json),
[unpaced/default checks](unpaced-checks.json),
[generator](../../q14_negated.py), [checker](../../check_q14_argument.py).
