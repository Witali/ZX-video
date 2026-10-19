"""Authenticate public wide native evidence, default tests and isolated wheel."""
import argparse
import gzip
import json
from pathlib import Path
import zipfile

from measure_long_copy import ROOT, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    native_path = ROOT/'libraries/evidence/wide_profiles.json'
    native = json.loads(native_path.read_text())
    assert native['complete'] and native['storage_budget_bytes']==10000
    for name, expected in native['source_sha256_lf'].items():
        assert sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n'))==expected
    units = (args.directory/'wide-unit.log').read_bytes()
    assert b'Ran 27 tests' in units and units.rstrip().endswith(b'OK')
    smoke_path = args.directory/'wide-smoke/report.json'
    smoke = json.loads(smoke_path.read_text())
    assert smoke['independent_wheel'] and not smoke['external_encoder']
    assert [r['variant'] for r in smoke['wide_profiles']]==['wide', 'wide-shared']
    wheel = next((args.directory/'wide-wheels').glob('*.whl'))
    members = []
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if not name.startswith('lzsa/') or name.endswith('/'):continue
            blob = archive.read(name)
            assert blob==(ROOT/'libraries/lzsa/src'/name).read_bytes()
            assert blob==(args.directory/'wide-installed'/name).read_bytes()
            members.append(dict(path=name, bytes=len(blob), sha256=sha(blob)))
    assert any(r['path']=='lzsa/wide.py' for r in members)
    destination = ROOT/'libraries/evidence/wide_profiles'
    destination.mkdir(exist_ok=True)
    archive_path = destination/'library-tests.log.gz'
    archive_path.write_bytes(gzip.compress(units, mtime=0))
    report = dict(date='2026-10-19', complete=True, release=False, goal_achieved=False,
        scope='Public raw wide profiles under the user-authorized 10000-byte service-memory cap.',
        budget_scope='code/table/alignment/embedded variables/external state/decoder stack/scratch/internal buffers',
        compressed_input_output_history_counted_separately=True,
        native_evidence_sha256=sha(native_path.read_bytes()), library_tests=27,
        default_profiles=31, upstream_resources=6,
        unit_log=dict(path=str(archive_path.relative_to(ROOT)).replace('\\', '/'), sha256=sha(archive_path.read_bytes())),
        profiles={k:dict(service_bytes=v['total_storage_bytes'], relocated_service_bytes=v['relocated_total_storage_bytes'],
            worst_alignment_service_bytes=v['total_storage_bytes']+255,
            corpus_cases=v['corpus_cases'], directed_cases=v['directed_cases'],
            actual_irq_probe_stack_headroom_bytes=v['verified_irq_headroom_bytes'],
            actual_irq_probe_code_bytes=13,
            maximum_corpus_input_bytes=max(r['compressed_input_bytes'] for r in v['blocks']),
            maximum_corpus_output_history_bytes=max(r['output_including_history_bytes'] for r in v['blocks']),
            maximum_real_input_bytes=v['maximum_real_input_bytes'],
            maximum_real_output_history_bytes=v['maximum_real_output_history_bytes'],
            maximum_real_separate_service_and_buffers_bytes=max(r['separate_service_and_buffers_bytes']
                for r in v['blocks'] if r['case'].startswith('real-')))
            for k,v in native['profiles'].items()},
        wheel=dict(filename=wheel.name, sha256=sha(wheel.read_bytes()), exact_members=members, smoke=smoke),
        limitations=['Raw-only; coroutine and guarded producer profiles retain their old implementation.',
            'Add actual IRQ/hardware stack headroom; six bytes were used by the register-preserving test handler.',
            'No physical disk/ROM/ULA or movie publication timing qualification.'],
        source_sha256_lf=native['source_sha256_lf'])
    assert all(p['worst_alignment_service_bytes']<=10000 for p in report['profiles'].values())
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(report['profiles']))


if __name__ == '__main__':main()
