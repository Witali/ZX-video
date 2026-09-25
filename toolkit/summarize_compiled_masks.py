"""Archive full compiled-mask measurements against the four-slot baseline."""
import argparse
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha
from summarize_uncontended_frame import metrics


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('fuse','cpu','evidence','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--baseline',type=Path,default=Path('toolkit/slot_queue_evidence'))
    args=p.parse_args();cpu=json.loads(args.cpu.read_bytes())
    if not cpu['complete'] or cpu['checked_frames']!=4221:raise ValueError('incomplete CPU verification')
    args.evidence.mkdir(parents=True,exist_ok=True);files=[];volumes=[]
    for part in (1,2,3):
        path=args.fuse/f'part{part:02}.json';new=json.loads(path.read_bytes())
        old_path=args.baseline/path.name;old=json.loads(old_path.read_bytes())
        c=cpu['volumes'][part-1]
        for r in (old,new):
            if not r['complete'] or not r['trace_nonce_exact'] or r['errors'] or not r['ay_records_exact']:
                raise ValueError('incomplete Fuse result')
        if (old['trd_sha256']!=new['trd_sha256'] or new['frames']!=c['checked_frames']
                or new['runtime_sectors_checked']!=old['runtime_sectors_checked']
                or not new.get('compiled_masks') or new.get('uncontended_frame')):
            raise ValueError('different source or variant')
        dest=args.evidence/path.name;dest.write_text(json.dumps(new,indent=2)+'\n',encoding='utf-8',newline='\n')
        files.append(dict(file=dest.name,sha256=sha(dest.read_bytes())))
        for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
            blob=path.with_suffix(suffix).read_bytes()
            if sha(blob)!=new[key]:raise ValueError('trace hash differs')
            dest=args.evidence/(path.stem+suffix+'.gz');dest.write_bytes(gzip.compress(blob,mtime=0))
            files.append(dict(file=dest.name,sha256=sha(dest.read_bytes()),uncompressed_sha256=sha(blob)))
        volumes.append(dict(part=part,trd_sha256=new['trd_sha256'],baseline_report_sha256=sha(old_path.read_bytes()),
            baseline=metrics(old),compiled=metrics(new),
            metadata_cpu={k:c[k] for k in ('baseline_tstates','compiled_tstates','delta_tstates','initialize_tstates')}))
    totals={name:{key:sum(v[name][key] for v in volumes) for key in
        ('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','read_service_tstates',
         'seek_service_tstates','publication_span_tstates')} for name in ('baseline','compiled')}
    totals['metadata_cpu']={key:cpu[key] for key in ('baseline_tstates','compiled_tstates','delta_tstates')}
    nominal=all(v['compiled']['nominal_late_frames']==0 and v['compiled']['max_actual_deviation_tstates']<=64 for v in volumes)
    fallback=all(v['compiled']['actual_out_over_one_field']==0 and v['compiled']['bad_actual_intervals']==0 for v in volumes)
    result=dict(complete=True,release=False,scope=__doc__,baseline_commit='30de92c',
        cpu_report_sha256=sha(args.cpu.read_bytes()),source_streams_unchanged=True,
        all_frame_metadata_compared_in_cpu=True,full_compact_and_native_cpu_comparison=False,
        fuse_samples_per_frame=80,full_fuse_pixel_comparison=False,physical_drive_verified=False,
        new_bootstrap_capacity_verified=False,nominal_schedule_met=nominal,fallback_met=fallback,
        initial_disk_and_irq_phases_not_matched=True,
        timing_note='End-to-end outcome includes changed initial phases and disk rotations; it is not an isolated CPU saving.',
        volumes=volumes,totals=totals,evidence=files)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(totals),flush=True)


if __name__=='__main__':main()
