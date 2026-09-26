"""Archive and verify complete optional-read experiments, including missed IRQs."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha
from audit_irq_fields import audit
from profile_integrated_timing import stats
from summarize_transfer_prefetch import audio_analysis,first_late_window
from summarize_uncontended_frame import metrics

ROOT=Path(__file__).parent


def optional(r,m):
    events=r['optional_packet_events'];counts=Counter();elapsed=[];cpu=0
    if len(events)%2:raise ValueError('unpaired guard events')
    for start,end in zip(events[::2],events[1::2]):
        if start['kind']!='start' or end['kind']!='end' or end['accepted'] not in (0,1):raise ValueError('guard event mismatch')
        if end['accepted']:
            reason='accepted'
            if not start['count'] or start['length']-start['position']<4705:raise ValueError('unsafe slot accepted')
            if any(start['tstate']<=v['start_tstate']<end['tstate'] for v in r['reads']):raise ValueError('optional disk I/O')
            if any(start['tstate']<=v['tstate']<end['tstate'] and v['kind']=='enqueue_full' for v in r['audio_enqueue_events']):raise ValueError('optional AY wait')
            elapsed.append(end['tstate']-start['tstate'])
        elif not start['count']:reason='no_slot'
        elif start['length']-start['position']<4705:reason='short_slot'
        else:reason='audio_full'
        counts[reason]+=1;cpu+=m['ready_packet_guard'][reason+'_overhead_tstates']
    return dict(outcomes=dict(counts),guard_cpu_tstates=cpu,accepted_elapsed=stats(elapsed),
        accepted_disk_reads=0,accepted_ay_waits=0,
        note='Guard CPU includes caller CALL/NOPs, excludes packet body/RET and common pending store.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fuse',type=Path);p.add_argument('--directory',type=Path);p.add_argument('--irq-baseline',type=Path)
    a=p.parse_args();evidence=ROOT/'ready_packet_guard_evidence';output=ROOT/'ready_packet_guard_summary.json'
    if a.fuse:
        if not a.directory or not a.irq_baseline:raise ValueError('all fresh paths required')
        evidence.mkdir(exist_ok=True);files=[]
        for name,path,meta in [('guard',a.fuse/f'part{i:02}.json',a.directory/f'ZX-video-huffman-preview_part{i:02}.json') for i in (1,2,3)]+[
            ('irqbase',a.irq_baseline,None)]:
            blobs={'.json':path.read_bytes()}
            if meta:blobs['.metadata.json']=meta.read_bytes()
            for suffix in ('.trace.txt','.debugger.txt'):blobs[suffix]=path.with_suffix(suffix).read_bytes()
            for suffix,blob in blobs.items():
                dest=name+'_'+path.stem+suffix+'.gz';packed=gzip.compress(blob,mtime=0)
                (evidence/dest).write_bytes(packed)
                files.append(dict(file=dest,sha256=sha(packed),uncompressed_sha256=sha(blob)))
    else:files=json.loads(output.read_bytes())['evidence']
    for f in files:
        blob=(evidence/f['file']).read_bytes()
        if sha(blob)!=f['sha256'] or sha(gzip.decompress(blob))!=f['uncompressed_sha256']:raise ValueError('archive changed')
    def data(directory,name):return gzip.decompress((directory/name).read_bytes())
    def load(directory,name):return json.loads(data(directory,name))
    olddir=ROOT/'transfer_prefetch_evidence';built=json.loads((ROOT/'ready_packet_guard_build.json').read_bytes())
    cpus={name:json.loads((ROOT/file).read_bytes()) for name,file in
        (('baseline','audio_wait_prefetch_cpu.json'),('guard','ready_packet_guard_cpu.json'))}
    if not built['complete'] or any(not c['complete'] for c in cpus.values()):raise ValueError('incomplete build or CPU replay')
    if any(c['source_sha256']!=sha((ROOT/'replay_queue_calls.py').read_bytes()) for c in cpus.values()):raise ValueError('CPU replay source changed')
    for file,digest in built['source_sha256'].items():
        if sha((ROOT/file).read_bytes())!=digest:raise ValueError(('source changed',file))
    volumes=[]
    for part in (1,2,3):
        row=dict(part=part,used_sectors=built['volumes'][part-1]['used_sectors'])
        for variant,directory,prefix in (('baseline',olddir,'prefetch'),('guard',evidence,'guard')):
            stem=f'{prefix}_part{part:02}'
            blob=data(directory,stem+'.json.gz');r=json.loads(blob)
            meta=data(directory,stem+'.metadata.json.gz');m=json.loads(meta);cpu=cpus[variant]['volumes'][part-1]
            if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact'] or not r['ay_records_exact'] or
                r['debugger_installed_bytes'] or r['fast_read_retries'] or not r['progress_100_percent'] or
                r['frames']!=m['frames'] or r['ay_ticks']!=6*m['frames'] or r['runtime_sectors_checked']!=m['video_sectors'] or
                sha(meta)!=r['integrated_bootstrap_metadata_sha256'] or sha(blob)!=cpu['trace_report_sha256'] or
                r['trd_sha256']!=m['trd_sha256'] or r['trd_sha256']!=cpu['trd_sha256']):raise ValueError('incomplete evidence')
            for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                if sha(data(directory,stem+suffix+'.gz'))!=r[key]:raise ValueError('trace mismatch')
            script=data(directory,stem+'.debugger.txt.gz').decode()
            if any(s.startswith('se ') and s[3:].split(' ',1)[0].isdigit() for s in script.splitlines()):raise ValueError('RAM writes')
            if len(r['queue_call_events'])!=2*len(cpu['calls']):raise ValueError('CPU count mismatch')
            for c,b,e in zip(cpu['calls'],r['queue_call_events'][::2],r['queue_call_events'][1::2]):
                if c['start']!=b['tstate'] or c['end']!=e['tstate'] or sum(c['cpu_stages'].values())!=c['cpu_tstates']:raise ValueError('CPU mismatch')
            row[variant]=dict(metrics(r),trd_sha256=r['trd_sha256'],stream_sha256=cpu['stream_sha256'],
                actual_late_indices=[i for i,t in enumerate(r['actual_phase_tstates']) if t>64],
                first_counter_late_window=first_late_window(r),first_actual_late_window=first_late_window(r,actual=True),
                queue_cpu_stages=cpu['cpu_stages'],audio_wait=audio_analysis(r,cpu))
            if variant=='guard':
                if m['trd_sha256']!=built['volumes'][part-1]['trd_sha256']:raise ValueError('build differs')
                row[variant].update(optional=optional(r,m),irq=audit(r,m))
        if row['guard']['stream_sha256']!=row['baseline']['stream_sha256']:raise ValueError('stream changed')
        volumes.append(row)
    irqbase=load(evidence,'irqbase_part01.json.gz');oldmeta=load(olddir,'prefetch_part01.metadata.json.gz')
    for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
        if sha(data(evidence,'irqbase_part01'+suffix+'.gz'))!=irqbase[key]:raise ValueError('IRQ trace mismatch')
    keys=('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','publication_span_tstates','bad_actual_intervals')
    totals={variant:{key:sum(v[variant][key] for v in volumes) for key in keys} for variant in ('baseline','guard')}
    for variant in totals:
        totals[variant]['actual_late_frames']=sum(len(v[variant]['actual_late_indices']) for v in volumes)
        totals[variant]['queue_and_ay_wait_cpu']=sum(v[variant]['audio_wait']['queue_and_full_wait_cpu'] for v in volumes)
    report=dict(complete=True,release=False,baseline_commit='347f995',scope=__doc__,evidence=files,
        source_sha256=sha(Path(__file__).read_bytes()),build_sha256=sha((ROOT/'ready_packet_guard_build.json').read_bytes()),
        cpu_sha256={k:sha((ROOT/f).read_bytes()) for k,f in (('baseline','audio_wait_prefetch_cpu.json'),('guard','ready_packet_guard_cpu.json'))},
        volumes=volumes,totals=totals,baseline_irq=audit(irqbase,oldmeta),
        pixel_samples_per_frame=80,full_pixel_comparison=False,physical_drive_verified=False,
        phases_matched=False,compressed_streams_exact=True,capacity_met=all(v['used_sectors']<=2544 for v in volumes),
        nominal_schedule_met=totals['guard']['actual_late_frames']==0,
        fallback_met=all(v['guard']['max_actual_deviation_tstates']<=70908+64 and not v['guard']['bad_actual_intervals'] for v in volumes),
        ay_continuity_met=totals['guard']['audio_underruns']==0 and all(not v['guard']['irq']['missing_irq_fields'] for v in volumes))
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(totals,indent=2))


if __name__=='__main__':main()
