"""Measure displayed-frame quality and changes between adjacent frames.

Reference is the accepted Spectrum movie, not the original HD source.
Active area is 256x144. Missing changes: source RGB changes at a pixel but
candidate RGB does not. Spurious changes: source RGB is constant but candidate
RGB changes. These are pixel-transition diagnostics, not optical-flow scores
or a claim of perceptual equivalence. Filmstrips cover selected short scenes.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from probe_exact_dictionary import STATES_SHA256
from probe_lossless_layouts import sha
from review_bounded_dictionary import render, ssim


def transition_counts(previous_reference, reference, previous_candidate, candidate):
    actual = np.any(reference != previous_reference, axis=2)
    obtained = np.any(candidate != previous_candidate, axis=2)
    return dict(source_changes=int(actual.sum()), missing_changes=int((actual & ~obtained).sum()),
                spurious_changes=int((~actual & obtained).sum()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--filmstrip', type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.reference) as saved:
        reference = saved['states'].astype(np.uint8)
    with np.load(args.candidate) as saved:
        candidate = saved['states'].astype(np.uint8)
    if sha(reference.tobytes()) != STATES_SHA256 or candidate.shape != reference.shape:
        raise ValueError('unexpected reference/candidate')
    rows = []
    pixel_ages = np.zeros((144, 256), dtype=np.int32)
    cell_ages = np.zeros((18, 32), dtype=np.int32)
    pixel_peak = cell_peak = 0
    previous_reference = previous_candidate = None
    for frame, (old, new) in enumerate(zip(reference, candidate)):
        first, second = render(old)[24:168], render(new)[24:168]
        different = np.any(first != second, axis=2)
        cell_different = different.reshape(18, 8, 32, 8).any(axis=(1, 3))
        pixel_ages = np.where(different, pixel_ages + 1, 0)
        cell_ages = np.where(cell_different, cell_ages + 1, 0)
        pixel_peak = max(pixel_peak, int(pixel_ages.max()))
        cell_peak = max(cell_peak, int(cell_ages.max()))
        transitions = (transition_counts(previous_reference, first, previous_candidate, second)
                       if frame else dict(source_changes=0, missing_changes=0, spurious_changes=0))
        rows.append(dict(frame=frame, ssim=ssim(first, second), changed_rgb_pixels=int(different.sum()), **transitions))
        previous_reference, previous_candidate = first, second
        if frame % 500 == 0:
            print(f'Motion quality: {frame}/{len(reference)}', flush=True)
    scores = [row['ssim'] for row in rows]
    worst_ssim = min(range(len(rows)), key=lambda i: scores[i])
    worst_missing = max(range(1, len(rows)), key=lambda i: rows[i]['missing_changes'])
    worst_spurious = max(range(1, len(rows)), key=lambda i: rows[i]['spurious_changes'])
    events = list(dict.fromkeys([worst_ssim, worst_missing, worst_spurious]))
    # Five adjacent frames, reference/candidate/difference rows per event.
    sheet = Image.new('RGB', (5 * 256, len(events) * (3 * 192 + 48)), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    strips = []
    for index, event in enumerate(events):
        first_frame = min(max(0, event - 2), len(reference) - 5)
        selected = list(range(first_frame, first_frame + 5))
        strips.append(dict(event=event, frames=selected))
        y = index * (3 * 192 + 48)
        draw.text((6, y + 4), f'Event {event}: reference / candidate / changed RGB', fill='white')
        for col, frame in enumerate(selected):
            first, second = render(reference[frame]), render(candidate[frame])
            mask = np.zeros_like(first)
            mask[np.any(first != second, axis=2)] = [255, 70, 70]
            draw.text((col * 256 + 6, y + 24), f'Frame {frame}, SSIM {scores[frame]:.6f}', fill='white')
            for row, pixels in enumerate((first, second, mask)):
                sheet.paste(Image.fromarray(pixels), (col * 256, y + 48 + row * 192))
    args.filmstrip.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.filmstrip)
    total_source = sum(row['source_changes'] for row in rows)
    report = dict(scope=__doc__, reference_sha256=STATES_SHA256,
                  candidate_sha256=sha(candidate.tobytes()), frames=len(reference),
                  mean_ssim=float(np.mean(scores)), minimum_ssim=float(min(scores)),
                  percentile_1_ssim=float(np.percentile(scores, 1)),
                  max_consecutive_pixel_error_frames=pixel_peak,
                  max_consecutive_cell_error_frames=cell_peak,
                  mean_missing_change_pixels=float(np.mean([x['missing_changes'] for x in rows[1:]])),
                  mean_spurious_change_pixels=float(np.mean([x['spurious_changes'] for x in rows[1:]])),
                  source_change_pixels_total=total_source,
                  missing_source_changes_fraction=sum(x['missing_changes'] for x in rows) / total_source if total_source else 0,
                  worst_events=[rows[i] for i in events], filmstrips=strips,
                  full_motion_viewing_complete=False, per_frame=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # One JSON line per frame keeps the report compact and individually diffable.
    summary = json.dumps({k: v for k, v in report.items() if k != 'per_frame'}, indent=2)
    args.output.write_text(summary[:-2] + ',\n  "per_frame": [\n' +
                           ',\n'.join('    ' + json.dumps(row) for row in rows) + '\n  ]\n}\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'per_frame'}), flush=True)


if __name__ == '__main__':
    main()
