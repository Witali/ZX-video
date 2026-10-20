"""Bounded S01 Small audit: guarded screen, exact delta model, useful6mode.

All per-block initialization is in the measured entry-to-RET interval. There
is no separate required target preparation, state table or scratch buffer.
The independent model observes the unchanged Small decoder on kosarev.
"""
import argparse
from collections import Counter
from datetime import date
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
for path in (ROOT/'libraries/lzsa/src',ROOT/'libraries/zx0/src',ROOT/'libraries/tests',ROOT):
    sys.path.insert(0,str(path))

from next_s01_lzsa_profiles import KINDS,EXPECTED_STACK,build
from next_f00_measure import PROTECTED,dirty
from native_inplace_block import execute as inplace
from next_e02_profiles import extra_word_cases
from next_e03_measure import region_binding,read_gzip,sha,DLL_SHA
from measure_long_copy import samples
from measure_full_token_dispatch import directed_tokens
from emulator.cpu import load_library,execute_block
from lzsa import decompress
import z80


class Observer:
    """Count unchanged nibble call contexts and actual carry-word/EOF exits."""
    def __init__(self,profile):
        self.labels=profile[1];listing=profile[2]['instruction_listing']
        self.returns={row['address']+3:('length' if row['address']==self.labels['ExtendedCode'] else 'offset')
            for row in listing if row['instruction'] in ('CALL ReadNibble','CALL NibbleSkipC')}
        self.word_branch=next(row['address'] for row in listing if row['instruction']=='JR WordLength')
        self.watch={self.labels['NibbleSkipC']:self.nibble,self.word_branch:self.extended,
            self.labels['start']:self.start,self.labels['ReadToken']:self.token}
        self.counts=Counter();self.first_token=None;self.started=None

    def start(self,m):self.started=m.ticks_to_stop

    def token(self,m):
        if self.first_token is None:self.first_token=m.ticks_to_stop

    def nibble(self,m):
        returned=m.memory[m.sp]|(m.memory[m.sp+1]<<8)
        context=self.returns[returned]
        phase='cached' if m.alt_af&0x80 else 'refill'
        self.counts[context+'_'+phase]+=1

    def extended(self,m):
        assert m.f&1
        self.counts['eof' if m.f&0x40 else 'word']+=1

    def finish(self):
        assert self.counts['eof']==1
        assert self.started-self.first_token==24
        return dict(counts=dict(self.counts),per_block_setup_tstates=24,
            required_external_initialization_tstates=0)


def model(kind,counts):
    delta=0
    if kind in ('eof_stack','combined'):delta+=14*counts.get('word',0)-6*counts['eof']
    if kind in ('tagged','combined'):
        delta+=18*counts.get('offset_cached',0)+14*counts.get('offset_refill',0)
        delta-=9*counts.get('length_cached',0)+13*counts.get('length_refill',0)
    return delta


def state_exhaustion():
    """Exhaust tags/normalization over the entire token, phase and flag domain.

    Hardware instruction/guard coverage is separate. This finite model checks
    the layout's discriminator and every preserved token field. All AF' bits
    except S may vary, including undocumented flags; they do not classify tags.
    """
    count=0
    for token in range(256):
        cls=token>>5
        for flags in range(256):
            phase='cached' if flags&0x80 else 'refill'
            for nibble in range(16):
                a=0xf0|nibble
                if cls in (0,1):
                    c=(0xff-1)&255
                    assert c&128 and a==0xf0+nibble
                if cls in (4,5):
                    saved=(token+1)&255;c=(saved-1)&255
                    assert c==token and c&128
                    assert c&7==token&7 and ((c>=160)==(token>=160))
                for base in (3,9):
                    c=base-1
                    assert not c&128
                    if nibble<15:assert ((a+1-240+c)&255)==base+nibble
                    assert 16+c==15+base
                assert phase in ('cached','refill')
                count+=1
    return dict(complete=True,token_phase_nibble_flag_states=count,
        tokens=256,alternate_flag_values=256,nibbles=16,
        boundary_tokens=[0,31,32,63,128,159,160,191],
        scope='Analytical tag/arithmetic exhaust; native guarded cases separately execute emitted instructions.')


