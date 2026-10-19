"""Authenticate the compact integration's full CPU/service-memory evidence."""
import argparse
import gzip
import json
from pathlib import Path
import re
from zipfile import ZipFile

from measure_long_copy import ROOT, sha
from measure_fast_jumps import layout
from test_libraries import profiles
from zx0.block import build as zb
from zx0.resumable import build as zc
from lzsa.block import build as lb
from lzsa.resumable import build as lc


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'.tmp')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();evidence=ROOT/'libraries/evidence'
    data=json.loads((evidence/'compact_frontier.json').read_text())
    assert data['complete'] and data['service_memory_limit_bytes']==10000
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    resources=json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    resources=resources['original_resources']+resources['added_pinned_resources']
    for item in resources:
        path=ROOT/'libraries'/item['package']/'src'/item['package']/'asm'/item['file']
        assert sha(path.read_bytes())==item['sha256']
    for name,builder in (('zx0-block',zb),('zx0-coroutine',zc),('lzsa2-block',lb),('lzsa2-coroutine',lc)):
        item=data['profiles'][name];memory=item['memory']
        public=builder(core=0x8000,core_limit=0x8400,**item['options'])
        assert layout(public)==item['candidate']
        assert memory['measured_service_bytes']==memory['emitted_code_and_data_bytes']+memory['caller_stack_peak_including_return']+memory['private_stack_peak']
        assert memory['self_modifying_operand_bytes_already_in_regions']==len(set(public[2]['patched_addresses']))
        assert memory['within_service_cap'] and memory['service_reserved_for_tested_irq_contract_bytes']<=10000
        assert memory['test_irq_handler_code_bytes']==13
        assert len(item['blocks'])==(417 if name.startswith('zx0') else 97)
        assert all(r['exact'] and r['relocated_exact'] for r in item['blocks'])
        if 'coroutine' in name:assert all(r['quota_returns_exact'] for r in item['blocks'])
    archived={}
    destination=evidence/'compact_frontier';destination.mkdir(exist_ok=True)
    for filename,count in (('compact-codec-integration-library.log',34),('compact-frontier-toolkit.log',67)):
        raw=(args.directory/filename).read_bytes();text=raw.decode('utf-8',errors='replace')
        assert re.search(rf'Ran {count} tests in ',text) and text.rstrip().endswith('OK')
        path=destination/(filename+'.gz');path.write_bytes(gzip.compress(raw,mtime=0));archived[path.relative_to(evidence).as_posix()]=sha(path.read_bytes())
    wheels={}
    for package in ('zx0','lzsa'):
        path=next((args.directory/'compact-frontier-wheels').glob(f'zxvideo_{package}-*.whl'))
        smoke=json.loads((args.directory/f'compact-frontier-smoke-{package}'/'report.json').read_text())
        assert smoke['independent_wheel'] and len(smoke['combined_profiles'])==2
        with ZipFile(path) as wheel:
            files=[]
            for source in (ROOT/'libraries'/package/'src'/package).rglob('*'):
                if source.is_file() and '__pycache__' not in source.parts:
                    relative=source.relative_to(ROOT/'libraries'/package/'src').as_posix()
                    assert wheel.read(relative)==source.read_bytes();files.append(relative)
        wheels[package]=dict(wheel_sha256=sha(path.read_bytes()),source_and_resources_exact=files,smoke=smoke)
    sources=[p for package in ('zx0','lzsa') for p in (ROOT/'libraries'/package/'src'/package).rglob('*.py')]
    sources += [ROOT/'libraries/tests'/name for name in ('measure_compact_frontier.py','verify_compact_frontier.py','smoke_install.py')]
    result=dict(date='2026-10-19',complete=True,goal_achieved=False,release=False,baseline_revision='f5a0362c',
        service_memory_limit_bytes=10000,input_output_excluded_from_cap=True,default_profiles_exact=31,
        upstream_resources_exact=len(resources),native_profile_comparisons=1028,native_runs=4112,
        library_tests=34,toolkit_tests=67,summaries={name:item['summary'] for name,item in data['profiles'].items()},
        service_memory={name:item['memory'] for name,item in data['profiles'].items()},wheels=wheels,
        source_sha256_lf={p.relative_to(ROOT).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n')) for p in sources},
        evidence_sha256=dict(archived,**{'compact_frontier.json':sha((evidence/'compact_frontier.json').read_bytes())}))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,goal_achieved=False,tests=101,native_comparisons=1028,service_memory_limit_bytes=10000)))


if __name__=='__main__':main()
