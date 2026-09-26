"""Measure repeated-zero mask groups against complete HL-reader delivery traces.

This is an offline opportunity profile, not a new Z80 implementation or speedup.
Every disk starts with unknown previous masks; no history crosses disk boundaries.
"""
import argparse
from bisect import bisect_right
from collections import Counter
import gzip
import json
from pathlib import Path
import struct
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
from bulk_frame_stream import read_packet
from compiled_masks_z80 import expected_tstates
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from profile_integrated_timing import analyze,stats,PERIOD,FIELD

ROOT=Path(__file__).parent


def enqueue_spans(trace,cpu):
    spans=[];active=None
    for event in trace['audio_enqueue_events']:
        if event['kind']=='enqueue_start':
            if active is not None:raise ValueError('nested enqueue')
            active=dict(start=event['tstate'],full_hits=0,steps=[])
        elif event['kind']=='enqueue_full':
            if active is None:raise ValueError('full outside enqueue')
            active['full_hits']+=1
        else:
            if active is None:raise ValueError('end without enqueue')
            active['end']=event['tstate'];spans.append(active);active=None
    if active is not None or len(spans)!=trace['frames']:raise ValueError('incomplete enqueue spans')
    starts=[s['start'] for s in spans]
    for call in cpu['calls']:
        i=bisect_right(starts,call['start'])-1
        if call['kind']=='step' and i>=0 and call['start']<spans[i]['end']:
            if call['end']>spans[i]['end']:raise ValueError('step crosses enqueue end')
            spans[i]['steps'].append(call)
    if sum(len(s['steps']) for s in spans)!=sum(s['full_hits'] for s in spans):raise ValueError('missing prefetch calls')
    return spans


