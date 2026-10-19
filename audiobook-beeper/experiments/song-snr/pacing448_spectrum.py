"""Independent spectral/ideal-DAC controls for the optional448-T experiment.

All spectra describe the same fixed listening-filter output. An ideal
multilevel control isolates clock/reconstruction error; it is neither an
executed Spectrum player nor an upper bound on joint error cancellation.
"""
import argparse
import json
from pathlib import Path
import shutil

import numpy as np

from build_pdm import CPU_CLOCK
from pacing448_control import instruction_timeline, sha
from probe_reconstruction_error import wav8
from study import filtered, metrics, uniform


def spectrum(error):
    """Measure the whole cropped error, including frequencies above4500 Hz."""
    values = np.asarray(error, dtype=float)[4410:-4410]
    window = np.hanning(len(values))
    power = np.abs(np.fft.rfft(values * window)) ** 2
    if len(power) > 2:
        power[1:-1] *= 2
    frequency = np.fft.rfftfreq(len(values), 1 / 44100)
    total = float(power.sum())
    strongest = np.argsort(power[frequency >= 20])[-8:][::-1]
    ids = np.flatnonzero(frequency >= 20)[strongest]
    return dict(cropped_samples=len(values), bin_width_hz=44100 / len(values),
        filter_scope='Complete output after the unchanged listening filter; fixed100ms edges; no fitted gain, delay or clock',
        error_power_fraction_above4000_hz=float(power[frequency > 4000].sum() / max(total, 1e-300)),
        error_power_fraction_above4500_hz=float(power[frequency > 4500].sum() / max(total, 1e-300)),
        strongest_bins=[dict(hz=float(frequency[k]),
            total_power_fraction=float(power[k] / max(total, 1e-300)),
            three_bin_total_power_fraction=float(power[max(0, k-1):k+2].sum() / max(total, 1e-300))) for k in ids])


def ideal_levels(source, edges):
    """Same unquantized Lanczos16 midpoint control as the archived audit.

    Use the declared source clock, with zero outside the complete source.
    No fitted phase, level or bandwidth is introduced by this interpolation.
    """
    positions = (edges[:-1] + edges[1:]) / (2 * (CPU_CLOCK / 8000)) - .5
    indices = np.floor(positions).astype(np.int64)[:, None] + np.arange(-15, 17)
    distance = positions[:, None] - indices
    weights = np.sinc(distance) * np.sinc(distance / 16)
    values = np.where((indices >= 0) & (indices < len(source)),
        source[np.clip(indices, 0, len(source)-1)].astype(float)-128, 0.)
    return (np.sum(weights * values, axis=1) / weights.sum(axis=1) + 128) / 256


def run(evidence, cache, output, scratch, ffmpeg):
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    report = dict(date='2026-10-19', complete=False, ideal_dac=[], silence=[],
                  counterfactual_not_player=True, emulator_verified=False,
                  fitted_gain_delay_clock=False, producer_sha256=sha(Path(__file__).read_bytes()))
    for name in ('loud3000', 'steps', 'quiet440', 'multitone'):
        source_path = evidence / 'general' / 'inputs' / (name + '.wav')
        source = wav8(source_path)
        for ordinary in (449, 448):
            times = instruction_timeline(len(source), ordinary)
            count = (len(source)-3)*16+15
            edges = np.r_[times[:count:16], times[count-1]]
            actual = filtered(ideal_levels(source, edges), edges, ffmpeg, scratch)
            values, fixed_edges = uniform(source / 256, edges[-1])
            wanted = filtered(values, fixed_edges, ffmpeg, scratch)
            row = dict(source=name, ordinary_tstates=ordinary,
                source_sha256=sha(source.tobytes()),
                ideal_compensated_multilevel_dac=metrics(wanted, actual),
                error_spectrum=spectrum(actual-wanted), counterfactual_not_player=True)
            report['ideal_dac'].append(row)
            print(json.dumps(dict(source=name, ideal_dac_ordinary=ordinary,
                snr_db=row['ideal_compensated_multilevel_dac']['snr_db'],
                fraction_above4000=row['error_spectrum']['error_power_fraction_above4000_hz'])), flush=True)
    host = json.loads((evidence / 'pacing448-control' / 'report.json').read_bytes())
    if not host['complete'] or not host['host_corpus_complete']:
        raise ValueError('Wait for the complete host corpus; do not treat a partial run as complete')
    for name in ('silence', 'long_silence'):
        dest = evidence / 'pacing448-control' / name
        for label in ('before449', 'candidate448'):
            identity = json.loads((dest / (label+'-diagnostics.json')).read_bytes())
            actual = np.load(cache / name / (label+'-actual.npy'))
            reference = np.load(cache / name / (label+'-reference.npy'))
            assert sha(actual.astype('<f8').tobytes()) == identity['actual_float64_sha256']
            assert sha(reference.astype('<f8').tobytes()) == identity['reference_float64_sha256']
            assert not np.any(reference), 'This absolute-noise control requires exact silence'
            report['silence'].append(dict(source=name, variant=label,
                actual_float64_sha256=identity['actual_float64_sha256'],
                absolute_error_rms=identity['waveform']['error_rms'],
                spectrum=spectrum(actual-reference)))
    report['complete'] = True
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    args = parser.parse_args()
    run(args.evidence, args.cache, args.output, args.scratch, args.ffmpeg)
