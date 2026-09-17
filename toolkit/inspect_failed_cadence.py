"""Locate the first timing excursion in a failed Fuse debugger transcript."""
import argparse
import json
from pathlib import Path
import re

from inspect_frame_cadence import FIELD_TSTATES


def inspect(text, volume, labels):
    numbers = [int(line.strip(), 0) for line in text.splitlines()
               if re.fullmatch(r'(?:0x[0-9a-fA-F]+|-?\d+)', line.strip())]
    if len(numbers) % 2: raise ValueError('unpaired trace value')
    events = list(zip(numbers[::2], numbers[1::2]))
    frames = [value for event, value in events if event == 101]
    problems = []
    for index, (a, b) in enumerate(zip(frames, frames[1:])):
        if abs(b - a - 6 * FIELD_TSTATES) > 3546.9 or b // FIELD_TSTATES - a // FIELD_TSTATES != 6:
            problems.append(dict(frame=volume['frame_start'] + index + 1, interval_ms=(b-a)/3546.9))
    pcs = [value for event, value in events if event == 197]
    return dict(volume=volume['trd_name'], volume_start=volume['frame_start'],
        displayed_frames=len(frames), last_frame=volume['frame_start']+len(frames)-1,
        failure_labels=[name for name, address in labels.items() if pcs and address == pcs[-1]],
        timing_excursions=problems,
        last_scheduler_values=[(event, value) for event, value in events if event in (108, 130, 131)][-18:])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path); p.add_argument('--volume', type=int, required=True)
    p.add_argument('--transcript', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); meta = json.loads((args.build / 'build_metadata.json').read_text())
    report = inspect(args.transcript.read_text(errors='replace'), meta['volumes'][args.volume-1], meta['player_labels'])
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
