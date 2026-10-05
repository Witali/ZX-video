# Round 31: general products from unsigned byte/word partials

2026-10-04. Continue from round30 on unchanged mode-3 speech. The general
signed16x16 kernel used a serial BC:HL accumulator, shifting two upper bytes
with CB-prefixed RL. Replace it with two unsigned8x16 products:
lo8(a)*b + (hi8(a)*b)<<8. Normalize signs once; retain the one-product byte
shortcut when either magnitude fits a byte. Zero entry paths are unchanged.
Magnitude 32768 is unsigned and valid, so -32768 needs no special saturation.

The unsigned core reuses A for incoming multiplier bits and the emerging
high product byte, with HL as the low word. Skip leading zeros, initialize
HL from DE for the first one, then use ADD HL,HL / RLA and conditional
ADD HL,DE / ADC A,0. It returns A:HL and preserves BC/DE, IX/IY, all
alternate registers and SP. The nonzero entry omits the general zero check.

For two partials, retain the multiplier high byte in B, then the low partial's
high byte in C and its low word on the real stack. Combine bytes with one
ADD/ADC carry chain before applying the original sign. The public result
remains exact signed32 HL:DE; IX/IY and all alternates remain preserved.
Only the existing mul_sign byte and real stack are written. The deepest new
path adds four bytes below the routine's entry SP; the 256-byte reserve and
complete guarded playback remain sufficient. No new table or BSS is added.

## Instruction costs and complete comparison

For nonzero unsigned byte x, let k=bit_length(x), p=popcount(x). The unsigned
nonzero entry costs **11*(8-k) + 34 + 27*(k-1) + 13*(p-1) + 10 T**, including
RET. The general entry adds 16 T for nonzero x, or returns zero in **29 T**.
The old serial bit costs **39 T for zero**, **57/58 T for one**, depending
on low-word addition carry. The saved checker derives both full signed costs,
including entry, signs, dispatch, zero/byte cases, nested calls and RET.

Shared nonzero entry/sign costs are 35+28 T, then 20/39 T per positive/
negative argument. Dispatch adds 20 T when the first magnitude is a byte,
34 T when swapping the second byte magnitude, or 35 T for two word magnitudes.
New byte body costs 46 T plus its unsigned nonzero product; word body costs
114 T plus general-low and nonzero-high products. Final sign handling costs
28/89 T for positive/negative output. Zero paths remain 50/60 T depending
on which argument is zero.

A lower-bound sweep covers all 32768 possible nonzero normalized multiplier
magnitudes. Cancel the identical sign/dispatch costs and assume no old
low-word carries: every nonzero byte path saves **at least 94 T**, every
word path **at least 110 T**. Old carries can only increase these savings.
This is a nominal instruction-count guarantee, not a ULA/hardware result.

Observe both complete executions: **186880 calls**, **159013 unique input
pairs**, with every pair unchanged. Classes: 44611 byte, 141690 word, 579
zero. Execute every unique pair in isolation on both binaries; the weighted
instruction-derived costs equal the respective profiled function totals.

| Measurement | Round30 | Selected round31 |
| --- | ---: | ---: |
| General multiplier T | 167043802 | 126588295 |
| Complete speech T | 1675816164 | 1635360657 |
| Complete T/sample | 8967.3382 | 8750.8597 |

The multiplier saves **24.2185%**; complete CPU saves **40455507 T / 2.4141%**.
The difference between the function totals equals the entire stream saving,
including all wrapper/setup costs. First complete frame **1128232 -> 1094940
T** (-33292). The baseline instrumented run preserves every saved OUT timestamp.
Current operand pairs are archived with their uncompressed SHA-256 for reuse:
`9d4ea89c50eb01f74ab39613d3560d2acb8db95c6ee72006f5201f27a1524f10`.

## Verification

Execute **all 16777216 unsigned8x16 input pairs** and compare the full 24-bit
product, exact cost formula and BC/DE/IX/IY/alternate/SP preservation. Also
check 1785 boundary pairs through the nonzero entry. Execute **2228224 signed
products**: every signed word in both argument orders against 17 fixed
zero/sign/byte/word extrema, with exact signed32 results, costs and guarded
writes. Independently instruction-step 256 signed boundary pairs per binary,
20384 instructions in the baseline and 17405 in the selected implementation.

The standard **1074400 PCM16/PCM8 samples** and archived upstream **20480
all-pitch samples** pass: **1094880 exact complete-stream samples**. All-pitch
total **185156724 -> 180714036 T** (-4442688); every standard fixture improves.
General arithmetic including Q14, table generation/cache, controls, full-frame
and cached-silence instruction audits, protected code/RAM and fresh default
identity pass. The quick probe was followed by complete exhaustive/domain
and stream verification. No failed candidate or interrupted verification
occurred in this round.

## Selection and remaining work

Select **pure-r31**. Code **8859 bytes** at 8000..A29A, **39 bytes smaller**.
State remains 1041 bytes at B000..B410, reserved stack 256 bytes at BF00..BFFF.
Tables remain 16010 useful bytes within a 16384-byte arena, separate from
code/state/input. Payload remains 23360 bytes, **8:1 versus mono 8-kHz PCM8**.
All playback code is immutable. Binary SHA-256:
`cd86cb9bcbf5e1162f753e07724acd6a9f7a64584de30a5de1f8d2b913099d3f`.

23.36 seconds of speech takes 467.246 nominal CPU seconds. The real-time
average goal is still unmet by **20.0020x** against 437.5 T/sample. Output
remains unpaced. ULA, disk and physical hardware are unverified.

Next investigate sharing coefficient preparation between the two products
inside MULT16_32_Q14. Both calls use the same coefficient but independently
normalize signs and restore signed products. Reuse the saved operand trace
to quantify duplicated work before implementing a fused path. Preserve the
intentional signed16 truncation of the high argument and arithmetic rounding
of the negative fractional product; a mathematically similar full product
is insufficient without those exact semantics. Compare full wrapper cost,
including extraction, storage and final combination. No next speedup is yet
measured; retain the public general multiplier contract and table budget.

Reproduce with saved fixtures and the round30 build/report/OUT trace:

```text
build.py --skip-host --variant pure-r31
check_word_product.py
check_round.py --variant pure-r31
check_unpaced.py --variant pure-r31 --previous pure-r30 --check-default
report_round.py --variant pure-r31 --previous pure-r30 --round 31
```

[Measurements](report.json), [standard checks](checks.json),
[word products, costs and trace checks](word-product-checks.json),
[observed signed operand pairs](observed-word-operands.i16.gz),
[unpaced checks](unpaced-checks.json), [generator](../../word_product.py),
[checker](../../check_word_product.py).
