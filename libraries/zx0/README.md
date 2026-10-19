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

The optional `banked.build(aligned_ring_table=True)` places the existing
four-bank table at7F00 and saves21 T per ring_page call (108 ->87 T with
direct OUT). Reserve code/state/table through7F04: alignment adds121..245
bytes depending on the other banked options. It adds no input/output buffer
or stack. Defaults retain their original bytes/layout. [Measured applicability](../TRICK_AUDIT.md)
includes64 complete native banked blocks and IRQ checks; adoption in a player
still needs its RAM, contention and physical delivery/publication checks.

Run [examples/prepare.py](examples/prepare.py) with an output directory to
create a small raw sample, compressed payload and complete assembly example:

```powershell
python /path/to/zx0/examples/prepare.py build/zx0-example
```

The example uses the tested serializer and needs no compressor executable.
Compile its `example.asm` with an assembler supporting ORG, DB, EQU, INCLUDE
and INCBIN (for example sjasmplus). The default reservations fit this tiny
sample; a larger project must choose and validate its own layout.
# Optional Mega one-shot decoder

`zx0.block.build('fast',core=0x8000,core_limit=0x8400)` or
`python -m zx0 build --variant fast-block --core 0x8000 --core-limit 0x8400 --output build/zx0-block`
exports the207-byte Fast entry `zx0_DecompressZX0`. The same resident-block
API also accepts standard, turbo and mega. HL=input, DE=output; AF/BC/DE/HL
clobbered, IX and alternate registers retained. Preserve live registers in IRQ
and reserve caller-stack plus handler/hardware headroom. Validate the complete
valid block, output length/allocation and nonwrapping output externally.
Fast/Turbo/Mega need writable offset operands and non-reentrant code. No quota,
paging or yields; use existing coroutine profiles for those caller requirements.

`python -m zx0 build --variant mega --core 0x8000 --core-limit 0x8300 --output build/zx0-mega`
exports the pinned673-byte bit-phase-specialized decoder. HL points to a complete
valid ZX0 v2 block, DE to its nonwrapping output; call `zx0_dzx0_mega` with
resident source/history and the caller stack. AF/BC/DE/HL are clobbered. Preserve
them in IRQ handlers and reserve caller-stack headroom; the offset operand needs
writable RAM. There is no yield, paging or output-quota contract. See the native
comparison in [SECOND_PASS.md](../SECOND_PASS.md); defaults retain their ABI.

## Optional unconditional jump policy

`zx0.block.build('standard', fast_jumps=True)` changes two unconditional JR
instructions into JP, saving 2 T each time for two extra code bytes (68 ->70).
The real 364-block fixture improves 201,490,104 ->199,405,316 T (1.034685%).
Turbo/Mega have only one eligible startup jump: +1 byte and -2 T per block.
Fast already uses JP, so this option adds no bytes or CPU gain there.
Conditional branches, wire format and caller ABI are unchanged.

```powershell
python -m zx0 build --variant standard --fast-jumps --core 0x8000 --core-limit 0x8100 --output build/zx0-standard-fast-jumps
```

The CLI flag is supported by resident Standard/Turbo/Mega/Fast-block profiles.
The existing coroutine CLI variants retain their own branch policy.
[Full counts, space costs and regression scope](../OPTIMIZATION_PLAN.md#item30--unconditional-branch-speed-policy-2026-10-19).

## Optional measured Fast branch layout

`zx0.block.build(branch_tuned=True)` and `zx0.resumable.build(branch_tuned=True)`
select conditional JR/JP forms using the full frozen real-input frequencies.
The data format, conditions/flags, coroutine quotas and caller ABI remain exact.
The resident Fast profile improves 156,012,520 ->153,706,279 T (1.478241%)
on 364 real blocks while shrinking 207 ->193 bytes. The same coroutine work
improves 180,610,040 ->178,657,995 T (1.080806%), 401 ->388 total bytes.
The policy rechecks relative reach and retains JP when a coroutine insertion
makes a target too far away. Metadata records changes and fallbacks.

Enable with `--branch-tuned` on `--variant fast` or `--variant fast-block`.
Defaults are unchanged. Three directed cases per profile are 1..4 T slower;
individual slices can also be slower. All real blocks improve in the retained
corpus. This is an intermediate step toward the separate 10% goal, not its
completion or a player-release claim. [Complete candidate counts](../evidence/ten_percent_tuned_branches.json).

## Optional multi-byte literal prefix

Fast resident/coroutine builds accept `literal_prefix=True` / `--literal-prefix`.
One LDI before LDIR saves 5 T on proven BC>=2 runs; BC=1 bypasses it. Resident
code grows two bytes, saving another 569,485 T on all real blocks with none
slower. The coroutine checks quota before output and preserves every return
cursor, but grows 30 bytes and spends 26 T extra per target synchronization.
At 256-byte demands it saves 268,301 T overall while two real blocks and some
slices slow; keep the option off for workloads where that cost dominates.
Choose core reservations explicitly; the untuned coroutine exceeds its old
default reservation. [Counts, limits and verification](../LITERAL_PREFIX.md).

## Optional repeated-match tail refill

`inline_tail_refill=True` on Fast resident/coroutine builds, or
`--inline-tail-refill` on Fast CLI profiles, removes a redundant CALL/RET when
a repeated-match gamma code exhausts its bit reservoir. It costs three bytes
and saves 18/5 T per such refill (terminating/continuing stop bit), without
changing input bytes, quotas, IRQ requirements or caller ABI. It combines with
`branch_tuned`. The complete real corpus saves another 359,963 T per profile;
no block or slice slows in all 417 retained cases. Defaults remain exact.
[Absolute counts, register contract and reproduction](../TAIL_REFILL.md).

## Optional smaller and faster Mega

`zx0.block.build('mega', mega_tuned=True)` / `--variant mega --mega-tuned`
removes four dead offset-word shifts and tunes four reuse exits. Defaults and
wire format stay exact. Real CPU146,421,546 ->145,701,295T (-0.491902%) with
`fast_jumps=True`, code674 ->670bytes. Maximum decoder stack is4bytes including
the caller return, so complete service memory is674bytes before caller IRQ
code/headroom; there are no separate variables, tables or scratch buffers.
Count resident input/output/history separately. This is the existing resident
ABI with no coroutine equivalent. Individual changed untaken exits cost+3T,
although every retained complete case improves. [Counts, IRQ memory contract,
public/prototype equivalence and full tests](../MEGA_OFFSET_AUDIT.md).
