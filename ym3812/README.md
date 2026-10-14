# YM3812 / OPL2 audio reconstruction

All YM3812 code, experiments, source audio, commands, auditions, figures and
verification evidence are collected here. The folder was consolidated on
2026-10-14 from `codex/ym3812-sea-foam` at `de2d5160` for integration into main.
This is a folder reorganization; the chip algorithms and saved audio stay exact.
See [the consolidation checks](verification.json) for the layout, test and
full replay evidence recorded after moving the files.

## Listening and experiment archive

| Work | Documentation | Audition |
| --- | --- | --- |
| Nine-channel speech and waveform/FM comparisons | [Speech experiment](analysis/ym3812/README.md) | [30-second WAV](analysis/ym3812/evidence/ym3812-preview.wav) |
| Smooth register transitions and frame-boundary click analysis | [Transition experiment](analysis/ym3812_clicks/README.md) | [30-second WAV](analysis/ym3812_clicks/evidence/ym3812-preview.wav) |
| Complete sea-foam song, earlier sine-purity trials and beep analysis | [Song archive](analysis/ym3812_sea_foam/README.md) | [Original 90-second WAV](analysis/ym3812_sea_foam/evidence/ym3812-preview.wav) |
| Source-confirmed coherent tracking and softer FM, all 15 trials | [Latest result](analysis/ym3812_sea_foam/TRACKING_RESULT.md) | **[Selected 90-second WAV](analysis/ym3812_sea_foam/tracking-evidence/ym3812-preview.wav)** |

The latest [old/new comparison](analysis/ym3812_sea_foam/tracking-evidence/before-after.wav)
plays the selected version from 91 seconds. It retains the nine-voice, 50-Hz
target model and actual YM3812 register/wait stream. Source PCM supplies fitting
targets only. All rejected attempts and earlier measurements remain archived.
The latest selected [VGZ](analysis/ym3812_sea_foam/tracking-evidence/ym3812.vgz)
is 483,310 bytes for 90 seconds.

## Code and dependencies

- [Original chip fitter/exporter](experimental_ym3812.py)
- [Temporal source lattice](coherent_ym3812.py), [harmonic groups/exporter](grouped_ym3812.py)
- Three `test_*ym3812.py` modules and the song's `test_overtones.py`
- `analysis/`: the complete speech, transition and song experiment archives
- `sources/original-song.wav`: the exact unprocessed song input
- `layout.json`: every moved file and retained shared dependency, with hashes

Shared analysis helpers copied from `ay-converter/` are fixed dependency
snapshots, recorded as `dependency_copy` in [the layout manifest](layout.json).
They keep original names and bytes so historical relative paths and producer
hash checks work. The AY converter's own files remain in place. This includes
13 Python helpers, two analysis helpers, the speech comparison inputs and
optional AY renderer helpers with their original Ayumi MIT license. The audio
core used for YM3812 rendering is the separate pinned `ymfm-py==0.2.0` package.

With Windows CPython 3.12, NumPy/Pillow and the pinned native core, from the
repository root:

```powershell
python -m pip install numpy pillow
python -m pip install --no-deps --target .tmp/dependencies/ymfm ymfm-py==0.2.0
$env:PYTHONPATH='.tmp/dependencies/ymfm;ym3812;ym3812/analysis/ym3812_sea_foam'
$env:OPENBLAS_NUM_THREADS='1'
python -m unittest test_experimental_ym3812 test_coherent_ym3812 test_grouped_ym3812 test_overtones -v
python ym3812/verify_layout.py --output .tmp/ym3812-layout.json
python ym3812/analysis/ym3812_sea_foam/verify_tracking.py --tests ym3812/analysis/ym3812_sea_foam/tracking-evidence/tests.log
```

Hydrate WAV/PNG files through Git LFS before reproduction. Detailed experiment
pages contain the corresponding build and replay commands. The layout checker
authenticates every relocated file, producer and evidence manifest and local
documentation link. Historical JSON records retain their original dates,
measurements, producer identities and paths; the layout manifest maps their
former repository locations to this folder.

Physical YM3812 playback and a native Z80 delivery format remain unqualified.
The existing Spectrum players and release disks are unchanged.
