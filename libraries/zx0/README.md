# ZX0 v2 library

Install with `python -m pip install /path/to/zx0`, or copy `src/zx0` onto your
Python path. This directory is independent of the LZSA library and ZX-video.
Forward v2 is supported; classic v1 and backward streams are separate formats.
Resources and adaptations retain the BSD-3-Clause notice for Einar Saukas,
and the Fast source credits for spke and uniabis. Upstream revision:
`ecde3a2ae05061fe06469ed46df81a33b7de7d86`.

## Host use

```python
from zx0 import compress, decompress, trace, rewrite

packed = compress(raw, executable="/path/to/zx0")
assert decompress(packed, limit=len(raw)) == raw
output, proof = trace(packed, limit=len(raw))
trace(packed, limit=len(raw), input_start=proof["minimum_input_start"],
      bank_bytes=proof["minimum_footprint"])
candidate = rewrite(packed, minimum_match=4)
```

`trace` proves the forward input/output overlap at every write, including
shared-memory replay. `layout` adds the existing whole-sector/shared-tail
placement calculation; its four-byte header belongs to ZX-video transport.
For other transports use the trace's minimum start/footprint directly.
`Token`, `parse`, `encode` and `rewrite` expose the tested lossless token pass.
Replacing short matches can increase packed size. Measure decoder work and
complete delivery before selecting it. `zx0.selection.choose_cpu` selects from
already measured alternative blocks under a total byte budget; its option
bytes must include any framing overhead owned by the caller.

## Z80 use

```python
from zx0.resumable import build
from zx0.export import export

regions, labels, metadata = build("fast", prefix=0x5000, prefix_limit=0x5400,
    core=0x6000, core_limit=0x6400, stack=0x4ff0, output_base=0xa000)
export("build/zx0", regions, labels, metadata)
```

Configure the generated `input_pointer`, `block_end` (absolute output end)
and `slice_target` (absolute requested output address). Call `begin` for a new
block, then `slice_until` for monotonically increasing targets. Token-boundary
decoders can finish a whole token beyond a target; retain the entire declared
output range. `slice_output` records the current end. Read the final EOD before
reusing input/history. The Fast/tuned Turbo variants require nonwrapping output,
at most 15872 bytes and an end address no higher than FFFF. They restore the
caller SP on return. AF/BC/DE/HL and AF' may be clobbered; IRQ handlers must
preserve live values and have enough private-stack headroom. Fast removes the
persistent IX continuation, allowing callers to reuse IX between slices.
Paging code must keep the selected input/output bank available during a call.
Both emitted code regions and their state/operands must be in writable RAM;
validate code, input, output, both stacks and application workspaces together.

For a simple caller-stack decoder, use `zx0.emit_decoder(assembler, "standard")`
or `"turbo"`: HL=input, DE=output; AF/BC/HL/DE are working registers. Turbo
patches its offset operand and needs writable code. `--variant standard/turbo`
exports those original compact modes without coroutine state.

Additional transferred generators keep their existing explicit contracts:

| Module | Purpose |
| --- | --- |
| `incremental` | Bounded Turbo emitter; exact copies, token boundaries, inline matches/literals, paging hooks and state emitter. `emit_wait` is the optional historical frame-packet adapter. |
| `bank_local` | Spectrum bank-local C000 input/E000 output, dynamic pointer and inline literals |
| `banked` | Spectrum bank ring, fixed 256-byte window, fast literal/refill options and token boundaries |
| `streaming`, `streaming_inline` | Suspend before unavailable input pages, retain explicit input-needed/completion flags |
| `split_bank2`, `split_streaming` | Checked relocation by assembler fixups into the established Spectrum reservations |
| `resumable` | Fast or tuned Turbo, configurable prefix/core/private stack/output |

The Spectrum templates use documented fixed layouts and paging ports. They
do not silently relocate or supply disk data. The `incremental` emitter and
configurable coroutine are the entry points for different memory layouts.
Commented original assembly is in `src/zx0/asm`; generate `decoder.asm` when
you need the project adaptations, since original upstream files lack them.

Run [examples/prepare.py](examples/prepare.py) with an output directory to
create a small raw sample, compressed payload and complete assembly example:

```powershell
python /path/to/zx0/examples/prepare.py build/zx0-example
```

The example uses the tested serializer and needs no compressor executable.
Compile its `example.asm` with an assembler supporting ORG, DB, EQU, INCLUDE
and INCBIN (for example sjasmplus). The default reservations fit this tiny
sample; a larger project must choose and validate its own layout.
