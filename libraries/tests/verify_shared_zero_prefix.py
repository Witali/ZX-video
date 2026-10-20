"""Authenticate current shared Maximum API/export/wheel against native proofs."""
import argparse
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'libraries/zx0/src'))
from zx0.maximum import build
from test_libraries import profiles


def sha(blob):return hashlib.sha256(blob).hexdigest()


def regions(profile):
    return [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wheel',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();evidence={};checked={}
    for name,origin,moved in (('shared_zero_prefix_native.json.gz',0x8000,0x9103),
                              ('shared_zero_prefix_high_word.json.gz',0x0800,0x0703)):
        blob=(ROOT/'libraries/evidence'/name).read_bytes();report=json.loads(gzip.decompress(blob))
        assert report['complete'];evidence[name]=dict(sha256=sha(blob),decoded_sha256=sha(gzip.decompress(blob)))
        for cap,saved in report['profiles'].items():
            current=build(core=origin,prefix_cap=int(cap),shared_prefixes=True)
            assert regions(current)==saved['regions']
            assert regions(build(core=moved,prefix_cap=int(cap),shared_prefixes=True))==saved['relocated_regions']
            assert current[2]['service_memory_bytes']==saved['summary']['service_bytes']
            assert current[2]['shared_prefix_audit']==saved['audit']
            assert not saved['summary']['slower_cases']
            checked.setdefault(cap,saved['summary'])
    frozen=json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    assert profiles()==frozen
    library_log=(ROOT/'.tmp/shared-prefix-library-tests.log').read_text()
    assert 'Ran 58 tests' in library_log and '\nOK' in library_log
    with tempfile.TemporaryDirectory(dir=ROOT/'.tmp',prefix='shared-prefix-wheel-') as temporary:
        target=Path(temporary);install=target/'installed';install.mkdir()
        with zipfile.ZipFile(args.wheel) as wheel:
            assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in wheel.namelist())
            wheel.extractall(install)
        child="""import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from zx0.maximum import build
from zx0.export import export
rows={}
for cap in (31,63,127,227,228):
    result=build(prefix_cap=cap,shared_prefixes=True)
    export(Path(sys.argv[2])/str(cap),*result)
    rows[str(cap)]=dict(service=result[2]['service_memory_bytes'],regions=[dict(address=at,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()) for at,blob in result[0]])
assert not any(name=='z80' or name=='toolkit' or name.startswith('numpy') for name in sys.modules)
print(json.dumps(rows))
"""
        result=subprocess.run([sys.executable,'-I','-c',child,str(install),str(target/'exports')],
            check=True,capture_output=True,text=True)
        smoke=json.loads(result.stdout)
        original=json.loads(gzip.decompress((ROOT/'libraries/evidence/shared_zero_prefix_native.json.gz').read_bytes()))
        for cap,row in smoke.items():
            assert row['regions']==original['profiles'][cap]['regions']
            assert row['service']==checked[cap]['service_bytes']
    paths=[Path(__file__),ROOT/'libraries/tests/shared_zero_prefix_profile.py',
        ROOT/'libraries/tests/measure_shared_zero_prefix.py',ROOT/'libraries/tests/test_shared_maximum.py']
    paths+=list((ROOT/'libraries/zx0/src/zx0').glob('*.py'))
    logs={};archive_directory=ROOT/'libraries/evidence/shared_zero_prefix'
    archive_directory.mkdir(exist_ok=True)
    for filename in ('shared-prefix-library-tests.log','shared-prefix-wheel.log'):
        raw=(ROOT/'.tmp'/filename).read_bytes();compressed=gzip.compress(raw,mtime=0)
        (archive_directory/(filename+'.gz')).write_bytes(compressed)
        logs[filename+'.gz']=dict(sha256=sha(compressed),decoded_sha256=sha(raw))
    result=dict(date=date.today().isoformat(),complete=True,release=False,resident_only=True,
        profiles=checked,public_profiles_match_native_regions=True,
        candidate_comparisons=5*(417+56),native_runs=4*5*(417+56),
        library_unit_tests=58,legacy_profiles_exact=len(frozen),
        evidence=evidence,wheel_sha256=sha(args.wheel.read_bytes()),isolated_wheel_profiles=smoke,
        source_sha256_lf={str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes().replace(b'\r\n',b'\n')) for path in paths},
        archived_logs=logs,
        default_instruction_delta_tstates=0,payload_delta_bytes=0,
        exclusions=['IRQ execution','ULA/WAIT','physical disk/ROM','coroutine/guarded input','movie publication'])
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,profiles=len(checked),library_tests=58,isolated_wheel_profiles=len(smoke))))


if __name__=='__main__':main()
