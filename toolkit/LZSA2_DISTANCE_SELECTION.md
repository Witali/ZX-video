# Fixed-command LZSA2 distance selection

2026-09-30, baseline `ca95df5`. This follows the exact short-input oracle;
it is a bounded host-compressor experiment, not a player release.

## Result and decision

**Do not integrate this pass or expand it to a full-movie search.** On one
complete 15872-byte block, changing match distances saves only **108 Z80 T**
at the same compressed size. This is 0.0114% of that block's decoder work,
or 0.00056% of the saved 21-block stream's decoder work. It does not explain
or close the gap to smooth five-level 25/3 fps.

The selected block is index 11 (zero-based): its first 128 bytes supplied
the promising short-reset example in [the oracle study](LZSA2_EXACT_ORACLE.md).
Keep the full block's history and command boundaries here; the short example's
480-T gain did not predict the benefit of this more restricted full-block pass.

| Measurement | Baseline | Candidate | Difference |
| --- | ---: | ---: | ---: |
| Block payload bytes | 7165 | 7165 | 0 |
| Block encoded nibbles, before final byte rounding | 14329 | 14330 | +1 |
| Block token-body T | 864303 | 864195 | -108 |
| Complete block decoder T, including quota/wrappers | 944426 | 944318 | -108 |
| Complete video stream bytes, including headers | 154956 | 154956 | 0 |
| Complete stream decoder T | 19412006 | 19411898 | -108 |
| Producer T, excluding ROM and physical disk | 1058423 | 1058423 | 0 |
| Decoder + producer T | 20470429 | 20470321 | -108 |
| Video sectors | 606 | 606 | 0 |

The original parse already has the minimum **14329 nibbles** for these
fixed command positions and lengths with canonical offsets. The candidate
uses the spare half-byte in the final rounded byte to reduce CPU work.
It changes 320 distances, mostly at equal cost. No decoded byte, native
instruction, runtime RAM allocation or block boundary changes.

## Search scope and cost accounting

[optimize_lzsa2_distances.py](optimize_lzsa2_distances.py) retains all literal
and match positions and lengths. It enumerates every valid prior source
for each complete match, including overlapping copies. In this block there
are 2194 match commands and 75520 candidate distances.

The forward dynamic program retains `(last distance, used nibble count)`.
Nibble parity gives the decoder's reservoir phase. A backward minimum-size
bound prunes paths that cannot finish within the original physical byte
budget. For each used-size state, two best distinct prior distances suffice
to find the cheapest non-repeat predecessor; repeat predecessors are kept
separately. There is no beam width or candidate cap. The peak is 370 states
and the pass evaluates 153219 transitions.

This is a minimum-token-CPU search **within this scope**, not a globally
optimal LZSA2 compressor. It excludes moving/splitting matches, changing
literal runs, external dictionaries and noncanonical wider offset encodings.
Those can be legal format choices but were not searched. Tie-breaking may
change an offset without improving cost.

[lzsa2_distance_cost.py](lzsa2_distance_cost.py) executes each token class
on the independent full-flags Z80 core, using the unchanged assembled
decoder. Classes include literal thresholds 3/18/256, match thresholds
9/24/256, all eight XYZ modes and both nibble phases. Within a length class,
each extra copied byte adds 21 T. The copy-loop formulas are:

- Short/16-bit literal length: `LDIR = 21L - 5`.
- Literal length 3..255: two `LDI` plus `LDIR = 21L - 15`.
- Match length at least two: one `LDI` plus `LDIR = 21M - 10`.

Dispatch, extension parsing, stack and pointer instructions are included
in the measured class constants. The assembled instruction table cites
[Zilog UM0080](https://www.zilog.com/docs/z80/um0080.pdf). It is saved in
the CPU evidence, and the banked harness checks executed instruction timing.
Token output boundaries are unchanged, making quota/wrapper costs invariant;
the complete block measurement confirms the predicted -108 T exactly.
This model excludes ULA contention, actual AY/IRQ scheduling, TR-DOS ROM
execution and physical disk latency.

## Verification and limits

- All 3214 length/mode/phase boundary cases agree with direct native timing,
  including 15872-byte native block limits and EOD handling.
- 187 fixed-command layouts are checked against 2716 exhaustively serialized
  distance alternatives. The DP matches the best permitted CPU cost and the
  independently enumerated minimum size. Author-decoder round trips pass.
- The complete 21-block candidate passes guarded banked decoding, per-write
  input/output cursor and overlap checks, and exact sector order/EOF. Only
  block 11 changes; raw video is identical. An isolated copy of block 11
  also passes a separate short-sector retry at a fresh stream start.
- The independent full-flags core agrees on every slice. Separate synthetic
  IM1 runs inject 184 interrupts, with zero unavailable injection events.
  These verify register/state preservation, not realtime AY cadence.
- The locally built unmodified author decoder round-trips all 21 blocks.
- Root test TRD remains unchanged. No new TRD or candidate Fuse playback
  is claimed. Last actual measurement remains **7.683025 fps**, 118 missed
  nominal deadlines; the overall goal and release timing gates still fail.

## Reproduction

Use the locally built author DLL from the [oracle setup](LZSA2_EXACT_ORACLE.md).
Set `PYTHONPATH=local_tools/python_packages;.tmp/lzma-z80-packages;toolkit`.
The same archived input and metadata can be restored with the stage-profile
and borrowed-literal reproducers. Run:

```text
python toolkit/optimize_lzsa2_distances.py --stream .tmp/lzsa2-stages/video.stream --block 11 --output .tmp/lzsa2-distances
python toolkit/benchmark_row_lzsa.py --stream .tmp/lzsa2-distances/video.stream --raw .tmp/lzsa2-distances/video.raw --metadata .tmp/borrowed-literals/metadata.json --output .tmp/lzsa2-distances/cpu.json
python toolkit/verify_lzsa2_search.py --stream .tmp/lzsa2-distances/video.stream --raw .tmp/lzsa2-distances/video.raw --cpu .tmp/lzsa2-distances/cpu.json --output .tmp/lzsa2-distances/verification.json
python toolkit/verify_lzsa2_distances.py --baseline .tmp/lzsa2-stages/video.stream --work .tmp/lzsa2-distances --author .tmp/lzsa2-oracle/build/lzsa2_oracle_host.dll --output toolkit/lzsa2_distance_profile.json --evidence toolkit/lzsa2_distance_evidence
```

[Summary](lzsa2_distance_profile.json) identifies sources, inputs, native
code and unchanged TRD by SHA-256. [Compressed evidence](lzsa2_distance_evidence/)
contains the candidate stream, command decisions, banked/native checks,
cost table and exhaustive alternatives. Measured PC pass time was about
0.40 s on this machine; a single run is not a host-performance benchmark.

## Next bounded compressor experiment

Close this distance-only hypothesis. Test a few independent-block reset
positions near packet boundaries on a saved difficult window, as proposed
in [the compatible-compressor plan](LZSA2_COMPRESSION_PLAN.md). Keep raw
bytes, LZSA2 syntax and the 15872-byte native ceiling. Count added headers,
lost history, carry copies, sectors and native T before considering actual
playback integration. Avoid another whole-disk or codec sweep.
