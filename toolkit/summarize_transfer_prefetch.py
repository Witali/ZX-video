"""Archive the paired real-TRD runs and account for work during full AY waits.

CPU comes from replaying real queue requests and the Z80 instruction table.
Elapsed read/seek service includes ROM, IRQ, ULA and controller latency.
Neither quantity may be subtracted twice or labelled pure disk rotation.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from profile_integrated_timing import stats
from summarize_uncontended_frame import metrics

ROOT=Path(__file__).parent


def first_late_window(r,*,actual=False):
    first=next((i for i,p in enumerate(r['publications']) if
                (r['actual_phase_tstates'][i]>64 if actual else p['late_fields'])),None)
    if first is None:return []
    events={kind:[e for e in r['pipeline_events'] if e['kind']==kind] for kind in
        ('packet_start','video_payload_ready','packet_ready','prepare_start','prepare_end','draw_start','native_done')}
    if any(len(v)!=r['frames'] for v in events.values()):raise ValueError('incomplete frame boundaries')
    rows=[];origin=r['publications'][0]['tstate']
    for i in range(max(0,first-3),min(r['frames'],first+4)):
        rows.append(dict(local_frame=i,late_fields=r['publications'][i]['late_fields'],
            native_slack_tstates=origin+i*425448-events['native_done'][i]['tstate'],
            ready_slots_at_packet=events['packet_start'][i]['count'],
            stages={name:events[end][i]['tstate']-events[start][i]['tstate'] for name,start,end in
                (('transfer','packet_start','video_payload_ready'),('metadata','video_payload_ready','packet_ready'),
                 ('prepare','prepare_start','prepare_end'),('draw','draw_start','native_done'))}))
    return rows


def audio_analysis(r,cpu):
    spans=[];active=None;hits=0;freed_before_hook=0
    for event in r['audio_enqueue_events']:
        if event['kind']=='enqueue_start':
            if active is not None:raise ValueError('nested enqueue')
            active=event['tstate'];hits=0
        elif event['kind']=='enqueue_full':
            occupied=(event['write_index']-event['read_index'])&31
            # IRQ may free one record between foreground CP/JP and this
            # breakpoint. The branch was taken using the earlier read index.
            if active is None or occupied not in (30,31):raise ValueError('invalid full-branch occupancy')
            freed_before_hook+=occupied==30
            hits+=1
        else:
            if active is None or event['tstate']<active:raise ValueError('unmatched enqueue')
            spans.append(dict(start=active,end=event['tstate'],full_hits=hits));active=None
    if active is not None or len(spans)!=r['frames']:raise ValueError('incomplete enqueue trace')
    steps=[];position=0
    for call in cpu['calls']:
        while position<len(spans) and spans[position]['end']<=call['start']:position+=1
        if call['kind']=='step' and position<len(spans) and spans[position]['start']<=call['start']:
            if call['end']>spans[position]['end']:raise ValueError('step crosses enqueue boundary')
            steps.append(call)
    full=sum(s['full_hits'] for s in spans)
    enabled=r.get('audio_wait_prefetch',{}).get('enabled',False)
    if len(steps)!=(full if enabled else 0):raise ValueError('full-wait step count differs')
    if any(c['return_a'] not in (0,1) for c in steps):raise ValueError('invalid step status')
    busy=sum(c['return_a']==1 for c in steps);idle=len(steps)-busy
    # A full check is re-executed after each failed attempt: 55 T. Previous
    # EI/HALT/JP costs 18 T (excluding HALT waiting). New helper costs 62/80 T
    # plus callee work. Queue replay already includes the helper's 17-T CALL.
    extra=100*busy+118*idle if enabled else 73*full
    return dict(full_hits=full,irq_freed_slot_before_hook=freed_before_hook,frames_blocked=sum(s['full_hits']>0 for s in spans),
        enqueue_elapsed=stats([s['end']-s['start'] for s in spans]),
        prefetch_calls=len(steps),prefetch_busy=busy,prefetch_idle=idle,
        prefetch_sectors=sum(c['sectors'] for c in steps),
        prefetch_cpu_including_call=sum(c['cpu_tstates'] for c in steps),
        additional_wait_cpu_not_in_queue_replay=extra,
        queue_and_full_wait_cpu=sum(c['cpu_tstates'] for c in cpu['calls'])+extra,
        formula='baseline: queue CPU + 73*full; prefetch: queue CPU + 100*busy + 118*idle',
        excludes='ordinary successful enqueue copy, other parser code, rendering, IRQ, ULA, ROM and physical latency')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path);p.add_argument('--prefetch',type=Path)
    p.add_argument('--directory',type=Path)
    p.add_argument('--evidence',type=Path,default=ROOT/'transfer_prefetch_evidence')
    p.add_argument('--output',type=Path,default=ROOT/'audio_wait_prefetch_summary.json')
    a=p.parse_args();files=[]
    if a.baseline:
        if not a.prefetch or not a.directory:raise ValueError('all fresh paths required')
        a.evidence.mkdir(parents=True,exist_ok=True)
        for name,directory in (('baseline',a.baseline),('prefetch',a.prefetch)):
            for part in (1,2,3):
                r=json.loads((directory/f'part{part:02}.json').read_bytes())
                meta=(ROOT/'bank2_zx0_evidence'/f'part{part:02}.metadata.json' if name=='baseline' else
                      a.directory/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()
                if sha(meta)!=r['integrated_bootstrap_metadata_sha256']:raise ValueError('metadata differs')
                blobs={'.json':(directory/f'part{part:02}.json').read_bytes()}
                if name=='prefetch':blobs['.metadata.json']=meta
                for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                    blob=(directory/f'part{part:02}{suffix}').read_bytes()
                    if sha(blob)!=r[key]:raise ValueError('trace changed')
                    blobs[suffix]=blob
                for suffix,blob in blobs.items():
                    dest=f'{name}_part{part:02}{suffix}.gz';packed=gzip.compress(blob,mtime=0)
                    (a.evidence/dest).write_bytes(packed)
                    files.append(dict(file=dest,sha256=sha(packed),uncompressed_sha256=sha(blob)))
    else:files=json.loads(a.output.read_bytes())['evidence']
    for f in files:
        blob=(a.evidence/f['file']).read_bytes()
        if sha(blob)!=f['sha256'] or sha(gzip.decompress(blob))!=f['uncompressed_sha256']:raise ValueError('archive changed')
    build_path=ROOT/'audio_wait_prefetch_build.json';built=json.loads(build_path.read_bytes())
    cpus={n:json.loads((ROOT/f).read_bytes()) for n,f in
          (('baseline','transfer_cpu_profile.json'),('prefetch','audio_wait_prefetch_cpu.json'))}
    if not built['complete'] or any(not c['complete'] for c in cpus.values()):raise ValueError('incomplete model or build')
    if any(c['source_sha256']!=sha((ROOT/'replay_queue_calls.py').read_bytes()) for c in cpus.values()):raise ValueError('replay source changed')
    for name,digest in built['source_sha256'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError(('builder source changed',name))
    volumes=[]
    for part in (1,2,3):
        row=dict(part=part,used_sectors=built['volumes'][part-1]['used_sectors'])
        for name in ('baseline','prefetch'):
            raw=gzip.decompress((a.evidence/f'{name}_part{part:02}.json.gz').read_bytes());r=json.loads(raw)
            cpu=cpus[name]['volumes'][part-1]
            meta=(ROOT/'bank2_zx0_evidence'/f'part{part:02}.metadata.json').read_bytes() if name=='baseline' else gzip.decompress((a.evidence/f'{name}_part{part:02}.metadata.json.gz').read_bytes())
            m=json.loads(meta)
            if (sum(cpu['cpu_stages'].values())!=sum(c['cpu_tstates'] for c in cpu['calls']) or
                len(r['queue_call_events'])!=2*len(cpu['calls'])):raise ValueError('CPU aggregate differs')
            for call,before,after in zip(cpu['calls'],r['queue_call_events'][::2],r['queue_call_events'][1::2]):
                if (call['start']!=before['tstate'] or call['end']!=after['tstate'] or
                    call['elapsed_tstates']!=call['end']-call['start'] or
                    call['cpu_tstates']!=sum(call['cpu_stages'].values())):raise ValueError('CPU call differs')
            if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact'] or
                not r['ay_records_exact'] or r['debugger_installed_bytes'] or r['fast_read_retries'] or
                not r['progress_100_percent'] or r['frames']!=m['frames'] or r['ay_ticks']!=6*m['frames'] or
                r['runtime_sectors_checked']!=m['video_sectors'] or sha(raw)!=cpu['trace_report_sha256'] or
                r['trd_sha256']!=m['trd_sha256'] or r['trd_sha256']!=cpu['trd_sha256'] or
                sha(meta)!=r['integrated_bootstrap_metadata_sha256']):raise ValueError('incomplete/different evidence')
            script=gzip.decompress((a.evidence/f'{name}_part{part:02}.debugger.txt.gz').read_bytes()).decode()
            if any(line.startswith('se ') and line[3:].split(' ',1)[0].isdigit() for line in script.splitlines()):raise ValueError('RAM writes')
            if name=='prefetch' and (not m['audio_wait_prefetch']['enabled'] or m['trd_sha256']!=built['volumes'][part-1]['trd_sha256']):raise ValueError('wrong variant')
            row[name]=dict(metrics(r),audio_wait=audio_analysis(r,cpu),queue_cpu_stages=cpu['cpu_stages'],
                actual_nominal_late_frames=sum(t>64 for t in r['actual_phase_tstates']),
                actual_nominal_late_indices=[i for i,t in enumerate(r['actual_phase_tstates']) if t>64],
                first_counter_late_window=first_late_window(r),
                first_actual_late_window=first_late_window(r,actual=True),
                queue_call_count=len(cpu['calls']),trd_sha256=r['trd_sha256'],stream_sha256=cpu['stream_sha256'])
        if row['baseline']['stream_sha256']!=row['prefetch']['stream_sha256']:raise ValueError('stream changed')
        volumes.append(row)
    keys=('frames','nominal_late_frames','actual_nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','read_service_tstates',
          'seek_service_tstates','publication_span_tstates','bad_actual_intervals')
    totals={name:{key:sum(v[name][key] for v in volumes) for key in keys} for name in cpus}
    for name in cpus:
        totals[name]['queue_and_full_wait_cpu']=sum(v[name]['audio_wait']['queue_and_full_wait_cpu'] for v in volumes)
    result=dict(complete=True,release=False,scope=__doc__,baseline_commit='5749312',volumes=volumes,totals=totals,
        source_sha256=sha(Path(__file__).read_bytes()),build_report_sha256=sha(build_path.read_bytes()),
        cpu_report_sha256={n:sha((ROOT/f).read_bytes()) for n,f in
            (('baseline','transfer_cpu_profile.json'),('prefetch','audio_wait_prefetch_cpu.json'))},
        evidence=files,initial_disk_and_irq_phases_not_matched=True,fuse_samples_per_frame=80,
        full_fuse_pixel_comparison=False,physical_drive_verified=False,
        capacity_verified=all(v['used_sectors']<=2544 for v in volumes),
        nominal_schedule_met=all(v['prefetch']['nominal_late_frames']==0 and v['prefetch']['max_actual_deviation_tstates']<=64 for v in volumes),
        fallback_met=all(v['prefetch']['actual_out_over_one_field']==0 and v['prefetch']['bad_actual_intervals']==0 for v in volumes),
        ay_schedule_met=all(v['prefetch']['audio_underruns']==0 for v in volumes))
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(totals=totals,fps=[v['prefetch']['fps'] for v in volumes],
        audio_wait=[{n:v[n]['audio_wait'] for n in cpus} for v in volumes])),flush=True)


if __name__=='__main__':main()
