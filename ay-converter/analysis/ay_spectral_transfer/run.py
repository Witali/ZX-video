"""Run a bounded milestone against the unchanged prepared30-second AY baseline."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent; CORE = HERE.parents[1]
sys.path.insert(0, str(CORE)); sys.path.insert(0, str(CORE / 'analysis/six_voice_spectral'))
import chip_model
import noise_colour
import quality
import spectral_fit
from support import sha, save
from analyze import read, diagnostic, plot
from verify_preview import expected_registers


def render(registers, node, folder, width=11):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'registers.gz').write_bytes(gzip.compress(registers, mtime=0))
    subprocess.run([str(node), str(CORE / 'render_ym2149.js'), str(folder / 'registers.gz'),
                    str(folder / 'chip.f32'), '50', str(folder / 'chip-render.json'), str(width)], check=True)
    audio = np.fromfile(folder / 'chip.f32', '<f4').astype(float)
    assert len(audio) == 1323000 and np.isfinite(audio).all()
    return audio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--node', default='node')
    parser.add_argument('--stage', type=int, choices=(1, 2, 3), default=1)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    args.output.mkdir(parents=True)
    old = CORE / 'analysis/o_henry/evidence/compact30'
    reference = old / 'original-preview.wav'; source = read(reference)
    assert sha(reference.read_bytes()) == '99d8ddbca22dd76037e23d4f545d9452b3c8518061666726d9346d4e0fb3e2bd'
    original = json.loads((old / 'report.json').read_bytes()); gain = original['fixed_preview_calibration']
    baseline_registers = gzip.decompress((old / 'registers.gz').read_bytes())
    assert expected_registers(gzip.decompress((old / 'soundtrack.ay12.gz').read_bytes()), 12) == baseline_registers
    baseline_audio = render(baseline_registers, args.node, args.output / 'baseline', 14) * gain
    quality.write_wav(args.output / 'baseline.wav', baseline_audio, 44100)
    assert (args.output / 'baseline.wav').read_bytes() == (old / 'ay-preview.wav').read_bytes()
    baseline = diagnostic(source, read(args.output / 'baseline.wav'))
    settings = [('direct512', dict(window=512)), ('direct2048', dict(window=2048))]
    if args.stage >= 2: settings += [('weighted512', dict(window=512, weight=1.)), ('bands512', dict(window=512, weight=1., band_peaks=4))]
    if args.stage >= 3: settings += [(f'continuity{value:g}', dict(window=512, weight=1., band_peaks=4, continuity=value)) for value in (.02, .05, .1)]
    trials = []; start = time.perf_counter()
    with chip_model.select('AY-3-8910'):
        for name, options in settings:
            folder = args.output / name; folder.mkdir()
            raw, metadata = spectral_fit.fit(source, args.node, folder, output_gain=gain, **options)
            audio = render(raw, args.node, folder) * gain
            quality.write_wav(folder / 'ay-preview.wav', audio, 44100)
            details = diagnostic(source, read(folder / 'ay-preview.wav'))
            eligible = abs(audio).max() < 1 and details['metrics']['objective_db'] < baseline['metrics']['objective_db']
            eligible &= details['metrics']['level_mae_db'] <= baseline['metrics']['level_mae_db'] + .2
            for size in ('512', '2048', '8192'):
                eligible &= details['unpooled'][size]['magnitude_cosine'] >= baseline['unpooled'][size]['magnitude_cosine'] - .005
            entry = dict(name=name, settings=options, gain=gain, metadata=metadata, diagnostics=details,
                         peak=float(abs(audio).max()), clipping_samples=int((abs(audio) >= 1).sum()),
                         eligible=bool(eligible), registers_sha256=sha(raw), wave_sha256=sha((folder / 'ay-preview.wav').read_bytes()))
            trials.append(entry); save(folder / 'report.json', entry)
            print(json.dumps(dict(stage=args.stage, name=name, objective=details['metrics']['objective_db'],
                                 level_mae=details['metrics']['level_mae_db'], eligible=bool(eligible),
                                 cosines=[v['magnitude_cosine'] for v in details['unpooled'].values()])), flush=True)
    eligible = [t for t in trials if t['eligible']]
    selected = min(eligible, key=lambda t: t['diagnostics']['metrics']['objective_db']) if eligible else None
    report = dict(complete=True, date='2026-10-13', stage=args.stage, seconds=30, fields=1500,
                  reference_sha256=sha(reference.read_bytes()), baseline=baseline, baseline_replay_exact=True,
                  same_prepared_source_and_gain=True, source_conditioning_repeated=False, baseline_gain=gain,
                  selected=selected['name'] if selected else 'baseline', trials=trials, elapsed_seconds=time.perf_counter() - start,
                  producer_sha256_lf={p.name: sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in
                                     (CORE / 'spectral_fit.py', CORE / 'render_ym2149.js', Path(__file__))})
    save(args.output / 'report.json', report)
    versions = [('Current AY encoder', read(args.output / 'baseline.wav'))]
    if selected: versions.append((selected['name'], read(args.output / selected['name'] / 'ay-preview.wav')))
    plot(source, versions, args.output / 'spectrogram-full.png')
    plot(source, versions, args.output / 'spectrogram-detail.png', baseline['worst_interval_seconds'])
    print(json.dumps(dict(complete=True, selected=report['selected'], seconds=30)), flush=True)


if __name__ == '__main__': main()
