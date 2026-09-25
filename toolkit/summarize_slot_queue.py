"""Archive full integrated queue runs and compare against the last player."""
import argparse
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha

FIELD=70908


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('fuse','cpu','evidence','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--baseline',type=Path,default=Path('toolkit/register_fragments_evidence'))
    p.add_argument('--attempts',type=Path)
    args=p.parse_args();cpu=json.loads(args.cpu.read_bytes())
    if not cpu['complete']:raise ValueError('partial CPU measurement')
    args.evidence.mkdir(parents=True,exist_ok=True);volumes=[];files=[]
    for part in (1,2,3):
        src=args.fuse/f'part{part:02}.json';r=json.loads(src.read_bytes())
        base=args.baseline/f'fuse_part{part:02}.json';b=json.loads(base.read_bytes())
        c=cpu['volumes'][part-1]
        if (not r['complete'] or not b['complete'] or not r['trace_nonce_exact'] or r['errors']
                or r['trd_sha256']!=b['trd_sha256'] or r['trd_sha256']!=c['trd_sha256']):
            raise ValueError('partial or inconsistent measurement')
        dest=args.evidence/src.name
        dest.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
        files.append(dict(file=dest.name,sha256=sha(dest.read_bytes())))
        for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
            blob=src.with_suffix(suffix).read_bytes()
            if sha(blob)!=r[key]:raise ValueError('trace or debugger hash differs')
            dest=args.evidence/(src.stem+suffix+'.gz');dest.write_bytes(gzip.compress(blob,mtime=0))
            files.append(dict(file=dest.name,sha256=sha(dest.read_bytes()),uncompressed_sha256=sha(blob)))
        def metrics(x):
            pubs=x['publications'];runs=x['late_runs'];first=pubs[0]['tstate']
            return dict(frames=x['frames'],nominal_late_frames=x['nominal_late_frames'],
                missed_nominal_frame_indices=[i for i,pub in enumerate(pubs) if pub['late_fields']],
                max_late_fields=x['max_late_fields'],max_actual_deviation_tstates=x['max_actual_deviation_tstates'],
                actual_out_over_one_field=x['actual_out_over_one_field'],bad_actual_intervals=x['bad_actual_intervals'],
                ay_ticks=x['ay_ticks'],ay_records_exact=x['ay_records_exact'],audio_underruns=x['audio_underruns'],
                runtime_sectors=x['runtime_sectors_checked'],retries=x['fast_read_retries'],
                fps=(len(pubs)-1)*50*FIELD/(pubs[-1]['tstate']-first),
                nominal_schedule_met=x['nominal_late_frames']==0,
                fallback_met=x['actual_out_over_one_field']==0 and x['bad_actual_intervals']==0,
                late_runs=runs,recovered_late_runs=sum(q['recovered_at'] is not None for q in runs),
                read_service_tstates=sum(q['tstates'] for q in x['reads']),
                post_first_publication_read_service_tstates=sum(q['tstates'] for q in x['reads'] if q['start_tstate']>=first),
                seek_service_tstates=sum(q['tstates'] for q in x['seek_calls']))
        volumes.append(dict(part=part,trd_sha256=r['trd_sha256'],baseline_report_sha256=sha(base.read_bytes()),
            baseline=metrics(b),queue=metrics(r),cpu=c['summary']))
    attempts=[]
    if args.attempts:
        for path in sorted(args.attempts.glob('*.json')):
            blob=path.read_bytes();v=json.loads(blob)
            dest=args.evidence/('attempt-'+path.name+'.gz');dest.write_bytes(gzip.compress(blob,mtime=0))
            files.append(dict(file=dest.name,sha256=sha(dest.read_bytes()),uncompressed_sha256=sha(blob)))
            attempts.append(dict(file=dest.name,report_sha256=sha(blob),
                **{k:v[k] for k in ('part','complete','frames','failure','nominal_late_frames','audio_underruns','trace_nonce_exact')}))
    totals={name:{key:sum(v[name][key] for v in volumes) for key in
        ('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','read_service_tstates','seek_service_tstates')}
        for name in ('baseline','queue')}
    totals['cpu']={key:sum(v['cpu'][key] for v in volumes) for key in
        ('raw_bytes','packets','blocks','old_reader_tstates','queue_total_tstates')}
    totals['cpu']['delta_tstates']=totals['cpu']['queue_total_tstates']-totals['cpu']['old_reader_tstates']
    result=dict(complete=True,release=False,baseline_commit='248db65',scope=__doc__,
        cold_boot_then_debugger_installed=True,new_release_images_built=False,
        initial_bootstrap_256_sectors_excluded_from_runtime_count=True,full_movie_packets_compared_in_cpu=True,
        fuse_pixel_samples_per_frame=80,full_fuse_pixel_comparison=False,physical_drive_verified=False,
        capacity_with_new_bootstrap_measured=False,nominal_schedule_met=False,fallback_met=False,
        cpu_report_sha256=sha(args.cpu.read_bytes()),volumes=volumes,totals=totals,evidence=files,
        earlier_attempt_summaries=attempts)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(totals),flush=True)


if __name__=='__main__':main()
