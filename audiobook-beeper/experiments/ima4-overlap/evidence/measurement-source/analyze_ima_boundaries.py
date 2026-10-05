"""Fold filtered output error by encoder boundaries without fitting the audio.

This is a diagnostic, not a universal quality gate: periodic sources and short
clips can bias the groups. Use identical reference/filter/window settings for
before/after comparisons. Times are relative PDM output T-states at 3546900 Hz;
each IMA sample emits 16 pulses, except for the final silent loop/exit guard.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import wave

import numpy as np


def read_wav(path):
    with wave.open(str(path), 'rb') as stream:
        if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (1, 2, 44100):
            raise ValueError('comparison requires mono PCM16 at 44100 Hz')
        return np.frombuffer(stream.readframes(stream.getnframes()), '<i2').astype(float)/32768


def boundary_metrics(source, output, times, period, guard=8):
    if period <= 2*guard or guard < 1:
        raise ValueError('boundary regions must leave a nonempty middle')
    count = min(len(source), len(output))
    if count <= 8820:
        raise ValueError('clip must exceed the fixed 100-ms exclusions at both ends')
    source = source[:count]
    error = output[:count]-source
    error_energy = np.r_[0., np.cumsum(error**2)]
    signal_energy = np.r_[0., np.cumsum(source**2)]
    edges = np.rint((times[::16]-times[0])*44100/3546900).astype(np.int64)
    edges = edges[(edges >= 0) & (edges < count)]
    if np.any(np.diff(edges) <= 0):
        raise ValueError('nonmonotonic output times')
    indices = np.arange(len(edges)-1)
    valid = (edges[:-1] > 4410) & (edges[1:] < count-4410)
    noise = np.bincount(indices[valid] % period, weights=np.diff(error_energy[edges])[valid], minlength=period)
    power = np.bincount(indices[valid] % period, weights=np.diff(signal_energy[edges])[valid], minlength=period)
    regions = {'after_boundary': slice(0, guard), 'middle': slice(guard, period-guard),
               'before_boundary': slice(period-guard, period)}
    ratios = {key: float(noise[region].sum()/power[region].sum()) if power[region].sum() else None
              for key, region in regions.items()}
    after, middle = ratios['after_boundary'], ratios['middle']
    reference_power = np.sum(source[4410:-4410]**2)
    residual_power = np.sum(error[4410:-4410]**2)
    return dict(period_samples=period, boundary_region_samples=guard,
                compared_samples_44100=count, source_sample_intervals=int(valid.sum()),
                fixed_clock_snr_db=float(10*np.log10(reference_power/residual_power))
                    if reference_power and residual_power else None,
                region_noise_to_signal_power=ratios,
                boundary_to_middle_ratio=after/middle if after is not None and middle else None,
                phase_noise_energy=noise.tolist(), phase_source_energy=power.tolist())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--times', type=Path, required=True)
    parser.add_argument('--periods', type=int, nargs='+', default=[64, 128])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, output = read_wav(args.reference), read_wav(args.audio)
    times = np.frombuffer(gzip.decompress(args.times.read_bytes()), '<u4').astype(np.int64)
    report = dict(scope=__doc__, files={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in (args.reference, args.audio, args.times)},
                  periods=[boundary_metrics(source, output, times, period) for period in args.periods])
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({str(r['period_samples']): r['boundary_to_middle_ratio'] for r in report['periods']}))


if __name__ == '__main__':
    main()
