"""Bind installed F00 APIs to complete native proofs and preserve prior calls.

Native timings are reused by exact emitted-byte/label identity. This verifier
does not relabel the original private-source matrix as a new public-source run.
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


def sha(data):
    return hashlib.sha256(data).hexdigest()


def layout(profile):
    return dict(regions=[dict(address=at, bytes=len(blob), sha256=sha(blob))
                         for at, blob in profile[0]], labels=profile[1],
                metadata=json.loads(json.dumps(profile[2])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zx0-wheel', type=Path, required=True)
    parser.add_argument('--lzsa-wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    used = {}

    def read(name):
        raw = (ROOT/'libraries/evidence'/name).read_bytes()
        used[name] = sha(raw)
        return json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)

    native = read('next_f00_full.json.gz')
    prior = read('next_f00_prior_sources.json.gz')
    e01 = read('next_e01_public_verification.json')
    assert e01['complete'] and len(e01['current_public_calls']) == 18
    assert native['complete'] and native['raw_qualification_complete']
    for name, digest in native['archived_proof_sha256'].items():
        assert sha((ROOT/'libraries/evidence'/name).read_bytes()) == digest, name
    assert native['launch_source_sha256_lf'] == native['final_source_sha256_lf']
    changed_native_sources = []
    for name, digest in native['final_source_sha256_lf'].items():
        current = sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n'))
        if current != digest:
            assert name in ('libraries/lzsa/src/lzsa/wide.py',
                            'libraries/lzsa/src/lzsa/hybrid.py'), name
            assert prior[name]['sha256_lf'] == digest
            assert sha(prior[name]['text'].encode()) == digest
            changed_native_sources.append(name)

    # Preserve every preceding table selection, including older wrappers.
    old_table = json.loads(prior['libraries/evidence/decoder_variants_verification.json']['text'])
    assert old_table['complete'] and len(old_table['profiles']) == 68
    probes = []
    for row in old_table['profiles']:
        module = row['builder'].removesuffix('.build')
        profile = importlib.import_module(module).build(**row['kwargs'])
        current = layout(profile)
        assert current['regions'] == row['regions'], row['name']
        assert sum(len(blob) for _, blob in profile[0]) == row['code_state_table_padding_bytes']
        probes.append(dict(module=module, kwargs=row['kwargs'], expected=current,
                           codec=row['codec']))
    # E01 has full metadata and label witnesses, unlike some older table rows.
    lz_e01 = read('next_e01_lzsa_full.json.gz')
    for name, row in lz_e01['profiles'].items():
        builder = importlib.import_module(row['module']).build
        for origin, field in ((0x8000, 'candidate'), (0x9103, 'relocated')):
            current = layout(builder(**dict(row['kwargs'], cold_match_extension=True, core=origin)))
            assert current == {key: row[field][key] for key in current}, (name, origin)
        current = layout(builder(**row['kwargs']))
        assert current == {key: row['baseline'][key] for key in current}, name

    from lzsa.hot import build
    calls = []
    for mode, kind in (('literals', 'hot_clone'), ('nibble', 'hot_pair'),
                       ('combined', 'combined')):
        saved = native['profiles'][kind]
        assert saved['C_complete'] and saved['native_complete']
        assert saved['qualification']['complete']
        assert len(saved['blocks']) == 675 and len(saved['supplemental']) == 60
        assert not saved['summary']['slower_cases']
        supplemental_slower = [dict(case=row['case'], delta_tstates=row['delta_tstates'])
                               for row in saved['supplemental'] if row['delta_tstates'] > 0]
        assert len(supplemental_slower) == (0 if mode == 'nibble' else 4)
        assert all(row['delta_tstates'] == 10 for row in supplemental_slower)
        for origin, field in ((0x8000, None), (0x9103, 'relocated')):
            profile = build(mode, core=origin)
            current = layout(profile)
            golden = saved if field is None else saved[field]
            assert current['regions'] == golden['regions'], (mode, origin)
            assert current['labels'] == golden['labels'], (mode, origin)
            assert current['metadata']['service_memory_bytes'] == golden['metadata']['service_memory_bytes']
            # Actual guest entry bytes account for44 T of required setup.
            # The final4/10/4/10-T sequence restores HL' and returns. Both
            # sequences lie inside the measured start-through-RET interval.
            blob = profile[0][0][1]
            start = profile[1]['start']-origin
            done = profile[1]['done']-origin
            assert blob[start:start+10] == bytes.fromhex('d9e5d906003708c3')+profile[1]['ReadToken'].to_bytes(2, 'little')
            assert blob[done:done+4] == bytes.fromhex('d9e1d9c9')
            probes.append(dict(module='lzsa.hot', kwargs=dict(profile=mode, core=origin),
                               expected=current, codec='lzsa2'))
        for row in saved['alignments']:
            current = layout(build(mode, core=0x8000+row['low_byte']))
            assert current['regions'] == row['regions']
            assert sha(json.dumps(current['labels'], sort_keys=True).encode()) == row['labels_sha256']
            assert current['metadata']['service_memory_bytes'] == row['service_bytes']
        current = layout(build(mode))
        calls.append(dict(module='lzsa.hot', kwargs=dict(profile=mode), native_profile=kind,
                          codec='lzsa2', regions=current['regions'], labels=current['labels'],
                          metadata=current['metadata'], service_bytes=current['metadata']['service_memory_bytes'],
                          real_cpu_tstates=saved['summary']['real_tstates'],
                          real_delta_tstates=saved['summary']['real_delta_tstates'],
                          slower_frozen_cases=[], slower_supplemental_cases=supplemental_slower,
                          qualification=saved['qualification']))

    logs = {}
    archive = ROOT/'libraries/evidence/next_f00_public'
    archive.mkdir(exist_ok=True)
    for name, minimum in (('next-f00-library-tests.log', 87),
                           ('next-f00-toolkit-tests.log', 24),
                           ('next-f00-wheel.log', None)):
        raw = (ROOT/'.tmp'/name).read_bytes()
        decoded = raw.decode('utf-8')
        if minimum is None:
            assert 'Successfully built' in decoded
            count = None
        else:
            assert '\nOK' in decoded and not re.search(r'\n(?:FAILED|ERROR)', decoded)
            count = int(re.search(r'Ran (\d+) tests', decoded)[1])
            assert count >= minimum
        compressed = gzip.compress(raw, mtime=0)
        (archive/(name+'.gz')).write_bytes(compressed)
        logs[name] = dict(tests=count, sha256=sha(compressed), decoded_sha256=sha(raw))

    frozen = json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    resources = frozen['original_resources'] + frozen['added_pinned_resources']
    assert len(resources) == 6
    for row in resources:
        path = ROOT/'libraries'/row['package']/'src'/row['package']/'asm'/row['file']
        assert sha(path.read_bytes()) == row['sha256']

    wheel_file_checks = {}
    with tempfile.TemporaryDirectory(dir=ROOT/'.tmp', prefix='next-f00-wheel-') as temporary:
        folder = Path(temporary)
        installed = folder/'installed'
        installed.mkdir()
        for path, package in ((args.zx0_wheel, 'zx0'), (args.lzsa_wheel, 'lzsa')):
            with zipfile.ZipFile(path) as wheel:
                assert all(not Path(name).is_absolute() and '..' not in Path(name).parts
                           for name in wheel.namelist())
                wheel.extractall(installed)
                checked = []
                for source in (ROOT/'libraries'/package/'src'/package).rglob('*'):
                    if source.is_file() and (source.suffix in ('.py', '.asm') or source.name == 'LICENSE'):
                        relative = source.relative_to(ROOT/'libraries'/package/'src').as_posix()
                        assert wheel.read(relative) == source.read_bytes(), relative
                        checked.append(relative)
                wheel_file_checks[path.name] = checked
        inputs = folder/'probes.json'
        inputs.write_text(json.dumps(probes), encoding='utf-8')
        child = """import hashlib,importlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);probes=json.loads(Path(sys.argv[2]).read_text());export_root=Path(sys.argv[3])
