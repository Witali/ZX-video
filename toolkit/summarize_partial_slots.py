"""Archive/verify full-disk partial-slot traces, CPU costs and wait diagnostics."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from summarize_uncontended_frame import metrics


def overlap(intervals, services):
    total = index = 0
    for start, end in intervals:
        while index < len(services) and services[index][1] <= start:
            index += 1
        cursor = index
        while cursor < len(services) and services[cursor][0] < end:
            left, right = services[cursor]
            total += max(0, min(end, right)-max(start, left))
            cursor += 1
    return total


def pipeline(report, frame_start):
    events = report['pipeline_events']
    counts = Counter(row['kind'] for row in events)
    if any(counts[name] != report['frames'] for name in
           ('packet_start', 'packet_ready', 'prepare_start', 'draw_start')):
        raise ValueError('pipeline frame coverage differs')
    packet = wait = None
    frames = []
    waits = []
    previous = -1
    for row in events:
        now = row['tstate']
        if now < previous or row['page'] & 7 != 7:
            raise ValueError('unordered event or wrong bank for queue state')
        previous = now
        kind = row['kind']
        if kind == 'packet_start':
            if packet is not None:
                raise ValueError('overlapping packets')
            packet = row
        elif kind == 'packet_ready':
            if packet is None or wait is not None:
                raise ValueError('packet ends before its wait or start')
            frames.append(dict(frame=frame_start+len(frames), tstates=now-packet['tstate'],
                               count_at_start=packet['count'], phase_at_start=packet['phase']))
            packet = None
        elif kind == 'empty_wait_start':
            if wait is not None or packet is None or row['count'] != 0:
                raise ValueError('invalid synchronous wait start')
            wait = row
        elif kind == 'empty_wait_end':
            if wait is None:
                raise ValueError('wait end without start')
            if row['count'] == 0 and (row['phase'] != 2 or
                    ((row['slice_output']-0xe000) & 65535) <= row['position']):
                raise ValueError('wait ended without readable data')
            waits.append(dict(frame=frame_start+len(frames), start=wait['tstate'], end=now,
                tstates=now-wait['tstate'], phase_at_start=wait['phase'], count_at_end=row['count']))
            wait = None
    if packet is not None or wait is not None:
        raise ValueError('incomplete pipeline at EOF')
    intervals = [(w['start'], w['end']) for w in waits]
    read_time = overlap(intervals, [(r['start_tstate'], r['end_tstate']) for r in report['reads']])
    seek_time = overlap(intervals, [(r['start_tstate'], r['end_tstate']) for r in report['seek_calls']])
    return dict(events=len(events), frames=len(frames),
        packet_tstates=sum(row['tstates'] for row in frames),
        packet_start_occupancy=dict(sorted(Counter(row['count_at_start'] for row in frames).items())),
        synchronous_waits=len(waits), wait_tstates=sum(w['tstates'] for w in waits),
        wait_phase_counts=dict(sorted(Counter(w['phase_at_start'] for w in waits).items())),
        max_wait_tstates=max((w['tstates'] for w in waits), default=0),
        read_service_inside_waits_tstates=read_time, seek_service_inside_waits_tstates=seek_time,
        longest_waits=sorted(waits, key=lambda row: row['tstates'], reverse=True)[:10],
        note='Waits include Z80/ROM/IRQ/ULA/controller time. Read and seek services are not isolated physical latency.')


def summarize(cpu, reports):
    if not cpu['complete'] or cpu['checked_frames'] != 4221:
        raise ValueError('full paired CPU run required')
    volumes = []
    for part in (1, 2, 3):
        c = cpu['volumes'][part-1]
        volume = dict(part=part, cpu=c['summary'])
        for mode in ('baseline', 'partial'):
            row = reports[mode, part]
            if (not row['complete'] or row['errors'] or not row['ay_records_exact']
                    or not row['trace_nonce_exact'] or row['failure']
                    or row['trd_sha256'] != c['trd_sha256'] or row['frames'] != c['frames_expected']
                    or row.get('partial_slot_consumption', False) != (mode == 'partial')):
                raise ValueError('different source, partial run or wrong variant')
            volume[mode] = dict(metrics=metrics(row), pipeline=pipeline(row, c['frame_start']))
        volumes.append(volume)
    names = ('frames', 'nominal_late_frames', 'audio_underruns', 'ay_ticks', 'runtime_sectors',
             'read_service_tstates', 'seek_service_tstates', 'publication_span_tstates')
    totals = {mode: {name: sum(v[mode]['metrics'][name] for v in volumes) for name in names}
              for mode in ('baseline', 'partial')}
    for mode in totals:
        totals[mode].update({name: sum(v[mode]['pipeline'][name] for v in volumes)
                            for name in ('packet_tstates', 'synchronous_waits', 'wait_tstates')})
        totals[mode]['cpu_tstates'] = cpu['totals'][mode]
    return dict(complete=True, release=False, source_streams_unchanged=True,
        full_packet_bytes_checked_in_cpu=True, reads_of_unproduced_bytes_forbidden=True,
        full_pixel_cpu_comparison=False, fuse_samples_per_frame=80, full_fuse_pixel_comparison=False,
        physical_drive_verified=False, new_bootstrap_capacity_verified=False,
        initial_irq_and_disk_phases_not_matched=True,
        nominal_schedule_met=all(v['partial']['metrics']['nominal_late_frames'] == 0 and
            v['partial']['metrics']['max_actual_deviation_tstates'] <= 64 for v in volumes),
        fallback_met=all(v['partial']['metrics']['actual_out_over_one_field'] == 0 and
            v['partial']['metrics']['bad_actual_intervals'] == 0 for v in volumes),
        volumes=volumes, totals=totals)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--partial', type=Path)
    parser.add_argument('--pilot', type=Path)
    parser.add_argument('--cpu', type=Path, default=Path('toolkit/partial_slots_cpu.json'))
    parser.add_argument('--evidence', type=Path, default=Path('toolkit/partial_slots_evidence'))
    parser.add_argument('--output', type=Path, default=Path('toolkit/partial_slots_summary.json'))
    args = parser.parse_args()
    cpu = json.loads(args.cpu.read_bytes())
    reports, files = {}, []
    if bool(args.baseline) != bool(args.partial):
        raise ValueError('both fresh directories or neither')
    if args.baseline:
        args.evidence.mkdir(parents=True, exist_ok=True)
        for mode, directory, parts in (('baseline', args.baseline, (1, 2, 3)),
                                       ('partial', args.partial, (1, 2, 3)),
                                       ('pilot', args.pilot, (3,))):
            if directory is None:
                continue
            for part in parts:
                path = directory/f'part{part:02}.json'
                row = json.loads(path.read_bytes())
                reports[mode, part] = row
                stem = f'{mode}-part{part:02}'
                dest = args.evidence/(stem+'.json')
                dest.write_text(json.dumps(row, indent=2)+'\n', encoding='utf-8', newline='\n')
                files.append(dict(file=dest.name, sha256=sha(dest.read_bytes())))
                for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
                    blob = path.with_suffix(suffix).read_bytes()
                    if sha(blob) != row[key]:
                        raise ValueError('fresh evidence hash mismatch')
                    dest = args.evidence/(stem+suffix+'.gz')
                    dest.write_bytes(gzip.compress(blob, mtime=0))
                    files.append(dict(file=dest.name, sha256=sha(dest.read_bytes()), uncompressed_sha256=sha(blob)))
        result = summarize(cpu, reports)
        result.update(cpu_report_sha256=sha(args.cpu.read_bytes()), evidence=files)
        args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    else:
        result = json.loads(args.output.read_bytes())
        if result['cpu_report_sha256'] != sha(args.cpu.read_bytes()):
            raise ValueError('CPU report changed')
        for item in result['evidence']:
            path = args.evidence/item['file']
            blob = path.read_bytes()
            if sha(blob) != item['sha256']:
                raise ValueError(f'evidence hash changed: {path}')
            if path.suffix == '.gz' and sha(gzip.decompress(blob)) != item['uncompressed_sha256']:
                raise ValueError('uncompressed hash mismatch')
        for mode in ('baseline', 'partial'):
            for part in (1, 2, 3):
                reports[mode, part] = json.loads((args.evidence/f'{mode}-part{part:02}.json').read_bytes())
        repeated = summarize(cpu, reports)
        if any(result[key] != value for key, value in repeated.items()):
            # JSON makes histogram keys strings; normalize only that representation.
            repeated = json.loads(json.dumps(repeated))
            if any(result[key] != value for key, value in repeated.items()):
                raise ValueError('derived summary changed')
    print(json.dumps(result['totals'], indent=2))


if __name__ == '__main__':
    main()
