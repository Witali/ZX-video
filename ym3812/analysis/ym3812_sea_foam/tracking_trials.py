"""Bounded coherent-trajectory ablations through the actual full OPL2 stream."""
import argparse
import gzip
import json
from pathlib import Path
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent; CORE = HERE.parents[1]
sys.path.insert(0, str(CORE)); sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CORE / 'analysis/six_voice_spectral'))
import coherent_ym3812 as coherent
import experimental_ym3812 as opl
import experimental_six_voice as six
import inspect_beeps
import quality
from analyze import diagnostic, read
from simulation_refine import Objective
from support import save
from test_experimental_ym3812 import audit

PROFILES = [('track01', dict(strength=.001)), ('track04', dict(strength=.004)),
            ('gate01', dict(strength=.001, inactive=True, gate=.001)),
            ('gate04', dict(strength=.004, inactive=True, gate=.003)),
            ('levels01', dict(strength=.001, inactive=True, gate=.001, refit_levels=True)),
            ('envelope01', dict(strength=.001, inactive=True, gate=.001, refit_levels=True, envelopes=True))]


def texture_events(source, audio, controls):
    stats, frequency, _ = inspect_beeps.control_stats(controls)
    texture, prominence, _ = inspect_beeps.texture(source, audio, audio, frequency)
    mask = (controls['level'] <= 40) & (frequency >= 300) & (frequency <= 8000) & (prominence[:, :, 0] < 8) & (prominence[:, :, 1] > 14)
    return dict(control=stats, texture=texture, exposed_field_voice_count=int(mask.sum()), exposed_fields=int(mask.any(axis=1).sum()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--profiles', nargs='+', default=[name for name, _ in PROFILES])
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    if any(name not in dict(PROFILES) for name in args.profiles): raise ValueError('unknown profile')
    args.output.mkdir(parents=True); started = time.perf_counter()
    old = HERE / 'evidence'; previous = json.loads((old / 'report.json').read_bytes())
    beep = json.loads((HERE / 'beep-evidence/report.json').read_bytes())
    for name, expected in previous['artifacts_sha256'].items(): assert opl.sha((old / name).read_bytes()) == expected, name
    source = six.read_reference(old / 'reference.wav'); baseline_audio = read(old / 'ym3812-preview.wav')
    with np.load(old / 'controls.npz') as saved: original = {k: saved[k] for k in saved.files}
    lattice = coherent.SourceLattice(source, original, previous['fitting_gain'])
    print(json.dumps(dict(stage='source_lattice_ready', seconds=time.perf_counter() - started)), flush=True)
    baseline = previous['trials'][1]['diagnostics']; trials = []
    spans = beep['exposed_synthetic_lines']['strongest3_second_spans']
    for name in args.profiles:
        options = dict(PROFILES)[name]; folder = args.output / name; folder.mkdir()
        controls, info = lattice.fit(**options)
        np.savez_compressed(folder / 'controls.npz', **controls)
        np.savez_compressed(folder / 'tracking.npz', **info)
        data, writes = opl.smooth_vgm(controls); checked = audit(data, controls)
        raw, samples, parsed = opl.replay(data)
        assert samples == 3969000 and len(raw) == 4474431 and parsed == writes
        audio = opl.playback(raw, samples) * previous['global_playback_gain']
        clipping = int(np.sum(abs(audio) >= 1)); native_clipping = int(np.sum(abs(raw) >= 1))
        quality.write_wav(folder / 'ym3812-preview.wav', audio, opl.OUT_RATE)
        (folder / 'ym3812.vgm').write_bytes(data)
        coded = gzip.compress(data, mtime=0); (folder / 'ym3812.vgz').write_bytes(coded)
        observed = read(folder / 'ym3812-preview.wav')
        screening = []
        for start, end in spans:
            a, b = round(start * opl.RATE), round(end * opl.RATE)
            objective = Objective(source[a:b])
            before = objective.measure(baseline_audio[a:b]); after = objective.measure(observed[a:b])
            screening.append(dict(interval=[start, end], before=before, after=after))
        measured = diagnostic(source, observed)
        events = texture_events(source, observed, controls)
        gates = dict(no_clipping=clipping == native_clipping == 0,
            objective=measured['metrics']['objective_db'] < baseline['metrics']['objective_db'],
            levels=measured['metrics']['level_mae_db'] <= baseline['metrics']['level_mae_db'] + .20,
            all_cosines=all(measured['unpooled'][s]['magnitude_cosine'] >= baseline['unpooled'][s]['magnitude_cosine'] - .005 for s in ('512', '2048', '8192')),
            fewer_exposed=events['exposed_field_voice_count'] < beep['exposed_synthetic_lines']['field_voice_count'],
            fewer_bounces=events['control']['three_field_pitch_bounces'] <= beep['control_stats']['three_field_pitch_bounces'] * .8)
        trial = dict(name=name, options=options, complete=True, audit=checked, excerpt_screening=screening,
            diagnostics=measured, events=events, admission=gates, admitted=all(gates.values()),
            writes=writes, vgm_bytes=len(data), vgz_bytes=len(coded), vgm_sha256=opl.sha(data),
            peak=float(abs(audio).max()), clipping_samples=clipping, native_clipping_samples=native_clipping,
            native_samples=len(raw), output_samples=samples,
            artifacts_sha256={p.name: opl.sha(p.read_bytes()) for p in sorted(folder.iterdir()) if p.is_file()})
        save(folder / 'report.json', trial); trials.append(trial)
        save(args.output / 'progress.json', dict(complete=False, completed_profiles=[t['name'] for t in trials]))
        print(json.dumps(dict(stage='complete_full_tracking_trial', name=name, objective=measured['metrics']['objective_db'],
              exposed=events['exposed_field_voice_count'], bounces=events['control']['three_field_pitch_bounces'],
              admitted=trial['admitted'], gates=gates)), flush=True)
    eligible = [t for t in trials if t['admitted']]
    selected = min(eligible, key=lambda t: t['diagnostics']['metrics']['objective_db']) if eligible else None
    save(args.output / 'report.json', dict(complete=True, date='2026-10-14', seconds=90, fields=4500,
        selected=selected['name'] if selected else None, baseline=baseline, trials=trials,
        source_sha256=opl.sha((old / 'reference.wav').read_bytes()), original_controls_sha256=opl.sha((old / 'controls.npz').read_bytes()),
        global_playback_gain=previous['global_playback_gain'], fitting_gain=previous['fitting_gain'],
        output_filter_unchanged=True, source_pcm_in_output=False, elapsed_seconds=time.perf_counter() - started,
        producer_sources_sha256_lf={str(p.relative_to(CORE)).replace('\\', '/'): opl.sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in (Path(__file__), CORE / 'coherent_ym3812.py', CORE / 'experimental_ym3812.py')},
        artifacts_sha256={str(p.relative_to(args.output)).replace('\\', '/'): opl.sha(p.read_bytes()) for p in sorted(args.output.rglob('*')) if p.is_file()}))


if __name__ == '__main__': main()
