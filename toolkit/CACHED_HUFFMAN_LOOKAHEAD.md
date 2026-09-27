# Cache two Huffman input bytes in registers

Date: 2026-09-27. Baseline: compact-cursor CPU configuration at `cb94632`.
**This report describes the CPU prototype.** The subsequent
[disk integration and full playback experiment](LOOKAHEAD_PLAYER.md)
retains these results and still fails the release timing gates.

## Register allocation

The existing player already uses both Z80 register sets. `EXX` exchanges
BC/DE/HL with BC'/DE'/HL'; `EX AF,AF'` independently exchanges the accumulator
and flags. Main reconstruction code retains its own traversal registers
while Huffman decoding uses the alternate set.

| Purpose during reconstruction | Existing allocation | Prototype allocation |
|---|---|---|
| Current Huffman byte | B' | B' |
| Huffman bit position | C' | C' |
| Next Huffman byte | Indexed read for each symbol | E' |
| Motion output cursor, phases 2/4/6 | DE' | HL' |
| Decoded short symbol / initial long-code rank | E' while decoder is active | AF' temporarily |

AF' refers to the accumulator swap instruction, independent of `EXX`.
Its temporary use is safe only because these Huffman callers have no live
AF' value and the AY interrupt preserves it. Output routines later reuse
alternate registers for their own purposes; the next reconstruction
initializes the Huffman cache again.

Short-return flags also change: the final exchange restores flags held with
the prefix lookup, rather than the old OR F8h flags. Existing callers set
their own flags before dependent branches (for example SLA for the next
mask bit, XOR for attributes or arithmetic for the next tile). A new caller
must not assume that this primitive preserves AF' or returns a particular Z.

[The implementation](cached_huffman_lookahead.py) patches complete instruction
sequences and validates their original bytes. Motion replaces 117 register
operations in its three nonzero phases. Their sizes and T-states are
unchanged. Primary DE still reads the motion cache. These changes do not
alter Huffman codes, motion vectors, frame data or the native renderer.

## Exact instruction costs

The current shared bitmap short-code primitive costs **145 T** without a
byte crossing and **169 T** with a crossing, including RET and excluding
the caller's CALL. The prototype costs **134 / 162 T**: **-11 / -7 T**.
The attribute entry costs one T less in both implementations.

The indexed lookahead load `LD L,(IX+1)` costs 19 T. Reusing E costs 4 T,
saving 15 T. Holding the decoded symbol with `EX AF,AF'` adds 4 T relative
to the previous result handling: net **-11 T**. On a byte crossing,
`LD B,E; LD E,(IX+1)` costs 23 T versus the old 19-T B refresh: net **-7 T**.

Long codes keep the canonical fallback. Its entry saves the rank with
`EX AF,AF'; INC IX; PUSH AF` (**25 T**) instead of
`INC IX; LD B,E; PUSH BC` (**25 T**). The existing POP AF then recovers the
rank; the following SLA B sets the flags used for the next bit. The final
cache refresh plus return grows **29→58 T**. Including the common 11-T
saving, a long code costs **18 T more**. The absolute baseline depends on
length, bit offset and table carry; all old/new counts are saved in the
[exhaustive case report](cached_huffman_lookahead_cases.json).

Frame setup grows **19→65 T (+46)**. Therefore each frame's exact delta is:

```text
46 - 11 * short_inside - 7 * short_cross + 18 * long
```

