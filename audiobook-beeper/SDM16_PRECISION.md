# Reconstructed16-bit input to SDM

2026-10-19. The user's proposed precision mechanism has been implemented as
an automatic standalone C research program, with an independent exact Python
reference. This is a complete nine-source **host counterfactual**, not a new
Spectrum player or replacement TRD. The source-independent quality goal is
still active.

## Where precision is currently lost

The IMA decoder already reconstructs a16-bit predictor. The continuous
player keeps its unsigned-biased value in IX and adds16-bit IMA deltas.
However, `pcm_high_lookup` uses IXH to select a64-level modulation input:

```
unsigned = signed_predictor + 32768
existing_input = floor(unsigned / 1024) / 64
proposed_input = unsigned / 65536
```

Thus all eight IXL bits and two low IXH bits currently disappear at this
boundary. A16-bit container alone changes nothing. A valid implementation
must demonstrate that those lower bits affect the modulator's carried state
and eventual source pulses. Source preparation stays the same PCM8 reference
in this experiment; this does not claim16-bit original-source fidelity or
alter the source/gain/bandwidth to obtain a better score.

Normalization has no half-LSB bias: signed0 is exactly duty0.5, and maximum
32767 is65535/65536, not1. The new model agrees with the old one at each of
the64 zero-origin anchors `signed=1024*k-32768`.

## Separate input and state precision

The new C program has three modes, all with beta0.5 and the existing449-T
ordinary table weights. Modulation order does not change in this milestone.

| Mode | Input | State between packets |
|---|---|---|
|A, authenticated control|64 input levels|Original16 accumulated-error codes and two recent-error codes|
|B, input-only control|Full reconstructed PCM16|The same rounding/clipping asA|
|C, state-precision control|Full reconstructed PCM16|Continuous f64 accumulated/recent state; no packet or bank resets/clipping|

All variants use the same complete decoded IMA samples and physical449-T
timeline, including real page/bank additions. Ordinary modulation weights
are not silently changed to absorb those sparse holds. The original IMA
nibbles remain frozen; they were optimized jointly forA and have **not** been
reoptimized forB/C. A total-quality regression is not a proof that a new
matched encoder cannot improve, nor is this an SNR upper bound.

Six tests compare all2048 anchor words/successors with the original table
and an exact Fraction implementation, check175 full16-bit cells, compare
whole A/B carried trajectories, and independently check continuousC state.
A one-LSB example is signed37 versus38: A is unchanged; B changes its first
successor and its third output word. This demonstrates real lower-bit
influence while also exposing the discontinuities of the coarseB state.

## Measured result and limits

All nine complete original sources finish. Every A packet word and successor
matches the existing implementation, and all nine archived original-clock
scores reproduce exactly. The same continuous f64 filter,768-kHz area
integration, fixed100-ms edges and unfitted original8-kHz reference are used.

| Complete song metric,dB |A|B|C|
|---|---:|---:|---:|
|SDM reconstruction versus decodedIMA16, diagnostic|25.831087|26.270322|26.579564|
|Total versus original8-kHz source|20.250316|19.096820|19.118673|

The song's SDM diagnostic improves0.439235 dB from full input precision and
0.748477 dB with continuous state as well. The total falls on the frozen old
IMA path. Across the corpus B has eight total-SNR/nine RMS regressions; C has
six/seven. Short original silence RMS is0.0154867382 inA and approximately
0.0155139391 inB/C. Noise, AM/delay and coherent-line diagnostics remain saved;
the experiment does not establish absence of flutter, AM or added background.
Decoded near-silence can have a tiny nonzero reference, producing an extreme
PDM diagnostic SNR. Use absolute original-silence RMS for background decisions.

The standalone C program uses no Python child, Python DLL or BLAS dependency.
Python performs input authentication, rendering and diagnostics. It retains
all1,195,520 decoded source samples across27 variant runs; the179-file archive
contains packed pulse words, carried-state bytes, source/IMA identities,
producer snapshots, listening WAVs, diagnostics and exact parity checks.
Raw f64 arrays remain a reproducible ignored cache. No full emulator run is
claimed for these new modulators, and no physical sample timing was changed.

[Whole-corpus results](experiments/song-snr/evidence/sdm16-precision/report.json),
[parity evidence](experiments/song-snr/evidence/sdm16-precision/parity.json),
[independent archive audit](experiments/song-snr/evidence/sdm16-precision/audit.json).

```powershell
python -m unittest discover -s audiobook-beeper/experiments/song-snr `
  -p test_sdm16_precision.py -v
python audiobook-beeper/experiments/song-snr/sdm16_precision.py `
  audiobook-beeper/experiments/song-snr/evidence `
  --output .tmp/reproduce-sdm16 --scratch .tmp/reproduce-sdm16-cache
