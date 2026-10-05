# Round 18: combined-register signed 8x16 multiplication

2026-10-04. Follow the round17 complete profile: signed 8x16 products cost
300146569 T on unchanged round16 speech. Retain exact Speex mode-3 input,
PCM16 feedback and PCM8 port output. Compare three implementations, using
bounded arithmetic/frame checks before the complete speech run.

| Candidate | Complete speech T | T/sample | Decision |
| --- | ---: | ---: | --- |
| Round16 separate accumulator and multiplier | 2164784952 | 11583.824 | Baseline |
| A:HL, fixed eight steps (`pure-r18-fixed`) | 2105364513 | 11265.863 | Superseded |
| A:HL, skip leading zeros (`pure-r18`) | 2066995457 | 11060.549 | Superseded |
| Also retain signed word (`pure-r18-signed`) | **2042203676** | **10927.888** | Select |

Each candidate preserves all 186880 speech samples, specialized primitives
and a complete first-frame instruction audit. Only the selected candidate
receives the full signal/capacity/random suite below. Superseded images,
source and scoped checks remain under [candidates](candidates/).

## Exact algorithm and timing

Use A for the unread multiplier bits and the high product byte; HL holds
the low product word. Each `ADD HL,HL / RLA` shifts the accumulator while
extracting the next multiplier bit. A selected addition uses `ADD HL,DE /
ADC A,0`. For unsigned multiplier m and word w, after i bits the combined
register is `((m*2^i) mod 256)*65536 + floor(m/2^(8-i))*w`. The low product
term stays below `2^i*65536`, so no hidden carry can corrupt unread bits.
At i=8 the register contains exactly m*w. A zero prefix can be skipped;
the first set bit initializes HL directly from DE.

The final candidate retains DE's original bit pattern. If DE is negative,
subtract abs(m) from the high result byte: unsigned(DE) differs from its
signed value by 65536. Then sign-extend the 24-bit result and apply the
original eight-bit multiplier's sign, held in C. This handles -32768 and
-128 without truncation, a signed-word magnitude conversion or sign RAM.

The original loop costs 39 T for a zero bit, or 56/57 T for a set bit
depending on carry. The A:HL loop costs **27/40 T**. Selected leading-zero
probes cost **11 T** each; first-one detection and transfer cost **34 T**.
For nonzero signed multiplier a, let b=bit_length(abs(a)), p=popcount(abs(a)):

`T = (176 if a<0 else 112) + 4 + 11*(8-b) + 34 + 27*(b-1) + 13*(p-1) - (word<0)`.

This includes sign handling and RET, excludes caller CALL. Zero a remains
41 T. The negative word path is one T shorter because untaken JR plus SUB
replaces a taken JR. The saved [domain check](s8-domain-checks.json) executes
every signed word for nine byte multipliers (-128,-127,-65,-1,0,1,65,97,127):
**589824 exact products**, every measured count matching this formula.
The pre-existing 12048-pair test spans every signed byte and edge words,
plus random pairs. Its timing range improves from **41..664 to 41..465 T**.

## Selection and scope

Selected total falls **122581276 T (5.6625%)** from round16. First-frame
audit: 1677749 -> **1631519 T**, delta -46230, with every instruction checked.
LPC and synthesis/preparation totals remain exactly 317769021 and 1130838416
T: the saving is in excitation and its innovation preparation. Code is
**6947 bytes** (+10), state 1041, reserved stack 256. Table payload remains
16010 useful bytes in the 16384-byte arena; no additional lookup RAM.

All **1074400 PCM16/PCM8 samples** pass: speech, six signal fixtures, complete
six-bank capacity and 512 random valid mode-3 packets. General arithmetic,
excitation/innovation tables, coefficient tables/products, cache changes,
input controls, write guards, stack preservation and first-frame/cached
silence audits pass. A fresh default rebuild matches the selected image.

Set `pure-r18-signed` as the exact default. Output is unpaced, storage stays
23360 bytes / 8:1 versus PCM8, and the waveform is unchanged. The average
budget is still exceeded **24.978x**: 23.36 seconds of speech needs 583.49
nominal CPU seconds. The active goal is not achieved; ULA, disk and physical
hardware remain outside this throughput measurement.

Reproduce the selected result with `build.py --skip-host`,
`check_round.py --variant pure-r18-signed`, `check_s8_combined.py`, and
`check_unpaced.py --variant pure-r18-signed --previous pure-r16 --check-default`.
Archive with `report_round.py --variant pure-r18-signed --previous pure-r16 --round 18`.
The other build variant names in the table reproduce the superseded cores;
their saved bounded checks call `check_round.specialized`, `check_primitives.audit`
and the complete `verify.native` speech run. [Report](report.json),
[full checks](checks.json), [unpaced checks](unpaced-checks.json),
[transform](../../followup_opt.py), [domain checker](../../check_s8_combined.py).
