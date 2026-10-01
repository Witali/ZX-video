"""Profile exact cell-player stage boundaries in a complete real Fuse run.

Elapsed residuals include IRQs, contention and control code. They are not
deterministic CPU times. Report the independent CPU replay separately.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json
from profile_integrated_timing import merged, overlap, stats


def analyze(r, m, cpu):
    assert r['complete'] and not r['errors'] and not r['failure']
    assert r['trace_nonce_exact'] and r['ay_records_exact']
    assert r['integrated_slot_queue'] and r['debugger_installed_bytes'] == 0
    assert r['trd_sha256'] == m['trd_sha256']
    assert cpu['complete'] and cpu['all_native_screens_exact']
    grouped = defaultdict(list)
    for event in r['pipeline_events']:
        grouped[event['kind']].append(event)
    pairs = [('packet', 'packet_start', 'packet_ready'), ('draw', 'draw_start', 'native_done')]
    assert all(len(grouped[k]) == m['frames'] for _, lo, hi in pairs for k in (lo, hi))
    starts, ends = grouped['empty_wait_start'], grouped['empty_wait_end']
    assert len(starts) == len(ends)
    waits = [(a['tstate'], b['tstate']) for a, b in zip(starts, ends)]
    assert all(b >= a for a, b in waits)
    reads = [(e['start_tstate'], e['end_tstate']) for e in r['reads']]
    seeks = [(e['start_tstate'], e['end_tstate']) for e in r['seek_calls']]
    service = merged(reads + seeks)
    assert len(grouped['decode_start']) == len(grouped['decode_end']) > 0
    decodes=[(a['tstate'], b['tstate']) for a,b in zip(grouped['decode_start'],grouped['decode_end'])]
    assert all(a<=b for a,b in decodes)
    assert not any(overlap(service,a,b) for a,b in decodes)
    stage_intervals = []
    frames = []
    for i, pub in enumerate(r['publications']):
        stages = {}
        for name, lo, hi in pairs:
            a, b = grouped[lo][i]['tstate'], grouped[hi][i]['tstate']
            assert a <= b <= pub['tstate']
            io = overlap(service, a, b)
            stages[name] = dict(start=a, end=b, elapsed=b-a, disk_service=io,
                                residual=b-a-io, empty_wait=overlap(waits, a, b))
            stage_intervals.append((a, b))
        assert stages['packet']['end'] <= stages['draw']['start']
        frames.append(dict(frame=m['frame_start']+i, late_fields=pub['late_fields'], stages=stages))
    ordered = sorted(stage_intervals)
    assert all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:]))
    begin, end = grouped['packet_start'][0]['tstate'], r['publications'][-1]['tstate']
    phases = {name: {k: stats([f['stages'][name][k] for f in frames])
                    for k in ('elapsed', 'disk_service', 'residual', 'empty_wait')} for name, _, _ in pairs}
    return dict(complete=True, release=False, scope=__doc__, frames=frames,
        frame_fields=m['frame_fields'], nominal_frame_tstates=m['frame_fields']*70908,
        nominal_late_frames=r['nominal_late_frames'], max_late_fields=r['max_late_fields'],
        stages=phases, sector_elapsed=stats([b-a for a,b in reads]),
        active_elapsed=end-begin, active_disk_service=overlap(service, begin, end),
        decode_slices=stats([b-a for a,b in decodes]), active_decode_elapsed=overlap(decodes,begin,end),
        decode_scope='Queue decoder bridge through its return: includes LZSA2, paging, IRQ and ULA; overlaps packet stages',
        disk_service_all=sum(b-a for a,b in service),
        disk_service_in_stages=sum(p['disk_service']['total'] for p in phases.values()),
        empty_wait=stats([b-a for a,b in waits]),
        queue_at_packet=dict(Counter(e['count'] for e in grouped['packet_start'])),
        deterministic_cpu=dict(scope=cpu['scope'], stages=cpu['new_instruction_stages'],
            draw=stats([f['draw']['tstates'] for f in cpu['frames']]),
            next_packet=stats([f['next_packet']['tstates'] for f in cpu['frames'] if f.get('next_packet')])),
        trd_sha256=r['trd_sha256'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','metadata','cpu','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    r,m,cpu=[json.loads(path.read_bytes()) for path in (a.trace,a.metadata,a.cpu)]
    assert sha(a.metadata.read_bytes())==r['integrated_bootstrap_metadata_sha256']
    for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
        assert sha(a.trace.with_suffix(suffix).read_bytes())==r[key]
    result=analyze(r,m,cpu)
    result['inputs']={k:dict(path=str(getattr(a,k)),sha256=sha(getattr(a,k).read_bytes())) for k in ('trace','metadata','cpu')}
    result['source_sha256_lf']=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))
    write_json(a.output,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('frames','deterministic_cpu','scope','inputs')}))


if __name__=='__main__':main()
