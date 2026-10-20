"""Authenticate complete ordinary-wide coroutine evidence and isolated wheel."""
import argparse
import gzip
import json
from pathlib import Path
import zipfile

from measure_long_copy import ROOT,sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    path=ROOT/'libraries/evidence/wide_coroutine.json'
    native=json.loads(path.read_text())
    assert native['complete']
    for name,expected in native['source_sha256_lf'].items():
        assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==expected
    unit=(args.directory/'wide-coroutine-unit.log').read_bytes()
    assert b'Ran 30 tests' in unit and unit.rstrip().endswith(b'OK')
    smoke=json.loads((args.directory/'coroutine-smoke/report.json').read_text())
    assert smoke['independent_wheel'] and not smoke['external_encoder']
    assert [p['variant'] for p in smoke['wide_profiles']]==['wide','wide-shared','wide-coroutine','wide-shared-coroutine']
    wheel=next((args.directory/'coroutine-wheels').glob('*.whl'))
    members=[]
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if not name.startswith('lzsa/') or name.endswith('/'):continue
            blob=archive.read(name)
            assert blob==(ROOT/'libraries/lzsa/src'/name).read_bytes()
            assert blob==(args.directory/'coroutine-installed'/name).read_bytes()
            members.append(dict(path=name,sha256=sha(blob)))
    assert any(m['path']=='lzsa/wide_coroutine.py' for m in members)
    logs=ROOT/'libraries/evidence/wide_coroutine'
    logs.mkdir(exist_ok=True)
    logfile=logs/'library-tests.log.gz'
    logfile.write_bytes(gzip.compress(unit,mtime=0))
    profiles={}
    for key,p in native['profiles'].items():
        metadata=p['metadata']
        assert metadata['service_memory_bytes']==metadata['code_bytes']+metadata['private_stack_bytes']+metadata['caller_stack_bytes']
        assert p['summary']['actual_private_stack_bytes']==metadata['private_stack_bytes']==16
        assert p['summary']['actual_caller_stack_bytes']==metadata['caller_stack_bytes']==4
        assert p['summary']['publication_offsets_exact']
        profiles[key]=dict(code_tables_alignment_state_bytes=metadata['code_bytes'],
            service_bytes=metadata['service_memory_bytes'],
            relocated_service_bytes=p['relocated_metadata']['service_memory_bytes'],
            worst_alignment_service_bytes=metadata['service_memory_bytes']+255,
            private_stack_bytes=16,caller_stack_bytes=4,embedded_state_bytes=metadata['state_bytes'],
            actual_irq_handler_code_bytes=13,actual_irq_stack_headroom_bytes=6,
            maximum_corpus_input_bytes=max(r['compressed_input_bytes'] for r in p['blocks']),
            maximum_corpus_output_history_bytes=max(r['output_history_bytes'] for r in p['blocks']),
            summary=p['summary'])
        assert profiles[key]['worst_alignment_service_bytes']<=10000
    report=dict(date='2026-10-20',complete=True,release=False,goal_achieved=False,
        scope='Ordinary complete-input wide coroutine with exact publication cursors and bounded service memory.',
        storage_budget_bytes=10000,external_input_output_history_separate=True,
        profiles=profiles,library_tests=30,default_profiles=31,upstream_resources=6,
        native_sha256=sha(path.read_bytes()),source_sha256_lf=native['source_sha256_lf'],
        unit_log=dict(path=str(logfile.relative_to(ROOT)).replace('\\','/'),sha256=sha(logfile.read_bytes())),
        wheel=dict(filename=wheel.name,sha256=sha(wheel.read_bytes()),members=members,smoke=smoke),
        limitations=['Complete input required; partial-input guarded variants are not implemented.',
                    'IRQ code/headroom and data buffers are reported separately from decoder service.',
                    'No physical delivery, ROM/ULA timing or movie publication deadline claim.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:p['service_bytes'] for k,p in profiles.items()}))


if __name__=='__main__':main()
