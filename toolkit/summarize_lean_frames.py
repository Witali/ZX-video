"""Compare fully executed FAP3 with guarded FAP2, keeping cadence separate."""
import argparse
import json
from pathlib import Path

from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('old-stream','stream','old-storage','storage','old-cpu','cpu','clock','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args()
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    os,ns,oz,nz,oc,nc,clock = [read(path) for path in
        (args.old_stream,args.stream,args.old_storage,args.storage,args.old_cpu,args.cpu,args.clock)]
    if not all(r['complete'] for r in (os,ns,oz,nz,oc,nc)):
        raise ValueError('complete storage and deterministic CPU runs required')
    if (nc['format'] != 'FAP3' or nc['stored_guards'] or nc['states_sha256'] != oc['states_sha256']
            or any(cpu['raw_sha256'] != stream['output_sha256']
                or storage['input_sha256'] != stream['output_sha256']
                for cpu,storage,stream in ((oc,oz,os),(nc,nz,ns)))
            or len(oc['frames']) != len(nc['frames']) or len(nc['frames']) != ns['frames']
            or clock['raw_sha256'] != nc['raw_sha256']
            or clock['states_sha256'] != nc['states_sha256']):
        raise ValueError('mismatched FAP2/FAP3 evidence')
    for old,new in zip(oc['frames'],nc['frames']):
        if new['stages']['packet']-old['stages']['packet'] != -40:
            raise AssertionError('packet instruction-table delta differs')
        for phase in ('audio','handoff','metadata','reconstruct','output'):
            if new['stages'][phase] != old['stages'][phase]:
                raise AssertionError(('unchanged phase differs',new['index'],phase))
        if new['irq_tstates'] != old['irq_tstates']: raise AssertionError('manual AY ISR differs')
    stage_rows = {name:dict(before=value,after=nc['summary']['stages'][name],
        delta=nc['summary']['stages'][name]-value) for name,value in oc['summary']['stages'].items()}
    old_total,new_total = (r['summary']['total_tstates'] for r in (oc,nc))
    old_bytes,new_bytes = (r['zx0_with_headers_bytes'] for r in (oz,nz))
    publications = clock.get('publications',[])
    late = [dict(index=i,fields=row['late_fields']) for i,row in enumerate(publications) if row['late_fields']]
    # Use the common policy audit for actual T-state phase errors/recovery,
    # rather than interpreting a field counter as an exact publication time.
    from assess_frame_jitter import assess
    timing = assess(publications)
    report = dict(scope=__doc__,complete=True,baseline_commit='17f079c',release=False,
        states_sha256=nc['states_sha256'],frames=len(nc['frames']),
        raw_bytes=dict(before=os['raw_bytes'],after=ns['raw_bytes'],delta=ns['raw_bytes']-os['raw_bytes']),
        zx0_bytes_with_headers=dict(before=old_bytes,after=new_bytes,delta=new_bytes-old_bytes),
        sectors=dict(before=(old_bytes+255)//256,after=(new_bytes+255)//256,
            delta=(new_bytes+255)//256-(old_bytes+255)//256),
        preliminary_three_trd_data_allowance=1937664,
        preliminary_data_margin_bytes=1937664-new_bytes,
        actual_disk_delivery_verified=False,ula_included=False,
        packet_guard_path_tstates=dict(before=54,after=14,delta=-40),
        foreground_tstates=dict(before=old_total,after=new_total,delta=new_total-old_total,
            reduction_percent=100*(old_total-new_total)/old_total),
        stages=stage_rows,summary=nc['summary'],
        instruction_table='https://www.zilog.com/docs/z80/um0080.pdf',
        exact_framewise_packet_delta=True,unchanged_video_and_audio_phases=True,
        exact_pixels_and_ay=nc['summary']['exact_pixels_and_ay'],
        generated_guard_bytes_per_packet=1,
        empty_value_streams=dict(coded=sum(r['coded_bytes']==0 for r in ns['packets']),
            literals=sum(r['literal_bytes']==0 for r in ns['packets'])),
        cadence=dict(complete=clock['complete'],verified_frames=len(clock['frames']),
            failure=clock.get('failure'),late_frames=len(late),first_late=late[0] if late else None,
            audit=timing),
        sources={name:dict(path=getattr(args,name).name,sha256=sha(getattr(args,name).read_bytes()))
            for name in ('old_stream','stream','old_storage','storage','old_cpu','cpu','clock')})
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
