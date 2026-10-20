# LZSA2 smaller conditional branch policy

Completed 2026-10-20 from `bb687f71`, continuing the interrupted 2026-10-19
experiment. The broader goal remains approximately another 10% per library
against `f5a0362c`, with identical data and features. This is a small optional
faster-and-smaller result; it does not achieve that goal.

`lzsa.block.build(compact_branches=True)` and
`lzsa.resumable.build(compact_branches=True)` shorten only
`JP NC,Case11x` to `JR NC,Case11x`. CLI: `--compact-branches`. The former
`branch_tuned` policy still shortens this site and lengthens its two measured
other sites, with its previous bytes frozen exactly. Selecting both policies
raises `ValueError` / a CLI error. Small rejects the new option. All applicable
long-copy, near-literal, nibble, quota and guarded-input features compose;
their existing validation still applies.

The changed site follows `CP 192`: carry selects the 10x offset path;
noncarry selects the 11x path. The same condition and flags are retained.
[Zilog UM0080](https://www.zilog.com/docs/z80/um0080.pdf) counts conditional
JP as three bytes/10 T in either direction, JR as two bytes/7 T untaken or
12 T taken. The complete dispatch `CP 192; branch` is therefore 17 T before,
14 T untaken (-3) or 19 T taken (+2) after. No memory access, register or stack
operation is added. The frozen real frequency report records 6,192 taken and
17,608 untaken executions: 238,000 ->197,560 T, exactly -40,440 T. Per-call
assembler instances check relative reach and preserve the overflow fallback.

## Complete native results

The [native report](evidence/compact_branches_native.json) covers eight
profiles, 95 existing real/directed/random blocks and both single-nibble EOF
forms: 776 comparisons. Every candidate also runs relocated at 9103h and
with preserving IM1 interrupts. Protected input/history/output, exact input
EOF, pending registers and output cursors remain correct. Each profile uses
identical payloads, external input/output/history and enabled features.

| Profile | Real baseline T | Compact T | Emitted bytes before -> after |
| --- | ---: | ---: | ---: |
| Resident Fast | 17,767,606 | 17,727,166 | 218 ->217 |
| Resident +fast_jumps, matching goal baseline | 17,765,094 | 17,724,654 | 219 ->218 |
| Resident +nibble_prefill | 17,686,110 | 17,645,670 | 223 ->222 |
| Same +long_copy, near_literals | 17,660,394 | 17,619,954 | 307 ->306 |
| Ordinary Fast coroutine | 19,412,006 | 19,371,566 | 384 ->383 |
| Coroutine +fast_jumps, matching goal baseline | 19,407,004 | 19,366,564 | 386 ->385 |
| Coroutine +nibble_prefill, compact_sync | 19,292,992 | 19,252,552 | 385 ->384 |
| Same +long_copy, near_literals, restore_compare | 19,267,276 | 19,226,836 | 469 ->468 |

All 21 real blocks improve. Against the Fast+jumps goal baseline, resident
gain is 0.227638%, coroutine 0.208378%. All 97 cases together save 40,927 T
per profile. Seventeen directed blocks per profile are slower, maximum +4 T;
their names and deltas are saved in the verification report. Each ordinary
coroutine profile has 124 slower slices, maximum +23 T. The token publication
cursors remain identical; branch savings can be distributed unevenly among
slices. No slower result is omitted from the frontier claim.

The existing tuned policy is still 10,170 real T faster while taking two
more bytes. For example, the nibble-prefilled resident alternatives are
17,635,500 T /224 bytes tuned versus 17,645,670 T /222 bytes compact.
These are separate choices on the size/CPU frontier, not a replacement for
the stronger tuned result.

Both guarded CALL/direct modes pass 63 complete producer cases at six
placements. Actual deterministic producer+decoder totals are
29,502,408 ->29,461,998 T and 27,285,937 ->27,245,527 T: -40,410 each.
Producer work, input waits, carry copies and all 772 once-only sectors stay
exact. Each mode has 164 slower slices out of 2,670, maximum +23 T. The
strongest applicable guarded copy/init/nibble/sync combinations
also pass 65 cases at six placements per mode, including both tiny EOFs and
IRQ replay at offset 253. Each combined mode has 102 slower placements,
maximum +4 T. The detailed report retains guarded slice regressions.

## Complete service memory

Emitted byte counts include state and self-modified operands. Plain required
stacks include return addresses: resident caller 4; ordinary caller/private
4/14; guarded 4/20 bytes. The guarded private maximum is the finish return
2 + guard_literals return 2 + input_wait return 2 + saved AF 2 + yield return
2 + saved AF/AF'/BC/DE/HL 10 =20 bytes. Saved literal AF/HL are popped before
input_wait. Direct header waits are shallower; literal waits retain the same
maximum. Caller `CALL sync` accounts for its four bytes. Observed ordinary
peaks are 4/14, IRQ peaks 10/20; resident peaks 4/10. The benchmark's IM1 stub
uses 13 code bytes and adds six bytes to whichever stack is active. Reserving
that headroom separately in both coroutine stacks gives the IRQ totals below.

| Service | Plain required bytes | With benchmark IRQ bytes |
| --- | ---: | ---: |
| Resident compact default | 221 | 240 |
| Largest tested resident compact combination | 310 | 329 |
| Ordinary compact default | 401 | 426 |
| Largest tested ordinary compact combination | 486 | 511 |
| Guarded CALL copy combination, including patcher and carry | 900 | 925 |
| Guarded direct copy combination, including patcher and carry | 892 | 917 |

Guarded components include the standalone final-input patcher with RET
(57/54 bytes CALL/direct) and the reference supplier's required 256-byte
shared-sector carry scratch, rather than hiding it as external input.
There are no tables, required alignment gaps or other internal buffers.
The test harness reserves 128 bytes for each caller/private stack as a
testing margin; these are explicitly separate from required stack space.
External input, output and match history are excluded as the user specified.

The report separately inventories the reference sector producer, disk
adapter/state, cached seek and full generated video/paging/state: 1,069/1,066
bytes CALL/direct, including its embedded guard patcher. Composing that code
with the strongest consumer, carry, 10-byte main /20-byte disk /20-byte
private stack bounds, two-byte elapsed counter, two-byte IRQ-vector word
and a conservative configured 258-byte mock-ROM workspace arena gives
2,200/2,192 bytes, or 2,231/2,223 with the benchmark IRQ stub and headroom in
all three stacks. The standalone patcher is removed when counting its embedded
replacement. All are below 10,000 total service bytes. The ROM body is mocked:
this inventories the actual reference configuration and does not establish
physical TR-DOS workspace or ROM stack requirements for a movie player.

## Verification and reproduction

[Authenticated summary and archives](evidence/compact_branches_verification.json)
bind source hashes, full native/guarded runs, all 36 library tests, isolated
installed LZSA wheel/API/CLI/ORG-DB round trips, 31 frozen default layouts and
six exact upstream resources. No default instructions or payload bytes change.
The interrupted 2026-10-19 native/six-profile and four guarded reports are
preserved under `evidence/compact_branches/interrupted-2026-10-19`, with their
original dates. Their implementation had not yet been committed or fully
packaged; the dated 2026-10-20 proof supersedes them without deleting them.

Use Python with z80==1.2.0 and the package, library-test and toolkit paths;
set TMP/TEMP to a private worktree directory. Existing prepared real fixtures
are unchanged. Complete commands:

```powershell
python -m unittest discover -s libraries/tests -v *> .tmp/compact-branches-library-tests.log
python libraries/tests/measure_compact_branches.py --output libraries/evidence/compact_branches_native.json
# Recover video.stream/video.raw from toolkit/row_lzsa_evidence/*.gz, as for compact_sync.
python toolkit/test_streaming_lzsa2.py --noncanonical --stream .tmp/video.stream --raw .tmp/video.raw --fast-jumps --nibble-prefill --compact-sync --output .tmp/compact-branches-call-before.json
python toolkit/test_streaming_lzsa2.py --noncanonical --stream .tmp/video.stream --raw .tmp/video.raw --fast-jumps --nibble-prefill --compact-sync --compact-branches --output .tmp/compact-branches-call-after.json
# Repeat both commands with --direct-header and direct-before/direct-after output names.
python libraries/tests/measure_compact_branches_streaming.py --output .tmp/compact-branches-combinations.json
python -m pip wheel --no-deps --no-build-isolation --wheel-dir .tmp/compact-branches-wheel libraries/lzsa
python -m pip install --no-deps --no-index --target .tmp/compact-branches-installed .tmp/compact-branches-wheel/zxvideo_lzsa-0.1.0-py3-none-any.whl
python -I libraries/tests/smoke_compact_branches.py .tmp/compact-branches-installed .tmp/compact-branches-wheel-installed
python libraries/tests/summarize_compact_branches.py --directory .tmp --output libraries/evidence/compact_branches_verification.json
```

These are full flat CPU tests; they exclude ROM execution, physical disk
latency, ULA contention, AY and actual movie frame publication. This optional
library result does not qualify a player/movie release or achieve the broad
speed goal.