Short code addresses, total region length and the **875-byte** bank-6 inline
patch body are retained. One **7-byte** refresh helper occupies fixed bank 2
at **8FC0..8FC6**, after reconstruction state ending at **8FB8** and before
the renderer at 9000. The setup CALL temporarily needs two more stack bytes
than the old setup load. No interrupt-disabled section or new data-copy
loop is introduced. Instruction timings use the same
[Zilog table](https://www.zilog.com/docs/z80/um0080.pdf) as earlier work.

## Packet boundary requirement

This cache requires **two readable lookahead bytes**, even for empty coded
input. A final byte crossing may refresh E beyond the first guard, although
that second byte does not contribute to any valid decoded symbol. The
guards need not be zero: exhaustive cases use **A5/3C**. A test deliberately
providing only one guard fails, proving that the requirement cannot be
silently inherited from the previous decoder.

At the prototype baseline, the FAP3 disk parser guarantees one final guard. The standalone
frame fixture provides `coded + guard + literals + guard`, so it already
satisfies the new requirement. **Passing that fixture does not verify the
integrated parser.** The player must reserve a second readable byte before
this optimization can be enabled there.

The [input auditor](audit_cached_huffman_lookahead.py) checks all 4221 actual
packets. Maximum payload sizes are **2638 / 2921 / 3645 bytes**, below the
proposed **4702-byte** payload limit in the unchanged 4704-byte packet window.
All current packets fit. There are **2635 packets without literals** and
**44 without coded values**, so empty-tail behavior matters. For other
videos, an oversized packet must retain the old decoder or be rejected by
the optional configuration; it must not overrun the window. Reserving an
extra readable byte need not add a byte to the compressed stream or copy it.

## Complete CPU-stage result

All **4221 frames** pass exact compact-frame and both complete native-screen
comparisons. Every frame's cycle delta matches its actually executed short
and long symbol counts and the formula above.

| Volume | Frames | Baseline T | Prototype T | Delta T |
|---|---:|---:|---:|---:|
| 1 | 1624 | 386925436 | 385003910 | -1921526 |
| 2 | 1297 | 328284145 | 326528010 | -1756135 |
| 3 | 1300 | 308154748 | 306517321 | -1637427 |
| **Total** | **4221** | **1023364329** | **1018049241** | **-5315088** |

This is **0.5194% less CPU work in the measured frame stages**. There are
**55 slower frames** (15/14/26 by volume), with maximum penalties of
**46/46/50 T**. Their setup/long-code costs are included, not discarded.
The totals exclude ZX0, queues and packet copying, AY/IRQ cadence, ULA,
TR-DOS ROM and physical disk latency. They do not predict a matching
improvement in publication timing. See the [audited summary](cached_huffman_lookahead_summary.json).

**Prototype decision:** retain it for integrated measurement.
This CPU experiment built no TRDs or full disk playback; the previous
nominal-deadline, fallback-jitter and AY-continuity failures remain open.

## Verification and reproduction

[Five tests](test_cached_huffman_lookahead.py) cover all candidate codes at
eight bit offsets, mixed complete frames, all motion register rewrites,
empty input, the required second guard, and real AY interrupts after every
instruction in mixed-frame and long-code exercises. Actual player AY/IRQ
handlers preserve both register sets, AF', pointers and stack in those
tests. They do not measure 50 Hz delivery cadence.

The exhaustive volume audit executes **68,712 paired cases**: every used code
in each of the three actual table sets at all eight bit positions. Values,
bit cursors, both cached bytes, stack and instruction timings match.

The [full-frame benchmark](benchmark_cached_huffman_lookahead.py) supplies
packets from the host and compares exact compact frames and both complete
6912-byte native screens with saved states. Every instruction and each
frame's delta are checked; symbol-path counts must match the earlier
complete baseline. Its [report](cached_huffman_lookahead_cpu.json) states
coverage explicitly. The [saved-evidence auditor](summarize_cached_huffman_lookahead.py)
checks hashes and arithmetic without repeating Z80 or playback execution.

From the measured worktree, with the existing Python dependencies:

```powershell
python -m unittest test_cached_huffman_lookahead -v
python toolkit/audit_cached_huffman_lookahead.py --raw-directory ../volume-huffman/.tmp/probe
python toolkit/benchmark_cached_huffman_lookahead.py --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz
python toolkit/summarize_cached_huffman_lookahead.py
```

The raw inputs and source states are local fixtures, not bundled by this
experiment. A six-frame smoke run checked exact pixels/cursors with
**-6066 T** against **1487678 T**; it is explicitly incomplete.

## Corrected attempts and integration gate

The initial 8FB0 helper placement was rejected because actual reconstruction
ends at 8FB8. It moved to 8FC0. An early long-path trampoline was assumed to
add 32 T, but executed cases measured **42 T**; the missing 10-T jump was
caught by the cycle assertion, including the partial movie smoke. Replacing
that trampoline with the equal-size PUSH AF sequence reduced the final
long-code delta to **18 T**. No failed intermediate variant is enabled.

The follow-up required before adoption was to integrate the two-readable-byte packet
contract, regenerate cold-installed code including inline patches, verify
dirty-RAM independent boots and disk swaps, and remeasure all three volumes
through EOF. Count bootstrap sectors, IRQ/ULA effects, queue CPU, ROM and
disk latency. Check nominal deadlines and fallback recovery separately,
and retain AY at every 50 Hz interrupt. That integration and its remaining
timing failures are now recorded in [the disk report](LOOKAHEAD_PLAYER.md).
Existing release TRDs are unchanged.
