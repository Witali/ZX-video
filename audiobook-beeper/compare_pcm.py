"""Compare live PDM reconstruction and diagnose unequal output hold lengths."""
import argparse
import gzip
import json
import subprocess
from pathlib import Path

import numpy as np

from build_pdm import RATE, reconstruct
from verify_pcm import native_intervals, reference, save

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--output', type=Path, default=HERE/'pcm-comparison.json')
    args = parser.parse_args()

    def filtered(values):
        result = subprocess.run([
            args.ffmpeg, '-v', 'error', '-nostdin', '-f', 'f32le', '-ar', str(RATE),
            '-ac', '1', '-i', '-', '-af',
            'highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2',
            '-ar', '44100', '-f', 'f32le', '-',
        ], input=values.astype('<f4').tobytes(), capture_output=True, check=True)
        return np.frombuffer(result.stdout, '<f4')[4410:-4410].astype(float)

    results = {}
    source = None
    for name, directory in [('fast', HERE/'experiments/pcm-live-fast'),
                            ('steady', HERE/'pcm-live-preview')]:
        meta = json.loads((directory/'player.json').read_bytes())
        pcm = gzip.decompress((directory/'soundtrack.pcm.gz').read_bytes())
        if source is not None and source != pcm:
            raise ValueError('comparison PCM differs')
        source = pcm
        count = meta['bits_per_cycle']
        bits, _ = reference(pcm, oversample=meta['oversample'])
        indices = np.maximum(np.arange(count)-3, 0)//meta['oversample']
        levels = np.frombuffer(pcm, np.uint8)[indices].astype(float)/256
        levels[:3] = 0
        actual = np.frombuffer(gzip.decompress((directory/'output-times.u32.gz').read_bytes()), '<u4')[:count+1]
        schedules = {'fuse': actual}
        if name == 'fast':
            schedules.update(
                uniform=np.round(np.arange(count+1)*meta['deterministic_cycle_tstates']/count).astype(np.int64),
                native=np.r_[0, np.cumsum(native_intervals(meta))],
            )
        for schedule, times in schedules.items():
            expected = filtered(reconstruct(levels, times))
            signal = filtered(reconstruct(bits[:count], times))
            results[f'{name}_{schedule}'] = dict(
                reconstruction_snr_db=float(10*np.log10(np.mean(expected**2)/np.mean((signal-expected)**2))),
                waveform_correlation=float(np.corrcoef(expected, signal)[0, 1]),
                actual_port_schedule=schedule == 'fuse',
            )
    report = dict(date='2026-10-02', same_pcm_bytes=True, results=results,
                  snr_gain_db=results['steady_fuse']['reconstruction_snr_db']-results['fast_fuse']['reconstruction_snr_db'],
                  scope='conversion error against each schedule-aligned PCM reference; clocks differ; not intelligibility')
    save(args.output, report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
