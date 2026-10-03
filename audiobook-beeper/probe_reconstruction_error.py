"""Separate timing reconstruction, codec, six-bit selection and PDM errors.

Uses saved complete Fuse timelines. Fitted gain is a diagnosis only, never
the acceptance score. This does not assemble or verify a new player.
"""
import argparse
import gzip
import io
import json
from pathlib import Path
import subprocess
import wave
import numpy as np
from build_pdm import reconstruct, RATE
from assess_snr import FILTER, ratio
from verify_direct import reference, sample_positions
from pdm_player import CPU_CLOCK


def wav8(path):
    data = path.read_bytes() if path.is_file() else gzip.decompress(Path(str(path) + '.gz').read_bytes())
    with wave.open(io.BytesIO(data), 'rb') as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 1, 8000)
        return np.frombuffer(wav.readframes(wav.getnframes()), 'u1')


def filtered(signal, ffmpeg):
    run = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-f', 'f32le', '-ar', str(RATE),
                          '-ac', '1', '-i', '-', '-af', FILTER, '-ar', '44100', '-f', 'f32le', '-'],
                         input=np.asarray(signal, dtype='<f4').tobytes(), capture_output=True, check=True)
    return np.frombuffer(run.stdout, '<f4').astype(float)


def inspect(path, ffmpeg):
    meta = json.loads((path / 'player.json').read_bytes())
    packed = gzip.decompress((path / 'soundtrack.ima.gz').read_bytes())
    pcm, _, _, bits = reference(packed, model=meta['model'], idle_pairs=meta['loop_idle_pairs'])
    count = meta['outputs_per_cycle']
    times = np.frombuffer(gzip.decompress((path / 'output-times.u32.gz').read_bytes()), '<u4').astype(np.int64)[:count + 1]
    times -= times[0]
    bounds = times[sample_positions(meta)]
    source = wav8(path / 'source-preview.wav')
    target = wav8(path / 'compensated-pcm.wav')
    period = CPU_CLOCK / 8000
    segments = int(np.ceil(times[-1] / period))
    fixed_bounds = np.r_[np.arange(segments) * period, times[-1]]
    fixed_levels = np.pad(source / 256, (0, max(0, segments - len(source))), constant_values=.5)[:segments]
    signals = {'original': filtered(reconstruct(fixed_levels, fixed_bounds), ffmpeg)}
    for name, values in [('timing_target', target / 256), ('ima_pcm16', (pcm.astype(float) + 32768) / 65536),
                         ('six_bit_level', (np.floor((pcm.astype(float) + 32768) / 1024) + .5) / 64)]:
        signals[name] = filtered(reconstruct(values, bounds), ffmpeg)
    signals['pdm'] = filtered(reconstruct(bits[:count], times), ffmpeg)
    trimmed = {k: v[4410:-4410] for k, v in signals.items()}
    ref = trimmed['original']
    rows = []
    for name, signal in trimmed.items():
        if name == 'original':
            continue
        gain = float(np.dot(ref, signal) / np.dot(signal, signal))
        rows.append(dict(stage=name, fixed_clock_snr_db=ratio(ref, signal - ref),
                         error_rms=float(np.sqrt(np.mean((signal - ref) ** 2))),
                         diagnostic_fitted_gain=gain,
                         diagnostic_gain_corrected_snr_db=ratio(ref, signal * gain - ref)))
    windows = []
    for start in range(0, len(ref) - 44100, 44100):
        sl = slice(start, start + 44100)
        windows.append(dict(start_seconds=.1 + start / 44100,
                            signal_rms=float(np.std(ref[sl])),
                            snr_db=ratio(ref[sl], trimmed['pdm'][sl] - ref[sl])))
    return dict(scope=__doc__,input=str(path),samples=len(source),rows=rows,one_second_windows=windows,
                source_rms=float(np.std(ref)),
                pdm_relative_to_six_bit_snr_db=ratio(trimmed['six_bit_level'], trimmed['pdm']-trimmed['six_bit_level']),
                filter=FILTER,reference_rate_hz=8000,new_player_verified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',action='append',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    for path in a.input:
        result=inspect(path,a.ffmpeg)
        (a.output/(path.name+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(json.dumps({k:v for k,v in result.items() if k!='one_second_windows'}),flush=True)


if __name__=='__main__':main()
