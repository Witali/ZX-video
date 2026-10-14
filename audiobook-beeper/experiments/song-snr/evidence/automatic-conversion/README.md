# Automatic C audio-to-TRD conversion

2026-10-14. `audiobook-beeper/convert_snr_audio.py` accepts ordinary audio/video
or an explicitly prepared monoPCM8/8000-Hz WAV and produces a complete TRD,
source/packed audio, player metadata, quality report and producer snapshots.
C is the default: a standalone process performs waveform encoding and a
separate native PCM trellis generates the unchanged-source baseline. The
original Python encoders stay intact; `--encoder python` selects them.

All inputs use the same frozen half-recent PDM/search parameters. No hand-tuned
gain, clock fit, beam or packet preset is selected per source. Ordinary input uses
existing common dynamics/fades but is never repeated or silently truncated;
an explicit duration can select an excerpt. Prepared input keeps every byte
and its guard. The search prior may zero only the128 already-silent guard
samples after proving that all original content precedes the physical search
end; the measured source is unchanged. Oversized or malformed input fails.

The full-TRD1024 timeline includes every page/bank tail. Sources fitting512K
use identical clocks there; larger sources explicitly require1024K for the
continuous-quality model. The same bootloader retains functional smaller-RAM
fallback/refills. Optional `--verify-fuse` performs complete native checks on
all four models and actual cold Pentagon runs; its time is included in the
grand total and insufficient-RAM quality remains separately unqualified.

Ten tests pass, including Unicode C/Python conversion producing identical
TRD/packed bytes, input/short-source fidelity, capacity/format/guard rejection,
the maximum-timeline distinction and real optional cold Fuse execution.
`tests.log` records the final run. A source shorter than200 ms has no score
under the fixed100-ms edge policy; no shorter crop is substituted.

## Complete song measurement

`benchmark.py` invokes the public program as a new subprocess on the entire
prepared720,384-sample song with its original title. External wall time is
**72.7946 seconds**, including imports, model/guard preparation, C waveform
and baseline encoding, workset/file I/O, TRD assembly, source snapshots,
unchanged-filter scoring/previews and temporary cleanup. This is below the
90.048-second prepared duration. Compiler caches are already populated; this
does not promise the same time for cold compilation or arbitrary host/media.

The resulting entire disk is byte-identical to the independently cold-played
`clock-joint` song: SHA`ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074`.
The complete previous512/1024 Fuse proof therefore applies to these exact
bytes. The source file also remains identical. Fixed-clock SNR is20.250315887
dB, gain23.335544175 over the same-source legacy baseline. Artifact acceptance
is still false: known tonal noise and corpus/modulation regressions require
further generic improvement. Neither this program nor its speed test promotes
the research preview to main or claims physical-hardware/no-audible-flutter
proof. Root main226388fb... remains unchanged.

```powershell
python audiobook-beeper/convert_snr_audio.py source.wav `
  --prepared-pcm --cover title.scr --output result
python audiobook-beeper/convert_snr_audio.py source.wav `
  --prepared-pcm --encoder python --cover title.scr --output python-reference
python audiobook-beeper/experiments/song-snr/evidence/automatic-conversion/benchmark.py `
  --output .tmp/automatic-reproduction
```

For benchmark reproduction use a fresh output directory, as existing user
files are intentionally preserved. `report.json` has the exact historical
command, phase times and reused complete execution identity. The standalone
waveform process requires the locally installed NumPy OpenBLAS DLL; no Python
runtime executes inside that child. Python remains the lightweight source/model
and assembly frontend. All normal steps are included in measured conversion.
