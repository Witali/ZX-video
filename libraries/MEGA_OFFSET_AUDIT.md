# Optional ZX0 Mega offset-register tuning

2026-10-19, source checkpoint `6db73511`. This is a separately scoped native
experiment. The optional public `mega_tuned=True` on `zx0.block.build('mega')`,
or `--mega-tuned` with `--variant mega`, enables the combined result. An
independent test-only builder remains its byte/address/label oracle. Defaults,
upstream assembly resources and compressed bytes stay exact. This profile
uses the resident Mega ABI; there is no equivalent coroutine/quota wrapper.

## Dead offset-word shifts

Each of the four phase-specific `dzx0m_elias_offset` loops executes `RL B`.
That B value is dead: the subsequent offset consumer executes `LD B,C` before
reading B, and the intervening `ADD A,A` replaces the shift's flags. The one
phase variant that refills A first uses `LD A,(HL)` and `INC HL` before that
ADD, neither of which consumes the shift's carry. Even on EOF, `INC C` sets
the decision flags and the caller ABI permits BC to be clobbered. Retain all
`RL B` instructions in the length/literal/reuse Elias loops, where B is the
necessary high count byte. This transformation places no new bound on lengths
or offsets and does not reject length-one repeated matches.

Removing the four instructions saves eight code bytes and 8 T per executed
offset-gamma iteration. With Zilog's ordinary CPU timings, a phase body
without a refill costs 34 ->26 T; the refilling body costs 47 ->39 T. Both
include the final 10-T JP NC. The independent native observer counts 76,838
real iterations, giving exactly -614,704 T. IRQ service, contention, WAIT,
ROM, physical disk latency and publication timing are outside these totals.

## Independent reuse-exit branch candidate

The full retained branch profile also identifies four reuse exits to literal
parsing where JP improves the aggregate over JR NC. JP costs 10 T versus
JR's 7 untaken /12 taken: -2 T per taken exit, +3 T per untaken exit, and one
extra byte per site. This branch change is independently measured; it has
32 slower cases, including 31 real blocks, with a largest +156 T. Do not
describe it as universally faster. The combined candidate saves enough from
dead shifts to improve every complete case, while that individual exit path
still has its +3-T alternative.

## Complete native evidence

The baseline is the existing 673-byte Mega plus its previously implemented
startup `fast_jumps` option: 674 bytes and 146,421,546 real CPU T-states.
That older Mega advantage is already established; it is not a new gain from
this experiment. All 417 frozen cases (364 real, directed and seeded random)
use unchanged bytes. Each of three candidates also runs relocated to 9103h
and with register-preserving IM1 interrupts. Protected resident replay checks
sequential input, exact EOF, initialized overlapping history, sequential
output, patched-code permissions, caller SP/IX/alternate registers and stack
limits. Per-case executed loop/branch counts independently predict every
measured CPU difference. There are 1,251 complete candidate comparisons and
4,170 native runs including one shared baseline per case.

| Candidate | Real CPU T | Difference from existing Mega | Bytes | Slower complete cases |
| --- | ---: | ---: | ---: | ---: |
| Remove dead offset shifts | 145,806,842 | -614,704 (-0.419818%) | 666 | 0 |
| Four reuse exits as JP | 146,315,999 | -105,547 (-0.072084%) | 678 | 32 (31 real) |
| Combine both | 145,701,295 | -720,251 (-0.491902%) | 670 | 0 |

All-case baseline 151,878,711 T becomes 151,258,695 /151,773,165 /151,153,149 T
respectively. Every candidate retains four-byte maximum caller-stack use in
plain execution. Code size includes all emitted bytes, with no table, hidden
padding, state, new buffers or changed input-sector requirement. The combined
raw total is 6.609229% below the f5a0362c Fast total, but most of that is the
old Mega implementation at more than three times Fast's code size. Only the
0.491902% reduction versus existing Mega belongs to this experiment. It
cannot complete the approximately 10%-per-library goal, and lacks a matching
coroutine implementation. The user subsequently requested a separate
faster-and-smaller profile, authorizing promotion of the combined candidate
as the optional resident API/CLI mode. Without `fast_jumps`, code is669 versus
673 bytes with the same improvement apart from the shared startup. All31
defaults/six upstream resources remain exact;28library tests and the isolated
ZX0 wheel/API/CLI exports pass. No player/movie qualification is claimed.

## Complete service-memory accounting

The user caps service memory at10,000bytes, counting input/output/history
separately. With both options, code is670bytes, including the mutable two-byte
previous-offset operand. There are no extra variables, tables, alignment
padding, private stack reservation, scratch area or internal buffers. The
maximum decoder stack is4bytes including the caller's2-byte return address:
the complete Mega has no CALL and only one live PUSH HL per match. Hence this
bound holds for all legal lengths, phases and offsets, beyond the tested
corpus. Total service memory is674bytes (673withoutfast_jumps), within10,000.

Interrupt headroom depends on the caller's handler. The harness's
AF/AF'-preserving IM1 handler needs6additional stack bytes (hardware PC push
plus two saved AF pairs), giving10bytes including caller return and live
PUSH HL. Its13instruction bytes belong to the caller's IRQ implementation;
count them too if choosing that handler. This would require693service bytes
for the670-byte profile plus10stack plus13handler bytes. Other handlers must
reserve and count their own code, variables and stack; this is not a universal
IRQ memory bound. Input/history must remain resident through the complete
call. Separate input/output allocations require at most6,209/8,192bytes for
the real corpus and15,878/15,872bytes across all directed cases. A validated
in-place layout may share them; do not silently count that as zero data RAM.

## Reproduction

Install the existing native test dependency, set `PYTHONPATH` accordingly,
and use a writable local TMP/TEMP. Run:

```powershell
python libraries/tests/measure_mega_offset.py --output libraries/evidence/ten_percent_mega_offset.json
python -m unittest discover -s libraries/tests -v
python -m pip wheel --no-deps --no-build-isolation --wheel-dir .tmp/mega-wheels libraries/zx0
python -m pip install --no-index --no-deps --target .tmp/mega-installed .tmp/mega-wheels/zxvideo_zx0-0.1.0-py3-none-any.whl
python -I libraries/tests/smoke_install.py .tmp/mega-installed zx0 .tmp/mega-smoke
python libraries/tests/verify_mega_offset.py --output libraries/evidence/ten_percent_mega_offset_verification.json
```

Save the unit log as `.tmp/mega-offset-unit.log` for the verification command.
The baseline parser is asserted byte/address/label identical to the public
Mega generator before substitutions. [Test-only builder](tests/mega_offset_profile.py),
[complete per-case evidence](evidence/ten_percent_mega_offset.json),
[source/input/test authentication](evidence/ten_percent_mega_offset_verification.json).

Example: `python -m zx0 build --variant mega --mega-tuned --fast-jumps
--core 0x8000 --core-limit 0x8400 --output build/zx0-mega-tuned`.
HL=input, DE=output; AF/BC/DE/HL clobbered, IX/alternate registers retained.
Use writable code, nonwrapping output, complete input/history and the caller
stack; validate external sizes and placement before calling.
