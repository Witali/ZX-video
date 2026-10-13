"""Opt-in direct integer-period fitting for three real AY/YM tone channels.

No ideal sine voices or PCM synthesis: this module emits ordinary R0..R10.
Finite-window square/noise templates approximate magnitude addition; only a
complete continuous chip replay can admit a candidate as an improvement.
"""
from functools import lru_cache
from itertools import permutations
from pathlib import Path
import subprocess
import tempfile

import numpy as np
import music_profile
import psychoacoustic
from simulation_refine import spectra, tick_rms

CORE = Path(__file__).resolve().parent
CLOCK = 1773450


@lru_cache(maxsize=2)
def square_dictionary(window):
    periods = np.arange(14, 2464)
    frequency = CLOCK / (16 * periods)
    hz = np.fft.rfftfreq(2 * window, 1 / 22050)
    useful = (hz >= 50) & (hz <= 8000); bins = np.flatnonzero(useful)
    basis = np.zeros((len(periods), len(bins)), np.float32)
    # Physical unipolar square-wave harmonics, followed by equal mono /3.
    # Source targets have no DC. The approximation retains every odd harmonic
    # below8 kHz; actual DAC/counter/filter behavior is judged after replay.
    for harmonic in range(1, 181, 2):
        rows = np.flatnonzero(frequency * harmonic < 8050)
        if not len(rows): break
        indices = np.rint(frequency[rows, None] * harmonic / hz[1]).astype(int) + np.arange(-8, 9)
        x = (indices * hz[1] - frequency[rows, None] * harmonic) * window / 22050
        kernel = abs(np.sinc(x) + .5 * np.sinc(x - 1) + .5 * np.sinc(x + 1)) * (2 / (3 * np.pi * harmonic))
        valid = (indices >= bins[0]) & (indices <= bins[-1])
        np.add.at(basis, (np.broadcast_to(rows[:, None], indices.shape)[valid], (indices - bins[0])[valid]), kernel[valid])
    return periods, frequency, basis, hz, useful


def noise_dictionary(node, work, window):
    """Measure unit-volume noise through the same vendored chip core."""
    import gzip
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    rows = np.zeros((31 * 50, 11), np.uint8)
    rows[:, 0:6:2] = 1; rows[:, 7] = 0x37; rows[:, 8] = 15
    rows[:, 6] = np.repeat(np.arange(1, 32), 50)
    (work / 'noise.gz').write_bytes(gzip.compress(rows.tobytes(), mtime=0))
    subprocess.run([str(node), str(CORE / 'render_ym2149.js'), str(work / 'noise.gz'),
                    str(work / 'noise.f32'), '50', str(work / 'noise-render.json')], check=True)
    import noise_colour
    raw = np.fromfile(work / 'noise.f32', '<f4').astype(float)
    converted = noise_colour.downsample(raw)
    measured = []; variance = []
    for period in range(31):
        # Keep continuous LFSR history; omit the first200 ms of each segment.
        ticks = np.arange(period * 50 + 10, (period + 1) * 50)
        measured.append(np.sqrt(np.mean(spectra(converted, ticks, window) ** 2, axis=0)))
        segment = converted[(period * 50 + 10) * 441:(period + 1) * 50 * 441]
        variance.append(float(np.var(segment)))
    return np.array(measured), np.array(variance)


