"""Bind public branch-profile bytes, guarded replay, regressions and package evidence."""
import argparse
import gzip
import json
from pathlib import Path
import zipfile

from measure_long_copy import ROOT, sha
from measure_fast_jumps import layout
from test_libraries import profiles
from lzsa.block import build as lb
from lzsa.resumable import build as lc
from zx0.block import build as zb
from zx0.resumable import build as zc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); tmp = args.directory
    assert profiles() == json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    evidence = {}; loaded = {}
    for name in ('ten_percent_branch_mix', 'ten_percent_tuned_branches', 'ten_percent_tuned_combinations'):
        path = ROOT/'libraries/evidence'/f'{name}.json'
        data = json.loads(path.read_text()); assert data['complete'] and not data['release']
        loaded[name] = data
        evidence[name] = dict(file=f'evidence/{name}.json', sha256=sha(path.read_bytes()))
    component = json.loads((ROOT/'libraries/evidence/ten_percent_tuned_branches.json').read_text())
    main_cases = sum(len(item['blocks']) for item in component['profiles'].values())
    combination_cases = sum(len(item['blocks']) for item in loaded['ten_percent_tuned_combinations']['profiles'].values())
    assert main_cases == 1024 and combination_cases == 570
    assert all(row['exact'] for report in (component, loaded['ten_percent_tuned_combinations'])
               for item in report['profiles'].values() for row in item['blocks'])
    for name, builder, extra in (('lzsa2-block',lb,dict(fast_jumps=True)),
            ('lzsa2-coroutine',lc,dict(fast_jumps=True)),('zx0-block',zb,{}),('zx0-coroutine',zc,{})):
        old = builder(core=0x8000,core_limit=0x8400,**extra)
        new = builder(core=0x8000,core_limit=0x8400,branch_tuned=True,**extra)
        assert layout(old) == component['profiles'][name]['baseline']
        assert layout(new) == component['profiles'][name]['candidate']

    folder = ROOT/'libraries/evidence/tuned_branches'; folder.mkdir(parents=True,exist_ok=True)
    archives = []
    def archive(path):
        blob = path.read_bytes(); packed = gzip.compress(blob,mtime=0)
        destination = folder/(path.name+'.gz'); destination.write_bytes(packed)
        archives.append(dict(file=str(destination.relative_to(ROOT/'libraries')).replace('\\','/'),
                             sha256=sha(packed), decoded_sha256=sha(blob)))

    old_summary = json.loads((ROOT/'libraries/evidence/fast_jumps_verification.json').read_text())
    streaming = {}
    for mode in ('call','direct'):
        old_path = ROOT/'libraries/evidence/fast_jumps_streaming'/f'fast-jumps-{mode}-after.json.gz'
        indexed = next(row for row in old_summary['archives'] if row['file'].endswith(old_path.name))
        assert sha(old_path.read_bytes()) == indexed['sha256']
        old = json.loads(gzip.decompress(old_path.read_bytes()))
        current_path = tmp/f'tuned-branch-{mode}.json'
        new = json.loads(current_path.read_text())
        assert old['complete'] and new['complete'] and old['cases'] == new['cases'] == 63
        assert len(old['blocks']) == len(new['blocks']) == len(old['independent']) == len(new['independent']) == 63
        assert old['stream_sha256'] == new['stream_sha256'] and old['baseline'] == new['baseline']
        assert old['layout']['prefix_end'] == new['layout']['prefix_end']
        assert old['layout']['core_end'] == new['layout']['core_end']
        slower = slices = irqs = slower_real = real_slow_slices = 0; largest = real_largest = 0
        for before,after,a,b in zip(old['blocks'],new['blocks'],old['independent'],new['independent']):
            assert before['exact'] and after['exact'] and a['case'] == b['case']
            for field in ('payload_sha256','raw_sha256','producer_tstates','sectors','step_tstates',
                          'input_waits','carry_copy_bytes','first_output_loaded_bytes','input_pointer'):
                assert before[field] == after[field], (mode,field,a['case'])
            assert len(before['slice_tstates']) == len(after['slice_tstates'])
            delta = [y-x for x,y in zip(before['slice_tstates'],after['slice_tstates'])]
            assert sum(delta) == after['decoder_tstates']-before['decoder_tstates']
            slower += sum(t>0 for t in delta); slices += len(delta); largest = max(largest,max(delta))
            if a['case'].startswith('real-'):
                slower_real += after['decoder_tstates'] > before['decoder_tstates']
                real_slow_slices += sum(t>0 for t in delta)
                real_largest = max(real_largest,max(delta))
            assert len(a['full_flags']) == len(b['full_flags']) == 6
            for x,y in zip(a['full_flags'],b['full_flags']):
                assert x['exact'] and y['exact'] and x['input_waits'] == y['input_waits']
                assert x['input_start'] == y['input_start']
                irqs += y['injected_interrupts']
        before,after = old['candidate'],new['candidate']
        assert before['producer_tstates'] == after['producer_tstates']
        assert before['sector_reads'] == after['sector_reads'] == 772
        assert before['sectors_exact_once'] and after['sectors_exact_once']
        streaming[mode] = dict(cases=63,real_cases=21,placements_per_case=6,
            baseline_tstates=before['total_tstates'],candidate_tstates=after['total_tstates'],
            delta_tstates=after['total_tstates']-before['total_tstates'],
            baseline_decoder_tstates=before['decoder_tstates'],candidate_decoder_tstates=after['decoder_tstates'],
            producer_tstates=after['producer_tstates'],sector_reads=772,sectors_exact_once=True,
            slices=slices,slower_slices=slower,largest_slice_delta=largest,slower_real_blocks=slower_real,
            slower_real_slices=real_slow_slices,largest_real_slice_delta=real_largest,
            injected_interrupts=irqs,input_waits_and_producer_exact=True,code_and_state_extent_unchanged=True)
        archive(current_path)
    for name,count in (('library',25),('toolkit',67)):
        path = tmp/f'tuned-branch-{name}-tests.log'; text=path.read_text(encoding='utf-8')
        assert f'Ran {count} tests in ' in text and text.rstrip().endswith('OK')
        archive(path)
    wheels = []
    for package in ('zx0','lzsa'):
        result = json.loads((tmp/f'tuned-wheel-{package}/report.json').read_text())
        assert result['independent_wheel'] and result['branch_tuned_profiles'][0]['exact_export']
        wheel = tmp/'tuned-wheels'/f'zxvideo_{package}-0.1.0-py3-none-any.whl'
        with zipfile.ZipFile(wheel) as packed:
            for path in (ROOT/'libraries'/package/'src'/package).glob('*.py'):
                assert packed.read(f'{package}/{path.name}').replace(b'\r\n',b'\n') == path.read_bytes().replace(b'\r\n',b'\n')
            for path in (ROOT/'libraries'/package/'src'/package/'asm').glob('*.asm'):
                assert packed.read(f'{package}/asm/{path.name}') == path.read_bytes()
        wheels.append(dict(report=result,wheel_sha256=sha(wheel.read_bytes())))
    sources = {str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes().replace(b'\r\n',b'\n'))
               for package in ('zx0','lzsa') for path in sorted((ROOT/'libraries'/package/'src'/package).glob('*.py'))}
    second = json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    for resource in second['original_resources']+second['added_pinned_resources']:
        path = ROOT/'libraries'/resource['package']/'src'/resource['package']/'asm'/resource['file']
        assert sha(path.read_bytes()) == resource['sha256']
    report = dict(date='2026-10-19',baseline_revision='f5a0362c',complete=True,release=False,
        goal_achieved=False,goal='Another approximately 10% per library; still active.',
        evidence=evidence,streaming=streaming,archives=archives,source_sha256_lf=sources,
        default_profiles_exact=31,upstream_resources_exact=6,default_instruction_delta_tstates=0,
        observed_units=dict(libraries=25,toolkit=67,total=92),isolated_wheels=wheels,
        native_profile_comparisons=main_cases+combination_cases,payload_delta_bytes=0,state_delta_bytes=0,stack_delta_bytes=0,
        physical_disk_rom_ula_publication_measured=False,new_player_release=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,goal_achieved=False,streaming=streaming,unit_tests=92)))


if __name__ == '__main__':
    main()
