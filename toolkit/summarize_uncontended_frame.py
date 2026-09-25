"""Archive complete relocated-player measurements against the four-slot baseline."""
import argparse
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha


def metrics(x):
    pubs=x['publications'];first,last=pubs[0]['tstate'],pubs[-1]['tstate']
    return dict(frames=x['frames'],nominal_late_frames=x['nominal_late_frames'],
        missed_nominal_frame_indices=[i for i,p in enumerate(pubs) if p['late_fields']],
        max_late_fields=x['max_late_fields'],max_actual_deviation_tstates=x['max_actual_deviation_tstates'],
        actual_out_over_one_field=x['actual_out_over_one_field'],bad_actual_intervals=x['bad_actual_intervals'],
        ay_ticks=x['ay_ticks'],audio_underruns=x['audio_underruns'],runtime_sectors=x['runtime_sectors_checked'],
        fps=(len(pubs)-1)*50*70908/(last-first),publication_span_tstates=last-first,
        late_runs=x['late_runs'],recovered_late_runs=sum(r['recovered_at'] is not None for r in x['late_runs']),
        read_service_tstates=sum(r['tstates'] for r in x['reads']),
        seek_service_tstates=sum(r['tstates'] for r in x['seek_calls']))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('fuse','cpu','machine','evidence','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--baseline',type=Path,default=Path('toolkit/slot_queue_evidence'))
    args=p.parse_args();cpu=json.loads(args.cpu.read_bytes());machine=json.loads(args.machine.read_bytes())
    if not cpu['complete'] or cpu['checked_frames']!=4221 or not machine['complete']:raise ValueError('incomplete verification')
    args.evidence.mkdir(parents=True,exist_ok=True);files=[];volumes=[]
    for part in (1,2,3):
        path=args.fuse/f'part{part:02}.json';new=json.loads(path.read_bytes())
        old_path=args.baseline/path.name;old=json.loads(old_path.read_bytes())
        for r in (old,new):
            if not r['complete'] or not r['trace_nonce_exact'] or r['errors'] or not r['ay_records_exact']:
                raise ValueError('incomplete Fuse result')
        if old['trd_sha256']!=new['trd_sha256'] or new['frames']!=cpu['volumes'][part-1]['checked_frames']:
            raise ValueError('different source')
        if not new.get('uncontended_frame'):raise ValueError('not a relocated run')
        dest=args.evidence/path.name;dest.write_text(json.dumps(new,indent=2)+'\n',encoding='utf-8',newline='\n')
        files.append(dict(file=dest.name,sha256=sha(dest.read_bytes())))
        for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
            blob=path.with_suffix(suffix).read_bytes()
            if sha(blob)!=new[key]:raise ValueError('trace hash differs')
            dest=args.evidence/(path.stem+suffix+'.gz');dest.write_bytes(gzip.compress(blob,mtime=0))
            files.append(dict(file=dest.name,sha256=sha(dest.read_bytes()),uncompressed_sha256=sha(blob)))
        volumes.append(dict(part=part,trd_sha256=new['trd_sha256'],baseline_report_sha256=sha(old_path.read_bytes()),
            baseline=metrics(old),relocated=metrics(new),cpu_tstates=cpu['volumes'][part-1]['tstates'],
            cpu_delta_tstates=cpu['volumes'][part-1]['delta_tstates']))
    totals={name:{key:sum(v[name][key] for v in volumes) for key in
        ('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','read_service_tstates',
         'seek_service_tstates','publication_span_tstates')} for name in ('baseline','relocated')}
    totals['cpu']=dict(tstates=sum(v['cpu_tstates'] for v in volumes),delta_tstates=0)
    result=dict(complete=True,release=False,scope=__doc__,baseline_commit='30de92c',
        cpu_report_sha256=sha(args.cpu.read_bytes()),machine_report_sha256=sha(args.machine.read_bytes()),
        source_streams_unchanged=True,full_compact_and_native_cpu_comparison=True,
        fuse_samples_per_frame=80,full_fuse_pixel_comparison=False,physical_drive_verified=False,
        new_bootstrap_capacity_verified=False,nominal_schedule_met=False,fallback_met=False,
        initial_disk_and_irq_phases_not_matched=True,
        timing_note='End-to-end outcome includes changed initial phases and disk rotations; it is not an isolated ULA saving.',
        volumes=volumes,totals=totals,evidence=files)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(totals),flush=True)


if __name__=='__main__':main()
