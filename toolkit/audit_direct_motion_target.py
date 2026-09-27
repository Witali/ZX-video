"""Audit saved full-frame CPU evidence; this does not establish disk timing."""
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit():
    paths = {name:ROOT/name for name in
             ('direct_motion_target_cpu.json','cached_huffman_lookahead_cpu.json','frame_hotspot_profile.json')}
    result, baseline, profile = [json.loads(p.read_bytes()) for p in paths.values()]
    if (not result['complete'] or result['checked_frames'] != 4221
            or not result['full_compact_and_both_native_exact'] or result.get('failure')
            or result['release'] or result['new_trds_built'] or result['actual_playback_measured']):
        raise ValueError('incomplete or overstated CPU evidence')
    if (result['reference_sha256'] != sha(paths['cached_huffman_lookahead_cpu.json'].read_bytes())
            or result['states_sha256'] != baseline['states_sha256']
            or result['states_sha256'] != profile['states_sha256']
            or result['compressed_movie_stream_delta_bytes'] != 0):
        raise ValueError('reference or scope differs')
    for name, expected in (result['source_sha256'] | result['baseline_sources']).items():
        if sha((ROOT/name).read_bytes()) != expected: raise ValueError(('source differs',name))
    volumes = []
    keys = ('baseline_tstates','tstates','delta_tstates','nonzero_motion_entries')
    for new, old, prof in zip(result['volumes'], baseline['volumes'], profile['volumes'], strict=True):
        if any(new[key] != old[key] or old[key] != prof[key] for key in ('part','start','end','raw_sha256')):
            raise ValueError('volume identities differ')
        if len(new['frames']) != new['end']-new['start'] or new['checked_frames'] != len(new['frames']):
            raise ValueError('frame coverage differs')
        change = new['implementation']
        if (change['baseline_setup_tstates'] != 16+11+4+10+4
                or change['setup_tstates'] != 4+16+4
                or change['code_growth_bytes'] != 3 or change['end']-change['old_end'] != 3
                or change['target']-change['baseline_target'] != 3
                or change['labels']['lookahead_refresh']-change['end'] != 5
                or sha(bytes.fromhex(change['code_hex'])) != change['code_sha256']):
            raise ValueError('setup timing or placement differs')
        if new['inline_code_bytes'] != old['inline_code_bytes']:
            raise ValueError('inline code size changed')
        # The earlier executed motion histogram predates only changes that
        # leave all motion entry frequencies intact. PUSH HL marks each
        # original nonzero setup and independently confirms the new count.
        previous_entries = sum(row['count'] for row in prof['instruction_histogram']
                               if row['stage'] == 'reconstruct/motion' and row['instruction'] == 'PUSH HL')
        if new['nonzero_motion_entries'] != previous_entries:
            raise ValueError('old motion histogram disagrees')
        for index, (after, before) in enumerate(zip(new['frames'], old['frames'], strict=True), new['start']):
            count = sum(after['phase_entries'].get(str(phase),0) for phase in (2,4,6))
            if (after['frame'] != index or before['frame'] != index
                    or after['baseline_tstates'] != before['tstates']
                    or after['nonzero_motion_entries'] != count
                    or after['tstates']-before['tstates'] != -21*count
                    or after['delta_tstates'] != -21*count):
                raise ValueError(('frame delta differs',index))
        for key in keys:
            if new[key] != sum(f[key] for f in new['frames']): raise ValueError(('volume sum',key))
        volumes.append({key:new[key] for key in ('part','checked_frames',*keys)})
    for key in keys:
        if result[key] != sum(v[key] for v in volumes): raise ValueError(('total sum',key))
    if result['slower_frames'] != 0: raise ValueError('unexpected slower frame')
    return dict(complete_saved_evidence_audit=True, release=False,
        source_sha256=sha(Path(__file__).read_bytes()),
        report_sha256={name:sha(path.read_bytes()) for name,path in paths.items()},
        checked_frames=4221, **{key:result[key] for key in keys}, volumes=volumes,
        reduction_percent=-100*result['delta_tstates']/result['baseline_tstates'],
        changed_frames=sum(f['nonzero_motion_entries']>0 for v in result['volumes'] for f in v['frames']),
        maximum_frame_saving_tstates=max(-f['delta_tstates'] for v in result['volumes'] for f in v['frames']),
        slower_frames=0, setup_before_tstates=45*result['nonzero_motion_entries'],
        setup_tstates=24*result['nonzero_motion_entries'],
        full_compact_and_both_native_exact=True, compressed_movie_stream_delta_bytes=0,
        code_growth_bytes=3, bootstrap_compressed_delta_bytes=None,
        new_trds_built=False, actual_playback_measured=False,
        decision='CPU hypothesis verified. Keep as an optional prototype pending bank-2 ZX0/ABI placement, bootstrap size and full disk-delivery verification.')


if __name__ == '__main__':
    value = audit()
    (ROOT/'direct_motion_target_summary.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(value,indent=2))
