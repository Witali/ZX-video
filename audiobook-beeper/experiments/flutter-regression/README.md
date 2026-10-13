# Matched IMA4 vibration audit and PCM-origin correction

2026-10-13. The user identifies O. Henry speech in
`ZX-audiobook-IMA4-full-disk.trd` as the strongest vibration example and asks
for a correction in the latest encoder. The preferred original direct disk
must remain reproducible. This experiment changes the current IMA4 PDM
table's PCM origin; it does **not** establish elimination of subjective
flutter or implement a physically constant sample clock.

## What the historical comparison establishes

[`audit.py`](audit.py) authenticates five saved complete native/cold-Fuse
checkpoints with identical prepared PCM SHA256
`ea3c0d945a0cc349747664c137c3725aee3fe8cf5e17b991ae3e24f51829a304`.
It reuses their actual port timestamps and exact mathematical PDM bits;
these are authenticated old execution proofs, not newly executed historical
players. The [report](evidence/history/report.json) separates source-clock
error from PDM-only error.

| Checkpoint | First-loop fixed-clock SNR, dB | Physical sample range, T |
| --- | ---: | ---: |
| Original direct, `b359f532` | 8.316930 | 423..590 |
| Measured weights, `83abfc59` | 8.429852 | 423..590 |
| Compensation/phase lock, `4a819dff` | 18.997821 | 423..590 |
| Waveform search, `5d28485e` | 21.019865 | 423..598 |
| Current overlap search, `b87ac68f` | 22.183509 | 423..598 |

Original/weighted references use their declared mean clock; compensated
references use the declared fixed8-kHz source clock. Both complete loops are
retained in the report. All stages already have approximately
-4.28%..+4.81% five-millisecond physical rate excursions and a141.5..141.7-us
component at the exact Spectrum field frequency,50.021154 Hz. Thus the
audit does **not** find a newly introduced large physical clock modulation.
The older rounded50-Hz diagnostic understated that component. Current
source compensation substantially improves effective waveform timing.

Source preparation is a separate confound: the generic-converter change
`d4a980d7` removed the old speech filtering/volume4 limiter and changed the
selected source position. The old matched preparation is8.332 dB louder;
the later gentle normalization improves signal strength but leaves cyclic
noise. See the existing [source/preparation audit](../../DIRECT_REGRESSION.md)
and [full-disk vibration investigation](../ima4-flutter/README.md).

## Correction and compatibility

The current direct pointer quantizer maps PCM8 value128 to bin32. Its old
midpoint target was `(32+.5)/64`, corresponding to PCM8 value130. The new
measured IMA4 model explicitly sets `pcm_origin=0`: bin32 targets exactly
one-half duty. The encoder regenerates its waveform search and independently
calibrates the new stream; swapping tables underneath an old stream is not
a valid improvement. An independent Fraction recurrence verifies all2048
table entries and rounding ties.

Historical dictionaries lacking `pcm_origin` retain their old midpoint
targets. The preferred direct TRD rebuilds byte for byte, SHA256
`9ce319e8b9352a96ed965d87ff3d1d8698df7d788221563758d306d23c053013`.
IMA3 packet words/successors and its default selection remain unchanged.
No source-level change, filtering change or second normalization is applied
to either arm of the quiet comparison.

New tables need126 first/88 second patterns versus122/86. Reclaim128 bytes
of startup padding, moving the first code pattern from8400 to8380 hex.
Page alignment leaves the PCM-pointer/decoder addresses unchanged. The
complete loader with maximum supported filler and chaining still fits.
RAM remains93440 audio +6912 shadow screen +16384 bank5 tables/TR-DOS
workspace +14336 bank2 code/tables =131072 bytes. Source capacity remains
186880 PCM samples and16 PDM outputs/sample, approximately128 kHz.

## Actual quiet-source comparison

[`compare_source.py`](compare_source.py) runs both table origins through
the public IMA4 converter with identical prepared PCM and parameters:
two clock-compensation passes, best waveform width256/prior0.1/horizon128,
commit64, one attempt, no winner-clock refinement and no audible capture.
Both retain the completely verified fallback. Prepared source SHA256 is
`d6e5b1c1041d8c626d4fec3fea6a313c212e35c844fcdacd33734c3c16548fb4`.
Both exit2 because this quiet source still fails the unchanged20-dB gate;
this is a completed quality preview, not an execution failure.

The converter's worse-loop SNR improves11.428863 to12.096913 dB. The
separate stable-float64 [comparison](evidence/quiet-comparison/report.json)
measures11.450700 to12.130164 dB on loop1. The small pipeline difference is
retained rather than substituting the audit score for the converter gate.
Measured field-error power peak falls26.525%, field-profile standard deviation
falls32.642%, and total error power falls14.483%. These are absolute power
improvements; a flatter max/min ratio alone would not establish a fix.
Mean speed remains approximately-0.04327%, with exact warm-loop field phase.

