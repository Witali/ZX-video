# Additional Z80 forum survey

Date: 2026-10-13. Baseline: `12d4eeac`, branch `codex/z80-codec-tricks`.
This completes the requested additional source search. It adds candidates
10–21 to [the optimization checklist](OPTIMIZATION_PLAN.md); it does not
claim those candidates have passed complete codec experiments.

## Coverage and the compiler hint

The user remembers a name resembling `x80cc`. Exact-name searches, the
programming topic index and additional public section listings did not
identify its forum thread. The closest verified name is **80cc / z88dk-80cc**,
an alternative compiler documented in the
[official z88dk wiki source](https://raw.githubusercontent.com/wiki/z88dk/z88dk/Tool---80cc.md).
The identification is a hypothesis; no link between this compiler and the
remembered zx-pk.ru thread has been established. Do not rename the hint or
attribute another compiler's discussion to it without evidence.

The previous nine-item pass covered selected techniques, rather than every
forum page. In this survey, requesting `pp=200` still produced at most 40
posts per **thread** page. Follow the displayed page count instead. The
54 captured pages below contain 1,778 unique post IDs. All captured bodies
were screened for assembly/optimization terms; selected technical discussions
were inspected. This is not a manual semantic review of every post.

| Topic | Captured pages at 40 posts/page | Coverage |
| --- | --- | --- |
| [ЭТЮДЫ](https://zx-pk.ru/showthread.php?t=9031&pp=40) | 1–29 | All pages captured and screened |
| [Кодогенерация SDCC: пожелания об улучшении компилятора](https://zx-pk.ru/showthread.php?t=19900&pp=40) | 1–3 | All pages captured and screened |
| [LLVM Backend для Z80](https://zx-pk.ru/showthread.php?t=20094&pp=40) | 1–4 | All pages captured and screened |
| [SDCC - Small Device C Compiler](https://zx-pk.ru/showthread.php?t=17346&pp=40) | 1–2 | All pages captured and screened |
| [Sphinx C-- для Z80](https://zx-pk.ru/showthread.php?t=29057&pp=40) | 1–2 | All pages captured and screened |
| [Язык Cowgol и компилятор](https://zx-pk.ru/showthread.php?t=35441&pp=40) | 1–2 | All pages captured and screened |
| [Ретро-ЯП Millfork](https://zx-pk.ru/showthread.php?t=35495&pp=40) | 1–4 | All pages captured and screened; many examples are 6502 |
| [Компилятор Turbo Rascal](https://zx-pk.ru/showthread.php?t=35427&pp=40) | 1 | Complete single page |
| [z80 c-- компилятор](https://zx-pk.ru/showthread.php?t=32389&pp=40) | 1 | Complete single page |
| [ccz80](https://zx-pk.ru/showthread.php?t=10236&pp=40) | 1 | One post about loading compiler output in an emulator |
| [C compiler](https://zx-pk.ru/showthread.php?t=26&pp=40) | 1 | Complete single page; historical compiler selection |
| [An 8080/Z80 C Compiler](https://zx-pk.ru/showthread.php?t=1313&pp=40) | 1 | Complete single page; historical BDS C |
| [Cross Platform C Compiler](https://zx-pk.ru/showthread.php?t=10093&pp=40) | 1 | Complete single page |
| [Алгоритм компрессора ZX0 (ZX5, ZX2)](https://zx-pk.ru/showthread.php?t=35384&pp=40) | 1 | Complete single page |
| [SjASMPlus от z00m](https://zx-pk.ru/showthread.php?t=30314&pp=40) | 1 of 18 | Partial; pages 2–18 remain |

The first topic-listing page was also screened in Programming, Software,
Graphics, Other Software, Operating Systems, News and Vector. These are
title searches, not complete readings of those sections. The original
[compression comparison thread](https://zx-pk.ru/showthread.php?t=23155&pp=40)
still has pages 2–3 outside the retained first-page capture. Other topics
outside these captures remain unreviewed. Public forum search requests
returned a human-verification form, so no exhaustive site-wide text search
is claimed.

The [coverage record](evidence/forum_research_2026-10-13.json) saves page
URLs, displayed totals, unique post counts, normalized-body hashes and
selected post IDs. It stores metadata rather than copies of forum posts.
Document hashes use UTF-8 with LF newlines to survive Windows/Git conversion.

## Source groups for candidates 10–21

- **SDCC-RMW:** [Barmaley_m, post 534511](https://zx-pk.ru/showthread.php?p=534511&viewfull=1#post534511)
  discusses indexed memory shifts, duplicate loads across pushes, storing
  results before restoring registers, and bulk initialization. These are
  historical examples, not a claim about current SDCC output.
  [The maintainer reply, post 538284](https://zx-pk.ru/showthread.php?p=538284&viewfull=1#post538284)
  explains that the selected assembler format disabled the peephole pass in
  that example; the suggested shift was already recognized by that pass.
- **SDCC-ADDR:** [Eltaron, post 540541](https://zx-pk.ru/showthread.php?p=540541&viewfull=1#post540541)
  compares constructing a pointer with direct access to a known global.
  [SfS, post 540940](https://zx-pk.ru/showthread.php?p=540940&viewfull=1#post540940)
  discusses initialized data rather than emitted per-byte initialization.
- **ETUDES-JUMP:** [Sergey, post 780551](https://zx-pk.ru/showthread.php?p=780551&viewfull=1#post780551)
  notes the possible two-T saving from changing JR to JP. The decision must
  use the actual branch condition and taken frequency.
- **ETUDES-SHIFT:** [drbars, post 872541](https://zx-pk.ru/showthread.php?p=872541&viewfull=1#post872541)
  gives alternate rotate/mask address constructions.
  [0xDEAD, post 1130519](https://zx-pk.ru/showthread.php?p=1130519&viewfull=1#post1130519)
  asks about ADD A,A versus RLA/RLCA. Equal timing does not imply equal flags.
- **ETUDES-BOUND:** [GriV, post 170101](https://zx-pk.ru/showthread.php?p=170101&viewfull=1#post170101)
  and [axor, post 170717](https://zx-pk.ru/showthread.php?p=170717&viewfull=1#post170717)
  propose bounded arithmetic using carry. The lower-bound example fails the
  native check below; do not copy it verbatim.
- **ETUDES-CMP:** [Destr, post 826005](https://zx-pk.ru/showthread.php?p=826005&viewfull=1#post826005)
  discusses extracting a sign after subtraction. Signed overflow and the
  incoming carry require a separate proof.
- **80CC-OPTIONS:** [Official optimizer option index](https://raw.githubusercontent.com/z88dk/z88dk/master/src/80cc/OPTIONS.md)
  supplies candidate families: reused addresses, narrow shifts, dead loads,
  branch threading, tail merging and block placement. Our proposed codec
  sites and priorities are inferences, not measured results from that source.
- **80CC-DESIGN:** [Official design index](https://raw.githubusercontent.com/z88dk/z88dk/master/src/80cc/DESIGN_INDEX.md)
  records a reverted loop-width optimization: a range fact attached to a
  reused virtual register incorrectly affected a second, larger loop, which
  wrapped indefinitely. Range proofs must belong to the actual loop/path.
  CPU-specific Rabbit/eZ80/Z80N opportunities cannot supply classic-Z80
  opcodes or timings without checking their availability.

## Native primitive screening

These are conditional snippet comparisons, not integrated optimizations.
The [report](evidence/forum_primitive_screen.json) and
[reproducer](tests/screen_new_forum_tricks.py) use the independent `z80==1.2.0`
core and [Zilog instruction timings](https://www.zilog.com/docs/z80/um0080.pdf).
There are no decoder changes; actual codec delta is 0 T/bytes/RAM/payload.

| Candidate | Old/new T-states | Code bytes | Checks and limitation |
| --- | --- | --- | --- |
| Indexed byte shift | 46 → 23 (−23) | 8 → 4 | 512 value/carry cases; memory, F and preserved pairs agree; A must be dead |
| Corrected decrement bounded below by 23 | 22 or 23 → 14 (−8 or −9) | 6 → 4 | All 233 inputs 23–255 agree in A; all final F values differ |
| Clear two adjacent bytes with a word store | 30 → 26 (−4) | 7 → 6 | One RAM-state probe; AF/HL clobbers and IRQ-visible ordering not qualified |

For the indexed shift, `LD A,(IX+d); SRL A; LD (IX+d),A` costs 19+8+19 T;
`SRL (IX+d)` costs 23 T. It leaves A unchanged, so a later use of A invalidates
the substitution even though memory and flags agree.

The forum's `SUB 23; ADC A,22` produces 22 when the input is 23. On the
explicit domain 23–255, `SUB 24; ADC A,23` instead computes
`max(23,A-1)` in 7+7 T. This is not an unrestricted saturation formula and
does not preserve the flags of the branch version. Inputs below 23 and a
lower bound of 255 need different handling.

The adjacent-byte example is our inference for streaming LZSA2 `begin`, where
`input_needed` and `finished` are neighboring fields. The baseline uses
`XOR A; LD (finished),A; LD (input_needed),A` (4+13+13 T). A possible
`LD HL,0; LD (input_needed),HL` costs 10+16 T. Confirm the actual field layout,
the overwritten HL, the consumed AF and caller/IRQ observations before
applying it; the one-state primitive probe does not establish that contract.

Our branch-cost inference is similarly conditional: an unconditional JR
costs 12 T versus JP's 10 T, with one extra code byte. A conditional JR costs
7/12 T versus JP's 10 T; JP wins on average only when the branch is taken
more than 60% of the time. Preserve item01's untaken 7-T word path rather
than replacing it globally. Moving its optional long-copy helper may remove
the near trampoline, but that placement has not been built or measured.

## Reproduction and next experiment

With Python and the existing native test extra available:

```text
python libraries/tests/screen_new_forum_tricks.py --output libraries/evidence/forum_primitive_screen.json
python libraries/tests/summarize_trick_pass.py --output .tmp/forum_defaults.json
```

The default reauthentication passes all 31 byte/address/label profiles and
four original assembly resources. No new complete codec, streaming, IRQ or
player playback qualification is performed by this survey. Proceed through
candidate 10 onward using the existing experiment protocol, one completed
experiment per commit. Retain the compiler-identification uncertainty until
the actual forum link or another identifying detail becomes available.
