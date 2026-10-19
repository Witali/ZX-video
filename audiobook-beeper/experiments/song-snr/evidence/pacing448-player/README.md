# Optional448-T Pentagon pacing CPU proof

Date:2026-10-19. Baseline producer:5d10036c. This is a bounded player
mechanism proof, not an audio-quality result or a full Fuse/hardware release.
The root research experiment evaluates source-clock sound separately.

The `pentagon_ordinary_tstates=448` model flag changes only the six-byte
`hardware_delay` implementation. Absent and explicit449 settings reproduce
the prior complete disk and metadata exactly, with the UI both off and on.
Malformed values and use in the unsupported legacy direct builder fail
before output creation. Table-generation weights remain explicit and may
intentionally differ from physical timing in a causal control: these proofs
use identical449-T table weights and source bytes before and after the448-T
hardware change. The opt-in metadata states that difference.

| Path | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Stub body | four NOPs:16 T | LD A,R:9 T + INC HL:6 T | -1 T |
| Pentagon ordinary packet |423+JP10+stub16=449 T|423+JP10+stub15=448 T|-1 T|
|128/Scorpion ordinary packet|423 T|423 T|0 T|
|Page-tail extra|14 T|14 T|0 T|
|Bank-tail extra128/Pentagon|243 T|243 T|0 T|
|Scorpion bank-tail extra|267 T|267 T|0 T|

The final JP(IY),8 T, replaces the same original JP(IY), so it does not enter
the added-pacing count. Old stub bytes are `00 00 00 00 FD E9`; new bytes are
`ED 5F 23 FD E9 00`. The final zero is unreachable padding. Every address,
source descriptor, lookup, worker boundary and audio RAM allocation stays
unchanged. Cold `stream_patch_first` writes JP `hardware_delay` only for
cache_mode>=2;128/Scorpion continue executing their old direct JP(IY).

At FIRST exit, main HL is dead packet-pointer scratch. SECOND overwrites it
with POP HL before using it. A/F are also dead: SECOND first swaps them out
to read the saved phase/code from AF', then swaps back and overwrites A with
LD A,(DE), F with AND, before either controls data or a branch. The saved
AF' phase/code, predictor IX, second pointer IY, lookup SP, BC and DE remain
intact. LD A,R obtains a refresh-register value and puts IFF2 in PV; neither
value reaches a meaningful operation. The new body has one fewer M1 fetch,
so its evolving R differs; the proof deliberately seeds R0/127/128/255 and
both IFF2 values. Maskable live interrupts remain disabled. This does not
claim resilience to an external NMI.

The six-test final run passed in54.967 seconds. `report.json` records:

- 3,552 literal-path executions in1,776 before/after pairs: all130 FIRST and92 SECOND bodies,
  both nibble branches and all four RAM profiles. Each assembled old/new
  pair preserves all source bits, AF/AF'/IX/IY/SP and other register values,
  IFF1/IFF2 and every RAM byte. Only Pentagon slot7 shortens by1 T.
- 32 directed page/bank cases, each executing before and after: both last
  literal bits, four profiles and UI off/on. Page path52 T; bank281 T or
  Scorpion305 T through the next JP(HL). All register and permitted-memory
  guards pass; the UI may change its two intended green attributes.
- Eight complete16,640-byte native executions, including page and bank
  handoffs. Every source bit, predictor, index and continuous interval
  matches independently generated expected data. No ROM calls or refills.
- The maximum one-TRD payload,2392 sectors/612352 bytes, cold-loads correctly
  for all four profiles. Pentagon1024 loads all bytes. Worker end isBFE0,
  leaving31 bytes before the reservedBFFF byte. Loading/progress dispatch
  remains present. The full-bank native UI interval becomes4.096313895 s.

Native CPU checks exclude real128/Scorpion address-dependent ULA waits and
physical floppy latency. Page/bank extras still prevent a perfectly uniform
8-kHz schedule. No SNR, AM/FM, background-noise or complete-source acceptance
claim follows from these tests alone.

Two test-harness corrections preceded the final run: a breakpoint on the
same FIRST entry needed an independent stop pointer to count its initial
OUT, and the two-attribute UI handoff needed both intended cells admitted
by its memory guard. Neither correction changed any player/encoder source.

Reproduce from the worktree root with the project's Python dependencies:

```powershell
python audiobook-beeper/test_pacing448.py --output .tmp/reproduce-pacing448-player
```

`sources/` freezes the final producers/test. `prior-producer/` contains the
exact prior sources read from Git. Assembly, disks and short native reports
are retained under449/,448/,native/ andmaximum/. `manifest.json` records
SHA256 and byte count of every retained file except itself.