- [Before, same quiet PCM/current midpoint converter](evidence/quiet-comparison/midpoint-output.wav)
- [After, corrected table/current converter](evidence/quiet-comparison/zero-floor-output.wav)
- [Unchanged prepared source](evidence/quiet-comparison/zero-floor-reference.wav)
- [Bootable23.36-second looping audition](../../../ZX-audiobook-IMA4-flutter-check.trd)

The audition disk SHA256 is
`15ed36d0def8b42a4ccff58e070fcf4a087a78d8c7daf47901032050b0c58845`.
It is a new excerpt for comparison; the original113.712-second full disk
remains unchanged. Both WAVs retain the same actual levels, with no fitted
gain, delay or time stretch. They are filtered Fuse port reconstructions,
not recordings of physical speakers.

The louder control still passes20 dB on both converter loops, minimum
21.996457 dB. Its diagnostic field-power peak decreases28.17% while total
SNR decreases about0.17 dB against the prior stronger, three-attempt search;
that louder comparison is not an identical-search causal control.
Digital silence on independently executed clocks reduces total noise power
about49.85%. Its field-profile standard deviation increases about26%, and
its max/min power ratio increases12.8 to23.1; zero-origin tables therefore
do not uniformly flatten all cyclic noise. Fitted voice AM/delay terms explain
less than0.002 dB of error in the quiet comparison. No strong simple voice
FM regression, subjective cure, constant clock, or conversion-speed goal is
claimed. Physical hardware and a fresh normal-speed endpoint capture are
not tested.

## Timing and full verification

The authoritative generated assembly's instruction sequences are unchanged.
Using the same standard Z80 table as [DIRECT.md](../../DIRECT.md), the first
eight holds sum215 T and the second eight208 T:423 T/sample before and after,
delta0. Page/bank extensions remain14/140 T, delta0. OUT(C),r=12 T,
OUT(n),A=11 T, POP=10 T, POP IY=14 T, JP(HL)=4 T and JP(IY)=8 T; pulse
values and new pattern addresses do not alter these counts. Full native
execution checks every hold. ULA waits, TR-DOS ROM execution and disk latency
are separately measured by Fuse, not included in deterministic CPU totals.

Both quiet arms and the louder corrected arm each pass complete native and
cold-Fuse two-loop bit/predictor/index, paging, memory and phase checks.
The corrected quiet arm verifies5985285 bits and373760 predictor/index
observations; no prefix or startup exclusions are used. An independent
FFmpeg IMA decoder reproduces every decoded sample.43 focused/compatibility
tests pass, including exact rational tables, full RAM/filler bounds, native
mu-law controls and unchanged accepted IMA3 disk reproduction.

The [sequential integration proof](evidence/series/verification/report.json)
repeats the corrected louder excerpt in two resident parts, deliberately
testing a real independent reload. It passes5980094 bits/373756 observations,
one automatic transition,32 loading steps per part, all1054 sector calls
outside audio and END OF AUDIO. Pulse deltas are[0,0]/[0,1] T against the
qualified clocks, within the unchanged8-T limit. SNR is22.010503/22.001649 dB.
Cold preparation27.388691 seconds; loading pause22.750404 seconds. This is
an integration test with repeated source, not a new audiobook release.

## Reproduction and retained failures

Use the project Python dependencies, `audiobook-beeper` and `toolkit` on
PYTHONPATH. `audit.py`, `probe_zero.py`, `compare_source.py`, `silence.py`,
`measure_comparison.py`, `legacy_check.py` and `series_check.py` reproduce
their documented bounded measurements; each accepts explicit output/tool
paths. The [manifest](evidence/manifest.json) authenticates all saved files,
and archives contain the exact producer sources used by each conversion.

```powershell
python audiobook-beeper/experiments/flutter-regression/compare_source.py --repository C:/Work/ZX-video --output build/flutter-ab --arm midpoint --ffmpeg C:/Tools/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python audiobook-beeper/experiments/flutter-regression/compare_source.py --repository C:/Work/ZX-video --output build/flutter-ab --arm zero-floor --ffmpeg C:/Tools/ffmpeg.exe --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python audiobook-beeper/experiments/flutter-regression/reproduce.py --output build/flutter-rebuilt
```

`reproduce.py` authenticates the whole archive and requires byte-identical
audition disk assembly. Add `--verify --ffmpeg ... --fuse ...` to repeat the
complete two-loop execution proof. A final byte-identical rebuild passes.

[`diagnostics/`](evidence/diagnostics/) retains the initial historical audit's
missing-model error, a corrected omitted256-byte pointer-page host estimate,
the sandbox-temp test failure, the silence-only singular-fit failure and the
LFS-pointer compatibility-fixture failure. Corrections respectively supply
the authentic old model, account for/reclaim startup padding, use project
temporary storage, omit undefined silent-source SNR/modulation fits, and
hydrate the exact authenticated fixture. Completed reruns pass. Host-only
table substitution remains an inferior provisional estimate, not a release.
