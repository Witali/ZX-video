"""Emit and reject three bounded LL3 continuation alternatives.

The qualified C flat guarded API screens all675 frozen inputs. Its current
baseline is bound case-by-case to E01's original kosarev CPU proof; independent
E00 helper-path counts predict every candidate delta. Four small word-literal
cases additionally run both CPU backends. No rejected option is promoted.
"""
import argparse
import ast
from collections import Counter
from datetime import date
import gzip
import json
from pathlib import Path
import subprocess

from next_e02_profiles import ROOT,KINDS,build,transformed_source,extra_word_cases
from measure_long_copy import samples,sha
from measure_full_token_dispatch import directed_tokens
from profile_branch_mix import instructions
from profile_next_lzsa import Observer
from native_block import execute as independent
from lzsa.hybrid import build as public
from emulator.cpu import load_library,execute_block


def read(path):
    blob=path.read_bytes()
    return json.loads(gzip.decompress(blob) if path.suffix=='.gz' else blob)


def regions(profile):
    return [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]]


def layout(profile):
    origin,blob=profile[0][0];labels=profile[1]
    branches=[]
    for at,op in instructions(blob[labels['start']-origin:],labels['start']):
        if op[0] in (0x18,0x20,0x28,0x30,0x38):
            span=int.from_bytes(op[1:],'little',signed=True)
            assert -128<=span<=127
            branches.append(dict(address=at,opcode_hex=op.hex(),span=span,target=at+2+span))
    return dict(regions=regions(profile),labels=labels,metadata=profile[2],relative_branches=branches)


def model(kind,paths,clone):
    if kind=='direct-hl':return 19*sum(paths.values())
    if kind=='hot-clone':return -27*clone['nibble']+10*(clone['byte']+clone['word'])
    if kind=='shared-tail':return 12*(paths['byte']+paths['word'])
    raise ValueError('unknown construction')


def helper_counts(row):
    paths=Counter();clone=Counter()
    for encoded,count in row['observers']['ll3_context_paths'].items():
        call,context,path=ast.literal_eval(encoded)
        paths[path]+=count
        if context=='body_224_1':clone[path]+=count
    return paths,clone


