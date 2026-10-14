"""Audit the existing song's tonal flicker without producing a replacement track.

Re-run the unchanged fitter with diagnostic captures and require all saved
targets/gain to match exactly. Compare source, original YM and pure-sine audio
on aligned windows; identify short tone segments and sparse-spectrum RMS boost.
These are causal hypotheses and measurements, not perceptual beep labels.
"""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import sys
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1]
sys.path.insert(0, str(CORE))
sys.path.insert(0, str(CORE / 'analysis/six_voice_spectral'))
import experimental_ym3812 as opl
import experimental_six_voice as six
from analyze import read, plot
from simulation_refine import spectra, tick_rms
from support import save


def instrumented_fit(source):
    """Capture pre-normalization prediction without changing selection/math."""
    text = inspect.getsource(opl.fit)
    old = '            coefficients *= np.clip(rms[tick] / max(prediction, 1e-12), .1, 10)'
    assert text.count(old) == 1
    altered = text.replace(old, old + '\n            captures.append((tick, prediction, rms[tick], np.clip(rms[tick] / max(prediction, 1e-12), .1, 10), len(chosen)))')
    namespace = dict(opl.__dict__); namespace['captures'] = []
    exec(compile(altered, '<instrumented unchanged fitter>', 'exec'), namespace)
    controls, gain = namespace['fit'](source, 'sine')
    return controls, gain, np.asarray(namespace['captures'])


def control_stats(controls):
    multiple = np.array([p['car_mul'] for p in opl.PATCHES])[controls['patch']]
    frequency = controls['fnum'] * 2. ** controls['block'] * multiple * opl.NATIVE_RATE / 2 ** 20
    live = controls['level'] < 64; audible = controls['level'] <= 40
    delta = 12 * np.log2(frequency[1:] / frequency[:-1])
    active_pair = audible[1:] & audible[:-1]
    tl_delta = abs(controls['level'][1:].astype(int) - controls['level'][:-1].astype(int)) * .75
    bounce = (abs(delta[:-1]) >= 3) & (abs(delta[1:]) >= 3) & (abs(delta[:-1] + delta[1:]) < .5)
    bounce &= audible[:-2] & audible[1:-1] & audible[2:]
    segments = []
    for channel in range(9):
        start = None
        for tick in range(len(live) + 1):
            split = tick == len(live) or not audible[tick, channel]
            if tick and tick < len(live): split |= abs(delta[tick - 1, channel]) >= 1
            if start is not None and split:
                end = tick
                segments.append(dict(start_field=start, end_field=end, channel=channel,
                                     seconds=(end - start) / 50, frequency_hz=float(np.median(frequency[start:end, channel])),
                                     peak_level_code=int(controls['level'][start:end, channel].min())))
                start = None
            if tick < len(live) and audible[tick, channel] and start is None: start = tick
    short = [s for s in segments if s['seconds'] <= .08]
    return dict(active_voice_mean=float(live.sum(axis=1).mean()), audible_threshold_tl=40,
        audible_pitch_pairs=int(active_pair.sum()),
        jumps_gt3_semitones=int(np.sum(active_pair & (abs(delta) >= 3))),
        jumps_gt12_semitones=int(np.sum(active_pair & (abs(delta) >= 12))),
        level_steps_ge6db=int(np.sum(active_pair & (tl_delta >= 6))),
        three_field_pitch_bounces=int(bounce.sum()), audible_segments=len(segments),
        segments_le80ms=len(short), short_segments_above800hz=sum(s['frequency_hz'] >= 800 for s in short)), frequency, segments


