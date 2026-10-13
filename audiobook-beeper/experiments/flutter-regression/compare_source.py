"""Run an identical-PCM, identical-search IMA4 control/candidate comparison.

Exit 2 is the converter's recorded quality-gate failure, not a truncated run.
Every arm still requires its complete native/cold-Fuse two-loop proof.
"""
import argparse
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parents[2] / 'toolkit')]
from audit import read
import convert_audio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--arm', choices=('midpoint', 'zero-floor'), required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--fuse', required=True)
    args = parser.parse_args()
    source = args.repository / 'audiobook-beeper/experiments/ima4-full-disk/selected/part-00001/source-preview.wav'
    data = read(source, args.repository)
    assert hashlib.sha256(data).hexdigest() == '92984c2a82953bfbf5a79479099a110069227c3670c70ff02bdab2dcfa737f22'
    args.output.mkdir(parents=True, exist_ok=True)
    prepared = args.output / (args.arm + '-source.wav')
    prepared.write_bytes(data)
    model = dict(convert_audio.MEASURED_MODEL)
    model.pop('pcm_origin', None)
    if args.arm == 'zero-floor':
        model['pcm_origin'] = 0
    convert_audio.MEASURED_MODEL = model
    convert_audio.legacy_main([str(prepared), '--prepared-pcm', '--disk-mode', 'preview',
        '--quality', 'best', '--attempts', '1', '--no-refine-clock', '--no-recording',
        '--ffmpeg', args.ffmpeg, '--fuse', args.fuse,
        '--output', str(args.output / args.arm)])


if __name__ == '__main__':
    main()
