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

For tighter code RAM, `lzsa.block.build('small')` or CLI `--profile small-block`
exports137 bytes instead of Fast's218. It shares nibble/length helpers and
returns at exact EOF before extra reads. The caller contract stays resident
input/history, HL/DE pointers, external size validation and writable offset;
plain caller-stack maximum is8 bytes including return, plus IRQ headroom.
All95 native blocks pass, but the21 real blocks cost14.948% more CPU than
resident Fast. Both cores still round to one256-byte raw code sector. Choose
this profile explicitly for code space; the speed-first default is unchanged.

For a larger resident speed profile, use `lzsa.block.build('wide',
core=0x8000, core_limit=0xb000)` or the intermediate `'wide-shared'` variant:

```powershell
python -m lzsa build --profile wide-block --core 0x8000 --core-limit 0xb000 --output build/lzsa-wide
python -m lzsa build --profile wide-shared-block --core 0x8000 --core-limit 0xb000 --output build/lzsa-shared
```

Wide profiles decode the same standard raw LZSA2 payload with the same HL/DE
caller interface and exact EOF. A 512-byte table selects complete token
specializations. At 8000h, wide uses 6,998 code/table bytes plus six caller-
stack bytes including return: **7,004 service bytes**. Shared uses 3,446+6 =
**3,452 service bytes**. At 9103h they need another 253 alignment bytes;
worst alignment adds 255. Offset variables are embedded in code, with no
external state, scratch or internal buffers. The complete service footprint
stays below the user-authorized **10,000-byte** cap. Metadata records each
component; do not add embedded operands twice. The default small reservation
rejects these profiles until the caller reserves a larger code range.

Compressed input and complete decoded output/history are separate caller
buffers. The retained real corpus needs up to 8,198 compressed-input bytes
and 15,872 output/history bytes; no shared-buffer overlap is assumed here.
Across all 95 corpus cases, the literal-only case needs 15,878 compressed-input
bytes; the output/history maximum remains 15,872. The test IRQ handler itself
occupies 13 code bytes, also separate from the decoder's service footprint.
Add actual IRQ/hardware-return stack headroom separately: the measured
register-preserving IM1 test handler needs six extra bytes. IRQ must preserve
both main and alternate live registers, because HL' temporarily holds the
dispatch address; the raw decoder restores the caller's HL' at EOF.

On the complete 21-block real fixture, wide/shared cost 15,623,953 /15,869,483 T
versus 17,765,094 T for Fast +fast_jumps: **12.052517% /10.670425% less CPU**.
All real blocks improve, while 21/22 directed cases slow by at most 20/30 T.
These are explicit speed/space choices; `fast`/`small` and coroutine defaults
stay unchanged. Wide variants use their own branch/copy layouts and reject
the independent Fast tuning flags. They provide no coroutine/partial-input
checks or new player timing qualification. [Full native/package evidence](../evidence/wide_profiles_verification.json).

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

## Optional unconditional jump policy

`lzsa.block.build(fast_jumps=True)` replaces the 16-bit-offset path's
unconditional JR with JP (12 ->10 T, 218 ->219 bytes). Ordinary and streaming
`lzsa.resumable.build(fast_jumps=True)` additionally accelerate the post-yield
return (+2 core bytes total). Cold input retries retain their original size
to fit the existing producer-helper tail. Small does not accept this option.
Conditional branches, AF' ownership, exact EOF and the caller ABI are unchanged.

```powershell
python -m lzsa build --profile fast-block --fast-jumps --core 0x8000 --core-limit 0x8100 --output build/lzsa-fast-jumps
```

Real resident CPU 17,767,606 ->17,765,094 T (-0.014138%); ordinary coroutine
19,412,006 ->19,407,004 T (-0.025768%). It combines with the applicable existing
long-copy/near-literal/restore-compare options. Both partial-input guard modes
retain waits, slices and sector reads. [Counts, rejected cold-wrapper trial
and full regression scope](../OPTIMIZATION_PLAN.md#item30--unconditional-branch-speed-policy-2026-10-19).

## Optional measured Fast branch layout

`lzsa.block.build(branch_tuned=True)` and
`lzsa.resumable.build(branch_tuned=True)` choose conditional JR/JP forms from
the complete real-input frequencies. Add CLI `--branch-tuned` for either Fast
profile; Small remains independent. The option combines with `fast_jumps`.
Conditions/flags, data format, exact EOF, input guards and coroutine ABI stay
unchanged; relative branches are checked at generation time.

With `fast_jumps=True`, 21 real resident blocks improve 17,765,094 ->17,714,484 T
(0.284885%), 219 ->220 bytes. The ordinary coroutine improves
19,407,004 ->19,356,394 T (0.260782%), 386 ->387 total bytes. All real blocks
improve; 17 directed cases per profile are 3..8 T slower, and some slices are
slower. Defaults are unchanged. This optional intermediate gain does not
complete the user's separate 10% goal. [Complete candidate counts](../evidence/ten_percent_tuned_branches.json).

## Optional pre-normalized nibble cache

`nibble_prefill=True` / `--nibble-prefill` normalizes each spare low nibble in
AF' during refill, allowing cached entries to skip their final OR F0h. It
costs +3 T on refill, saves 7 T on the cached entry and adds four code bytes.
Carry phase, raw-v2 data, exact EOF and suspension/IRQ requirements remain
unchanged. Small does not accept it. It combines with existing Fast options.

With fast_jumps and branch_tuned, complete real resident CPU improves
17,714,484 ->17,635,500 T (0.445872%), 220 ->224 bytes. The ordinary coroutine
improves 19,356,394 ->19,277,410 T (0.408051%), 387 ->391 bytes. Unmatched
final refills and some slices are 3 T slower, so the option stays explicit.
[Native, guarded-input and compatibility evidence](../NIBBLE_PREFILL.md)
records all cases. This smaller gain does not complete the active 10% goal.
