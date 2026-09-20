"""Re-evaluate the ZX0-only reservoir using subsequent measured stage deltas.

This is an optimistic scheduling model, not an integrated Z80 player.
ZX0 work is uniform per consumed byte, freely preemptible, with ideal input.
Transport, new scheduling/paging, ULA and physical disk are excluded.
The source frame data, existing AY work and six-field deadlines stay fixed.
"""
import argparse
import hashlib
import json
from pathlib import Path

from probe_decoded_queue_schedule import simulate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports',type=Path,default=Path(__file__).parent)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    names=dict(cpu='token_boundary_fast_cpu.json',reservoir='predecode_reservoir.json',
        cache='cache_columns_cpu.json',groups='attribute_groups_cpu.json',
        attrs='attribute_masks_cpu.json',gray='gray_cells_cpu.json')
    data={k:json.loads((args.reports/name).read_text(encoding='utf-8')) for k,name in names.items()}
    if not all(r['complete'] for r in data.values()): raise ValueError('incomplete source report')
    for key in ('raw_sha256','states_sha256'):
        if len({r[key] for r in data.values()})!=1: raise ValueError('different inputs')
    old=data['cpu']; source=data['reservoir']; rows=source['frames_detail']; count=len(rows)
    if count!=4221 or any(len(data[k]['frames'])!=count for k in ('cpu','cache','groups','attrs','gray')):
        raise ValueError('different frame counts')
    positions=[old['frames'][0]['consumed_raw_bytes']-rows[0]['packet_bytes']]+[f['consumed_raw_bytes'] for f in old['frames']]
    zx0=[sum(h['stages'].get('banked_zx0',0) for h in old['header_results'])]+[r['zx0_tstates'] for r in rows]
    old_draw=[r['output_tstates'] for r in rows]
    old_pre=[r['foreground_after_copy_tstates']-r['zx0_tstates']-r['output_tstates'] for r in rows]
    irq=[r['irq_tstates'] for r in old['frames']]
    pre=[]; draw=[]; detail=[]
    for i,row in enumerate(rows):
        cache,group,attr,gray=(data[k]['frames'][i] for k in ('cache','groups','attrs','gray'))
        if any(r['index']!=i for r in (row,cache,group,attr,gray)): raise ValueError('frame order differs')
        cache_delta=cache['unrolled']-cache['baseline']
        prepare=group['prepare_tstates']+group['added_call_tstates']
        if gray['prepare_tstates']!=group['prepare_tstates']: raise ValueError('different group preparation')
        expected_delta=cache_delta+attr['delta']+group['delta_tstates']+gray['output_delta']
        pre.append(old_pre[i]+cache_delta+attr['delta']+prepare)
        draw.append(gray['output_tstates'])
        actual_delta=pre[-1]+draw[-1]-old_pre[i]-old_draw[i]
        if actual_delta!=expected_delta: raise ValueError(('stage replacement differs',i))
        detail.append(dict(index=i,pre_tstates=pre[-1],draw_tstates=draw[-1],stage_delta_tstates=actual_delta))
    scenarios=[]
    for slots in (1,3,4,5,7):
        prior=simulate(positions,zx0,old_pre,old_draw,irq,slots,0)
        recorded=next(r for r in source['zx0_queue_scenarios'] if r['decoded_blocks']==slots and r['extra_work_per_frame']==0)
        if prior!=recorded: raise ValueError('previous model did not reproduce')
        for extra in (0,5000,10000):
            scenarios.append(dict(previous_late_frames=prior['late_frames'],
                **simulate(positions,zx0,pre,draw,irq,slots,extra)))
    report=dict(scope=__doc__,complete=True,estimated_only=True,release=False,baseline_commit='c829610',
        raw_sha256=old['raw_sha256'],states_sha256=old['states_sha256'],frames=count,
        compressed_stream_bytes=source['compressed_stream_bytes'],compressed_stream_delta_bytes=0,
        current_stage_work_delta_tstates=sum(r['stage_delta_tstates'] for r in detail),
        old_non_zx0_foreground_tstates=sum(old_pre)+sum(old_draw),
        updated_non_zx0_foreground_tstates=sum(pre)+sum(draw),
        no_new_player_code=True,implemented_player_delta_tstates=0,
        original_ay_cost_included=True,early_ay_option_used=False,density_16_used=False,
        new_ring_transport_tstates_measured=False,physical_disk_verified=False,ula_verified=False,
        fit_of_all_slot_counts_in_128k_verified=False,
        scenarios=scenarios,frames_detail=detail,
        inputs={k:dict(file=name,sha256=hashlib.sha256((args.reports/name).read_bytes()).hexdigest()) for k,name in names.items()})
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('scenarios','frames_detail','inputs')},indent=2))
    for row in scenarios:
        if not row['extra_work_per_frame']: print(json.dumps(row))


if __name__=='__main__': main()
