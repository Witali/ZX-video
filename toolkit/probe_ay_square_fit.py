"""Compare the legacy and square-aware AY encoders on bounded source windows."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

import ay_fidelity as ay
from ay_square_fit import refine, recover_isolated_tones
from build_long_video_trd import AyFrame
import compare_ay_fidelity as quality


def frames(periods, volumes, noise):
    periods = periods.copy()
    for voice in range(3):
        previous = 1
        for i in range(len(periods)):
            if not volumes[i, voice] or (voice == 1 and noise[i]):
                periods[i, voice] = previous
            else:
                previous = periods[i, voice]
    return [AyFrame(tuple(map(int, p)), tuple(map(int, v)), int(n))
            for p, v, n in zip(periods, volumes, noise)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--starts', type=float, nargs='+', default=[60, 170, 430])
    parser.add_argument('--duration', type=float, default=8)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rate, hz, context = 22050, 50, 1
    report = dict(date='2026-10-01', source=str(args.input.resolve()),
        source_mix='FFmpeg mono downmix, matching the generic converter',
        update_rate_hz=hz, metric_rate_hz=hz, onset_tolerance_seconds=1/hz,
        scope='offline synthesis comparison; no new TRD or full movie verification', windows=[])
    for start in args.starts:
        directory = args.output/f'{start:g}s'
        directory.mkdir(exist_ok=True)
        first, duration = max(0, start-context), args.duration+context+min(context, start)
        command = [args.ffmpeg, '-v', 'error', '-nostdin', '-ss', str(first), '-t', str(duration),
            '-i', str(args.input), '-map', '0:a:0', '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-']
        pcm = subprocess.run(command, check=True, capture_output=True).stdout
        samples = np.frombuffer(pcm, '<f4').astype(float)
        count = round(duration*hz)
        if len(samples) != round(duration*rate):
            raise ValueError('probe requires the complete requested source window')
        magnitude, rms = ay.spectra(samples, rate, hz, count)
        amplitude, explained = ay.decompose(magnitude, rate)
        periods, volumes, notes = ay.arrange(amplitude, rms, explained)
        recovered_periods, recovered_volumes, recovered_notes = periods.copy(), volumes.copy(), notes.copy()
        recovered = recover_isolated_tones(magnitude, rms, recovered_periods, recovered_volumes, recovered_notes, rate)
        noise, volumes, share = ay.arrange_noise(magnitude, rms, explained, volumes, rate)
        new_noise, recovered_volumes, _ = ay.arrange_noise(magnitude, rms, explained, recovered_volumes, rate)
        new_periods, new_volumes, fit = refine(magnitude, recovered_periods, recovered_volumes, new_noise, rate)
        fit['recovered_isolated_tone_ticks'] = recovered
        square_volumes = new_volumes.copy()
        square_volumes[noise > 0, 1] = volumes[noise > 0, 1]
        quiet_volumes = volumes.copy()
        quiet_volumes[noise > 0, 1] = np.maximum(0, quiet_volumes[noise > 0, 1]-1)
        selections = dict(before=frames(periods, volumes, noise),
                          quieter_only=frames(periods, quiet_volumes, noise),
                          square_only=frames(new_periods, square_volumes, new_noise),
                          after=frames(new_periods, new_volumes, new_noise))
        lo, hi = round((start-first)*rate), round((start-first+args.duration)*rate)
        tick_lo, tick_hi = round((start-first)*hz), round((start-first+args.duration)*hz)
        signals = dict(original=samples[lo:hi])
        signals.update({name: ay.render(value, hz, rate)[lo:hi] for name, value in selections.items()})
        reference = quality.features(signals['original'], rate, hz, tick_hi-tick_lo)
        metrics = {name: quality.compare(reference, quality.features(signal, rate, hz, tick_hi-tick_lo))
                   for name, signal in signals.items() if name != 'original'}
        noise_mask = noise[tick_lo:tick_hi] > 0
        powers = {name: float(np.sum(ay.LEVELS[v[tick_lo:tick_hi, 1][noise_mask]]**2))
                  for name, v in [('before', volumes), ('after', new_volumes)]}
        record = dict(start_seconds=start, duration_seconds=args.duration,
            context_seconds=[start-first, context], source_pcm_sha256=sha(pcm),
            metrics=metrics, fit=fit, noise_ticks=int(np.count_nonzero(noise_mask)),
            noise_level_squared_sum=powers, artifacts={})
        for name, value in selections.items():
            raw = b''.join(f.serialize() for f in value[tick_lo:tick_hi])
            path = directory/f'{name}.ay'
            path.write_bytes(raw)
            record['artifacts'][path.name] = sha(raw)
            assert all(AyFrame.deserialize(f.serialize()) == f for f in value)
            import ay_interrupt
            import ay_huffman_stream
            ticks = ay_interrupt.encode_ticks(value[tick_lo:tick_hi])
            coded, _ = ay_huffman_stream.encode(ticks)
            _, restored = ay_huffman_stream.decode(coded)
            assert restored == ticks
            record.setdefault('resident_ayh1_bytes', {})[name] = len(coded)
        np.savez_compressed(directory/'analysis.npz', pcm=np.frombuffer(pcm, '<f4'),
            periods=periods, new_periods=new_periods, volumes=volumes, new_volumes=new_volumes, noise=noise, new_noise=new_noise,
            rms=rms, explained=explained, notes=notes, share=share)
        record['artifacts']['analysis.npz'] = sha((directory/'analysis.npz').read_bytes())
        # Equal-RMS previews keep the comparison from favouring the louder mix.
        levels = {name: np.sqrt(np.mean(signal**2)) for name, signal in signals.items()}
        target = min(.10, *(.9*levels[name]/max(float(np.max(np.abs(signal))), 1e-12)
                            for name, signal in signals.items()))
        for name, signal in signals.items():
            path = directory/f'{name}.wav'
            quality.write_wav(path, signal*target/max(levels[name], 1e-12), rate)
            record['artifacts'][path.name] = sha(path.read_bytes())
        record['preview_common_rms'] = float(target)
        report['windows'].append(record)
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps({key: record[key] for key in ['start_seconds', 'metrics', 'noise_ticks']}), flush=True)


if __name__ == '__main__':
    main()
