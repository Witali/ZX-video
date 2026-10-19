# Smaller and faster LZSA2 coroutine target synchronization

Measured 2026-10-19 against `841bf955`. This bounded experiment contributes
to the user's faster-and-smaller direction. It does not complete the separate
approximately 10% speed goal or select a player default.

`lzsa.resumable.build(compact_sync=True)` / CLI `--compact-sync` replaces
the cold quota synchronization. Existing raw-v2 data, hot field decoding,
coroutine yields, input guards and EOF handling stay intact. Resident-block
profiles have no synchronization wrapper and reject the CLI option.

The old helper loads target into HL and block end into DE, subtracts them,
then reloads target to patch the quota operands. Ordinary requests later
load target into DE again. The new helper loads end into HL and target into
BC; only the equality result of `SBC HL,BC` is live. It patches operands from
B/C directly. Ordinary mode first copies BC into DE for the request's output
comparison. Streaming restores the decoder frame immediately and needs no
target copy. Both callers overwrite the dead HL difference. BC is scratch
before begin or before the saved decoder frame is restored; pending decoder
counts, AF' nibble cache and caller stack are unaffected.

If target equals block end, BC becomes FFFFh for the patched quota sentinel,
allowing the decoder to read raw EOF. Ordinary DE retains the actual target.
The opposite subtraction direction changes dead carry/sign flags; equality
is unchanged, and the subsequent ordinary comparison clears carry first.

| Selected previous wrapper | Code difference | Begin difference | Ordinary resume difference |
| --- | ---: | ---: | ---: |
| Default target reload | -5 bytes | -8 T | -28 T |
| `restore_compare=True` | -3 bytes | -3 T | -23 T |

Streaming removes the entire target restoration: -3 bytes/-16 T per call
versus default, or -1 byte/-11 T versus restore_compare. When both options
are enabled, compact_sync replaces the older restore_compare calculation;
metadata records this explicitly. Existing defaults and old option bytes
remain unchanged.

The helper's standalone regular/final costs are 119/124 T ordinary and
111/116 T streaming. Old reload costs are 127/132 T, or 122/127 T with
restore_compare. `LD HL,(nn)` is 16 T; `LD BC,(nn)` and `LD DE,(nn)` are 20 T;
register moves are 4 T; `SBC HL,rr` is 15 T. Calls/returns and the 7/12-T
equality branch retain their previous costs. Ordinary requests additionally
remove a 20-T DE reload. Unit tests execute all 65,536 target words at two
block ends in each input mode: 262,144 exact sentinel/equality/cycle checks.

| Complete 21-real-block profile | Before | After | Saved | Code/state bytes |
| --- | ---: | ---: | ---: | ---: |
| Default ordinary coroutine | 19,412,006 T | 19,376,978 T | 35,028 T / 0.180445% | 384 -> 379 |
| Same + restore_compare | 19,405,676 T | 19,376,978 T | 28,698 T / 0.147885% | 382 -> 379 |
| Fast jumps, tuned branches and nibble prefill | 19,277,410 T | 19,242,382 T | 35,028 T / 0.181705% | 391 -> 386 |
| Same + long_copy, near_literals, restore_compare | 19,245,702 T | 19,217,004 T | 28,698 T / 0.149114% | 472 -> 469 |

The [native report](evidence/compact_sync_native.json) includes all 95 prior
real/directed/random cases plus both single-nibble EOF forms in four profiles:
388 comparisons, each repeated with relocated code and IRQs. No block or
slice slows. Per-slice changes equal the instruction counts above. Repeated
zero and repeated positive demands preserve the saved pending BC and output
cursors. Plain observed caller/private stack peaks are 4/14 bytes; IRQ peaks
are 10/20 bytes, identical to the baseline. No stack operation was added.

Both guarded input modes pass 63 cases/six placements. CALL total CPU improves
29,484,761 ->29,452,121 T; direct improves 27,268,290 ->27,235,650 T: -32,640 T
each. All 2,670 slices per mode are no slower. Producer work, waits, carry and
772 once-only sectors stay exact. The strongest combined streaming options
also pass 65 cases/six placements/both modes, including both tiny EOFs and
IRQ replay. Old short word escapes and overlap paths remain intact.

The user caps maximum-speed service memory at 10,000 bytes, including code,
variables, tables, padding, stacks and internal scratch/buffers; external
compressed input, output and match history are separate. This experiment adds
none of those allocations. Its conservative measured-profile accounting
includes decoder code/state, separate 128-byte caller/private stack ranges
and the 13-byte benchmark IRQ stub: 648 bytes for default, 738 bytes for
the largest ordinary profile and 833 bytes for the largest guarded profile. State is already inside code/state totals.
Tables, required alignment padding and internal buffers are zero. Observed
stack peaks do not replace an application's own IRQ stack requirement; the
guarded wrapper's static maximum is 20 private bytes before IRQ, 26 with this
six-byte IRQ stack overhead. A real application must include its own service
allocations, producer code and IRQ handler when checking its complete cap.

The first four-register-copy proposal is retained as
[a superseded complete native report](evidence/compact_sync/superseded-four-register-moves.json.gz).
It saved three bytes/20 T per ordinary request, but copying BC into HL was
unnecessary. Direct B/C quota stores save another two bytes/eight T per
sync, eliminating its +5-T begin penalty relative to restore_compare.

[Verification and archived guarded reports](evidence/compact_sync_verification.json)
bind source hashes, 33 passing library tests, 31 frozen default profiles,
six upstream resources and unchanged payload/state/stack sizes. No external
encoder, wheel reinstall, physical disk/ROM/ULA or movie timing is claimed.

Reproduction uses existing fixtures and z80==1.2.0, package/test/toolkit paths,
and TMP/TEMP inside the worktree:

```powershell
python -m unittest discover -s libraries/tests -v *> .tmp/compact-sync-library-tests.log
python libraries/tests/measure_compact_sync.py --output libraries/evidence/compact_sync_native.json
python -c "import gzip,pathlib; p=pathlib.Path('.tmp'); f=pathlib.Path('toolkit/row_lzsa_evidence'); [(p/n).write_bytes(gzip.decompress((f/(n+'.gz')).read_bytes())) for n in ('video.stream','video.raw')]"
python toolkit/test_streaming_lzsa2.py --noncanonical --stream .tmp/video.stream --raw .tmp/video.raw --fast-jumps --branch-tuned --nibble-prefill --compact-sync --output .tmp/compact-sync-call.json
python toolkit/test_streaming_lzsa2.py --noncanonical --stream .tmp/video.stream --raw .tmp/video.raw --fast-jumps --branch-tuned --nibble-prefill --compact-sync --direct-header --output .tmp/compact-sync-direct.json
python libraries/tests/measure_compact_sync_streaming.py --output .tmp/compact-sync-combinations.json
python libraries/tests/summarize_compact_sync.py --directory .tmp --output libraries/evidence/compact_sync_verification.json
```
