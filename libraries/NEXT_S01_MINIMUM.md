# S01 — Minimum service memory and compact intermediates

Completed 2026-10-20 in `codex/codec-speed-pass3`. This bounded audit examines
at most three designs per codec, against ZX0 Standard and LZSA2 Small. All
required Z80 initialization is included. The target is minimum total service
memory and nondominated intermediate speed/size choices under 10,000 B.
Input/output/history are separate. No global minimum or new maximum-speed
gain is established; fastest resident choices remain the F00/E01 profiles.

## Public results

| Selection | Code including embedded state B | Required stack B | Service B | Real CPU T | Delta T vs size baseline | Included entry setup T |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ZX0 Standard, unchanged baseline | 68 | 6 | 74 | 201,490,104 | 0 | 34 |
| `zx0.small.build('gamma-jp')` | 69 | 6 | 75 | 199,881,370 | -1,608,734 | 34 |
| Existing Standard both-JP | 70 | 6 | 76 | 199,405,316 | -2,084,788 | 34 |
| `zx0.small.build('smc')` | 74 | 4 | 78 | 189,794,309 | -11,695,795 | 43 |
| LZSA2 Small, unchanged baseline | 137 | 8 | 145 | 20,423,546 | 0 | 24 |
| `lzsa.compact.build(compact_eof=True)` | 136 | 8 | **144** | 20,423,420 | -126 | 24 |

ZX0 uses 364 real blocks; LZSA2 uses 21. Their totals are not cross-codec
speed comparisons. ZX0 SMC/gamma reduce CPU by 5.804650%/0.798418% against
Standard; LZSA2's 0.000617% gain accompanies a one-byte service reduction.
Existing Fast/Mega/Hybrid/Maximum profiles remain faster at larger footprints.
The [function-linked table](DECODER_VARIANTS.md) compares all choices with
both original/pass Fast and identifies the measured aggregate Pareto points.

Code, embedded operands and all required caller-stack bytes count together.
There are no tables, alignment padding, extra variables, scratch or internal
buffers. Embedded mutable state is two B in ZX0 SMC/LZSA2 and zero in gamma-JP,
already inside code. Actual IRQ code and hardware/handler stack are additional;
the 13-code/six-extra-stack example totals 97/94/163 B for SMC/gamma/compact EOF.

ZX0 Standard remains the smallest tested usable Spectrum profile at74 B.
Gamma-JP remains ROM-compatible. SMC trades four extra service B for faster
copies; its offset bytes require writable nonreentrant code. LZSA2 reduces
the retained minimum to144 B. Defaults are preserved byte/label/metadata exact.

```python
from zx0.small import build as zx_build
from lzsa.compact import build as lz_build

zx_regions, zx_labels, zx_meta = zx_build('smc', core=0x8000, core_limit=0x8400)
lz_regions, lz_labels, lz_meta = lz_build(compact_eof=True)
```

The LZSA2 alias is `lzsa.block.build('small', compact_eof=True)`. Export with
the corresponding package's `export.export`. CLI selections:

```powershell
python -m zx0 build --variant small-smc --output build/zx0-small
python -m zx0 build --variant small-gamma-jp --output build/zx0-gamma
python -m lzsa build --profile small-block --compact-eof --core 0x8000 --core-limit 0x8400 --output build/lzsa-small
```

These APIs require complete valid input/history, HL=input, DE=nonwrapping
output and a valid caller stack. IX/IY/alternate pairs survive, including
AF' for ZX0; LZSA2 uses AF' for its clobbered cache. Preserve all live registers
in IRQs. No quotas, paging, streaming or guarded-wrapper mode is exposed.

## ZX0 designs and complete costs

1. **Fixed RST28 helper:** separating the15-byte Elias helper would predict
   49 main+15 helper+6 stack=70 B and save6 T per replaced CALL. On Spectrum128,
   0028h..0036h is ROM. This is rejected before guest execution because it
   requires a replacement ROM and loses arbitrary RAM placement. It is not
   a usable Spectrum minimum or a proof that other smaller layouts cannot exist.
2. **SMC offset:** replace the persistent stack offset by an embedded operand.
   Startup grows3 code B; copy grows1; new-offset handling grows2. Required
   stack drops6 ->4 B, so service74 ->78 B. The complete match setup/restoration
   changes70 ->42 T, excluding identical LDIR work. Reset runs every call:
   `LD BC,FFFF; LD(offset),BC; INC BC; LD A,80`,43 T versus34 T originally.
   New-offset parsing removes POP BC10 but replaces PUSH BC11 by store20.
   With one EOF, the exact full-case equation is
   `9 -28*matchCopies -10*newOffsetEntries +9*(newOffsetEntries-1)`
   = `-28*matchCopies -newOffsetEntries`. Initialization has not disappeared.
   Incoming B during offset gamma is dead: LD B,C replaces it and the next
   ADD A,A overwrites RL B flags. Full16-bit shifts remain for every length.
3. **One unconditional jump:** both single-site layouts were emitted only
   for static binary-oracle checks. Baseline host counters select gamma-JP:
   804,367 real gamma-back jumps versus238,027 copy-back jumps. At equal75-B
   service the selected layout saves1,608,734 T, versus a predicted476,054 T
   for the unselected copy-only layout. Only gamma-JP receives native replay.

