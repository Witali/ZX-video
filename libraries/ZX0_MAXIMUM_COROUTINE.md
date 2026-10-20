# Same-quota ZX0 maximum coroutine

Completed 2026-10-20 from the resident maximum checkpoint `6759dedf`.
`zx0.maximum_coroutine.build()` and CLI `--variant maximum-coroutine` add an
ordinary complete-input coroutine to the phased Maximum core. The comparison
is the same-feature original Fast coroutine from `f5a0362c`, including every
256-byte demand and every actual return cursor, rather than the raw-only Fast
baseline. Best real gain is **8.086252%**. The broad approximately 10% goal
remains unachieved; this bounded profile is complete.

## CPU and caller contract

This optional profile explicitly requires the Spectrum Z80's undocumented
`CP IXH` / `CP IXL` register-half forms, each two bytes/eight T. It does not
change any existing documented-opcode profile. Qualification for other CPU
clones is separate. The generated assembly states this contract prominently.
The native unit proof checks full flags/A/IX against ordinary immediate CP
in 2,560 accumulator/operand/opcode comparisons and proves eight T per CP.

Set `input_pointer`, `block_end` and `slice_target`; CALL `begin`, then
`slice_until` with nonwrapping monotonic targets. Input and initialized history
must remain resident. Code/state are writable and non-reentrant. The caller
may overwrite working and alternate registers between returns. Each decoding entry
saves caller IX in state and installs the quota in IX; every yield/finish
restores that entry's original IX and caller SP. IX/IY and alternate BC/DE/HL
are preserved at returns; AF/AF'/BC/DE/HL remain caller-clobberable. IRQ must
preserve all live decoder registers, including IX and AF'.

Twelve phase checks precede four literal, four repeated-offset and four
new-offset command preparations. The last group follows raw EOF detection;
checks never split a copy or precede a partial LDI prefix. EX AF,AF' parks the
full live reservoir/flags during comparisons and restores it before gamma
preparation or suspension. Return PC plus saved AF/BC/DE/HL encode the pending
phase. A final target is normalized to FFFF internally so the decoder reaches
raw EOF after producing the last byte. The real caller target is unchanged.

Early preparation means the private saved source/count can differ from Fast
at suspension. Those are internal continuation details: the public
`input_pointer` word remains the configured start in both profiles, and every
published output cursor and EOF completion state matches Fast exactly. The
ordinary contract requires complete input; no partial-input producer/paging
feature is omitted from this comparison or newly advertised.

## Complete real CPU and service memory

All 364 original real blocks, unchanged compressed bytes and all demand targets
are retained. Real Fast coroutine costs 180,610,040 T; original Fast resident
156,012,520 T and raw Maximum 140,193,198 T are separate reference measurements.

| Prefix cap | Code/wrapper/state bytes | Required total service | With 13-byte IRQ /6-byte headroom in each stack | Real coroutine T | Gain vs Fast coroutine |
| --- | ---: | ---: | ---: | ---: | ---: |
| 31 | 4,885 | 4,901 | 4,926 | 167,431,057 | 7.296927% |
| 63 | 6,421 | 6,437 | 6,462 | 166,492,817 | 7.816411% |
| 127 default | 7,957 | 7,973 | 7,998 | 166,005,457 | 8.086252% |

Every complete main case improves versus Fast. On 417 real/directed/random
cases, totals are 173,123,225 /172,109,785 /171,530,905 T versus 186,463,469 T.
Out of 12,542 slices,32/18/12 are slower at caps 31/63/127, maxima 348/188/71 T;
9/6/2 of those are real slices. Best cap 127's real regressions are
`real-1-112`, slice 1 +21 T, and `real-3-56`, slice 28 +71 T. The authenticated
summary lists every slower main slice. These differences are retained even
though all complete cases improve.

Another 56 directed cases per cap cover match counts 127/128/255/256/257 and
32767/32768/49151, using disjoint relocated input/code/output/stacks. All
complete cases improve; cap 127 has no slower high-word slice. Caps 31/63 have
16/6 slower high-word slices, maximum 427/267 T. Every tested return cursor
and completion state matches Fast across both suites, IRQ and relocation.

The complete service cap includes all hot/cold/state regions, embedded offset
and 20 state bytes already in the emitted totals, required caller stack 4 and
private stack 12. Its maximum is 2 bytes for the finish return, 2 for the yield
CALL return, and 8 for saved AF/BC/DE/HL: 12 bytes. A live match source PUSH
needs only 4 including the finish return. Caller `CALL sync` peaks at 4 including its own return. Native
peaks are exactly 4/12 plain and 10/18 with the 13-byte preserving IRQ, whose
hardware return plus two PUSHes adds 6. Tables, alignment padding, scratch and
internal buffers are zero; external input/output/history are excluded as
authorized. Unused placement gaps are reusable and are not required padding.
The 128-byte test stack margins are separate testing choices, not intrinsic
service costs. The builder adds actual declared IRQ code and headroom in
both stacks, and rejects totals exceeding 10,000 bytes or overlapping code
and declared private stack. The stronger 21-byte IX-clobbering test IRQ adds
8 bytes per stack; cap 127 then uses 8,010 service bytes.

## Exact changed-path timing

