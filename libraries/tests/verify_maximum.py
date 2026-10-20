"""Authenticate full maximum-frontier evidence, legacy baselines and wheel."""
import argparse
from datetime import date
import gzip
import json
from pathlib import Path
import zipfile

from measure_long_copy import ROOT,sha
from test_libraries import profiles
from zx0.block import build as block
from zx0.maximum import build
from mega_prefix_profile import build as prototype
from measure_mega_prefix import high_word_samples


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'.tmp')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    base=ROOT/'libraries'
    evidence=base/'evidence/ten_percent_maximum.json'
    native=json.loads(evidence.read_text())
    assert native['complete'] and not native['test_only'] and not native['coroutine_supported']
    historical=base/'evidence/ten_percent_mega_prefix.json'
    prior=json.loads(historical.read_text())
    assert prior['date']=='2026-10-19' and prior['complete'] and prior['test_only']
    old_path=base/'evidence/trick_23.json'
    old=json.loads(old_path.read_text())
    assert sha(block()[0][0][1])==old['profiles']['fast']['code_sha256']
    assert sha(block('mega')[0][0][1])==old['profiles']['mega']['code_sha256']
    old_rows={row['case']:row for row in old['blocks']}
    assert old['summary']['fast']['real_tstates']==156012520
    assert old['summary']['mega']['real_tstates']==146422274
    tuned=json.loads((base/'evidence/ten_percent_mega_offset.json').read_text())
    assert native['baseline']==tuned['profiles']['combined']['candidate']
    assert native['baseline']['code_bytes']==670
    assert profiles()==json.loads((base/'tests/decoder_baseline.json').read_text())['profiles']
    resources=[]
    frozen=json.loads((base/'second_pass_verification.json').read_text())
    for resource in frozen['original_resources']+frozen['added_pinned_resources']:
        source=base/resource['package']/'src'/resource['package']/'asm'/resource['file']
        assert sha(source.read_bytes())==resource['sha256']
        resources.append(resource)
    summaries={}
    for cap,code,real in ((31,4450,141618798),(63,5986,140680558),(127,7522,140193198)):
        item=native['profiles'][str(cap)];summary=item['summary'];rows=item['blocks']
        assert summary==prior['profiles'][str(cap)]['summary']
        assert item['candidate']==prior['profiles'][str(cap)]['candidate']
        assert summary['cases']==417 and summary['real_blocks']==364
        assert summary['real_baseline_tstates']==145701295
        assert summary['real_candidate_tstates']==real and summary['slower_blocks']==0
        assert item['workspace_bytes']==code+4 and item['service_with_probe_irq_bytes']==code+23
        assert item['max_observed_irq_stack_bytes']==10
        for origin in (0x8000,0x9103):
            public=build(core=origin,prefix_cap=cap,irq_code_bytes=13,irq_stack_bytes=6)
            assert public[:2]==prototype(origin=origin,prefix_cap=cap)[:2]
            assert public[2]['service_memory_bytes']==code+23<=10000
        for row in rows:
            assert row['delta_tstates']==row['predicted_delta_tstates']
            assert row['exact'] and row['relocated_exact'] and row['stack_bytes']<=4
            previous=old_rows[row['case']]
            assert (row['payload_sha256'],row['raw_sha256'])==(previous['payload_sha256'],previous['raw_sha256'])
        slow_fast=[dict(case=row['case'],delta_tstates=row['candidate_tstates']-old_rows[row['case']]['profiles']['fast']['tstates'])
                   for row in rows if row['candidate_tstates']>old_rows[row['case']]['profiles']['fast']['tstates']]
        summaries[str(cap)]=dict(code_bytes=code,service_bytes=code+4,service_with_probe_irq_bytes=code+23,
            real_tstates=real,all_cases_tstates=summary['candidate_tstates'],
            incremental_gain_vs_tuned_mega_percent=(145701295-real)/145701295*100,
            total_gain_vs_original_fast_percent=(156012520-real)/156012520*100,
            gain_vs_original_mega_percent=(146422274-real)/146422274*100,
            slower_than_tuned_mega_blocks=0,slower_than_original_fast=slow_fast,
            dynamic_counts={key:sum(row['dynamic_counts'].get(key,0) for row in rows)
                            for key in rows[0]['dynamic_counts']},
            memory=dict(code_and_embedded_variables=code,embedded_offset_already_in_code=2,
                extra_variables_tables_alignment_scratch_internal_buffers=0,
                decoder_stack_including_caller_return=4,probe_irq_extra_stack=6,probe_irq_code=13,
                max_separate_real_input_bytes=max(row['payload_bytes'] for row in rows if row['case'].startswith('real-')),
                max_separate_real_output_history_bytes=max(row['raw_bytes'] for row in rows if row['case'].startswith('real-')),
                max_separate_input_bytes=max(row['payload_bytes'] for row in rows),
                max_separate_output_history_bytes=max(row['raw_bytes'] for row in rows)))
    high_path=base/'evidence/ten_percent_maximum_high_word.json'
    high=json.loads(high_path.read_text())
    assert high['complete'] and not high['test_only'] and high['high_word_supplement']
    assert high['placement']==dict(core=0x0800,relocated_core=0x0903,source=0x0400,output=0x3000,caller_stack=0x2ff0)
    high_inputs={name:(sha(payload),sha(raw)) for name,payload,raw in high_word_samples()}
    high_summaries={}
    for cap in (31,63,127):
        item=high['profiles'][str(cap)];summary=item['summary']
        assert summary['cases']==56 and summary['slower_blocks']==0
        assert item['max_observed_irq_stack_bytes']==10
        for row in item['blocks']:
            assert row['exact'] and row['relocated_exact']
            assert row['delta_tstates']==row['predicted_delta_tstates']
            assert (row['payload_sha256'],row['raw_sha256'])==high_inputs[row['case']]
            assert row['stack_bytes']<=4 and row['irq_stack_bytes']<=10
        high_summaries[str(cap)]=dict(cases=56,raw_bytes=summary['raw_bytes'],
            baseline_tstates=summary['baseline_tstates'],candidate_tstates=summary['candidate_tstates'],
            delta_tstates=summary['delta_tstates'],injected_interrupts=summary['injected_interrupts'],
            slower_blocks=0,exact=True,relocated_exact=True,
            word_joins=sum(row['dynamic_counts'].get('word_joins',0) for row in item['blocks']))
    unit=args.directory/'maximum-unit.log'
    unit_text=unit.read_text(encoding='utf-8')
    assert 'Ran 31 tests' in unit_text and unit_text.rstrip().endswith('OK')
    smoke=json.loads((args.directory/'maximum-smoke/report.json').read_text())
    assert smoke['independent_wheel'] and len(smoke['maximum_profiles'])==3
    wheel=args.directory/'maximum-wheels/zxvideo_zx0-0.1.0-py3-none-any.whl'
    wheel_files=[]
    with zipfile.ZipFile(wheel) as archive:
        for source in sorted((base/'zx0/src/zx0').rglob('*')):
            if not source.is_file() or '__pycache__' in source.parts:continue
            member='zx0/'+source.relative_to(base/'zx0/src/zx0').as_posix()
            assert archive.read(member)==source.read_bytes(),member
            wheel_files.append(dict(file=member,sha256=sha(source.read_bytes())))
    logs=[]
    for name in ('maximum-unit','maximum-native','maximum-high-word','maximum-wheel','maximum-install','maximum-smoke'):
        source=args.directory/(name+'.log');archive=base/'evidence/maximum'/(name+'.log.gz')
        archive.parent.mkdir(parents=True,exist_ok=True)
        archive.write_bytes(gzip.compress(source.read_bytes(),mtime=0))
        logs.append(dict(file=archive.relative_to(base).as_posix(),sha256=sha(archive.read_bytes())))
    files=['tests/mega_prefix_profile.py','tests/measure_mega_prefix.py','tests/test_maximum.py',
           'tests/verify_maximum.py','tests/smoke_install.py','tests/native_block.py',
           'zx0/src/zx0/maximum.py','zx0/src/zx0/__main__.py','zx0/src/zx0/export.py']
    report=dict(date=date.today().isoformat(),source_baseline='1784e45a',goal_baseline='f5a0362c',
        complete=True,release=False,goal_achieved=False,coroutine_supported=False,
        same_resident_abi=True,global_optimum_established=False,
        native_candidate_comparisons=1251,native_replays=4170,
        high_word_candidate_comparisons=168,high_word_native_replays=560,
        high_word_supplement=high_summaries,
        default_profiles_exact=31,upstream_resources_exact=resources,library_tests=31,
        profiles=summaries,payload_delta_bytes=0,required_input_sector_delta=0,
        original_fast=dict(code_bytes=207,real_tstates=156012520),
        original_mega=dict(code_bytes=673,real_tstates=146422274),
        original_mega_with_fast_jumps=dict(code_bytes=674,real_tstates=146421546),
        tuned_mega_with_fast_jumps=dict(code_bytes=670,real_tstates=145701295),
        wheel=dict(name=wheel.name,sha256=sha(wheel.read_bytes()),files=wheel_files,smoke=smoke),
        source_sha256_lf={name:sha((base/name).read_bytes().replace(b'\r\n',b'\n')) for name in files},
        native_evidence_sha256=sha(evidence.read_bytes()),historical_prototype_sha256=sha(historical.read_bytes()),
        high_word_evidence_sha256=sha(high_path.read_bytes()),
        original_fast_mega_evidence_sha256=sha(old_path.read_bytes()),logs=logs,
        limits=['Only resident ZX0 maximum-speed direction; the per-library/coroutine goal remains active.',
                'The historical Mega advantage over Fast is not a new optimization.',
                'Individual changed conditional exits cost 3 T more when untaken; no complete case slows.',
                'No physical disk, ULA, player/movie delivery or global optimality claim.',
                'Count the actual caller IRQ implementation; the probe is only one 13-byte/6-extra-stack handler.',
                'No coroutine slices exist for this profile.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({key:value for key,value in report.items() if key not in ('source_sha256_lf','wheel','upstream_resources_exact','profiles')}))


if __name__=='__main__':main()