Both selected candidates improve all473 baseline cases. Relative to existing
76-B both-JP Standard, gamma-JP uses one fewer byte but costs476,054 more
real T;450 cases including all364 real cases slow, maximum2,792 T. SMC has
76 slower non-real cases at most50 T against that different reference, with
no slower real case. Keep these comparisons separate from zero regressions
against original Standard. Both-JP remains publicly available through
`zx0.block.build('standard', fast_jumps=True)`; its archived417-case proof
and current emitted bytes are bound by the new independent jump counts.

## LZSA2 designs, boundary correction and regressions

The accepted EOF layout replaces `JR NZ,WordLength; POP BC; RET` by
`POP BC; RET Z; PUSH BC`, saving one code B. Carry is already set; POP/PUSH
preserve Z. EOF discards only the helper return and returns to the block
caller. A word escape restores that return before reading A=low/B=high;
the caller then replaces C. Temporary BC cannot affect the decoded length.
EOF27 ->21 T; word dispatch12 ->26 T. The exact equation is
`14*wordEscapes -6*EOFs`. All21 real inputs have zero word escapes, saving6 T
each. The full675-case batch has899 word escapes: **+8,536 T**, with643
slower non-real cases, maximum232 T. All eight supplemental word-literal1/2
and word-match2/3 cases add8 T but remain correct in both cache phases.

Two further bounded candidates share the nibble reader's continuation with
length parsing to remove one nested return: tagged139 code+6 stack=145 B,
combined138+6=144 B. Their real CPU is20,748,300/20,748,174 T, worse than the
accepted144-B EOF mode, so both are dominated and receive no promotion gates.
Length cached/refill paths save9/13 T; offset nibble paths add18/14 T.
All675+8 C cases reconcile this independent original-backend observer model.

A token80h discriminator collision was found during pre-emission review.
The repaired architecture increments Case10x's token before saving it and
decrements C in the common tail, restoring80h..BFh exactly. Case00x uses
proven B=FF; length bases3/9 normalize to2/8 with adjusted constants. The
1,048,576-state tag/nibble/alternate-flag check is analytical; complete emitted
native cases are separate evidence. The rejected designs and all slower
cases remain saved. None is an unrecorded extra candidate.

## Qualification, provenance and reproduction

[ZX0 proof](evidence/next_s01_zx0_full.json.gz), SHA256
`2a202c04484bc67ce1d32e15e68d130b2a97bc17a21d32947561728ac6fc6223`:
473 baseline cases reproduce original/C counts, including56 high-word cases.
Each candidate passes473*6 protected configurations plus nine FFFFh probes.
All473 have actual minimum-safe compressed-input overlap and exact host/native
write-cursor digests. SMC/gamma observed plain/IRQ stacks are4/10 and6/12 B;
they receive3,808/3,992 IRQs. All256 candidate alignments pass an independent
pinned-Standard binary relocation oracle. Measured source launch/final hashes match.

[LZSA2 proof](evidence/next_s01_lzsa_full.json.gz), SHA256
`05cf06edbb09b2c1aea741f46aebabe13c6964370bd370875f994524b154f48f`:
675+8 baseline cases bind qualified C/original counts, then all three candidates
pass C screening and exact models. Only useful EOF passes675+8 inputs at six
protected configurations plus nine FFFFh probes:4,107 configurations. Required
plain/IRQ stack reservations are8/14 B; observed peaks are8/12 B. All byte EOF,
dirty operand, permitted code writes, IX/IY/alternate pairs, SP, input/frontier
and host/native minimum-safe overlap digest checks pass. All256 origins for
baseline and every candidate are inventoried. Initial setup stays24 T,504 T
across21 real blocks, with zero required external initializer.

The first LZSA2 run completed native checks but failed while writing a summary
with a relative output path. Preserve its full data/source in the
[reporting-attempt archive](evidence/next_s01_lzsa_reporting_attempt.json.gz).
Path normalization was corrected and a full frozen rerun exited0. The separate
[reporting finalizer](tests/next_s01_lzsa_finalize.py) attaches that provenance,
checks equal guest bytes/all C results, and adds inventories/components; it
runs no guest instructions. Original executed hashes are retained, while
public compact.py changes are bound through the [prior-source archive](evidence/next_s01_prior_sources.json.gz).

Total useful-candidate protected configurations: **9,801**. Current public
functions are self-contained; bytes/every label match native origins and
all alignments. [Public authentication](evidence/next_s01_public_verification.json)
records107 library/24 selected toolkit tests,31 legacy layouts/six resources,
unchanged preceding71 calls, isolated wheels, API/CLI exports and actual
inventory/initialization. Saved CPU is reused by exact identity, without
claiming new guest replay on the later public sources. The table is rebuilt
against those witnesses. Wrapper, contention, physical ROM/disk and movie
timing remain separate; S01 is complete, E04..E07 remain in the queue.

```powershell
python libraries/tests/next_s01_zx0_measure.py --output .tmp/next-s01-replay/next_s01_zx0_full.json.gz
python libraries/tests/next_s01_lzsa_measure.py --output .tmp/next-s01-replay/next_s01_lzsa_full.json.gz
python -m unittest discover -s libraries/tests -v
```

Select the already qualified C DLL explicitly through `CODEC_EMULATOR_DLL`.
The public integration reproducer is [verify_next_s01_public.py](tests/verify_next_s01_public.py),
with rebuilt wheels and its named local test/build logs. Fresh replays keep
new source identities and should write to `.tmp`, preserving frozen history.
