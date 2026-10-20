"""Authenticate the sole public cap255 selection without rerunning native code.

Exact regions and every label bind the installed API to the frozen E04 raw
qualification. A separate isolated copy of the pre-E04 public sources checks
all preceding74 layouts and complete metadata. Generated tables/accounting
documents are deliberately not current runtime-source authorities.
"""
import argparse
from datetime import date
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
for package in ('zx0', 'lzsa'):
    sys.path.insert(0, str(ROOT / 'libraries' / package / 'src'))

EXPECTED_PROOFS = {
    'next_e04_full.json.gz': '7c0b3565b19e4da0c0de0e13f96fc9ea2a1eea0a96cf05e4edc34568f4bae009',
    'next_e04_prior_sources.json.gz': '083a6dbe7a1fa21df378d7c518906d8ddb8d2610f3a5a8febb5fe63665d71a3b',
    'next_s01_public_verification.json': '2a8fecf2b3341ac99ee91cb0eb6e39589cdfc59e71d9b44f6eacc3487cf45618',
}


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def normalized(value):
    return json.loads(json.dumps(value))


def layout(profile):
    return dict(regions=[dict(address=at, bytes=len(blob), sha256=sha(blob))
                         for at, blob in profile[0]],
                labels=profile[1], metadata=normalized(profile[2]))


def identity(current, saved):
    assert current['regions'] == saved['regions']
    assert current['labels'] == saved['labels']


def qualification(rows, baselines):
    """Recheck saved semantic/cost witnesses, rather than executing a decoder."""
    for row, base in zip(rows, baselines):
        assert row['case'] == base['case']
        assert row['model_exact'] and row['c_guarded']['exact']
        assert base['c_guarded']['exact'] and base['E01_native_exact']
        assert row['baseline_tstates'] == base['c_guarded']['tstates']
        assert row['word_entries'] == base['word_entries']
        assert row['delta_tstates'] == -135 * row['word_entries']
        assert row['c_guarded']['tstates'] == row['baseline_tstates'] + row['delta_tstates']
        native_modes(row, base['host'])


def native_modes(row, host):
    modes = row['native']
    assert set(modes) == {'plain', 'irq', 'relocated', 'inplace_plain', 'inplace_irq', 'inplace_relocated'}
    for name, result in modes.items():
        assert result['exact']
        assert result['copies']['word_entries'] == row['word_entries']
        assert result['write_input_cursors_sha256'] == host['write_input_cursors_sha256']
        assert result['stack_bytes'] <= (10 if name in ('irq', 'inplace_irq') else 4)
        if name not in ('irq', 'inplace_irq'):
            assert result['tstates'] == row['c_guarded']['tstates']
        if name.startswith('inplace_'):
            assert result['host_read_order_exact'] and result['code_protected'] and result['raw_abi_exact']
            assert result['host_minimum_input_start'] == result['native_minimum_input_start']
        for entry in result['copies']['word_residuals']:
            assert entry['incoming_bc'] >= 256
            assert entry['remaining_bc'] == entry['incoming_bc'] - 255 >= 1


