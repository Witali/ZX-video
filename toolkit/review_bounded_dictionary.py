"""Measure active-area luma SSIM and render the worst dictionary comparisons.

SSIM: 11x11 Gaussian window, sigma=1.5, population covariance,
C1=(.01*255)^2, C2=(.03*255)^2; average the valid window centres.
Reference is the accepted Spectrum rendering, not the original movie.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import build_long_video_trd as video
from build_zxv_trd import render_spectrum_screen
from probe_exact_dictionary import STATES_SHA256


def render(state):
    return render_spectrum_screen(*video.expand_compact_screen(state.tobytes()))


def ssim(first, second):
    if np.array_equal(first, second):
        return 1.0
    weights = np.array([0.299, 0.587, 0.114])
    first = first.astype(float) @ weights
    second = second.astype(float) @ weights
    blur = lambda image: cv2.GaussianBlur(image, (11, 11), 1.5)
    x, y = blur(first), blur(second)
    vx = np.maximum(blur(first * first) - x * x, 0)
    vy = np.maximum(blur(second * second) - y * y, 0)
    cov = blur(first * second) - x * y
    score = ((2*x*y + 6.5025)*(2*cov + 58.5225)) / ((x*x + y*y + 6.5025)*(vx + vy + 58.5225))
    return float(np.mean(score[5:-5, 5:-5]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--contact-sheet', type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.reference) as saved:
        reference = saved['states'].astype(np.uint8)
    with np.load(args.candidate) as saved:
        candidate = saved['states'].astype(np.uint8)
    if hashlib.sha256(reference.tobytes()).hexdigest() != STATES_SHA256 or candidate.shape != reference.shape:
        raise ValueError('unexpected reference/candidate')
    scores = []
    for frame, (first, second) in enumerate(zip(reference, candidate)):
        scores.append(ssim(render(first)[24:168], render(second)[24:168]))
        if frame % 500 == 0:
            print(f'SSIM {frame}/{len(reference)}', flush=True)
    order = np.argsort(scores)[:6]
    # Columns: reference, candidate, red mask of actual differing RGB pixels.
    sheet = Image.new('RGB', (256 * 3, (192 + 24) * len(order)), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for row, frame in enumerate(order):
        first, second = render(reference[frame]), render(candidate[frame])
        mask = np.zeros_like(first)
        mask[np.any(first != second, axis=2)] = [255, 70, 70]
        y = row * 216
        draw.text((6, y + 5), f'Frame {frame}: reference | candidate | changed RGB; SSIM {scores[frame]:.6f}', fill='white')
        for col, pixels in enumerate((first, second, mask)):
            sheet.paste(Image.fromarray(pixels), (col * 256, y + 24))
    args.contact_sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.contact_sheet)
    report = dict(scope=__doc__, frames=len(reference), reference_sha256=STATES_SHA256,
                  candidate_sha256=hashlib.sha256(candidate.tobytes()).hexdigest(),
                  mean_ssim=float(np.mean(scores)), minimum_ssim=float(min(scores)),
                  percentile_1_ssim=float(np.percentile(scores, 1)),
                  worst_frames=[dict(frame=int(i), ssim=scores[i]) for i in order],
                  contact_sheet=args.contact_sheet.name, frame_ssim=scores,
                  temporal_motion_review_complete=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'frame_ssim'}), flush=True)


if __name__ == '__main__':
    main()
