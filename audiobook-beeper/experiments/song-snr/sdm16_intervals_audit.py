"""Independent full-input traversal and fixed-memory ledger for PCM16 tables.

The audit follows serialized root pointers and variable-length records for
every input, rather than reusing the producer's interval boundaries. Native
execution remains a separate proof; a compact host table is not a player.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_component(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    listed = set()
    for item in manifest['artifacts']:
        path = folder / item['path']
        assert path.is_relative_to(folder)
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
        listed.add(item['path'])
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*')
              if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts}
    assert actual == listed and len(listed) == manifest['files']
    return len(listed)


def traverse(folder, bits, catalogue, states, variant):
    prefix = 'hybrid' if variant == 'raw' else f'hybrid-{variant}'
    data = np.frombuffer((folder / f'{prefix}-intervals.bin').read_bytes(), dtype='<u2')
    root = np.fromfile(folder / f'hybrid-root-high{bits}.bin', '<u2').reshape(len(states), 1 << bits)
    stride = 4 if variant == 'inlineC' else 3
    dictionary = np.fromfile(folder / f'{prefix}-word-dictionary.bin', 'u1').reshape(-1, stride)
    if variant == 'raw':
        params = np.frombuffer((folder / 'hybrid-q-parameters.bin').read_bytes(),
                               dtype=np.dtype([('m', 'i1'), ('threshold', '<u2')]))
    elif variant == 'compactC':
        constants = np.fromfile(folder / 'hybrid-compactC-parameters.bin', '<u2').astype('i4')
    u = np.arange(65536, dtype='i4')
    maximum = 0
    for row, seed in enumerate(states):
        pointers = root[row, u >> (16 - bits)].astype('i4') // 2
        visits = np.ones(65536, 'i4')
        while True:
            advance = u > data[pointers]
            if not advance.any():
                break
            payload = data[pointers[advance] + 1]
            pointers[advance] += 2 + ((payload >> 13) & 1)
            visits[advance] += 1
            assert visits.max() <= 65536
        maximum = max(maximum, int(visits.max()))
        payload = data[pointers + 1]
        entries = dictionary[payload & 2047].astype('i4')
        words = entries[:, 0] * 256 + entries[:, 1]
        if variant == 'raw':
            area = entries[:, 2] + ((payload >> 11) & 1) * 256
            q = seed // 2 + (u >> 9) - params['m'][area] - ((u & 511) < params['threshold'][area])
            q = np.clip(q, 0, 15)
        else:
            if variant == 'compactC':
                constant = constants[entries[:, 2] + ((payload >> 11) & 1) * 256]
            else:
                constant = entries[:, 2] + entries[:, 3] * 256
            difference = ((u - constant + 32768) & 65535) - 32768
            q = seed // 2 + (difference >> 9)
            assert q.min() >= 0 and q.max() <= 15
        recent = ((payload >> 12) & 1).astype('i4')
        has_cut = (payload & 8192) != 0
        recent[has_cut] |= u[has_cut] >= data[pointers[has_cut] + 2]
        np.testing.assert_array_equal(words, catalogue['words'][:, seed])
        np.testing.assert_array_equal(q * 2 + recent, catalogue['successors'][:, seed])
    return dict(variant=variant, high_bits=bits, full_input_cells=len(states) * 65536,
                maximum_actual_interval_visits=maximum, all_words_and_successors_exact=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=HERE / 'evidence/sdm16-intervals')
    parser.add_argument('--output', type=Path, default=HERE / 'evidence/sdm16-intervals-audit')
    args = parser.parse_args()
    folder, output = args.evidence.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((folder / 'manifest.json').read_text())
    for name, item in manifest['artifact_files'].items():
        path = folder / name
        assert path.is_relative_to(folder)
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*')
              if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts}
    assert actual == set(manifest['artifact_files'])
    table = HERE / 'evidence/sdm16-architecture/model-b-all-pcm16-cells.npz'
    report = json.loads((folder / 'report.json').read_text())
    assert report['complete'] and digest(table) == report['table_sha256']
    producer = HERE / 'sdm16_intervals.py'
    assert digest(producer) == report['producer_sha256']
    catalogue = np.load(table)
    states = report['reachable_states']
    checks = [traverse(folder, bits, catalogue, states, variant)
              for variant in ('raw', 'compactC', 'inlineC') for bits in (4, 5, 6, 8)]
    failed = HERE / 'evidence/sdm16-intervals-attempt-1'
    failed_manifest = json.loads((failed / 'manifest.json').read_text())
    assert failed_manifest['complete'] is False
    for name, item in failed_manifest['artifact_files'].items():
        path = failed / name
        assert path.is_relative_to(failed)
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256']
    qfolder = HERE / 'evidence/sdm16-qphase'
    qfiles = verify_component(qfolder)
    qreport = json.loads((qfolder / 'report.json').read_text())
    assert qreport['catalogue_sha256'] == digest(table)
    qtrace = gzip.decompress((qfolder / 'native-qcodes.u8.gz').read_bytes())
    assert qtrace == (catalogue['successors'] // 2).astype('u1').tobytes()
    assert hashlib.sha256(qtrace).hexdigest() == qreport['exhaustive_native']['output_qcodes_sha256']
    assert sum(item[1] for item in qreport['core_instruction_table']) == 36
    assert bytes.fromhex('dd7d95dd7c9ccb2f83') in (qfolder / 'kernel.bin').read_bytes()
    assert gzip.decompress((qfolder / 'generator.py.gz').read_bytes()) == (HERE / 'sdm16_qphase.py').read_bytes()
    sfolder = HERE / 'evidence/sdm16-selector'
    sfiles = verify_component(sfolder)
    sreport = json.loads((sfolder / 'report.json').read_text())
    assert 42 + 8 + 3 * 17 + 44 + 10 == sreport['worst_3_compare_path_tstates'] == 155
    assert 449 - 26 - 70 + 155 == sreport['source_period_if_naively_substituted_without_Pentagon_pacing_tstates'] == 508

    # A deliberately optimistic ledger uses the existing complete UI player's
    # measured fixed code/worker spans. It charges no new selector code, new
    # alignment gaps, retained 70-T lookup, or duplicate tables. An overflow of
    # this ledger rejects a literal drop-in; it is not an impossibility bound.
    baseline = HERE / 'evidence/pacing448-execution/sea_foam/player.json'
    old = json.loads(baseline.read_text())['player_labels']
    pattern_report = json.loads((HERE / 'evidence/sdm16-patterns/report.json').read_text())
    roots = report['hybrid']['root_formats']
    constants = dict(total_fixed_ram=32768, TRDOS_workspace=1024, cache_workspace=16,
                     decoder_rows=89 * 16 * 4, startup_span=old['first_base'] - 0x8000,
                     worker_span=old['stream_worker_end'] - old['worker_origin'],
                     UI_code_before_lookup=old['pcm_high'] - old['code_end'],
                     literal_to_pattern_address_maps=256 * 4)
    available = constants['total_fixed_ram'] - constants['TRDOS_workspace'] - constants['cache_workspace']
    fixed_cost = sum(constants[key] for key in ('decoder_rows', 'startup_span', 'worker_span',
                                               'UI_code_before_lookup', 'literal_to_pattern_address_maps'))
    ledgers = []
    for root in roots:
        if root['high_bits'] not in (4, 5, 8):
            continue
        for variant, key in (('raw', 'total_table_bytes_including_state_map'),
                             ('compactC', 'compactC_total_bytes'), ('inlineC', 'inlineC_total_bytes')):
            for pattern, sizes in pattern_report['sizes'].items():
                needed = fixed_cost + root[key] + sizes['pattern_code_bytes']
                ledgers.append(dict(table_variant=variant, root_high_bits=root['high_bits'],
                                    pattern_variant=pattern, minimum_accounted_bytes=needed,
                                    fixed_available_bytes=available, surplus_bytes=available - needed,
                                    literal_drop_in_fits=needed <= available))
    audit = dict(complete=True, checked_artifact_files=len(actual),
                 preserved_failed_attempt_artifacts_checked=len(failed_manifest['artifact_files']),
                 serialized_root_checks=checks, accounted_components=constants,
                 qphase_artifacts_checked=qfiles, selector_artifacts_checked=sfiles,
                 all_saved_native_qcodes_match_cells=len(qtrace),
                 qcore_literal_bytes_and_36T_count_verified=True,
                 selector_155T_and_508T_substitution_counts_verified=True,
                 optimistic_fixed_memory_ledgers=ledgers,
                 current_UI_player_metadata_sha256=digest(baseline),
                 independent_instruction_or_disk_execution=False,
                 full_player_fit_verified=False, release_accepted=False,
                 limit='Measured inherited layout charges no new selector or alignment. Rearranging persistent/cold code could change this ledger; actual allocation and timing are still required.')
    (output / 'report.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    (output / 'auditor.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(), mtime=0))
    items = {p.name: dict(bytes=p.stat().st_size, sha256=digest(p)) for p in sorted(output.iterdir())
             if p.is_file() and p.name != 'manifest.json'}
    (output / 'manifest.json').write_text(json.dumps(dict(artifact_files=items), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(audit))


if __name__ == '__main__':
    main()
