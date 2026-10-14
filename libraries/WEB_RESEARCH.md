# Z80 speed and size candidates from other sites

2026-10-14, baseline `5abac404`, branch `codex/z80-codec-tricks`.
The user prioritizes decoder speed, then library code size, and requests
sources beyond zx-pk.ru. This is a completed source survey and primitive
screen, not an integration of new decoder profiles. Retain the standard
ZX0 v2/raw LZSA2 formats and the earlier regression evidence.

## Sources inspected

The [source record](evidence/web_research_2026-10-14.json) records 20 successfully
retrieved documents, failed fetches, response/text hashes and review limits.
Articles and rule files were keyword-screened and selected routines inspected;
no complete semantic audit of every optimizer rule is claimed. No downloaded
source, compiler or optimizer was installed or executed.

| Source | Useful material and applicability |
| --- | --- |
| [Grauw: fast Z80 loops](https://map.grauw.nl/articles/fast_loops.php) | Residue entry into an unrolled block-copy loop; split low/high loop counters. Recalculate classic-Z80 timings: the article includes MSX M1 waits. |
| [SHIAR: optimizing Z80 assembly](https://shiar.nl/calc/z80/optimize) | Stack-word exchange, additive inverses, flag-driven branches and direct stores. The snippets need explicit register/flag liveness. |
| [WikiTI: Z80 Optimization](https://wikiti.brandonw.net/index.php?title=Z80_Optimization) | Loop counters, scratch-free pointer additions, alternative registers and unrolling. Its CPI example also reads RAM and advances HL; these effects are part of the contract. |
| [z80 Heaven: optimization](https://z80-heaven.wikidot.com/optimization) | Small flag/arithmetic substitutions and a subtract/restore form of 16-bit comparison. Many basic replacements are already present in the libraries. |
| [Adam Ziemba: Z80 ASM Optimization Tricks](https://www.ticalc.org/archives/files/fileinfo/285/28502.html) | Read the HTML member of the author's archive. Paired immediate loads and values in patched operands; TI-OS workspace advice does not reserve Spectrum RAM. |
| [Baze: Z80 Bits](https://map.grauw.nl/sources/external/z80bits.html) | Original authored collection hosted by Grauw: multiplication, division, conversions and CRC. These are useful general routines but are not current ZX0/LZSA2 decoder hotspots. |
| [MDL optimizer](https://github.com/santiontanon/mdlz80optimizer) and [patterns](https://github.com/santiontanon/mdlz80optimizer/blob/master/src/main/resources/data/pbo-patterns.txt) | Separate size/speed rules and explicit dead-register/dead-flag constraints. A future advisory audit must protect patched operands and update generators, rather than just edit an exported binary. |
| [Official SDCC rule](https://svn.code.sf.net/p/sdcc/code/trunk/sdcc/src/z80/peeph-z80.def) | Direct indexed immediate-zero store when A is unused. Check flag liveness before applying the standalone snippet outside the compiler's context. |
| [z88dk rules](https://github.com/z88dk/z88dk/blob/master/lib/sdcc/sdcc_peeph.3) | Selected block-instruction, load/store and call rules; platform/CPU-specific rules need independent eligibility checks. |
| [Official ZX0](https://github.com/einar-saukas/ZX0) and [Mega source](https://github.com/einar-saukas/ZX0/blob/main/z80/dzx0_mega.asm) | The Mega source expands bit-phase/length/offset paths. Treat its advertised speed as an upstream comparison, not a measured gain over our adapted Fast profile. |
| [Official LZSA2 small decoder](https://github.com/emmanuel-marty/lzsa/blob/master/asm/z80/unlzsa2_small.asm) | Shares nibble/extended-length helpers for smaller whole-block code. It does not provide our coroutine, input guards or exact-EOD wrapper. |

The previously unidentified `x80cc` thread remains unidentified. This survey
does not establish a new compiler identity from similarly named optimizers.

## Priority for these libraries

The proposed mappings below are our inferences from the sources and current
generators. Complete native block/slice comparisons must establish their
actual gains. Code-size comparisons must retain state, stack and padding
accounting, including any workspace moved outside the code image.

1. **Item10: helper placement.** Keep the optional LZSA2 literal kernel close
   enough to remove its near trampoline while retaining the untaken word
   form's 7-T JR. It can improve speed and save the three-byte trampoline.
2. **Item20: restore HL after comparison.** In LZSA2 `sync`, the current
   `OR A; SBC HL,DE; LD HL,(slice_target)` can potentially end in
   `ADD HL,DE` instead of the reload. The local fragment is 35 → 30 T and
   6 → 4 bytes. Z, carry, sign and overflow agree; H/N and undocumented
   flags differ. The following branch consumes Z, but the complete caller
   and streaming paths still need replay.
3. **Item22: unroll the entire long copy.** The existing optional LZSA2
   kernel unrolls the first 16 bytes and leaves the rest to LDIR. A loop
   entered according to the length residue can speed up the entire long
   transfer. Preserve the current short/escaped-word paths and choose a
   threshold with complete dispatch costs, not just copy-body timing.
4. **Items23–24: specialize frequent decoding work.** Explore additional
   ZX0 Elias bit-phase paths from Mega, and distance-1 matches as repeated
   byte fills. Profile their frequency first; both add code and may penalize
   common short tokens through dispatch.
5. **Items28–29: select the caller's required features.** A project that
   already has a complete input block and needs no yield/paging can use a
   synchronous decoder. A compact LZSA2 profile may then share more helpers.
   Streaming/movie callers still need their delivery and suspension ABI.

Other useful ideas refine existing items: avoid repeated target patching
when a suspension resumes with the same target; reuse loaded state; replace
constant subtraction with addition of its inverse only when comparison
flags are unnecessary; use flags already produced by arithmetic. The
current last-offset/target operands and direct-header bypass already exploit
self-modifying code, so those are not newly discovered gains.

## Native screening of seven primitives

[Reproducer](tests/screen_web_tricks.py),
[report](evidence/web_primitive_screen.json). There are 6,604 executed cases,
including 24 forward-overlap copies at distance 1/2. Counts use the
[Zilog instruction table](https://www.zilog.com/docs/z80/um0080.pdf) and the
independent `z80==1.2.0` core, without MSX M1 waits or ULA contention.
These probes do not test integrated input frontiers, coroutine yields or IRQs.

| Primitive / consistent endpoints | Before → after T-states | Bytes | Native scope / condition |
| --- | --- | --- | --- |
| Residue-entry 16-LDI loop, 256-byte transfer, AF retained | 5371 → 4321 (−1050) versus LDIR; 5291 → 4321 (−970) versus a 16-LDI prefix | 2 → 47 versus LDIR | 519 positive-length cases plus 24 overlap cases; code must be writable and privately owned |
| EX DE,HL / POP HL / PUSH DE → EX (SP),HL | 25 → 19 (−6) | 3 → 1 | 96 cases; DE must be dead and the stack word owned |
| Add A to HL with DE retained | 43 → 20 (−23) | 6 → 5 | 4608 cases; A/result flags dead; scratch-DE baseline without saves is already 22 T/4 bytes |
| Load positive constant / OR A / SBC HL,BC → load inverse / ADD HL,BC | 29 → 21 (−8) | 6 → 4 | 45 cases; BC and result flags dead, so unsuitable for bounds branches |
| INC HL / DEC B / JR NZ → INC HL / DJNZ | 22n−5 → 19n−5 (−3n) | 4 → 3 | 256 lengths, including B=0 meaning 256; B must not also belong to LDI/LDIR |
| LZSA2 comparison followed by target restore | 35 → 30 (−5) | 6 → 4 | 288 boundary/carry cases; S/Z/PV/C retained, H/N differ |
| Exact distance-1, 16-byte match: load seed once, unrolled stores | 331 → 264 (−67) | 2 → 42 | 768 byte/page cases; restores HL/DE/BC/A/SP, preserves S/Z/C; dispatch/length checks excluded |

The residue-entry loop has an AF-preserving setup of 65 T, then
`16*n + 10*ceil(n/16)` T. The complete loop is therefore
`65 + 16*n + 10*ceil(n/16)`, compared with LDIR's `21*n−5`.
It adds 45 bytes over LDIR and 13 over the existing 16-LDI-prefix body.
At 18 bytes it is 80 T slower than the prefix; at 36 it ties; at 37 it
first wins. Those thresholds exclude any new selector/guard/return work.
BC=0 is excluded: a decoder must distinguish a zero-length/no-copy state
from the Z80 block instruction's 65536-byte interpretation. No new assumption
that escaped LZSA2 word lengths are large is permitted.

The distance-1 fill is our derived specialization, inspired by the loop
material. It uses full INC HL, including page crossings, and reads the seed
only once. The 13-T store/increment body needs 56 T of setup/restoration for
the sixteen-byte sample, totaling 264 T. It costs 42 bytes, and selecting
this path is additional work. Do not report the body's savings as a full
decoder gain or claim applicability to distance-2/ordinary matches.

The byte-add variant is also our derivation of the WikiTI pointer-add idea:
`ADD A,L; LD L,A; ADC A,H; SUB L; LD H,A`. It preserves DE and computes the
wrapped HL sum in 20 T. The benefit depends on register pressure: if a
scratch pair's high byte is already zero, a cheaper existing path may win.

Our compare/restore inference follows from modular arithmetic: after
`x−y`, adding y restores x. The restoring addition carries exactly when
the subtraction borrowed; ADD HL retains S/Z/PV from SBC HL. The native
probes cover signed/unsigned boundaries as well as incoming carry values.
This does not establish that all other flags are interchangeable.

## Code-size choices and limits

The retained profile builds still have exact bytes/labels. Current code plus
state totals are 401 bytes for adapted Fast ZX0 (125 prefix +276 core),
384 for ordinary resumable LZSA2, and 473 for direct-header streaming LZSA2.
These totals exclude application buffers and separately reserved stack space.

Upstream whole-block ZX0 routines are 68/126/187/673 bytes for
Standard/Turbo/Fast/Mega. The author's advertised gains over Standard are
21/25/28% for the three faster variants. Those are not measurements over our
Fast coroutine, and the whole-block routines do not provide its target/yield
contract. Standard/Turbo whole-block emitters are already available here.
Study Mega's paths selectively rather than assume replacing Fast with the
entire larger decoder is worthwhile.

The upstream LZSA2 small/fast sources advertise 134/210 bytes. These are raw
whole-block cores, not alternatives with the 384/473-byte wrappers' same
features. Their helper sharing is a starting point for a compact optional
profile; preserve standard escapes, nibble state, exact input consumption
and register/IRQ contracts in any adaptation. A compact coroutine's size
and speed penalty have not been measured.

Moving zero-initialized state to external RAM reduces transported code only
if its initialization and RAM reservation are accounted for. It does not
make that RAM free. RST-based short calls depend on owning the vectors;
Spectrum ROM vectors are not available to a generic RAM library by default.
Existing HL' ownership by the AY/IM2 clock also prevents blindly borrowing
all alternate registers or copying tutorial DI/EI sequences into a decoder.

## Reproduction and continuation

```text
python libraries/tests/screen_web_tricks.py --output libraries/evidence/web_primitive_screen.json
python libraries/tests/summarize_trick_pass.py --output .tmp/web_defaults.json
```

The screening reauthenticates all 31 default profiles; the retained summary
also authenticates four original assembly resources. Current decoder delta
is 0 T/bytes/state/payload. This deliverable adds source evidence and candidate
groups22–29; it does not mark them adopted. Continue with item10 of the saved
sequential queue, one complete experiment at a time, with the existing full
block/slice/guard/overlap/IRQ/transport protocol before accepting a profile.
