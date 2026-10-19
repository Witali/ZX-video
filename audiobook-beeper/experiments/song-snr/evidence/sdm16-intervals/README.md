# Exact full-input B interval representations

2026-10-19. This experiment preserves the complete model-B mapping from
signed PCM16 and feedback state to its sixteen output bits and next state.
It changes no encoder, packet model, source clock, player, or disk image.
The authenticated input is the complete `model-b-all-pcm16-cells.npz` from
the preceding architecture audit; its SHA256 is recorded in `report.json`.

Closure from state16 contains18 states. Every one of the1,179,648 reachable
PCM16/state cells is reconstructed exactly. The one-LSB37/38 eight-packet
trajectories also match the independent Fraction recurrence. Four focused
tests pass; `focused-tests.log` contains the actual output.

## Representations

The direct high-byte map has4608 leaves and9853 constant-record intervals.
At most six record intervals occur inside one256-input leaf. Exact leaf
deduplication still requires41589 bytes including the record dictionary;
relative-threshold deduplication requires45231 bytes. These formats are
retained as measured controls, not as accepted resident players.

Separating output words from successors leaves2558 constant-word intervals.
Inside them, successor changes are monotonic:2270 qcode changes of+2 and555
recent-state changes of+1. The qcode changes can be computed exactly rather
than stored. Only the555 recent-state cutoffs remain explicit.

The compact representations use the following data:

| Component | Compact C | Inline C |
|---|---:|---:|
| Global word interval descriptors |11342 B|11342 B|
|1124-word dictionary |3372 B|4496 B|
|372 distinct-area C parameters |744 B|included above|
| Original-state to compact-row map |32 B|32 B|
| State by high5 root pointers |1152 B|1152 B|
| Total table bytes |16642 B|17022 B|

The high5 roots cover2048 inputs each and require at most11 word descriptors
per root. High4 roots reduce these totals to16066/16446 bytes but require up
to15 descriptors. High6 roots need17794/18174 bytes and up to8 descriptors;
high8 roots need24706/25086 bytes and up to5. These totals exclude selector
instructions, alignment, literal-to-pattern conversion, decoder, startup,
worker, UI, screens, TR-DOS workspace, stack, and audio storage. They are not
a complete RAM fit or an execution-time proof.

## Serialized layout

`state-index.bin` maps original state IDs0..31 to compact rows; unreachable
IDs contain255. The row order is `report.json`'s `reachable_states`.
`hybrid-root-highN.bin` contains little-endian u16 byte offsets indexed by
compact state row and the high N bits of the biased unsigned input.

Each interval descriptor contains a little-endian inclusive u16 endpoint
and a u16 payload. Payload bits0..10 select a word dictionary record; bit12
is the initial recent-state bit; bit13 announces an additional little-endian
u16 absolute input cutoff at which recent changes from0 to1. Traverse4 or6
bytes to the following descriptor if the input exceeds its endpoint.

For compact C, bit11 is the high bit of the area ID. A dictionary record is
`word16` in big-endian order followed by the low8 bits of the area ID. The
parameter table contains a little-endian u16 C for each sorted distinct
weighted area. For inline C, bit11 is unused and each dictionary record is
a big-endian word followed directly by a little-endian u16 C.

For a selected word, its weighted area is the sum of the original449-T
packet holds at its set bits. Define

```
C = ceil(65536 * weighted_area / 449 - 256)
d = signed16((unsigned_PCM16 - (C mod 65536)) mod 65536)
qcode = original_state // 2 + (d >> 9)
next_state = 2 * qcode + recent_bit
```

All selected reachable differences lie in[-6822,7333], with qcode1..15.
Thus neither a negative-C exception flag nor clipping is necessary on this
verified reachable domain. This is an exhaustive data result; the separate
native qphase experiment counts the arithmetic instructions and their guards.

## Reproduction and limits

Run from the research worktree with its existing dependencies:

```powershell
python audiobook-beeper/experiments/song-snr/sdm16_intervals.py `
  --output .tmp/reproduced-sdm16-intervals
python -m unittest discover -s audiobook-beeper/experiments/song-snr `
  -p test_sdm16_intervals.py -v
```

Frozen generator/test sources are in `sources/`. The generated report and
binary dumps preserve every measured representation. `manifest.json`
indexes those artifacts and the added reproduction material.

The first run is retained separately in `../sdm16-intervals-attempt-1`.
Its complete-domain decoders passed, but the final root witness reader used
a shadowed Python dictionary variable and failed an assertion. That reader
was corrected and the complete experiment was rerun successfully. The failed
traceback and partial dumps remain explicit evidence; they are not a passing
experiment.

No source-specific palette, lower-bit truncation, new timing assumption, or
quality claim is introduced. A complete selector, memory allocation and own
clock playback proof remain required before this becomes a player change.