for index,row in enumerate(probes):
    profile=importlib.import_module(row['module']).build(**row['kwargs'])
    current=dict(regions=[dict(address=at,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()) for at,blob in profile[0]],labels=profile[1],metadata=profile[2])
    assert json.loads(json.dumps(current))==row['expected']
    package='zx0' if row['codec']=='zx0' else 'lzsa'
    destination=export_root/str(index)
    importlib.import_module(package+'.export').export(destination,*profile)
    restored=[];assembly=(destination/'decoder.asm').read_text()
    for line in assembly.splitlines():
        if line.startswith('org '):restored.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):restored[-1][1].extend(int(v[1:],16) for v in line[3:].split(','))
    assert [(at,bytes(blob)) for at,blob in restored]==profile[0]
    if row['module']=='lzsa.hot':
        assert 'initialization' in assembly and '10 T' in assembly
for mode in ('literals','nibble','combined'):
    from lzsa.__main__ import main
    destination=export_root/('cli-'+mode)
    sys.argv=['lzsa','build','--profile','hot-'+mode+'-block','--core','0x8000','--core-limit','0xb000','--output',str(destination)]
    main()
    from lzsa.hot import build
    p=build(mode,core=0x8000,core_limit=0xb000)
    metadata=json.loads((destination/'metadata.json').read_text())
    assert all(metadata[k]==v for k,v in json.loads(json.dumps(p[2])).items())
