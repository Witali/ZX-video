"""Audit complete prefix-guard playback against the archived IM2-fixed baseline."""
import argparse
from collections import Counter
from functools import lru_cache
import gzip
import json
from pathlib import Path

from audit_irq_fields import audit
from build_fap3_trd import sha
from profile_integrated_timing import analyze,stats
from summarize_fast_return_irq import rom_invariants
from summarize_transfer_prefetch import audio_analysis,first_late_window
from summarize_uncontended_frame import metrics
from test_packet_prefix_guard import PrefixTests

ROOT=Path(__file__).parent


@lru_cache(None)
def guard_model(count,phase,slot,position,produced,length,occupied):
    accepted,cpu,path,m=PrefixTests().execute(count=count,phase=phase,slot=slot,position=position,
        produced=produced,length=length,occupied=occupied)
    return accepted,cpu,m['peek'] in path,m['audio_ready'] in path


def optional(r,c):
    groups=[];current=None
    for event in r['optional_packet_events']:
        kind=event['kind']
        if kind=='start':
            if current is not None:raise ValueError('overlapping optional reads')
            current=dict(start=event)
        else:
            if current is None or kind in current:raise ValueError('unpaired optional read')
            current[kind]=event
            if kind=='end':groups.append(current);current=None
    if current is not None:raise ValueError('unfinished optional read')
    outcomes=Counter();cpu=0;elapsed=[];accepted_calls=0;details=[]
    for group in groups:
        start,end=group['start'],group['end'];count=start['count'];phase=start['phase']
        produced=start['length'] if count else (start['slice_output']+0x2000)&65535
        length=group.get('length',{}).get('body_length',294)
        occupied=group.get('audio',{}).get('occupancy',(start['audio_write']-start['audio_read'])&31)
        accepted,cost,peek,ay=guard_model(count,phase,start['read_slot'],start['position'],produced,length,occupied)
        if (end['accepted']!=int(accepted) or peek!=('length' in group) or ay!=('audio' in group)):
            raise ValueError(('guard differs from actual instruction model',group))
        cpu+=cost
        if accepted:
            reason='accepted_complete' if count else 'accepted_active_prefix'
            if produced-start['position']<length+2 or occupied>25:raise ValueError('unsafe optional packet')
            if any(start['tstate']<=v['start_tstate']<end['tstate'] for v in r['reads']):raise ValueError('optional disk I/O')
            if any(start['tstate']<=v['tstate']<end['tstate'] and v['kind']=='enqueue_full' for v in r['audio_enqueue_events']):
                raise ValueError('optional AY wait')
            calls=[v for v in c['calls'] if start['tstate']<=v['start']<end['tstate']]
            if (len(calls)!=2 or [v['kind'] for v in calls]!=['take','take'] or
                [v['copied_bytes'] for v in calls]!=[2,length] or any(v['end']>end['tstate'] or v['sectors'] or
                v['cpu_stages'].get('zx0',0) for v in calls)):raise ValueError('optional producer or unexpected calls')
            accepted_calls+=len(calls);elapsed.append(end['tstate']-start['tstate'])
        elif not count and phase!=2:reason='no_active_prefix'
        elif produced<start['position']:reason='invalid_position'
        elif not peek:reason='below_minimum_packet'
        elif not 294<=length<=4703:reason='invalid_body_length'
        elif not ay:reason='packet_incomplete'
        else:reason='audio_full'
        outcomes[reason]+=1
        details.append(dict(start=start['tstate'],end=end['tstate'],outcome=reason,cpu_tstates=cost,
            available=produced-start['position'],body_length=length if peek else None))
    return dict(outcomes=dict(outcomes),queries=len(groups),guard_cpu_tstates=cpu,
        previous_same_query_overhead_tstates=24*len(groups),
        extra_same_query_overhead_tstates=cpu-24*len(groups),
        accepted_elapsed=stats(elapsed),accepted_queue_calls=accepted_calls,
        accepted_disk_reads=0,accepted_zx0_tstates=0,accepted_ay_waits=0,queries_detail=details,
        note='Instruction CPU includes outer CALL and two NOPs; excludes parser body/RET, common pending store, IRQ, ULA and ROM. Query counts differ between runs.')


