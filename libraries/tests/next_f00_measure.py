"""F00: full raw qualification of three measured faster/larger candidates.

675 frozen cases bind the C screen to E01 CPU and E00 instruction counts.
Each candidate then receives the original protected kosarev plain/IRQ/
relocated gate and all three actual minimum-safe in-place variants. The
private plain runner only adds the missing IY sentinel to the original gate.
"""
import argparse
from collections import Counter
from datetime import date
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
for path in (ROOT/'libraries/lzsa/src',ROOT/'libraries/zx0/src',ROOT/'libraries/tests',ROOT):
    sys.path.insert(0,str(path))

import native_block
from native_inplace_block import execute as inplace
from next_e02_profiles import extra_word_cases,transformed_source
from next_e02_measure import helper_counts,model as e02_model
from next_e03_measure import hot_family_cases,phase_counts,region_binding,read_gzip,sha,DLL_SHA
from next_f00_profiles import KINDS,EXPECTED_SERVICE,EXPECTED_REAL_TSTATES,build
from emulator.cpu import load_library,execute_block
from measure_long_copy import samples
from measure_full_token_dispatch import directed_tokens
from lzsa.hybrid import build as public
from profile_next_lzsa import Observer
import z80


def protected_source():
    source=inspect.getsource(native_block.execute)
    old='preserved=dict(ix=0x1357,alt_bc=0x2468,alt_de=0x369a,alt_hl=0xace1)'
    assert source.count(old)==1
    return source.replace(old,'preserved=dict(iy=0x57b9,ix=0x1357,alt_bc=0x2468,alt_de=0x369a,alt_hl=0xace1)')


def protected_runner():
    namespace=dict(vars(native_block))
    exec(compile(protected_source(),'<F00 original protected runner plus IY sentinel>','exec'),namespace)
    return namespace['execute']


PROTECTED=protected_runner()


def dirty(profile):
    regions,labels,metadata=profile
    patches=set(metadata['patched_addresses'])
    return [(at,bytes(0xa5 if at+i in patches else byte for i,byte in enumerate(blob))) for at,blob in regions],labels,metadata


def model(kind,oracle):
    _,clone=helper_counts(oracle)
    clone_delta=e02_model('hot-clone',Counter(),clone)
    phase=oracle['observers']['nibble_phases']
    # The frozen E00 address is supplied by main, avoiding a guessed body PC.
    pair_delta=-15*phase.get(str((FROZEN_HOT_BRANCH,'cached')),0)
    if kind=='hot_clone':return clone_delta
    if kind=='hot_pair':return pair_delta
    if kind=='combined':return clone_delta+pair_delta
    raise ValueError(kind)


FROZEN_HOT_BRANCH=None


