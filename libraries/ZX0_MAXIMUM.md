# Measured ZX0 maximum-speed direction and memory frontier

Completed 2026-10-20 from `1784e45a`, resuming the interrupted work in
`.worktree/codec-zx0-maxspeed`. The saved complete test-only prototype report
dated 2026-10-19 is retained. The new public replay independently reproduces
all 417 cases for each of three sizes. This is a bounded measured frontier,
not proof of a global optimum or completion of the per-library/coroutine goal.

Current update: the separately measured[shared word-prefix extension](ZX0_WORD_PREFIX.md)
adds caps227/228and makes228the maximum-direction default (9,990library
service bytes;9,995with its verified minimalIRQ). The original31/63/127audit
below and its committed reports remain historical evidence from`6759dedf`.

`zx0.maximum.build()` and CLI `--variant maximum` export the fastest of these
three candidates, with cap127as the original default at`6759dedf`. It retains the resident Fast caller contract:
HL=complete valid input, DE=nonwrapping output, caller stack; AF/BC/DE/HL
clobbered, IX and alternate registers preserved. Source and initialized
history remain resident. Code contains a writable previous-offset operand;
the routine is not reentrant. Validate sizes and placement externally.
There is no coroutine, paging, quota, yield or disk-reader implementation.

## Results and baseline provenance

All figures below are complete deterministic CPU T-states on the identical
364 real blocks. The strongest pre-existing baselines are tracked separately:
original Mega is 673 bytes /146,422,274 T; the already available startup
`fast_jumps=True` version is 674 bytes /146,421,546 T. The subsequently tuned
Mega (`mega_tuned=True`, `fast_jumps=True`, checkpoint `1784e45a`) is 670 bytes
/145,701,295 T. The main goal's original Fast is 207 bytes /156,012,520 T.
Do not attribute the old Mega advantage over Fast to this new transformation.

| Build-time prefix cap | Code bytes | Service bytes | With probe IRQ | Real CPU T | New gain over tuned Mega | Total gain over original Fast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 31 | 4,450 | 4,454 | 4,473 | 141,618,798 | 2.801963% | 9.226004% |
| 63 | 5,986 | 5,990 | 6,009 | 140,680,558 | 3.445911% | 9.827392% |
| 127 (original default) | 7,522 | 7,526 | 7,545 | 140,193,198 | 3.780404% | 10.139777% |

The largest profile saves 5,508,097 real T versus tuned Mega, and 6,229,076 T
(4.254186%) versus original unmodified Mega. All-case 417-block totals are
146,946,342 /145,932,902 /145,354,022 T versus tuned Mega's 151,153,149 T.
No complete case is slower than tuned Mega or original Fast. Individual
untaken changed conditional exits cost 3 T more, and the word-count join
costs 10 T; complete-case improvements do not imply every instruction path
improves. There are no coroutine slices to compare.

The 10.139777% Fast comparison includes the historical Mega benefit; the new
incremental gain is 3.780404%. This public resident direction crosses the
numeric Fast target on this corpus under the revised memory budget, while
the broader new 10%-per-library and coroutine work remains incomplete.

## Algorithm and instruction-table counts

The pinned Mega unrolls bit-reservoir phases. This generator further expands
length/literal/reuse Elias depth: after K is proved as a lower count bound,
copy P=min(prefix_cap,K-1) bytes using inline LDI, then join the original
positive-count LDIR tail. Leaving at least one byte avoids the BC=0 LDIR
underflow. Forward LDI preserves overlapping match semantics. Match clones
save source HL once, load the same patched negative offset and add DE before
copying; they use the original POP afterward. There are no runtime selectors.

The high byte B is known zero until the eighth count data bit. Omit RL B only
where the gamma depth proves its result stays zero; preserve the deeper word
loops. Offset dead-shift removal is already in the tuned-Mega baseline and
is not counted again. Expanded relative branches become JP; the baseline's
remaining JR C exits contribute -2 T taken /+3 T untaken.

Use Zilog's instruction table: LDI=16 T, repeating LDIR=21 T, final LDIR=16 T,
RL B=8 T, JP=10 T, JR C=7/12 T, LD HL,(nn)=16 T, LD HL,nn=10 T. For N>P,
the original copy is 21N-5 T; the new prefix/tail is 21N-5-5P+10 T.

| Guaranteed count /prefix | Original copy at minimum count | Prefix plus tail | Difference |
| --- | ---: | ---: | ---: |
| 4 /3 | 79 T | 74 T | -5 T |
| 8 /7 | 163 T | 138 T | -25 T |
| 32 /31 | 667 T | 522 T | -145 T |
| 64 /63 | 1,339 T | 1,034 T | -305 T |
| 128 /127 | 2,683 T | 2,058 T | -625 T |

Nonrefilling gamma body: 34 ->26 T (-8); refilling body: 47 ->39 T (-8).
Deeper word loops retain 34/47 T and a 10-T join on exit. Reuse phase seven
changes its immediate offset load into an indirect load, +6 T per prefix
entry. Every block's independent instruction observer proves exactly:

```text
delta = -8 * removed_word_shifts -5 * prefix_bytes +10 * prefix_entries
        +6 * phase7_indirect_loads +10 * word_joins
        -2 * changed_jr_taken +3 * changed_jr_not_taken
```

