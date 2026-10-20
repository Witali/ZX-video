"""E01: one opt-in LZSA2 cold length escape, qualified kosarev CPU only.

Each of twelve fixed raw selections replays the frozen 95+580 inputs using
disjoint plain/IM1/relocated and actual minimum-safe in-place equivalents.
The immediately preceding classic profile is independently watched, and each
complete CPU delta must equal -3*nibble_length + 2*extended_length. No input,
copy kernel, literal selector or wrapper feature is changed by this trial.
"""
import argparse
from collections import Counter
from datetime import date
import gzip
import importlib.metadata
import json
from pathlib import Path
import subprocess

from measure_long_copy import ROOT,samples,sha
from measure_full_token_dispatch import directed_tokens
from profile_branch_mix import instructions
from native_block import execute
from native_inplace_block import execute as inplace
from lzsa.hybrid import build as hybrid
from lzsa.wide import build as wide


def selections():
    rows=[('hybrid-'+name,hybrid,dict(profile=name)) for name in
        ('compact','balanced','fast','compact-base','balanced-base','fast-base')]
    rows += [('wide-expanded',wide,{}),('wide-shared',wide,dict(shared_literals=True)),
        ('wide-shared-new',wide,dict(shared_literals=True,short_lengths=list(range(2,9)))),
        ('wide-shared-new-repeat',wide,dict(shared_literals=True,short_lengths=list(range(2,9)),repeat_lengths=list(range(4,9)))),
        ('wide-new3',wide,dict(short_lengths=list(range(3,9)))),
        ('wide-new2',wide,dict(short_lengths=list(range(2,9))))]
    return rows


def regions(profile):
    return [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]]


def identity(profile):
    return sha(json.dumps(dict(regions=regions(profile),labels=profile[1],metadata=profile[2]),sort_keys=True).encode())


def branch_address(profile):
    return profile[1]['LongMatchNibble']+6


def branch_observer(profile,*,candidate=False,wanted=None):
    at=branch_address(profile);origin,blob=profile[0][0]
    assert blob[at-origin]==(0x30 if candidate else 0xda)
    counts=Counter()
    def hit(machine):counts['short' if machine.f&1 else 'extended']+=1
    watch={at:hit}
    if wanted is not None:
        watch[profile[1]['token_'+str(wanted)]]=lambda machine:counts.update(('target_token',))
    return counts,watch


def spans(profile):
    at,blob=profile[0][0];start=profile[1]['start']-at
    rows=[]
    for pc,code in instructions(blob[start:],at+start):
        if code[0] in (0x18,0x20,0x28,0x30,0x38):
            displacement=int.from_bytes(code[1:],'little',signed=True)
            rows.append(dict(address=pc,opcode=code[0],displacement=displacement,target=pc+2+displacement))
    return rows


def inventory(builder,kwargs,saved):
    rows=[]
    for low,old in enumerate(saved['alignments']):
        core=0x8000+low
        try:classic=builder(core=core,**kwargs)
        except ValueError as error:
            assert not old['accepted'] and str(error)==old['error']
            classic=None
        else:
            assert old['accepted'] and identity(classic)==old['complete_profile_sha256'],('default changed',low)
        try:changed=builder(core=core,cold_match_extension=True,**kwargs)
        except ValueError as error:
            assert classic is None,('new layout rejects formerly valid placement',low)
            rows.append(dict(low=low,core=core,classic_accepted=False,candidate_accepted=False,error=str(error)))
            continue
        size=changed[2]['service_memory_bytes']
        assert size<=10000
        if classic is not None:assert size==classic[2]['service_memory_bytes']-1
        old_spans=spans(classic) if classic else None
        new_spans=spans(changed)
        at=branch_address(changed)
        new_branch=next(row for row in new_spans if row['address']==at)
        assert new_branch['opcode']==0x30 and new_branch['displacement']==26
        if old_spans is not None:
            assert [(r['opcode'],r['displacement']) for r in new_spans if r['address']!=at]==[(r['opcode'],r['displacement']) for r in old_spans]
        rows.append(dict(low=low,core=core,classic_accepted=classic is not None,candidate_accepted=True,
            classic_service_bytes=classic[2]['service_memory_bytes'] if classic else None,
            candidate_service_bytes=size,candidate_with_example_irq_bytes=size+19,
            example_irq_fits=size+19<=10000,alignment_padding=changed[2]['alignment_padding'],
            regions=regions(changed),new_jr=new_branch,existing_relative_displacements_unchanged=old_spans is not None))
    return rows