```

## Implementation still required

The present fixed lookup layout and CPU schedule do not implementB orC.
More source RAM does not automatically enlarge fixed packet/decoder code
space. Expanding the complete song to raw packed128-kHz pulses would require
approximately1.44 MB and lose seamless residency on Pentagon1024.

[The separate architecture audit](experiments/song-snr/evidence/sdm16-architecture/README.md)
enumerates all65536 inputs and32 states forB (2097152 cases). Reachable
closure stays18 states, but138 FIRST/124 SECOND patterns put the existing
resident layout atC240,576 bytes past bank2 before the worker. The complete
six-byte lookup would need approximately7.08 MB;3006 distinct records and
5383 constant intervals indicate possible compression, without proving a
fast enough selector. The arrays and their input axes are retained.

Concrete native arithmetic probes measure30 T per pulse with a preserved
C=16 mask. Sixteen pulses plus decoding need575/591 T per sample and do not
fit the current period. An11-pulse first-order probe fits448-T packet spacing
but changes the carrier to88 kHz and introduces a148-T unweighted decode
hold; it has no paging/audio-quality proof. A literal residual-input spill
and map costs138 extra T and reaches24 states (144 bytes per row, colliding
with decoder data). These are measured concrete formats, not impossibility
bounds for other representations. All28 architecture artifacts are hashed.

The next step is a CPU/RAM-feasible representation that retains lower-bit
influence, followed by reoptimization of the IMA encoder for that actual
modulator and complete own-clock playback/artifact checks. Input precision,
state precision and true second-order shaping remain separate mechanisms.
The old25-level/reduced-gain SD2 port must not be repeated as an apparent
precision upgrade. Existing encoders, player defaults and delivered b96763ca
remain unchanged.

## Compact pattern bodies, 2026-10-19

The [standalone pattern generator](experiments/song-snr/sdm16_patterns.py)
now implements three source-independent code-sharing layouts for all138
FIRST and124 SECOND literals needed by the completeB catalogue. This is a
memory mechanism for a future full-input selector, not an integrated player.

| Layout | FIRST+SECOND bytes | Saved bytes | Additional deterministic T/sample |
|---|---:|---:|---:|
| Existing unrolled bodies |13732|0|0|
| Shared SECOND high suffixes |11124|2608|0|
| Also shared FIRST suffixes |9220|4512|10|
| Both SECOND suffixes and FIRST suffixes |7156|6576|20 before pacing exchange|

The first compact layout redirects an existing10-T conditional JP to one of
sixteen shared high-phase tails. It preserves every native pulse timestamp,
port, value and live register. The maximum-sharing layout introduces two
constant10-T transfers. On Pentagon its padding can change26 ->6 T using
`INC HL` with deadHL, retaining449 T ordinary/463 T page/692 T bank. Its
intra-packet timestamps still change, so identical total duration is not an
audio-quality equivalence proof. On128/Scorpion it adds20 T: ordinary443,
page457, bank686/710 T before any ULA waits. The intermediate layout adds10 T
without a pacing exchange. The saved instruction-by-instruction tables
separate these CPU counts from ULA, ROM and physical-disk delays.

All18864 paired native cases pass across four coherent-bank profiles,
covering every required FIRST/SECOND literal, both nibble phases and
ordinary/page/bank tails. Live flags/registers, lookupSP, predictor/prefetch,
physical paging and guarded memory match the unshared control. These are
component tests, not every possible literal pair or a whole disk execution.
The [independent auditor](experiments/song-snr/sdm16_patterns_audit.py) checks
all25 saved artifacts and assembles the actual unchanged repository macros:
all13732 baseline code bytes match the experimental control. Its finalDS
padding is sealed with a sentinel because pyz80 omits trailing reservations.

[Native results](experiments/song-snr/evidence/sdm16-patterns/report.json),
[instruction counts](experiments/song-snr/evidence/sdm16-patterns/timing.json),
[independent audit](experiments/song-snr/evidence/sdm16-patterns-audit/report.json).
Reproduce with `python audiobook-beeper/experiments/song-snr/sdm16_patterns.py`
and `python audiobook-beeper/experiments/song-snr/sdm16_patterns_audit.py`.
No fullPCM16 selector, cold boot, UI, ULA/Fuse or complete-source quality proof
is established by this code-sharing experiment. The delivered disk is unchanged.

## Exact compact tables and successor arithmetic, 2026-10-19

The [interval producer](experiments/song-snr/sdm16_intervals.py) now preserves
all1179648 reachableB input/state cells in a serialized representation.
Instead of5383 full word/successor intervals it stores2558 word intervals
and555 recent-state cutoffs. The2270 remaining successor changes are computed
from the selected word's weighted high-time area:

```
C = ceil(65536 * area(word) / 449 - 256)
d = signed16((unsigned_PCM16 - (C mod 65536)) mod 65536)
qcode = old_state // 2 + (d >> 9)
next_state = 2 * qcode + recent
```

The reachable difference range is[-6822,7333], qcode1..15. All32 original
states additionally pass the separate exhaustive check: difference[-6822,7910],
qcode0..15. Neither clipping nor an exceptional negative-C marker is needed
on these verified selected-word domains. Arbitrary unrelated input/word/state
triples are outside this assertion.

The compactC table has11342 interval bytes,3372 dictionary bytes for1124
words,744 parameter bytes for372 weighted areas,32 state-map bytes and root
pointers. High4/5/6/8 roots give16066/16642/17794/24706 total table bytes,
requiring at most15/11/8/5 word-record visits. InlineC embeds each two-byte
constant in a four-byte word record:17022 bytes with high5 roots. These are
host table sizes, not cycle or complete-player memory claims.

Four focused tests pass in2.655 s, including exact Fraction witnesses. A first
run failed in its final witness reader through a shadowed Python dictionary;
the model and complete-domain decoders had passed. Its19 artifacts/traceback
are retained with `complete:false`; the exact failed producer was not saved
before correction. The successful rerun freezes29 artifacts and its actual
producer/test sources.

The [qphase component](experiments/song-snr/sdm16_qphase.py) executes the exact
arithmetic on all2097152 originalB cells, with per-cell predictor, port,
register and lookup-SP guards. WithHL=C/E=old_qcode its literal sequence
`LD A,IXL; SUB L; LD A,IXH; SBC A,H; SRA A; ADD A,E` costs36 T and clobbers
onlyA/F. Extracting qcode from a raw-stateE makes44 T, or from the proposed
root-pageE59 T. Three1536-case native component tests verify these counts and
flags/IFF preservation. LoadingC throughPOP adds10 T: the root-page variant
then costs69 T before word selection, recent calculation or pattern dispatch.
It leaves only27 T of the historical70+26=96-T Pentagon lookup/padding budget;
it does not establish a complete fast-enough lookup.

## Executed selector rejected; complete memory remains open

The [literal high8 selector](experiments/song-snr/evidence/sdm16-selector/README.md)
executes all19676 boundary/high-byte/extreme/one-LSB native vectors for all18
reachable states. Every2097152 host cell also matches. All native paths are
padded to155 T: root42, low-byte load8, at most three CP/JP comparisons51,
packet fetch44, continuationJP10. The old query plus POPs is70 T, excluding
JP(IY)8. Even removing all26 Pentagon pacing T gives449-26-70+155=508 T per
sample, before additional table-bank paging. This concrete implementation
would slow playback and is rejected. Its roots9216/handlers207437/local
records32298 bytes are per-state flat harness components, not a global RAM
allocation. The compact hybrid is a distinct representation and has not been
assigned that selector's timings.

An [independent archive/traversal audit](experiments/song-snr/sdm16_intervals_audit.py)
checks all188 saved successful/failed interval, qphase and selector artifacts;
follows serialized roots for every input in all12 raw/compactC/inlineC and
high4/5/6/8 combinations; and compares every saved native qcode with the
authenticated original catalogue. It independently verifies the literal36-T
qcore bytes and155/508-T selector counts.

Its optimistic inherited-UI memory ledger reserves1024 TR-DOS bytes and16
cache bytes from fixed32768 RAM, leaving31728. It charges5696 decoder bytes,
832 startup bytes,1459 worker bytes,108 UI/padding bytes and1024 literal-to-
pattern address bytes. Even compactC/high4 plus the7156-byte pattern variant
needs32341 bytes:613 over, before any new selector instructions or alignment.
High5 is1189 over. Rearranging cold/persistent code or changing the addressing
ABI could change these costs; this is a literal-drop-in rejection, not an
impossibility bound. Adding source RAM alone does not solve the fixed lookup
layout or count the extra bank switches.

[Exact interval results](experiments/song-snr/evidence/sdm16-intervals/report.json),
[native qphase results](experiments/song-snr/evidence/sdm16-qphase/report.json),
[independent full traversal and ledger](experiments/song-snr/evidence/sdm16-intervals-audit/report.json).
Reproduce with the commands in the interval/selector evidence READMEs, then
run `python audiobook-beeper/experiments/song-snr/sdm16_qphase.py` and
`python audiobook-beeper/experiments/song-snr/sdm16_intervals_audit.py`.
Original player, executable encoders and delivered disk remain unchanged.
The next precision implementation needs a different counted register/lookup
layout that fits both complete fixed RAM and the constant source schedule;
only then should its IMA producer and full-source audio checks be matched.
