"""Authenticate speed-pass-3 native, producer, package and rejected-layout evidence."""
import argparse
import gzip
import json
from pathlib import Path
import sys
from unittest.mock import patch

from measure_fast_jumps import ROOT, layout, sha
from test_libraries import profiles
from lzsa.block import build as lblock
from lzsa.resumable import build as coroutine
from zx0.block import build as zblock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stream-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--library-tests', type=int, required=True)
    parser.add_argument('--toolkit-tests', type=int, required=True)
    args = parser.parse_args()
    tmp = args.stream_directory
    defaults = profiles()
    assert defaults == json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    component_path = ROOT/'libraries/evidence/fast_jumps.json'
    component = json.loads(component_path.read_text())
    assert component['complete'] and not component['release']
    for name, item in component['profiles'].items():
        for fast, key in ((False, 'baseline'), (True, 'candidate')):
            if name.startswith('zx0-'):
                generated = zblock(name.removeprefix('zx0-'), fast_jumps=fast)
            else:
                combined = name.endswith('-combined')
                options = dict(core=0x8000, core_limit=0x8400, long_copy=combined,
                               near_literals=combined, fast_jumps=fast)
                if 'coroutine' in name:
                    generated = coroutine(**options, restore_compare=combined)
                else:
                    generated = lblock(**options)
            assert layout(generated) == item[key], (name, key)
        assert item['summary']['slower_blocks'] == item['summary']['slower_slices'] == 0

    archives = []
    archive_dir = ROOT/'libraries/evidence/fast_jumps_streaming'
    archive_dir.mkdir(parents=True, exist_ok=True)

    def archive(path, name):
        raw = path.read_bytes()
        packed = gzip.compress(raw, mtime=0)
        destination = archive_dir/name
        destination.write_bytes(packed)
        item = dict(file=str(destination.relative_to(ROOT/'libraries')).replace('\\', '/'),
                    bytes=len(packed), sha256=sha(packed), decoded_sha256=sha(raw))
        archives.append(item)
        return item

    streaming = {}
    for mode in ('call', 'direct'):
        paths = [tmp/f'fast-jumps-{mode}-{stage}.json' for stage in ('before', 'after')]
        before, after = [json.loads(path.read_text()) for path in paths]
        assert before['complete'] and after['complete'] and before['cases'] == after['cases'] == 63
        assert before['stream_sha256'] == after['stream_sha256']
        assert before['baseline'] == after['baseline']
        assert len(before['blocks']) == len(after['blocks']) == len(before['independent']) == len(after['independent']) == 63
        assert before['layout']['prefix_end'] == after['layout']['prefix_end']
        assert after['layout']['core_end']-before['layout']['core_end'] == 2
        rows = []
        for old, new, independent_old, independent_new in zip(
                before['blocks'], after['blocks'], before['independent'], after['independent']):
            for field in ('decoded_bytes', 'payload_bytes', 'input_pointer', 'raw_sha256',
                          'payload_sha256', 'producer_tstates', 'sectors', 'carry_copy_bytes',
                          'input_waits', 'first_output_loaded_bytes', 'step_tstates'):
                assert old[field] == new[field], (mode, old['index'], field)
            assert old['exact'] and new['exact']
            assert len(old['slice_tstates']) == len(new['slice_tstates'])
            deltas = [b-a for a, b in zip(old['slice_tstates'], new['slice_tstates'])]
            assert not any(t > 0 for t in deltas)
            assert sum(deltas) == new['decoder_tstates']-old['decoder_tstates']
            assert independent_old['case'] == independent_new['case']
            assert len(independent_old['full_flags']) == len(independent_new['full_flags']) == 6
            for index, (a, b) in enumerate(zip(independent_old['full_flags'], independent_new['full_flags'])):
                assert a['exact'] and b['exact'] and a['input_start'] == b['input_start']
                assert a['input_waits'] == b['input_waits']
                if index != 3:  # Placement 253 also measures IRQ code; it is a correctness probe.
                    assert b['tstates'] <= a['tstates']
            rows.append(dict(case=independent_new['case'], raw_sha256=new['raw_sha256'],
                payload_sha256=new['payload_sha256'], baseline_tstates=old['decoder_tstates'],
                candidate_tstates=new['decoder_tstates'], delta_tstates=sum(deltas),
                slices=len(deltas), slower_slices=0, input_waits=len(new['input_waits']),
                injected_interrupts=sum(r['injected_interrupts'] for r in independent_new['full_flags'])))
        old, new = before['candidate'], after['candidate']
        assert old['producer_tstates'] == new['producer_tstates']
        assert old['sector_reads'] == new['sector_reads'] == 772
        assert old['sectors_exact_once'] and new['sectors_exact_once']
        streaming[mode] = dict(cases=63, real_blocks=21, placements_per_case=6,
            baseline_tstates=old['total_tstates'], candidate_tstates=new['total_tstates'],
            delta_tstates=new['total_tstates']-old['total_tstates'],
            baseline_decoder_tstates=old['decoder_tstates'], candidate_decoder_tstates=new['decoder_tstates'],
            producer_tstates=new['producer_tstates'], sectors=772, sectors_exact_once=True,
            identical_waits_producer_and_slices=True, slower_blocks=0, slower_slices=0,
            prefix_end=after['layout']['prefix_end'],
            blocks=rows)
        for path in paths:
            archive(path, path.name+'.gz')

    # Replay the exact discarded code rather than shipping a second generator.
    rejected_path = ROOT/'libraries/tests/fixtures/fast_jumps_cold_retry_rejected.json'
    rejected = json.loads(rejected_path.read_text())
    frozen_profile = ([(at, bytes.fromhex(data)) for at, data in rejected['regions']],
                      rejected['labels'], rejected['metadata'])
    sys.path.insert(0, str(ROOT/'toolkit'))
    import test_streaming_lzsa2 as guard
    import inplace_slot_input_z80 as producer
    stream = (tmp/'lzsa-stream').read_bytes()
    fits = guard.Harness(stream, 57, fast_jumps=True)
    assert fits.p['prefix_end'] <= producer.CODE
    original_limit = producer.CODE
    # This helper has only absolute branches and no address-dependent padding.
    # Reuse its measured emitted extent, with the rejected wrapper's end.
    extended_end = frozen_profile[2]['prefix_end'] + len(fits.regions[-1][1])
    assert extended_end-original_limit == 1  # The original layout has one spare byte.
    with patch.object(guard.resumable_lzsa2, 'build', return_value=frozen_profile):
        try:
            guard.Harness(stream, 57, fast_jumps=True)
        except ValueError as error:
            assert str(error) == 'streaming prefix exceeds free decoder-helper tail'
            rejection = str(error)
        else:
            raise AssertionError('discarded cold-retry expansion unexpectedly fits')
    rejected_direct = json.loads((tmp/'fast-jumps-direct-rejected-cold.json').read_text())
    assert rejected_direct['complete'] and rejected_direct['cases'] == 63
    archive(tmp/'fast-jumps-direct-rejected-cold.json', 'rejected-cold-direct.json.gz')
    archive(tmp/'fast-jumps-cold-retry-rejected.log', 'rejected-cold-call.log.gz')

    wheels = [json.loads((tmp/f'wheel-{package}/report.json').read_text()) for package in ('zx0', 'lzsa')]
    assert all(item['independent_wheel'] and item['cli_export'] and item['resources']
               and all(row['exact_export'] for row in item['fast_jump_profiles']) for item in wheels)
    producer_comparison = json.loads((tmp/'library-producer-comparison.json').read_text())
    assert len(producer_comparison) == 2 and all(r['code_labels_and_timing_rows_identical'] for r in producer_comparison)
    for name, count in (('library', args.library_tests), ('toolkit', args.toolkit_tests)):
        log = tmp/f'fast-jumps-{name}-tests.log'
        text = log.read_text(encoding='utf-8')
        assert f'Ran {count} tests in ' in text and text.rstrip().endswith('OK')
        archive(log, log.name+'.gz')
    sources = {str(path.relative_to(ROOT)).replace('\\', '/'):sha(path.read_bytes().replace(b'\r\n', b'\n'))
               for package in ('lzsa', 'zx0') for path in sorted((ROOT/'libraries'/package/'src'/package).glob('*.py'))}
    sources['toolkit/test_streaming_lzsa2.py'] = sha((ROOT/'toolkit/test_streaming_lzsa2.py').read_bytes().replace(b'\r\n', b'\n'))
    report = dict(date='2026-10-19', baseline_revision='dbde780c', complete=True, release=False,
        branch='codex/codec-speed-pass3', scope=__doc__, default_profiles=len(defaults),
        default_bytes_addresses_labels_exact=True, default_instruction_delta_tstates=0,
        cpu_report=dict(file='evidence/fast_jumps.json', sha256=sha(component_path.read_bytes())),
        streaming=streaming, archives=archives,
        rejected_cold_retries=dict(fixture=str(rejected_path.relative_to(ROOT/'libraries')).replace('\\', '/'),
            sha256=sha(rejected_path.read_bytes()), error=rejection, helper_overrun_bytes=1,
            discarded_wrapper_growth_bytes=2, original_helper_headroom_bytes=1,
            producer_origin=original_limit, final_helper_end=fits.p['prefix_end'],
            final_wrapper_size_unchanged=True, direct_only_completion=63,
            decision='retain original cold retries; use JP only in the main decoder'),
        observed_units=dict(libraries=args.library_tests, toolkit=args.toolkit_tests,
                            total=args.library_tests+args.toolkit_tests),
        isolated_wheels=wheels, original_producer_variants=producer_comparison,
        payload_delta_bytes=0, stack_delta_bytes=0, state_delta_bytes=0,
        source_sha256_lf=sources,
        physical_disk_rom_ula_publication_measured=False, new_player_release=False,
        setup_attempts=['Initial baseline export failed in system temporary directory; rerun passed with worktree TMP/TEMP.',
                        'Initial producer imports failed because sparse checkout omitted ay-converter; include that source directory.',
                        'Initial layout audit expected a two-byte overrun; emitted helper extent proves one byte, because the original layout has one spare byte.'])
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(complete=True, native_comparisons=sum(p['summary']['cases'] for p in component['profiles'].values()),
                         guarded_cases=126, guarded_placements=756, units=report['observed_units']['total'])))


if __name__ == '__main__':
    main()
