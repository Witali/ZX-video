"""Archive complete same-boundary FAP3 disk-reader measurements and compare them.

Does not publish disk images or declare a release. I/O windows include ROM,
emulated disk waits, interrupts and contention; deterministic RAM CPU is
reported independently by benchmark_fap3_disk.py.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HZ = 50 * 70908


def read(path):
    return json.loads(path.read_text())


def metrics(report):
    pubs = report['publications']
    elapsed = (pubs[-1]['tstate'] - pubs[0]['tstate']) / HZ
    io = {}
    for kind in ('trdos', 'direct503'):
        rows = [r for r in report['reads'] if r.get('kind', 'trdos') == kind]
        io[kind] = dict(calls=len(rows), window_seconds=sum(r['tstates'] for r in rows) / HZ)
    return dict(actual_fps=(len(pubs)-1)/elapsed,
        first_to_last_seconds=elapsed,
        nominal_late_frames=report['nominal_late_frames'],
        max_late_fields=report['max_late_fields'],
        actual_out_over_one_field=report['actual_out_over_one_field'],
        max_actual_deviation_seconds=report['max_actual_deviation_tstates']/HZ,
        bad_actual_intervals=report['bad_actual_intervals'],
        recovered_late_runs=sum(r['recovered_at'] is not None for r in report['late_runs']),
        unrecovered_late_runs=sum(r['recovered_at'] is None for r in report['late_runs']),
        audio_underruns=report['audio_underruns'],io=io)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'baseline', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []; next_frame = 0
    for part in range(1, 5):
        stem = f'ZX-video-optimized-preview_part{part:02}'
        meta = read(args.build/(stem+'.json'))
        current = read(args.build/f'fuse_part{part:02}.json')
        old_meta = read(args.baseline/f'part{part:02}.json')
        old = read(args.baseline/f'fuse_part{part:02}.json')
        digest = hashlib.sha256((args.build/(stem+'.trd')).read_bytes()).hexdigest()
        assert digest == meta['trd_sha256'] == current['trd_sha256']
        assert current['complete'] and old['complete'] and not current['errors']
        assert meta['frame_start'] == next_frame
        for key in ('frame_start','frame_end_exclusive','raw_sha256','states_sha256','video_bytes','used_sectors'):
            assert meta[key] == old_meta[key], key
        next_frame = meta['frame_end_exclusive']
        rows.append(dict(part=part,frames=meta['frames'],video_bytes=meta['video_bytes'],
            used_sectors=meta['used_sectors'],previous=metrics(old),current=metrics(current)))
        shutil.copyfile(args.build/(stem+'.json'), args.output/f'part{part:02}.json')
        shutil.copyfile(args.build/f'fuse_part{part:02}.json', args.output/f'fuse_part{part:02}.json')
    assert next_frame == 4221
    for name in ('cpu.json','swap_checks.json','prompt_fuse.json'):
        shutil.copyfile(args.build/name, args.output/name)
    result = dict(baseline_commit='63cc07d',status='optional experiment; timing FAILED',release=False,
        frames=next_frame,ay_records=next_frame*6,pixel_changes=False,ay_changes=False,
        full_pixel_comparison=False,pixel_samples_per_frame=80,
        default_enabled=False,root_images_replaced=False,physical_drive_verified=False,
        io_window_scope='Includes ROM, emulated disk waits, IRQ and ULA; not deterministic player CPU',
        volumes=rows)
    (args.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