def source_hashes():
    names=('libraries/tests/next_f00_profiles.py','libraries/tests/next_f00_measure.py',
        'libraries/tests/test_next_f00.py','libraries/tests/next_e02_profiles.py',
        'libraries/tests/next_e02_measure.py','libraries/tests/next_e03_profiles.py',
        'libraries/tests/next_e03_measure.py','libraries/tests/native_block.py',
        'libraries/tests/native_inplace_block.py','libraries/tests/profile_next_lzsa.py',
        'libraries/tests/profile_branch_mix.py','libraries/tests/measure_long_copy.py',
        'libraries/tests/measure_full_token_dispatch.py','libraries/lzsa/src/lzsa/hybrid.py',
        'libraries/lzsa/src/lzsa/wide.py','libraries/lzsa/src/lzsa/_wide_kernels.py',
        'libraries/lzsa/src/lzsa/_z80.py','libraries/lzsa/src/lzsa/codec.py','emulator/cpu.py')
    assert all((ROOT/name).is_file() for name in names)
    return {name:sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n')) for name in names}


def alignment_screen(kind):
    rows=[]
    for low in range(256):
        p=build(kind,core=0x8000+low)
        aligned_delta=EXPECTED_SERVICE[kind]-9499
        assert p[2]['service_memory_bytes']==EXPECTED_SERVICE[kind]+((-low)&255)
        assert p[2]['service_memory_bytes']+19<=10000
        assert p[2]['caller_stack_bytes']==6
        assert p[2]['service_memory_bytes']-public('fast',core=0x8000+low,cold_match_extension=True)[2]['service_memory_bytes']==aligned_delta
        rows.append(dict(low_byte=low,service_bytes=p[2]['service_memory_bytes'],
            example_irq_inclusive_bytes=p[2]['service_memory_bytes']+19,
            regions=region_binding(p)['regions'],labels_sha256=region_binding(p)['labels_sha256']))
    return rows


def totals(rows,field='c_guarded'):
    real=[row for row in rows if row['real']]
    slower=[dict(case=row['case'],real=row['real'],delta_tstates=row['delta_tstates']) for row in rows if row['delta_tstates']>0]
    return dict(cases=len(rows),real_cases=len(real),real_tstates=sum(row[field]['tstates'] for row in real),
        real_delta_tstates=sum(row['delta_tstates'] for row in real),
        faster_cases=sum(row['delta_tstates']<0 for row in rows),equal_cases=sum(row['delta_tstates']==0 for row in rows),
        slower_cases=slower,slower_real_cases=sum(row['real'] for row in slower),
        max_regression_tstates=max([row['delta_tstates'] for row in slower] or [0]))


def native_modes(profile,relocated,payload,raw,expected_cpu):
    result={}
    for name,p,irq,overlap in (
        ('plain',profile,False,False),('irq',profile,True,False),('relocated',relocated,False,False),
        ('inplace_plain',profile,False,True),('inplace_irq',profile,True,True),('inplace_relocated',relocated,False,True)):
        got=inplace(p,payload,raw,codec='lzsa2',interrupts=irq) if overlap else PROTECTED(dirty(p),payload,raw,interrupts=irq,alternate_af=0x9797)
        if not irq:
            assert got['tstates']==expected_cpu,(name,got['tstates'],expected_cpu)
        assert got['stack_bytes']<=12 if irq else got['stack_bytes']<=6
        if overlap:
            assert got['host_read_order_exact'] and got['code_protected'] and got['raw_abi_exact']
            assert got['host_minimum_input_start']==got['native_minimum_input_start']
            assert got['actual_overlap_bytes']>0 or not raw
        result[name]=got
    return result


def supplemental_oracles(baseline,library):
    rows=[]
    for name,payload,raw,phase in extra_word_cases():
        observer=Observer(baseline);observer.reset()
        reference=PROTECTED(dirty(baseline),payload,raw,watch=observer.watch)
        observed=observer.finish(reference)
        _,clone=helper_counts(dict(observers=observed))
        assert clone==Counter(word=1)
        rows.append((name,payload,raw,dict(first_phase=phase,clone_paths=dict(clone),clone_delta=10,pair_delta=0,
            baseline_tstates=reference['tstates'])))
    for name,payload,raw,phase,exit_form in hot_family_cases():
        old=execute_block(baseline,payload,raw,library=library)
        rows.append((name,payload,raw,dict(first_phase=phase,match_exit_form=exit_form,
            clone_delta=0,pair_delta=-15*int(phase=='full'),baseline_tstates=old['tstates'])))
    assert len(rows)==60
    return rows


def main(output):
    global FROZEN_HOT_BRANCH
    output=Path(output)
    library=load_library();dll=Path(library._name)
    assert sha(dll.read_bytes())==DLL_SHA
    launch_sources=source_hashes()
    e00=read_gzip('next_e00_lzsa_full.json.gz')['profiles']['fast']
    e01=read_gzip('next_e01_lzsa_full.json.gz')['profiles']['hybrid-fast']
    assert e01['complete'] and e01['accepted']
    FROZEN_HOT_BRANCH=e00['labels']['body_167_0']+2
    baseline=public('fast',cold_match_extension=True)
    assert region_binding(baseline)['regions']==e01['candidate']['regions']
    assert baseline[1]==e01['candidate']['labels']
    cases=list(samples())+[row[:3] for row in directed_tokens()]
    assert len(cases)==675
    assert [case[0] for case in cases]==[row['case'] for row in e00['blocks']]==[row['case'] for row in e01['blocks']]
    backend_files=[Path(z80.__file__)]+sorted(Path(z80.__file__).parent.glob('*.pyd'))
    assert len(backend_files)>=2
    report=dict(date=date.today().isoformat(),stage='F00',complete=False,release=False,public_changes=False,
        objective='Find nondominated faster raw candidates within10000 total service bytes; larger than E01 is allowed.',
        launch_source_sha256_lf=launch_sources,baseline=region_binding(baseline),baseline_real_tstates=14926306,
        protected_runner_extra_guard='Original native_block.execute, privately adding only IY=57B9 sentinel; mutable2B operands poisonedA5A5 in supplied image.',
        protected_runner_source_sha256=sha(protected_source().encode()),
        native_C=dict(dll_path=str(dll),dll_sha256=DLL_SHA,build=json.loads(dll.with_name('build.json').read_text())),
        native_kosarev_files={str(path):sha(path.read_bytes()) for path in backend_files},
        archived_proof_sha256={name:sha((ROOT/'libraries/evidence'/name).read_bytes()) for name in
            ('next_e00_lzsa_full.json.gz','next_e01_lzsa_full.json.gz','next_e02_lzsa_full.json.gz','next_e03_full.json.gz')},
        C_qualification_proof_sha256={name:sha((ROOT/'emulator/evidence'/name).read_bytes()) for name in
            ('verification.json','native_build.json')},
        baseline_binding=[],profiles={},attempts=[],unperformed=['Public API/CLI/export/wheel integration','Coroutine/guarded wrappers','Physical ULA/disk/ROM/movie timing'])
    def save():
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_bytes(gzip.compress((json.dumps(report,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0))
    current=dict(stage='init')
    try:
        save()
        for index,((name,payload,raw),golden,oracle) in enumerate(zip(cases,e01['blocks'],e00['blocks'])):
            current=dict(stage='C baseline',case=name,index=index)
            assert sha(payload)==golden['payload_sha256']==oracle['payload_sha256']
            assert sha(raw)==golden['raw_sha256']==oracle['raw_sha256']
            got=execute_block(baseline,payload,raw,library=library)
            assert got['tstates']==golden['candidate_tstates']
            report['baseline_binding'].append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),
                real=name.startswith('real-'),tstates=got['tstates'],E01_kosarev_exact=True))
            if index%100==99:print('C baseline',index+1,flush=True)
        assert sum(row['tstates'] for row in report['baseline_binding'] if row['real'])==14926306
        extras=supplemental_oracles(baseline,library)
        for kind in KINDS:
            current=dict(stage='alignment+C screen',profile=kind)
            p,moved=build(kind),build(kind,core=0x9103)
            entry=dict(**region_binding(p),relocated=region_binding(moved),alignments=alignment_screen(kind),
                C_complete=False,native_complete=False,blocks=[],supplemental=[])
            report['profiles'][kind]=entry
            assert p[2]['service_memory_bytes']==EXPECTED_SERVICE[kind]
            for index,((name,payload,raw),golden,oracle) in enumerate(zip(cases,e01['blocks'],e00['blocks'])):
                current=dict(stage='C screen',profile=kind,case=name,index=index)
                got=execute_block(p,payload,raw,library=library)
                delta=model(kind,oracle)
                assert got['tstates']==golden['candidate_tstates']+delta,(kind,name,got,delta)
                assert got['stack_bytes']<=6
                entry['blocks'].append(dict(case=name,real=name.startswith('real-'),payload_sha256=sha(payload),raw_sha256=sha(raw),
                    baseline_tstates=golden['candidate_tstates'],delta_tstates=delta,model_exact=True,c_guarded=got))
                if index%100==99:print('C screen',kind,index+1,flush=True)
            entry['summary']=totals(entry['blocks'])
            assert entry['summary']['real_tstates']==EXPECTED_REAL_TSTATES[kind]
            for name,payload,raw,oracle in extras:
                got=execute_block(p,payload,raw,library=library)
                expected=(oracle['clone_delta'] if kind in ('hot_clone','combined') else 0)+(oracle['pair_delta'] if kind in ('hot_pair','combined') else 0)
                assert got['tstates']==oracle['baseline_tstates']+expected,(kind,name,got,oracle,expected)
                entry['supplemental'].append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),
                    baseline=oracle,delta_tstates=expected,c_guarded=got))
            entry['C_complete']=True;save()
            print('C screen complete',kind,entry['summary']['real_tstates'],flush=True)
        for kind in KINDS:
            p,moved=build(kind),build(kind,core=0x9103)
            entry=report['profiles'][kind]
            for index,((name,payload,raw),row) in enumerate(zip(cases,entry['blocks'])):
                current=dict(stage='protected6mode',profile=kind,case=name,index=index)
                row['protected']=native_modes(p,moved,payload,raw,row['c_guarded']['tstates'])
                if index%50==49:
                    save();print('protected6mode',kind,index+1,flush=True)
            for (name,payload,raw,oracle),row in zip(extras,entry['supplemental']):
                current=dict(stage='supplemental6mode',profile=kind,case=name)
                row['protected']=native_modes(p,moved,payload,raw,row['c_guarded']['tstates'])
            # Keep input disjoint for theFFFF cursor probe: a minimum-safe
            # in-place block can need EOF bytes beyond its final output byte.
            boundary=[]
            selected=[cases[0],next(case for case in cases if case[0]=='single-nibble-eof-one'),next(case for case in cases if case[0]=='word-literal-1')]
            for name,payload,raw in selected:
                cpu=next(row['c_guarded']['tstates'] for row in entry['blocks'] if row['case']==name)
                modes={}
                for mode,builder,irq in [('plain',p,False),('irq',p,True),('relocated',moved,False)]:
                    got=PROTECTED(dirty(builder),payload,raw,output=0xffff-len(raw),interrupts=irq,alternate_af=0x9797)
                    if not irq:assert got['tstates']==cpu
                    modes[mode]=got
                boundary.append(dict(case=name,output=0xffff-len(raw),output_cursor=0xffff,modes=modes))
            entry['FFFF_output_cursor_probes']=boundary
            entry['native_complete']=True
            all_rows=entry['blocks']+entry['supplemental']
            entry['qualification']=dict(complete=True,frozen_cases=675,supplemental_cases=60,modes_per_case=6,
                native_configs=len(all_rows)*6,FFFF_configs=9,
                maximum_plain_stack_bytes=max(row['protected']['plain']['stack_bytes'] for row in all_rows),
                maximum_irq_stack_bytes=max(row['protected']['irq']['stack_bytes'] for row in all_rows),
                maximum_inplace_irq_stack_bytes=max(row['protected']['inplace_irq']['stack_bytes'] for row in all_rows),
                actual_overlap_cases=sum(row['protected']['inplace_plain']['actual_overlap_bytes']>0 for row in entry['blocks']),
                injected_interrupts=sum(row['protected'][mode]['injected_interrupts'] for row in all_rows for mode in ('irq','inplace_irq')),
                source_frontier_code_EOF_ABI_dirtyoffset=True,
                host_native_write_cursor_digests_exact=True,raw_only=True,
                max_intrinsic_service_bytes=max(row['service_bytes'] for row in entry['alignments']),
                max_example_IRQ_service_bytes=max(row['example_irq_inclusive_bytes'] for row in entry['alignments']))
            save();print('FULL complete',kind,entry['qualification'],flush=True)
        report['final_source_sha256_lf']=source_hashes()
        assert report['final_source_sha256_lf']==launch_sources,'F00 sources changed during proof'
        report.update(complete=True,raw_qualification_complete=True,
            decision='Three raw candidates passed complete correctness gates; public promotion and final frontier policy remain a separate integration step.')
        save()
    except BaseException as error:
        report['attempts'].append(dict(**current,error=repr(error),complete=False))
        report['failure']=dict(**current,error=repr(error))
        save();raise
    overview={key:value for key,value in report.items() if key not in ('baseline','baseline_binding','profiles','native_C')}
    overview['baseline']=dict(service_bytes=9499,real_tstates=14926306,regions=region_binding(baseline)['regions'])
    overview['native_C']=dict(dll_sha256=DLL_SHA,dll_path=str(dll),build_sha256=sha(dll.with_name('build.json').read_bytes()))
    overview['profiles']={name:dict(regions=row['regions'],metadata=row['metadata'],summary=row['summary'],qualification=row['qualification']) for name,row in report['profiles'].items()}
    overview['full_evidence']=dict(path=str(output.relative_to(ROOT)).replace('\\','/'),sha256=sha(output.read_bytes()))
    output.with_name('next_f00.json').write_text(json.dumps(overview,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({name:row['summary'] for name,row in report['profiles'].items()},sort_keys=True),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'libraries/evidence/next_f00_full.json.gz')
    main(parser.parse_args().output)
