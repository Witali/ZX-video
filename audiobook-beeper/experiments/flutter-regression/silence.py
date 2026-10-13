"""Measure actual beeper noise for zero PCM on independent two-loop clocks."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parents[2]/'toolkit')]
import convert_audio
from measure_comparison import measure


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--fuse', type=Path, required=True)
    p.add_argument('--ffmpeg', required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    model = dict(convert_audio.MEASURED_MODEL)
    model.pop('pcm_origin', None)
    report = dict(complete=False, input='8192 exact PCM8 zero samples, packed IMA4 zeros', arms=[])
    for label, origin in (('midpoint', .5), ('zero-floor', 0)):
        convert_audio.MEASURED_MODEL = dict(model, pcm_origin=origin)
        candidate, _ = convert_audio.calibrate(a.output/label, bytes(4096), np.full(8192,128,dtype='u1'), a.fuse)
        convert_audio.validate(candidate, a.fuse, a.ffmpeg)
        row = measure(candidate, a.repository, a.ffmpeg, a.output, label)
        report['arms'].append(row)
        print(json.dumps(dict(label=label, noise_rms=[x['error_rms'] for x in row['loops']])), flush=True)
        (a.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    report['complete'] = True
    (a.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
