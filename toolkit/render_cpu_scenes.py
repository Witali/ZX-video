"""Render five-frame source/candidate/difference strips around CPU hotspots.

This inspects selected scenes, not the whole movie in motion. Source means
accepted Spectrum frames; no comparison with the original HD master.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from probe_exact_dictionary import STATES_SHA256
from probe_lossless_layouts import sha
from review_bounded_dictionary import render, ssim


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--cpu-report', type=Path, required=True)
    p.add_argument('--events', type=int, nargs='+', required=True)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    with np.load(args.reference, allow_pickle=False) as saved:
        reference = saved['states']
    with np.load(args.candidate, allow_pickle=False) as saved:
        candidate = saved['states']
    cpu = json.loads(args.cpu_report.read_text(encoding='utf-8'))
    if (sha(reference.tobytes()) != STATES_SHA256 or candidate.shape != reference.shape
            or not cpu['complete'] or len(cpu['frames']) != len(candidate)
            or sha(candidate.tobytes()) != cpu['states_sha256']):
        raise ValueError('source/candidate/CPU coverage differs')
    if any(not 2 <= event < len(candidate)-2 for event in args.events):
        raise ValueError('event cannot form a five-frame strip')
    sheet = Image.new('RGB', (1280, len(args.events)*624), (24, 24, 24))
    draw, rows = ImageDraw.Draw(sheet), []
    for index, event in enumerate(args.events):
        y = index*624
        draw.text((6, y+4), f'Event {event}: reference / candidate / changed RGB', fill='white')
        for column, frame in enumerate(range(event-2, event+3)):
            a, b = render(reference[frame]), render(candidate[frame])
            changed = np.any(a != b, axis=2)
            diff = np.zeros_like(a); diff[changed] = [255, 70, 70]
            score = ssim(a[24:168], b[24:168])
            ticks = cpu['frames'][frame]['total_tstates']
            draw.text((column*256+6, y+24), f'{frame}: {ticks} T, SSIM {score:.6f}', fill='white')
            for row, pixels in enumerate((a, b, diff)):
                sheet.paste(Image.fromarray(pixels), (column*256, y+48+row*192))
            rows.append(dict(event=event, frame=frame, tstates=ticks, ssim=score,
                changed_rgb_active_pixels=int(changed[24:168].sum())))
    sheet.save(args.image)
    report = dict(scope=__doc__, complete=True, reference_sha256=STATES_SHA256,
        candidate_sha256=cpu['states_sha256'], cpu_input_sha256=cpu['input_sha256'],
        events=args.events, frames=rows, image_sha256=sha(args.image.read_bytes()),
        full_motion_viewing_complete=False)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(events=args.events, inspected_frames=len(rows))))


if __name__ == '__main__':
    main()
