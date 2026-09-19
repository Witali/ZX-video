"""Save timestamped source-frame sheets to inspect a proposed credit cut."""
import argparse
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    inputs = p.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--source', type=Path)
    inputs.add_argument('--states', type=Path, help='render converted compact states at 25/3 fps')
    p.add_argument('--ffmpeg', type=Path)
    p.add_argument('--times', nargs='+', type=float, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--width', type=int, default=384)
    p.add_argument('--columns', type=int, default=4)
    args = p.parse_args()
    if args.source and not args.ffmpeg:
        p.error('--source requires --ffmpeg')
    if args.width < 1 or args.columns < 1 or any(t < 0 for t in args.times):
        p.error('invalid sheet geometry/timestamps')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cache = args.output.parent/(args.output.stem+'_frames')
    cache.mkdir(exist_ok=True)
    thumbs = []
    if args.states:
        import numpy as np
        import build_long_video_trd as video
        with np.load(args.states, allow_pickle=False) as saved:
            states = saved['states']
    for index, seconds in enumerate(args.times):
        frame = cache/f'{index:03d}_{seconds:.3f}.png'
        if args.states:
            state = states[round(seconds*25/3)].tobytes()
            bitmap, attrs = video.expand_compact_screen(state)
            rendered = Image.fromarray(video.base.render_spectrum_screen(bitmap, attrs))
            rendered.resize((args.width, args.width*192//256), Image.Resampling.NEAREST).save(frame)
        else:
            subprocess.run([str(args.ffmpeg), '-hide_banner', '-loglevel', 'error', '-y',
                '-ss', str(seconds), '-i', str(args.source), '-frames:v', '1',
                '-vf', f'scale={args.width}:-1', str(frame)], check=True)
        with Image.open(frame) as image:
            thumbs.append(image.convert('RGB').copy())
    width, height = thumbs[0].size
    sheet = Image.new('RGB', (width*args.columns, (height+24)*((len(thumbs)+args.columns-1)//args.columns)), '#181818')
    draw = ImageDraw.Draw(sheet)
    for index, (thumb, seconds) in enumerate(zip(thumbs, args.times)):
        x, y = (index % args.columns)*width, (index//args.columns)*(height+24)
        sheet.paste(thumb, (x, y))
        draw.text((x+8, y+height+4), f'{seconds:.3f} s', fill='white')
    sheet.save(args.output)
    args.output.with_suffix('.json').write_text(json.dumps(dict(source=str((args.source or args.states).resolve()),
        times_seconds=args.times, image=str(args.output.resolve())), indent=2)+'\n', encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
