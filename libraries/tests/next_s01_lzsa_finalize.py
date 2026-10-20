"""Reporting-only S01 finalization; no guest execution or source mutation.

Retain the completed native matrix whose overview failed, authenticate the
clean rerun, and add a compact cold-start/batch/full-service inventory. The
measured source snapshots remain unchanged; this finalizer has its own hash.
"""
import gzip
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
for path in (ROOT/'libraries/lzsa/src',ROOT/'libraries/zx0/src',ROOT/'libraries/tests',ROOT):
    sys.path.insert(0,str(path))

from next_s01_lzsa_measure import alignment
from next_s01_lzsa_profiles import build
from measure_long_copy import sha


def main():
    full=ROOT/'libraries/evidence/next_s01_lzsa_full.json.gz'
    archive=full.with_name('next_s01_lzsa_reporting_attempt.json.gz')
    report=json.loads(gzip.decompress(full.read_bytes()))
    old=json.loads(gzip.decompress(archive.read_bytes()))
    assert report['complete'] and old['complete']
    assert report['profiles']['eof_stack']['native_complete'] and old['profiles']['eof_stack']['native_complete']
    measured_name='libraries/tests/next_s01_lzsa_measure.py'
    assert sha(old['measurement_source_lf'].encode())==old['launch_source_sha256_lf'][measured_name]
    for name,digest in report['launch_source_sha256_lf'].items():
        if name!=measured_name:assert digest==old['launch_source_sha256_lf'][name]
        assert digest==sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))
    for kind in report['profiles']:
        left,right=old['profiles'][kind],report['profiles'][kind]
        assert left['regions']==right['regions'] and left['labels']==right['labels']
        assert len(left['blocks'])==len(right['blocks'])==675
        assert all(a['case']==b['case'] and a['c_guarded']==b['c_guarded'] for a,b in zip(left['blocks'],right['blocks']))
    failure=dict(kind='reporting-only completed previous attempt',process_exit_code=1,
        archive=str(archive.relative_to(ROOT)).replace('\\','/'),archive_sha256=sha(archive.read_bytes()),
        measurement_source_sha256_lf=old['launch_source_sha256_lf'][measured_name],
        error=old['attempts'][-1]['error'],
        native_matrix_complete=True,decoder_failure=False,
        repair='Resolve output path before measurement; suppress huge console lists. Guest generation/oracles/runners unchanged. Clean full rerun exited0.',
        clean_rerun_guest_regions_and_all_candidate_C_results_exact=True)
    if not report.get('reporting_finalization'):
        report['attempts'].append(failure)
    report['baseline_alignments']=alignment('baseline')
    report['reporting_finalization']=dict(guest_execution=False,measured_sources_unchanged=True,
        source_path=str(Path(__file__).relative_to(ROOT)).replace('\\','/'),
        source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')))
    report['path_timing_model']=dict(eof_old_tstates=27,eof_new_tstates=21,
        word_dispatch_old_tstates=12,word_dispatch_new_tstates=26,
        eof_candidate_delta='14*word_escapes - 6*EOFs',
        tagged_length_delta=dict(cached=-9,refill=-13),
        tagged_offset_delta=dict(cached=18,refill=14))
    baseline=report['baseline_binding']
    report['resident_data_requirements']=dict(compressed_input_max_bytes=max(row['payload_bytes'] for row in baseline),
        output_history_max_bytes=max(row['raw_bytes'] for row in baseline),
        retained_input='Complete compressed block; excluded from service.',
        retained_output_history='Complete nonwrapping output/history; excluded from service.')
    def timing(rows):
        real=[row for row in rows if row['real']]
        total=sum(row['c_guarded']['tstates'] for row in rows)
        real_total=sum(row['c_guarded']['tstates'] for row in real)
        return dict(required_one_time_initialization_tstates=0,per_block_setup_tstates=24,
            first_real_cold_start_tstates=real[0]['c_guarded']['tstates'],
            first_real_setup_tstates=24,first_real_decode_tstates=real[0]['c_guarded']['tstates']-24,
            real_batch_tstates=real_total,real_batch_setup_tstates=len(real)*24,
            real_batch_decode_tstates=real_total-len(real)*24,
            all_cases_batch_tstates=total,all_cases_batch_setup_tstates=len(rows)*24,
            all_cases_batch_decode_tstates=total-len(rows)*24)
    report['baseline_timing_components']=timing(baseline)
    for kind,entry in report['profiles'].items():entry['timing_components']=timing(entry['blocks'])
    full.write_bytes(gzip.compress((json.dumps(report,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0))
    summary=dict(date=report['date'],stage=report['stage'],complete=True,release=False,public_changes=False,
        full_report=dict(path=str(full.relative_to(ROOT)).replace('\\','/'),sha256=sha(full.read_bytes())),
        baseline=dict(code_bytes=137,caller_stack_bytes=8,service_bytes=145,
            timing_components=report['baseline_timing_components'],baseline_native_C_and_kosarev_cases=683),
        resident_data_requirements=report['resident_data_requirements'],
        profiles={},prior_reporting_failure=failure,
        source_binding='Launch/final measured source hashes and qualifiedDLL/build/proof hashes retained in full report; measured sources unchanged during clean exit0 run.',
        static_alignments=dict(baseline=256,candidate_profiles=3,origins_each=256,alignment_padding_bytes=0),
        state_exhaustion=report['state_exhaustion'],path_timing_model=report['path_timing_model'],
        unperformed=report['unperformed'])
    for kind,entry in report['profiles'].items():
        p=build(kind);stats=dict(entry['summary']);stats['slower_case_count']=len(stats.pop('slower_cases'))
        summary['profiles'][kind]=dict(code_bytes=p[2]['code_bytes'],caller_stack_bytes=p[2]['caller_stack_bytes'],
            service_bytes=p[2]['service_memory_bytes'],diagnostic_irq_code_bytes=13,additional_irq_stack_bytes=6,
            diagnostic_irq_inclusive_service_bytes=p[2]['service_memory_bytes']+19,
            stats=stats,timing_components=entry['timing_components'],decision=entry['decision'],
            native_complete=entry['native_complete'],qualification=entry.get('qualification'),
            native_gates_unperformed=[] if entry['native_complete'] else ['IRQ','relocated runtime','actual minimum in-place runtime','FFFF cursor'])
    target=full.with_name('next_s01_lzsa.json')
    target.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('finalized',sha(full.read_bytes()),full.stat().st_size,target.stat().st_size)


if __name__=='__main__':main()