def source_hashes():
    names=('libraries/tests/next_s01_lzsa_profiles.py','libraries/tests/next_s01_lzsa_measure.py',
        'libraries/tests/next_s01_lzsa_tests.py','libraries/lzsa/src/lzsa/compact.py',
        'libraries/lzsa/src/lzsa/_z80.py','libraries/lzsa/src/lzsa/codec.py',
        'libraries/tests/native_block.py','libraries/tests/native_inplace_block.py',
        'libraries/tests/next_f00_measure.py','libraries/tests/next_e02_profiles.py',
        'libraries/tests/measure_long_copy.py','libraries/tests/measure_full_token_dispatch.py','emulator/cpu.py')
    return {name:sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n')) for name in names}


def alignment(kind):
    rows=[]
    for low in range(256):
        p=build(kind,core=0x8000+low)
        assert p[2]['service_memory_bytes']==build(kind)[2]['service_memory_bytes']
        rows.append(dict(low_byte=low,**region_binding(p),example_irq_inclusive_bytes=p[2]['service_memory_bytes']+19))
    return rows


def summarize(rows):
    real=[row for row in rows if row['real']]
    slower=[dict(case=row['case'],real=row['real'],delta_tstates=row['delta_tstates']) for row in rows if row['delta_tstates']>0]
    return dict(cases=len(rows),real_cases=len(real),real_tstates=sum(row['c_guarded']['tstates'] for row in real),
        real_delta_tstates=sum(row['delta_tstates'] for row in real),
        faster_cases=sum(row['delta_tstates']<0 for row in rows),equal_cases=sum(row['delta_tstates']==0 for row in rows),
        slower_cases=slower,slower_real_cases=sum(row['real'] for row in slower),
        maximum_regression_tstates=max([row['delta_tstates'] for row in slower] or [0]))


def native_modes(profile,moved,payload,raw,expected_cpu):
    result={};limit=profile[2]['caller_stack_bytes']
    for name,p,irq,overlap in (
        ('plain',profile,False,False),('irq',profile,True,False),('relocated',moved,False,False),
        ('inplace_plain',profile,False,True),('inplace_irq',profile,True,True),('inplace_relocated',moved,False,True)):
        got=inplace(p,payload,raw,codec='lzsa2',interrupts=irq) if overlap else PROTECTED(dirty(p),payload,raw,interrupts=irq,alternate_af=0x9797)
        if not irq:assert got['tstates']==expected_cpu,(name,got['tstates'],expected_cpu)
        assert got['stack_bytes']<=limit+(6 if irq else 0),(name,limit,got)
        if overlap:
            assert got['host_read_order_exact'] and got['code_protected'] and got['raw_abi_exact']
            assert got['host_minimum_input_start']==got['native_minimum_input_start']
        result[name]=got
    return result


def extra_cases():
    yield from (row[:3] for row in extra_word_cases())
    for phase in ('cached','refill'):
        for n in (2,3):
            prefix=bytes.fromhex('0f41ffe9' if phase=='cached' else '4f41ffffe9')
            suffix=bytes.fromhex('e7f0e8' if phase=='cached' else 'e7e8')
            payload=prefix+n.to_bytes(2,'little')+suffix;raw=b'A'*(n+1)
            assert decompress(payload,limit=len(raw))==raw
            yield f'extra-word-match-{n}-{phase}',payload,raw


def main(output):
    output=Path(output).resolve();library=load_library();dll=Path(library._name)
    assert sha(dll.read_bytes())==DLL_SHA
    sources=source_hashes();baseline=build()
    cases=list(samples())+[row[:3] for row in directed_tokens()]
    assert len(cases)==675
    frozen=read_gzip('next_e00_lzsa_full.json.gz')['profiles']['fast']['blocks']
    assert [row[0] for row in cases]==[row['case'] for row in frozen]
    extras=list(extra_cases())
    assert len(extras)==8
    assert any(name=='word-match-2' for name,_,_ in cases)
    backend_files=[Path(z80.__file__)]+sorted(Path(z80.__file__).parent.glob('*.pyd'))
    report=dict(date=date.today().isoformat(),stage='S01 LZSA2',complete=False,release=False,
        public_changes=False,baseline_revision='2d998229',launch_source_sha256_lf=sources,
        baseline=region_binding(baseline),state_exhaustion=state_exhaustion(),
        C=dict(dll_path=str(dll),dll_sha256=DLL_SHA,build=json.loads(dll.with_name('build.json').read_text())),
        kosarev_files={str(path):sha(path.read_bytes()) for path in backend_files},
        C_qualification_proof_sha256={name:sha((ROOT/'emulator/evidence'/name).read_bytes()) for name in ('verification.json','native_build.json')},
        baseline_binding=[],supplemental_baseline=[],profiles={},attempts=[],
        timing_scope='Complete entry-to-RET deterministic CPU, including24T per-block setup; required external target initialization0T. Cold-start equals complete block total; batch equals sum, no free preparation.',
        service_scope='Code including embedded2B mutable offset + maximum caller/decoder stack; input/output/history excluded; tables/alignment/scratch/internal buffers0.',
        unperformed=['Public package/API/export/wheel integration','Coroutine/quota/input readiness','Spectrum contention/ROM/disk/movie release'])
    def save():
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_bytes(gzip.compress((json.dumps(report,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0))
    current={}
    try:
        save()
        for index,((name,payload,raw),golden) in enumerate(zip(cases,frozen)):
            current=dict(stage='baseline C+kosarev',index=index,case=name)
            assert sha(payload)==golden['payload_sha256'] and sha(raw)==golden['raw_sha256']
            observer=Observer(baseline)
            independent=PROTECTED(dirty(baseline),payload,raw,watch=observer.watch,alternate_af=0x9797)
            c=execute_block(baseline,payload,raw,library=library)
            assert independent['tstates']==c['tstates'] and independent['stack_bytes']==c['stack_bytes']
            row=dict(case=name,real=name.startswith('real-'),payload_sha256=sha(payload),raw_sha256=sha(raw),
                payload_bytes=len(payload),raw_bytes=len(raw),c_guarded=c,kosarev=independent,oracle=observer.finish())
            report['baseline_binding'].append(row)
            if index%100==99:save();print('baseline',index+1,flush=True)
        report['baseline_summary']=dict(real_tstates=sum(r['c_guarded']['tstates'] for r in report['baseline_binding'] if r['real']),
            maximum_stack_bytes=max(r['c_guarded']['stack_bytes'] for r in report['baseline_binding']),
            first_real_cold_start_tstates=next(r['c_guarded']['tstates'] for r in report['baseline_binding'] if r['real']),
            all_case_batch_tstates=sum(r['c_guarded']['tstates'] for r in report['baseline_binding']),
            per_block_setup_tstates=24,required_one_time_external_initialization_tstates=0)
        print('baseline summary',report['baseline_summary'],flush=True)
        for name,payload,raw in extras:
            observer=Observer(baseline)
            got=PROTECTED(dirty(baseline),payload,raw,watch=observer.watch,alternate_af=0x9797)
            c=execute_block(baseline,payload,raw,library=library);assert got['tstates']==c['tstates']
            report['supplemental_baseline'].append(dict(case=name,payload_sha256=sha(payload),raw_sha256=sha(raw),
                c_guarded=c,kosarev=got,oracle=observer.finish()))
        for kind in KINDS:
            p,moved=build(kind),build(kind,core=0x9103)
            entry=dict(**region_binding(p),relocated=region_binding(moved),alignments=alignment(kind),
                C_complete=False,native_complete=False,blocks=[],supplemental=[])
            report['profiles'][kind]=entry
            for index,((name,payload,raw),old) in enumerate(zip(cases,report['baseline_binding'])):
                current=dict(stage='C screen',profile=kind,index=index,case=name)
                c=execute_block(p,payload,raw,library=library);delta=model(kind,old['oracle']['counts'])
                assert c['tstates']==old['c_guarded']['tstates']+delta,(kind,name,c,old,delta)
                assert c['stack_bytes']<=EXPECTED_STACK[kind]
                entry['blocks'].append(dict(case=name,real=old['real'],delta_tstates=delta,model_exact=True,c_guarded=c))
                if index%100==99:print('C screen',kind,index+1,flush=True)
            for (name,payload,raw),old in zip(extras,report['supplemental_baseline']):
                c=execute_block(p,payload,raw,library=library);delta=model(kind,old['oracle']['counts'])
                assert c['tstates']==old['c_guarded']['tstates']+delta,(kind,name,c,delta)
                entry['supplemental'].append(dict(case=name,delta_tstates=delta,model_exact=True,c_guarded=c))
            entry['summary']=summarize(entry['blocks']);entry['C_complete']=True
            print('screen summary',kind,json.dumps({k:v for k,v in entry['summary'].items() if k!='slower_cases'}),flush=True);save()
        # Native6mode is reserved for nondominated points after the bounded
        # actual-emission/C screen. Equal service and slower realCPU rejects.
        baseline_cpu=report['baseline_summary']['real_tstates'];baseline_service=baseline[2]['service_memory_bytes']
        points={'baseline':(baseline_service,baseline_cpu)}
        points.update({k:(build(k)[2]['service_memory_bytes'],v['summary']['real_tstates']) for k,v in report['profiles'].items()})
        for kind,entry in report['profiles'].items():
            own=points[kind]
            dominators=[k for k,p in points.items() if k!=kind and p[0]<=own[0] and p[1]<=own[1] and p!=own]
            entry['screen_dominators']=dominators
            if dominators:
                entry['decision']='rejected: dominated in complete real CPU/service screen';continue
            p,moved=build(kind),build(kind,core=0x9103)
            for index,((name,payload,raw),row) in enumerate(zip(cases,entry['blocks'])):
                current=dict(stage='protected6mode',profile=kind,index=index,case=name)
                row['protected']=native_modes(p,moved,payload,raw,row['c_guarded']['tstates'])
                if index%50==49:save();print('protected6mode',kind,index+1,flush=True)
            for (name,payload,raw),row in zip(extras,entry['supplemental']):
                row['protected']=native_modes(p,moved,payload,raw,row['c_guarded']['tstates'])
            selected=[cases[0],next(case for case in cases if case[0]=='single-nibble-eof-one'),next(case for case in cases if case[0]=='word-literal-1')]
            entry['FFFF_output_cursor_probes']=[]
            for name,payload,raw in selected:
                expected=next(r['c_guarded']['tstates'] for r in entry['blocks'] if r['case']==name)
                modes={}
                for mode,profile,irq in [('plain',p,False),('irq',p,True),('relocated',moved,False)]:
                    got=PROTECTED(dirty(profile),payload,raw,output=0xffff-len(raw),interrupts=irq,alternate_af=0x9797)
                    if not irq:assert got['tstates']==expected
                    modes[mode]=got
                entry['FFFF_output_cursor_probes'].append(dict(case=name,output_cursor=65535,modes=modes))
            entry['native_complete']=True
            allrows=entry['blocks']+entry['supplemental']
            entry['qualification']=dict(complete=True,frozen_cases=675,supplemental_cases=len(extras),
                native_configs=len(allrows)*6,FFFF_configs=9,
                maximum_plain_stack_bytes=max(r['protected']['plain']['stack_bytes'] for r in allrows),
                maximum_irq_stack_bytes=max(r['protected']['irq']['stack_bytes'] for r in allrows),
                maximum_inplace_irq_stack_bytes=max(r['protected']['inplace_irq']['stack_bytes'] for r in allrows))
            entry['decision']='useful nondominated raw candidate; public integration not performed';save()
        assert source_hashes()==sources
        report['final_source_sha256_lf']=source_hashes();report['complete']=True;save()
        summary={k:v for k,v in report.items() if k not in ('baseline_binding','supplemental_baseline','profiles')}
        summary['full_report']=dict(path=str(output.relative_to(ROOT)).replace('\\','/'),sha256=sha(output.read_bytes()))
        summary['profiles']={k:dict(service_bytes=build(k)[2]['service_memory_bytes'],code_bytes=build(k)[2]['code_bytes'],
            caller_stack_bytes=EXPECTED_STACK[k],summary=v['summary'],decision=v['decision'],
            screen_dominators=v['screen_dominators'],native_complete=v['native_complete'],qualification=v.get('qualification'))
            for k,v in report['profiles'].items()}
        # Keep full slower lists in gzip and compact count/max in the overview.
        for item in summary['profiles'].values():
            item['summary']['slower_case_count']=len(item['summary'].pop('slower_cases'))
        output.with_name('next_s01_lzsa.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
        print('COMPLETE',json.dumps(summary['profiles']),flush=True)
    except BaseException as error:
        report['attempts'].append(dict(current=current,error=repr(error),complete=False));save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)