def fit(samples, node, work, *, window=512, weight=0., band_peaks=0, continuity=0., output_gain=1.):
    if window not in (512, 2048) or not 0 <= weight <= 1.5 or band_peaks not in (0, 4) or not 0 <= continuity <= .2:
        raise ValueError('unsupported bounded spectral fit settings')
    samples = np.asarray(samples, float)
    if samples.ndim != 1 or not len(samples) or len(samples) % 441 or not np.isfinite(samples).all(): raise ValueError('expected aligned finite mono22050-Hz PCM')
    if not np.isfinite(output_gain) or output_gain <= 0: raise ValueError('invalid output gain')
    period_bank, frequencies, basis, hz, useful = square_dictionary(window)
    noise, noise_variance = noise_dictionary(node, Path(work) / ('dictionary-' + str(window)), window)
    noise = noise[:, useful]
    count = len(samples) // 441; ticks = np.arange(count)
    magnitude = spectra(samples, ticks, window)[:, useful] / output_gain
    masking = psychoacoustic.thresholds(magnitude, hz[useful])
    weights = psychoacoustic.error_weights(magnitude, magnitude, masking)
    peak = np.maximum(magnitude.max(axis=1), 1e-12)
    weights *= (np.maximum(magnitude, peak[:, None] * .025) / peak[:, None]) ** -weight
    rms = tick_rms(samples) / output_gain
    levels = music_profile.chip_levels()
    periods = np.full((count, 3), 252, np.uint16); volumes = np.zeros((count, 3), np.uint8)
    modes = np.zeros((count, 3), np.uint8); shared = np.ones(count, np.uint8)
    previous_period = periods[0].copy(); previous_mode = modes[0].copy(); previous_level = np.zeros(3)
    from support import save
    for tick, target in enumerate(magnitude):
        if tick % 250 == 0: print(dict(stage='spectral_ay_fit', tick=tick, total=count), flush=True)
        if rms[tick] < 1e-8:
            periods[tick] = previous_period; previous_level[:] = 0; continue
        peaks = np.flatnonzero((target[1:-1] > target[:-2]) & (target[1:-1] >= target[2:])) + 1
        keep = list(peaks[np.argsort(target[peaks])[-18:]])
        if band_peaks:
            for low, high in ((50, 800), (800, 1800), (1800, 3500), (3500, 8001)):
                eligible = peaks[(hz[useful][peaks] >= low) & (hz[useful][peaks] < high) & (target[peaks] > target.max() * .025)]
                keep.extend(eligible[np.argsort(target[eligible])[-band_peaks:]])
        peaks = np.unique(keep).astype(int)
        if not len(peaks): peaks = np.array([target.argmax()])
        log = np.log(np.maximum(target, 1e-15)); left = log[np.maximum(peaks - 1, 0)]; right = log[np.minimum(peaks + 1, len(log) - 1)]
        curvature = left - 2 * log[peaks] + right
        shift = np.divide(.5 * (left - right), curvature, out=np.zeros(len(peaks)), where=abs(curvature) > 1e-12)
        observed = hz[useful][peaks] + np.clip(shift, -.5, .5) * hz[1]
        pitch = np.concatenate([observed / harmonic for harmonic in (1, 2, 3, 4, 5, 8)])
        proposed = np.rint(CLOCK / (16 * np.maximum(pitch, 45))).astype(int)
        proposed = np.unique(np.clip(np.r_[proposed - 1, proposed, proposed + 1, previous_period], 14, 2463))
        tone = basis[proposed - 14].astype(float)
        # Broad median power estimates shared noise color without treating
        # isolated source partials as random LFSR peaks.
        floor = np.median(np.lib.stride_tricks.sliding_window_view(np.pad(target, (8, 8), mode='edge'), 17), axis=-1)
        colour = abs(noise @ floor) / np.maximum(np.linalg.norm(noise, axis=1), 1e-20)
        n = int(colour.argmax()); shared[tick] = n + 1
        mixed = np.sqrt((tone * .5) ** 2 + (noise[n] * np.sqrt(.5)) ** 2)
        columns = np.vstack((tone, noise[n], mixed))
        candidates = np.array([(int(p), 0) for p in proposed] + [(int(previous_period[0]), 1)] + [(int(p), 2) for p in proposed])
        variances = np.r_[np.full(len(proposed), 1 / 36), noise_variance[n], np.full(len(proposed), 1 / 144 + noise_variance[n] * .5)]
        weighted = columns * weights[tick]; power = np.sum(weighted * columns, axis=1)
        remaining = target.copy(); excluded = np.zeros(len(columns), bool); chosen = []; coefficient = []
        for channel in range(3):
            correlation = weighted @ remaining
            score = np.maximum(correlation, 0) ** 2 / np.maximum(power, 1e-20)
            if continuity:
                distance = abs(np.log2(candidates[:, 0, None] / previous_period))
                amplitude = np.maximum(correlation / np.maximum(power, 1e-20), 0)
                movement = np.min(np.minimum(distance, 2) + .5 * (candidates[:, 1, None] != previous_mode) +
                                  abs(amplitude[:, None] - previous_level) / np.maximum(previous_level + .05, .05), axis=1)
                score /= 1 + continuity * movement
            score[excluded] = -1
            selected = int(score.argmax())
            if score[selected] <= max(float(np.sum(weights[tick] * target ** 2)) * .001, 1e-16): break
            level = max(0., float(correlation[selected] / max(power[selected], 1e-20)))
            chosen.append(selected); coefficient.append(level); remaining = np.maximum(remaining - level * columns[selected], 0)
            if candidates[selected, 1] != 0: excluded |= candidates[:, 1] != 0
            if candidates[selected, 1] != 1: excluded |= abs(np.log2(candidates[:, 0] / candidates[selected, 0])) < .018
        pp = previous_period.copy(); mm = np.zeros(3, np.uint8); aa = np.zeros(3)
        if chosen:
            selected = columns[chosen]; gram = (selected * weights[tick]) @ selected.T; correlation = (selected * weights[tick]) @ target
            coefficient = np.array(coefficient)
            for iteration in range(12):
                for j in range(len(chosen)):
                    coefficient[j] = max(0., (correlation[j] - gram[j] @ coefficient + gram[j, j] * coefficient[j]) / max(gram[j, j], 1e-20))
            predicted = np.sqrt(np.sum(coefficient ** 2 * variances[chosen]))
            coefficient *= np.clip(rms[tick] / max(predicted, 1e-12), .1, 10)
            pp[:len(chosen)], mm[:len(chosen)] = candidates[chosen].T; aa[:len(chosen)] = coefficient
        cost = abs(np.log2(previous_period[:, None] / pp)) + .1 * (previous_mode[:, None] != mm)
        cost[:, aa == 0] = 0
        order = min(permutations(range(3)), key=lambda p: sum(cost[j, p[j]] for j in range(3)))
        periods[tick], modes[tick] = pp[list(order)], mm[list(order)]
        amplitudes = aa[list(order)]
        volumes[tick] = abs(amplitudes[:, None] - levels).argmin(axis=1)
        previous_period = periods[tick].copy(); previous_mode = modes[tick].copy(); previous_level = levels[volumes[tick]]
    rows = np.zeros((count, 11), np.uint8)
    rows[:, :6:2] = periods & 255; rows[:, 1:6:2] = periods >> 8
    rows[:, 6] = shared; rows[:, 8:11] = volumes
    for ch in range(3):
        rows[:, 7] |= (((modes[:, ch] == 1) | (volumes[:, ch] == 0)).astype(np.uint8) << ch)
        rows[:, 7] |= (((modes[:, ch] == 0) | (volumes[:, ch] == 0)).astype(np.uint8) << (ch + 3))
    np.savez_compressed(Path(work) / 'fit-controls.npz', periods=periods, volumes=volumes, modes=modes, noise_periods=shared)
    return rows.tobytes(), dict(window=window, weight=weight, band_peaks=band_peaks, continuity=continuity,
        output_gain=output_gain, clock_hz=CLOCK, source_samples_added_to_output=False, update_rate_hz=50,
        model='direct_integer_AY_periods_square_and_shared_noise_v1', peak_budget=18,
        channel_assignment='exact3! by physical pitch continuity', simultaneous_non_tone_carriers_max=1)


