"""Authenticate the saved native platform proof without rerunning benchmarks.

Compiled CPU/bus/generator identities must match. Decoder modules may acquire
new optional features later: the two baseline emitted layouts/ABIs must still
match the actually executed bytes, and source differences are reported rather
than attributed to the old run. This verifier is not a new native execution.
"""
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'emulator/evidence'
sys.path[:0] = [str(ROOT/'libraries/zx0/src'),str(ROOT/'libraries/lzsa/src')]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(name):
    raw = (EVIDENCE/name).read_bytes()
    return json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)


def source_check(mapping):
    for path,expected in mapping.items():
        assert sha((ROOT/path).read_bytes().replace(b'\r\n',b'\n')) == expected,path


def main():
    build = read('native_build.json')
    native = read('native_comparison.json.gz')
    spectrum = read('spectrum_decoder_baseline.json.gz')
    assert native['complete'] and spectrum['complete']
    assert native['abi_version'] == build['abi_version'] == 2
    assert native['dll_sha256'] == build['dll_sha256']
    assert native['native_build_manifest'] == build
    source_check(build['source_sha256_lf'])
    source_check(native['source_hashes_lf'])
    assert len(native['blocks']) == 1148
    assert all(row['full_64k_memory_exact'] for row in native['blocks'])
    differences = []
    for row in native['blocks']:
        changed = row.get('undocumented_flag_differences',{})
        if changed:
            assert row['codec'] == 'lzsa2' and not row['case'].startswith('real-')
            assert set(changed) == {'alt_af'}
            assert changed['alt_af']['xor'] in (8,32,40)
            assert row['documented_flags_and_preserved_registers_exact']
            differences.append(dict(case=row['case'],**changed['alt_af']))
    assert len(differences) == 10
    for codec,count,total in (('zx0',473,139892818),('lzsa2',675,14944429)):
        rows = [row for row in native['blocks'] if row['codec'] == codec]
        assert len(rows) == count
        assert sum(row['tstates'] for row in rows if row['case'].startswith('real-')) == total
    for path,expected in native['native_proof_sha256'].items():
        path = path.replace('\\','/')
        file = ROOT/path if path.startswith('libraries/') else ROOT/'libraries/evidence'/path
        assert sha(file.read_bytes()) == expected,path
    final = spectrum['final_build_revalidation']
    assert final['complete'] and final['compiled_c_and_headers_current']
    assert final['native_library']['sha256'] == native['dll_sha256']
    assert final['compiled_source_sha256_lf'] == build['source_sha256_lf']
    observed_sources = dict(final['source_sha256_lf'])
    for update in final.get('post_revalidation_reporting_updates',[]):
        observed_sources[update['path']] = update['source_sha256_lf']
    source_check({path:expected for path,expected in observed_sources.items()
                  if path.startswith('emulator/')})
    assert len(spectrum['blocks']) == 1092 and len(spectrum['irq_probes']) == 300
    assert final['exact_machine_result_cases'] == 1392
    assert not spectrum['contention'] and not spectrum['release']
    for row in spectrum['blocks']+spectrum['irq_probes']:
        assert row['exact'] and row['final_memory_verified']
        assert len(row['final_physical_banks']) == 8
        assert not row['live_source_order_guard'] and not row['live_write_guard']
        assert not row['contention'] and not row['rom_booted']
        assert row['bus_state']['unmodeled_port_reads'] == row['bus_state']['unmodeled_port_writes'] == 0
        if row['interrupts']:
            assert row['tstates'] == row['plain_tstates']+95*row['irq_acknowledgements']
        else:
            assert row['tstates'] == row['original_tstates']
    from zx0.maximum import build as zx_build
    from lzsa.hybrid import build as lz_build
    for codec,current in (('zx0',zx_build(prefix_cap=228,shared_prefixes=True)),('lzsa2',lz_build('fast'))):
        recorded = spectrum['profiles'][codec]
        assert [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in current[0]] == recorded['regions']
        assert current[2]['entry'] == recorded['metadata']['entry']
        assert current[2]['patched_addresses'] == recorded['metadata']['patched_addresses']
        assert current[2]['service_memory_bytes'] == recorded['metadata']['service_memory_bytes']
    log = gzip.decompress((EVIDENCE/'platform-tests.log.gz').read_bytes()).decode()
    assert re.search(r'Ran 31 tests',log) and '\nOK' in log and '\nFAILED' not in log
    result = dict(date=date.today().isoformat(),complete=True,release=False,
        native_abi=2,spectrum_bus_abi=1,unit_integration_tests=31,
        native_cases=1148,spectrum_normal_cases=1092,spectrum_irq_probes=300,
        final_artifact_revalidated_configurations=1392,
        real_cpu_tstates=dict(zx0=139892818,lzsa2=14944429),
        median_guarded_host_speedup=native['median_guarded_speedup'],
        clobbered_undocumented_flag_differences=differences,
        compiled_sources_exact=True,current_baseline_emitted_regions_abi_and_service_exact=True,
        library_source_matches_observed={path:sha((ROOT/path).read_bytes().replace(b'\r\n',b'\n')) == expected
            for path,expected in observed_sources.items() if path.startswith('libraries/')},
        artifacts={path.name:dict(sha256=sha(path.read_bytes()),
            decoded_sha256=sha(gzip.decompress(path.read_bytes())) if path.name.endswith('.gz') else None)
            for path in sorted(EVIDENCE.iterdir()) if path.is_file() and path.name != 'verification.json'},
        exclusions=['instruction-level ULA contention','live banked source/write guards','ROM boot',
                    'coroutine/guarded supplier qualification','AY/disk/movie release'],
        verification_source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')))
    (EVIDENCE/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({key:result[key] for key in ('complete','unit_integration_tests','native_cases',
        'spectrum_normal_cases','spectrum_irq_probes','median_guarded_host_speedup')}))


if __name__ == '__main__':
    main()
