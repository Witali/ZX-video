# Reusable ZX0 and LZSA libraries

[Z80 instruction timing desk reference](Z80_TIMINGS.md) keeps per-instruction
T-states, conditional/repeating costs and common optimization arithmetic close
to the implementations. [Measured codec paths](TIMING.md) retain experiment
totals and their input scope.

The current [speed/service-memory frontier](FRONTIER.md) tracks three user
targets: maximum speed under 10,000 service bytes, faster AND smaller, and
intermediate tradeoffs. Count code, variables, tables, padding and required
stacks/buffers together; compressed input/output are explicitly separate.

[Decoder variants and function links](DECODER_VARIANTS.md) lists the measured
choices, exact builder calls and implementation files, with CPU comparisons
against both the original adapted Fast and the latest optimization baseline.
It also includes the smallest retained valid Standard/Small implementations.

The optional [shared ZX0 Maximum layout](ZX0_SHARED_PREFIXES.md) shrinks the
fastest resident choice from 9,990 to 7,578 service bytes and saves another
277,150 real CPU T. Use `zx0.maximum.build(shared_prefixes=True)`; the smaller
5,114-byte shared127 also beats the previous maximum. Defaults stay exact.

The optional [fixed LZSA2 hybrids](LZSA_HYBRID.md) add a 4,999-byte compact
choice that beats the old 7,004-byte Expanded by 3.683344%, and a 9,500-byte
fast choice gaining 4.349245%. Use `lzsa.hybrid.build(profile='compact')` or
`profile='fast'`, then the normal exporter. All token forms remain valid;
these new profiles are resident-only and retain directed regression lists.

[Next Z80 experiments](NEXT_TRICKS_PLAN.md) records the researched follow-up
queue, fixed current baselines, memory/timing bounds and complete test gates.
Its candidates are planned hypotheses, not newly benchmarked improvements.

These are two independently installable libraries extracted from ZX-video.
Copy either directory to another project or install it from this checkout:

```powershell
python -m pip install ./libraries/zx0
python -m pip install "./libraries/lzsa[native]"
```

The `native` extra is optional; it installs the pinned `z80==1.2.0` execution
core used for CPU-aware optimization and replay. Basic host decoding, encoding,
overlap checks and assembly generation require only Python 3.10 or newer.
The packages do not import the video converter, NumPy, OpenCV, AY or TR-DOS.
Each folder includes its own licenses, original assembly resources and example.

| Library | Wire format | Reused improvements |
| --- | --- | --- |
| [ZX0](zx0/README.md) | Forward ZX0 v2 | Fast and tuned Turbo coroutines, exact or token-boundary copies, inline literals/matches, bank-local/ring input, guarded page supply, checked split relocation, short-match rewrites, measured bytes/CPU selection and overlap proofs |
| [LZSA](lzsa/README.md) | Standard raw LZSA2 | S/P dispatch, AF' preservation, byte-exact EOF, token-boundary coroutine, guarded input, 46-T direct header, final-input branch bypass, exact short-input oracle, fixed-command distance selection and native CPU-budget fitting |

Generate a ready-to-include **adapted** decoder, including the improvements:

```powershell
python -m zx0 build --variant fast --output build/zx0
python -m lzsa build --streaming --direct-header --output build/lzsa
```

Each command writes `decoder.asm` (ORG/DB with named entry/state EQU symbols
and routine comments), binary regions, `metadata.json` and a license. Include
the generated assembly in your Z80 project, or load its binary regions at the
recorded addresses. Code and patched operands need writable RAM. Use a separate
private decoder stack and preserve live decoder registers in interrupt handlers.
Relocate using generator arguments, then assemble the resulting include at its
new addresses. The defaults retain ZX-video's reservations.

Ordinary compression uses a caller-installed upstream `zx0` or `lzsa`
executable. Both adapters use temporary files and independently verify the
whole returned block. The LZSA oracle is exhaustive only on explicitly bounded
short input; it is not a substitute for the full upstream encoder. The library
does not bundle Windows executables or promise that a CPU-oriented stream will
also save disk sectors. Native costs and delivery costs remain separate.

