"""Complete measurements from fitted targets after the fixed-gain clipping rejection.

The initial refit runner aborted on its third trial after complete fitting and
native playback. Reuse those exact targets; retain the clipping failure and
measure all streams without changing gain or admitting the clipped audition.
"""
import argparse
import gzip
import json
from pathlib import Path
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import refit_overtones as r
import overtones as h
from analyze import diagnostic, read
from compare import register_perturbations
from support import save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fitted', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    args.output.mkdir(parents=True); start = time.perf_counter()
    old = HERE / 'evidence'; previous = json.loads((old / 'report.json').read_bytes())
    source = h.six.read_reference(old / 'reference.wav'); before = read(old / 'ym3812-preview.wav')
    baseline = dict(high=h.high_stats(source, before), diagnostics=previous['trials'][1]['diagnostics'])
    gain = previous['global_playback_gain']; trials = []
    for window, exponent in ((1024, 0.), (2048, 0.), (2048, .5)):
        name = f'fit{window}-w{exponent:g}'; controls_path = args.fitted / (name + '.npz')
        with np.load(controls_path) as stored: controls = {key: stored[key] for key in stored.files}
        assert h.opl.validate(controls) == 4500
        (args.output / controls_path.name).write_bytes(controls_path.read_bytes())
        data, writes = h.pure_vgm(controls); checked = h.audit(data, controls)
        raw, samples, parsed = h.opl.replay(data)
        assert samples == 3969000 and len(raw) == 4474431 and parsed == writes and not np.any(abs(raw) >= 1)
        audio = h.opl.playback(raw, samples) * gain
        clipping = int(np.sum(abs(audio) >= 1))
        h.quality.write_wav(args.output / (name + '.wav'), audio, h.opl.OUT_RATE)
        coded = gzip.compress(data, mtime=0); (args.output / (name + '.vgz')).write_bytes(coded)
        effects, independent = register_perturbations(data, gain); assert np.array_equal(raw, independent)
        observed = read(args.output / (name + '.wav')); high = h.high_stats(source, observed); measured = diagnostic(source, observed)
        gates = dict(no_clipping=clipping == 0,
            extra_2048=high['scales']['2048']['1800-8000']['extra_power_fraction'] <= baseline['high']['scales']['2048']['1800-8000']['extra_power_fraction'] * .8,
            all_extra_scales=all(high['scales'][s]['1800-8000']['extra_power_fraction'] <= baseline['high']['scales'][s]['1800-8000']['extra_power_fraction'] for s in high['scales']),
            high_missing=all(high['scales'][s]['1800-8000']['missing_power_fraction'] <= baseline['high']['scales'][s]['1800-8000']['missing_power_fraction'] + .04 for s in high['scales']),
            low_band=all(high['scales'][s]['low_band_cosine'] >= baseline['high']['scales'][s]['low_band_cosine'] - .005 for s in high['scales']),
            levels=measured['metrics']['level_mae_db'] <= baseline['diagnostics']['metrics']['level_mae_db'] + .20)
        trials.append(dict(name=name, window=window, exponent=exponent, admitted=all(gates.values()), admission=gates,
                     high=high, diagnostics=measured, audit=checked, write_effects=effects,
                     writes=writes, vgm_bytes=len(data), vgz_bytes=len(coded), vgm_sha256=h.opl.sha(data),
                     peak=float(abs(audio).max()), native_clipping_samples=0, clipping_samples=clipping,
                     saved_pcm_clips_only_for_rejected_trial=bool(clipping), complete_independent_native_replay_exact=True))
        print(json.dumps(dict(stage='recovered_full_refit', name=name, clipping=clipping, admitted=all(gates.values()))), flush=True)
    assert trials[2]['clipping_samples'] > 0 and not any(t['admitted'] for t in trials)
    save(args.output / 'report.json', dict(complete=True, date='2026-10-14', seconds=90, fields=4500, selected=None,
         baseline=baseline, trials=trials, global_playback_gain=gain, fitting_gain=previous['fitting_gain'],
         source_pcm_in_output=False, output_filter_unchanged=True, elapsed_seconds=time.perf_counter() - start,
         original_attempt=dict(complete=False, failure='AssertionError: output clips at unchanged fixed gain in fit2048-w0.5',
             completed_targets_all_three=True, original_producer_sha256_lf=h.opl.sha((HERE / 'refit_overtones.py').read_bytes().replace(b'\r\n', b'\n'))),
         recovery='Reuse exact fitted NPZ targets; no refit, gain adjustment or clipping-gate exemption.',
         source_sha256=h.opl.sha((old / 'reference.wav').read_bytes()), previous_report_sha256=h.opl.sha((old / 'report.json').read_bytes()),
         native_core_sha256=previous['native_core_sha256'],
         producer_sources_sha256_lf={str(p.relative_to(h.CORE)).replace('\\', '/'): h.opl.sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in (Path(__file__), HERE / 'refit_overtones.py', HERE / 'overtones.py', h.CORE / 'experimental_ym3812.py')},
         artifacts_sha256={p.name: h.opl.sha(p.read_bytes()) for p in sorted(args.output.iterdir()) if p.is_file()}))


if __name__ == '__main__': main()
