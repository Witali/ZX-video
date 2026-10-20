# Format-preserving codec acceleration

Measured on 2026-10-20 in `codex/audio-snr-research`, against878c578e.
The user requested faster encoding and decoding with the same data format.
The changes accelerate the PC pipeline. Original Python reference encoders,
source PCM, search parameters, IMA nibble order and Z80 player remain intact.
Byte identity, rather than an approximate SNR tolerance, is the acceptance
criterion. This work does not resolve the separate audio artifact/release gate.

## Measured stages

| Workload | Baseline | Optimized | Scope |
| --- | ---: | ---: | --- |
| Complete public TRD conversion |73.436s|68.505s|One sequential warm-cache pair, all work and previews included |
| Full-song model preparation |8.975s|1.711s|One paired warm native-module comparison, including Lanczos |
| Full-song standalone C search |30.612s|20.748s|Medians of three alternating pairs, process startup and workset I/O included |
| Full-song host C decoding |70.627ms|25.174ms|Three paired medians, all three output files included |

Song preparation is5.24x faster. Windows peak process working set decreases
from2,998,796,288 to747,761,664 bytes, about75%; it includes imports, model
preparation and serialization. The standalone search takes32.2% less wall
time and31.2% less CPU time. CPU medians are28.672/19.734s. All six complete
search runs retain360,192 compressed bytes,1,440,448 search iterations and
final predictor/index0/0. Wall ranges27.962..33.185s and20.597..28.115s show
host variation; these measurements are not a guaranteed conversion duration.

The host decoder is2.81x faster including file I/O; process CPU cycles fall
5.74x. This is the offline IMA-to-PCM/PDM control, not faster playback on the
Spectrum. The full public converter also prepares a separate baseline,
assembles the bootable TRD, renders quality previews and validates guards;
the stage timings above must not be added and labelled full conversion time.

The actual public449-T conversion pair is73.436/68.505s including process
overhead:6.71% shorter on this observation. Its model preparation changes
8.778->3.418s and waveform search/workset I/O26.901->24.810s. Unchanged
baseline encoding9.287/10.090s and quality/preview generation22.444/23.665s
limit the total gain and show host variation. This is a different nonuniform
model from the uniform16 search comparison, so its kernel speedup must not
be replaced by the larger uniform-model number. Both full public outputs,
including every audio preview, reproduce the same delivered655360B TRD,
SHA256`b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e`.
No full-song emulator replay is needed to infer identity of unchanged disks;
this does not claim new emulator or physical-hardware verification.

## Implementation and preserved behavior

The original C profile puts approximately53% of bracketed search time in
candidate merge/selection and42% in candidate scoring; BLAS accounts for
about4%. The profile is instrumented wall time on a bounded prefix and
excludes process startup. Replacing BLAS is not the main opportunity.

`native_waveform_encoder.c` now maintains only the best currently retained
decoder keys in a tracked heap. Its worst `(score,candidate ID)` threshold
can only improve, so candidates unable to beat it need no hash lookup.
Evicted hash entries remain present with an inactive heap position, preserving
probe chains and allowing better later duplicates. Exact arithmetic and tie
order are preserved. Widths above64 use the original selector. Five focused
tests compare the new path with original C and an independent Python merge
and sort, including1400 randomized duplicate/tie cases, evicted keys, extreme
finite values, signed zero and the4096-wide fallback. Existing complete C vs
Python encoder tests also cover guards, errors, nonuniform clocks and Unicode.

`native_waveform_prepare.c/.py` accelerates the six-state source recurrence
and query gathering with the same installed NumPy ILP64 OpenBLAS and strict
floating-point order. It avoids large gathering temporaries. A local hash
table then finds unique positive finite float64 pulse rows; only unique rows
are sorted and inverse IDs are remapped. No clock rounding or substitution
of a nominal28-T packet is allowed: the song still has110 distinct floating
rows. Six focused tests exercise all256 source values,35,469 phase cells,
50,000 later/padded queries, noncontiguous data, nearby float rows, hash
growth and invalid inputs. Real preparation queries have shape`N x16`.

`clock_control.prepare(..., backend='python')` remains independent and does
not load a C compiler. The public converter's default`--encoder c` explicitly
selects native preparation;`--encoder python` selects the original reference
preparation and encoder. The matched C research driver also uses the native
path. Producer snapshots include both new native preparation files.

