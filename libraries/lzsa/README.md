# Raw LZSA2 library

Install with `python -m pip install /path/to/lzsa`; use
`python -m pip install "/path/to/lzsa[native]"` for measured Z80 optimization.
Alternatively copy `src/lzsa` onto your Python path. This directory is
independent of ZX0 and ZX-video. The package covers the project's standard
**raw LZSA2** format; LZSA1 and framed LZSA are not implemented here.
It retains Emmanuel Marty's zlib notice and spke/uniabis decoder credits.
Pinned upstream revision: `15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5`.

## Host use

For a complete resident block, `lzsa.block.build(core=0x8000,core_limit=0x8400)`
or `python -m lzsa build --profile fast-block --core 0x8000 --core-limit 0x8400 --output build/lzsa-block`
exports a separate one-shot entry `lzsa2_start`. Supply HL=input, DE=output;
AF/AF'/BC/DE/HL are clobbered, IX and other alternate pairs retained. It uses
the caller stack and a writable offset operand, with no quota/paging/yield
state. Validate input and expected nonwrapping output/allocation externally,
keep source/history resident and preserve live registers including AF' in IRQ.
Reserve stack for the decoder plus the actual IRQ handler and hardware return.
The coroutine stays the default. See [measured comparison](../SECOND_PASS.md).

```python
from lzsa import compress, decompress, trace

packed = compress(raw, executable="/path/to/lzsa")
assert decompress(packed, limit=len(raw)) == raw
output, proof = trace(packed, limit=len(raw))
trace(packed, limit=len(raw), input_start=proof["minimum_input_start"],
      bank_bytes=proof["minimum_footprint"])
```

`limit` is the exact decoded size for one independent raw block. The parser
rejects truncation, trailing bytes, invalid offsets and output overflow. The
overlap trace checks unread input and live match history in shared RAM.
`encode(raw, matches)` serializes validated `(position,length,distance)`
matches using standard offset/length fields and shared nibbles.
`optimal(raw, max_bytes=256)` is the transferred exhaustive minimum-size
short-input oracle. Its result includes cost/state statistics; its tie-break
does not minimize CPU and it should not be used to encode large streams.

```python
from lzsa.distance_cost import Costs
from lzsa.distances import optimize
from lzsa.resumable import build
from lzsa.native import execute
from lzsa.budget import fit

costs = Costs()
candidate, comparison = optimize(packed, len(raw), costs, objective="cycles")
regions, labels, metadata = build()
baseline = execute(regions, labels, metadata, packed, raw)
candidate, measured, report = fit(candidate, raw, len(packed),
    baseline["tstates"], costs, regions, labels, metadata)
if not report["budget_met"]:
    candidate = packed
```

`optimize` retains command positions/lengths, searching every valid canonical
distance with true last-offset and nibble state. `size-no-slower-tokens`
minimizes bytes without slowing any modeled individual token/EOD. Both
objectives retain the original byte budget. `fit` removes selected two-byte
matches, ranks them with the exact suffix model and verifies each complete
candidate with native replay. Check the returned budgets and overlap before
acceptance. `execute` includes coroutine slices, protected memory and optional
synthetic IM1 probes. It measures flat deterministic CPU, excluding physical
disk, TR-DOS, ULA contention and frame scheduling. For relocated output,
choose a nonoverlapping `caller_stack` as well as generator `stack`.

`author.Author(path)` retains the ctypes binding to an optional separately
built upstream library. [author_wrapper.c](author_wrapper.c) exports the same
two calls on Windows and ELF platforms. Build it against the complete pinned
upstream checkout with that checkout's notices; upstream C sources/binaries
are not bundled. The CLI compressor adapter is the ordinary portable backend.

## Z80 use

```powershell
python -m lzsa build --streaming --direct-header --output build/lzsa
```

`lzsa.resumable.build` returns regions, labels and an instruction timing list.
Prefix/core reservations, private stack and output base are configurable.
Defaults retain the current Spectrum layout. Set `input_pointer`, `block_end`
and `slice_target`; call `begin` and resume through `slice_until`. Targets are
minimums checked between tokens. Output must not wrap; declared buffers,
stacks, code and workspace must be disjoint or have a proven overlap layout.
Code and state need writable RAM. AF/BC/DE/HL and AF' may be clobbered on
return; SP is restored. Interrupt handlers must preserve live working
registers, especially AF' holding the nibble reservoir. The altered EOF path
consumes exactly the block, avoiding the upstream two-byte overread.

For streaming, supply whole input pages only during suspension. Publish the
exclusive loaded high-byte frontier in `input_high`, `header_frontier` and
`literal_frontier`. Initialize guards for every new partial block. Set
`all_loaded` only after all input and any shared-sector tail are retained.
`input_needed` requests more input; `finished` proves EOD independently of
whether the output target was reached. Whole-page frontiers and the 32-byte
header/seven-byte literal lookahead are part of this ABI.

`lzsa.streaming.emit_guard_update` emits the existing final-input branch
bypass. It expects `all_loaded` in A, clobbers AF/HL and falls through; append
RET for a callable helper. Call it with the decoder suspended, after updating
frontiers and completion. It restores guarded branch destinations for partial
input and repoints them to the original paths after final input. There is no
additional per-token test once complete. With `direct_header=True`, the
available-prefix path remains 46 T versus 96 T for the prior CALL/RET guard.
Direct mode requires `streaming=True`; AF is dead at entry, AF' stays live.

`word_state_init=True` / `--word-state-init` optionally clears adjacent
input_needed/finished in one word instruction, saving4 T per begin and one
code byte. Both input-guard modes retain exact EOF/yield/IRQ behavior.
[Second-pass evidence](../SECOND_PASS.md) includes both full streaming checks.

`restore_compare=True` / `--restore-compare` optionally restores the compared
target with ADD HL,DE instead of a reload, saving5 T per begin/resume and two
code bytes. Equality/carry semantics remain valid; the complete ordinary and
both streaming modes are measured in [the second pass](../SECOND_PASS.md).

An optional long-copy profile applies sixteen `LDI` instructions to the
byte-extended literal18..255 and match24..255 forms. All short and escaped
16-bit forms keep their existing paths, including short lengths encoded with
a16-bit escape. Enable it with `build(long_copy=True, core_limit=0x9000)`, or:

```powershell
python -m lzsa build --long-copy --core-limit 0x9000 --output build/lzsa-long
```

Explicitly reserve the additional87 core bytes (84 with streaming); the
default reservation rejects this profile. It adds no state, stack or tables.

For ordinary complete input, `near_literals=True` (CLI `--near-literals`)
places the same helper near its JR caller. This saves another10 T per
byte-form literal and3 bytes, leaving84 extra core bytes. Short and escaped
word paths stay unchanged. [Second-pass verification](../SECOND_PASS.md).
The default placement keeps these kernels in uncontended Spectrum bank2.
Retain writable code and the same forward-copy/IRQ contracts. Streaming users
must use `emit_guard_update` or the optional `long8_complete`
labels when bypassing guards. Calling the old short-copy targets is correct
but loses the long-copy improvement on completely loaded blocks.
[Timing and complete-block evidence](../LONG_COPY.md) records a small0.124%
CPU gain on the retained real fixture; compressed bytes/sectors are unchanged.
This profile has no new movie publication or physical disk qualification.

Original assembly lives in `src/lzsa/asm`; the generated adapted
`decoder.asm` includes the coroutine, guards and byte-exact EOF changes.
Run [examples/prepare.py](examples/prepare.py) to create a complete tiny example
without an installed compressor:

```powershell
python /path/to/lzsa/examples/prepare.py build/lzsa-example
```
