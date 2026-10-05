# Round 26: register-held pitch accumulation

2026-10-04. Continue from exact round24 on the unchanged complete mode-3
speech. Preserve the three pitch-history selections and all gain products.
Keep their modulo24 sum in alternate HL/C during each excitation sample.
The signed8 multiply and its neg32 tail preserve these registers. Transfer
each product's low word via the real stack and combine its high byte with
the word-add carry. Write the three-byte sum to the existing scratch only
after all active-or-skipped taps have finished. The fourth allocated scratch
byte is not read by the current excitation path and remains untouched.

## Exact timing

The former RAM accumulation costs **89 T per active product**. The new
sequence costs **52 T**: PUSH DE 11, LD A,L 4, EXX 4, POP DE 10,
ADD HL,DE 11, ADC A,C 4, LD C,A 4, EXX 4. Real SP is unchanged after each
transfer. Initialization costs **42 -> 25 T**, with a new **41-T** final
writeback. Thus net saving is **37 T/active term minus 24 T/sample**.

With 559217 active terms and 186880 samples, the predicted **16205909 T**
saving matches complete execution exactly: **1850951266 -> 1834745357 T**,
**9817.7727 T/sample**, 0.876% fewer T. The first-frame audit falls
**1214473 -> 1201256 T** (-13217), including all packet/LPC/output work.

## Verification

All **1074400 PCM16/PCM8 samples** remain exact across full speech, signals,
six-bank capacity and 512 random packets. Existing arithmetic, table/cache,
memory/code-write guards, input controls, full first-frame and cached-silence
instruction audits pass. A fresh default build matches SHA-256
`fc566280c135d0d92d39ab84253b9fa6829837ad6b65b65049558aed72eb72fe`.

Additional checks execute **200187 modulo24 additions**, covering every
low word and boundary/random high bytes, plus **1037 exact three-byte
writebacks**. Writes are limited to the real stack and declared sum bytes;
the fourth byte is guarded. All three add blocks, initialization and flush
match independent per-instruction timing counts. The multiply checker runs
**589824 products**, nine signed multipliers across the complete word
domain, preserving alternate AF/BC/DE/HL, IX/IY and the caller stack on
every case. Generic/specialized existing tests cover other multiplier edges.

The initial new block checker stopped repeatedly at a shared flush-entry /
previous-block-end breakpoint; that verification run was interrupted. The
harness now explicitly resumes such entries and fails on unexpected
non-progress. Its instruction audit clears the entry breakpoint instead of
executing an uncounted first instruction. Final assertions require complete
25/52/41-T block totals. This was a checker issue, not a decoder mismatch.

## Decision and next candidate

Select **pure-r26**. Code **7320 bytes** (-23), state 1041 and stack reserve
256 unchanged. Tables remain 16010 useful bytes in their 16384-byte arena;
the speech payload remains 23360 bytes / 8:1 versus PCM8. Output is unpaced.
23.36 seconds of sound takes 524.213 nominal CPU seconds; average real-time
deficit is still **22.4406x**. ULA, disk and hardware remain unverified;
the broader throughput goal is active.

Next inspect a fast history-address path for pitch >=41. For j=0..39 and
delays pitch+1, pitch, pitch-1, all three indices are negative and adjacent:
no second-period subtraction or skipped tap is needed. One advancing IX
cursor could replace three repeated address calculations. Preserve the
existing path for smaller pitch values and include the selection/setup cost.
Direct inspection of the unchanged packets finds **3519 of 4672 subframes**
with pitch >=41, leaving 1153 on the general path. This is an input count,
not a measured speedup; no candidate has been implemented yet. To reproduce
the count, read seven pitch bits at offsets `28+33*subframe` in each 160-bit
mode-3 packet, then add 17.

Reproduce `build.py --skip-host --variant pure-r26`,
`check_pitch_accumulator.py`,
`check_s8_combined.py --variant pure-r26 --check-alternates`,
`check_round.py --variant pure-r26`, and
`check_unpaced.py --variant pure-r26 --previous pure-r24 --check-default`.
[Measurements](report.json), [full checks](checks.json),
[accumulator checks](pitch-accumulator-checks.json),
[helper preservation](s8-domain-checks.json), [unpaced checks](unpaced-checks.json),
[transform](../../followup_opt.py), [checker](../../check_pitch_accumulator.py).
