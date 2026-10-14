"""Fit true sine voices with finer spectral resolution and dominant-source weights."""
import argparse
import gzip
import json
from pathlib import Path
import sys
import time
import wave

import numpy as np
import ymfm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import overtones as h
import experimental_ym3812 as opl
import psychoacoustic
import quality
from analyze import diagnostic, plot, read
from compare import register_perturbations
from simulation_refine import spectra, tick_rms
from support import save


def fit(source, window, exponent, gain):
    """Nine measured sine carriers; no regional weak-peak quotas.

    Longer Hann windows resolve harmonic frequencies more accurately. The
    source-only inverse exponent can be reduced without a playback filter.
    Preserve the old exact channel assignment and20-ms RMS targets. Quantize
    against the old fixed fitting gain so trial gain cannot hide extra tones.
    """
    if window not in (512, 1024, 2048) or not np.isfinite(exponent) or not 0 <= exponent <= 1:
        raise ValueError('unsupported fitting settings')
    if not np.isfinite(gain) or gain <= 0: raise ValueError('positive fitting gain required')
    if not len(source) or len(source) % 441 or not np.isfinite(source).all(): raise ValueError('finite whole-field source required')
    frequency, fnum, block, *_ = opl.dictionary()
    chip = ymfm.YM3812(clock=opl.CLOCK); chip.reset()
    for address, value in opl.initial_registers():
        if address == 0x60: value = 0
        if address == 0xc0: value = 1
        opl.register(chip, address, value)
    for address, value in ((0x43, 0), (0xa0, 0), (0xb0, 0x26)): opl.register(chip, address, value)
    opl.chip_audio(chip, 4096); tone = opl.chip_audio(chip, 16384)
    fundamental = abs(np.fft.rfft(tone))[16] / (len(tone) / 2)
    variance = float(np.var(tone))
    hz = np.fft.rfftfreq(window * 2, 1 / opl.RATE); useful = (hz >= 50) & (hz <= 8000)
    multiples = np.array([1, 2]); patches = np.array([0, 14], np.uint8)
    actual = frequency[None, :, None] * multiples[:, None, None]
    distance = (hz[useful][None, None, :] - actual) * window / opl.RATE
    basis = (abs(np.sinc(distance) + .5 * np.sinc(distance - 1) + .5 * np.sinc(distance + 1)) * fundamental).astype(np.float32)
    count = len(source) // 441
    magnitude = spectra(source, np.arange(count), window)[:, useful].astype(np.float32)
    masking = psychoacoustic.thresholds(magnitude, hz[useful])
    weights = psychoacoustic.error_weights(magnitude, magnitude, masking)
    peak = np.maximum(magnitude.max(axis=1), 1e-12)
    weights *= (np.maximum(magnitude, peak[:, None] * .025) / peak[:, None]) ** -exponent
    rms = tick_rms(source)
    indices = np.full((count, 9), int(np.argmin(abs(frequency - 440))), np.uint16)
    chosen_patches = np.zeros((count, 9), np.uint8); amplitudes = np.zeros((count, 9))
    before = indices[0].copy(); before_patch = chosen_patches[0].copy()
    for tick, target in enumerate(magnitude):
        if tick % 500 == 0: print(json.dumps(dict(stage='sine_refit', window=window, exponent=exponent, tick=tick, total=count)), flush=True)
        if rms[tick] < 1e-8: indices[tick] = before; continue
        peaks = np.flatnonzero((target[1:-1] > target[:-2]) & (target[1:-1] >= target[2:])) + 1
        peaks = peaks[np.argsort(target[peaks])[-32:]]
        peaks = peaks[target[peaks] > target.max() * .035]
        if not len(peaks): peaks = np.array([target.argmax()])
        log = np.log(np.maximum(target, 1e-15))
        left, right = log[np.maximum(peaks - 1, 0)], log[np.minimum(peaks + 1, len(log) - 1)]
        curve = left - 2 * log[peaks] + right
        shift = np.divide(.5 * (left - right), curve, out=np.zeros(len(peaks)), where=abs(curve) > 1e-12)
        observed = hz[useful][peaks] + np.clip(shift, -.5, .5) * hz[1]
        proposed = np.searchsorted(frequency, np.r_[observed, observed / 2])
        proposed = np.unique(np.clip(np.r_[proposed - 1, proposed, proposed + 1, before], 0, len(frequency) - 1))
        rows = basis[:, proposed].reshape(-1, basis.shape[-1]).astype(float)
        candidates = np.column_stack((np.tile(proposed, 2), np.repeat(np.arange(2), len(proposed))))
        actual_frequency = frequency[candidates[:, 0]] * multiples[candidates[:, 1]]
        previous_frequency = frequency[before] * np.where(before_patch == 14, 2, 1)
        weighted = rows * weights[tick]; power = np.sum(weighted * rows, axis=1)
        remaining = target.astype(float).copy(); chosen = []; coefficients = []
        excluded = actual_frequency > 8000
        for _ in range(9):
            correlation = weighted @ remaining
            score = np.maximum(correlation, 0) ** 2 / np.maximum(power, 1e-20)
            held = np.any((abs(np.log2(actual_frequency[:, None] / previous_frequency)) < .015) &
                          (patches[candidates[:, 1], None] == before_patch), axis=1)
            score *= 1 + .012 * held; score[excluded] = -1
            selected = int(score.argmax())
            if score[selected] <= max(float(np.sum(weights[tick] * target ** 2)) * .001, 1e-16): break
            coefficient = max(0., float(correlation[selected] / max(power[selected], 1e-20)))
            chosen.append(selected); coefficients.append(coefficient)
            remaining = np.maximum(remaining - coefficient * rows[selected], 0)
            # Resolution-based exclusion protects close distinct musical tones
            # while avoiding two voices fitting the same unresolved peak.
            excluded |= abs(actual_frequency - actual_frequency[selected]) < max(opl.RATE / window, actual_frequency[selected] * .006)
        padded_index = before.copy(); padded_patch = before_patch.copy(); level = np.zeros(9)
        if chosen:
            selected_rows = rows[chosen]; gram = (selected_rows * weights[tick]) @ selected_rows.T
            correlation = (selected_rows * weights[tick]) @ target; coefficients = np.array(coefficients)
            for _ in range(12):
                for j in range(len(chosen)):
                    coefficients[j] = max(0, (correlation[j] - gram[j] @ coefficients + gram[j, j] * coefficients[j]) / max(gram[j, j], 1e-20))
            selected = candidates[chosen]
            prediction = np.sqrt(np.sum(coefficients ** 2) * variance)
            coefficients *= np.clip(rms[tick] / max(prediction, 1e-12), .1, 10)
            padded_index[:len(selected)] = selected[:, 0]; padded_patch[:len(selected)] = patches[selected[:, 1]]
            level[:len(selected)] = coefficients
            actual_frequency = frequency[padded_index] * np.where(padded_patch == 14, 2, 1)
            cost = abs(np.log2(previous_frequency[:, None] / actual_frequency[None, :])) + .1 * (before_patch[:, None] != padded_patch)
            cost[:, level == 0] = 0; order = opl.assignment(cost)
            indices[tick], chosen_patches[tick], amplitudes[tick] = padded_index[order], padded_patch[order], level[order]
        else: indices[tick], chosen_patches[tick] = before, before_patch
        before, before_patch = indices[tick].copy(), chosen_patches[tick].copy()
    levels = abs(amplitudes[:, :, None] / gain - opl.LEVELS).argmin(axis=2).astype(np.uint8)
    levels[amplitudes == 0] = 64
    return dict(fnum=fnum[indices], block=block[indices], patch=chosen_patches, level=levels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    args.output.mkdir(parents=True); start = time.perf_counter()
    old = HERE / 'evidence'; previous = json.loads((old / 'report.json').read_bytes())
    source = h.six.read_reference(old / 'reference.wav'); before = read(old / 'ym3812-preview.wav')
    baseline = dict(high=h.high_stats(source, before), diagnostics=previous['trials'][1]['diagnostics'])
    gain = previous['global_playback_gain']; trials = []
    for window, exponent in ((1024, 0.), (2048, 0.), (2048, .5)):
        name = f'fit{window}-w{exponent:g}'
        controls = fit(source, window, exponent, previous['fitting_gain'])
        np.savez_compressed(args.output / (name + '.npz'), **controls)
        data, writes = h.pure_vgm(controls); checked = h.audit(data, controls)
        raw, samples, parsed = opl.replay(data)
        assert samples == 3969000 and len(raw) == 4474431 and parsed == writes and not np.any(abs(raw) >= 1)
        audio = opl.playback(raw, samples) * gain; assert not np.any(abs(audio) >= 1)
        quality.write_wav(args.output / (name + '.wav'), audio, opl.OUT_RATE)
        coded = gzip.compress(data, mtime=0); (args.output / (name + '.vgz')).write_bytes(coded)
        effects, independent = register_perturbations(data, gain); assert np.array_equal(raw, independent)
        observed = read(args.output / (name + '.wav')); high = h.high_stats(source, observed); measured = diagnostic(source, observed)
        gates = dict(extra_2048=high['scales']['2048']['1800-8000']['extra_power_fraction'] <= baseline['high']['scales']['2048']['1800-8000']['extra_power_fraction'] * .8,
            all_extra_scales=all(high['scales'][s]['1800-8000']['extra_power_fraction'] <= baseline['high']['scales'][s]['1800-8000']['extra_power_fraction'] for s in high['scales']),
            high_missing=all(high['scales'][s]['1800-8000']['missing_power_fraction'] <= baseline['high']['scales'][s]['1800-8000']['missing_power_fraction'] + .04 for s in high['scales']),
            low_band=all(high['scales'][s]['low_band_cosine'] >= baseline['high']['scales'][s]['low_band_cosine'] - .005 for s in high['scales']),
            levels=measured['metrics']['level_mae_db'] <= baseline['diagnostics']['metrics']['level_mae_db'] + .20)
        trial = dict(name=name, window=window, exponent=exponent, admitted=all(gates.values()), admission=gates,
                     high=high, diagnostics=measured, audit=checked, write_effects=effects,
                     writes=writes, vgm_bytes=len(data), vgz_bytes=len(coded), vgm_sha256=opl.sha(data),
                     peak=float(abs(audio).max()), native_clipping_samples=0, clipping_samples=0,
                     complete_independent_native_replay_exact=True)
        trials.append(trial); print(json.dumps(dict(stage='complete_sine_refit', name=name, admitted=trial['admitted'], gates=gates,
                           high_extra=high['scales']['2048']['1800-8000']['extra_power_fraction'])), flush=True)
    eligible = [t for t in trials if t['admitted']]
    selected = min(eligible, key=lambda t: t['high']['scales']['2048']['1800-8000']['extra_power_fraction']) if eligible else None
    if selected:
        name = selected['name']; data = gzip.decompress((args.output / (name + '.vgz')).read_bytes())
        for target, source_name in (('ym3812-preview.wav', name + '.wav'), ('controls.npz', name + '.npz'), ('ym3812.vgz', name + '.vgz')):
            (args.output / target).write_bytes((args.output / source_name).read_bytes())
        (args.output / 'ym3812.vgm').write_bytes(data)
        output = read(args.output / 'ym3812-preview.wav')
        versions = [('Previous YM3812', before), ('Resolved sine YM3812', output)]
        plot(source, versions, args.output / 'spectrogram-full.png')
        plot(source, versions, args.output / 'spectrogram-detail.png', baseline['high']['worst_extra_interval_seconds'])
        sections = []
        for path in (old / 'ym3812-preview.wav', args.output / 'ym3812-preview.wav'):
            with wave.open(str(path), 'rb') as stream: sections.append(stream.readframes(stream.getnframes()))
        with wave.open(str(args.output / 'before-after.wav'), 'wb') as stream:
            stream.setparams((1, 2, 44100, 0, 'NONE', 'not compressed')); stream.writeframes(sections[0] + bytes(88200) + sections[1])
    save(args.output / 'report.json', dict(complete=True, date='2026-10-14', seconds=90, fields=4500,
         selected=selected['name'] if selected else None, baseline=baseline, trials=trials,
         global_playback_gain=gain, fitting_gain=previous['fitting_gain'], output_filter_unchanged=True,
         source_pcm_in_output=False, elapsed_seconds=time.perf_counter() - start,
         source_sha256=opl.sha((old / 'reference.wav').read_bytes()), previous_report_sha256=opl.sha((old / 'report.json').read_bytes()),
         native_core_sha256=previous['native_core_sha256'],
         producer_sources_sha256_lf={str(p.relative_to(h.CORE)).replace('\\', '/'): opl.sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in (Path(__file__), HERE / 'overtones.py', h.CORE / 'experimental_ym3812.py')},
         artifacts_sha256={p.name: opl.sha(p.read_bytes()) for p in sorted(args.output.iterdir()) if p.is_file()}))
    print(json.dumps(dict(complete=True, selected=selected['name'] if selected else None)), flush=True)


if __name__ == '__main__': main()