For fully resident blocks, the explicit `zx0.block` / `lzsa.block` APIs and
`--variant fast-block` / `--profile fast-block` exports omit coroutine checks
and state. They use HL=input, DE=output, caller stack and externally validated
allocations. See [SECOND_PASS.md](SECOND_PASS.md) for native speed/code results,
register/IRQ contracts and the separate673-byte ZX0 Mega option.

Existing `toolkit` imports delegate to these packages; there is one maintained
implementation of the transferred algorithms. Video transforms, dictionary
numbering, block/reset placement around frame packets, window/deadline planning,
disk queues, sector caches, borrowed packet literals and AY remain application
components. Their useful mechanisms are preserved in ZX-video, including the
generic code's use of the shared compression tools. Rejected experiments keep
their reports and are not silently turned on by library installation.

The [nine-item Z80 trick pass](OPTIMIZATION_PLAN.md) adds two explicitly
optional measured profiles: LZSA2 `long_copy=True` for byte-extended forms,
and ZX0 `banked.build(aligned_ring_table=True)`. Complete native/streaming/
IRQ results and rejected candidates are retained. Both need more code RAM;
runtime compressed bytes stay unchanged, while actual boot-code disk packing
and playback qualification remain application work. All defaults stay exact.

The additional items10–29 pass is complete: optional smaller/faster coroutine
helpers, resident Fast/Mega profiles and an explicit compact LZSA2 tradeoff.
[Decisions and reproduction](SECOND_PASS.md) record unsuccessful candidates too;
[final summary](second_pass_verification.json) authenticates evidence, exact
defaults/resources,85 observed unit tests and independent wheel exports.

The [item30 follow-up](OPTIMIZATION_PLAN.md#item30--unconditional-branch-speed-policy-2026-10-19)
adds optional `fast_jumps=True` / `--fast-jumps`: unconditional JP saves 2 T
per selected branch, costing one byte per site. ZX0 Standard gains 1.034685%
on the real fixture (68 ->70 bytes); LZSA2 Fast gains 0.014138% resident or
0.025768% ordinary coroutine (+1/+2 bytes). Turbo/Mega save only 2 T per
block; ZX0 Fast already uses JP. Conditional branches and the LZSA2 cold
wrapper remain unchanged. [Component/integration evidence](evidence/fast_jumps_verification.json)
records 89 tests, both guarded producer modes, relocation and IRQ checks.

The optional `branch_tuned=True` / `--branch-tuned` Fast policy is the first
implementation step toward the user's additional 10% goal. It changes only
conditional JR/JP forms: same-format resident real gains are 1.478241% for
ZX0 and 0.284885% for LZSA2, with ZX0 code 207 ->193 and LZSA2 219 ->220
bytes (the LZSA2 comparison includes `fast_jumps`). All real blocks improve,
but small directed cases and slices can be slower; defaults remain unchanged.
[Full limits and timing](TIMING.md#measured-fast-conditional-branches-item31-2026-10-19),
[evidence](evidence/ten_percent_branch_verification.json).
This intermediate result does not complete the 10%-per-library goal.

The optional Fast ZX0 `literal_prefix=True` / `--literal-prefix` saves another
5 T per proven multi-byte literal run for two resident code bytes. Coroutine
quotas remain exact, with a 30-byte code/26-T-per-request tradeoff; two real
blocks and some slices slow despite the aggregate gain. See
[full native counts and caller limits](LITERAL_PREFIX.md). The ten-percent
goal remains active; defaults are unchanged.

## Verification and provenance

[Verification](verification.json) records the extraction from `0085a116`.
[The pre-extraction baseline](tests/decoder_baseline.json) protects all 31
default decoder configurations, their addresses and label maps. Their opcode
bytes are unchanged: deterministic instruction delta **0 T** on every existing
path. Absolute retained costs and historical comparisons are in
[timing notes](TIMING.md); these measurements have distinct input scopes.
This refactor does not qualify a new movie/TRD or claim real disk/hardware timing.

Run the portable tests after installation of the optional native core:

```powershell
python -m unittest discover -s libraries/tests -v
```

The repository's existing native, streaming and integration tests also exercise
the compatibility imports. Upstream copies under `toolkit/third_party` remain
for historical references. Packaged resources match their original Git blobs;
Explicit checkout attributes keep source hashes stable across platforms.
