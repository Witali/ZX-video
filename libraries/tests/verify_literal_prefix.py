"""Authenticate the completed literal-prefix component experiment and wheel checks."""
import argparse
import gzip
import json
from pathlib import Path
import re
from zipfile import ZipFile

from measure_long_copy import ROOT, sha
from measure_fast_jumps import layout
from test_libraries import profiles
from zx0.block import build as block
from zx0.resumable import build as coroutine


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'.tmp')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    evidence=ROOT/'libraries/evidence'
    data=json.loads((evidence/'ten_percent_literal_prefix.json').read_text())
    review=json.loads((evidence/'literal_prefix_independent_review.json').read_text())
    assert data['complete'] and review['complete']
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    old=json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    resources=old['original_resources']+old['added_pinned_resources']
    for item in resources:
        path=ROOT/'libraries'/item['package']/'src'/item['package']/'asm'/item['file']
        assert sha(path.read_bytes())==item['sha256']
    for path,wanted in review['source_sha256_lf'].items():
        assert sha((ROOT/path).read_bytes().replace(b'\r\n',b'\n'))==wanted
    for name,profile in data['profiles'].items():
        builder=coroutine if 'coroutine' in name else block
        public=builder(core=0x8000,core_limit=0x8400,literal_prefix=True,branch_tuned=name.endswith('-tuned'))
        assert layout(public)==profile['candidate']
        assert len(profile['blocks'])==417 and profile['summary']['real_blocks']==364
        assert all(row['delta_tstates']==row['expected_delta_tstates'] for row in profile['blocks'])
        if builder is coroutine:assert all(row['quota_returns_exact'] for row in profile['blocks'])
    log=(args.directory/'literal-prefix-library-tests.log').read_bytes()
    text=log.decode('utf-8',errors='replace')
    assert re.search(r'Ran 28 tests in ',text) and text.rstrip().endswith('OK')
    archive=evidence/'literal_prefix';archive.mkdir(exist_ok=True)
    (archive/'library-tests.log.gz').write_bytes(gzip.compress(log,mtime=0))
    wheels={}
    for package in ('zx0','lzsa'):
        report=json.loads((args.directory/f'literal-prefix-smoke-{package}'/'report.json').read_text())
        assert report['independent_wheel'] and report['cli_export'] and report['exact_round_trip']
        assert len(report['resident_profiles'])==(4 if package=='zx0' else 2)
        if package=='zx0':assert len(report['literal_prefix_profiles'])==2
        path=next((args.directory/'literal-prefix-wheels').glob(f'zxvideo_{package}-*.whl'))
        with ZipFile(path) as wheel:
            files=[]
            for source in (ROOT/'libraries'/package/'src'/package).rglob('*'):
                if source.is_file() and '__pycache__' not in source.parts:
                    relative=source.relative_to(ROOT/'libraries'/package/'src').as_posix()
                    assert wheel.read(relative)==source.read_bytes()
                    files.append(relative)
        wheels[package]=dict(wheel_sha256=sha(path.read_bytes()),source_and_resources_exact=files,smoke=report)
    source_files=[path for package in ('zx0','lzsa') for path in (ROOT/'libraries'/package/'src'/package).rglob('*.py')]
    source_files += [ROOT/'libraries/tests'/name for name in ('measure_literal_prefix.py','review_literal_prefix.py',
                     'test_literal_prefix.py','verify_literal_prefix.py','smoke_install.py')]
    result=dict(date='2026-10-19',complete=True,goal_achieved=False,release=False,
        baseline_revision='674a1fc8',goal_baseline='f5a0362c',default_profiles_exact=31,
        upstream_resources_exact=len(resources),native_profile_comparisons=1668,native_runs=6672,
        native_scope='417 complete blocks x four profiles; before/after, relocated, IRQ',
        independent_pre_copy_and_deferred_irq_cases=28,library_tests=28,wheels=wheels,
        timing_policy=dict(long_literal_delta=-5,coroutine_sync_per_request=26,payload_delta_bytes=0),
        summaries={name:item['summary'] for name,item in data['profiles'].items()},
        source_sha256_lf={path.relative_to(ROOT).as_posix():sha(path.read_bytes().replace(b'\r\n',b'\n')) for path in source_files},
        evidence_sha256={name:sha((evidence/name).read_bytes()) for name in
                         ('ten_percent_literal_prefix.json','literal_prefix_independent_review.json','literal_prefix/library-tests.log.gz')})
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,goal_achieved=False,native_comparisons=1668,library_tests=28,wheels=list(wheels))))


if __name__=='__main__':main()
