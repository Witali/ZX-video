"""E00 baseline authentication, without relabeling old native/test runs.

This records the immutable pre-experiment public bytes and service inventory.
Historical native, IRQ, relocation, wheel and integration evidence is reused
only after source and region authentication. New observer/in-place runs have
their own reports; this script does not claim to execute those tests.
"""
import argparse
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'libraries/zx0/src'), str(ROOT/'libraries/lzsa/src')]
from zx0.maximum import build as maximum
from lzsa.hybrid import build as hybrid
from test_libraries import profiles


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rows(profile):
    return [dict(address=at, bytes=len(blob), sha256=sha(blob))
            for at, blob in profile[0]]


def read(name):
    raw = (ROOT/'libraries/evidence'/name).read_bytes()
    return json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = ROOT/'libraries/evidence'
    fixed = subprocess.check_output(['git', 'rev-parse', '9c28b01f'], cwd=ROOT, text=True).strip()
    source_checks = {}
    evidence_checks = {}
    old_runs = []
    for name, log_directory in (
            ('shared_zero_prefix_verification.json', 'shared_zero_prefix'),
            ('hybrid_public_verification.json', 'hybrid_public')):
        saved = read(name)
        assert saved['complete'] and not saved['release']
        evidence_checks[name] = sha((evidence/name).read_bytes())
        for relative, expected in saved['source_sha256_lf'].items():
            current = (ROOT/relative).read_bytes().replace(b'\r\n', b'\n')
            assert sha(current) == expected, relative
            # Public sources must also be exactly the fixed decoder baseline.
            if '/src/' in relative:
                pinned = subprocess.check_output(['git', 'show', fixed+':'+relative], cwd=ROOT)
                assert sha(pinned.replace(b'\r\n', b'\n')) == expected, relative
            source_checks[relative] = expected
        for relative, record in saved.get('evidence', {}).items():
            raw = (evidence/relative).read_bytes()
            assert sha(raw) == record['sha256']
            assert sha(gzip.decompress(raw)) == record['decoded_sha256']
            evidence_checks[relative] = sha(raw)
        for relative, expected in saved.get('evidence_sha256', {}).items():
            path = ROOT/relative if relative.startswith('libraries/') else evidence/relative
            assert sha(path.read_bytes()) == expected, relative
            evidence_checks[str(path.relative_to(evidence)).replace('\\', '/')] = expected
        for filename, record in saved['archived_logs'].items():
            compressed_name = filename if filename.endswith('.gz') else filename+'.gz'
            raw = (evidence/log_directory/compressed_name).read_bytes()
            assert sha(raw) == record['sha256']
            assert sha(gzip.decompress(raw)) == record['decoded_sha256']
            evidence_checks[log_directory+'/'+compressed_name] = sha(raw)
        old_runs.append(dict(manifest=name, source_authenticated=True,
            native_irq_relocation_and_integration_reused=True,
            newly_executed_native_or_integration_tests=0))

    zx_native = read('shared_zero_prefix_native.json.gz')
    zx_high = read('shared_zero_prefix_high_word.json.gz')
    public = []
    for cap, saved in zx_native['profiles'].items():
        cap = int(cap)
        for origin, expected in ((0x8000, saved['regions']),
                (0x9103, saved['relocated_regions']),
                (0x0800, zx_high['profiles'][str(cap)]['regions']),
                (0x0703, zx_high['profiles'][str(cap)]['relocated_regions'])):
            assert rows(maximum(core=origin, prefix_cap=cap, shared_prefixes=True)) == expected
        current = maximum(prefix_cap=cap, shared_prefixes=True)
        assert current[2]['service_memory_bytes'] == saved['summary']['service_bytes']
        public.append(dict(module='zx0.maximum', arguments=dict(prefix_cap=cap, shared_prefixes=True),
            regions=rows(current), service_memory=current[2]['service_memory'],
            service_bytes=current[2]['service_memory_bytes']))
    for saved in read('hybrid_public_verification.json')['current_public_calls'][:6]:
        assert saved['module'] == 'lzsa.hybrid'
        current = hybrid(**saved['kwargs'])
        assert rows(current) == saved['regions']
        assert current[2]['service_memory_bytes'] == saved['service_bytes']
        public.append(dict(module='lzsa.hybrid', arguments=saved['kwargs'],
            regions=rows(current), service_memory=current[2]['service_memory'],
            service_bytes=current[2]['service_memory_bytes'], real_cpu_tstates=saved['real_cpu_tstates']))
    frozen = json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    assert profiles() == frozen and len(frozen) == 31
    alignments = []
    for name, builder, kwargs in (
            ('zx0-shared127', maximum, dict(prefix_cap=127, shared_prefixes=True)),
            ('zx0-shared228', maximum, dict(prefix_cap=228, shared_prefixes=True)),
            *((f'lzsa-hybrid-{name}', hybrid, dict(profile=name))
              for name in ('compact', 'balanced', 'fast'))):
        inventory = []
        for low in range(256):
            result = builder(core=0x8000+low, **kwargs)
            service = result[2]['service_memory_bytes']
            assert service <= 10000
            inventory.append(dict(origin=0x8000+low, service_bytes=service,
                service_with_diagnostic_irq_bytes=service+13+6,
                regions=rows(result)))
        alignments.append(dict(profile=name, low_byte_origins=256,
            min_service_bytes=min(row['service_bytes'] for row in inventory),
            max_service_bytes=max(row['service_bytes'] for row in inventory),
            max_service_with_diagnostic_irq_bytes=max(row['service_with_diagnostic_irq_bytes'] for row in inventory),
            origins=inventory))
    result = dict(date=date.today().isoformat(), complete=True, release=False,
        stage='E00 baseline authentication', fixed_decoder_revision=fixed,
        observation_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        legacy_layouts_exact=31, public_calls=public, alignment_checks=alignments,
        source_sha256_lf=source_checks, evidence_sha256=evidence_checks,
        reused_runs=old_runs, existing_decoder_instruction_delta_tstates=0,
        memory_scope='code+embedded/external state+tables+padding+scratch/internal buffers+required stacks; I/O/history excluded',
        acceptance='strictly lower real decode CPU AND total service memory, same features/inputs',
        independent_new_runs='See next_e00_zx0, next_e00_lzsa and next_e00_inplace reports; not asserted by this script')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, indent=2)+'\n').encode()
    args.output.write_bytes(gzip.compress(raw, mtime=0) if args.output.suffix == '.gz' else raw)
    print(json.dumps(dict(complete=True, baseline=fixed[:8], sources=len(source_checks),
        public_calls=len(public), legacy_layouts=31, alignment_builds=5*256,
        newly_executed_native_tests=0)))


if __name__ == '__main__':
    main()
