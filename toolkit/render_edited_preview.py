"""Render exact retained screens with an approximate AY soundtrack for review.

This PC preview is not a Spectrum timing test. Audio is synthesized before
selecting the excerpt so AY oscillator/noise phase continues across the edit.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np

import ay_fidelity
import build_long_video_trd as video
from compare_ay_fidelity import write_wav
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--ffmpeg', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--first-frame', type=int, default=0)
    args = p.parse_args()
    with np.load(args.build/'source/conversion.npz', allow_pickle=False) as saved:
        states = saved['states']
    raw = (args.build/'audio/50Hz/raw.bin').read_bytes()
    if not 0 <= args.first_frame < len(states) or len(raw) != len(states)*54:
        raise ValueError('invalid excerpt or AY length')
    frames = [video.AyFrame.deserialize(raw[i:i+9]) for i in range(0, len(raw), 9)]
    rate = 22050
    samples = ay_fidelity.render(frames, 50, rate)[args.first_frame*2646:]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as folder:
        folder = Path(folder)
        wav = folder/'audio.wav'
        write_wav(wav, samples, rate)
        command = [str(args.ffmpeg.resolve()), '-y', '-hide_banner', '-loglevel', 'error',
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '256x192', '-r', '25/3', '-i', '-',
            '-i', str(wav), '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
            str(args.output.resolve())]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        try:
            for state in states[args.first_frame:]:
                bitmap, attrs = video.expand_compact_screen(state.tobytes())
                process.stdin.write(video.base.render_spectrum_screen(bitmap, attrs).tobytes())
            process.stdin.close()
            if process.wait():
                raise RuntimeError('ffmpeg preview failed')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    args.output.with_suffix('.json').write_text(json.dumps(dict(scope=__doc__,
        first_frame=args.first_frame, frames=len(states)-args.first_frame,
        duration_seconds=(len(states)-args.first_frame)*3/25,
        input_states_sha256=sha(states.tobytes()), input_ay_sha256=sha(raw)), indent=2)+'\n', encoding='utf-8')
    print(args.output, flush=True)


if __name__ == '__main__':
    main()
