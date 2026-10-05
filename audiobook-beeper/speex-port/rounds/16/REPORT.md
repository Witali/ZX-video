# Round 16: omit zero low bytes in exact partial products

2026-10-04. Baseline round15, same complete Speex mode-3 speech and reference.
The user permits consecutive port writes; assess total throughput without
adding delays or requiring uniform sample deadlines.

The coefficient products shifted left by eight and twelve bits always have
a zero low byte. Point their cached offsets at byte 1, leave E unchanged,
and start a fresh ADD at D before propagating carry through C and B. Using
OR 129/193 instead of 128/192 adds the address offset at no extra CPU cost.
ADD must replace ADC at D: carry from the previous partial's top byte is
discarded, while adding the skipped zero low byte cannot generate carry.
All ten coefficient taps, signed high-nibble behavior and 32-bit wrap remain exact.

Each omitted `LD A,E / ADD A,(HL) / LD E,A / INC L` costs 4+7+4+4 = **19 T**.
Two per product save **38 T**; the product call drops **306 -> 268 T**
including RET (caller CALL excluded). Splitting the sample still costs 159 T.
Ten products per sample save exactly **380 T/sample**, or **71014400 T**
for the full 186880-sample control. No setup or table-construction penalty.

Full decode costs **2164784952 T / 11583.8236 T/sample**, down from
2235799352 / 11963.8236. The two new exact rounds together save **13.7807%**
versus round09's 2510789186 T; output still requires **26.4773x** the average
real-time budget. 23.36 seconds of speech needs 618.51 nominal CPU seconds.
First-frame instruction audit: 1738549 -> **1677749 T**, delta -60800,
exactly 160*380. Ordinary minimum OUT interval drops 4986 -> 4606 T;
irregular intervals are recorded, but are not a failure gate for this goal.

All **1074400 PCM16/PCM8 samples** pass on the selected binary, covering full
speech, six signal fixtures, six-bank capacity and 512 random valid packets.
All 40960 coefficient entries, 12800 products, cache-page cases, general
arithmetic, excitation, input controls, memory guards and instruction audits
pass. Another 100 edge products record the 306/268-T costs explicitly.
The ten-page preparation audit remains exactly 59433 T. A fresh default
build reproduces the selected hash. `finish_followup.py` now explicitly
builds its historical round09 so that old evidence remains reproducible.

Select **pure-r16 as the exact default**. Code **6937 bytes** (-8 from
round15), state 1041, reserved stack 256, useful table payload 16010 in the
same 16-KiB arena. Compressed data remains 23360 bytes / **8:1 versus PCM8**.
No precision, format, sound or table-storage tradeoff. CPU timing excludes
ULA, disk and physical hardware. The active throughput goal remains unmet.

The complete phase profile is synthesis/preparation **6051.147 T/sample**,
LPC **1700.391**, remaining decoding **3832.286**. The next investigation
should split synthesis preparation/products and remaining excitation work
before choosing another optimization. Even a free LPC stage alone would
leave this implementation far over the 437.5-T budget.

Reproduce in order: `build.py --skip-host`,
`check_round.py --variant pure-r16`,
`check_unpaced.py --variant pure-r16 --previous pure-r15 --check-default`,
`report_round.py --variant pure-r16 --previous pure-r15 --round 16`.
Use saved speech/signal/random fixtures and the previous build.
[Report](report.json), [checks](checks.json), [unpaced checks](unpaced-checks.json),
[transform](../../followup_opt.py), [assembly](decoder.s).
