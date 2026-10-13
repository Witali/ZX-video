# Reusable ZX0 and LZSA libraries

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

Existing `toolkit` imports delegate to these packages; there is one maintained
implementation of the transferred algorithms. Video transforms, dictionary
numbering, block/reset placement around frame packets, window/deadline planning,
disk queues, sector caches, borrowed packet literals and AY remain application
components. Their useful mechanisms are preserved in ZX-video, including the
generic code's use of the shared compression tools. Rejected experiments keep
their reports and are not silently turned on by library installation.

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
