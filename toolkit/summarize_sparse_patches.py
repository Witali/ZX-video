"""Separate full frame-stage evidence from publication and AY clock evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from summarize_gray_cells import clock_result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('probe','cpu','before','after','storage','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reference-reports',type=Path,default=Path(__file__).parent)
    args = p.parse_args(); paths = {k:getattr(args,k) for k in ('probe','cpu','before','after','storage')}
    reports = {k:json.loads(p.read_text(encoding='utf-8')) for k,p in paths.items()}
    probe,cpu,old,new,storage = (reports[k] for k in paths)
    if not all(r['complete'] for r in (probe,cpu,storage)) or cpu['checked_frames'] != 4221:
        raise ValueError('incomplete stage report')
    for key in ('raw_sha256','states_sha256'):
        if len({r[key] for r in (cpu,old,new)}) != 1: raise ValueError('different inputs')
    if probe['raw_sha256'] != cpu['raw_sha256'] or storage['input_sha256'] != cpu['raw_sha256']:
        raise ValueError('different stream')
    if probe['implemented_delta'] != cpu['delta_tstates'] or len(probe['frames_detail']) != len(cpu['frames']):
        raise ValueError('different stage deltas')
    for a,b in zip(probe['frames_detail'],cpu['frames']):
        if a['index'] != b['index'] or a['delta_tstates'] != b['delta_tstates']: raise ValueError('per-frame delta differs')
    references = dict(original='token_boundary_fast_cpu.json', cache='cache_columns_cpu.json', attrs='attribute_masks_cpu.json')
    refs = {k:json.loads((args.reference_reports/name).read_text(encoding='utf-8')) for k,name in references.items()}
    for report in refs.values():
        if not report['complete'] or len(report['frames']) != cpu['checked_frames']:
            raise ValueError('incomplete previous CPU reference')
        for key in ('raw_sha256','states_sha256'):
            if report[key] != cpu[key]: raise ValueError('different previous CPU input')
    original_instructions = {row['address']:row for row in refs['original']['instruction_listing']}
    old_patch = sum(row['tstates']*row['count'] for row in refs['original']['instruction_histogram']
        if original_instructions.get(row['address'],{}).get('stage') == 'patch')
    if old_patch != cpu['baseline_patch_tstates']: raise ValueError('previous measured patch count differs')
    reference_reconstruction = 0
    for row in cpu['frames']:
        i = row['index']; cache = refs['cache']['frames'][i]; attrs = refs['attrs']['frames'][i]
        expected = refs['original']['frames'][i]['stages']['reconstruct']+cache['unrolled']-cache['baseline']+attrs['delta']
        if expected+row['delta_tstates'] != row['stages']['reconstruct']:
            raise ValueError(('previous measured reconstruction differs',i))
        reference_reconstruction += expected
    for key in ('frames_requested','lookahead','packet_ahead','unrolled_copy','unrolled_cache',
                'attribute_groups','attribute_flags','gray_cells','compressed_bytes','early_ay'):
        if old.get(key,False) != new.get(key,False): raise ValueError('different clock options: '+key)
    if old.get('sparse_patches') or not new['sparse_patches']: raise ValueError('wrong patch variants')
    for r in (old,new):
        if not r['complete'] and not r.get('failure'): raise ValueError('clock has no terminal result')
    size = sum(b['zx0_bytes']+4 for b in storage['blocks'])
    if size != old['compressed_bytes']: raise ValueError('different stream size')
    common = min(old['checked']['publish'],new['checked']['publish'])
    result = dict(scope=__doc__,complete=True,release=False,baseline_commit='a8f28c2',
        frames=cpu['checked_frames'],raw_sha256=cpu['raw_sha256'],states_sha256=cpu['states_sha256'],
        compressed_stream_bytes=size,compressed_stream_delta_bytes=0,stream_sector_delta=0,
        patch_stage=dict(before=cpu['baseline_patch_tstates'],after=cpu['patch_tstates'],delta=cpu['delta_tstates'],
            change_percent=cpu['patch_change_percent']),
        previous_full_cpu_reference_verified=True,
        reconstruction_stage=dict(before=reference_reconstruction,
            after=sum(row['stages']['reconstruct'] for row in cpu['frames']),
            reference_adjustments='Original measured Z80 plus measured unrolled-cache and attribute-flag deltas'),
        full_frame_stages=dict(before=cpu['baseline_total_tstates'],after=cpu['total_tstates'],
            baseline_comparison=cpu['baseline_comparison'],includes_zx0_or_ay_clock=False),
        slower_frames=cpu['slower_frames'],max_extra_frame_tstates=cpu['max_extra_frame_tstates'],
        exact_all_compact_and_native_screens=cpu['exact_all_compact_and_native_screens'],memory=cpu['memory'],
        common_publications=common,clocks=[clock_result(name,r,common) for name,r in (('before',old),('after',new))],
        full_movie_cadence_verified=False,physical_disk_verified=False,ula_verified=False,
        limitations=['Full stage baseline is derived from instruction deltas checked in paired Z80 tests.',
            'Clock foreground totals can include different amounts of future work.',
            'Compressed stream includes ZX0 block headers; three complete TRD volumes are not assembled.'],
        inputs={k:dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in paths.items()})
    result['reference_inputs'] = {k:dict(file=name,sha256=hashlib.sha256((args.reference_reports/name).read_bytes()).hexdigest())
                                  for k,name in references.items()}
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('clocks','inputs','limitations')},indent=2))


if __name__ == '__main__': main()
