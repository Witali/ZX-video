"""Verify archived streams/hashes and the independently regenerated CLI audition."""
import argparse
import gzip
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent; CORE = HERE.parents[1]
sys.path.insert(0, str(CORE))
import experimental_ym3812 as opl
from test_experimental_ym3812 import audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    args = parser.parse_args()
    evidence = HERE / 'evidence'; report = json.loads((evidence / 'report.json').read_bytes())
    assert report['complete'] and report['selected'] == 'cosine2'
    for relative, expected in report['artifacts_sha256'].items():
        assert opl.sha((evidence / relative).read_bytes()) == expected, relative
    for relative, expected in report['producer_sources_sha256_lf'].items():
        assert opl.sha((CORE / relative).read_bytes().replace(b'\r\n', b'\n')) == expected, relative
    old = CORE / 'analysis/ym3812/evidence'
    assert opl.sha((old / 'reference.wav').read_bytes()) == report['reference_sha256']
    assert opl.sha((evidence / 'controls.npz').read_bytes()) == report['controls_sha256']
    with np.load(evidence / 'controls.npz') as saved: controls = {k: saved[k] for k in saved.files}
    streams = []
    for trial in report['trials']:
        data = gzip.decompress((evidence / 'trials' / (trial['name'] + '.vgz')).read_bytes())
        assert opl.sha(data) == trial['vgm_sha256'] and len(data) == trial['vgm_bytes']
        options = trial['options']
        regenerated, writes = opl.vgm(controls, (options or {}).get('legacy_ramp', 0)) if options is None or 'legacy_ramp' in options else opl.smooth_vgm(controls, **options)
        assert data == regenerated and writes == trial['writes']
        checked = audit(data, controls); streams.append(dict(name=trial['name'], **checked))
        assert trial['complete_native_replay_exact'] and trial['chip_clipping_samples'] == trial['clipping_samples'] == 0
    selected = next(t for t in report['trials'] if t['name'] == report['selected'])
    for name in ('ym3812-preview.wav', 'ym3812.vgm', 'ym3812.vgz'):
        assert (evidence / name).read_bytes() == (args.cli / name).read_bytes()
    assert opl.sha((evidence / 'ym3812-preview.wav').read_bytes()) == selected['wave_sha256']
    assert opl.sha((evidence / 'ym3812.vgm').read_bytes()) == selected['vgm_sha256']
    tests = (evidence / 'tests.log').read_text(encoding='utf-8')
    assert 'Ran 8 tests' in tests and tests.rstrip().endswith('OK')
    result = dict(complete=True, streams=streams, all_retained_streams_regenerated_byte_exact=True,
                  independent_cli_wav_vgm_vgz_byte_exact=True, all_archive_and_producer_hashes_match=True,
                  unit_tests=8, unit_tests_pass=True,
                  report_sha256=opl.sha((evidence / 'report.json').read_bytes()),
                  verification_source_sha256_lf=opl.sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
                  artifacts_sha256={str(p.relative_to(evidence)).replace('\\', '/'): opl.sha(p.read_bytes())
                                    for p in sorted(evidence.rglob('*')) if p.is_file() and p.name != 'verification.json'})
    (evidence / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(complete=True, streams=len(streams), fields_each=1500, tests=8, cli_byte_exact=True)))


if __name__ == '__main__': main()