def main():
    """Explicit experimental CLI; does not change the accepted auto profile."""
    import argparse, gzip, json
    import chip_model, quality
    from experimental_six_voice import read_reference
    from ay_format import AyFrame
    from support import sha, save
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path, help='already prepared mono22050-Hz PCM16 WAV')
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--node', default='node')
    parser.add_argument('--chip', choices=chip_model.CHOICES, default='AY-3-8910')
    parser.add_argument('--window', type=int, default=512); parser.add_argument('--weight', type=float, default=0.)
    parser.add_argument('--band-peaks', type=int, default=0); parser.add_argument('--continuity', type=float, default=0.)
    parser.add_argument('--output-gain', type=float, default=1.)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    args.output.mkdir(parents=True); source = read_reference(args.reference)
    with chip_model.select(args.chip):
        raw, metadata = fit(source, args.node, args.output, window=args.window, weight=args.weight,
                            band_peaks=args.band_peaks, continuity=args.continuity, output_gain=args.output_gain)
        (args.output / 'registers.gz').write_bytes(gzip.compress(raw, mtime=0))
        rows = np.frombuffer(raw, np.uint8).reshape(-1, 11)
        periods = rows[:, :6:2].astype(int) + 256 * rows[:, 1:6:2].astype(int)
        packed = b''.join(AyFrame(tuple(map(int, p)), tuple(map(int, r[8:11])), int(r[6]), int(r[7])).serialize() for p, r in zip(periods, rows))
        (args.output / 'soundtrack.ay9.gz').write_bytes(gzip.compress(packed, mtime=0))
        subprocess.run([args.node, str(CORE / 'render_ym2149.js'), str(args.output / 'registers.gz'),
                        str(args.output / 'chip.f32'), '50', str(args.output / 'chip-render.json'), '11',
                        chip_model.render_name()], check=True)
    audio = np.fromfile(args.output / 'chip.f32', '<f4').astype(float) * args.output_gain
    if abs(audio).max() >= 1: raise ValueError('audition gain clips; choose a lower explicit gain')
    quality.write_wav(args.output / 'ay-preview.wav', audio, 44100)
    save(args.output / 'report.json', dict(complete=True, experimental=True, fields=len(rows), target_chip=args.chip,
        metadata=metadata, registers_sha256=sha(raw), reference_sha256=sha(args.reference.read_bytes()),
        repeated_source_conditioning=False, selected_for_default=False, peak=float(abs(audio).max())))


if __name__ == '__main__': main()
