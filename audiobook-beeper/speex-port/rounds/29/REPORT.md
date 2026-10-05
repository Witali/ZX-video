# Round 29: direct signed24 pitch products

2026-10-04. Continue from round28 on unchanged mode-3 speech and consecutive
PCM8 output. Constant products were converted from A:HL to signed32 HL:DE,
then the pitch sum consumed only L:DE. Return A:HL directly and push HL
across EXX instead. The high product byte remains in A; ADD HL,DE supplies
the carry for ADC A,C. No signed32 conversion or LD A,L is needed.

## Exact costs and completed milestone

Ordinary routines remove five 4-T instructions before RET: **20 T saved**.
The caller's sum block falls **52 -> 48 T**, with the real SP unchanged.
Zero uses XOR A / LD H,A / LD L,A / RET, **30 -> 22 T**. Identity uses sign
extension into A and EX DE,HL, **30 -> 26 T**. Both are cheaper than the
initial proposed zero/identity sequences. The indirect call is unchanged.
The final product range fits signed24 for every book gain and signed16 word.
All alternate registers and IX/IY remain preserved by the product routines.

| Active product kind | Observed calls | Total saving per call |
| --- | ---: | ---: |
| Ordinary | 526693 | 24 T |
| Zero | 18847 | 12 T |
| Identity | 13677 | 8 T |

**526693*24 + 18847*12 + 13677*8 = 12976212 T** saved. The sum matches the
complete executed delta exactly: **1693838136 -> 1680861924 T**, **0.7661%
fewer T**, **9063.7743 -> 8994.3382 T/sample**. This passes the below-9000
intermediate target. The initial 8994.833 estimate was conservative because
it used more expensive zero/identity returns. First complete frame including
startup falls **1140964 -> 1132552 T** (-8412).

## Verification

All **4259840 constant/word products** match independent signed24 arithmetic;
constant costs, all 96 pointers, sizes, register contracts and guarded writes
pass. Independently step 11394 instructions across nine signed/carry boundary
words per routine. For both old and new binaries, test **200187 modulo24
additions**, covering every low word and high-byte carry/wrap cases.

For **all 32 codebook triples, all 128 pitch periods and all 40 positions**,
execute both complete pitch-sum paths: **163840 cases per variant**. Every
history-byte address, modulo24 sum, SP/IY/alternate AF value and advancing IX
cursor matches the independent model. Include skipped taps and the 40/41
path threshold. Every observed cycle delta matches the active products'
individual savings; 48 boundary executions are instruction-stepped.

The standard **1074400 PCM16/PCM8 samples** plus the archived upstream
**20480 all-pitch samples** pass: **1094880 complete-stream samples**. The
all-pitch fixture falls **187146244 -> 185709684 T** (-1436560). Controls,
generic arithmetic, innovation/coefficient tables and caching, full frame
and silence instruction audits, protected code/RAM writes and fresh default
build identity pass. Rebuilding round28 with the updated generator also
reproduces its archived binary and assembly exactly. No failed implementation
or interrupted verification occurred in this round.

## Selection, memory and remaining objective

Select **pure-r29**. Code **8910 bytes** at 8000..A2CD, **325 bytes smaller**:
319 fewer routine bytes and six removed caller instructions. State remains
1041 bytes at B000..B410, reserved stack 256 bytes at BF00..BFFF. Tables
remain 16010 useful bytes inside the 16384-byte arena, separate from code,
state and input storage. Payload remains 23360 bytes / **8:1 versus PCM8**.
All playback code is immutable. Selected binary SHA-256:
`0b820e8dfaa8056a5f47b569219bea6fb6c3e0390b170eb83945d9580c5bfe2b`.

The average real-time goal is still unmet: 23.36 seconds of speech takes
480.246 nominal CPU seconds, **20.5585x** the 437.5-T/sample average budget.
No pacing is added. ULA, disk and physical hardware are unverified.

Next inspect the synthesis filter's five arithmetic right shifts of signed24
E:HL after the initial byte discard. Proposed equivalent: initialize A with
the sign of E, perform three ADD HL,HL / RL E / RLA steps, then select the
upper three bytes. Cost **12 + 3*(11+8+4) + 12 = 93 T versus 120 T**, saving
**27 T/sample**, including zero-feedback output. Current full count predicts
5045760 fewer T, **8967.338 T/sample**. This is an unimplemented instruction
estimate; verify signed extrema, rounding transitions and full streams before
selection. It does not complete the real-time goal.

Reproduce with the saved fixtures and round28 build/report:

```text
build.py --skip-host --variant pure-r29
check_constant_pitch.py --variants pure-r29 --previous pure-r28
check_pitch_direct.py
check_round.py --variant pure-r29
check_unpaced.py --variant pure-r29 --previous pure-r28 --check-default
report_round.py --variant pure-r29 --previous pure-r28 --round 29
```

[Measurements](report.json), [standard checks](checks.json),
[unpaced checks](unpaced-checks.json), [constant plans](constant-pitch-plan.json),
[constant products and extra stream](constant-pitch-checks.json),
[sum/address checks](direct-pitch-checks.json),
[generator](../../constant_pitch.py), [path checker](../../check_pitch_direct.py).
