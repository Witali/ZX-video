"""Verify complete paired TRDs, real ROM IRQ invariants and exact CPU replay."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from audit_irq_fields import audit
from benchmark_fap3_disk import run
from build_fap3_trd import sha
from profile_integrated_timing import analyze,stats
from summarize_transfer_prefetch import audio_analysis,first_late_window
from summarize_uncontended_frame import metrics

ROOT=Path(__file__).parent


def rom_invariants(r,fixed):
    direct=[v for v in r['rom_return_states'] if v['kind']=='direct']
    restore=[v for v in r['rom_return_states'] if v['kind']=='restore']
    reads=[v for v in r['reads'] if v['kind']=='direct503']
    full=[v for v in r['reads'] if v['kind']=='trdos']
    if len(direct)!=len(reads):raise ValueError('missing direct ROM observations')
    if any((v['im'],v['i'],v['vector'])!=(2,0xbe,0xbd80) or
           (v['hl']-v['rom_destination'])&65535!=256 for v in direct):raise ValueError('direct ROM invariant failed')
    if len(restore)!=(len(full) if fixed else len(r['reads'])):raise ValueError('unexpected IRQ restorations')
    return dict(direct_returns=len(direct),direct_im2_i_be_fast_vector_exact=True,
        direct_iff1_histogram=dict(Counter(v['iff1'] for v in direct)),
        restore_visits=len(restore),full_dispatch_reads=len(full),
        full_return_states=[v for v in restore if (v['im'],v['i'],v['vector'])!=(2,0xbe,0xbd80)],
        successful_restore_cpu_saved_tstates=58*len(direct) if fixed else 0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('baseline','fixed','baseline-directory','directory','baseline-cpu','fixed-cpu'):
        p.add_argument('--'+key,type=Path)
    a=p.parse_args();evidence=ROOT/'fast_return_irq_evidence';output=ROOT/'fast_return_irq_summary.json'
    if a.fixed:
        if any(v is None for v in vars(a).values()):raise ValueError('all fresh paths required')
        evidence.mkdir(exist_ok=True);files=[]
        for name,folder,images,cpu in (('baseline',a.baseline,a.baseline_directory,a.baseline_cpu),
                                       ('fixed',a.fixed,a.directory,a.fixed_cpu)):
            blobs={name+'_cpu.json':cpu.read_bytes()}
            for part in (1,2,3):
                stem=f'part{part:02}'
                for suffix in ('.json','.debugger.txt','.trace.txt'):
                    blobs[name+'_'+stem+suffix]=(folder/(stem+suffix)).read_bytes()
                blobs[name+'_'+stem+'.metadata.json']=(images/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()
            for dest,blob in blobs.items():
                packed=gzip.compress(blob,mtime=0);dest+='.gz';(evidence/dest).write_bytes(packed)
                files.append(dict(file=dest,sha256=sha(packed),uncompressed_sha256=sha(blob)))
    else:
        previous=json.loads(output.read_bytes());files=previous['evidence']
        for name,digest in previous['source_sha256'].items():
            if sha((ROOT/name).read_bytes())!=digest:raise ValueError(('analysis/model source changed',name))
    for f in files:
        b=(evidence/f['file']).read_bytes()
        if sha(b)!=f['sha256'] or sha(gzip.decompress(b))!=f['uncompressed_sha256']:raise ValueError('archive changed')
    def blob(name):return gzip.decompress((evidence/name).read_bytes())
    def load(name):return json.loads(blob(name))
    build=json.loads((ROOT/'fast_return_irq_build.json').read_bytes())
    if not build['complete']:raise ValueError('incomplete build')
    for path,digest in build['source_sha256'].items():
        if sha((ROOT/path).read_bytes())!=digest:raise ValueError(('builder source changed',path))
    cpus={name:load(name+'_cpu.json.gz') for name in ('baseline','fixed')}
    for c in cpus.values():
        if not c['complete'] or c['frames']!=4221 or c['source_sha256']!=sha((ROOT/'replay_queue_calls.py').read_bytes()):
            raise ValueError('incomplete CPU or different model')
    frame_cpu=json.loads((ROOT/'inline_huffman_patches_cpu.json').read_bytes())
    volumes=[]
    for part in (1,2,3):
        row=dict(part=part,used_sectors=build['volumes'][part-1]['used_sectors'])
        for variant in ('baseline','fixed'):
            stem=f'{variant}_part{part:02}'
            raw=blob(stem+'.json.gz');r=json.loads(raw)
            meta=blob(stem+'.metadata.json.gz');m=json.loads(meta);c=cpus[variant]['volumes'][part-1]
            if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact'] or
                not r['ay_records_exact'] or not r['progress_100_percent'] or r['debugger_installed_bytes'] or
                r['fast_read_retries'] or r['frames']!=m['frames'] or r['ay_ticks']!=6*m['frames'] or
                r['runtime_sectors_checked']!=m['video_sectors'] or r['trd_sha256']!=m['trd_sha256'] or
                r['trd_sha256']!=c['trd_sha256'] or sha(meta)!=r['integrated_bootstrap_metadata_sha256'] or
                sha(raw)!=c['trace_report_sha256']):raise ValueError('incomplete/different evidence')
            for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                if sha(blob(stem+suffix+'.gz'))!=r[key]:raise ValueError('trace mismatch')
            script=blob(stem+'.debugger.txt.gz').decode()
            if any(s.startswith('se ') and s[3:].split(' ',1)[0].isdigit() for s in script.splitlines()):raise ValueError('RAM writes')
            if len(r['queue_call_events'])!=2*len(c['calls']):raise ValueError('CPU call count mismatch')
            for call,before,after in zip(c['calls'],r['queue_call_events'][::2],r['queue_call_events'][1::2]):
                if call['start']!=before['tstate'] or call['end']!=after['tstate'] or sum(call['cpu_stages'].values())!=call['cpu_tstates']:
                    raise ValueError('CPU call mismatch')
            irq=audit(r,m);irq.pop('actual_phase_tstates')
            profile=analyze(r,m,frame_cpu['volumes'][part-1])
            worst=sorted(profile.pop('frames'),key=lambda v:v['work_elapsed'],reverse=True)[:12]
            row[variant]=dict(metrics(r),irq=irq,rom=rom_invariants(r,variant=='fixed'),
                ay_record_field_gaps=r['ay_record_field_gaps'],ay_record_field_duplicates=r['ay_record_field_duplicates'],
                read_service=stats([v['tstates'] for v in r['reads']]),
                seek_service=stats([v['tstates'] for v in r['seek_calls']]),
                actual_late_indices=[i for i,t in enumerate(r['actual_phase_tstates']) if t>64],
                trd_sha256=m['trd_sha256'],stream_sha256=c['stream_sha256'],
                first_actual_late_window=first_late_window(r,actual=True),
                audio_wait=audio_analysis(r,c),queue_cpu_stages=c['cpu_stages'],
                queue_calls=len(c['calls']),delivery_profile=profile,worst_work_frames=worst)
            if variant=='fixed' and m['trd_sha256']!=build['volumes'][part-1]['trd_sha256']:raise ValueError('wrong build')
        if row['baseline']['stream_sha256']!=row['fixed']['stream_sha256']:raise ValueError('stream changed')
        volumes.append(row)
    timing={}
    options=dict(fast_disk=True,cached_seek=True,interleaved=True,irq_safe_paging=True,poison_irq=True)
    for name,case in (('same_track',{}),('cold',{'cached':255}),('next_track',{'cached':2}),
                      ('track_wrap',{'sector':15}),('ring_wrap',{'region':3,'high':255}),('short_retry',{'short':True})):
        old=run(**options,**case);new=run(**options,**case,fast_return_irq=True)
        timing[name]=dict(baseline=old,fixed=new,delta_tstates=new['tstates']-old['tstates'])
    keys=('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','publication_span_tstates','bad_actual_intervals')
    totals={v:{key:sum(row[v][key] for row in volumes) for key in keys} for v in ('baseline','fixed')}
    for variant in totals:
        totals[variant].update(actual_late_frames=sum(len(v[variant]['actual_late_indices']) for v in volumes),
            missing_irq_fields=sum(len(v[variant]['irq']['missing_irq_fields']) for v in volumes),
            queue_and_ay_wait_cpu=sum(v[variant]['audio_wait']['queue_and_full_wait_cpu'] for v in volumes))
    report=dict(complete=True,release=False,scope=__doc__,baseline_commit='347f995',
        build_sha256=sha((ROOT/'fast_return_irq_build.json').read_bytes()),evidence=files,
        source_sha256={f:sha((ROOT/f).read_bytes()) for f in ('summarize_fast_return_irq.py','benchmark_fap3_disk.py',
            'fast_return_irq.py','test_fast_return_irq.py','replay_queue_calls.py','measure_fap3_fuse.py',
            'audit_irq_fields.py','profile_integrated_timing.py','inline_huffman_patches_cpu.json')},
        timing=timing,volumes=volumes,totals=totals,
        lost_irq_bug_absent_in_all_complete_fixed_runs=totals['fixed']['missing_irq_fields']==0,
        capacity_met=all(v['used_sectors']<=2544 for v in volumes),compressed_streams_exact=True,
        phases_matched=False,full_pixel_comparison=False,pixel_samples_per_frame=80,
        physical_drive_verified=False,other_video_verified=False,
        nominal_schedule_met=totals['fixed']['actual_late_frames']==0,
        fallback_met=all(v['fixed']['max_actual_deviation_tstates']<=70908+64 and not v['fixed']['bad_actual_intervals'] for v in volumes),
        ay_continuity_met=totals['fixed']['audio_underruns']==0 and totals['fixed']['missing_irq_fields']==0 and
            all(not v['fixed']['ay_record_field_gaps'] and not v['fixed']['ay_record_field_duplicates'] for v in volumes))
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(totals,indent=2),flush=True)


if __name__=='__main__':main()
