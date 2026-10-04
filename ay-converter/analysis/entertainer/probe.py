"""Bounded host-only diagnostics of The Entertainer; does not change releases.

Compare six fixed ablations over the same 31.12-second excerpt. Keep the
baseline renderer and independent metrics, add a finer onset proxy, and
report register changes within the encoder's own note tracks. Those tracks
are not a ground-truth transcription. No candidate is hardware-qualified.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np

CONVERTER = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CONVERTER))
import ay_fidelity as ay
import ay_square_fit as fit
from ay_format import AyFrame, registers
import quality


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def decode(ffmpeg, source, *, duration=None):
    command = [str(ffmpeg), '-v', 'error', '-nostdin', '-i', str(source)]
    if duration is not None:
        command += ['-t', str(duration)]
    command += ['-map', '0:a:0', '-vn', '-ac', '1', '-ar', '22050', '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(command, capture_output=True, check=True).stdout,
                         '<f4').astype(float)


def stable_periods(periods, volumes, noise, paths):
    """Diagnostic only: one median period per continuous encoder note run."""
    out = periods.copy()
    for voice in range(3):
        key = paths[:, voice].copy()
        key[volumes[:, voice] == 0] = -1
        if voice == 1:
            key[noise > 0] = -1
        edges = np.r_[0, np.flatnonzero(np.diff(key)) + 1, len(key)]
        for lo, hi in zip(edges[:-1], edges[1:]):
            if key[lo] >= 0:
                out[lo:hi, voice] = int(np.rint(np.median(out[lo:hi, voice])))
    return out


def pitch_stats(periods, volumes, noise, paths):
    report = {}
    for voice, name in enumerate(('bass', 'harmony', 'melody')):
        active = volumes[:, voice] > 0
        if voice == 1:
            active &= noise == 0
        same_note = (active[1:] & active[:-1] & (paths[1:, voice] == paths[:-1, voice])
                     & (paths[1:, voice] >= 0))
        cents = 1200 * np.log2(periods[:-1, voice] / periods[1:, voice])
        motion = np.abs(cents[same_note])
        key = np.where(active, paths[:, voice], -1)
        edges = np.r_[0, np.flatnonzero(np.diff(key)) + 1, len(key)]
        runs = [int(hi-lo) for lo, hi in zip(edges[:-1], edges[1:]) if key[lo] >= 0]
        report[name] = dict(active_ticks=int(active.sum()), same_note_transitions=len(motion),
            changed_period_within_note=int(np.count_nonzero(motion > 1e-6)),
            steps_over_20_cents=int(np.count_nonzero(motion > 20)),
            maximum_within_note_step_cents=float(motion.max()) if len(motion) else 0,
            note_runs=len(runs), runs_shorter_than_60ms=sum(n < 3 for n in runs))
    return report


def onset_proxy(samples):
    # 92.88-ms windows /10-ms hop, separate from the legacy 371.52-ms /100-ms
    # metric. This is a signal-feature detector, not a count of piano notes.
    magnitude, _ = ay.spectra(samples, 22050, 100, round(len(samples)/220.5), window_size=2048)
    frequency = np.fft.rfftfreq(4096, 1/22050)
    return quality.onsets(magnitude[:, (frequency >= 80) & (frequency <= 6000)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ffmpeg', type=Path, required=True)
    parser.add_argument('--node', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('use a new output directory')
    args.output.mkdir(parents=True)
    ticks, rate = 1556, 22050
    samples = decode(args.ffmpeg, args.input, duration=32.128)
    original = samples[:ticks*441]
    magnitude, rms = ay.spectra(samples, rate, 50, (len(samples)+440)//441)
    print('Decompose the unchanged source once', flush=True)
    amplitude, explained = ay.decompose(magnitude, rate)
    # Identical input and decomposition for every ablation, including context.
    ay.decompose = lambda *unused, **kwargs: (amplitude.copy(), explained.copy())
    nominal = ay.LEVELS.copy()
    source = (CONVERTER/'vendor/ayumi-js/ayumi.js').read_text()
    table = re.search(r'const YM_DAC_TABLE = \[(.*?)\]', source, re.S).group(1)
    ym_levels = np.array([float(x) for x in table.split(',') if x.strip()])[1::2]
    variants = [('baseline', True, 50, False, False),
                ('no_noise', False, 50, False, False),
                ('no_fine_tuning', True, 0, False, False),
                ('stable_note_pitch', True, 50, False, True),
                ('ym_volume_curve', True, 50, True, False),
                ('combined_music_probe', False, 0, True, False)]
    reference_features = quality.features(original, rate, 10, (ticks+4)//5)
    source_onsets = onset_proxy(original)
    archived = json.loads((args.baseline/'report.json').read_bytes())
    results = {}
    for name, noise_enabled, tuning, curve, stable in variants:
        print('Evaluate '+name, flush=True)
        ay.LEVELS = ym_levels.copy() if curve else nominal.copy()
        fit.volume_candidates.cache_clear()
        p, v, paths, noise, _, metadata = ay.arrange_for_chip(
            magnitude, rms, rate, noise=noise_enabled, tuning_cents=tuning)
        if stable:
            p = stable_periods(p, v, noise, paths)
        p, v, noise, paths = p[:ticks], v[:ticks], noise[:ticks], paths[:ticks]
        raw = b''.join(registers(AyFrame(tuple(map(int, a)), tuple(map(int, b)), int(c)))
                       for a, b, c in zip(p, v, noise))
        directory = args.output/name
        directory.mkdir()
        (directory/'registers.gz').write_bytes(gzip.compress(raw, mtime=0))
        if name == 'baseline':
            assert raw == gzip.decompress((args.baseline/'registers.gz').read_bytes())
        subprocess.run([str(args.node), str(CONVERTER/'render_ym2149.js'),
                        str(directory/'registers.gz'), str(directory/'chip.f32'),
                        '50', str(directory/'render.json')], check=True)
        rendered = np.frombuffer((directory/'chip.f32').read_bytes(), '<f4').astype(float)
        render_rms = np.sqrt(np.mean(rendered**2))
        original_rms = np.sqrt(np.mean(original**2))
        target = min(.12, .9*original_rms/max(np.max(np.abs(original)), 1e-12),
                     .9*render_rms/max(np.max(np.abs(rendered)), 1e-12))
        quality.write_wav(directory/'preview.wav', rendered*target/max(render_rms, 1e-12), 44100)
        # Match the original converter's resampling and global level policy.
        down = np.frombuffer(subprocess.run([str(args.ffmpeg), '-v', 'error', '-nostdin',
            '-f', 'f32le', '-ar', '44100', '-ac', '1', '-i', str(directory/'chip.f32'),
            '-ar', '22050', '-f', 'f32le', '-'], capture_output=True, check=True).stdout,
            '<f4').astype(float)
        coarse = quality.compare(reference_features, quality.features(down, rate, 10, (ticks+4)//5))
        detected = onset_proxy(down)
        finer = {f'tolerance_{ms}ms': quality.match_onsets(source_onsets, detected, ms//10)
                 for ms in (20, 50, 100)}
        results[name] = dict(parameters=dict(noise=noise_enabled, tuning_cents=tuning,
            volume_curve='YM2149 Ayumi fixed-volume' if curve else 'nominal 3 dB',
            constant_note_period=stable), coarse_metrics=coarse, finer_onset_proxy=finer,
            noise_ticks=int(np.count_nonzero(noise)),
            registers_sha256=sha(raw), pitch_diagnostics=pitch_stats(p, v, noise, paths),
            artifact_sha256={n:sha((directory/n).read_bytes()) for n in
                             ('registers.gz', 'preview.wav', 'render.json')})
        if name == 'baseline':
            for key in ('semitone_spectral_cosine', 'chroma_cosine', 'loudness_correlation', 'rhythm_onset_f1'):
                assert abs(coarse[key]-archived['metrics'][key]) < 1e-10, key
        print(json.dumps(dict(name=name, metrics=coarse, finer=finer['tolerance_20ms'])), flush=True)
        (directory/'chip.f32').unlink()
        save(args.output/'results.partial.json', results)
    report = dict(scope='Host-only bounded ablations; unchanged production converter and TRD. No new Fuse or hardware qualification.',
        date='2026-10-04', source_sha256=sha(args.input.read_bytes()), ticks=ticks, duration_seconds=ticks/50,
        baseline_registers_exact=True, baseline_coarse_metrics_exact=True,
        analysis_window_ms=4096/rate*1000, coarse_metric_window_ms=8192/rate*1000,
        coarse_metric_hop_ms=100, coarse_onset_tolerance_ms=100,
        finer_proxy_window_ms=2048/rate*1000, finer_proxy_hop_ms=10,
        onset_proxy_limitation='Signal detections, not annotated note events; spectral/chroma similarities are not accuracy percentages.',
        nominal_to_ym_level_error_db={str(i):float(20*np.log10(nominal[i]/ym_levels[i])) for i in range(1,16)},
        variants=results, player_native_tstates_delta=0,
        sources_sha256={p.relative_to(CONVERTER).as_posix():sha(p.read_bytes().replace(b'\r\n', b'\n'))
                        for p in [Path(__file__), CONVERTER/'ay_fidelity.py', CONVERTER/'ay_square_fit.py',
                                  CONVERTER/'quality.py', CONVERTER/'render_ym2149.js',
                                  CONVERTER/'vendor/ayumi-js/ayumi.js']})
    save(args.output/'results.json', report)
    print('Finished all six fixed ablations', flush=True)


if __name__ == '__main__':
    main()