def read_json(path):
    blob=path.read_bytes()
    return json.loads(gzip.decompress(blob) if path.suffix=='.gz' else blob)


def frozen_baselines():
    evidence=ROOT/'libraries/evidence'
    files={key:evidence/path for key,path in dict(
        basic='wide_hybrid/wide_hybrid_experiment.json.gz',
        short='wide_hybrid/wide_hybrid_experiment_short.json.gz',
        copies='wide_short_experiment_full.json.gz',
        wide='ten_percent_full_token_dispatch.json',
        e00='next_e00_lzsa_full.json.gz',defaults='next_e01_lzsa_defaults.json.gz').items()}
    saved={key:read_json(path) for key,path in files.items()}
    golden={}
    for name,selector,short in (('compact','budget-5000',True),('balanced','budget-6500',True),
        ('fast','budget-9500',True),('compact-base','budget-3452',False),
        ('balanced-base','budget-4500',False),('fast-base','budget-5500',False)):
        row=saved['short' if short else 'basic']['profiles'][selector]
        golden['hybrid-'+name]={item['case']:item['candidate_tstates'] for item in row['full_blocks']+row['directed_blocks']}
    for name,key in (('wide-expanded','expanded'),('wide-shared','shared-literal-bodies')):
        row=saved['wide']['profiles'][key]
        golden[name]={case:item['tstates']+(10*sum(count for token,count in item['counts'].items()
            if (int(token)>>3)&3) if name=='wide-shared' else 0)
            for case,item in saved['copies']['baseline_cases'].items()}
        # The original Shared report saves full-case95 CPU but only aggregate
        # directed coverage. Bind those95, then independently execute all675;
        # the remaining580 classic references use archived token frequencies.
        assert all(golden[name][item['case']]==item['candidate_tstates'] for item in row['blocks'])
    for name,key in (('wide-shared-new','shared-new-all'),('wide-shared-new-repeat','shared-new-all-repeat-4to8'),
        ('wide-new3','new-3to8'),('wide-new2','new-all')):
        golden[name]={item['case']:item['candidate_tstates'] for item in saved['copies']['profiles'][key]['blocks']}
    assert all(len(rows)==675 for rows in golden.values())
    e00={row['case']:row for row in saved['e00']['profiles']['fast']['blocks']}
    at=next(row['address'] for row in saved['e00']['profiles']['fast']['real']['branches']
        if row['kind']=='jp' and row['condition']=='C' and 'CopyMatchA' in row['target_labels'])
    for row in e00.values():
        counts=row['observers']['branches']
        row['model_counts']=dict(short=counts.get(str((at,1)),0),extended=counts.get(str((at,0)),0))
    return golden,e00,saved['defaults'],{str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes()) for path in files.values()}


def layout(profile):
    return dict(regions=regions(profile),labels=profile[1],metadata=profile[2],relative_branches=spans(profile))


def summarize(rows):
    real=[row for row in rows if row['real']]
    slower=[dict(case=row['case'],real=row['real'],delta_tstates=row['delta_tstates']) for row in rows if row['delta_tstates']>0]
    return dict(cases=len(rows),real_cases=len(real),baseline_real_tstates=sum(row['baseline_tstates'] for row in real),
        candidate_real_tstates=sum(row['candidate_tstates'] for row in real),
        real_delta_tstates=sum(row['delta_tstates'] for row in real),
        all_delta_tstates=sum(row['delta_tstates'] for row in rows),
        faster_cases=sum(row['delta_tstates']<0 for row in rows),equal_cases=sum(row['delta_tstates']==0 for row in rows),
        slower_case_count=len(slower),slower_real_cases=[row for row in slower if row['real']],
        maximum_regression_tstates=max([row['delta_tstates'] for row in slower]+[0]),slower_cases=slower,
        short_outcomes=sum(row['branch_counts']['short'] for row in rows),extended_outcomes=sum(row['branch_counts']['extended'] for row in rows),
        maximum_plain_stack_bytes=max(row['inplace_plain']['stack_bytes'] for row in rows),
        maximum_irq_stack_bytes=max(row['inplace_irq']['stack_bytes'] for row in rows),
        injected_interrupts=sum(row['irq']['injected_interrupts']+row['inplace_irq']['injected_interrupts'] for row in rows),
        all_per_case_models_exact=True,all_inplace_host_read_order_exact=True,
        irq_and_relocation_exact=True,dirty_offset_and_code_permissions_exact=True,
        slices='Raw one-shot profile: complete blocks and individual length outcomes; no coroutine quota slices exposed.')


