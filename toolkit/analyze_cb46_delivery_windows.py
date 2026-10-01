"""Attribute complete CB46 late runs to measured work and physical disk service.

Use saved Fuse events. Elapsed costs include IRQ/ULA effects; these are not
instruction counts or a prediction of a different producer schedule.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json
from profile_integrated_timing import merged, overlap, stats


def analyze(trace, metadata, lookback=20):
    assert trace['complete'] and not trace['errors'] and not trace['failure']
    assert trace['trd_sha256'] == metadata['trd_sha256']
    assert trace['trace_nonce_exact'] and trace['ay_records_exact']
    assert len(trace['publications']) == metadata['frames']
    events = defaultdict(list)
    for event in trace['pipeline_events']:
        events[event['kind']].append(event)

    def pairs(start, end):
        assert len(events[start]) == len(events[end])
        result = [(a['tstate'], b['tstate']) for a, b in zip(events[start], events[end])]
        assert all(a <= b for a, b in result)
        return result

    draw = pairs('draw_start', 'native_done')
    decode = pairs('decode_start', 'decode_end')
    waits = pairs('empty_wait_start', 'empty_wait_end')
    packet = pairs('packet_start', 'packet_ready')
    disk = merged([(r['start_tstate'], r['end_tstate'])
                   for r in trace['reads'] + trace['seek_calls']])
    pubs = trace['publications']
    assert len(draw) == len(packet) == len(pubs)
    # Disk can occur inside a draw bridge's keepalive service. Do not add
    # inclusive phase totals as if they were disjoint CPU work.
    busy = merged(draw + decode + disk + packet)
    frames = []
    for i, pub in enumerate(pubs):
        if not pub['late_fields']:
            continue
        a = pubs[i-1]['tstate'] if i else packet[i][0]
        b = pub['tstate']
        frames.append(dict(local_frame=i, global_frame=metadata['frame_start']+i,
            late_fields=pub['late_fields'], packet_elapsed=packet[i][1]-packet[i][0],
            packet_disk=overlap(disk, *packet[i]), packet_decode=overlap(decode, *packet[i]),
            packet_empty_wait=overlap(waits, *packet[i]),
            draw_elapsed=draw[i][1]-draw[i][0],
            since_previous_publication=b-a, since_previous_disk=overlap(disk, a, b),
            queue_count_at_packet=events['packet_start'][i]['count']))
    runs = []
    for run in trace['late_runs']:
        first = max(0, run['start']-lookback)
        last = run['recovered_at'] if run['recovered_at'] is not None else len(pubs)-1
        a, b = pubs[first]['tstate'], pubs[last]['tstate']
        reads = [r for r in trace['reads'] if a <= r['start_tstate'] < b]
        counts = Counter(e['count'] for e in events['packet_start'] if a <= e['tstate'] < b)
        runs.append(dict(run, window_first=first, window_last=last,
            global_start=metadata['frame_start']+run['start'], elapsed=b-a,
            nominal_elapsed=(last-first)*metadata['frame_fields']*70908,
            draw_elapsed=overlap(draw, a, b), decode_elapsed=overlap(decode, a, b),
            disk_elapsed=overlap(disk, a, b), packet_elapsed=overlap(packet, a, b),
            empty_wait_elapsed=overlap(waits, a, b), measured_work_union=overlap(busy, a, b),
            outside_measured_work=b-a-overlap(busy, a, b),
            reads=stats([r['tstates'] for r in reads]),
            queue_counts=dict(counts),
            slow_reads=[{k:r[k] for k in ('sector','tstates','start_tstate','end_tstate')}
                        for r in reads if r['tstates'] > 70908]))
    return dict(complete=True, release=False, scope=__doc__, lookback_frames=lookback,
        frames=metadata['frames'], frame_start=metadata['frame_start'],
        trd_sha256=metadata['trd_sha256'], late_frames=frames, windows=runs,
        totals=dict(draw=overlap(draw, pubs[0]['tstate'], pubs[-1]['tstate']),
            decode=overlap(decode, pubs[0]['tstate'], pubs[-1]['tstate']),
            disk=overlap(disk, pubs[0]['tstate'], pubs[-1]['tstate'])))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('metadata','trace','output'):
        p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--lookback', type=int, default=20)
    a = p.parse_args()
    assert a.lookback >= 0
    metadata, trace = [json.loads(path.read_bytes()) for path in (a.metadata,a.trace)]
    assert sha(a.metadata.read_bytes()) == trace['integrated_bootstrap_metadata_sha256']
    assert sha(a.trace.with_suffix('.trace.txt').read_bytes()) == trace['trace_sha256']
    result = analyze(trace, metadata, a.lookback)
    result['inputs'] = {key:dict(path=str(path), sha256=sha(path.read_bytes()))
                       for key,path in (('metadata',a.metadata),('trace',a.trace))}
    result['source_sha256_lf'] = sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))
    write_json(a.output, result)
    print(json.dumps(dict(frames=result['frames'], late_frames=len(result['late_frames']),
                          windows=result['windows'])))


if __name__ == '__main__':
    main()
