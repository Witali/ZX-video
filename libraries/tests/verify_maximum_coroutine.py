"""Authenticate same-feature maximum-coroutine CPU, service RAM and packaging."""
import argparse,gzip,json,re
from pathlib import Path
from measure_long_copy import ROOT,sha
from measure_fast_jumps import layout
from test_libraries import profiles
from zx0.maximum_coroutine import build
from zx0.maximum import build as raw_build


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    folder=ROOT/'libraries/evidence/maximum_coroutine';folder.mkdir(exist_ok=True)
    archives=[]
    def archive(name):
        source=a.directory/name;data=source.read_bytes();blob=gzip.compress(data,mtime=0)
        path=folder/(name+'.gz');path.write_bytes(blob)
        archives.append(dict(file=str(path.relative_to(ROOT/'libraries')).replace('\\','/'),sha256=sha(blob),decoded_sha256=sha(data)))
        return json.loads(data) if name.endswith('.json') else data.decode('utf-8')
    native=archive('maximum-coroutine-native.json');high=archive('maximum-coroutine-high-word.json')
    screen=archive('maximum-coroutine-quota-screen.json');indexscreen=archive('maximum-coroutine-index-screen.json')
    demands=archive('maximum-coroutine-demands.json');units=archive('maximum-coroutine-unit.log')
    wheel=json.loads((a.directory/'maximum-coroutine-wheel-installed/report.json').read_text())
    assert native['complete'] and high['complete'] and screen['complete'] and indexscreen['complete'] and demands['complete'] and wheel['complete']
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    frozen=json.loads((ROOT/'libraries/second_pass_verification.json').read_text());resources=frozen['original_resources']+frozen['added_pinned_resources']
    for r in resources:assert sha((ROOT/'libraries'/r['package']/'src'/r['package']/'asm'/r['file']).read_bytes())==r['sha256']
    rawfrozen=json.loads((ROOT/'libraries/evidence/ten_percent_maximum.json').read_text())['profiles']
    summaries={}
    for cap,service,real in ((31,4901,167431057),(63,6437,166492817),(127,7973,166005457)):
        profile=build(prefix_cap=cap);item=native['profiles'][str(cap)];supplement=high['profiles'][str(cap)]
        assert layout(profile)==item['layout'] and json.loads(json.dumps(profile[2]))==item['metadata']
        assert item['summary']['cases']==417 and item['summary']['real_blocks']==364
        assert item['summary']['real_baseline_tstates']==180610040 and item['summary']['real_candidate_tstates']==real
        assert item['summary']['slower_blocks']==0 and supplement['summary']['slower_blocks']==0 and supplement['summary']['cases']==56
        assert profile[2]['service_memory_bytes']==service and sum(profile[2]['service_memory'].values())==service
        assert build(prefix_cap=cap,irq_code_bytes=13,irq_stack_bytes=6)[2]['service_memory_bytes']==service+25<=10000
        assert raw_build(prefix_cap=cap)[0][0][1].hex()==rawfrozen[str(cap)]['candidate']['regions'][0]['code_hex']
        for r in item['blocks']+supplement['blocks']:
            assert r['exact'] and r['relocated_exact'] and r['same_fast_return_cursors'] and r['same_fast_eof_states']
            assert r['candidate_tstates']-r['raw_maximum_tstates']==r['added_instruction_tstates']
            assert r['caller_stack_bytes']<=4 and r['private_stack_bytes']<=12 and r['irq_caller_stack_bytes']<=10 and r['irq_private_stack_bytes']<=18
        summaries[str(cap)]=dict(summary=item['summary'],high_word_summary=supplement['summary'],service_memory=profile[2]['service_memory'],
            service_bytes=service,service_with_13_byte_irq_and_6_byte_stack_headroom=service+25,
            gain_vs_same_feature_fast_percent=(180610040-real)/180610040*100,
            real_added_wrapper_check_tstates=sum(r['added_instruction_tstates']for r in item['blocks']if r['case'].startswith('real-')),
            observed_stack_peaks={key:max(r[key]for r in item['blocks']+supplement['blocks'])for key in ('caller_stack_bytes','private_stack_bytes','irq_caller_stack_bytes','irq_private_stack_bytes')},
            every_slower_slice=[dict(case=r['case'],slower_slice_deltas=r['slower_slice_deltas'])for r in item['blocks']if r['slower_slices']],
            slower_real_slices=sum(r['slower_slices']for r in item['blocks']if r['case'].startswith('real-')))
    assert demands['cases']==417 and len(demands['forced_all_phase_comparisons'])==12
    assert demands['service_bytes_with_this_irq']==8010 and demands['all_caller_ix_iy_alternate_pairs_preserved']
    assert len(demands['inplace_minimum_start_cases'])==417
    for case in demands['inplace_minimum_start_cases']:
        assert len(case['profiles'])==3 and all(r['exact'] and r['every_fast_return_exact'] and r['unread_input_never_overwritten']for r in case['profiles'].values())
    assert len(indexscreen['profiles']['index']['blocks'])==417
    assert indexscreen['profiles']['index']['summary']['real_candidate_tstates']==166005457
    rejected={name:dict(service_memory_bytes=item['service_memory_bytes'],summary=item['summary'])for name,item in screen['profiles'].items()}
    tests=int(re.search(r'Ran (\d+) tests in ',units).group(1));assert tests==35 and units.rstrip().endswith('OK')
    for name in ('maximum-coroutine-native.log','maximum-coroutine-high-word.log','maximum-coroutine-demands.log','maximum-coroutine-wheel.log','maximum-coroutine-install.log','maximum-coroutine-smoke.log'):archive(name)
    wheel_file=next((a.directory/'maximum-coroutine-wheel').glob('zxvideo_zx0-*.whl'))
    for source in (ROOT/'libraries/zx0/src/zx0').glob('*.py'):
        assert source.read_bytes().replace(b'\r\n',b'\n')==(a.directory/'maximum-coroutine-installed/zx0'/source.name).read_bytes().replace(b'\r\n',b'\n')
    sourcefiles=[ROOT/'libraries/zx0/src/zx0'/name for name in ('maximum.py','maximum_coroutine.py','__main__.py','export.py')]
    sourcefiles += [ROOT/'libraries/tests'/name for name in ('maximum_coroutine_native.py','measure_maximum_coroutine.py','measure_maximum_coroutine_demands.py','screen_maximum_coroutine.py','test_maximum_coroutine.py','smoke_maximum_coroutine.py','verify_maximum_coroutine.py')]
    report=dict(date='2026-10-20',complete=True,release=False,goal_achieved=False,baseline_revision='f5a0362c',raw_maximum_revision='6759dedf',
        profiles=summaries,rejected_quota_strategies=rejected,selected_quota='saved/restored IX with explicit Spectrum CP IXH/IXL contract',
        main_profile_comparisons=1251,high_word_profile_comparisons=168,all_every_return_cursors_and_eof_states_exact=True,
        repeated_zero_final_demand_cases=417,repeated_demand_returns=sum(len(r['targets'])for r in demands['blocks']),
        forced_phase_sites=12,forced_and_periodic_ix_clobber_irqs=sum(r['injected_interrupts']for r in demands['blocks']),
        forced_ix_clobber_irqs=sum(r['forced_interrupts']for r in demands['blocks']),periodic_ix_clobber_irqs=sum(r['periodic_interrupts']for r in demands['blocks']),
        minimum_safe_inplace_profile_comparisons=1251,minimum_safe_inplace_source_and_return_states_exact=True,
        strong_irq_service_bytes=8010,library_unit_tests=tests,default_profiles_exact=31,upstream_resources_exact=len(resources),
        native_ix_half_flags_cases=2560,ix_half_cp_tstates=8,plain_required_caller_stack_bytes=4,plain_required_private_stack_bytes=12,
        configured_test_stack_margins_bytes=128,private_input_preparation_may_suspend_earlier=True,public_input_pointer_word_unchanged=True,
        payload_delta_bytes=0,old_default_instruction_delta_tstates=0,raw_maximum_caps_31_63_127_byte_exact=True,
        tables_padding_scratch_internal_buffers_bytes=0,external_input_output_history_excluded=True,
        wheel=dict(file=wheel_file.name,sha256=sha(wheel_file.read_bytes()),isolated_installed_sources_exact=True,report=wheel),
        archives=archives,source_sha256_lf={str(f.relative_to(ROOT)).replace('\\','/'):sha(f.read_bytes().replace(b'\r\n',b'\n'))for f in sourcefiles},
        physical_cpu_clones_rom_disk_ula_publication_qualified=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,caps={c:s['gain_vs_same_feature_fast_percent']for c,s in summaries.items()},tests=tests,forced_irqs=report['forced_and_periodic_ix_clobber_irqs'])))


if __name__=='__main__':main()