Across all 417 cases at cap127 the counts are respectively 102,686 shifts,
1,336,155 copied prefix bytes, 127,533 prefix entries, 7,063 indirect loads,
141 joins, 143,922 taken exits and 223,954 untaken exits: exactly -5,799,127 T.
Source: [Zilog UM008011 instruction descriptions](https://www.zilog.com/docs/z80/um0080.pdf#page=84),
cross-checked against the repository's saved timing table. These counts
exclude IRQ service, WAIT, ULA contention, ROM, paging and physical disk.
Compressed data and required input sectors are unchanged. A larger resident
routine may change application load/allocation; player adoption is unmeasured.

## Every service-memory byte

The hard cap is 10,000 bytes. The original cap127code is 7,522 bytes including its
two-byte mutable offset operand. Extra variables, tables, alignment, scratch
areas, internal buffers and private stack reservations are all zero. Maximum
decoder stack is four bytes including the caller's two-byte return and one
live source PUSH HL. There are no nested decoder CALLs. This structural bound
also covers legal lengths outside the corpus. Total decoder service is 7,526.

The native harness's AF/AF'-preserving IM1 handler adds 13 code bytes and six
stack bytes (hardware PC plus two AF saves), so complete service including
that handler is 7,545, with maximum observed stack ten bytes. Other handlers
must count their actual code, variables and extra stack. API arguments
`irq_code_bytes` and `irq_stack_bytes` add caller IRQ reservations and enforce
the cap; `service_limit` may reduce it but cannot exceed 10,000. These arguments
account for caller-owned storage; the generator does not emit an IRQ handler.

Input/output/history are explicitly separate and excluded, as authorized.
The real corpus needs at most 6,209 compressed bytes and 8,192 output/history
bytes per independent allocation. Directed cases reach 15,878 /15,872 bytes.
Do not silently treat resident data as zero RAM or assume in-place overlap.

## Correctness, exports and reproduction

Three candidates each pass all 417 real/directed/seeded-random cases, also
relocated to 9103h and with register-preserving IRQs: 1,251 comparisons and
4,170 full native executions including the shared tuned-Mega baselines.
Protected replay validates exact EOF, sequential input/output, initialized
overlapping history, patched-code permissions, caller SP/IX/alternate
registers, stack depth and each gamma-proven prefix bound. Pure literal blocks
legitimately use only two stack bytes; the resumed harness checks <=4 rather
than incorrectly requiring every block to reach the maximum four.

A separate 56-case high-word supplement tests offsets1/2/127/128/255/256/257
and match lengths127/128/255/256/257/32767/32768/49151. It covers both reused
and new-offset word-count gamma paths beyond the original corpus's15872-byte
directed limit. Each cap again passes plain/IRQ/relocation and exact dynamic
delta checks:168comparisons/560native runs. The explicit disjoint layout is
code0800h (relocated0903h), input0400h, output3000h, callerSP2ff0h. The native
harness now accepts an optional caller stack and rejects overlapping live
allocations. Supplement totals are17,223,072 /17,207,712 /17,183,712T versus
tunedMega17,240,318T; no slower case. These directed totals do not enter the
real-corpus speed percentages above.

All 31 default byte/label profiles and six pinned assembly resources remain
exact. All 31 library tests pass, including dirty-offset startup, short/long
gamma boundaries, CLI rejection of irrelevant tuning/coroutine flags, strict
service overflow and ORG/DB export reconstruction. The isolated wheel imports
no tests/toolkit/numpy modules and reproduces API/CLI exports of all three caps.
Generated assembly comments document gamma depth, overlapping copies, register
ownership, stack, service accounting and the word-loop join.

```powershell
python -m zx0 build --variant maximum --prefix-cap 127 --irq-code-bytes 13 --irq-stack-bytes 6 --output build/zx0-maximum
python -m zx0 build --variant maximum --prefix-cap 31 --core 0x8000 --core-limit 0xa000 --output build/zx0-frontier31
python libraries/tests/measure_mega_prefix.py --public --output libraries/evidence/ten_percent_maximum.json
python libraries/tests/measure_mega_prefix.py --public --high-word --output libraries/evidence/ten_percent_maximum_high_word.json
python -m unittest discover -s libraries/tests -v
python -m pip wheel --no-deps --no-build-isolation --wheel-dir .tmp/maximum-wheels libraries/zx0
python -m pip install --no-index --no-deps --target .tmp/maximum-installed .tmp/maximum-wheels/zxvideo_zx0-0.1.0-py3-none-any.whl
python -I libraries/tests/smoke_install.py .tmp/maximum-installed zx0 .tmp/maximum-smoke
python libraries/tests/verify_maximum.py --output libraries/evidence/ten_percent_maximum_verification.json
```

Use the existing native `z80` dependency on PYTHONPATH and a writable local
TMP/TEMP. To reproduce this historical complete authentication use`6759dedf`;
the current wheel/smoke adds more profiles and has its own[reproduction](ZX0_WORD_PREFIX.md).
Use a writable local
TMP/TEMP. Save each command's output as the correspondingly named
`.tmp/maximum-native.log`, `maximum-unit.log`, `maximum-wheel.log`,
`maximum-install.log` and `maximum-smoke.log` before authentication.
Save the separate supplement output as`.tmp/maximum-high-word.log`.

- [Independent prototype](tests/mega_prefix_profile.py) and
  [historical full 2026-10-19 report](evidence/ten_percent_mega_prefix.json).
- [New complete public 2026-10-20 replay](evidence/ten_percent_maximum.json).
- [Complete high-word supplement](evidence/ten_percent_maximum_high_word.json).
- [Source, input, wheel and test-log authentication](evidence/ten_percent_maximum_verification.json).

Accept the optional public measured frontier. Preserve smaller Fast/Mega
profiles for applications with different memory/features. No movie, TRD,
physical disk delivery or universal fastest-decoder claim is made.