def archived_layouts(prior, rows, directory):
    """Rebuild old public calls in a clean process with the five old modules."""
    installed = directory / 'pre-e04'
    installed.mkdir()
    for package in ('zx0', 'lzsa'):
        shutil.copytree(ROOT / 'libraries' / package / 'src' / package, installed / package,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    overlaid = []
    for relative, saved in prior.items():
        assert sha(saved['text'].encode()) == saved['sha256_lf'], relative
        if relative.startswith('libraries/zx0/src/zx0/') and relative.endswith('.py'):
            destination = installed / relative.removeprefix('libraries/zx0/src/')
            destination.write_text(saved['text'], encoding='utf-8', newline='\n')
            overlaid.append(relative)
    assert len(overlaid) == 5
    inputs = directory / 'old-calls.json'
    outputs = directory / 'old-layouts.json'
    inputs.write_text(json.dumps(rows), encoding='utf-8')
    child = """import hashlib,importlib,json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);rows=json.loads(Path(sys.argv[2]).read_text());results=[]
for row in rows:
    p=importlib.import_module(row['builder'].removesuffix('.build')).build(**row['kwargs'])
    results.append(dict(regions=[dict(address=at,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()) for at,blob in p[0]],labels=p[1],metadata=p[2]))
Path(sys.argv[3]).write_text(json.dumps(results),encoding='utf-8')
assert not any(name=='z80' or name=='toolkit' or name.startswith('numpy') for name in sys.modules)
"""
    subprocess.run([sys.executable, '-I', '-c', child, str(installed), str(inputs), str(outputs)],
                   capture_output=True, text=True, check=True)
    return json.loads(outputs.read_text()), overlaid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zx0-wheel', type=Path, required=True)
    parser.add_argument('--lzsa-wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sources = [Path(__file__), ROOT / 'libraries/tests/test_maximum255.py']
    for package in ('zx0', 'lzsa'):
        sources.extend((ROOT / 'libraries' / package / 'src' / package).glob('*.py'))
    launch_sources = {path.relative_to(ROOT).as_posix(): sha(path.read_bytes().replace(b'\r\n', b'\n'))
                      for path in sources}
    proofs = {}
    def read(name):
        blob = (ROOT / 'libraries/evidence' / name).read_bytes()
        proofs[name] = sha(blob)
        if name in EXPECTED_PROOFS:
            assert proofs[name] == EXPECTED_PROOFS[name], name
        return json.loads(gzip.decompress(blob) if name.endswith('.gz') else blob)

    native = read('next_e04_full.json.gz')
    prior = read('next_e04_prior_sources.json.gz')
    s01 = read('next_s01_public_verification.json')
    assert native['complete'] and native['C_complete'] and native['raw_qualification_complete']
    assert native['launch_source_sha256_lf'] == native['final_source_sha256_lf']
    changed_sources = []
    for relative, digest in native['final_source_sha256_lf'].items():
        current = sha((ROOT / relative).read_bytes().replace(b'\r\n', b'\n'))
        if current != digest:
            assert relative in prior and prior[relative]['sha256_lf'] == digest, relative
            assert sha(prior[relative]['text'].encode()) == digest
            changed_sources.append(relative)
    for relative, digest in s01['source_sha256_lf'].items():
        current = sha((ROOT / relative).read_bytes().replace(b'\r\n', b'\n'))
        if current != digest:
            assert relative in prior and prior[relative]['sha256_lf'] == digest, relative
    for name, digest in native['archived_proofs'].items():
        read(name)
        assert proofs[name] == digest

    table = json.loads(prior['libraries/evidence/decoder_variants_verification.json']['text'])
    assert table['complete'] and len(table['profiles']) == 74
    rows = table['profiles']
    probes = []
    previous = []
    current_layouts = []
    for row in rows:
        module = row['builder'].removesuffix('.build')
        profile = importlib.import_module(module).build(**row['kwargs'])
        current = layout(profile)
        assert current['regions'] == row['regions'], row['name']
        code = sum(len(blob) for _, blob in profile[0])
        assert code == row['code_state_table_padding_bytes']
        if 'service_memory_bytes' in profile[2]:
            assert profile[2]['service_memory_bytes'] == row['service_bytes']
        current_layouts.append(current)
        previous.append({key: row[key] for key in
                         ('name', 'codec', 'kind', 'builder', 'kwargs', 'service_bytes', 'real_cpu_tstates', 'regions')})
        probes.append(dict(module=module, kwargs=row['kwargs'], codec=row['codec'], expected=current))
    with tempfile.TemporaryDirectory(dir=ROOT / '.tmp', prefix='next-e04-prior-') as temporary:
        archived, overlaid = archived_layouts(prior, rows, Path(temporary))
        for row, current, old in zip(rows, current_layouts, archived):
            assert current == old, row['name']

    # Keep the current source authority for S01/F00 separate from the original
    # native execution provenance: old reports and source hashes stay intact.
    for row in s01['current_public_calls']:
        p = importlib.import_module(row['module']).build(**row['kwargs'])
        assert layout(p) == {key: row[key] for key in layout(p)}
    f00 = read('next_f00_public_verification.json')
    for row in f00['current_public_calls']:
        p = importlib.import_module(row['module']).build(**row['kwargs'])
        assert layout(p) == {key: row[key] for key in layout(p)}
    e01_lz = read('next_e01_lzsa_full.json.gz')
    for name, row in e01_lz['profiles'].items():
        builder = importlib.import_module(row['module']).build
        for origin, field in ((0x8000, 'candidate'), (0x9103, 'relocated')):
            current = layout(builder(**dict(row['kwargs'], cold_match_extension=True, core=origin)))
            assert current == {key: row[field][key] for key in current}, (name, origin)

    from zx0.maximum_branches import build
    from next_e04_profiles import binary_oracle
    saved = native['candidate']
    baseline = native['baseline']
    assert saved['C_complete'] and saved['native_complete'] and saved['qualification']['complete']
    assert len(saved['blocks']) == len(baseline['blocks']) == 473
    assert len(saved['supplemental']) == 36 and len(saved['alignments']) == 256
    identity(layout(build(prefix_cap=228, policy='fast')), baseline)
    assert baseline['real_tstates'] == 139552884
    assert baseline['metadata']['service_memory_bytes'] == 7517
    qualification(saved['blocks'], baseline['blocks'])
    for row in saved['supplemental']:
        assert row['baseline_protected']['exact'] and row['c_guarded']['exact']
        assert row['delta_tstates'] == -135 * row['word_entries']
        assert row['c_guarded']['tstates'] == row['baseline_tstates'] + row['delta_tstates']
        native_modes(row, row['host'])
    assert len(saved['boundary_coverage']) == 36
    assert {(r['family'], r['phase'], r['decoded_length']) for r in saved['boundary_coverage']} == {
        (family, phase, count) for family in ('length', 'literals', 'reuse')
        for phase in (1, 3, 5, 7) for count in (255, 256, 257)}
    assert len(saved['FFFF_output_cursor_probes']) == 3
    for row in saved['FFFF_output_cursor_probes']:
        assert row['output_cursor'] == 0xffff and all(result['exact'] for result in row['modes'].values())
    for origin, field in ((0x8000, None), (0x9103, 'relocated'), (0x0800, 'high_word'), (0x0703, 'high_word_relocated')):
        p = build(prefix_cap=255, policy='fast', core=origin)
        current = layout(p)
        identity(current, saved if field is None else saved[field])
        assert p[:2] == binary_oracle(origin)[:2]
        assert p[2]['service_memory_bytes'] == 8165
        assert len(p[2]['conditional_branch_sites']) == 61
        for site in p[2]['conditional_branch_sites']:
            assert site['target_address'] == p[1][site['target']]
            assert -128 <= site['final_displacement'] <= 127
        probes.append(dict(module='zx0.maximum_branches', kwargs=dict(prefix_cap=255, policy='fast', core=origin),
                           codec='zx0', expected=current, new_profile=True))
    for row in saved['alignments']:
        p = build(prefix_cap=255, policy='fast', core=row['origin'])
        assert layout(p)['regions'] == row['regions']
        assert sha(json.dumps(p[1], sort_keys=True).encode()) == row['labels_sha256']
        assert p[:2] == binary_oracle(row['origin'])[:2]
        assert p[2]['service_memory_bytes'] == row['service_bytes'] == 8165
        assert row['reference_IRQ_inclusive_bytes'] == 8184
    assert len(probes) == 78

    all_rows = saved['blocks']
    real = [row for row in all_rows if row['real']]
    summary = saved['summary']
    assert len(real) == 364 and sum(r['word_entries'] for r in real) == 46
    assert sum(r['word_entries'] for r in all_rows) == 186
    assert summary['real_tstates'] == sum(r['c_guarded']['tstates'] for r in real) == 139546674
    assert summary['all_tstates'] == sum(r['c_guarded']['tstates'] for r in all_rows) == 161800568
    assert summary['slower_cases'] == [] and summary['faster_cases'] == 105 and summary['equal_cases'] == 368
    assert sum(r['baseline_tstates'] for r in real) == 139552884
    assert all(r['delta_tstates'] <= 0 for r in all_rows + saved['supplemental'])
    assert native['initialization']['startup_tstates'] == 46 and native['initialization']['offset_reset_tstates'] == 20
    assert native['initialization']['all_setup_inside_start_through_EOF']
    assert not native['initialization']['target_initializer_required']
    cold = real[0]
    initialization = dict(per_block_setup_tstates_included=46, offset_reset_tstates_included=20,
        external_target_initializer_tstates=0, caller_CALL_excluded_tstates=17,
        timer_scope='Each cold block enters dzx0_mega; includes reset/cache setup, decode, EOF and RET. Caller CALL17 and ABI argument publication are outside this entry boundary.',
        real=dict(blocks=364, setup_tstates=16744, remaining_tstates=139529930, total_tstates=139546674),
        all=dict(blocks=473, setup_tstates=21758, remaining_tstates=161778810, total_tstates=161800568),
        cold_first_real=dict(case=cold['case'], payload_sha256=cold['payload_sha256'], raw_sha256=cold['raw_sha256'],
            total_tstates=cold['c_guarded']['tstates'], setup_tstates=46, remaining_tstates=cold['c_guarded']['tstates']-46),
        baseline_per_block_setup_tstates_included=46,
        static_tables='No table or target-side table generator; emitted image/offset operand is resident. Offset is reset on every measured entry.')
    for key in ('real', 'all'):
        scope = initialization[key]
        assert scope['setup_tstates'] == 46 * scope['blocks']
        assert scope['setup_tstates'] + scope['remaining_tstates'] == scope['total_tstates']
    profile = build(prefix_cap=255, policy='fast')
    current = layout(profile)
    origin, blob = profile[0][0]
    assert blob[:5] == bytes.fromhex('01ffffed43')
    assert int.from_bytes(blob[5:7], 'little') == profile[1]['dzx0m_last_offset+1']
    assert blob[7:9] == bytes.fromhex('03c3')
    assert int.from_bytes(blob[9:11], 'little') == profile[1]['dzx0m_literals0']
    initialization['entry_instruction_ledger'] = [
        dict(address=origin, instruction='LD BC,FFFFh', tstates=10),
        dict(address=origin+3, instruction='LD (last_offset+1),BC', tstates=20),
        dict(address=origin+7, instruction='INC BC', tstates=6),
        dict(address=origin+8, instruction='JP literals0', tstates=10)]
    assert sum(row['tstates'] for row in initialization['entry_instruction_ledger']) == 46
    assert current['metadata']['qualified_corpus']['real_tstates'] == 139546674
    assert current['metadata']['qualified_corpus']['real_baseline_tstates'] == 139552884
    assert current['metadata']['qualified_corpus']['slower_cases'] == 0
    assert current['metadata']['baseline_service_memory_bytes'] == 7517
    assert current['metadata']['service_delta_bytes'] == 648
    assert current['metadata']['startup_tstates'] == 46
    assert current['metadata']['offset_reset_tstates'] == 20
    assert not current['metadata']['target_initializer_required']
    assert current['metadata']['conditional_branch_lineage']['historical_slower_cases'] == 103
    irq_metadata = build(prefix_cap=255, irq_code_bytes=13, irq_stack_bytes=6)[2]
    assert irq_metadata['service_memory_bytes'] == 8184
    assert irq_metadata['baseline_service_memory_bytes'] == 7536
    assert irq_metadata['service_delta_bytes'] == 648
    calls = [dict(module='zx0.maximum_branches', kwargs=dict(prefix_cap=255, policy='fast'), codec='zx0',
        native_profile='255-fast', native_proof='next_e04_full.json.gz', **current,
        service_bytes=8165, real_cpu_tstates=139546674, qualification=saved['qualification'], initialization=initialization,
        primary_baseline=dict(module='zx0.maximum_branches', kwargs=dict(prefix_cap=228, policy='fast'),
            service_bytes=7517, real_cpu_tstates=139552884, service_delta_bytes=648, real_delta_tstates=-6210),
        slower_frozen_cases=summary['slower_cases'], slower_supplemental_cases=[],
        inherited_E01_branch_lineage=native['inherited_E01_branch_lineage'])]

    logs = {}
    archive = ROOT / 'libraries/evidence/next_e04_public'
    archive.mkdir(exist_ok=True)
    for name, minimum in (('next-e04-library-tests.log', 113), ('next-e04-toolkit-tests.log', 24), ('next-e04-wheel.log', None)):
        blob = (ROOT / '.tmp' / name).read_bytes()
        text = blob.decode('utf-8')
        if minimum is None:
            assert 'Successfully built' in text
            count = None
        else:
            assert '\nOK' in text and not re.search(r'\n(?:FAILED|ERROR)', text)
            count = int(re.search(r'Ran (\d+) tests', text)[1])
            assert count >= minimum, (name, count, minimum)
        compressed = gzip.compress(blob, mtime=0)
        (archive / (name + '.gz')).write_bytes(compressed)
        logs[name] = dict(tests=count, sha256=sha(compressed), decoded_sha256=sha(blob))
    resources = json.loads((ROOT / 'libraries/second_pass_verification.json').read_text())
    resources = resources['original_resources'] + resources['added_pinned_resources']
    assert len(resources) == 6
    for row in resources:
        assert sha((ROOT / 'libraries' / row['package'] / 'src' / row['package'] / 'asm' / row['file']).read_bytes()) == row['sha256']
    wheel_checks = {}
    with tempfile.TemporaryDirectory(dir=ROOT / '.tmp', prefix='next-e04-wheel-') as temporary:
        folder = Path(temporary)
        installed = folder / 'installed'
        installed.mkdir()
        for path, package in ((args.zx0_wheel, 'zx0'), (args.lzsa_wheel, 'lzsa')):
            with zipfile.ZipFile(path) as wheel:
                assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in wheel.namelist())
                wheel.extractall(installed)
                checked = []
                for source in (ROOT / 'libraries' / package / 'src' / package).rglob('*'):
                    if source.is_file() and (source.suffix in ('.py', '.asm') or source.name == 'LICENSE'):
                        relative = source.relative_to(ROOT / 'libraries' / package / 'src').as_posix()
                        assert wheel.read(relative) == source.read_bytes(), relative
                        checked.append(relative)
                wheel_checks[path.name] = checked
        inputs = folder / 'probes.json'
        inputs.write_text(json.dumps(probes), encoding='utf-8')
        child = """import hashlib,importlib,json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);probes=json.loads(Path(sys.argv[2]).read_text());destination=Path(sys.argv[3])
def restored(path):
    rows=[]
    for line in path.read_text().splitlines():
        if line.startswith('org '):rows.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):rows[-1][1].extend(int(v[1:],16) for v in line[3:].split(','))
    return [(at,bytes(blob)) for at,blob in rows]
for index,row in enumerate(probes):
    p=importlib.import_module(row['module']).build(**row['kwargs'])
    current=dict(regions=[dict(address=at,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()) for at,blob in p[0]],labels=p[1],metadata=p[2])
    assert json.loads(json.dumps(current))==row['expected']
    package='zx0' if row['codec']=='zx0' else 'lzsa'
    output=destination/str(index);importlib.import_module(package+'.export').export(output,*p)
    assert restored(output/'decoder.asm')==p[0]
    if row.get('new_profile'):assert 'initializ' in (output/'decoder.asm').read_text().lower()
for suffix in ([],['--branch-policy','fast']):
    output=destination/('cli-'+str(len(suffix)))
    sys.argv=['zx0','build','--variant','maximum-branches','--prefix-cap','255','--core','0x8000','--output',str(output)]+suffix
    importlib.import_module('zx0.__main__').main()
    p=importlib.import_module('zx0.maximum_branches').build(prefix_cap=255,policy='fast')
    assert restored(output/'decoder.asm')==p[0]
    metadata=json.loads((output/'metadata.json').read_text())
    assert all(metadata[key]==value for key,value in json.loads(json.dumps(p[2])).items())
assert not any(name=='z80' or name=='toolkit' or name.startswith('numpy') for name in sys.modules)
assert all('/installed/' in str(Path(sys.modules[name].__file__)).replace('\\\\','/') for name in ('zx0','lzsa'))
print(json.dumps(dict(exports=len(probes),cli_profiles=2)))
"""
        result = subprocess.run([sys.executable, '-I', '-c', child, str(installed), str(inputs), str(folder / 'exports')],
                                capture_output=True, text=True, check=True)
        smoke = json.loads(result.stdout.splitlines()[-1])
        assert smoke == dict(exports=78, cli_profiles=2)
    from test_libraries import profiles
    assert profiles() == json.loads((ROOT / 'libraries/tests/decoder_baseline.json').read_text())['profiles']
    final_sources = {path.relative_to(ROOT).as_posix(): sha(path.read_bytes().replace(b'\r\n', b'\n'))
                     for path in sources}
    assert launch_sources == final_sources, 'Public authentication sources changed during verification'
    report = dict(date=date.today().isoformat(), complete=True, release=False, resident_only=True,
        current_public_calls=calls, proof_sha256=proofs,
        source_changes_since_native_matrix=sorted(changed_sources),
        source_authentication='Current installed source is authenticated here; the pre-E04 package archive remains the source provenance of the unchanged native matrix.',
        preceding_table_calls_exact=74, preceding_table_full_metadata_exact=74,
        preceding_e01_LZSA_calls_metadata_exact=12, preceding_F00_calls_exact=3, preceding_S01_calls_exact=3,
        preceding_selection_sha256=sha(json.dumps(previous, sort_keys=True, separators=(',', ':')).encode()),
        archived_public_source_overlays=overlaid,
        default_profiles_exact=31, upstream_resources_exact=6, archived_logs=logs,
        isolated_wheel_exports=78, isolated_cli_profiles=2,
        wheels={path.name: sha(path.read_bytes()) for path in (args.zx0_wheel, args.lzsa_wheel)},
        wheel_source_and_resources_exact=wheel_checks,
        all256_alignments_exact=True, four_native_placements_exact=True, independent_insertion_oracle_exact=True,
        native_cases_reexecuted=0, native_evidence_reused_by_exact_bytes_and_all_labels=True,
        source_sha256_lf=final_sources,
        initialization=initialization, benchmark_scope=initialization,
        native_execution_source_sha256_lf=native['final_source_sha256_lf'],
        native_C=native['native_C'], native_C_qualification_proofs=native['C_qualification_proofs'],
        exclusions=['Coroutine/guarded qualification', 'ULA/WAIT', 'Physical disk/ROM', 'Movie/application cold-boot timing'],
        frontier_scope='One finite measured maximum-speed choice; no global optimum claim',
        default_instruction_delta_tstates=0, payload_delta_bytes=0)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(complete=True, public_calls=1, preceding_calls=74, **smoke)))


if __name__ == '__main__':
    main()