def lower_flags(encoded):
    pos=8;lower=[]
    for upper in encoded[:8]:
        for bit in range(8):
            present=upper&(128>>bit);lower.append(encoded[pos] if present else 0);pos+=bool(present)
    if len(lower)!=64 or any(lower[60:]):raise ValueError('bad flags/padding')
    expanded=restore(encoded,1,480,4)
    if any(bool(lower[i])!=bool(any(expanded[i*8:i*8+8])) for i in range(60)):
        raise ValueError('flags do not describe expanded masks')
    return lower[:60],expanded


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,help='Fresh exact three-volume HL-reader images; omit to audit saved masks')
    a=p.parse_args();out=ROOT/'zero_mask_history_profile.json';archive=ROOT/'zero_mask_history_evidence'
    reference=json.loads((ROOT/'hl_mask_reader_summary.json').read_bytes())
    old=json.loads(out.read_bytes()) if not a.directory else None
    if old:
        for name,digest in old['source_sha256'].items():
            if sha((ROOT/name).read_bytes())!=digest:raise ValueError(('source changed',name))
    def baseline_file(name):
        item=next(v for v in reference['evidence'] if v['file']==name)
        packed=(ROOT/item['directory']/name).read_bytes();raw=gzip.decompress(packed)
        if sha(packed)!=item['sha256'] or sha(raw)!=item['uncompressed_sha256']:raise ValueError('reference archive changed')
        return raw
    measured=json.loads((ROOT/'hl_mask_reader_cpu.json').read_bytes())
    queue_raw=baseline_file('hl_cpu.json.gz');queue=json.loads(queue_raw)
    if not queue['complete'] or queue['source_sha256']!=sha((ROOT/'replay_queue_calls.py').read_bytes()):
        raise ValueError('incomplete queue replay or changed replay source')
    frame_cpu=json.loads((ROOT/'inline_huffman_patches_cpu.json').read_bytes())
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='074e1e7',implemented=False,
        stream_delta_bytes=0,player_cpu_delta_tstates=0,actual_new_playback_measured=False,mask_archive_format='u16 length, u8 AY writes, mask bytes',
        queue_cpu_sha256=sha(queue_raw),
        source_sha256={n:sha((ROOT/n).read_bytes()) for n in ('profile_zero_mask_history.py','compiled_masks_z80.py',
            'bulk_frame_stream.py','benchmark_bank_local_zx0.py','probe_motion_metadata.py','probe_motion_entropy.py',
            'profile_integrated_timing.py','replay_queue_calls.py','direct_slot_input_z80.py','slot_queue_z80.py',
            'incremental_zx0.py','bank_local_zx0.py',
            'hl_mask_reader_cpu.json','hl_mask_reader_summary.json','inline_huffman_patches_cpu.json')},
        assumptions=['Previous mask state unknown at every independent disk start.',
            'Only 60 lower groups cover the 480 bitmap/attribute mask bytes.',
            'Removable write component: 8 LD (DE),A at 7 T = 56 T/group; retains cursor/dispatch and excludes history checks.',
            'Whole-loop optimistic ceiling: 153 T/group, before all replacement cursor/dispatch/history costs.',
            'Neither ceiling includes ULA, IRQ, ROM or disk. No predicted elapsed speedup.',
            'Enqueue time outside nested prefetch still includes copying, IRQ, ULA and wait glue; it is not pure idle time.',
            'Per-packet elapsed work contains AY backpressure and work preparing later packets; do not treat its mean as required CPU per frame.'],volumes=[],evidence=[])
    if a.directory:archive.mkdir(exist_ok=True)
    for part in (1,2,3):
        meta_raw=baseline_file(f'hl_part{part:02}.metadata.json.gz');m=json.loads(meta_raw)
        trace_raw=baseline_file(f'hl_part{part:02}.json.gz');trace=json.loads(trace_raw)
        if sha(meta_raw)!=trace['integrated_bootstrap_metadata_sha256']:raise ValueError('wrong reference metadata')
        qcpu=queue['volumes'][part-1]
        if qcpu['trace_report_sha256']!=sha(trace_raw) or not qcpu['complete']:raise ValueError('queue CPU differs')
        audio=enqueue_spans(trace,qcpu)
        profile=analyze(trace,m,frame_cpu['volumes'][part-1]);name=f'part{part:02}.masks.gz'
        if a.directory:
            built,stream,blocks=disk_blocks(a.directory,part)
            if (built['trd_sha256']!=m['trd_sha256'] or
                sha((a.directory/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes())!=sha(meta_raw)):
                raise ValueError('wrong fresh image')
            packets=Reader(b''.join(raw for _,raw in blocks));data=bytearray()
            for _ in range(m['frames']):
                _,d=read_packet(packets,stored_guards=False);pos=sum(map(len,d['ticks']))+8+192
                encoded=d['payload'][pos:pos+d['mask_bytes']]
                data+=struct.pack('<HB',len(encoded),sum(tick[0] for tick in d['ticks']))+encoded
            packets.end();stream_sha=sha(stream);packed=gzip.compress(bytes(data),mtime=0);(archive/name).write_bytes(packed)
        else:
            entry=next(v for v in old['evidence'] if v['file']==name);packed=(archive/name).read_bytes();data=gzip.decompress(packed)
            if sha(packed)!=entry['sha256'] or sha(data)!=entry['uncompressed_sha256']:raise ValueError('saved masks changed')
            stream_sha=entry['stream_sha256']
        data=bytes(data);report['evidence'].append(dict(file=name,sha256=sha(packed),uncompressed_sha256=sha(data),
            stream_sha256=stream_sha,metadata_sha256=sha(meta_raw),trace_report_sha256=sha(trace_raw)))
        if stream_sha!=reference['volumes'][part-1]['hl']['stream_sha256']:raise ValueError('stream differs')
        r=Reader(data);prev_flags=prev_expanded=None;rows=[];hist=Counter()
        for local in range(m['frames']):
            size=r.u16();writes=r.take(1)[0];encoded=r.take(size);flags,expanded=lower_flags(encoded);f=profile['frames'][local]
            ticks=expected_tstates(encoded,hl_flags=True)
            if ticks!=measured['volumes'][part-1]['frames'][local]['hl_tstates']:raise ValueError('different masks from CPU profile')
            zero=[v==0 for v in flags]
            repeated=[v==0 and prev_flags is not None and prev_flags[i]==0 for i,v in enumerate(flags)]
            # An explicit memory simulation checks that retaining prior zeros
            # still gives the exact complete output; other groups are written.
            simulated=bytearray(prev_expanded if prev_expanded is not None else bytes([0xa5])*480)
            for i in range(60):
                if not repeated[i]:simulated[i*8:i*8+8]=expanded[i*8:i*8+8]
            if bytes(simulated)!=expanded:raise ValueError('history skip changes mask bytes')
            chunks={}
            for width in (4,8):
                groups=[list(range(i,min(i+width,60))) for i in range(0,60,width)]
                stable=[g for g in groups if all(repeated[i] for i in g)]
                chunks[str(width)]=dict(zero_chunks=sum(all(zero[i] for i in g) for g in groups),
                    repeated_zero_chunks=len(stable),repeated_zero_groups=sum(map(len,stable)))
            repeat=sum(repeated);hist[repeat]+=1
            span=audio[local];elapsed=span['end']-span['start']
            step_elapsed=sum(c['elapsed_tstates'] for c in span['steps'])
            if step_elapsed>elapsed:raise ValueError('negative enqueue residual')
            row=dict(frame=m['frame_start']+local,local_frame=local,zero_groups=sum(zero),
                repeated_zero_groups=repeat,newly_zero_groups=sum(zero)-repeat,
                upper_zero_bytes=sum(v==0 for v in encoded[:8]),chunked=chunks,
                removable_write_tstates=56*repeat,whole_group_ceiling_tstates=153*repeat,
                metadata_cpu_tstates=ticks,work_elapsed_tstates=f['work_elapsed'],
                over_six_fields=f['work_elapsed']>PERIOD,late_fields=f['late_fields'],
                stages={k:v['elapsed'] for k,v in f['stages'].items()},
                enqueue=dict(elapsed=elapsed,full_hits=span['full_hits'],prefetch_elapsed=step_elapsed,
                    outside_prefetch_elapsed=elapsed-step_elapsed,ordinary_enqueue_cpu=1705+42*writes,
                    prefetch_busy_elapsed=sum(c['elapsed_tstates'] for c in span['steps'] if c['return_a']),
                    prefetch_sectors=sum(c['sectors'] for c in span['steps']),
                    prefetch_cpu=sum(c['cpu_tstates'] for c in span['steps'])))
            rows.append(row);prev_flags,prev_expanded=flags,expanded
        r.end()
        aggregates={}
        for scope,selected in (('all',rows),('over_budget',[v for v in rows if v['over_six_fields']]),
                               ('within_budget',[v for v in rows if not v['over_six_fields']])):
            aggregates[scope]=dict(frames=len(selected),
                **{k:stats([v[k] for v in selected]) for k in ('zero_groups','repeated_zero_groups','newly_zero_groups',
                    'removable_write_tstates','whole_group_ceiling_tstates','metadata_cpu_tstates','work_elapsed_tstates')},
                chunked={width:{k:sum(v['chunked'][width][k] for v in selected) for k in
                    ('zero_chunks','repeated_zero_chunks','repeated_zero_groups')} for width in ('4','8')},
                enqueue={k:stats([v['enqueue'][k] for v in selected]) for k in
                    ('elapsed','outside_prefetch_elapsed','ordinary_enqueue_cpu','prefetch_elapsed','prefetch_cpu')})
        # Reconstructing the packet without this metadata stage is a loose
        # bound, not a schedulability proof: work spans and async stages differ.
        without_metadata=stats([f['work_elapsed']-f['stages']['metadata']['elapsed'] for f in profile['frames']])
        first_empty=min(trace['audio_underrun_tstates'],default=None)
        full_events=[e for e in trace['audio_enqueue_events'] if e['kind']=='enqueue_full']
        first_full=min((e['tstate'] for e in full_events),default=None)
        starvation=None
        if first_empty is not None:
            stages=[dict(frame=f['local_frame'],stage=stage,**span) for f in profile['frames']
                for stage,span in f['stages'].items() if span['start']<=first_empty<span['end']]
            calls=[c for c in qcpu['calls'] if c['start']<=first_empty<c['end']]
            if len(stages)>1 or len(calls)>1:raise ValueError('overlapping foreground intervals')
            frame=stages[0]['frame'] if stages else None
            entries=[e for e in trace['pipeline_events'] if e['kind']=='packet_start']
            starvation=dict(tstate=first_empty,stage=stages[0] if stages else None,queue_call=calls[0] if calls else None,
                packet_entry=entries[frame] if frame is not None else None,
                previous_publication=next((p for p in reversed(trace['publications']) if p['tstate']<first_empty),None),
                full_branch_events_before=sum(e['tstate']<first_empty for e in full_events),
                first_full_branch_tstate=first_full,
                first_full_minus_empty_fields=(first_full-first_empty)/FIELD if first_full is not None else None)
        report['volumes'].append(dict(part=part,frames=rows,aggregates=aggregates,
            repeated_group_histogram=dict(sorted(hist.items())),all_history_simulated_bytes_exact=True,
            first_frame_repeated_zero_groups=rows[0]['repeated_zero_groups'],
            baseline_work_excluding_metadata_elapsed=without_metadata,
            first_late_local_frame=next((v['local_frame'] for v in rows if v['late_fields']),None),
            first_audio_underrun_tstate=first_empty,first_starvation=starvation,
            work_minus_enqueue_outside_prefetch=stats([v['work_elapsed_tstates']-v['enqueue']['outside_prefetch_elapsed'] for v in rows]),
            largest_work_frames=sorted(rows,key=lambda v:v['work_elapsed_tstates'],reverse=True)[:12]))
    report.update(complete=True,frames=sum(len(v['frames']) for v in report['volumes']),
        pixel_or_audio_changes=0,new_z80_code_bytes=0,new_runtime_state_bytes=0)
    out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    for v in report['volumes']:
        print(json.dumps(dict(part=v['part'],aggregates=v['aggregates'],
            work_without_metadata=v['baseline_work_excluding_metadata_elapsed']),indent=2),flush=True)


if __name__=='__main__':main()
