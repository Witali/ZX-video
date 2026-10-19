"""Authenticate the saved tail-refill corpus, unit log and standalone wheel."""
import argparse
import gzip
import json
from pathlib import Path
import zipfile

from measure_long_copy import ROOT, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT/'.tmp')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = ROOT/'libraries/evidence/ten_percent_tail_refill.json'
    native = json.loads(evidence.read_text())
    assert native['complete'] and not native['goal_achieved'] and not native['release']
    assert len(native['profiles']) == 4
    for item in native['profiles'].values():
        summary = item['summary']
        assert summary['cases'] == 417 and summary['real_blocks'] == 364
        assert summary['real_delta_tstates'] == -359963
        assert summary['slower_blocks'] == summary['slower_slices'] == 0
        assert item['candidate']['code_bytes']-item['baseline']['code_bytes'] == 3
    unit = args.directory/'tail-refill-unit.log'
    text = unit.read_text(encoding='utf-8')
    assert 'Ran 27 tests' in text and text.rstrip().endswith('OK')
    smoke = json.loads((args.directory/'tail-smoke/report.json').read_text())
    assert smoke['independent_wheel'] and len(smoke['inline_tail_refill_profiles']) == 2
    wheel = args.directory/'tail-wheels/zxvideo_zx0-0.1.0-py3-none-any.whl'
    files = []
    with zipfile.ZipFile(wheel) as archive:
        for source in sorted((ROOT/'libraries/zx0/src/zx0').rglob('*')):
            if not source.is_file() or '__pycache__' in source.parts:continue
            member = 'zx0/'+source.relative_to(ROOT/'libraries/zx0/src/zx0').as_posix()
            assert archive.read(member) == source.read_bytes(), member
            files.append(dict(file=member, sha256=sha(source.read_bytes())))
    archive = ROOT/'libraries/evidence/tail_refill/library-tests.log.gz'
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(gzip.compress(unit.read_bytes(), mtime=0))
    source_files = ['zx0/src/zx0/block.py', 'zx0/src/zx0/resumable.py',
                    'zx0/src/zx0/__main__.py', 'zx0/src/zx0/export.py',
                    'tests/measure_tail_refill.py', 'tests/test_tail_refill.py',
                    'tests/verify_tail_refill.py', 'tests/smoke_install.py']
    report = dict(date='2026-10-19', source_baseline='674a1fc8', goal_baseline='f5a0362c',
                  complete=True, goal_achieved=False, release=False,
                  native_profile_comparisons=1668, native_replays=6672,
                  default_profiles_exact=31, upstream_resources_exact=6, library_tests=27,
                  source_sha256_lf={name:sha((ROOT/'libraries'/name).read_bytes().replace(b'\r\n',b'\n'))
                                    for name in source_files},
                  evidence_sha256=sha(evidence.read_bytes()),
                  library_test_log=dict(file=archive.relative_to(ROOT/'libraries').as_posix(),
                                        sha256=sha(archive.read_bytes())),
                  wheel=dict(name=wheel.name, sha256=sha(wheel.read_bytes()), files=files, smoke=smoke),
                  limits=['Flat CPU component checks only; IRQ correctness is separately replayed.',
                          'No new toolkit/player/movie/disk delivery qualification.',
                          'Smaller intermediate gain; active ten-percent-per-library goal remains incomplete.'])
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({key:value for key,value in report.items() if key not in ('source_sha256_lf','wheel')}))


if __name__ == '__main__':
    main()
