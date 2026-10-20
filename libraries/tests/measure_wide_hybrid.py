"""Measured private raw LZSA2 sharing frontier; standard bytes and all token forms."""
import argparse,gzip,json
from collections import Counter
from pathlib import Path
from measure_long_copy import ROOT,samples,sha
from measure_full_token_dispatch import directed_tokens
from native_block import execute
from lzsa.wide import build as public
from wide_hybrid_profile import build


def profiled(profile,case):
    counter=Counter()
    def hit(value):
        def callback(machine):counter[value]+=1
        return callback
    watches={profile[1]['token_'+str(v)]:hit(v) for v in range(256)}
    name,payload,raw=case
    result=execute(profile,payload,raw,watch=watches)
    return result,counter


def ranking(counts):
    return {base:tuple(sorted(range(4),key=lambda ll:(-counts[base|(ll<<3)],ll)))
        for base in range(256) if base&24==0}


def grouped(rank,number):
    # The hottest number-1 forms are singletons; the remainder shares a body
    # whose next-hottest form falls through. Every old hot fallthrough stays
    # a fallthrough as the body count grows, making these nested partitions.
    return tuple((v,) for v in rank[:number-1])+(tuple(rank[number-1:]),)


def choose(counts,rank,weights,budget):
    states={0:(0,())};bases=sorted(weights)
    for base in bases:
        updated={}
        values=[counts[base|(v<<3)] for v in rank[base]]
        for cost,(benefit,choice) in states.items():
            for number in range(1,5):
                total=cost+(number-1)*weights[base]
                if total>budget:continue
                candidate=(benefit+sum(values[:number]),choice+(number,))
                if total not in updated or candidate>updated[total]:updated[total]=candidate
        states=updated
    cost,(benefit,selection)=max(states.items(),key=lambda pair:(pair[1][0],-pair[0],pair[1][1]))
    return {base:grouped(rank[base],n) for base,n in zip(bases,selection)},cost,benefit


def definition(profile):
    metadata=profile[2]
    return dict(code_bytes=metadata['code_bytes'],table_bytes=metadata['table_bytes'],alignment_padding=metadata['alignment_padding'],
        required_caller_stack_bytes=6,service_memory_bytes=metadata['code_bytes']+6,
        test_irq_extra_stack_bytes=6,test_irq_code_bytes=13,service_memory_with_test_irq_bytes=metadata['code_bytes']+25,
        embedded_mutable_bytes=2,external_state_bytes=0,other_tables_padding_scratch_internal_buffers_bytes=0,
        regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]])


