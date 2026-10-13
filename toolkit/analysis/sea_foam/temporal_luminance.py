"""Audit pooled source-relative brightness/colour changes in quiet cells."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]/'toolkit'))
from cell_palette_quality import averaged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    args = parser.parse_args()
    old = np.load(HERE/'evidence/work/five-states.npy', mmap_mode='r')
    new = np.load(args.build/'work/five-states.npy', mmap_mode='r')
    assert old.shape == new.shape == (507, 4608)
    rgb = np.memmap(args.build/'work/frames.rgb', dtype=np.uint8, mode='r', shape=(507, 72, 128, 3))
    sums = np.zeros((2, 2));count = 0;previous = None
    for index in range(507):
        source = rgb[index].astype(float)
        outputs = [averaged(f[index].tobytes())[12:84] for f in (old, new)]
        if previous is not None:
            prior, prior_outputs = previous
            quiet = (np.max(np.abs(source-prior).reshape(18, 4, 32, 4, 3), axis=(1, 3, 4)) <= 4).repeat(4, 0).repeat(4, 1)
            count += int(quiet.sum())
            for at in range(2):
                error = (outputs[at]-source)-(prior_outputs[at]-prior)
                sums[at, 0] += float(np.mean(error**2, axis=2)[quiet].sum())
                sums[at, 1] += float(((error @ np.array([.2126, .7152, .0722]))**2)[quiet].sum())
        previous = source, outputs
    result = dict(scope='Area-averaged 2x2 samples in near-static source cells; pooled over fields; no physical-pixel temporal claim',
        quiet_logical_samples=count, legacy=dict(rgb_mse=float(sums[0, 0]/count), luma_mse=float(sums[0, 1]/count)),
        stable=dict(rgb_mse=float(sums[1, 0]/count), luma_mse=float(sums[1, 1]/count)))
    (args.build/'luminance-temporal-check.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
