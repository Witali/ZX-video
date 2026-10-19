# Precision-player pipeline fragments

2026-10-19. This bounded experiment studies available registers and scheduling
inside the current FIRST/SECOND pipeline. It does not implement a full16-bit
modulator, alter an original source, or build a disk.

The assembled standalone probe passes11160 cases:124 actual model-B SECOND
patterns, two phases, ordinary/page/bank cursors, three compressed-byte values,
and five implementations. It checks every emitted bit, register guards,
prefetched nibble, source cursor, lookup SP, phase carry and descriptor cursor.
The CPU model is uncontended Pentagon; it does not model physical disk, ULA,
extended-bank hardware, UI, NMI or a complete player.

## Register and padding results

At the FIRST suffix, main HL and AF are dead. Main C remains FE and D16;
main E is feedback, IX is the predictor, IY is the SECOND entry and SP is a
lookup pointer. Alternate HL is the decoder row and DE the source cursor.
Alternate BC dies after `ADD IX,BC` until the next FIRST `POP BC`.

The ordinary main B value is only the high byte of a ULA output port. It can
be scratch on the uncontended Pentagon; each legacy bank release explicitly
replaces B with its last pulse bit. Arbitrary B is not authorized for the
address-dependent ULA waits of the128/Scorpion paths.

The nominal26-T shared pacing delta contains10 T of extra jump overhead and
only16 T of actual body work. Current optional448 pacing has a15-T body.
The following449 alternatives have exactly the old absolute34-T suffix:

| Sequence | Count |
|---|---:|
| Caller JP10 + four NOPs16 + JP(IY)8 |34 T|
| Caller JP10 + LD B,IXL8 + two NOPs8 + JP(IY)8 |34 T|
| Caller JP10 + EXX4 + LD C,IXL8 + EXX4 + JP(IY)8 |34 T|
| Inline EXX4 + LD B,A4 + LD C,IXL8 + EXX4 + INC HL6 + JP(IY)8 |34 T|

The inline form copies the exact predictor into alternate BC, using A=IXH
on entry. It grows each FIRST suffix by five bytes; a138-pattern dictionary
would grow690 bytes. The loaded alternate value lasts through SECOND but
does not survive the following decoder POP. The B and alternate-C probes
are separate alternatives, not an integrated new selector.

## Cached compressed byte and uniform regular-page advance

The LOW prefetch currently reads a whole compressed byte and discards its
high nibble. `LD B,A` caches the byte for4 T; removing a later NOP pays it.
HIGH then uses `LD A,B`4 instead of EXX4/LD A,(DE)7/EXX4, saving11 T.

Replace HIGH's `INC E`4 and page-branch JP10 with:

```
INC DE       ; 6
INC D        ; 4
DEC D        ; 4: restored D0 identifies bank wrap in C000..FFFF
JP Z,bank    ; 10
```

This adds10 T on ordinary high packets and removes the14-T page-only path,
without destroying the already extracted code in A. Its ordinary high total
therefore falls by one T. LOW falls by one T by replacing a ten-T dummy JP
with `RET C`5 plus NOP4. The RET is provably untaken: AND15 followed by two
RLCA instructions always leaves carry0; no intervening instruction changes
carry. It never reads the lookup SP.

| Fragment from pacing entry through SECOND | Old | Cached/uniform |
|---|---:|---:|
| LOW |242 T|241 T|
| HIGH ordinary |242 T|241 T|
| HIGH regular page |256 T|241 T|
| HIGH bank |485 T|470 T|

With the unchanged remainder of the current449-T packet these differences
derive448 T for ordinary packets and regular pages. Bank packets still need
677 T: an explicit229-T extra. No complete constant448-T transport is proved.

The high-half pulse intervals change from22/26/22/30/31/27/34 to
22/26/22/30/20/27/44 T. The bank's final hold changes277 to273 T. Thus the
large bank hold remains; a matched modulator and quality validation are
required even though every emitted literal bit matches in these fragments.

The source-memory experiment changes FFFF from AB to DC after LOW cached it.
HIGH still extracts AB's original high nibble, then advances to the next
source descriptor. This proves an early-paging window for the source byte;
it does not implement the descriptor prefetch/microsequencer needed to use
that window without a bank hold.

## Reproduction

```powershell
python audiobook-beeper/experiments/song-snr/sdm16_pipeline.py `
  --output .tmp/reproduced-sdm16-pipeline
```

The frozen generator, original routine snapshots, complete generated assembly,
assembler log, listing, binary, event examples and numerical report are saved
here and indexed by `manifest.json`. No full-corpus render or Fuse run was
performed because an integrated precision mechanism is still absent.
