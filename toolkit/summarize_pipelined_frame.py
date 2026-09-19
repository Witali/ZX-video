"""Compare recorded IM2 pipeline timing without equating different prefixes.

CPU instruction-table costs and ideal-clock publications are separate from
physical disk/ULA timing. Failure recordings remain incomplete releases.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from assess_frame_jitter import assess
from probe_lossless_layouts import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',type=Path,required=True)
    p.add_argument('--after',type=Path,required=True)
    p.add_argument('--full-cpu',type=Path,required=True)
    p.add_argument('--progress',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    reports=[json.loads(path.read_text(encoding='utf-8')) for path in (args.before,args.after,args.full_cpu,args.progress)]
    old,new,full,bar=reports
    if len({r['raw_sha256'] for r in reports})!=1 or len({r['states_sha256'] for r in reports})!=1:
        raise ValueError('different input frames/stream')
    common=min(len(old['publications']),len(new['publications']))
    checked=new['checked']; stages=new['foreground_stages']
    # Failure is inside input acquisition for the next packet, so reconstruction
    # and output for the verified prefix have both completed, with no partial
    # such stage hidden in the cumulative sum.
    if new['failure']['pc'] not in range(0x7c00,new['decoder_labels']['state']):
        raise ValueError('update stage comparison for a failure outside ZX0')
    if checked['compact']!=checked['native']: raise ValueError('different completed stages')
    n=checked['native']; previous=Counter()
    for row in full['frames'][:n]: previous.update(row['stages'])
    if stages['reconstruct']!=previous['reconstruct'] or stages['output']!=previous['output']+10*n:
        raise AssertionError('reconstruction/output timing differs from the instruction delta')
    pubs=new['publications']; phase=[r['tstates']-r['interrupt_entry_tstates'] for r in pubs]
    if set(phase)!={326}: raise AssertionError('video publication moved relative to IRQ entry')
    histogram=Counter()
    for row in new['instruction_histogram']: histogram[row['address'],row['tstates']]+=row['count']
    page=new['video_labels']['atomic_page']
    page_calls=sum(count for (address,_),count in histogram.items() if address==page)
    if stages['paging']!=88*page_calls: raise AssertionError('atomic paging sum differs')
    if not bar['requested_scope_complete'] or bar['complete'] or bar['checked']!=dict.fromkeys(checked,128):
        raise ValueError('expected the complete 128-frame virtual volume')
    if bar['played_ay_ticks']!=768 or bar['timing']['late_frames']: raise AssertionError('virtual volume failed')
    # The scheduler calls tick directly, after the IRQ, with bank 7 already in
    # place. The old bridge's 27 T are replaced by a single 17-T CALL.
    expected_progress=50*128+16393
    if bar['foreground_stages']['progress']!=expected_progress: raise AssertionError('progress sum differs')
    costs={
        'atomic_page':dict(previous_out=12,new_call_plus_routine=105,delta=93,routine=88),
        'video_irq_disabled':dict(previous=0,new=75,delta=75),
        'video_irq_no_ready':dict(previous=0,new=102,delta=102),
        'video_irq_before_deadline':dict(previous=0,new=196,delta=196),
        'video_irq_publish':dict(previous=0,new=495,delta=495),
        'split_wrapper':dict(previous_extra_ret=0,new_extra_ret=10,delta=10),
        'native_output':dict(previous=previous['output'],new=stages['output'],delta=10*n,
            note='Only the two 17-T CALL sites replace 12-T OUTs; helper time is separate.'),
        'reconstruct':dict(previous=previous['reconstruct'],new=stages['reconstruct'],delta=0),
        'foreground_frame_glue':dict(delta=361,
            derivation='prepare bridge +173; draw bridge +172; wrapper +10; output with helpers +186; old publish -180',
            excludes='scheduler loops, ZX0 paging, video IRQ, progress, outer host entry CALLs'),
        'progress_128':dict(previous_tick_and_bridge=77*128+16393,new_tick_and_call=67*128+16393,
            delta=-10*128,excludes='reset and scheduler wait/return common to both bar/no-bar')}
    # Show the complete old-data CPU budget for the burst that defeats the new
    # queue, not just the mean of the light prefix.
    windows=[]
    for first,last in ((395,421),(400,431),(408,431),(0,len(full['frames']))):
        rows=full['frames'][first:last]; total=Counter()
        for row in rows: total.update(row['stages'])
        windows.append(dict(first_frame=first,last_frame_exclusive=last,frames=len(rows),
            mean_tstates=sum(r['tstates'] for r in rows)/len(rows),stages=dict(total),
            frames_above_425448=sum(r['tstates']>425448 for r in rows),
            note='Previous full manual-IRQ data run: no scheduled lookahead/IRQ/ULA/disk; not a pipeline projection.'))
    result=dict(scope=__doc__,complete=True,release=False,
        inputs=[dict(file=path.name,sha256=sha(path.read_bytes())) for path in
            (args.before,args.after,args.full_cpu,args.progress)],
        common_publications=common,before_common=assess(old['publications'][:common]),
        after_common=assess(pubs[:common]),after_recording=assess(pubs),
        failure=new['failure'],checked=checked,publication_offset_from_irq_entry_tstates=326,
        foreground_paging_calls=page_calls,atomic_paging_tstates=stages['paging'],costs=costs,
        cpu_windows=windows,progress_virtual_volume=dict(frames=128,ay_ticks=768,
            audit=assess(bar['publications']),final_drain=bar['drain']),
        decision='Keep the optional IRQ pipeline; heavy-burst CPU/AY underflow still blocks release. '
            'Three real TRDs, final loader placement, disk delivery and ULA remain unverified.')
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('common_publications','before_common','after_common','after_recording','costs','cpu_windows')},indent=2))


if __name__=='__main__': main()