def save(report,output):
    archive=output.with_name(output.stem+'_full.json.gz')
    archive.write_bytes(gzip.compress((json.dumps(report,indent=2)+'\n').encode(),mtime=0))
    overview={key:value for key,value in report.items() if key!='profiles'}
    overview['profiles']={}
    for name,item in report['profiles'].items():
        summary={key:value for key,value in item.get('summary',{}).items() if key!='slower_cases'}
        overview['profiles'][name]=dict(kwargs=item['kwargs'],module=item['module'],complete=item['complete'],
            baseline_regions=item['baseline']['regions'],candidate_regions=item['candidate']['regions'],
            baseline_service_bytes=item['baseline']['metadata']['service_memory_bytes'],
            candidate_service_bytes=item['candidate']['metadata']['service_memory_bytes'],
            candidate_relocated_service_bytes=item['relocated']['metadata']['service_memory_bytes'],
            alignment_summary=item['alignment_summary'],summary=summary,accepted=item.get('accepted',False))
    overview['full_evidence']=dict(path=str(archive.relative_to(ROOT)).replace('\\','/'),sha256=sha(archive.read_bytes()))
    output.write_text(json.dumps(overview,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    golden,e00,defaults,evidence=frozen_baselines()
    cases=[(n,p,r,None) for n,p,r in samples()]+list(directed_tokens())
    assert len(cases)==675
    sources=('libraries/lzsa/src/lzsa/wide.py','libraries/lzsa/src/lzsa/hybrid.py',
        'libraries/lzsa/src/lzsa/_wide_kernels.py','libraries/lzsa/src/lzsa/_z80.py',
        'libraries/lzsa/src/lzsa/codec.py','libraries/tests/native_block.py',
        'libraries/tests/native_inplace_block.py','libraries/tests/measure_next_cold_extension.py',
        'libraries/tests/test_cold_extension.py','libraries/tests/profile_branch_mix.py',
        'libraries/Z80_TIMINGS.md')
    source_hashes={path:sha((ROOT/path).read_bytes().replace(b'\r\n',b'\n')) for path in sources}
    report=dict(date=date.today().isoformat(),stage='E01',complete=False,release=False,
        baseline_revision='a7d61019',fixed_decoder_baseline_revision='9c28b01f',
        observation_head=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip(),
        backend=dict(name='kosarev z80',version=importlib.metadata.version('z80'),qualified=True,
            spectrum_backend_used=False),source_sha256_lf=source_hashes,evidence_sha256=evidence,
        corpus_cases=95,directed_cases=580,profiles={},candidate_count=1,
        classic_cpu_binding='Hybrid/short/Expanded all675 use saved per-case native CPU; Shared95 uses saved native CPU and Shared580 uses saved Expanded/token-frequency equations, independently executed here.',
        policy='cold_match_extension=True; defaults False are exact',
        per_path_tstates=dict(classic_conditional_jp=10,candidate_nibble_jr_not_taken=7,
            candidate_extended_jr_taken=12,nibble_delta=-3,extended_delta=2),
        memory_contract=dict(scope='code/tables/alignment/embedded and external state/caller and private stacks/scratch/internal buffers',
            input_output_history_excluded=True,example_irq_code_bytes=13,example_irq_additional_stack_bytes=6,
            embedded_offset_operand_bytes=2,embedded_offset_already_in_code=True,caller_stack_includes_return=True,
            external_input_max=max(len(p) for n,p,r,t in cases),external_output_history_max=max(len(r) for n,p,r,t in cases)),
        exclusions=['coroutine/guarded features','unqualified Wide short/repeat combinations','physical disk/ROM','ULA/WAIT','movie timing'])
    for name,builder,kwargs in selections():
        baseline=builder(**kwargs);candidate=builder(cold_match_extension=True,**kwargs)
        moved=builder(core=0x9103,cold_match_extension=True,**kwargs)
        alignments=inventory(builder,kwargs,defaults['profiles'][name])
        valid=[row for row in alignments if row['candidate_accepted']]
        profile=dict(module=builder.__module__,kwargs=kwargs,complete=False,
            baseline=layout(baseline),candidate=layout(candidate),relocated=layout(moved),
            alignments=alignments,blocks=[],alignment_summary=dict(origins=256,
                classic_accepted=sum(row['classic_accepted'] for row in alignments),candidate_accepted=len(valid),
                candidate_rejected=256-len(valid),classic_defaults_exact=True,
                candidate_service_min=min(row['candidate_service_bytes'] for row in valid),
                candidate_service_max=max(row['candidate_service_bytes'] for row in valid),
                candidate_irq_fitting_origins=sum(row['example_irq_fits'] for row in valid),
                maximum_example_irq_bytes=max(row['candidate_with_example_irq_bytes'] for row in valid)))
        report['profiles'][name]=profile
        for index,(case,payload,raw,wanted) in enumerate(cases):
            previous=e00[case]
            assert sha(payload)==previous['payload_sha256'] and sha(raw)==previous['raw_sha256']
            counts,watch=branch_observer(baseline,wanted=wanted)
            old=execute(baseline,payload,raw,watch=watch)
            assert old['tstates']==golden[name][case]
            branch_counts=dict(short=counts['short'],extended=counts['extended'])
            assert branch_counts==previous['model_counts']
            if wanted is not None:assert counts['target_token']
            current,current_watch=branch_observer(candidate,candidate=True,wanted=wanted)
            plain=execute(candidate,payload,raw,watch=current_watch)
            assert dict(short=current['short'],extended=current['extended'])==branch_counts
            if wanted is not None:assert current['target_token']
            expected=-3*counts['short']+2*counts['extended']
            assert plain['tstates']-old['tstates']==expected,(name,case,'CPU model')
            irq=execute(candidate,payload,raw,interrupts=True)
            relocated=execute(moved,payload,raw)
            overlap=inplace(candidate,payload,raw,codec='lzsa2')
            overlap_irq=inplace(candidate,payload,raw,codec='lzsa2',interrupts=True)
            overlap_moved=inplace(moved,payload,raw,codec='lzsa2')
            assert plain['tstates']==relocated['tstates']==overlap['tstates']==overlap_moved['tstates']
            assert irq['tstates']==overlap_irq['tstates']
            assert all(row['host_read_order_exact'] for row in (overlap,overlap_irq,overlap_moved))
            assert all(row['actual_overlap_bytes']>0 or not raw for row in (overlap,overlap_irq,overlap_moved))
            assert plain['stack_bytes']<=6 and overlap['stack_bytes']<=6 and overlap_irq['stack_bytes']<=12
            profile['blocks'].append(dict(case=case,real=case.startswith('real-'),payload_sha256=sha(payload),raw_sha256=sha(raw),
                input_bytes=len(payload),output_history_bytes=len(raw),baseline_tstates=old['tstates'],
                candidate_tstates=plain['tstates'],delta_tstates=expected,branch_counts=branch_counts,
                model_exact=True,plain=plain,irq=irq,relocated=relocated,
                inplace_plain=overlap,inplace_irq=overlap_irq,inplace_relocated=overlap_moved))
            if (index+1)%75==0:print(name,f'{index+1}/675',flush=True)
        profile['summary']=summarize(profile['blocks'])
        profile['complete']=True
        profile['accepted']=(profile['summary']['real_delta_tstates']<0 and
            candidate[2]['service_memory_bytes']<baseline[2]['service_memory_bytes'] and
            not profile['summary']['slower_real_cases'])
        assert profile['accepted']
        save(report,output)
        print(name,json.dumps(profile['summary']|dict(slower_cases='see full archive')),flush=True)
    assert all(sha((ROOT/path).read_bytes().replace(b'\r\n',b'\n'))==digest for path,digest in source_hashes.items())
    report['complete']=True
    report['accepted']=all(item['accepted'] for item in report['profiles'].values())
    report['candidate_native_runs']=12*675*6
    report['independent_classic_observer_runs']=12*675
    save(report,output)


if __name__=='__main__':main()
