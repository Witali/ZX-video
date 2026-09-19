"""Instruction-table projection and independently measured no-op CPU/IRQ evidence."""
import argparse
import json
from pathlib import Path

from causal_tile_z80 import noop_run_delta_tstates
from frame_output_pipeline import frames, Harness
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('cells', 'baseline', 'clock', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--cpu', type=Path)
    args = p.parse_args()
    old = json.loads(args.baseline.read_text(encoding='utf-8'))
    clock = json.loads(args.clock.read_text(encoding='utf-8'))
    data = args.cells.read_bytes(); tables, mapping, packets = frames(data)
    if not old['complete'] or len(packets) != len(old['frames']):
        raise ValueError('full matching baseline required')
    deltas = [noop_run_delta_tstates(g[3],g[4]) for g,_ in packets]
    projected = [r['tstates']-4481+d for r,d in zip(old['frames'],deltas)]
    for row in clock['frames']:
        i = row['index']
        if row['stages']['reconstruct'] != old['frames'][i]['stages']['reconstruct']+deltas[i]:
            raise AssertionError('clock reconstruction timing differs')
    sizes = []
    for enabled in (False, True):
        h = Harness(tables,mapping,raw_attributes=True,decode_metadata=True,
            fast_mask_dispatch=True,selective_cache=True,skip_noop_runs=enabled)
        sizes.append(dict(noop_runs=enabled,main_bytes=len(h.recon_code),
            helper_bytes=h.recon['noop_scanner_end']-0x7a00 if enabled else 0))
    late = [(i,r['late_fields']) for i,r in enumerate(clock['publications']) if r['late_fields']]
    report = dict(scope=__doc__,complete=True,release=False,player_changed=True,
        cells_sha256=sha(data),states_sha256=old['states_sha256'],frames=len(packets),code_sizes=sizes,
        compression_change_bytes=0,raw_change_bytes=0,
        run_tstates=dict(before='260*k',after_stripe_end='92*k+200',
            after_nonzero_vector='92*k+236',after_zero_vector_patch='92*k+282',
            delta_nonzero_temporal=10,delta_intra_fragment=14,delta_zero_vector_patch=7),
        instruction_table_projection=dict(full_execution_measured=False,
            reconstruction_before=old['summary']['stages']['reconstruct'],
            reconstruction_after=old['summary']['stages']['reconstruct']+sum(deltas),
            reconstruction_delta=sum(deltas),zero_copy_delta=-4481*len(deltas),
            total_tstates=sum(projected),mean_tstates=sum(projected)/len(projected),
            max_tstates=max(projected),worst_frame=projected.index(max(projected)),
            frames_above_425448=sum(t>425448 for t in projected)),
        clock=dict(complete=clock['complete'],verified_frames=len(clock['frames']),
            failure=clock.get('failure'),late_frames=len(late),first_late=late[0] if late else None,
            max_late_fields=max((n for _,n in late),default=0),ideal_producer=True,ula_included=False),
        frame_deltas=[dict(index=i,reconstruction_delta=d,projected_total=projected[i]) for i,d in enumerate(deltas)])
    if args.cpu:
        cpu = json.loads(args.cpu.read_text(encoding='utf-8'))
        if (not cpu['complete'] or not cpu['skip_noop_runs'] or not cpu['zero_copy']
                or cpu['states_sha256'] != old['states_sha256'] or cpu['raw_sha256'] != old['raw_sha256']
                or len(cpu['frames']) != len(projected)):
            raise ValueError('full matching no-op run required')
        for row, expected in zip(cpu['frames'],projected):
            if row['tstates'] != expected: raise AssertionError('whole-frame formula differs')
        report['measured_cpu'] = dict(report=args.cpu.name,summary=cpu['summary'],
            total_delta=cpu['summary']['total_tstates']-old['summary']['total_tstates'])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'frame_deltas'},indent=2))


if __name__ == '__main__': main()
