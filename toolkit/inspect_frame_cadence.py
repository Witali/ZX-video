"""Measure six-field cadence and localize the worst frame intervals in Fuse."""
import argparse
import json
from pathlib import Path

FIELD_TSTATES = 70908  # Fuse Spectrum 128, also used by measure_fuse.py.
MAX_JITTER_MS = 1.0


def inspect(metadata, traces):
    if len(metadata['volumes']) != len(traces):
        raise ValueError('one complete trace per volume is required')
    rows = []
    for volume, trace in zip(metadata['volumes'], traces):
        stamps = trace['frame_timestamps']
        if len(stamps) != volume['frames'] or len(stamps) < 2:
            raise ValueError('frame count does not match volume')
        intervals = [b - a for a, b in zip(stamps, stamps[1:])]
        assert intervals == trace['frame_interval_tstates']
        field_gaps = [b // FIELD_TSTATES - a // FIELD_TSTATES for a, b in zip(stamps, stamps[1:])]
        worst = []
        for index in sorted(range(len(intervals)), key=lambda i: abs(intervals[i] - 6 * FIELD_TSTATES), reverse=True)[:5]:
            a, b = stamps[index:index + 2]
            prepared = trace['frame_prepared_timestamps'][index]
            calls = [(kind, cycles) for frame, kind, cycles in zip(trace['rom_call_entry_frames'], trace['rom_call_kinds'], trace['rom_call_tstates']) if frame == index]
            worst.append(dict(frame=volume['frame_start'] + index + 1,
                              interval_ms=intervals[index] * 1000 / trace['clock_hz'],
                              preparation_ms=(prepared - a) * 1000 / trace['clock_hz'],
                              after_preparation_ms=(b - prepared) * 1000 / trace['clock_hz'],
                              fields=field_gaps[index], rom_calls=calls))
        flips = trace.get('screen_flip_timestamps', [])
        if flips and len(flips) != len(stamps) - 1:
            raise ValueError('incomplete screen flip trace')
        flip_intervals = [b - a for a, b in zip(flips, flips[1:])]
        flip_fields = [b // FIELD_TSTATES - a // FIELD_TSTATES for a, b in zip(flips, flips[1:])]
        jitter = max(abs(value - 6 * FIELD_TSTATES) for value in intervals + flip_intervals)
        rows.append(dict(file=volume['trd_name'], frames=len(stamps), intervals=len(intervals),
                         clock_hz=trace['clock_hz'],
                         mean_ms=sum(intervals) * 1000 / trace['clock_hz'] / len(intervals),
                         maximum_ms=max(intervals) * 1000 / trace['clock_hz'],
                         minimum_ms=min(intervals) * 1000 / trace['clock_hz'],
                         non_six_field_intervals=sum(gap != 6 for gap in field_gaps),
                         maximum_jitter_tstates=jitter,
                         maximum_jitter_ms=jitter * 1000 / trace['clock_hz'],
                         measured_screen_flips=len(flips),
                         non_six_field_screen_flips=sum(gap != 6 for gap in flip_fields),
                         maximum_flip_interval_ms=max(flip_intervals, default=0) * 1000 / trace['clock_hz'],
                         minimum_flip_interval_ms=min(flip_intervals, default=0) * 1000 / trace['clock_hz'],
                         worst=worst))
    return dict(scope='Frame timestamps are main_loop entry after the screen flip; startup frame zero uses the audio-start anchor. Disk swaps excluded.',
                flip_scope='OUT (C),A completion at 7FFD; first startup screen excluded because it is already visible before audio starts.',
                frames=sum(row['frames'] for row in rows), fields_per_frame=6,
                nominal_fps=50 / 6, field_tstates=FIELD_TSTATES,
                non_six_field_intervals=sum(row['non_six_field_intervals'] for row in rows),
                non_six_field_screen_flips=sum(row['non_six_field_screen_flips'] for row in rows),
                measured_screen_flips=sum(row['measured_screen_flips'] for row in rows),
                expected_screen_flips=sum(row['frames'] - 1 for row in rows),
                maximum_jitter_ms=max(row['maximum_jitter_ms'] for row in rows),
                jitter_limit_ms=MAX_JITTER_MS,
                maximum_ms=max(row['maximum_ms'] for row in rows),
                minimum_ms=min(row['minimum_ms'] for row in rows), volumes=rows)


def require_smooth(report):
    """Reject missed/repeated fields and local timing excursions over 1 ms."""
    if report['measured_screen_flips'] != report['expected_screen_flips']:
        raise ValueError('direct screen flip timestamps are required')
    if report['non_six_field_intervals'] or report['non_six_field_screen_flips']:
        raise ValueError('screen changes must occur every six hardware fields')
    if report['maximum_jitter_ms'] > MAX_JITTER_MS:
        raise ValueError('video interval differs from six hardware fields by more than 1 ms')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path)
    p.add_argument('--timing', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--require-smooth', action='store_true')
    args = p.parse_args()
    report = inspect(json.loads((args.build / 'build_metadata.json').read_text()), json.loads(args.timing.read_text()))
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'volumes'}, indent=2))
    print(json.dumps(sorted((item for row in report['volumes'] for item in row['worst']), key=lambda item: item['interval_ms'], reverse=True)[:5], indent=2))
    if args.require_smooth:
        require_smooth(report)


if __name__ == '__main__':
    main()
