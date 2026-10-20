"""Authenticate installed E01 APIs against complete, retained native proofs.

This verifies current bytes, labels, service inventories and isolated wheel
exports. It never relabels the saved native replays as newly executed tests.
Run the library/integration suites and build both wheels before this script.
"""
import argparse
from datetime import date
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[2]
for package in ('zx0', 'lzsa'):
    sys.path.insert(0, str(ROOT/'libraries'/package/'src'))


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def normalized(value):
    return json.loads(json.dumps(value))


def layout(profile):
    regions, labels, metadata = profile
    return dict(regions=[dict(address=at, bytes=len(blob), sha256=sha(blob))
                         for at, blob in regions], labels=labels,
                metadata=normalized(metadata))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zx0-wheel', type=Path, required=True)
    parser.add_argument('--lzsa-wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = {}

    def read(name):
        blob = (ROOT/'libraries/evidence'/name).read_bytes()
        evidence[name] = sha(blob)
        report = json.loads(gzip.decompress(blob) if name.endswith('.gz') else blob)
        assert report['complete'], ('incomplete proof', name)
        return report

    zx_native = read('next_e01_zx0_branches.json.gz')
    zx_public = read('next_e01_zx0_public.json')
    lz_native = read('next_e01_lzsa_full.json.gz')
    assert len(zx_native['profiles']) == len(zx_public['current_public_calls']) == 6
    assert len(lz_native['profiles']) == 12 and lz_native['accepted']
    # These sources were frozen during the full LZSA native matrix. Export
    # comments may change independently; current wheel/source hashes follow.
    for relative, digest in lz_native['source_sha256_lf'].items():
        assert sha((ROOT/relative).read_bytes().replace(b'\r\n', b'\n')) == digest, relative
    for relative, digest in zx_public['source_sha256_lf'].items():
        assert sha((ROOT/relative).read_bytes().replace(b'\r\n', b'\n')) == digest, relative

    calls = []
    probes = []
    for row in zx_public['current_public_calls']:
        native = zx_native['profiles'][row['native_profile']]
        assert native['complete'] and not native['slower_real_cases']
        assert row['regions'] == native['regions']
        assert row['service_bytes'] == native['service_bytes']
        assert row['real_cpu_tstates'] == native['real_candidate_tstates']
        calls.append(dict(row, codec='zx0'))
        builder = importlib.import_module(row['module']).build
        for origin, field in ((0x8000, 'regions'), (0x9103, 'relocated_regions'),
                              (0x0800, 'high_word_regions'),
                              (0x0703, 'high_word_relocated_regions')):
            kwargs = dict(row['kwargs'], core=origin)
            current = builder(**kwargs)
            saved = layout(current)
            assert saved['regions'] == native[field]
            assert current[2]['service_memory_bytes'] == row['service_bytes']
            if origin == 0x8000:
                assert current[1] == row['labels']
            probes.append(dict(module=row['module'], kwargs=kwargs, expected=saved,
                               codec='zx0'))

    for name, native in lz_native['profiles'].items():
        assert native['complete'] and native['accepted']
        assert len(native['blocks']) == 675 and not native['summary']['slower_real_cases']
        kwargs = dict(native['kwargs'], cold_match_extension=True)
        builder = importlib.import_module(native['module']).build
        row = dict(name=name, codec='lzsa2', module=native['module'], kwargs=kwargs,
                   native_profile=name, regions=native['candidate']['regions'],
                   labels=native['candidate']['labels'],
                   service_bytes=native['candidate']['metadata']['service_memory_bytes'],
                   real_cpu_tstates=native['summary']['candidate_real_tstates'])
        calls.append(row)
        for origin, field in ((0x8000, 'candidate'), (0x9103, 'relocated')):
            placed = dict(kwargs, core=origin)
            current = builder(**placed)
            saved = layout(current)
            assert saved == {key:native[field][key] for key in saved}, (name, origin)
            probes.append(dict(module=native['module'], kwargs=placed,
                               expected=saved, codec='lzsa2'))
        # The opt-in must leave the preceding default exactly available.
        classic = builder(**native['kwargs'])
        assert layout(classic) == {key:native['baseline'][key] for key in layout(classic)}, name

    from test_libraries import profiles
    assert profiles() == json.loads(
        (ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    logs = {}
    archive = ROOT/'libraries/evidence/next_e01_public'
    archive.mkdir(exist_ok=True)
    for filename, minimum in (('next-e01-library-tests.log', 69),
                              ('next-e01-toolkit-tests.log', 24),
                              ('next-e01-wheel.log', None)):
        raw = (ROOT/'.tmp'/filename).read_bytes()
        text = raw.decode('utf-8')
        if minimum is not None:
            assert '\nOK' in text and not re.search(r'\n(?:FAILED|ERROR)', text)
            count = int(re.search(r'Ran (\d+) tests', text)[1])
            assert count >= minimum, filename
        else:
            assert 'Successfully built' in text
            count = None
        compressed = gzip.compress(raw, mtime=0)
        (archive/(filename+'.gz')).write_bytes(compressed)
        logs[filename] = dict(tests=count, sha256=sha(compressed), decoded_sha256=sha(raw))

    with tempfile.TemporaryDirectory(dir=ROOT/'.tmp', prefix='next-e01-wheel-') as temporary:
        folder = Path(temporary)
        installed = folder/'installed'
        installed.mkdir()
        for path in (args.zx0_wheel, args.lzsa_wheel):
            with zipfile.ZipFile(path) as wheel:
                assert all(not Path(name).is_absolute() and '..' not in Path(name).parts
                           for name in wheel.namelist())
                wheel.extractall(installed)
        inputs = folder/'probes.json'
        inputs.write_text(json.dumps(probes), encoding='utf-8')
        child = """import hashlib,importlib,json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
probes=json.loads(Path(sys.argv[2]).read_text());rows=[]
for index,row in enumerate(probes):
    profile=importlib.import_module(row['module']).build(**row['kwargs'])
    current=dict(regions=[dict(address=at,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()) for at,blob in profile[0]],labels=profile[1],metadata=profile[2])
    assert json.loads(json.dumps(current))==row['expected']
    destination=Path(sys.argv[3])/str(index)
    package='zx0' if row['codec']=='zx0' else 'lzsa'
    importlib.import_module(package+'.export').export(destination,*profile)
    restored=[]
    assembly=(destination/'decoder.asm').read_text()
    for line in assembly.splitlines():
        if line.startswith('org '):restored.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):restored[-1][1].extend(int(v[1:],16) for v in line[3:].split(','))
    assert [(at,bytes(data)) for at,data in restored]==profile[0]
    if row['codec']=='lzsa2':assert 'ColdExtendedMatch' in assembly and '10 -> 7 T' in assembly
    rows.append(dict(module=row['module'],kwargs=row['kwargs'],regions=current['regions']))
assert not any(name=='z80' or name=='toolkit' or name.startswith('numpy') for name in sys.modules)
print(json.dumps(rows))
"""
        result = subprocess.run([sys.executable, '-I', '-c', child, str(installed),
                                 str(inputs), str(folder/'exports')], check=True,
                                capture_output=True, text=True)
        smoke = json.loads(result.stdout)
        assert len(smoke) == len(probes) == 48

    sources = [Path(__file__)]
    for package in ('zx0', 'lzsa'):
        sources.extend((ROOT/'libraries'/package/'src'/package).glob('*.py'))
    report = dict(date=date.today().isoformat(), complete=True, release=False,
                  resident_only=True, current_public_calls=calls,
                  isolated_wheel_exports=len(smoke), native_cases_reexecuted=0,
                  native_evidence_reused_without_relabeling=True,
                  proof_sha256=evidence, archived_logs=logs, legacy_profiles_exact=31,
                  existing_default_instruction_delta_tstates=0, payload_delta_bytes=0,
                  wheels={path.name:sha(path.read_bytes()) for path in
                          (args.zx0_wheel, args.lzsa_wheel)},
                  source_sha256_lf={path.relative_to(ROOT).as_posix():sha(
                      path.read_bytes().replace(b'\r\n', b'\n')) for path in sources},
                  exclusions=['coroutine/guarded input', 'physical disk/ROM',
                              'ULA/WAIT', 'movie publication'])
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(complete=True, public_calls=len(calls),
                         isolated_wheel_exports=len(smoke), archived_logs=logs)))


if __name__ == '__main__':
    main()