The raw cap 127 core is unchanged apart from inserted checks. Raw Maximum
still measures 140,193,198 real T. Every added wrapper/check instruction is
independently observed on the native core:25,812,259 real T, yielding exactly
166,005,457 T. All 1,419 main/high-word profile comparisons satisfy
`coroutine T = raw Maximum T + sum(actual added instruction costs)`.
This proves the whole changed instruction stream, rather than estimating
gain from the number of LDI instructions.

Use the repository Z80 timing table: EX AF/EXX=4 T; CP IXH/IXL=8; immediate
CP=7; LD IX,(nn) /LD (nn),IX=20; PUSH=11; POP=10; CALL=17; RET=10;
conditional RET=5/11; conditional JP=10; conditional JR=7/12.
[Zilog UM0080](https://www.zilog.com/docs/z 80/um 0080.pdf) documents the ordinary
forms; the explicitly undocumented IX-half forms are separately cross-checked
against the pinned `z80==1.2.0` implementation and flags/timing test.

| Path | Original Fast T | Selected IX profile T | Difference |
| --- | ---: | ---: | ---: |
| Available high-byte quota comparison | 29 | 30 | +1 |
| Available equal-high/low-byte comparison | 57 | 59 | +2 |
| Sync helper, ordinary/final target | 112 /112 | 97 /102 | -15 /-10 |
| Begin through jump to raw core, ordinary/final | 216 /216 | 258 /263 | +42 /+47 |
| Demand through restored continuation, ordinary/final | 279 /279 | 304 /309 | +25 /+30 |
| Repeated ready demand return, ordinary/final | 195 /195 | 180 /185 | -15 /-10 |
| Yield helper, including RET | 114 | 134 | +20 |
| Finish helper after raw EOF return | 95 | 135 | +40 |

Raw Maximum's phased gamma/copy gains pay for these whole-coroutine costs.
The raw-only 10.139777% Fast advantage is not a coroutine result. The chosen
ordinary profile gains 8.086252% against its own same-feature Fast baseline.
CPU counts exclude IRQ service, WAIT, ULA contention, physical disk and ROM.

## Bounded alternatives and verification

The first 12-site immediate-patch version uses 8,019 service bytes and gives
168,105,346 real T (6.923588%);24 target stores per request increase sync
work. It slows 16 directed complete cases and 616 slices, maximum +308 T.
The alternate-DE experiment saves/restores caller DE' and uses EXX around
CP D/E:8,005 service bytes,168,919,725 real T (6.472683%), zero slower complete
cases but 21 slower slices, maximum +99 T. The final saved/restored IX version
is smaller and faster in aggregate, retaining these earlier complete results
as archived evidence and private diagnostic builders. No further alternative
was opened in this milestone.

[Authentication and every slower slice](evidence/maximum_coroutine_verification.json)
bind 1,251 main and 168 high-word comparisons, each with IRQ and relocation,
per-op delta proofs,35 passing library tests,31 exact default profiles and
six exact upstream resources. Raw Maximum caps 31/63/127 remain byte-exact.
An additional full 417-case pass compares 25,918 zero/repeated/final demands,
injecting 196,814 forced and 1,560 periodic IRQs, including all 12 phase comparisons. That handler temporarily
clobbers and restores IX; every caller pair, output cursor and EOF state is
checked on every return. Another 1,251 comparisons place input at its host-proved
minimum safe in-place start for all 417 cases and all three caps; every output
cursor/EOF state stays exact and no unread input byte is overwritten.
Isolated installed wheel/API/CLI/ORG-DB exports pass
for all three caps, without converter or other-library imports.

Reproduction uses Python with z 80==1.2.0, package/test/toolkit import paths
and TMP/TEMP inside the task worktree:

```powershell
python libraries/tests/screen_maximum_coroutine.py --modes patched alternate --output .tmp/maximum-coroutine-quota-screen.json
python libraries/tests/screen_maximum_coroutine.py --modes index --output .tmp/maximum-coroutine-index-screen.json
python libraries/tests/measure_maximum_coroutine.py --output .tmp/maximum-coroutine-native.json
python libraries/tests/measure_maximum_coroutine.py --high-word --output .tmp/maximum-coroutine-high-word.json
python libraries/tests/measure_maximum_coroutine_demands.py --output .tmp/maximum-coroutine-demands.json
python -m unittest discover -s libraries/tests -v *> .tmp/maximum-coroutine-unit.log
python -m pip wheel --no-index --no-deps --no-build-isolation --wheel-dir .tmp/maximum-coroutine-wheel libraries/zx0
python -m pip install --no-deps --no-index --target .tmp/maximum-coroutine-installed .tmp/maximum-coroutine-wheel/zxvideo_zx0-0.1.0-py3-none-any.whl
python -I libraries/tests/smoke_maximum_coroutine.py .tmp/maximum-coroutine-installed .tmp/maximum-coroutine-wheel-installed
python libraries/tests/verify_maximum_coroutine.py --directory .tmp --output libraries/evidence/maximum_coroutine_verification.json
```

Keep command logs at the names used by the verifier. Full JSONs and rejected
screens are stored losslessly in `evidence/maximum_coroutine/*.gz`. No
physical CPU-clone, disk/ROM/ULA, AY or movie-publication qualification is
claimed. Existing formats, data, defaults and released player code stay exact.