assert not any(name=='z80' or name=='toolkit' or name.startswith('numpy') for name in sys.modules)
print(json.dumps(dict(exports=len(probes),cli_profiles=3)))
"""
        result = subprocess.run([sys.executable, '-I', '-c', child, str(installed),
                                 str(inputs), str(folder/'exports')], check=True,
                                capture_output=True, text=True)
        smoke = json.loads(result.stdout.splitlines()[-1])
        assert smoke == dict(exports=74, cli_profiles=3)

    from test_libraries import profiles
    assert profiles() == json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    sources = [Path(__file__)]
    for package in ('zx0', 'lzsa'):
        sources.extend((ROOT/'libraries'/package/'src'/package).glob('*.py'))
    report = dict(date=date.today().isoformat(), complete=True, release=False,
                  resident_only=True, current_public_calls=calls, proof_sha256=used,
                  preceding_table_calls_exact=68, preceding_e01_calls_exact=18,
                  preceding_e01_public_proof_sha256=used['next_e01_public_verification.json'],
                  legacy_profiles_exact=31, upstream_resources_exact=6, archived_logs=logs,
                  isolated_wheel_exports=74, isolated_cli_profiles=3,
                  source_changes_since_native_matrix=changed_native_sources,
                  native_cases_reexecuted=0, native_evidence_reused_by_exact_bytes_and_labels=True,
                  initialization=dict(external_target_initializer_required=False,
                      separately_excluded_target_initialization_tstates=0,
                      per_block_initialization_tstates_included=44,
                      eof_restoration_and_RET_tstates_included=28,
                      real_corpus_blocks=21,real_entry_initialization_tstates_included=924,
                      real_eof_restoration_and_RET_tstates_included=588,
                      timed_path='start through final RET, including per-block setup and EOF',
                      dispatch_tables='512 precomputed bytes emitted in the loaded library image',
                      future_rule='Include any required one-time Z80 preparation in benchmark totals; show setup and decode components'),
                  default_instruction_delta_tstates=0, payload_delta_bytes=0,
                  wheels={path.name:sha(path.read_bytes()) for path in (args.zx0_wheel, args.lzsa_wheel)},
                  wheel_source_and_resources_exact=wheel_file_checks,
                  source_sha256_lf={path.relative_to(ROOT).as_posix():sha(path.read_bytes().replace(b'\r\n', b'\n')) for path in sources},
                  exclusions=['coroutine/guarded qualification', 'ULA/WAIT', 'physical disk/ROM', 'movie timing'])
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(complete=True, public_calls=3, preceding_calls=68, **smoke)))


if __name__ == '__main__':
    main()