def texture(source, old, new, frequency):
    count = len(source) // 441
    hz = np.fft.rfftfreq(4096, 1 / opl.RATE)
    bands = ((300, 1500), (1500, 4000), (4000, 8000))
    flat = {label: {f'{lo}-{hi}': [] for lo, hi in bands} for label in ('source', 'old', 'new')}
    prominence = np.zeros((count, 9, 3)); excess = np.zeros((count, 9, 2))
    for start in range(0, count, 128):
        ticks = np.arange(start, min(start + 128, count))
        mag = [spectra(audio, ticks, 2048) for audio in (source, old, new)]
        centres = np.rint(frequency[ticks] / hz[1]).astype(int)
        inner = np.clip(centres[..., None] + np.arange(-2, 3), 0, len(hz) - 1)
        outer = np.clip(centres[..., None] + np.arange(-12, 13), 0, len(hz) - 1)
        local = []
        for index, (label, values) in enumerate(zip(flat, mag)):
            peak = values[np.arange(len(ticks))[:, None, None], inner].max(axis=2)
            floor = np.maximum(values.max(axis=1)[:, None] * .0001, 1e-12)
            background = np.median(values[np.arange(len(ticks))[:, None, None], outer], axis=2)
            prominence[ticks, :, index] = 20 * np.log10(np.maximum(peak, floor) / np.maximum(background, floor))
            local.append(peak)
            for lo, hi in bands:
                power = values[:, (hz >= lo) & (hz < hi)] ** 2
                stable_floor = np.maximum(power.max(axis=1, keepdims=True) * 1e-8, 1e-30)
                ratio = np.exp(np.log(np.maximum(power, stable_floor)).mean(axis=1)) / np.maximum(power.mean(axis=1), 1e-30)
                flat[label][f'{lo}-{hi}'].extend(ratio.tolist())
        floor = np.maximum(mag[0].max(axis=1)[:, None] * .0001, 1e-12)
        for index in range(2): excess[ticks, :, index] = 20 * np.log10(np.maximum(local[index + 1], floor) / np.maximum(local[0], floor))
    result = {label: {band: dict(median=float(np.median(values)), mean=float(np.mean(values))) for band, values in groups.items()} for label, groups in flat.items()}
    return result, prominence, excess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    args.output.mkdir(parents=True)
    original = HERE / 'evidence'; revised = HERE / 'overtones-evidence'
    source = six.read_reference(original / 'reference.wav')
    old, new = read(original / 'ym3812-preview.wav'), read(revised / 'ym3812-preview.wav')
    previous = json.loads((original / 'report.json').read_bytes())
    latest = json.loads((revised / 'report.json').read_bytes())
    for folder, report in ((original, previous), (revised, latest)):
        for name, expected in report['artifacts_sha256'].items(): assert opl.sha((folder / name).read_bytes()) == expected, name
    with np.load(original / 'controls.npz') as saved: controls = {k: saved[k] for k in saved.files}
    with np.load(revised / 'controls.npz') as saved: changed = {k: saved[k] for k in saved.files}
    regenerated, gain, captures = instrumented_fit(source)
    assert gain == previous['fitting_gain']
    for key in controls: assert np.array_equal(controls[key], regenerated[key]), key
    for key in ('fnum', 'block', 'patch'): assert np.array_equal(controls[key], changed[key])
    assert np.array_equal(controls['level'] == 64, changed['level'] == 64)
    stats, frequency, segments = control_stats(controls)
    texture_stats, prominence, excess = texture(source, old, new, frequency)
    live = controls['level'] <= 40
    # A heuristic for an exposed synthesized line on a diffuse source region.
    # Actual perception requires listening; this is not a ground-truth label.
    exposed = live & (frequency >= 300) & (frequency <= 8000) & (prominence[:, :, 0] < 8) & (prominence[:, :, 1] > 14)
    score = (np.maximum(prominence[:, :, 1] - prominence[:, :, 0], 0) * exposed * opl.LEVELS[controls['level']]).sum(axis=1)
    spans = np.convolve(score, np.ones(150), 'valid'); picks = []
    for index in np.argsort(spans)[::-1]:
        if all(abs(int(index) - other) >= 250 for other in picks): picks.append(int(index))
        if len(picks) == 4: break
    selected_spans = sorted((index / 50, index / 50 + 3) for index in picks)
    np.savez_compressed(args.output / 'diagnostic-arrays.npz', captures=captures, frequency=frequency,
                        prominence=prominence, peak_excess_db=excess, exposed=exposed, exposed_score=score)
    result = dict(complete=True, date='2026-10-14', seconds=90, fields=4500,
        original_control_refit_all40500_targets_byte_exact=True, original_fitting_gain_exact=True,
        old_and_pure_frequency_patch_key_schedules_identical=True,
        changed_level_targets=int(np.sum(controls['level'] != changed['level'])),
        control_stats=stats, spectral_flatness=texture_stats,
        normalization=dict(whole_source_rms_to_selected_template_rms_median=float(np.median(captures[:, 3])),
                           p90=float(np.percentile(captures[:, 3], 90)), maximum=float(captures[:, 3].max()),
                           fields_gain_above1_5=int(np.sum(captures[:, 3] > 1.5)),
                           fields_gain_above2=int(np.sum(captures[:, 3] > 2))),
        exposed_synthetic_lines=dict(heuristic='TL<=40;300..8000Hz;source local prominence<8dB;old synthetic prominence>14dB',
                                    field_voice_count=int(exposed.sum()), fields_with_any=int(exposed.any(axis=1).sum()),
                                    old_mean_prominence_db=float(prominence[:, :, 1][exposed].mean()),
                                    new_mean_prominence_db=float(prominence[:, :, 2][exposed].mean()),
                                    source_mean_prominence_db=float(prominence[:, :, 0][exposed].mean()),
                                    strongest3_second_spans=selected_spans),
        evidence_interpretation='Heuristic candidate events; no claim of independently labeled audible beeps.',
        source_sha256=opl.sha((original / 'reference.wav').read_bytes()),
        old_wav_sha256=opl.sha((original / 'ym3812-preview.wav').read_bytes()),
        new_wav_sha256=opl.sha((revised / 'ym3812-preview.wav').read_bytes()),
        baseline_objective_db=previous['trials'][1]['diagnostics']['metrics']['objective_db'],
        pure_objective_db=latest['selected_metrics']['diagnostics']['metrics']['objective_db'],
        producer_sources_sha256_lf={str(p.relative_to(CORE)).replace('\\', '/'): opl.sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in (Path(__file__), CORE / 'experimental_ym3812.py')})
    for index, (start, end) in enumerate(selected_spans, 1):
        plot(source, [('Previous YM3812', old), ('Pure-sine YM3812', new)], args.output / f'span-{index}.png', (start, end))
        pieces = []
        for path in (original / 'comparison-source.wav', original / 'ym3812-preview.wav', revised / 'ym3812-preview.wav'):
            with wave.open(str(path), 'rb') as stream:
                stream.setpos(round(start * 44100)); pieces.append(stream.readframes(round((end - start) * 44100)))
        with wave.open(str(args.output / f'span-{index}-source-old-new.wav'), 'wb') as stream:
            stream.setparams((1, 2, 44100, 0, 'NONE', 'not compressed')); stream.writeframes(bytes(88200).join(pieces))
    result['artifacts_sha256'] = {p.name: opl.sha(p.read_bytes()) for p in sorted(args.output.iterdir()) if p.is_file()}
    save(args.output / 'report.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__': main()
