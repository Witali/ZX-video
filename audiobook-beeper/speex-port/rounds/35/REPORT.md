# Round 35: retain table steps in registers and use aligned addresses

2026-10-04. Continue from round34 on unchanged complete mode-3 speech.
The first three coefficient-table groups saved their positive 16*step to
RAM while the reverse recurrence used its negated step in DE/DE'. Keep
that saved value in the otherwise unused BC/BC' registers, then copy it
back to DE/DE' before the next group. All loops are unrolled, so BC/BC'
are available throughout the recurrence and PUSH writer.

Also use the existing page alignment of coef_out (7200..7B00) when setting
the temporary SP. Groups 0..2 end at offsets 64/128/192: set L directly.
Group 3 ends at the next page: increment H. The subsequent ADD/XOR sequence
initializes flags before their arithmetic use. IRQ stays disabled while
SP points into the table, and the real stack is restored as before.

## Contracts and cost accounting

The builder already documents both ordinary and alternate AF/BC/DE/HL as
clobbered. BC/BC' now hold the saved step instead of incidental prior values;
callers do not depend on those scratch outputs. The four-byte coef_step
allocation remains in place but has no instruction reference. Its value
is no longer updated. All other state, table contents, input, IX/IY and
caller SP retain their prior behavior. The generated filter/caller unit
is unchanged; it restores its saved input cursor after preparation.

| Changed work | Before | After | Saving per page |
| --- | ---: | ---: | ---: |
| Save/reload 16*step, three groups | (40+48)*3 T | (24+24)*3 T | 120 T |
| Group-end address, groups 0..2 | 43*3 T | 29*3 T | 42 T |
| Group-end address, group 3 | 43 T | 26 T | 17 T |
| Total | | | **179 T** |

A warm call changing page zero normally costs **7852 -> 7673 T**; the
first coefficient-domain case costs **7898 -> 7719 T**. Cached calls stay
**976 T**. The complete ten-page instruction audit costs **51493 -> 49703
T**, a 1790-T saving. It executes 5946 -> 6026 instructions: additional
short register copies replace slower memory operations. Every instruction
matches the Z80 timing table; all 640 generated entries remain exact.

Reuse the authenticated round34 coefficient trace. All 4672 arrays match,
with exactly 44692 changed pages. Measured preparation and complete savings
are both **44692*179 = 7999868 T**. Every OUT advances by exactly 179 times
the cumulative number of changed pages before that sample. Profiling also
preserves every uninstrumented OUT timestamp.

| Measurement | Round34 | Selected round35 |
| --- | ---: | ---: |
| Preparation T | 231223829 | 223223961 |
| Complete speech T | 1596096910 | 1588097042 |
| T/sample | 8540.7583 | 8497.9508 |
| First complete frame T | 1071160 | 1067580 |
| Code bytes | 8918 | 8891 |

Select the **0.5012% complete CPU saving**, with **3.4598% less preparation
CPU**. The **below-8500 T/sample intermediate target is achieved** on the
unchanged 186880-sample speech: 382958 T below its 1588480000-T threshold.
This input-specific milestone does not establish real-time Speex.

All other full fixtures improve: silence -3580 T, impulses -82340 T,
low tone -10740 T, high tone -50657 T, noise -137472 T, level jumps -60860 T,
six-bank capacity -3580 T, random packets -3658044 T and all-pitch input
-903055 T. The first build stopped on a host-generator string quoting
error; it was corrected before a candidate binary was produced. No native
arithmetic/timing failure or reverted candidate occurred. Adding test labels
later preserved the already measured binary identity.

## Verification and memory

- Every signed16 coefficient on both binaries: **65536 coefficients and
  4194304 exact entries per variant**, exact 179-T page saving, protected
  other pages, preserved SP/IX/IY and unchanged 976-T cached path.
- **10240 isolated address cases**: all ten pages, four group ends and 256
  initial flag values. Check exact HL/SP, unaffected registers, 29/26-T
  costs and forbidden writes; independently step all 30720 instructions.
- **1024 changed-page masks** plus 1024 cached repeats per variant. Check
  every table byte, input, all remaining BSS and register outputs outside
  the documented BC/BC' scratch. The retired four-byte step slot contains
  a nonzero sentinel and is write-protected. Every unchanged table page is
  protected; cached repeats forbid every table write. IX/IY/SP remain exact.
- Standard **1074400** plus all-pitch **20480 complete PCM16/PCM8 samples**
  pass, totalling **1094880 exact samples**. Arithmetic/table/cache/control
  checks, full-frame and cached-silence instruction audits, protected
  playback memory and fresh default identity all pass.

Code is 8891 bytes at 8000..A2BA, 27 bytes smaller. State remains 1041
bytes at B000..B410 and stack reserve BF00..BFFF. Tables remain 16010 useful
bytes within a 16384-byte arena; code/state/input require additional RAM.
The compressed payload stays 23360 bytes, 8:1 against mono 8-kHz PCM8.
Playback code is immutable. Binary SHA-256:
`a6d815ca9865e5af50a84c51e348a2cbd0a6b1acea29e94326a41780c9f33538`.

23.36 seconds of audio needs 453.742 nominal CPU seconds, **19.4239x**
the 437.5-T/sample real-time budget. Output remains unpaced. ULA, disk and
physical hardware are unverified. The overall real-time goal remains active.

## Next candidate

Inspect the exact cosine helper, whose unchanged earlier full profile
records 30846551 T across 46720 calls. Its positive-half table uses 8050
packed bytes and accumulates nibble deltas to reach each value. Codebook
LSP values are multiples of sixteen and quarter interpolation suggests
many four-unit-aligned arguments, but **margin averaging can break that
alignment**. Observe actual argument residues and costs before assuming
an aligned-only path is sufficient.

Compare a direct exact table for common aligned angles with an exact
fallback for the rest only if measured call distribution supports a net
saving. Keep the complete 0..25736 helper domain exact; do not silently
round angles or weaken arbitrary mode-3 packet handling. Account for table
bytes and fallback cost together. This next candidate is unimplemented
and no speedup is claimed.

Reproduce with saved fixtures and round34 image/report/OUT/operand evidence:

```text
build.py --skip-host --variant pure-r35
verify.py --native-only --restore-fixture --variant pure-r35
check_next_table_step.py
check_round.py --variant pure-r35
check_unpaced.py --variant pure-r35 --previous pure-r34 --check-default
report_round.py --variant pure-r35 --previous pure-r34 --round 35
```

The completed check_round run used --skip-speech to reuse the already
verified speech run; all other full fixtures were executed normally.

[Measurements](report.json), [standard checks](checks.json),
[coefficient domains, address/mask audits and complete cost proof](next-step-checks.json),
[unpaced/default checks](unpaced-checks.json),
[reused coefficient arrays](../34/observed-lpc-coefficients.i16.gz),
[generator](../../followup_opt.py), [checker](../../check_next_table_step.py).
