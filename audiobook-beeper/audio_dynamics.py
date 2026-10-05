"""Shared continuous source conditioning before quantization and RAM splitting.

All processing runs on the PC. Off preserves the former peak-only arithmetic;
gentle adds 2:1 soft-knee compression and a lookahead peak guard, followed by
one final peak normalization. No per-part AGC or additional Spectrum work.
"""
from pathlib import Path
import shutil
import subprocess

import numpy as np

PEAK = 109 / 128
RATE = 8000
COMPRESSOR = ('acompressor=threshold=0.125:ratio=2:attack=5:release=200:'
              'knee=2.828427:detection=rms:makeup=1:mode=downward:mix=1')
LIMITER = 'alimiter=limit=0.5:attack=5:release=100:level=0:latency=1'


def add_argument(parser):
    parser.add_argument('--dynamics', choices=('gentle', 'off'), default='gentle',
        help='gentle (default): soft compression and peak normalization; off: previous peak-only normalization. Prepared PCM is always preserved.')


def statistics(samples):
    if not len(samples):
        raise ValueError('empty audio')
    peak, power = 0., 0.
    for start in range(0, len(samples), 1000000):
        block = np.asarray(samples[start:start+1000000], dtype=float)
        if not np.all(np.isfinite(block)):
            raise ValueError('nonfinite audio')
        peak = max(peak, float(np.max(abs(block))))
        power += float(np.dot(block, block))
    return peak, float(np.sqrt(power/len(samples)))


def filter_chain(input_gain):
    return f'volume={input_gain:.17g},{COMPRESSOR},{LIMITER}'


def metadata(mode, before, after, pre_gain, post_gain, count):
    return dict(mode=mode, sample_rate_hz=RATE, samples=count, peak_target=PEAK,
        input_peak=before[0], input_rms=before[1], input_normalization_gain=(pre_gain if mode=='gentle' and before[0] else 1.),
        final_normalization_gain=post_gain, output_peak=after[0]*post_gain,
        output_rms=after[1]*post_gain,
        peak_only_reference_rms=before[1]*pre_gain,
        rms_gain_over_peak_only_db=(float(20*np.log10(after[1]*post_gain/(before[1]*pre_gain))) if before[1] else 0.),
        compressor=(COMPRESSOR if mode=='gentle' else None),
        peak_guard=(LIMITER if mode=='gentle' else None),
        sample_count_unchanged=True, continuous_before_splitting=True,
        scope='PC source dynamics, prior to fades/PCM quantization; not PDM SNR. No per-part gain or compressor reset.')


def normalize(samples, ffmpeg, mode='gentle'):
    if mode not in ('gentle', 'off'):
        raise ValueError('unknown dynamics mode')
    before = statistics(samples)
    pre = PEAK/before[0] if before[0] else 1.
    if mode == 'off' or not before[0]:
        return np.asarray(samples, dtype=float)*pre, metadata(mode, before, before, pre, pre, len(samples))
    run = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-f', 'f32le', '-ar', str(RATE),
        '-ac', '1', '-i', '-', '-af', filter_chain(pre), '-f', 'f32le', '-'],
        input=np.asarray(samples, dtype='<f4').tobytes(), capture_output=True, check=True)
    conditioned = np.frombuffer(run.stdout, '<f4').astype(float)
    if len(conditioned) != len(samples):
        raise ValueError('compressor/limiter changed sample count')
    after = statistics(conditioned)
    post = PEAK/after[0] if after[0] else 1.
    return conditioned*post, metadata(mode, before, after, pre, post, len(samples))


def normalize_file(source, destination, ffmpeg, mode='gentle'):
    """Stream the complete selected track; return the final gain to apply.

    Destination stores conditioned float32 before the final scalar gain. This
    keeps long-track preparation bounded in memory and matches preview math.
    """
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('source and destination must differ')
    if mode not in ('gentle', 'off'):
        raise ValueError('unknown dynamics mode')
    if not source.stat().st_size or source.stat().st_size % 4:
        raise ValueError('invalid float32 track')
    values = np.memmap(source, dtype='<f4', mode='r')
    before = statistics(values)
    count = len(values)
    del values
    pre = PEAK/before[0] if before[0] else 1.
    if mode == 'off' or not before[0]:
        shutil.copyfile(source, destination)
        return pre, metadata(mode, before, before, pre, pre, count)
    subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-y', '-f', 'f32le', '-ar', str(RATE),
        '-ac', '1', '-i', str(source), '-af', filter_chain(pre), '-f', 'f32le', str(destination)], check=True)
    if destination.stat().st_size != count*4:
        raise ValueError('compressor/limiter changed sample count')
    values = np.memmap(destination, dtype='<f4', mode='r')
    after = statistics(values)
    del values
    post = PEAK/after[0] if after[0] else 1.
    return post, metadata(mode, before, after, pre, post, count)
