"""Audit saved two-byte-cache evidence, without repeating CPU or playback runs."""
import json
from pathlib import Path

from build_fap3_trd import sha
from cached_huffman_lookahead import delta

ROOT = Path(__file__).parent


def main():
    names = ('cached_huffman_lookahead_cpu.json', 'cached_huffman_lookahead_cases.json')
    cpu, cases = [json.loads((ROOT/name).read_bytes()) for name in names]
    for report in (cpu, cases):
        if not report['complete'] or report.get('failure'):
            raise ValueError('incomplete or failed evidence')
        for name, expected in report['source_sha256'].items():
            if sha((ROOT/name).read_bytes()) != expected: raise ValueError(('changed source', name))
    for name, expected in cpu['baseline_source_sha256'].items():
        if sha((ROOT/name).read_bytes()) != expected: raise ValueError(('changed baseline source', name))
    for name, expected in cpu['reference_sha256'].items():
        if sha((ROOT/name).read_bytes()) != expected: raise ValueError(('changed reference', name))
    baseline_path = ROOT/'compact_cursor_cpu.json'
    baseline = json.loads(baseline_path.read_bytes())
    if sha(baseline_path.read_bytes()) != cases['baseline_sha256']:
        raise ValueError('case baseline differs')
    volumes = []
    for old, new, code in zip(baseline['volumes'], cpu['volumes'], cases['volumes'], strict=True):
        keys = ('part', 'start', 'end', 'raw_sha256')
        if any(tuple(v[k] for k in keys) != tuple(old[k] for k in keys) for v in (new, code)):
            raise ValueError('volume identity differs')
        if not new['checked_frames'] == len(new['frames']) == new['end']-new['start'] == code['checked_packets']:
            raise ValueError('incomplete volume')
        for before, after in zip(old['frames'], new['frames'], strict=True):
            wanted = delta(after['short_inside'], after['short_cross'], after['long'])
            if (before['frame'] != after['frame'] or before['tstates'] != after['baseline_tstates']
                    or after['tstates']-before['tstates'] != wanted or wanted != after['delta_tstates']):
                raise ValueError('per-frame baseline or cycle equation differs')
        for key in ('baseline_tstates', 'tstates', 'delta_tstates', 'short_inside', 'short_cross', 'long'):
            if new[key] != sum(f[key] for f in new['frames']): raise ValueError(('volume sum differs', key))
        if (code['paired_cases'] != sum(c['cases'] for c in code['costs'])
                or code['paired_cases'] != sum(c['code_count']*8 for c in code['contexts'])):
            raise ValueError('code/offset coverage differs')
        for row in code['costs']:
            wanted = {'inside': -11, 'cross': -7, 'long': 18}[row['kind']]
            if row['tstates']-row['baseline_tstates'] != row['delta_tstates'] or row['delta_tstates'] != wanted:
                raise ValueError('primitive cycle equation differs')
        if code['packets_exceeding_two_guard_capacity'] or code['max_payload_bytes'] > cases['proposed_packet_maximum']:
            raise ValueError('packet does not leave two readable guards')
        volumes.append(dict(part=new['part'], frames=new['checked_frames'],
            baseline_tstates=new['baseline_tstates'], tstates=new['tstates'],
            delta_tstates=new['delta_tstates'],
            slower_frames=sum(f['delta_tstates'] > 0 for f in new['frames']),
            min_frame_delta=min(f['delta_tstates'] for f in new['frames']),
            max_frame_delta=max(f['delta_tstates'] for f in new['frames']),
            paired_code_cases=code['paired_cases'], max_payload_bytes=code['max_payload_bytes']))
    for key in ('baseline_tstates', 'tstates', 'delta_tstates'):
        if cpu[key] != sum(v[key] for v in volumes): raise ValueError(('movie sum differs', key))
    if not (cpu['full_compact_and_both_native_exact'] and cpu['checked_frames'] == cases['checked_packets'] == 4221
            and cases['paired_cases'] == sum(v['paired_code_cases'] for v in volumes)):
        raise ValueError('movie/case coverage differs')
    summary = dict(scope=__doc__, complete_saved_evidence_audit=True, release=False,
        source_sha256=sha(Path(__file__).read_bytes()),
        report_sha256={name: sha((ROOT/name).read_bytes()) for name in names},
        checked_frames=cpu['checked_frames'], paired_code_cases=cases['paired_cases'],
        baseline_tstates=cpu['baseline_tstates'], tstates=cpu['tstates'],
        delta_tstates=cpu['delta_tstates'],
        reduction_percent=100*(cpu['baseline_tstates']-cpu['tstates'])/cpu['baseline_tstates'],
        slower_frames=sum(v['slower_frames'] for v in volumes),
        full_compact_and_both_native_exact=True, compressed_stream_delta_bytes=0,
        new_trds_built=False, integrated_guard_contract_verified=False,
        actual_new_playback_measured=False, physical_drive_verified=False,
        volumes=volumes,
        decision='Retain the CPU prototype for integration. Reserve two readable guard bytes and '
                 'recheck capacity, actual frame publication, AY continuity and total disk delivery '
                 'before enabling it in independently bootable TRDs.')
    (ROOT/'cached_huffman_lookahead_summary.json').write_text(
        json.dumps(summary, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
