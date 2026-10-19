"""Authenticate the completed test-only Mega native experiment and unit log."""
import argparse
import gzip
import json
from pathlib import Path
import zipfile

from measure_long_copy import ROOT,sha
from mega_offset_profile import build as reference
from zx0.block import build as public


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'.tmp')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    path=ROOT/'libraries/evidence/ten_percent_mega_offset.json'
    native=json.loads(path.read_text())
    assert native['complete'] and native['test_only'] and not native['coroutine_supported']
    assert native['baseline']['code_bytes']==674
    for name,code,delta,slow in (('dead-offset-shifts',666,-614704,0),
                               ('reuse-tail-jp',678,-105547,32),('combined',670,-720251,0)):
        item=native['profiles'][name]
        assert item['candidate']['code_bytes']==code
        assert item['summary']['cases']==417 and item['summary']['real_blocks']==364
        assert item['summary']['real_delta_tstates']==delta and item['summary']['slower_blocks']==slow
        assert all(row['delta_tstates']==row['predicted_delta_tstates'] for row in item['blocks'])
    unit=args.directory/'mega-offset-unit.log'
    text=unit.read_text(encoding='utf-8')
    assert 'Ran 28 tests' in text and text.rstrip().endswith('OK')
    for fast in (False,True):
        for origin in (0x8000,0x9103):
            candidate=public('mega',core=origin,core_limit=origin+0x400,fast_jumps=fast,mega_tuned=True)
            assert candidate[:2] == reference(origin=origin,fast_jumps=fast,reuse_tail_jp=True)[:2]
            assert candidate[2]['max_decoder_stack_bytes']==4 and candidate[2]['workspace_bytes']==673+fast
    frozen=json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    resources=[]
    for item in frozen['original_resources']+frozen['added_pinned_resources']:
        source=ROOT/'libraries'/item['package']/'src'/item['package']/'asm'/item['file']
        assert sha(source.read_bytes())==item['sha256']
        resources.append(item)
    archive=ROOT/'libraries/evidence/mega_offset/library-tests.log.gz'
    archive.parent.mkdir(parents=True,exist_ok=True)
    archive.write_bytes(gzip.compress(unit.read_bytes(),mtime=0))
    files=['tests/mega_offset_profile.py','tests/measure_mega_offset.py','tests/verify_mega_offset.py',
           'tests/test_mega_tuned.py','tests/smoke_install.py','zx0/src/zx0/codec.py',
           'zx0/src/zx0/block.py','zx0/src/zx0/__main__.py','zx0/src/zx0/export.py']
    wheel=args.directory/'mega-wheels/zxvideo_zx0-0.1.0-py3-none-any.whl'
    with zipfile.ZipFile(wheel) as package:
        for source in (ROOT/'libraries/zx0/src/zx0').rglob('*'):
            if not source.is_file() or '__pycache__' in source.parts:continue
            member='zx0/'+source.relative_to(ROOT/'libraries/zx0/src/zx0').as_posix()
            assert package.read(member)==source.read_bytes(),member
    smoke=json.loads((args.directory/'mega-smoke/report.json').read_text())
    assert smoke['independent_wheel'] and len(smoke['mega_tuned_profiles'])==2
    report=dict(date='2026-10-19',source_baseline='6db73511',goal_baseline='f5a0362c',
        complete=True,test_only=False,public_mega_tuned_matches_prototype=True,release=False,goal_achieved=False,coroutine_supported=False,
        native_candidate_comparisons=1251,native_replays=4170,default_profiles_exact=31,
        upstream_resources_exact=resources,library_tests=28,
        workspace=dict(code_bytes=670,embedded_offset_variable_bytes=2,extra_state_bytes=0,
                       tables_bytes=0,padding_bytes=0,scratch_internal_buffers_bytes=0,
                       max_decoder_stack_including_call_return=4,total_service_bytes=674,
                       example_irq_extra_stack_bytes=6,example_irq_code_bytes=13,
                       total_with_example_irq=693,input_output_history_counted_separately=True),
        wheel=dict(name=wheel.name,sha256=sha(wheel.read_bytes()),smoke=smoke),
        source_sha256_lf={name:sha((ROOT/'libraries'/name).read_bytes().replace(b'\r\n',b'\n')) for name in files},
        evidence_sha256=sha(path.read_bytes()),
        library_tests_log=dict(file=archive.relative_to(ROOT/'libraries').as_posix(),sha256=sha(archive.read_bytes())),
        limitations=['Optional resident Mega API/CLI only; no coroutine equivalent.',
                     'Reuse-tail-only branch candidate slows 32 cases, including31real, maximum156T.',
                     'Combined complete blocks improve but individual untaken changed branches cost3T more.',
                     'CPU component result only; no physical delivery or movie/player qualification.',
                     'The historical Mega gain does not count as a new improvement.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({key:value for key,value in report.items() if key not in ('source_sha256_lf','upstream_resources_exact')}))


if __name__=='__main__':main()
