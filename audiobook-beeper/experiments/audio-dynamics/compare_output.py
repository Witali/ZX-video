"""Compare completed conditioned output with the saved peak-only disk.

Both SNRs are relative to their own prepared signals: intentional compression
is not a coding error. Reuse the earlier cyclic-error diagnostic unchanged;
this is not a pitch tracker or a substitute for normal-speed listening.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'ima4-flutter'))
from analyze import wav, waveform_metrics
from audit_direct_regression import fixed_reference
from build_pdm import write_wav


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ffmpeg', required=True)
    a = p.parse_args()
    hashes = json.loads((HERE/'artifact-hashes.json').read_bytes())

    def read(name):
        data = (HERE/name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == hashes[name], name
        return data

    report = json.loads(read('release/report.json'))
    old_report_data = (HERE.parent/'ima4-full-disk/release/report.json').read_bytes()
    old_diagnostic_data = (HERE.parent/'ima4-flutter/analysis.json').read_bytes()
    old_hashes = json.loads((HERE.parent/'ima4-full-disk/artifact-hashes.json').read_bytes())
    diagnostic_hashes = json.loads((HERE.parent/'ima4-flutter/manifest.json').read_bytes())
    assert hashlib.sha256(old_report_data).hexdigest() == old_hashes['release/report.json']
    assert hashlib.sha256(old_diagnostic_data).hexdigest() == diagnostic_hashes['analysis.json']
    old_report = json.loads(old_report_data)
    old_diagnostics = json.loads(old_diagnostic_data)
    assert report['complete'] and report['retained_source_samples'] == old_report['retained_source_samples']
    rows = []
    for number, result in enumerate(report['verification']['volumes'][0]['parts'], 1):
        source, rate = wav(read(f'selected/part-{number:05d}/source-preview.wav'))
        assert rate == 8000
        timeline = np.frombuffer(gzip.decompress(read(
            f'release/verification/cold-0001/part-{number:02d}-times.u32.gz')), '<u4')
        actual, rate = wav(read(f'release/verification/cold-0001/part-{number:02d}-output.wav'))
        assert rate == 44100
        fixed = fixed_reference(np.rint(source*128+128).astype('u1'),
                                int(timeline[-1])-int(timeline[0]), 8000, a.ffmpeg)
        metrics = waveform_metrics(fixed, actual)
        old = old_report['verification']['volumes'][0]['parts'][number-1]
        old_metric = old_diagnostics['waveform_diagnostics'][number-1]
        rows.append(dict(part=number, previous_output_snr_db=old['fixed_clock_snr_db'],
            output_snr_db=result['fixed_clock_snr_db'],
            snr_difference_db=result['fixed_clock_snr_db']-old['fixed_clock_snr_db'],
            old_cyclic_error_power_max_min=old_metric['cyclic_error_power_max_min'],
            diagnostics=metrics))
        if number == 1:
            write_wav(HERE/'conditioned-output-first8.wav', actual[:8*44100])
        print(json.dumps(dict(part=number, snr_db=result['fixed_clock_snr_db'],
                              cyclic_power_ratio=metrics['cyclic_error_power_max_min'])), flush=True)
    output = dict(date='2026-10-05', parts=rows,
        scope='Matched source ranges and measurement filter; each disk uses its own prepared reference. Cyclic diagnostics use PCM16 listening WAVs; release SNR uses unquantized reconstructed output.',
        limitation='No new host endpoint capture or claim that perceived vibration is eliminated.',
        previous_report_sha256=hashlib.sha256((HERE.parent/'ima4-full-disk/release/report.json').read_bytes()).hexdigest(),
        previous_diagnostics_sha256=hashlib.sha256((HERE.parent/'ima4-flutter/analysis.json').read_bytes()).hexdigest())
    (HERE/'output-comparison.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
