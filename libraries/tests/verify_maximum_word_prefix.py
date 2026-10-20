"""Authenticate the bounded shared word-prefix extension after 6759dedf."""
import argparse
from datetime import date
import gzip
import json
from pathlib import Path
import zipfile

from measure_long_copy import ROOT,sha
from test_libraries import profiles
from zx0.maximum import build
from mega_prefix_profile import build as prototype


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'.tmp')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();base=ROOT/'libraries'
    reports={};summaries={};sources=[]
    for suffix,old_name,expected_cases,expected_total in (
            ('','ten_percent_maximum.json',417,145283522),
            ('_high_word','ten_percent_maximum_high_word.json',56,17161212)):
        path=base/'evidence'/('ten_percent_maximum_word_prefix'+suffix+'.json')
        current=json.loads(path.read_text());prior=json.loads((base/'evidence'/old_name).read_text())
        assert current['complete'] and not current['test_only'] and not current['coroutine_supported']
        assert current['minimal_irq_replayed']
        summaries['high_word' if suffix else 'main']={}
        for cap,code in ((227,9962),(228,9986)):
            item=current['profiles'][str(cap)];old=prior['profiles']['127'];summary=item['summary']
            total=expected_total-(225 if suffix else 705) if cap==228 else expected_total
            assert summary['cases']==expected_cases and summary['candidate_tstates']==total
            assert summary['slower_blocks']==0 and item['max_observed_irq_stack_bytes']==10
            assert item['candidate']['code_bytes']==code and item['workspace_bytes']==code+4<=10000
            assert item['service_with_probe_irq_bytes']==code+23
            assert item['service_with_minimal_irq_bytes']==code+9<=10000
            assert len(item['blocks'])==len(old['blocks'])==expected_cases
            for new_row,old_row in zip(item['blocks'],old['blocks']):
                for key in ('case','payload_sha256','raw_sha256','payload_bytes','raw_bytes','baseline_tstates'):
                    assert new_row[key]==old_row[key]
                assert new_row['exact'] and new_row['relocated_exact'] and new_row['minimal_irq_exact']
                assert new_row['delta_tstates']==new_row['predicted_delta_tstates']
                count=new_row['dynamic_counts'].get('word_joins',0)
                assert count==old_row['dynamic_counts'].get('word_joins',0)
                assert new_row['candidate_tstates']-old_row['candidate_tstates']==-5*(cap-127)*count
                assert new_row['dynamic_counts'].get('prefix_bytes',0)-old_row['dynamic_counts'].get('prefix_bytes',0)==(cap-127)*count
                assert new_row['stack_bytes']<=4 and new_row['irq_stack_bytes']<=10
                assert new_row['minimal_irq_stack_bytes']<=6
            assert max(row['minimal_irq_stack_bytes'] for row in item['blocks'])==6
            summaries['high_word' if suffix else 'main'][str(cap)]=dict(cases=expected_cases,
                baseline_tstates=summary['baseline_tstates'],candidate_tstates=total,
                gain_vs_cap127_tstates=old['summary']['candidate_tstates']-total,
                word_entries=sum(row['dynamic_counts'].get('word_joins',0) for row in item['blocks']),
                injected_full_af_interrupts=summary['injected_interrupts'],slower_blocks=0,
                injected_minimal_interrupts=sum(row['minimal_irq_injected_interrupts'] for row in item['blocks']))
        sources.append(dict(file=path.relative_to(base).as_posix(),sha256=sha(path.read_bytes())))
        reports[suffix]=current
    real=reports['']['profiles']['228']['summary']['real_candidate_tstates']
    assert real==140169968
    assert reports['_high_word']['placement']==dict(core=0x0800,relocated_core=0x0703,
        source=0x0400,output=0x3000,caller_stack=0x2ff0)
    for cap in (31,63,127,227,228):
        for origin in (0x0800,0x0703,0x8000,0x9103):
            public=build(core=origin,prefix_cap=cap,irq_code_bytes=3,irq_stack_bytes=2)
            assert public[:2]==prototype(origin=origin,prefix_cap=cap)[:2]
            assert public[2]['service_memory_bytes']<=10000
    sizes={}
    for cap,expected in ((227,9962),(228,9986),(229,10010),(255,10634)):
        candidate=prototype(prefix_cap=cap,allow_oversize=True)
        assert candidate[2]['code_bytes']==expected
        sizes[str(cap)]=dict(assembled_code_bytes=expected,decoder_service_bytes=expected+4,
            service_with_probe_irq_bytes=expected+23,
            service_with_minimal_irq_bytes=expected+9,
            fits_decoder_service_cap=expected+4<=10000,
            fits_service_cap_with_probe_irq=expected+23<=10000,
            native_checked=cap in (227,228))
    assert profiles()==json.loads((base/'tests/decoder_baseline.json').read_text())['profiles']
    resources=[]
    frozen=json.loads((base/'second_pass_verification.json').read_text())
    for resource in frozen['original_resources']+frozen['added_pinned_resources']:
        source=base/resource['package']/'src'/resource['package']/'asm'/resource['file']
        assert sha(source.read_bytes())==resource['sha256'];resources.append(resource)
    unit=args.directory/'maximum-word-prefix-unit.log';text=unit.read_text(encoding='utf-8')
    assert 'Ran 31 tests' in text and text.rstrip().endswith('OK')
    smoke=json.loads((args.directory/'maximum-word-prefix-final-smoke/report.json').read_text())
    assert smoke['independent_wheel'] and len(smoke['maximum_profiles'])==5
    wheel=args.directory/'maximum-word-prefix-final-wheels/zxvideo_zx0-0.1.0-py3-none-any.whl'
    files=[]
    with zipfile.ZipFile(wheel) as archive:
        for source in sorted((base/'zx0/src/zx0').rglob('*')):
            if not source.is_file() or '__pycache__' in source.parts:continue
            member='zx0/'+source.relative_to(base/'zx0/src/zx0').as_posix()
            assert archive.read(member)==source.read_bytes(),member
            files.append(dict(file=member,sha256=sha(source.read_bytes())))
    logs=[]
    for kind in ('unit','native','high-word','wheel','install','smoke'):
        source=args.directory/('maximum-word-prefix-'+kind+'.log')
        archive=base/'evidence/maximum_word_prefix'/(kind+'.log.gz')
        archive.parent.mkdir(parents=True,exist_ok=True)
        archive.write_bytes(gzip.compress(source.read_bytes(),mtime=0))
        logs.append(dict(file=archive.relative_to(base).as_posix(),sha256=sha(archive.read_bytes())))
    source_names=['zx0/src/zx0/maximum.py','zx0/src/zx0/__main__.py','zx0/src/zx0/export.py',
        'tests/mega_prefix_profile.py','tests/measure_mega_prefix.py','tests/test_maximum.py',
        'tests/smoke_install.py','tests/native_block.py','tests/verify_maximum_word_prefix.py']
    report=dict(date=date.today().isoformat(),source_baseline='6759dedf',goal_baseline='f5a0362c',
        complete=True,release=False,goal_achieved=False,coroutine_supported=False,
        default_prefix_cap=228,code_bytes=9986,decoder_stack_bytes=4,service_bytes=9990,
        probe_irq=dict(code_bytes=13,extra_stack_bytes=6,observed_total_stack_bytes=10,total_service_bytes=10009,
            diagnostic_only_exceeds_total_service_limit=True),
        minimal_irq=dict(code_bytes=3,extra_stack_bytes=2,observed_total_stack_bytes=6,total_service_bytes=9995),
        cap227_with_probe_irq_service_bytes=9985,
        extra_variables_tables_alignment_scratch_internal_buffers_bytes=0,
        embedded_offset_bytes_already_in_code=2,input_output_history_separate=True,
        real_tstates=real,real_gain_vs_cap127_tstates=23230,
        incremental_gain_vs_cap127_percent=23230/140193198*100,
        incremental_gain_vs_tuned_mega_percent=(145701295-real)/145701295*100,
        total_gain_vs_original_fast_percent=(156012520-real)/156012520*100,
        original_fast_real_tstates=156012520,original_mega_real_tstates=146422274,
        tuned_mega_real_tstates=145701295,original_mega_gain_not_new=True,
        summaries=summaries,sizing_candidates=sizes,native_candidate_comparisons=946,
        native_replays=4257,default_profiles_exact=31,upstream_resources_exact=resources,library_tests=31,
        payload_delta_bytes=0,required_input_sector_delta=0,
        source_sha256_lf={name:sha((base/name).read_bytes().replace(b'\r\n',b'\n')) for name in source_names},
        evidence=sources,logs=logs,wheel=dict(name=wheel.name,sha256=sha(wheel.read_bytes()),files=files,smoke=smoke),
        limitations=['Cap228 fits 10,000-byte library service and the separately measured minimal IRQ, but exceeds it with the diagnostic full-AF IRQ probe.',
            'Choose cap227 to retain the full-AF probe within total service 9985; count each real caller handler explicitly.',
            'Cap255 exceeds service cap even without IRQ and is size-only, not native-qualified.',
            'No global optimality, coroutine, physical disk/player/movie qualification or per-library goal completion.',
            'The old Mega advantage over Fast is tracked separately and is not a new optimization.',
            'Largest tested fitting prefix in this fixed suffix-sharing layout, not a global optimality proof.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({key:value for key,value in report.items() if key not in ('source_sha256_lf','wheel','upstream_resources_exact')}))


if __name__=='__main__':main()
