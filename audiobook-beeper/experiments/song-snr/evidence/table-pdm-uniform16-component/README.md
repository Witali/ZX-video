# Uniform table-output resident-PCM8 component

Executed2026-10-20. This isolated native Z80 component emits sixteen equally
spaced PDM decisions per448-T PCM sample. At the nominal3.584-MHz Pentagon
clock this is128000 decisions/s and8000 PCM samples/s. It retains the existing
64-level integral packet algorithm with beta0.5, extent0.5 and zero PCM origin;
the regenerated equal-hold table has six reachable states. This is a mechanism
proof, not an audio-quality or bootable-release result.

The input is residentPCM8, mapped to the existing64 PCM levels. The whole
720384-byte song could only plausibly reside on the1024-KiB target; the512-KiB
target still requires compression or streaming. IMA decode, source-bank handoff,
EOF handling, live disk delivery, progress UI, clone contention and a complete
player RAM map are not implemented by this component.

## Register and record layout

MainBC is10FE, allowing `OUT(C),B` to emit EAR-high. MainDE is the source byte
cursor. HL is lookup scratch and then the next FIRST target; IY is the current
SECOND target. IXL carries the successor-state offset, while IXH and all alternate
registers remain unchanged. SP points into lookup records and is later dead
scratch; interrupts, calls and pushes are forbidden. Three six-byte fields are
FIRST pointer, SECOND pointer, and the word whose low byte is zero and high byte
is successor-state-index times six. POPAF loads that final offset into A.

Each packet starts with SP at record+2 and DE pointing at its current sample.
The current packet's word was selected before entry. Its FIRST routine obtains
SECOND and successor state, increments DE and prefetches the next input. Its
SECOND routine selects the next record and enters its FIRST routine. A valid
lookahead byte must follow the last sample being measured.

## Counted timing

The old Pentagon ordinary packet is449T: its sixteen holds are
36,28,28,31,24,26,22,46,22,26,22,30,31,27,34,16T. This residentPCM8 component is
448T, delta-1T. The algorithms differ in decoder work and regenerated table
weights, so this is not a drop-in equivalence or quality comparison.

Every following ED output costs12T, leaving16T between output writes. Following
immediate outputs cost11T, leaving17T. The three immediate pulses are numbered
7,9,10; A is set to0 or16 using XOR A or LD A,B, each4T. Dead `LD SP,HL` is
intentional6T padding after POPAF and before the next live SP reload. The gap
after pulse15 includes the jump to the next FIRST routine.

| After pulse | Work and padding | Gap work | Following OUT | Total hold |
|---|---|---:|---:|---:|
|0|POPHL10 + INCDE6|16|12|28|
|1|LDA,H4 + LDIYH,A8 + NOP4|16|12|28|
|2|LDA,L4 + LDIYL,A8 + NOP4|16|12|28|
|3|POPAF10 + deadLDSPHL6|16|12|28|
|4|LDIXL,A8 +2NOP8|16|12|28|
|5|LDL,E4 + LDH,D4 +2NOP8|16|12|28|
|6|LDL,(HL)7 + setA4 + deadLDSPHL6|17|11|28|
|7|2NOP8 + JP(IY)8|16|12|28|
|8|LDH,page7 + setA4 + deadLDSPHL6|17|11|28|
|9|LDH,(HL)7 + setA4 + deadLDSPHL6|17|11|28|
|10|LDA,IXL8 + LDL,A4 + NOP4|16|12|28|
|11|LDSPHL6 + POPHL10|16|12|28|
|12..14|4NOP16|16|12|28|
|15|3NOP12 + JP(HL)4|16|12|28|

The259 gap-work T consist of139 useful and120 padding T; output instructions
cost189T. The available padding is only an aggregate budget: it does not prove
that IMA decoding, paging or UI can be fitted into the same slots and registers.
In particular indexedPOP14 and indexedADD15 cannot simply be inserted in these
strict28-T gaps. Copies between H/L and IY bytes must go through A; direct
prefixed H/L forms act on the index bytes instead. Both hazards are excluded
from the generated kernel and checked by actual native execution.

## Verification and memory

The script executes all1536 PCM8-by-reachable-state combinations as one-packet
cases, checking exact packet bits, successor state, next target, SP and source
cursor. A16383-sample varied trajectory crosses63 ordinary source-byte pages
inside one16-KiB source region. Across286704 actual OUT callbacks every interval
is28T and every sample lasts448T. RAM is unchanged and alternate-register guards
are exact. Frozen bits/timestamps and source bytes are retained with hashes.

There are97 FIRST and88 SECOND routines, together8132 bytes including a final
unused NOP. Allocated lookup pages occupy16384 bytes but only2304 record bytes
are used; the high-byte PCM map is256 bytes. Total component fixed allocation
is24772 bytes, before the rest of a complete player and loader. No bank handoff,
EOF transition, installed-Fuse run, physical-hardware result or quality claim
is implied by these flat native CPU checks.

Reproduce from the worktree with the existing Python runtime and project
dependencies: run `audiobook-beeper/experiments/song-snr/table_pdm_uniform16.py`.
The manifest covers every retained artifact; the producer and both directly
imported project dependencies are frozen alongside the generated assembly.
