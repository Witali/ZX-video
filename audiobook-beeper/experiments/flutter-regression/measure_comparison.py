"""Measure complete, verified candidate traces without fitted listening gains."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import runpy
import wave

import numpy as np

from audit import read, metrics, BEEPER, CPU, FIELD
from audit_direct_regression import fixed_reference
from convert_mulaw_audio import filter_signal, STABLE_FILTER
from verify_direct import reference, expand_samples
from build_pdm import write_wav


def measure(path, repository, ffmpeg, output, label):
    hashes = {}
    def data(name):
        value = read(path / name, repository)
        hashes[name] = hashlib.sha256(value).hexdigest()
        return value
    meta = json.loads(data('player.json'))
    native = json.loads(data('native.json'))
    fuse = json.loads(data('fuse.json'))
    assert native['complete'] and fuse['complete'] and fuse['cycles_verified'] == 2
    assert fuse['every_pdm_bit_exact'] and fuse['every_predictor_and_index_exact']
    packed = gzip.decompress(data('soundtrack.ima.gz'))
    assert hashlib.sha256(packed).hexdigest() == meta['packed_sha256']
    with wave.open(io.BytesIO(data('source-preview.wav')), 'rb') as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 1, 8000)
        source = np.frombuffer(w.readframes(w.getnframes()), 'u1')
    timeline = np.frombuffer(gzip.decompress(data('output-times.u32.gz')), '<u4').astype(np.int64)
    count = meta['outputs_per_cycle']
    assert len(timeline) == count * 2 + 1
    pcm, _, levels, bits = reference(packed, cycles=2, model=meta['model'], idle_pairs=meta['loop_idle_pairs'])
    assert len(source) == len(pcm)
    cyclic_fit = runpy.run_path(str(BEEPER / 'experiments/ima4-flutter/analyze.py'))['cyclic_fit']
    loops = []
    for loop in range(2):
        times = timeline[count*loop:count*(loop+1)+1].copy()
        times -= times[0]
        actual = filter_signal(bits[count*loop:count*(loop+1)], times, ffmpeg, 768000)
        fixed = fixed_reference(source, times[-1], 8000, ffmpeg)
        held = filter_signal(expand_samples(meta, levels)/256., times, ffmpeg, 768000)
        result = metrics(fixed, actual)
        result.update(loop=loop+1, pdm_only=metrics(held, actual),
            field_modulation=(cyclic_fit(fixed, actual, CPU/FIELD) if np.std(fixed)>1e-12 else None))
        loops.append(result)
        if loop == 0:
            write_wav(output / (label+'-output.wav'), actual)
            write_wav(output / (label+'-reference.wav'), fixed)
    return dict(label=label, path=str(path), source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
        model=meta['model'], source_files=hashes, native_and_cold_fuse_complete=True,
        loops=loops)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate', nargs=2, action='append', metavar=('LABEL', 'DIRECTORY'), required=True)
    parser.add_argument('--ffmpeg', required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    report = dict(complete=False, filter=STABLE_FILTER, field_hz=CPU/FIELD,
        physical_hardware_tested=False, candidates=[])
    for label, name in args.candidate:
        row = measure(Path(name), args.repository, args.ffmpeg, args.output, label)
        report['candidates'].append(row)
        print(json.dumps(dict(label=label, loops=[{k:v for k,v in x.items()
            if k not in ('field_error_power', 'pdm_only')} for x in row['loops']])), flush=True)
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    report['complete'] = True
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