def audit_hits(path):
    report=json.loads(path.read_text(encoding='utf-8'))
    expanded=public();shared=public(shared_literals=True)
    cases=list(samples())+[(n,p,r) for n,p,r,value in directed_tokens()]
    base=[]
    for case in cases:
        result,counts=profiled(expanded,case)
        oldshared=execute(shared,case[1],case[2])
        shared_extra=10*sum(n for token,n in counts.items() if token&24)
        assert oldshared['tstates']==result['tstates']+shared_extra
        base.append(dict(case=case[0],expanded_tstates=result['tstates'],shared_tstates=oldshared['tstates'],token_counts=dict(counts)))
    assert len(base)==675
    for item in report['profiles'].values():
        if not item.get('finalist'):continue
        after={r['case']:r for r in item['full_blocks']+item['directed_blocks']}
        hits=set(item['shared_hit_tokens']);short=set(item['options'].get('short_lengths',()))
        repeat=set(item['options'].get('repeat_lengths',()))
        for before in base:
            saving=0
            for token,count in before['token_counts'].items():
                n=(token&7)+2
                saving+=count*((5*n-4) if token>>5<7 and n in short else ((5*n-16) if token>>5==7 and n in repeat else 0))
            hit_count=sum(n for token,n in before['token_counts'].items() if token in hits)
            row=after[before['case']]
            assert row['candidate_tstates']==before['expanded_tstates']-saving+10*hit_count
            row.update(expanded_tstates=before['expanded_tstates'],shared_tstates=before['shared_tstates'],
                short_kernel_saving_tstates=saving,shared_hit_count=hit_count,shared_hit_tstates=10*hit_count,
                delta_from_expanded_tstates=row['candidate_tstates']-before['expanded_tstates'],
                delta_from_shared_tstates=row['candidate_tstates']-before['shared_tstates'],exact_hit_model=True)
        allrows=list(after.values())
        item['all_case_hit_audit']=dict(cases=675,exact=True,
            slower_than_expanded=[r['case'] for r in allrows if r['delta_from_expanded_tstates']>0],
            slower_than_shared=[r['case'] for r in allrows if r['delta_from_shared_tstates']>0],
            largest_delta_from_expanded_tstates=max(r['delta_from_expanded_tstates'] for r in allrows),
            largest_delta_from_shared_tstates=max(r['delta_from_shared_tstates'] for r in allrows))
    report['full_baseline_token_mix']=base
    report['all_finalists_675_case_hit_model_exact']=True
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--screen-only',action='store_true');p.add_argument('--short-kernels',action='store_true');p.add_argument('--verify-only',action='store_true');p.add_argument('--audit-hits',action='store_true');args=p.parse_args()
    if args.audit_hits:audit_hits(args.output);return
    if args.verify_only:
        report=json.loads(args.output.read_text(encoding='utf-8'))
        for item in report['profiles'].values():
            assert definition(build(**item['options']))==item['layout']
            if item.get('finalist'):assert definition(build(core=0x9103,**item['options']))==item['relocated_layout']
        report['revalidated_all_profile_bytes_exact']=True
        report['revalidated_generator_source_sha256_lf']={str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes().replace(b'\r\n',b'\n'))
            for path in (Path(__file__),ROOT/'libraries/tests/wide_hybrid_profile.py',ROOT/'libraries/lzsa/src/lzsa/wide.py',ROOT/'libraries/tests/wide_short_profile.py')}
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');return
    cases=list(samples());real=[c for c in cases if c[0].startswith('real-')];directed=list(directed_tokens())
    assert len(cases)==95 and len(directed)==580
    expanded,shared=public(),public(shared_literals=True)
    assert build()[0]==shared[0]
    counts=Counter();real_rows=[]
    for case in real:
        result,counter=profiled(expanded,case);counts.update(counter)
        shared_result=execute(shared,case[1],case[2])
        expected=10*sum(n for token,n in counter.items() if (token>>3)&3)
        assert shared_result['tstates']-result['tstates']==expected
        real_rows.append(dict(case=case[0],payload_sha256=sha(case[1]),raw_sha256=sha(case[2]),
            expanded_tstates=result['tstates'],shared_tstates=shared_result['tstates'],token_counts=dict(counter)))
    exp_total=sum(r['expanded_tstates'] for r in real_rows);share_total=sum(r['shared_tstates'] for r in real_rows)
    assert (exp_total,share_total)==(15623953,15869483)
    rank=ranking(counts)
    kernel_options=dict(short_lengths=list(range(2,9)),repeat_lengths=list(range(4,9))) if args.short_kernels else {}
    base=build(**kernel_options);base_size=base[2]['service_memory_bytes']
    def token_saving(token):
        n=(token&7)+2;cls=token>>5
        if not args.short_kernels:return 0
        return 5*n-4 if cls<7 and n<=8 else (5*n-16 if cls==7 and 4<=n<=8 else 0)
    kernel_saving=sum(n*token_saving(token) for token,n in counts.items())
    layout=base[2]['body_layout'];weights={row['base_token']:row['groups'][0]['body_bytes']-3 for row in layout}
    if not args.short_kernels:assert sum(weights.values())*3==7004-3452
    policies={
        'LL1-expanded':dict(groups=((0,2,3),(1,))),
        'LL2-expanded':dict(groups=((0,1,3),(2,))),
        'LL12-expanded':dict(groups=((0,3),(1,),(2,))),
        'shared-hot-fallthrough':dict(groups=((0,1,2,3),),fallthrough_order=rank),
        'pair-hot-fallthrough':dict(groups=((0,1),(2,3)),fallthrough_order=rank)}
    if args.short_kernels:policies={'short-shared':{},'short-shared-hot':dict(fallthrough_order=rank)}
    for cap in ((4300,5000,6500,8000,9500) if args.short_kernels else (3452,4000,4500,5000,5500,6000)):
        groups,cost,benefit=choose(counts,rank,weights,cap-base_size)
        policies['budget-'+str(cap)]=dict(groups_by_body=groups,fallthrough_order=rank)
    report=dict(date='2026-10-20',complete=False,release=False,experimental=True,goal_achieved=False,
        scope='Private raw sharing-layout experiment; public profiles/defaults unchanged; no coroutine/guarded/player adoption.',
        fixed_real_inputs=len(real),corpus_cases=95,directed_cases=580,
        baseline_expanded=dict(layout=definition(expanded),real_tstates=exp_total),baseline_shared=dict(layout=definition(shared),real_tstates=share_total),
        token_counts=dict(counts),real_inputs=real_rows,profiles={})
    report['short_kernel_options']=kernel_options
    report['modeled_short_kernel_real_saving_tstates']=kernel_saving
    report['modeled_fully_specialized_kernel_real_floor_tstates']=exp_total-kernel_saving
    finalists={'budget-5000','budget-6500','budget-9500'} if args.short_kernels else {'budget-3452','budget-4500','budget-5500'}
    for name,policy in policies.items():
        options=dict(kernel_options,**policy)
        profile=build(**options);hits=set(profile[2]['shared_hit_tokens'])
        modeled=exp_total-kernel_saving+10*sum(n for token,n in counts.items() if token in hits)
        rows=[]
        for case in real:
            result=execute(profile,case[1],case[2]);before=next(r for r in real_rows if r['case']==case[0])
            expected=before['expanded_tstates']-sum(n*token_saving(token) for token,n in before['token_counts'].items())+10*sum(n for token,n in before['token_counts'].items() if token in hits)
            assert result['tstates']==expected
            rows.append(dict(case=case[0],candidate_tstates=result['tstates'],delta_from_shared_tstates=result['tstates']-before['shared_tstates'],exact=True))
        assert sum(r['candidate_tstates'] for r in rows)==modeled
        item=dict(options=options,layout=definition(profile),body_layout=profile[2]['body_layout'],shared_hit_tokens=sorted(hits),shared_hit_tstates=10,
            real_tstates=modeled,real_delta_from_shared=modeled-share_total,real_delta_from_expanded=modeled-exp_total,
            real_slower_than_shared=sum(r['delta_from_shared_tstates']>0 for r in rows),real_blocks=rows)
        if name in finalists and not args.screen_only:
            moved=build(core=0x9103,**options);full=[];extra=[]
            for case,payload,raw in cases:
                plain=execute(profile,payload,raw);irq=execute(profile,payload,raw,interrupts=True);relocated=execute(moved,payload,raw)
                assert relocated['tstates']==plain['tstates'] and plain['stack_bytes']<=6
                assert irq['stack_bytes']<=12
                full.append(dict(case=case,payload_sha256=sha(payload),raw_sha256=sha(raw),candidate_tstates=plain['tstates'],exact=True,relocated_exact=True,
                    stack_bytes=plain['stack_bytes'],irq_stack_bytes=irq['stack_bytes'],injected_interrupts=irq['injected_interrupts']))
            for case,payload,raw,value in directed:
                seen=set()
                def watch(machine):seen.add(value)
                plain=execute(profile,payload,raw,watch={profile[1]['token_'+str(value)]:watch})
                assert value in seen
                irq=execute(profile,payload,raw,interrupts=True);relocated=execute(moved,payload,raw)
                assert plain['tstates']==relocated['tstates'] and plain['stack_bytes']<=6 and irq['stack_bytes']<=12
                extra.append(dict(case=case,token=value,payload_sha256=sha(payload),raw_sha256=sha(raw),candidate_tstates=plain['tstates'],exact=True,relocated_exact=True,
                    stack_bytes=plain['stack_bytes'],irq_stack_bytes=irq['stack_bytes'],injected_interrupts=irq['injected_interrupts']))
            item.update(finalist=True,full_blocks=full,directed_blocks=extra,relocated_layout=definition(moved),
                observed_stack_bytes=max(r['stack_bytes'] for r in full+extra),observed_irq_stack_bytes=max(r['irq_stack_bytes'] for r in full+extra))
        report['profiles'][name]=item
        print(name,definition(profile)['service_memory_bytes'],modeled,'delta_shared',modeled-share_total,flush=True)
    report['complete']=not args.screen_only
    report['screen_complete']=True
    report['source_sha256_lf']={str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes().replace(b'\r\n',b'\n'))
        for path in (ROOT/'libraries/lzsa/src/lzsa/wide.py',Path(__file__),ROOT/'libraries/tests/wide_hybrid_profile.py',ROOT/'libraries/tests/measure_full_token_dispatch.py',ROOT/'libraries/tests/native_block.py',ROOT/'libraries/tests/wide_short_profile.py')}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
