# ZX0 E04: a 255-byte shared copy prefix

Experiment dated 2026-10-20, starting at `ac8355e5`. This stage tests one
larger/faster resident candidate, retaining the 61 fixed E01 `fast` branches.
Its predecessor is the accepted cap228-fast decoder, not a hypothetical
uncontracted cap255 implementation. Input format, complete resident ABI and
the 473 frozen compressed inputs remain unchanged.

| Resident selection | Code B | Required stack B | Service B | Real CPU T, 364 blocks |
| --- | ---: | ---: | ---: | ---: |
| E01 shared cap228-fast | 7,513 | 4 | 7,517 | 139,552,884 |
| E04 shared cap255-fast | 8,161 | 4 | 8,165 | 139,546,674 |
| Incremental change | +648 | 0 | +648 | -6,210 |

The candidate saves 0.004450% of the predecessor's real CPU time. It is a
useful maximum-speed endpoint among the tested resident choices; cap228-fast
remains available for its smaller service reservation. This finite comparison
does not establish a global optimum or the broader additional-ten-percent goal.

## Copy and memory derivation

Each of three parser families and four reservoir phases has a shared copy
chain. The word-count entry proves BC >=256. Extending each chain from228 to255
adds27 `LDI` instructions: 12 x27 x2 =648 code bytes. One mutable two-byte offset
operand is already part of the code and is counted once. There are no separate
variables, tables, padding, scratch areas or internal buffers. The four-byte
stack reservation includes the caller return and the saved source word.
Compressed input and output/history are separate, as authorized.

For each extended entry,27 repeating `LDIR` iterations at21 T become27 `LDI`
instructions at16 T: -135 T. The final `LDIR` always starts with BC >=1,
including the length256 edge; no zero-count 65,536-byte copy is introduced.
The frozen real inputs enter these paths46 times, giving -6,210 T. Across all
473 inputs there are186 such entries: -25,110 T, for161,800,568 T in total.
105 cases improve and368 are equal; no frozen case regresses. Directed
255/256/257 inputs exercise all three families and all four phases.

An independent insertion oracle extends the old emitted binary and remaps
absolute references. Its complete bytes and every label match the generated
candidate. All61 relative displacements remain unchanged. The 13-code-byte/
six-extra-stack-byte diagnostic IRQ example makes total service8,184 B at
every one of the256 low-byte alignments, below10,000 B. Actual application IRQ
storage must still be declared through the builder's reservation arguments.

## Initialization is inside the totals

Every call starts before `LD BC,FFFF`:10 T, offset reset20 T, `INC BC`:6 T and
entry `JP`:10 T, for46 T including the20-T reset. The predecessor does the
same work. There is no separate required target initializer. Static code is
installed as the library image; there is no target table-generation step.

For364 real calls the setup subtotal is16,744 T; the remaining parser/copy/
EOF/return work is139,529,930 T. Their sum is139,546,674 T. For all473 calls,
21,758 T of setup plus161,778,810 T of remaining work gives161,800,568 T.
Each saved per-block measurement is a cold library invocation, including
reset; setup is not amortized away. Caller `CALL`17 T and application-specific
argument loads are outside the stated entry-through-RET convention. Hardware
IRQ execution, ULA, ROM/disk latency and application boot remain separate.

See [the initialization audit](BENCHMARK_INITIALIZATION.md) for the common
resident/coroutine/guarded boundaries and producer-plus-decoder accounting.

## Qualification and reproduction

The 509 inputs (473 frozen plus36 directed) pass all six protected modes:
plain, IRQ, relocation, actual minimum-safe overlap, overlap with IRQ and
overlap with relocation. There are3,054 configurations plus nine FFFFh cursor
probes. All473 frozen inputs have genuine input/output overlap. Host/native
read-order and input-frontier digests match. Dirty-offset reset, exact EOF,
code writes, IX/IY/all alternate pairs including AF', SP and required source
history pass. Observed stack peaks are4 plain and10 with IRQ;2,806 interrupts
are injected. Word-entry BC never falls below256; the first LDIR remainder
never falls below1. All256 static origins and four measured placements match
the independent binary/label oracle.

The frozen [full native proof](evidence/next_e04_full.json.gz) has SHA256
`7c0b3565b19e4da0c0de0e13f96fc9ea2a1eea0a96cf05e4edc34568f4bae009`.
[Its summary](evidence/next_e04.json) preserves the separate historical E01
branch comparison. The new prefix introduces no slower frozen or directed
case; E01's103 older non-real regressions against uncontracted cap228 remain
historical lineage, not E04 regressions.

Public integration uses `zx0.maximum_branches.build(prefix_cap=255,
policy='fast')` and CLI `--variant maximum-branches --prefix-cap 255` with an
explicit `--branch-policy fast` if desired. Defaults stay at228. Plain
Maximum, other policies and coroutine hooks reject255. All113 library and24
selected toolkit tests pass; package/wheel authentication is recorded in the
separate [public proof](evidence/next_e04_public_verification.json).
That check preserves the entire metadata of all74 preceding selections,
31 frozen defaults and six upstream resources. It verifies78 isolated wheel
API exports and two CLI exports. The [75-call table](DECODER_VARIANTS.md) and
the initialization audit include the new endpoint. The first focused CLI
test encountered default sandbox TEMP permissions; setting local TMP/TEMP
resolved the environment, and the complete113-test run passed.

The private reproducer is
[next_e04_measure.py](tests/next_e04_measure.py), with its independent oracle
in [next_e04_profiles.py](tests/next_e04_profiles.py). It uses the qualified
local C backend for screening and the original protected backend for complete
IRQ, relocation, EOF, register, code-permission, stack and actual compressed
overlap checks. Low ROM origins are flat-CPU high-word stress layouts, not a
claim that writable decoder code runs in Spectrum ROM.

```powershell
$env:PYTHONPATH='C:\Work\ZX-video\.tmp\library-test-deps'
$env:TMP=(Resolve-Path .tmp).Path
$env:TEMP=$env:TMP
$env:CODEC_EMULATOR_DLL=(Resolve-Path .tmp/codec-cpu-qualified/codec_cpu.dll).Path
python libraries/tests/next_e04_measure.py --output .tmp/next-e04-replay/next_e04_full.json.gz
python -m unittest discover -s libraries/tests -v
python libraries/tests/document_decoder_variants.py
python libraries/tests/audit_benchmark_initialization.py
python libraries/tests/document_decoder_variants.py
```

The private generator deliberately depends on the archived pre-public source
shape. Its executed launch/final source hashes are historical provenance.
Public API integration must bind current bytes and every label to that frozen
proof; changing current source hashes does not retroactively change which
sources the native run executed. Coroutine, guarded-input, physical disk/ULA
and movie publication qualification are separate stages.

The saved private sources and native proof remain unchanged. Public authentication
is reporting/export work using exact frozen bytes, not another native run.
Its source and wheel arguments are documented in
[verify_next_e04_public.py](tests/verify_next_e04_public.py); the archived logs
under [next_e04_public](evidence/next_e04_public) retain the complete checks.
The first real cold call takes207,318 T:46 setup plus207,272 remaining work.
