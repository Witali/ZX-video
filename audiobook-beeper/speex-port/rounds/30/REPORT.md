# Round 30: shorter exact synthesis shift

2026-10-04. Continue from round29 on the unchanged mode-3 speech control.
After rounding the 32-bit filter state and discarding its lowest byte, the
synthesis loop shifted signed24 E:HL right five times. Replace that block
with sign extension into A:E:HL, three left shifts and selection of the upper
three bytes. For signed24 x, sign_extend(x)<<3 fits signed32; dropping the
low byte therefore reproduces arithmetic x>>5, including negative values.

The block preserves D/BC, IX/IY, all alternate registers and SP. It clobbers
AF; the following excitation sign extension overwrites flags before use.
Rounding, input fetching, clipping, history updates and PCM output stay exact.
The generated source documents this arithmetic and the flag dependency.

## Measured timing

Old block: five SRA E / RR H / RR L groups, **5*3*8 = 120 T**.
New block: sign extension 12 T, three ADD HL,HL / RL E / RLA groups at
11+8+4 T each, and three byte transfers at 4 T each:
**12 + 3*(11+8+4) + 12 = 93 T**. Saving **27 T for every sample**.
Including the unchanged load, rounding and initial byte discard, the paths
fall **201/202 -> 174/175 T**, depending on low-word rounding carry.

Complete speech **1680861924 -> 1675816164 T**, exactly
**186880*27 = 5045760 T saved**, **0.3002% fewer T**.
Average **8994.3382 -> 8967.3382 T/sample**. Every one of the 186880 OUT
trace deltas equals 27*(sample_index+1), proving the saving occurs at each
sample rather than being inferred only from a total. First complete frame
including startup **1132552 -> 1128232 T** (-4320).

## Verification

Execute both old and new blocks on **393216 signed24 cases per variant**:
every upper word combined with six low-byte boundary patterns, varying
incoming flags. Compare independent arithmetic right-shift results, constant
costs, preserved registers and absence of all CPU writes.

Also test **every one of the 524288 signed32 >>13 rounding boundaries**,
immediately before, at and after each boundary: **1572864 cases per variant**.
The independent model explicitly wraps history+4096 modulo32, including
signed overflow and low-word carry. All results, the 201/202 and 174/175-T
path costs and register contracts match. Independently instruction-step 12
shift extrema/boundaries and 10 full rounding cases per variant.

Both versions pass 128 complete filter calls / 5120 samples each with
arbitrary signed coefficients, excitation and 32-bit history, exact final
history, PCM16/PCM8, SP/IX/IY and guarded memory. Selected **pure-r30** also
passes the standard **1074400 samples** and the archived upstream **20480
all-pitch samples**: **1094880 exact complete-stream samples**. All-pitch
total **185709684 -> 185156724 T** (-552960 = 20480*27).

Generic arithmetic, table generation/cache, controls, full-frame/cached-silence
instruction audits, protected playback code/RAM and a fresh default build
identity pass. No failed implementation or interrupted verification occurred.

## Selection, memory and next work

Select **pure-r30**. Code **8898 bytes** at 8000..A2C1, **12 bytes smaller**.
State remains 1041 bytes at B000..B410, reserved stack 256 bytes at BF00..BFFF.
Tables remain 16010 useful bytes in a 16384-byte arena, separate from code,
state and stored input. Speech payload remains 23360 bytes, **8:1 versus
mono 8-kHz PCM8**. All playback code is immutable. Binary SHA-256:
`8f18a320b0563c07f799f8d3877078993fd9d750ca602f1a884bae20e51cd27f`.

23.36 seconds of speech takes 478.805 nominal CPU seconds. The average
real-time goal remains unmet by **20.4968x** against 437.5 T/sample.
No pacing is introduced. ULA, disk and physical hardware are unverified.

Next investigate the general signed16x16 kernel used by LPC reconstruction.
The unchanged kernel's round25 profile measured 186880 calls / 167043802 T,
about 9.97% of the current total. Its serial 32-bit shift uses ADD HL,HL,
RL C and RL B. Prototype two unsigned8x16 combined-register products and
combine the low/high byte contributions, counting sign handling, zero and
byte fast paths, register preservation, calls and final carry propagation.
Observe actual operands on the current full speech and compare complete
costs before selecting. No speedup for this next candidate is yet measured.

Reproduce after restoring saved fixtures and retaining round29 build/report:

```text
build.py --skip-host --variant pure-r30
check_round.py --variant pure-r30
check_synthesis_shift.py
check_unpaced.py --variant pure-r30 --previous pure-r29 --check-default
report_round.py --variant pure-r30 --previous pure-r29 --round 30
```

[Measurements](report.json), [standard checks](checks.json),
[shift/rounding/filter/OUT checks](synthesis-shift-checks.json),
[unpaced checks](unpaced-checks.json), [transform](../../followup_opt.py),
[checker](../../check_synthesis_shift.py).
