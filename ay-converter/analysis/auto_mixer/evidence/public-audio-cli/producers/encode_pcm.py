"""Encode aligned mono 22050-Hz float32 PCM using the canonical AY core."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import numpy as np
from engine import encode
from ay_format import registers
from noise_colour import downsample
import quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--profile', choices=('auto', 'music', 'legacy'), default='auto')
    parser.add_argument('--node', required=True)
    parser.add_argument('--noise-steps', type=int, default=1)
    parser.add_argument('--tuning-cents', type=float, default=50)
    args = parser.parse_args()
    samples = np.fromfile(args.input, '<f4').astype(float)
    if len(samples) % 441:
        raise ValueError('PCM must contain whole 20-ms states')
    frames, info = encode(samples, args.node, args.output, profile=args.profile,
                          noise_steps=args.noise_steps, tuning_cents=args.tuning_cents)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'ay.bin').write_bytes(b''.join(f.serialize() for f in frames))
    raw = b''.join(registers(f) for f in frames)
    (args.output/'registers.gz').write_bytes(gzip.compress(raw, mtime=0))
    subprocess.run([args.node, str(Path(__file__).with_name('render_ym2149.js')),
                    str(args.output/'registers.gz'), str(args.output/'chip.f32'), '50',
                    str(args.output/'chip-render.json')], check=True)
    rendered = downsample(np.fromfile(args.output/'chip.f32', '<f4').astype(float))
    quality.write_wav(args.output/'audio-preview.wav', rendered, 22050)
    (args.output/'chip.f32').unlink()
    (args.output/'analysis.json').write_text(json.dumps(info, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
