"""Locate delivery costs in complete real-TRD traces, without changing Z80.

Stage durations are elapsed Fuse T-states, including IRQ and ULA. Disk and
seek intervals are separately intersected with stages; residual time is NOT
called deterministic CPU time. A saved full CPU model is reported separately.
"""
import argparse
from bisect import bisect_right
from collections import Counter,defaultdict
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha
from summarize_uncontended_frame import metrics

FIELD=70908
PERIOD=6*FIELD


def stats(values):
    values=sorted(values);n=len(values)
    return dict(count=n,total=sum(values),mean=sum(values)/n if n else 0,
        p50=values[(n-1)//2] if n else 0,p90=values[(n-1)*90//100] if n else 0,
        p99=values[(n-1)*99//100] if n else 0,max=max(values,default=0))


def merged(intervals):
    result=[]
    for start,end in sorted(intervals):
        if end<start:raise ValueError('negative interval')
        if result and start<=result[-1][1]:result[-1]=(result[-1][0],max(result[-1][1],end))
        else:result.append((start,end))
    return result


def overlap(intervals,start,end):
    return sum(max(0,min(end,b)-max(start,a)) for a,b in intervals if a<end and b>start)


def analyze(r,m,cpu):
    if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact'] or
        not r['integrated_slot_queue'] or r['debugger_installed_bytes'] or
        not r['ay_records_exact'] or r['fast_read_retries'] or r['trd_sha256']!=m['trd_sha256']):
        raise ValueError('incomplete/wrong playback')
    grouped=defaultdict(list)
    for e in r['pipeline_events']:grouped[e['kind']].append(e)
    boundaries=('packet_start','video_payload_ready','packet_ready','prepare_start','prepare_end','draw_start','native_done')
    if any(len(grouped[k])!=m['frames'] for k in boundaries):raise ValueError('missing stage boundaries')
    starts=grouped['empty_wait_start'];ends=grouped['empty_wait_end']
    if len(starts)!=len(ends):raise ValueError('unmatched empty waits')
    waits=[(a['tstate'],b['tstate']) for a,b in zip(starts,ends)]
    if any(b<a for a,b in waits) or len(merged(waits))!=len(waits):raise ValueError('invalid waits')
    read=[(v['start_tstate'],v['end_tstate']) for v in r['reads']]
    seek=[(v['start_tstate'],v['end_tstate']) for v in r['seek_calls']]
    service=merged(read+seek)
    stage_pairs=(('transfer','packet_start','video_payload_ready'),('metadata','video_payload_ready','packet_ready'),
                 ('prepare','prepare_start','prepare_end'),('draw','draw_start','native_done'))
    all_stages=[];frames=[];base=r['publications'][0]['tstate']
    for i,pub in enumerate(r['publications']):
        row=dict(frame=m['frame_start']+i,local_frame=i,nominal_tstate=base+i*PERIOD,
                 publication_tstate=pub['tstate'],late_fields=pub['late_fields'],stages={})
        for name,lo,hi in stage_pairs:
            a,b=grouped[lo][i]['tstate'],grouped[hi][i]['tstate']
            if b<a:raise ValueError('negative stage')
            io=overlap(service,a,b)
            row['stages'][name]=dict(start=a,end=b,elapsed=b-a,disk_service=io,
                residual=b-a-io,empty_wait=overlap(waits,a,b))
            all_stages.append((a,b,name,i))
        s=row['stages']
        if not s['transfer']['end']<=s['metadata']['end']<=s['prepare']['start']<=s['prepare']['end']<=s['draw']['start']<=s['draw']['end']<=pub['tstate']:
            raise ValueError('invalid frame lifetime')
        row.update(work_elapsed=sum(v['elapsed'] for v in s.values()),
            native_ready_slack=row['nominal_tstate']-s['draw']['end'],
            draw_start_after_preceding_out=s['draw']['start']-r['publications'][i-1]['tstate'] if i else None,
            stage_cpu_reference=cpu['frames'][i]['tstates'],queue_count_at_packet=grouped['packet_start'][i]['count'])
        frames.append(row)
    all_stages.sort()
    if any(a[1]>b[0] for a,b in zip(all_stages,all_stages[1:])):raise ValueError('overlapping foreground stages')
    stage_starts=[s[0] for s in all_stages];deadlines=Counter()
    for f in frames:
        index=bisect_right(stage_starts,f['nominal_tstate'])-1
        active=all_stages[index] if index>=0 and all_stages[index][1]>f['nominal_tstate'] else None
        f['phase_at_nominal']=active[2] if active else 'control_or_wait'
        f['phase_frame_at_nominal']=m['frame_start']+active[3] if active else None
        if f['late_fields']:deadlines[f['phase_at_nominal']]+=1
    phases={name:{field:stats([f['stages'][name][field] for f in frames])
                  for field in ('elapsed','disk_service','residual','empty_wait')} for name,_,_ in stage_pairs}
    return dict(part=m['part'],frames=frames,metrics=metrics(r),stages=phases,
        work_elapsed=stats([f['work_elapsed'] for f in frames]),
        individual_frames_over_six_fields=sum(f['work_elapsed']>PERIOD for f in frames),
        late_despite_native_ready_1000T_early=sum(f['late_fields']>0 and f['native_ready_slack']>=1000 for f in frames),
        empty_wait=stats([b-a for a,b in waits]),late_phase_histogram=dict(deadlines),
        queue_at_packet=dict(Counter(f['queue_count_at_packet'] for f in frames)),
        total_disk_service=sum(b-a for a,b in service),
        disk_service_inside_transfer=phases['transfer']['disk_service']['total'],
        draw_start_after_previous=stats([f['draw_start_after_preceding_out'] for f in frames[1:]]))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('fresh','directory'):p.add_argument('--'+key,type=Path)
    p.add_argument('--evidence',type=Path,default=Path('toolkit/integrated_timing_evidence'))
    p.add_argument('--output',type=Path,default=Path('toolkit/integrated_timing_profile.json'))
    a=p.parse_args();files=[]
    if a.fresh:
        if not a.directory:raise ValueError('metadata required')
        a.evidence.mkdir(parents=True,exist_ok=True)
        for part in (1,2,3):
            path=a.fresh/f'part{part:02}.json';r=json.loads(path.read_bytes())
            meta=(a.directory/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()
            if sha(meta)!=r['integrated_bootstrap_metadata_sha256']:raise ValueError('metadata changed')
            for name,blob in ((path.name,(json.dumps(r,indent=2)+'\n').encode()),(f'part{part:02}.metadata.json',meta)):
                (a.evidence/name).write_bytes(blob);files.append(dict(file=name,sha256=sha(blob)))
            for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                blob=path.with_suffix(suffix).read_bytes()
                if sha(blob)!=r[key]:raise ValueError('trace changed')
                name=path.stem+suffix+'.gz';packed=gzip.compress(blob,mtime=0);(a.evidence/name).write_bytes(packed)
                files.append(dict(file=name,sha256=sha(packed),uncompressed_sha256=sha(blob)))
    else:files=json.loads(a.output.read_bytes())['evidence']
    for f in files:
        blob=(a.evidence/f['file']).read_bytes()
        if sha(blob)!=f['sha256']:raise ValueError('archive changed')
        if 'uncompressed_sha256' in f and sha(gzip.decompress(blob))!=f['uncompressed_sha256']:raise ValueError('corrupt trace')
    model_path=Path('toolkit/inline_huffman_patches_cpu.json');model=json.loads(model_path.read_bytes())
    result=dict(complete=False,release=False,scope=__doc__,baseline_commit='b94c9ed',
        code_and_stream_unchanged=True,deterministic_player_cpu_delta_tstates=0,
        cpu_model_sha256=sha(model_path.read_bytes()),source_sha256=sha(Path(__file__).read_bytes()),volumes=[],evidence=files)
    for part in (1,2,3):
        r=json.loads((a.evidence/f'part{part:02}.json').read_bytes());m=json.loads((a.evidence/f'part{part:02}.metadata.json').read_bytes())
        cpu=model['volumes'][part-1]
        if m['raw_sha256']!=cpu['raw_sha256'] or m['frames']!=cpu['checked_frames']:raise ValueError('wrong CPU reference')
        v=analyze(r,m,cpu);result['volumes'].append(v)
        print(json.dumps({k:v[k] for k in ('part','stages','work_elapsed','individual_frames_over_six_fields',
            'late_despite_native_ready_1000T_early','empty_wait','late_phase_histogram','queue_at_packet',
            'total_disk_service','disk_service_inside_transfer','draw_start_after_previous')}),flush=True)
    # Bound the next relocation from the actually assembled decoder and the
    # independent, earlier CPU histogram. This is a candidate, not a speedup.
    import bank_local_zx0
    blob,z=bank_local_zx0.build(dynamic_input=True,inline_literals=True)
    cpu_queue_path=Path('toolkit/demand_decode_cpu.json')
    cpu_queue=json.loads(cpu_queue_path.read_bytes())
    tail=blob[z['slice_begin']-bank_local_zx0.CODE:]
    candidates=[]
    for part in (1,2,3):
        m=json.loads((a.evidence/f'part{part:02}.metadata.json').read_bytes())
        hp=m['inline_huffman_patches'];start=hp['redirect_address']+3
        # The instruction following the final original CALL bitmap is EXX,
        # store and RET. This RET is still targeted by the empty-mask path.
        limit=max(hp['original_call_sites'])+5
        rows=m['slot_queue_instruction_listing']
        if not any(r['address']==limit and r['instruction']=='RET' for r in rows):
            raise ValueError('retained empty-mask return not found')
        profile=cpu_queue['volumes'][part-1]['summary']['demand']
        hot=sum(r['tstates']*r['count'] for r in profile['instruction_histogram']
                if z['slice_begin']<=r['pc']<z['state'])
        candidates.append(dict(part=part,origin=start,limit_exclusive=limit,
            available_bytes=limit-start,required_bytes=len(tail),fits=len(tail)<=limit-start,
            prior_hot_core_cpu_tstates=hot,prior_all_zx0_cpu_tstates=profile['stages']['local_zx0']))
    result['next_candidate']=dict(name='move ZX0 slice_begin through state into retired fixed sparse-patch body',
        implemented=False,depends_on_inline_huffman=True,old_core_origin=z['slice_begin'],
        old_end_exclusive=z['end'],prefix_bytes=z['slice_begin']-bank_local_zx0.CODE,
        old_code_sha256=sha(blob),old_tail_sha256=sha(tail),volumes=candidates,
        prior_queue_cpu_report_sha256=sha(cpu_queue_path.read_bytes()),
        estimated_opcode_tstate_delta=0,measured_contention_saving_tstates=None,
        required_changes=['relocate absolute operands and suspended return addresses',
                          'rebuild queue, producer and parser references',
                          'preserve empty-mask RET and inline redirect',
                          'disable when inline Huffman is unavailable',
                          'verify every block and IRQ boundary, bootstrap size, and full Fuse deadlines'])
    result.update(complete=True,frames=sum(len(v['frames']) for v in result['volumes']))
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
