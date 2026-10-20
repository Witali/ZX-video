"""Test-only short LZSA2 kernels against the current public Expanded decoder.

The exact per-token equations are asserted for every complete replay. Input,
output/history, AF' phase, caller ABI, source cursor and SMC writes are checked
by the protected native harness; no public generator or default is changed.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

from measure_long_copy import ROOT,samples,sha
from measure_full_token_dispatch import directed_tokens
from native_block import execute
from lzsa.wide import build as public
from wide_short_profile import build


def model_delta(counts,options):
    shared=options.get('shared_literals',False)
    selected=set(options.get('short_lengths',range(2,9)))
    repeats=set(options.get('repeat_lengths',()))
    skipped=set(options.get('skip_tokens',()))
    result=0
    for token,count in counts.items():
        cls,n=token>>5,(token&7)+2
        key=token&0xe7 if shared else token
        if shared and (token>>3)&3:result+=10*count
        if key not in skipped:
            if cls!=7 and n in selected:result+=(4-5*n)*count
            elif cls==7 and n in repeats:result+=(16-5*n)*count
    return result


def layout(profile):
    regions,labels,metadata=profile
    return dict(code_bytes=metadata['code_bytes'],service_memory_bytes=metadata['service_memory_bytes'],
        alignment_padding=metadata['alignment_padding'],budget_valid=metadata.get('budget_valid',True),
        caller_stack_bytes=metadata['caller_stack_bytes'],table_bytes=metadata['table_bytes'],
        embedded_mutable_bytes=metadata['service_memory']['embedded_mutable_bytes'],
        state_bytes=metadata['state_bytes'],scratch_bytes=0,internal_buffer_bytes=0,
        regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in regions])


def micro(profile,token):
    target='token-'+f'{token:02x}'+'-empty'
    _,payload,raw,_=next(row for row in directed_tokens() if row[0]==target)
    regions,labels,metadata=profile
    name='short_ready_'+str(token)
    if name in labels:start=labels[name]
    elif token>>5==7:start=labels['token_'+str(token)]+1
    else:
        origin,blob=regions[0]
        low=labels['token_'+str(token)]-origin
        high=min([pc-origin for key,pc in labels.items() if key.startswith('token_') and key[6:].isdigit() and pc>origin+low]+[len(blob)])
        pattern=bytes.fromhex('ed43')+labels['offset'].to_bytes(2,'little')
        found=blob.find(pattern,low,high)
        assert found>=0
        start=origin+found
    tick=None;observed=[]
    def begin(m):
        nonlocal tick
        tick=m.ticks_to_stop
    def end(m):
        nonlocal tick
        if tick is not None:observed.append(tick-m.ticks_to_stop);tick=None
    execute(profile,payload,raw,watch={start:begin,labels['ReadToken']:end})
    assert len(observed)==1
    return observed[0]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output=args.output.resolve()
    base=public(core=0x8000,core_limit=0xc000)
    assert base[2]['code_bytes']==6998
    corpus=[(n,p,r,None) for n,p,r in samples()]
    directed=list(directed_tokens())
    cases=corpus+directed
    assert len(corpus)==95 and len(directed)==580
    baseline={};real_counts=Counter()
    for name,payload,raw,wanted in cases:
        counts=Counter()
        def hit(value):return lambda machine:counts.update((value,))
        watches={base[1]['token_'+str(v)]:hit(v) for v in range(256)}
        old=execute(base,payload,raw,watch=watches)
        if wanted is not None:assert counts[wanted]
        baseline[name]=dict(tstates=old['tstates'],counts=counts,
            payload_sha256=sha(payload),raw_sha256=sha(raw),
            compressed_input_bytes=len(payload),output_history_bytes=len(raw))
        if name.startswith('real-'):real_counts.update(counts)
    real_base=sum(v['tstates'] for k,v in baseline.items() if k.startswith('real-'))
    assert real_base==15623953
    # Every new-offset n=2 token occurs in the real corpus. Omit the kernel
    # with the smallest complete-real CPU loss, rather than assuming an unused
    # token. Any one omitted short kernel frees at least8 bytes for alignment.
    cold=min((t for t in range(256) if t>>5<7 and t&7<7),
             key=lambda t:(real_counts[t]*(5*((t&7)+2)-4),-(4+2*((t&7)+2)),t))
    variants=[
        ('shared-new-all',dict(shared_literals=True)),
        ('new-2',dict(short_lengths=(2,))),
        ('new-2to4',dict(short_lengths=(2,3,4))),
        ('new-3to8',dict(short_lengths=tuple(range(3,9)))),
        ('new-all',{}),
        ('new-all-cold-fit',dict(skip_tokens=(cold,))),
        ('shared-new-all-repeat-4to8',dict(shared_literals=True,repeat_lengths=tuple(range(4,9)))),
    ]
    full=dict(date='2026-10-20',complete=False,release=False,public_changed=False,
        scope='Raw-only private short kernels; same public Expanded baseline and complete inputs.',
        baseline=layout(base),baseline_real_tstates=real_base,
        corpus_cases=len(corpus),directed_cases=len(directed),
        baseline_cases=baseline,real_token_frequencies=dict(sorted(real_counts.items())),
        omitted_cold_token=cold,omitted_cold_token_real_count=real_counts[cold],profiles={})
    for name,options in variants:
        candidate=build(**options)
        aligned=build(core=0x9000,**options)
        rejection=None
        try:unaligned=build(core=0x9003,**options)
        except ValueError as error:
            rejection=str(error)
            unaligned=build(core=0x9003,allow_oversize=True,**options)
            assert not unaligned[2]['budget_valid']
        rows=[]
        for case,payload,raw,wanted in cases:
            counts=Counter()
            def hit(value):return lambda machine:counts.update((value,))
            watches={candidate[1]['token_'+str(v)]:hit(v) for v in range(256)}
            new=execute(candidate,payload,raw,watch=watches)
            irq=execute(candidate,payload,raw,interrupts=True)
            moved=execute(aligned,payload,raw)
            shifted=execute(unaligned,payload,raw)
            old=baseline[case]
            assert counts==old['counts']
            expected=model_delta(counts,options)
            assert new['tstates']-old['tstates']==expected,(name,case,expected,new['tstates']-old['tstates'])
            assert moved['tstates']==shifted['tstates']==new['tstates']
            assert new['stack_bytes']<=6 and moved['stack_bytes']<=6 and shifted['stack_bytes']<=6
            if wanted is not None:assert counts[wanted]
            rows.append(dict(case=case,baseline_tstates=old['tstates'],candidate_tstates=new['tstates'],
                delta_tstates=expected,formula_exact=True,stack_bytes=new['stack_bytes'],
                injected_interrupts=irq['injected_interrupts'],exact=True,relocated_exact=True))
        real=[r for r in rows if r['case'].startswith('real-')]
        actual=sum(r['candidate_tstates'] for r in real)
        summary=dict(cases=len(rows),real_blocks=len(real),real_baseline_tstates=real_base,
            real_candidate_tstates=actual,real_delta_tstates=actual-real_base,
            real_percent_saved=100*(real_base-actual)/real_base,
            slower_blocks=[r['case'] for r in rows if r['delta_tstates']>0],
            real_slower_blocks=[r['case'] for r in real if r['delta_tstates']>0],
            largest_delta_tstates=max(r['delta_tstates'] for r in rows),
            injected_interrupts=sum(r['injected_interrupts'] for r in rows),
            maximum_stack_bytes=max(r['stack_bytes'] for r in rows))
        micro_rows=[]
        for n in range(2,9):
            token=0x40+n-2
            before=micro(base,token);after=micro(candidate,token)
            assert before==21*n+76
            selected=n in set(options.get('short_lengths',range(2,9))) and token not in options.get('skip_tokens',())
            expected=16*n+80 if selected else before
            assert after==expected
            micro_rows.append(dict(class_='new-offset-9bit',length=n,
                endpoint='LD(offset),BC fetch through next ReadToken fetch',
                baseline_tstates=before,candidate_tstates=after,delta_tstates=after-before))
        for n in options.get('repeat_lengths',()):
            token=0xe0+n-2
            before=micro(base,token);after=micro(candidate,token)
            assert before==21*n+49 and after==16*n+65
            micro_rows.append(dict(class_='repeat-offset',length=n,
                endpoint='LD C,n fetch through next ReadToken fetch',
                baseline_tstates=before,candidate_tstates=after,delta_tstates=after-before))
        full['profiles'][name]=dict(options=options,candidate=layout(candidate),aligned_relocated=layout(aligned),
            unaligned_relocated=layout(unaligned),unaligned_public_rejection=rejection,
            summary=summary,micro_paths=micro_rows,blocks=rows)
        print(name,json.dumps(dict(code=candidate[2]['code_bytes'],service=candidate[2]['service_memory_bytes'],
            real_tstates=actual,real_delta=actual-real_base,slower=len(summary['slower_blocks']),
            real_slower=len(summary['real_slower_blocks']),cold=cold)),flush=True)
    full['source_sha256_lf']={str(p.relative_to(ROOT)).replace('\\','/'):sha(p.read_bytes().replace(b'\r\n',b'\n'))
        for p in (ROOT/'libraries/lzsa/src/lzsa/wide.py',ROOT/'libraries/tests/wide_short_profile.py',
                  ROOT/'libraries/tests/native_block.py',Path(__file__))}
    full['limitations']=[
        'Raw-only: no new coroutine, guarded producer or physical delivery claim.',
        'Full new-all exceeds cap by1byte at9003; its oversize relocation is correctness-only and explicitly invalid for public use.',
        'Code+table+alignment+six caller stack bytes counted; source/output/history and actual IRQ headroom are separate.',
        'The full guarded reference service currently9881bytes leaves119bytes; consumer-only headroom is not producer-inclusive headroom.']
    full['complete']=True
    args.output.parent.mkdir(parents=True,exist_ok=True)
    archive=args.output.with_name(args.output.stem+'_full.json.gz')
    archive.write_bytes(gzip.compress((json.dumps(full,indent=2)+'\n').encode('utf-8'),mtime=0))
    overview={k:v for k,v in full.items() if k not in ('baseline_cases','profiles')}
    overview['profiles']={k:{a:b for a,b in v.items() if a!='blocks'} for k,v in full['profiles'].items()}
    overview['full_evidence']=dict(path=str(archive.relative_to(ROOT)).replace('\\','/'),sha256=sha(archive.read_bytes()))
    args.output.write_text(json.dumps(overview,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
