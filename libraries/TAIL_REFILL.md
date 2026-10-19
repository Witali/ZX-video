# Optional ZX0 repeated-match tail refill

2026-10-19, source baseline `674a1fc8`, goal baseline `f5a0362c`.
The Fast decoder's rare repeated-match gamma path reaches an empty bit
reservoir after the inline gamma loop. Its existing adaptation calls
`ReloadReadGamma`, returns, and jumps to the known `CopyMatch1` continuation.
The optional `inline_tail_refill=True` / `--inline-tail-refill` replaces this
tail with a local refill and `CALL NC ReadGammaAligned` before that same jump.
The refill consumes the same byte. The aligned reader, partial BC count,
reservoir A/carry, next-input HL, output DE and copy boundaries stay exact.
Only Fast resident/coroutine profiles accept the option. It combines with
`branch_tuned`; defaults and upstream assembly resources remain unchanged.

## Instruction counts

Counts use [Zilog UM0080](https://www.zilog.com/docs/z80/um0080.pdf), excluding
IRQ service, contention, WAIT, paging, ROM and disk latency. Endpoints are the
old tail CALL / new local refill through entry to `CopyMatch1`.

| Refilled stop bit | Before | Candidate | Difference |
| --- | ---: | ---: | ---: |
| 1: immediate gamma termination | 55 T | 37 T | -18 T |
| 0: aligned reader required | 49 T + G | 44 T + G | -5 T |

`G` is the unchanged aligned-reader execution including its RET. Before:
CALL 17; LD A,(HL) 7; INC HL 6; RLA 4; RET C 11/5; JP 10, plus G on clear
carry. Candidate: LD A,(HL) 7; INC HL 6; RLA 4; CALL NC 10/17; JP 10, plus G
on clear carry. Both sequences preserve the same live flags on continuation.
The local sequence costs three more bytes. No state, input, output buffer or
stack reservation grows; the immediate-termination path removes one temporary
return address. Unexhausted-reservoir repeats retain their old instructions.

## Complete native result

The frozen 417-case corpus contains all 364 real blocks (2,965,011 output
bytes), directed lengths/offsets and seeded random blocks. Four complete
comparisons cover resident and 256-byte-demand coroutine profiles with and
without branch tuning. Every candidate additionally runs at 9103h and with
register-preserving IM1 interrupts. Protected resident replay checks exact
input consumption, sequential output/history, EOF and caller ABI. Coroutine
replay clobbers working registers between demands and checks complete output,
caller stack, unchanged slice counts and every slice CPU difference.

| Profile, real corpus | Before | Candidate | Difference | Total region bytes |
| --- | ---: | ---: | ---: | ---: |
| Fast resident | 156,012,520 | 155,652,557 | -359,963 (-0.230727%) | 207 ->210 |
| Fast coroutine | 180,610,040 | 180,250,077 | -359,963 (-0.199304%) | 401 ->404 |
| Branch-tuned Fast resident | 153,706,279 | 153,346,316 | -359,963 (-0.234189%) | 193 ->196 |
| Branch-tuned Fast coroutine | 178,657,995 | 178,298,032 | -359,963 (-0.201482%) | 388 ->391 |

All 417 cases save 359,968 T per profile; no block or slice is slower.
Resident execution watches all 29,611 tail refills (13,310 clear /16,301 set
stop bits); their independently predicted -5/-18 T sum equals every native
case delta. The real corpus contains 29,610 of these refills. Resident maximum
stack use never increases. All 31 default profiles and six original resources
stay byte/address/label exact. The standalone ZX0 wheel exports the option
without converter imports; 27 library tests pass. The saved verification
explicitly does not claim a new toolkit/player/movie qualification.

The separately tracked existing Mega remains faster at 146,421,546 T real
(674 bytes with its startup fast jump). This small compatible improvement
does not achieve the active approximately 10%-per-library goal.

## Short-match audit

The investigation began with known-length-two copies. Two LDI instructions
cost 32 T versus LDIR's 37 T, but splitting the shared immediate-offset copy
body requires either a 10-T join or a 6-T slower `LD HL,(nn)` offset fetch.
Those variants lose even before any new dispatch or patch stores. This is an
instruction-count rejection, not a measured implementation or a broader proof
that all short-match designs fail. Keep length-one repeats legal and retain
the overlapping-history and arbitrary-word-length contracts.

## Reproduction

Set `PYTHONPATH` to the installed `lzsa[native]` dependency directory, and use
a writable local TMP/TEMP for tests and wheels.

```powershell
python libraries/tests/measure_tail_refill.py --output libraries/evidence/ten_percent_tail_refill.json
python -m unittest discover -s libraries/tests -v
python -m pip wheel --no-deps --no-build-isolation --wheel-dir .tmp/tail-wheels libraries/zx0
python -m pip install --no-index --no-deps --target .tmp/tail-installed .tmp/tail-wheels/zxvideo_zx0-0.1.0-py3-none-any.whl
python -I libraries/tests/smoke_install.py .tmp/tail-installed zx0 .tmp/tail-smoke
python libraries/tests/verify_tail_refill.py --output libraries/evidence/ten_percent_tail_refill_verification.json
```

CLI example: `python -m zx0 build --variant fast-block --branch-tuned
--inline-tail-refill --core 0x8000 --core-limit 0x8400 --output build/zx0-tail`.
Custom reservations must account for the extra three bytes. Generated assembly
documents the local refill's registers and algorithm.

[Per-case native evidence](evidence/ten_percent_tail_refill.json),
[source, wheel and test authentication](evidence/ten_percent_tail_refill_verification.json).
