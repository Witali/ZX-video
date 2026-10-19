# Native full-input selector constraint

2026-10-19. This bounded prototype is complete and rejected as a direct
unchanged-clock player substitution. It implements and executes a specified
high-byte-root/binary-handler selector, rather than changing the released
player or advertising an optimality bound. The separate compact hybrid
format and successor-arithmetic studies remain distinct mechanisms.

The input is the saved actual C model-B65536×32 word/successor catalogue.
Every2097152 host cell is reconstructed exactly from generated intervals.
Closure from seed16 remains the same18 states. Native components cover all
18 reachable seeds and19676 vectors: every high-byte endpoint, every changed
interval's adjacent inputs, extremes and the signed PCM37/38 witness.
All native executions pass exact output/address, predictor, port, alternate
register, lookup-SP and no-memory-write guards. The complete run took
14.704797 s; assembler listings and binaries are retained for every seed.

## Specified representation and live ABI

Each state has two parallel256-byte root pages indexed by IXH. Each root
points to literal selector code. A nonconstant chunk loads IXL and performs
a balanced comparison tree over its exact byte boundaries. Terminal records
contain FIRST address16, SECOND address16, next-state-page8 and constant16.
The FIRST/SECOND addresses come from the independently verified zero-cycle
shared-high pattern implementation; the selector does not execute those
pattern routines here.

Main E changes meaning to `0x40+2*raw_state`, selecting the root pages.
The selector reads all16 predictor bits without changing IX. BC remains
the output port; D remains16 after terminal POP DE. Main A/F/HL are scratch,
while alternate decoder/source registers and AF' remain exact. SP is used
only as a lookup pointer with POP; there are no PUSH/CALL stack operations.

The entry must occur after current SECOND dispatch, while its old IY is
dead and before the phase/code EX AF. IY can then receive the future SECOND
address. This is an allocation requirement, not a completed rescheduling of
the live player: copying the selector into FIRST while old IY still names
the current SECOND would be incorrect.

## Exact instruction counts

The historical query and packet reads cost70 T:
8+4+7+7+4+6 for the input/page/SP selection, then10+14+10 for POP HL/IY/DE.
The8-T JP(IY) dispatch is outside that comparison.

| Prototype work | T states |
| --- | ---: |
| IXH/state root to JP(HL) |42|
| LD A,IXL for a variable chunk |8|
| Each CP immediate plus JP C |17|
| LD SP,record; POP HL; POP IY; POP DE |44|
| Terminal JP to caller continuation |10|
| Constant chunk before padding |96|
| Three-comparison path |155|

All shorter paths are padded to155 T using only dead A/F and NOPs. Native
tests vary R and IFF2; padding neither branches on those values nor alters
saved AF'. This removes selector branch-length variation in the flat CPU
probe. It does not establish ULA-independent timing on128/Scorpion.

There are at most six complete word/successor ranges within an IXH chunk,
requiring three balanced comparisons. Full range-count histogram is
1:1190,2:1988,3:1075,4:317,5:34,6:4. Word-only chunks are simpler:
1:2527,2:1691,3:339,4:43,5:8. Their worst case still needs three comparisons;
successor arithmetic and a different data layout must be counted separately.

Even with zero-cycle SECOND code sharing and removal of all26 Pentagon
pacing T, replacing70 T with155 T gives an ordinary508-T sample. That
exceeds the449-T target by59 T before any new selector-bank paging. These
counts reject this implementation, not every lower-bit-preserving selector.
The terminal JP is explicitly charged; no invisible return or stack call
is omitted from the bound.

For seed16, signed PCM37 and38 both select word6AD5, but successors17 and19
differ. The native result preserves this one-LSB state influence. Keeping
only a word selector without accounting for the successor would fail that
requirement.

## Memory and verification limits

Native testing loads one state's component into flat RAM at a time. Across
the18 components, the saved roots occupy9216 bytes, padded handlers207437
bytes and local terminal dictionaries32298 bytes. Local dictionaries repeat
some entries across states; these totals describe the executed component
format, not an optimal compressed global representation. Raw state-root
addresses also cross the existing5C00..5FFF TR-DOS workspace. The components
cannot all inhabit the current fixed32-KiB banks, and no bank-selection or
source-bank restoration implementation is supplied. Such work would add
counts beyond the already failing508-T ordinary path.

No boot, continuous playback, full-song encoding, Fuse, quality, AM/FM or
physical-hardware claim follows. Original player/C/Python source and all
previous experiment evidence stay unchanged.

Reproduce with the repository Python dependencies:

```powershell
python audiobook-beeper/experiments/song-snr/evidence/sdm16-selector/generate.py --output .tmp/reproduce-sdm16-selector
```

`report.json` records input/provenance hashes, all scope limits and component
totals. Each seed folder retains source, binary, listing, roots, records and
native vectors. `manifest.json` hashes every retained file except itself.