def timing():
    cases=dict(accepted=dict(),below_minimum=dict(produced=295),packet_incomplete=dict(produced=300,length=400),
        audio_full=dict(occupied=26),invalid_low=dict(length=293),invalid_high=dict(length=65535),
        invalid_position=dict(position=800,produced=700))
    rows=[]
    for count in (0,1):
        for slot in (0,3):
            for name,kw in cases.items():
                options=dict(count=count,phase=2,slot=slot,position=0,produced=8192,length=294,occupied=25);options.update(kw)
                accepted,t,peek,ay=guard_model(**options)
                rows.append(dict(case=name,options=options,accepted=accepted,peek=peek,audio_check=ay,
                    previous_tstates=24,new_tstates=t,delta_tstates=t-24))
    for phase in (0,1):
        options=dict(count=0,phase=phase,slot=0,position=0,produced=8192,length=294,occupied=25)
        accepted,t,_,_=guard_model(**options)
        rows.append(dict(case='no_active_prefix',options=options,accepted=accepted,previous_tstates=24,new_tstates=t,delta_tstates=t-24))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('fuse','directory','cpu'):p.add_argument('--'+key,type=Path)
    a=p.parse_args();evidence=ROOT/'packet_prefix_guard_evidence';output=ROOT/'packet_prefix_guard_summary.json'
    baseline=json.loads((ROOT/'fast_return_irq_summary.json').read_bytes())
    files=[dict(v,directory='fast_return_irq_evidence') for v in baseline['evidence'] if v['file'].startswith('fixed_')]
    if a.fuse:
        if a.directory is None or a.cpu is None:raise ValueError('all fresh paths required')
        evidence.mkdir(exist_ok=True);blobs={'prefix_cpu.json':a.cpu.read_bytes()}
        for part in (1,2,3):
            stem=f'part{part:02}'
            for suffix in ('.json','.debugger.txt','.trace.txt'):
                blobs['prefix_'+stem+suffix]=(a.fuse/(stem+suffix)).read_bytes()
            blobs['prefix_'+stem+'.metadata.json']=(a.directory/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()
        for name,raw in blobs.items():
            packed=gzip.compress(raw,mtime=0);name+='.gz';(evidence/name).write_bytes(packed)
            files.append(dict(directory=evidence.name,file=name,sha256=sha(packed),uncompressed_sha256=sha(raw)))
    else:
        previous=json.loads(output.read_bytes());files=previous['evidence']
        for name,digest in previous['source_sha256'].items():
            if sha((ROOT/name).read_bytes())!=digest:raise ValueError(('model source changed',name))
    for f in files:
        raw=(ROOT/f['directory']/f['file']).read_bytes()
        if sha(raw)!=f['sha256'] or sha(gzip.decompress(raw))!=f['uncompressed_sha256']:raise ValueError('archive changed')
    def blob(name):
        f=next(v for v in files if v['file']==name)
        return gzip.decompress((ROOT/f['directory']/name).read_bytes())
    def load(name):return json.loads(blob(name))
    build=json.loads((ROOT/'packet_prefix_guard_build.json').read_bytes())
    if not build['complete']:raise ValueError('incomplete build')
    for name,digest in build['source_sha256'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError(('builder source changed',name))
    cpus={v:load(v+'_cpu.json.gz') for v in ('fixed','prefix')}
    for c in cpus.values():
        if not c['complete'] or c['frames']!=4221 or c['source_sha256']!=sha((ROOT/'replay_queue_calls.py').read_bytes()):
            raise ValueError('incomplete or different CPU model')
    frame_cpu=json.loads((ROOT/'inline_huffman_patches_cpu.json').read_bytes());volumes=[]
    for part in (1,2,3):
        row=dict(part=part,used_sectors=build['volumes'][part-1]['used_sectors'])
        for variant in ('fixed','prefix'):
            stem=f'{variant}_part{part:02}';raw=blob(stem+'.json.gz');r=json.loads(raw)
            meta=blob(stem+'.metadata.json.gz');m=json.loads(meta);c=cpus[variant]['volumes'][part-1]
            if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact'] or
                not r['ay_records_exact'] or not r['progress_100_percent'] or r['debugger_installed_bytes'] or
                r['fast_read_retries'] or r['frames']!=m['frames'] or r['ay_ticks']!=6*m['frames'] or
                r['runtime_sectors_checked']!=m['video_sectors'] or r['trd_sha256']!=m['trd_sha256'] or
                r['trd_sha256']!=c['trd_sha256'] or sha(meta)!=r['integrated_bootstrap_metadata_sha256'] or
                sha(raw)!=c['trace_report_sha256']):raise ValueError('incomplete/different evidence')
            for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                if sha(blob(stem+suffix+'.gz'))!=r[key]:raise ValueError('trace mismatch')
            if any(s.startswith('se ') and s[3:].split(' ',1)[0].isdigit() for s in blob(stem+'.debugger.txt.gz').decode().splitlines()):
                raise ValueError('RAM writes')
            if len(r['queue_call_events'])!=2*len(c['calls']):raise ValueError('CPU count differs')
            for call,before,after in zip(c['calls'],r['queue_call_events'][::2],r['queue_call_events'][1::2]):
                if call['start']!=before['tstate'] or call['end']!=after['tstate'] or sum(call['cpu_stages'].values())!=call['cpu_tstates']:
                    raise ValueError('CPU call differs')
            irq=audit(r,m);irq.pop('actual_phase_tstates')
            profile=analyze(r,m,frame_cpu['volumes'][part-1]);worst=sorted(profile.pop('frames'),key=lambda v:v['work_elapsed'],reverse=True)[:12]
            row[variant]=dict(metrics(r),irq=irq,rom=rom_invariants(r,True),
                used_sectors=m['used_sectors'],video_start_sector=m['video_start_sector'],
                ay_record_field_gaps=r['ay_record_field_gaps'],ay_record_field_duplicates=r['ay_record_field_duplicates'],
                actual_late_indices=[i for i,t in enumerate(r['actual_phase_tstates']) if t>64],
                trd_sha256=m['trd_sha256'],stream_sha256=c['stream_sha256'],
                first_actual_late_window=first_late_window(r,actual=True),
                audio_wait=audio_analysis(r,c),queue_cpu_stages=c['cpu_stages'],queue_calls=len(c['calls']),
                delivery_profile=profile,worst_work_frames=worst,
                read_service=stats([v['tstates'] for v in r['reads']]),seek_service=stats([v['tstates'] for v in r['seek_calls']]))
            if variant=='prefix':
                if m['trd_sha256']!=build['volumes'][part-1]['trd_sha256']:raise ValueError('build differs')
                row[variant]['optional']=optional(r,c)
        if row['prefix']['stream_sha256']!=row['fixed']['stream_sha256']:raise ValueError('stream changed')
        volumes.append(row)
    keys=('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','publication_span_tstates','bad_actual_intervals')
    totals={variant:{key:sum(v[variant][key] for v in volumes) for key in keys} for variant in ('fixed','prefix')}
    for variant in totals:
        totals[variant].update(actual_late_frames=sum(len(v[variant]['actual_late_indices']) for v in volumes),
            missing_irq_fields=sum(len(v[variant]['irq']['missing_irq_fields']) for v in volumes),
            queue_and_ay_wait_cpu=sum(v[variant]['audio_wait']['queue_and_full_wait_cpu'] for v in volumes))
    totals['prefix']['guard_cpu_tstates']=sum(v['prefix']['optional']['guard_cpu_tstates'] for v in volumes)
    totals['prefix']['extra_same_query_guard_cpu_tstates']=sum(v['prefix']['optional']['extra_same_query_overhead_tstates'] for v in volumes)
    report=dict(complete=True,release=False,scope=__doc__,baseline_commit='a758f8c',evidence=files,
        build_sha256=sha((ROOT/'packet_prefix_guard_build.json').read_bytes()),
        baseline_summary_sha256=sha((ROOT/'fast_return_irq_summary.json').read_bytes()),
        source_sha256={f:sha((ROOT/f).read_bytes()) for f in ('summarize_packet_prefix_guard.py','packet_prefix_guard.py',
            'test_packet_prefix_guard.py','replay_queue_calls.py','measure_fap3_fuse.py','test_fap3_disk.py',
            'benchmark_context_huffman.py','pipelined_frame_z80.py','audit_irq_fields.py','profile_integrated_timing.py',
            'summarize_fast_return_irq.py','summarize_transfer_prefetch.py','summarize_uncontended_frame.py','inline_huffman_patches_cpu.json')},
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',timing=timing(),volumes=volumes,totals=totals,
        timing_excludes=['packet body/RET','common pending store','IRQ','ULA','ROM','disk latency'],
        capacity_met=all(v['used_sectors']<=2544 for v in volumes),compressed_streams_exact=True,
        phases_matched=False,full_pixel_comparison=False,pixel_samples_per_frame=80,
        physical_drive_verified=False,other_video_verified=False,
        nominal_schedule_met=totals['prefix']['actual_late_frames']==0,
        fallback_met=all(v['prefix']['max_actual_deviation_tstates']<=70908+64 and not v['prefix']['bad_actual_intervals'] for v in volumes),
        ay_continuity_met=totals['prefix']['audio_underruns']==0 and totals['prefix']['missing_irq_fields']==0 and
            all(not v['prefix']['ay_record_field_gaps'] and not v['prefix']['ay_record_field_duplicates'] for v in volumes))
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(totals,indent=2),flush=True)


if __name__=='__main__':main()
