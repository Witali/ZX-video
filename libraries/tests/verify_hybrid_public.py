"""Bind public LZSA2 hybrids/short options to complete frozen native proofs."""
import argparse
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
for package in ('lzsa','zx0'):sys.path.insert(0,str(ROOT/'libraries'/package/'src'))
from lzsa.hybrid import build as hybrid
from lzsa.wide import build as wide
from test_libraries import profiles


def sha(blob):return hashlib.sha256(blob).hexdigest()


def regions(profile):
    return [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wheel',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();evidence={}
    def read(name):
        blob=(ROOT/'libraries/evidence'/name).read_bytes();evidence[name]=sha(blob)
        return json.loads(gzip.decompress(blob) if name.endswith('.gz') else blob)
    vectors=read('wide_hybrid_experiment_selectors.json')
    basic=read('wide_hybrid/wide_hybrid_experiment.json.gz')
    short=read('wide_hybrid/wide_hybrid_experiment_short.json.gz')
    single=read('wide_short_experiment.json')
    archive=read('wide_hybrid_experiment_archives.json')
    for entry in archive['archives']:
        blob=(ROOT/'libraries/evidence'/entry['file']).read_bytes()
        assert sha(blob)==entry['sha256'] and sha(gzip.decompress(blob))==entry['decoded_sha256']
    blob=(ROOT/single['full_evidence']['path']).read_bytes()
    assert sha(blob)==single['full_evidence']['sha256']
    evidence[single['full_evidence']['path']]=sha(blob)
    calls=[]
    mapping={'compact-base':'basic-budget-3452','balanced-base':'basic-budget-4500',
        'fast-base':'basic-budget-5500','compact':'short-budget-5000',
        'balanced':'short-budget-6500','fast':'short-budget-9500'}
    for name,key in mapping.items():
        vector=vectors['profiles'][key]
        native=(basic if key.startswith('basic') else short)['profiles'][vector['report_profile']]
        assert native['finalist'] and native['all_case_hit_audit']['exact']
        assert len(native['full_blocks'])==95 and len(native['directed_blocks'])==580
        for origin,saved in ((0x8000,native['layout']),(0x9103,native['relocated_layout'])):
            profile=hybrid(name,core=origin)
            assert regions(profile)==saved['regions']
            assert profile[2]['service_memory_bytes']==saved['service_memory_bytes']
            assert profile[2]['group_counts']==vector['group_counts']
            assert profile[2]['shared_hit_tokens']==native['shared_hit_tokens']
        calls.append(dict(module='lzsa.hybrid',kwargs=dict(profile=name),
            regions=native['layout']['regions'],service_bytes=vector['service_memory_bytes'],
            real_cpu_tstates=vector['real_tstates'],regressions=vector['all_case_regressions']))
    for key,shared,lengths,repeats in (('shared-new-all',True,range(2,9),()),
        ('shared-new-all-repeat-4to8',True,range(2,9),range(4,9)),
        ('new-3to8',False,range(3,9),()),('new-all',False,range(2,9),())):
        saved=single['profiles'][key]
        kwargs=dict(shared_literals=shared,short_lengths=list(lengths),repeat_lengths=list(repeats))
        for origin,field in ((0x8000,'candidate'),(0x9000,'aligned_relocated')):
            profile=wide(core=origin,**kwargs)
            assert regions(profile)==saved[field]['regions']
            assert profile[2]['service_memory_bytes']==saved[field]['service_memory_bytes']
        if key=='new-all':
            try:wide(core=0x9003,**kwargs)
            except ValueError:pass
            else:raise AssertionError('oversize full-new alignment accepted')
        else:assert regions(wide(core=0x9003,**kwargs))==saved['unaligned_relocated']['regions']
        calls.append(dict(module='lzsa.wide',kwargs=kwargs,regions=saved['candidate']['regions'],
            service_bytes=saved['candidate']['service_memory_bytes'],
            real_cpu_tstates=saved['summary']['real_candidate_tstates'],
            regressions=saved['summary']['slower_blocks']))
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    logs={}
    for filename in ('hybrid-library-tests.log','hybrid-toolkit-tests.log','hybrid-wheel.log'):
        raw=(ROOT/'.tmp'/filename).read_bytes();text=raw.decode()
        if 'tests' in filename:
            assert '\nOK' in text and not re.search(r'\n(?:FAILED|ERROR)',text)
            count=int(re.search(r'Ran (\d+) tests',text)[1])
            if 'library' in filename:assert count==61
        else:count=None
        dest=ROOT/'libraries/evidence/hybrid_public';dest.mkdir(exist_ok=True)
        compressed=gzip.compress(raw,mtime=0);(dest/(filename+'.gz')).write_bytes(compressed)
        logs[filename]=dict(tests=count,sha256=sha(compressed),decoded_sha256=sha(raw))
    with tempfile.TemporaryDirectory(dir=ROOT/'.tmp',prefix='hybrid-wheel-') as temporary:
        target=Path(temporary);install=target/'installed';install.mkdir()
        with zipfile.ZipFile(args.wheel) as wheel:
            assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in wheel.namelist())
            wheel.extractall(install)
        inputs=target/'calls.json';inputs.write_text(json.dumps(calls))
        child="""import importlib,json,hashlib,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from lzsa.export import export
calls=json.loads(Path(sys.argv[2]).read_text());rows=[]
for index,row in enumerate(calls):
    result=importlib.import_module(row['module']).build(**row['kwargs'])
    regs=[dict(address=at,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()) for at,blob in result[0]]
    assert regs==row['regions'] and result[2]['service_memory_bytes']==row['service_bytes']
    dest=Path(sys.argv[3])/str(index);export(dest,*result);restored=[]
    for line in (dest/'decoder.asm').read_text().splitlines():
        if line.startswith('org '):restored.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):restored[-1][1].extend(int(v[1:],16) for v in line[3:].split(','))
    assert [(at,bytes(data)) for at,data in restored]==result[0]
    rows.append(dict(module=row['module'],kwargs=row['kwargs'],regions=regs))
assert not any(name=='z80' or name=='toolkit' or name.startswith('numpy') for name in sys.modules)
print(json.dumps(rows))
"""
        result=subprocess.run([sys.executable,'-I','-c',child,str(install),str(inputs),str(target/'exports')],
            check=True,capture_output=True,text=True)
        smoke=json.loads(result.stdout);assert len(smoke)==10
    sources=list((ROOT/'libraries/lzsa/src/lzsa').glob('*.py'))
    sources += [Path(__file__),ROOT/'libraries/tests/test_hybrid_profiles.py']
    result=dict(date=date.today().isoformat(),complete=True,release=False,resident_only=True,
        current_public_calls=calls,isolated_wheel_exports=len(smoke),wheel_sha256=sha(args.wheel.read_bytes()),
        evidence_sha256=evidence,archived_logs=logs,legacy_profiles_exact=31,
        source_sha256_lf={str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes().replace(b'\r\n',b'\n')) for path in sources},
        existing_default_instruction_delta_tstates=0,payload_delta_bytes=0,
        native_evidence_reused_without_relabeling=True,
        exclusions=['coroutine/guarded input','physical disk/ROM','ULA/WAIT','movie publication'])
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,public_calls=10,isolated_wheel_exports=10,
        library_tests=61,toolkit_tests=logs['hybrid-toolkit-tests.log']['tests'])))


if __name__=='__main__':main()