def summary(rows):
    real=[row for row in rows if row['real']]
    slower=[dict(case=row['case'],real=row['real'],delta_tstates=row['delta_tstates']) for row in rows if row['delta_tstates']>0]
    return dict(cases=len(rows),real_cases=len(real),baseline_real_tstates=sum(row['baseline_tstates'] for row in real),
        candidate_real_tstates=sum(row['candidate_tstates'] for row in real),
        real_delta_tstates=sum(row['delta_tstates'] for row in real),
        all_delta_tstates=sum(row['delta_tstates'] for row in rows),
        faster_cases=sum(row['delta_tstates']<0 for row in rows),equal_cases=sum(row['delta_tstates']==0 for row in rows),
        slower_count=len(slower),slower_real_count=sum(row['real'] for row in slower),
        maximum_regression_tstates=max([row['delta_tstates'] for row in slower]+[0]),slower_cases=slower,
        maximum_stack_bytes=max(row['native']['stack_bytes'] for row in rows),
        per_case_model_exact=True,guards_output_eof_registers_code_exact=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--dll',type=Path,default=ROOT/'.tmp/codec-cpu-qualified/codec_cpu.dll',
        help='Use the separately qualified native build, not the unqualified default alias.')
    args=parser.parse_args();output=args.output.resolve()
    e00_path=ROOT/'libraries/evidence/next_e00_lzsa_full.json.gz'
    e01_summary_path=ROOT/'libraries/evidence/next_e01_lzsa.json'
    e01_summary=read(e01_summary_path)
    e01_path=ROOT/e01_summary['full_evidence']['path']
    assert sha(e01_path.read_bytes())==e01_summary['full_evidence']['sha256']
    e00=read(e00_path)['profiles']['fast']
    e01=read(e01_path)['profiles']['hybrid-fast']
    assert e01['complete'] and e01['accepted']
    baseline=public('fast',cold_match_extension=True)
    assert regions(baseline)==e01['candidate']['regions'] and baseline[1]==e01['candidate']['labels']
    assert baseline[2]==e01['candidate']['metadata']
    golden={row['case']:row for row in e01['blocks']}
    oracle={row['case']:row for row in e00['blocks']}
    qualification_path=ROOT/'emulator/evidence/verification.json'
    build_path=ROOT/'emulator/evidence/native_build.json'
    qualification=read(qualification_path);native_build=read(build_path)
    assert qualification['complete'] and qualification['compiled_sources_exact']
    assert sha(build_path.read_bytes())==qualification['artifacts']['native_build.json']['sha256']
    library=load_library(args.dll);dll=Path(library._name)
    assert sha(dll.read_bytes())==native_build['dll_sha256'] and library.codec_cpu_abi_version()==2
    source_paths=('libraries/lzsa/src/lzsa/wide.py','libraries/lzsa/src/lzsa/hybrid.py',
        'libraries/lzsa/src/lzsa/_wide_kernels.py','libraries/lzsa/src/lzsa/_z80.py',
        'libraries/lzsa/src/lzsa/codec.py','libraries/tests/next_e02_profiles.py',
        'libraries/tests/next_e02_measure.py','libraries/tests/next_e02_tests.py',
        'libraries/tests/profile_next_lzsa.py','libraries/tests/native_block.py',
        'libraries/tests/profile_branch_mix.py','emulator/cpu.py','libraries/Z80_TIMINGS.md')
    source_hashes={path:sha((ROOT/path).read_bytes().replace(b'\r\n',b'\n')) for path in source_paths}
    report=dict(date=date.today().isoformat(),stage='E02',complete=False,accepted=False,release=False,
        baseline_revision='9fbd9ce7',observation_head=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip(),
        public_changes=0,source_sha256_lf=source_hashes,
        evidence_sha256={str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes()) for path in
            (e00_path,e01_path,e01_summary_path,qualification_path,build_path)},
        backend=dict(name='qualified z80-tester C flat guarded',dll_sha256=sha(dll.read_bytes()),
            dll_path=str(dll.relative_to(ROOT)).replace('\\','/'),
            abi=library.codec_cpu_abi_version(),build_source_sha256_lf=native_build['source_sha256_lf'],
            qualification='emulator/evidence/verification.json',contention=False),
        baseline=layout(baseline),baseline_binding=[],profiles={},
        helper_exit_model=dict(bytes=45,call_sites=64,returns=3,return_offsets=[27,37,44],
            real_calls=4870,real_paths=dict(nibble=4701,byte=169,word=0),
            call_tstates=17,ret_tstates=10,real_call_ret_tstates=131490,
            stack_bytes=6,stack_floor='caller return2 + saved caller HLprime2 + unchanged match PUSHHL2; removing helper return words cannot reduce total peak',
            direct_hl=dict(call_to_jp_delta_tstates=-7,return_sequence='EXX;INC HL;INC HL;INC HL;INC HL;JP(HL)',
                return_sequence_bytes=6,return_sequence_tstates=32,continuation_exx_bytes=1,continuation_exx_tstates=4,
                service_delta_bytes=79,per_call_delta_tstates=19),
            hot_clone=dict(token=248,context='body_224_1',inline_hot_bytes=27,cold_call_jump_bytes=6,
                replaced_call_bytes=3,service_delta_bytes=30,nibble_delta_tstates=-27,cold_delta_tstates=10,
                optimistic_growth_floor_bytes=24),
            shared_tail=dict(replaced_cold_suffix_bytes=3,jr_bytes=2,service_delta_bytes=-2,
                nibble_delta_tstates=0,cold_delta_tstates=12),
            clone_plus_tail_lower_service_delta_bytes=28),
        setup_note='An initial attempt used the unusable unqualified default DLL alias and stopped before any replay; the explicit qualified DLL is authenticated here.',
        preliminary_run_note='An initial screen was interrupted after baseline675 and two candidate675 sets to correct inherited nominal/variant metadata. Target instruction substitutions were unchanged; the final complete matrix below was rerun with correct test-only metadata.',
        unperformed=['IRQ/in-place/relocated runtime promotion matrix: every candidate fails speed+service acceptance',
            'coroutine/guarded input wrappers','physical disk/ROM/ULA/movie timing'])
    cases=[(name,payload,raw) for name,payload,raw in samples()]+[row[:3] for row in directed_tokens()]
    assert len(cases)==675
    baselines={};counts={}
    for name,payload,raw in cases:
        assert sha(payload)==golden[name]['payload_sha256']==oracle[name]['payload_sha256']
        assert sha(raw)==golden[name]['raw_sha256']==oracle[name]['raw_sha256']
        result=execute_block(baseline,payload,raw,library=library)
        assert result['tstates']==golden[name]['candidate_tstates'],('C baseline differs from kosarev E01',name)
        baselines[name]=result;counts[name]=helper_counts(oracle[name])
        report['baseline_binding'].append(dict(case=name,real=name.startswith('real-'),payload_sha256=sha(payload),raw_sha256=sha(raw),
            tstates=result['tstates'],kosarev_e01_tstates=golden[name]['candidate_tstates'],exact=True))
    assert sum(row['tstates'] for name,row in baselines.items() if name.startswith('real-'))==14926306
    print('C baseline675 matches E01 kosarev exactly',flush=True)
    supplemental=[]
    for name,payload,raw,phase in extra_word_cases():
        observer=Observer(baseline);observer.reset()
        original=independent(baseline,payload,raw,watch=observer.watch)
        observed=observer.finish(original)
        old=execute_block(baseline,payload,raw,library=library)
        assert old['tstates']==original['tstates']
        paths,clone=helper_counts(dict(observers=observed))
        assert paths==Counter(word=1) and clone==Counter(word=1)
        assert observer.cache[baseline[1]['LongLiterals']+2,phase]==1
        supplemental.append((name,payload,raw,phase,paths,clone,old['tstates']))
    expected_sizes={'direct-hl':79,'hot-clone':30,'shared-tail':-2}
    for kind in KINDS:
        candidate=build(kind);alignments=[]
        for low in range(256):
            old=public('fast',core=0x8000+low,cold_match_extension=True)
            new=build(kind,core=0x8000+low)
            item=layout(new)
            delta=new[2]['service_memory_bytes']-old[2]['service_memory_bytes']
            assert delta==expected_sizes[kind] and new[2]['caller_stack_bytes']==6
            assert new[0][0][1][new[1]['MatchUseC']-new[0][0][0]]==0xe5
            alignments.append(dict(low=low,core=0x8000+low,service_delta_bytes=delta,
                service_bytes=new[2]['service_memory_bytes'],example_irq_inclusive_bytes=new[2]['service_memory_bytes']+19,
                alignment_padding=new[2]['alignment_padding'],regions=item['regions'],labels=new[1],relative_branches=item['relative_branches']))
        rows=[]
        for name,payload,raw in cases:
            paths,clone=counts[name];expected=model(kind,paths,clone)
            result=execute_block(candidate,payload,raw,library=library)
            assert result['tstates']-baselines[name]['tstates']==expected,(kind,name,expected,result['tstates']-baselines[name]['tstates'])
            assert result['stack_bytes']<=6
            rows.append(dict(case=name,real=name.startswith('real-'),payload_sha256=sha(payload),raw_sha256=sha(raw),
                baseline_tstates=baselines[name]['tstates'],candidate_tstates=result['tstates'],delta_tstates=expected,
                paths=dict(paths),clone_paths=dict(clone),native=result))
        extras=[]
        for name,payload,raw,phase,paths,clone,old in supplemental:
            new=execute_block(candidate,payload,raw,library=library)
            reference=independent(candidate,payload,raw)
            assert new['tstates']==reference['tstates'] and new['tstates']-old==model(kind,paths,clone)
            extras.append(dict(case=name,phase=phase,payload_sha256=sha(payload),raw_sha256=sha(raw),
                baseline_tstates=old,candidate_tstates=new['tstates'],delta_tstates=new['tstates']-old,
                c_guarded=new,kosarev=reference,exact=True))
        totals=summary(rows)
        memory_delta=candidate[2]['service_memory_bytes']-baseline[2]['service_memory_bytes']
        passes=memory_delta<0 and totals['real_delta_tstates']<0
        assert not passes
        report['profiles'][kind]=dict(layout=layout(candidate),transformed_source_sha256=sha(transformed_source(kind).encode()),
            alignments=alignments,blocks=rows,supplemental=extras,summary=totals,service_delta_bytes=memory_delta,
            accepted=False,decision='reject: service grows' if memory_delta>0 else 'reject: real decode CPU grows',
            stack_accounting='six bytes retained; actual observed peak6 and unchanged match PUSHHL require it')
        print(kind,json.dumps(dict(service_delta_bytes=memory_delta,**{key:value for key,value in totals.items() if key!='slower_cases'})),flush=True)
    assert all(sha((ROOT/path).read_bytes().replace(b'\r\n',b'\n'))==digest for path,digest in source_hashes.items())
    report.update(complete=True,accepted=False,decision='All three bounded constructions rejected; keep E01 public decoder unchanged.',
        c_baseline_frozen_cases=675,c_candidate_frozen_cases=2025,c_supplemental_cases=16,kosarev_supplemental_cases=16,
        public_sources_unchanged=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    archive=output.with_name(output.stem+'_full.json.gz')
    archive.write_bytes(gzip.compress((json.dumps(report,indent=2)+'\n').encode(),mtime=0))
    overview={key:value for key,value in report.items() if key not in ('profiles','baseline_binding','baseline')}
    overview['baseline']=dict(regions=regions(baseline),service_memory_bytes=baseline[2]['service_memory_bytes'],real_tstates=14926306)
    overview['profiles']={kind:dict(service_bytes=item['layout']['metadata']['service_memory_bytes'],
        service_delta_bytes=item['service_delta_bytes'],accepted=False,decision=item['decision'],
        summary={key:value for key,value in item['summary'].items() if key!='slower_cases'},
        all256_alignments=True,maximum_irq_inclusive_bytes=max(row['example_irq_inclusive_bytes'] for row in item['alignments']))
        for kind,item in report['profiles'].items()}
    overview['full_evidence']=dict(path=str(archive.relative_to(ROOT)).replace('\\','/'),sha256=sha(archive.read_bytes()))
    output.write_text(json.dumps(overview,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
