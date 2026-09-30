# Exact short-input LZSA2 oracle

2026-09-30, baseline `a63043a`. Follow the completed wider-search experiment
with a finite reference check. Preserve LZSA2 syntax, decoded video, native
player and independently bootable disks. The overall smooth five-level
25/3-fps goal remains incomplete.

## Result

**No size gap was found on 1341 tested inputs.** The existing author encoder
matches the exact minimum byte length on every case in this corpus. This is
not a proof of optimality on 15.5 KiB blocks or other arbitrary inputs.
Do not replace it with the oracle or continue increasing search constants
without a concrete counterexample.

The comparison exposes **232 different equal-sized parses**. Measured with
the unchanged Z80 decoder, 20 oracle parses are faster, 24 slower and 188
equal. Seven faster cases are saved video excerpts. Thus byte-optimality
does not settle decoder cost, and fewer commands is not a sufficient timing
model. Example: a 128-byte excerpt at the start of video block 11 requires
**8784 -> 8304 T (-480, 5.46%)**, with identical compressed byte length.

The sum of best-of savings on these independently reset short inputs is
2786 T. **It is not a saving for the full video stream.** Each example has
fresh offset/nibble state and its own EOD; these blocks cannot simply be
spliced into the existing stream without losing history and adding overhead.

## Exactness and scope

[lzsa2_oracle.py](lzsa2_oracle.py) is an original reference implementation.
It enumerates all valid match offsets/lengths, including overlapping copies,
with minimum length two. The default explicit input bound is 256 bytes;
the search corpus uses 1..128 bytes. There is no beam width or heuristic
candidate limit.

The dynamic-programming state is `(position, last offset, pending literal
length)`. Literal length saturates at 256 because further literal bytes add
no additional length-field transitions within the supported raw-block bound.
Each position retains every such state with its least nibble cost. Equal
costs prefer fewer commands; this tie-breaker is **not** a Z80 optimization.

Costs include literal thresholds 3/18/256, match thresholds 9/24/256, offset
classes, repeat offsets and the repeat-offset raw EOD used by the upstream
writer. Cost is accumulated in four-bit units and rounded to bytes only at
the end. Nibble sharing is therefore preserved across command boundaries.
Canonical shortest offset/length encodings suffice for minimum byte size;
noncanonical longer encodings cannot improve that objective.

A literal transition preserves its own last offset and pending literal
length. A match closes the literal run, so its non-repeat predecessor may
be selected from the cheapest state at that position; its repeat predecessor
must instead have the matching previous offset. This reduces redundant
transitions without dropping a size-relevant state. The serializer asserts
that the computed nibble cost predicts its actual byte length.

## Verification

- **1022 binary inputs:** every nonempty binary string through length nine.
- **256 deterministic inputs:** repeated patterns with seeded mutations,
  lengths 32/48/64/96/128.
- **63 video excerpts:** three independently reset 128-byte excerpts from
  each of the 21 saved blocks; these are not representative playback runs.
- **126 exhaustive cross-checks:** every binary string through length six
  is also checked by a separate enumeration of complete command lists,
  comparing actual serialized byte lengths instead of DP cost.
- **30 serializer edges:** literal/match thresholds, long copies, overlapping
  distance-one runs, offsets around 32/512/8704 and maximum native block size.
- Every oracle payload passes both the original-author C decoder and the
  independent host parser. A locally built DLL reproduces all 21 archived
  full-block baseline payloads before it is used as the author reference.
- **531 native cases:** both sides of every changed parse, a fixed unchanged
  sample and all serializer edges. Bank guards, input cursors, in-place
  layout/overlap, sector order, exact EOF and a short-sector retry pass.
  An independent full-flags Z80 core agrees on every decode slice.

The pinned upstream checkout remains clean at
`15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5`. The C wrapper calls its unmodified
raw LZSA2 ratio encoder and decoder; no downloaded executable was introduced.
The new host writer is tested independently, but is not part of a production
converter or image builder.

## Next bounded optimization

On **one complete difficult block**, keep the current literal/match positions
and lengths, search alternative valid match distances, and prefer lower
measured Z80 cost under the original byte budget. Carry the true last-offset
and nibble state through the entire block, including EOD. Keep the original
payload as a fallback. This preserves the existing format and avoids turning
the whole encoder into an expensive unconstrained search before evidence of
a useful opportunity exists.

Only expand a winning candidate to the other saved blocks after checking
actual command timing, overlap and stream-sector effects. A full candidate
must then pass real disk/IRQ/ULA and frame-publication timing. Current root
TRD is unchanged: its last verified 7.683025 fps and 118 missed nominal
deadlines still fail the goal. No new candidate playback rate was measured.

## Reproduction

Use the existing project Python environment and pinned `z80` module. Build
the small local author wrapper from the clean pinned source:

```powershell
& toolkit/build_lzsa_oracle_host.cmd 'C:/Program Files/Microsoft Visual Studio/18/Community' 'C:/Work/ZX-video/.worktree/three-disk-quality/.tmp/codec_sources/lzsa' 'C:/Work/ZX-video/.tmp/lzsa2-oracle/build'
$env:PYTHONPATH='local_tools/python_packages;.tmp/lzma-z80-packages;toolkit'
python toolkit/probe_lzsa2_oracle.py --dll .tmp/lzsa2-oracle/build/lzsa2_oracle_host.dll --raw .tmp/lzsa2-stages/video.raw --stream .tmp/lzsa2-stages/video.stream --output .tmp/lzsa2-oracle
python toolkit/summarize_lzsa2_oracle.py --work .tmp/lzsa2-oracle --evidence toolkit/lzsa2_oracle_evidence --output toolkit/lzsa2_oracle_profile.json
```

The raw fixture is also archived in `row_lz4_evidence/video.raw.gz`; the
baseline stream is in `row_lzsa_evidence/video.stream.gz`. Reuse those if the
temporary directories are absent. The [summary](lzsa2_oracle_profile.json)
and [evidence](lzsa2_oracle_evidence) record every input, both payloads,
minimum-cost parse, selected cycle counts, source hashes and native results.
The DLL and build products remain temporary.
