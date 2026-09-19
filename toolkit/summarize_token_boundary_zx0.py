"""Compare whole-stream decoder measurements and a matched clock prefix.

Standalone fixed-quota decoder time is not total player delivery time.
Clock reports are partial and use an ideal compressed-byte producer.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from assess_frame_jitter import assess
from ay_interrupt import TSTATES as AY_TSTATES
import frame_clock_z80
from benchmark_banked_zx0 import Harness
from probe_lossless_layouts import sha
from zx0_speed import Token,encode


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--decoders',type=Path,nargs=3,required=True,metavar=('OLD','FIRST','FAST'))
    p.add_argument('--clocks',type=Path,nargs=3,required=True,metavar=('OLD','FIRST','FAST'))
    p.add_argument('--latency',type=Path,nargs='*',default=[])
    p.add_argument('--integrated',type=Path,nargs=3,metavar=('ORIGINAL','STATIC_PROJECTION','NEW'),
        help='Compare a complete manual-IRQ run against the old run plus verified output/reconstruction deltas')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); read=lambda path:json.loads(path.read_text(encoding='utf-8'))
    decoders=list(map(read,args.decoders)); clocks=list(map(read,args.clocks))
    if (not all(r['complete'] for r in decoders)
            or len({r['input_sha256'] for r in decoders})!=1
            or any(r['raw_sha256']!=decoders[0]['input_sha256'] for r in clocks)
            or len({r['states_sha256'] for r in clocks})!=1):
        raise ValueError('complete matching decoder reports and matching clock inputs required')
    matched=min(len(r['frames']) for r in clocks); reference=Counter(); trials=[]
    for index,(path,decoder,clock) in enumerate(zip(args.decoders,decoders,clocks)):
        stages=Counter()
        for row in clock['frames'][:matched]: stages.update(row['stages'])
        if not index: reference=stages.copy()
        trial=dict(decoder_report=path.name,decoder_sha256=sha(bytes.fromhex(decoder['code_hex'])),
            decoder_summary=decoder['summary'],
            decoder_delta_vs_exact=decoder['summary']['total_tstates']-decoders[0]['summary']['total_tstates'],
            matched_clock_frames=matched,matched_stages=dict(stages),
            matched_stage_delta={s:stages[s]-reference[s] for s in stages.keys()|reference.keys()},
            matched_foreground_delta=sum(stages.values())-sum(reference.values()),
            matched_timing=assess(clock['publications'][:matched]),
            full_recording_timing=assess(clock['publications']),failure=clock.get('failure'),
            clock_complete=clock['complete'])
        trials.append(trial)
    blocks=[]
    for old,new in zip(decoders[0]['blocks'],decoders[2]['blocks']):
        if (old['index']!=new['index'] or old['ring_start']!=new['ring_start']
                or old['compressed_bytes']!=new['compressed_bytes'] or old['decoded_bytes']!=new['decoded_bytes']):
            raise ValueError('decoder block coverage differs')
        blocks.append(dict(index=old['index'],old_tstates=old['tstates'],new_tstates=new['tstates'],
            delta_tstates=new['tstates']-old['tstates']))
    latency=[]
    _,clock_labels,clock_listing=frame_clock_z80.build(
        dict(next_frame=0,publish_bridge=0),dict(audio_start=0,elapsed_fields=0),
        zx0=decoders[2]['labels'],lookahead=True)
    # Sum both alternatives of ahead_fits conservatively. The decoder's
    # external CALL is already included in the separate latency bound.
    loop_rows=[r for r in clock_listing if r['instruction']!='CALL slice_until' and (
        clock_labels['wait_publish']<=r['address']<clock_labels['wait_field']
        or clock_labels['ahead']<=r['address']<clock_labels['ahead_done'])]
    loop_bound=sum(r['tstates'] for r in loop_rows)
    max_irq=(AY_TSTATES['previous_fast_irq']+AY_TSTATES['irq_call']+AY_TSTATES['changed_base']
        +11*AY_TSTATES['per_register']+AY_TSTATES['last_tick_extra'])
    for path in args.latency:
        data=read(path)
        if (not data['complete'] or data['input_sha256']!=decoders[0]['input_sha256']
                or data['decoder_sha256']!=trials[2]['decoder_sha256']):
            raise ValueError('incomplete/mismatched latency report')
        quantum=data['summary']['worst']['bound']['bound_tstates']
        latency.append(dict(report=path.name,first_payload_ring_offset=data['blocks'][0]['ring_start'],
            copy_paths=data['copy_paths'],summary=data['summary'],
            cpu_only_loop_bound=quantum+loop_bound+max_irq,
            margin_to_70908=70908-quantum-loop_bound-max_irq))
    # Demonstrate why the bound must not be reused for another movie.
    example=b'a'*8192
    h=Harness(fast_literal=True,fast_refill=True,token_boundaries=True)
    h.begin(encode(example,[Token(0,1),Token(1,8191,1)]),example)
    h.run(1); long_copy_tstates=h.run(2); h.finish()
    result=dict(scope=__doc__,complete=True,release=False,baseline_commit='81779ce',
        input_sha256=decoders[0]['input_sha256'],states_sha256=clocks[0]['states_sha256'],
        stream_extra_bytes=0,stream_extra_sectors=0,extra_buffer_bytes=0,
        code_delta_bytes=decoders[2]['summary']['code_bytes']-decoders[0]['summary']['code_bytes'],
        trials=trials,blocks=blocks,slower_blocks=sum(r['delta_tstates']>0 for r in blocks),
        latency=latency,clock_loop_overhead_bound_tstates=loop_bound,
        max_single_ay_irq_tstates=max_irq,clock_loop_instruction_listing=loop_rows,
        synthetic_long_match=dict(requested=2,produced=h.cpu.produced,resume_tstates=long_copy_tstates,
            exceeds_one_irq_field=long_copy_tstates>70908,
            reason='A valid 8191-byte match proves the movie-specific bound is not universal.'),
        full_integrated_run_verified=False,cadence_verified=False,disk_delivery_verified=False)
    if args.integrated:
        original,static,new=map(read,args.integrated)
        if (not all(r['complete'] for r in (original,static,new)) or new['cadence_requested']
                or not new['token_boundaries'] or not new['static_stripes'] or not new['black_borders']
                or not original['raw_sha256']==static['raw_sha256']==new['raw_sha256']==result['input_sha256']
                or not original['states_sha256']==static['states_sha256']==new['states_sha256']==result['states_sha256']
                or len(original['frames'])!=len(new['frames']) or len(new['frames'])!=len(static['frame_projection'])):
            raise ValueError('complete matching manual-IRQ reports/projection required')
        before,after=Counter(),Counter(); frame_deltas=[]
        for old,projection,current in zip(original['frames'],static['frame_projection'],new['frames']):
            adjusted=dict(old['stages'])
            adjusted['reconstruct']+=projection['reconstruction_delta']
            adjusted['output']=projection['output_tstates']
            for phase in ('packet','audio','metadata','handoff','reconstruct','output'):
                if adjusted[phase]!=current['stages'][phase]:
                    raise AssertionError('unchanged player stage differs')
            before.update(adjusted); after.update(current['stages'])
            frame_deltas.append(dict(index=current['index'],baseline_tstates=sum(adjusted.values()),
                new_tstates=current['tstates'],delta_tstates=current['tstates']-sum(adjusted.values())))
        if sum(before.values())!=static['projection']['foreground_after_black_borders_and_static_stripes']:
            raise AssertionError('projected baseline total differs')
        result['full_integrated_run_verified']=True
        result['integrated']=dict(scope='Complete Z80/RAM/data run with six manually called AY ISR per frame, not cadence.',
            report=args.integrated[2].name,summary=new['summary'],baseline_is_projection=True,
            baseline_tstates=sum(before.values()),new_tstates=sum(after.values()),
            delta_tstates=sum(after.values())-sum(before.values()),
            stage_delta={s:after[s]-before[s] for s in before.keys()|after.keys()},
            frame_deltas=frame_deltas)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for trial in trials:
        print(json.dumps(dict(decoder=trial['decoder_report'],total=trial['decoder_summary']['total_tstates'],
            matched_frames=matched,matched_foreground_delta=trial['matched_foreground_delta'],
            matched_late=trial['matched_timing']['late_publications'],
            matched_max_phase=trial['matched_timing']['max_phase_tstates'],failure=trial['failure'])))
    print('Slower blocks:',result['slower_blocks'])
    if 'integrated' in result: print(json.dumps({k:v for k,v in result['integrated'].items() if k!='frame_deltas'}))


if __name__=='__main__': main()