The host`table_pdm_uniform16_host.c` precomputes all1424 IMA transitions and
reads32KiB compressed chunks, writing explicit little-endian buffered output.
Clipping rejection, final statistics, invalid-state errors and partial-file
semantics are preserved. Static buffers avoid a352KiB Windows thread stack.
All18 canonical/matched full streams,2,391,040 samples, produce identical
word/state/PCM files. All1424 transitions and14,192 boundary cases also pass.

## Rejected controls and Z80 timing

Per-parent error-sum memoization removes24.4% of evaluated rows on the prefix
but gives no reliable total benefit. Last-level memoization and explicit
SSE2 also preserve bytes but have mixed timings. Their sources, outputs and
measurements are retained; they are not integrated or claimed as wins.
The earlier native preparation component without row hashing is also retained:
it reaches only1.66x on song preparation before unique-row sorting is fixed.

No live Z80 instruction changes. Decoder core remains49T, or57T including
the two`EXX` instructions; source extraction is separate. Current ordinary
449T playback plus14T page/243T Pentagon bank overhead remains unchanged:
absolute hot-path delta0T. Aligning all89 decoder rows to256-byte pages would
save one4T instruction but expands5696B to22784B, adding17088B beyond available
fixed RAM. A predictor-register rewrite would affect output dispatch and
needs a separate integrated timing proof. The previously retained448T PCM8
table component omits live IMA decoding and cannot establish this speedup.

## Evidence and reproduction

- [Profile and negative controls](experiments/song-snr/evidence/codec-speed-profile/README.md),
  including frozen original producers and`reproduce.py`.
- [Full-song standalone comparison](experiments/song-snr/evidence/codec-speed-full/README.md).
- [First native preparation component](experiments/song-snr/evidence/native-prepare-speed/README.md).
- [Native preparation with exact row hashing](experiments/song-snr/evidence/native-prepare-hash-speed/README.md).
- [Host decoder proof](experiments/song-snr/evidence/table-pdm-decode-speed-final/report.json);
  the preceding complete measurement is retained separately.
- [All-nine integrated encoding parity](experiments/song-snr/evidence/codec-speed-integration/README.md).
- [Complete public conversion pair](experiments/song-snr/evidence/codec-speed-conversion/README.md).
- [Live Z80 ledger and constraints](experiments/song-snr/evidence/codec-speed-z80-review/README.md).
- [Final regression suite](experiments/song-snr/evidence/codec-speed-tests/report.json):
  all28 tests pass without skips, including Unicode C/Python complete-TRD
  identity and short requested full native/Fuse checks. External30.201s;
  unittest29.353s. The complete song disk is authenticated, not replayed.
- [Independent final audit](experiments/song-snr/evidence/codec-speed-audit/report.json):
  13 manifests/366 unique artifacts across10 retained sets, including actual
  conversion files and original Python/source/disk identities. No codec,
  filter or emulator rerun. Its corrected boundary-record schema check and
  initial failed audit harness are both retained.

Preparation proves22 complete NWFB001/NWFB002 workset pairs over all nine
original sources and explicit448/449-T nonuniform fixtures. These preserve
targets, features, priors, IDs, successor tables and guards. Song workset v1
is138,493,944 bytes, SHA256`2c62776a8c3d94ec61c941c4bf44839e3191d9025bef20d437a5bec83b24853a`.
The standalone song output remains
`44a07e303522dfc4eef31d4654ba35dc6f275d82f6a07d2b3e723155a4d58d06`.

Use the existing Python/NumPy environment, installed C compiler and FFmpeg.
The native modules compile automatically into the ignored`.native-cache`.
Run the converter as before; no data migration or new disk format is needed:

```text
python audiobook-beeper/convert_snr_audio.py prepared.wav --prepared-pcm --encoder c --output NEW_EMPTY_DIRECTORY
python -m unittest test_native_waveform_select test_native_waveform_encoder test_native_waveform_prepare test_convert_snr_audio -v
```

For the tests, use the audiobook directory and existing toolkit/research
module paths. First invocation includes compilation; warm measurements above
exclude compilation. No physical-hardware performance claim is made.
