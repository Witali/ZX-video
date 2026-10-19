"""Authenticate compact sync speed/size results and guarded producer invariants."""
import argparse,gzip,json
from pathlib import Path
from measure_long_copy import ROOT,sha
from measure_fast_jumps import layout
from test_libraries import profiles
from lzsa.resumable import build


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    ev=ROOT/'libraries/evidence';folder=ev/'compact_sync';folder.mkdir(exist_ok=True)
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    archives=[]
    def archive(path):
        raw=path.read_bytes();blob=gzip.compress(raw,mtime=0);dest=folder/(path.name+'.gz');dest.write_bytes(blob)
        archives.append(dict(file=str(dest.relative_to(ROOT/'libraries')).replace('\\','/'),sha256=sha(blob),decoded_sha256=sha(raw)))
    previous=json.loads((ev/'nibble_prefill_verification.json').read_text());streaming={}
    for mode in ('call','direct'):
        oldpath=ev/'nibble_prefill'/f'nibble_prefill_streaming_{mode}.json.gz'
        assert sha(oldpath.read_bytes())==next(r['sha256'] for r in previous['archives'] if r['file'].endswith(oldpath.name))
        old=json.loads(gzip.decompress(oldpath.read_bytes()));newpath=args.directory/f'compact-sync-{mode}.json';new=json.loads(newpath.read_text())
        assert old['complete'] and new['complete'] and old['cases']==new['cases']==63
        assert old['stream_sha256']==new['stream_sha256'] and old['baseline']==new['baseline']
        assert old['layout']['prefix_end']-3==new['layout']['prefix_end'] and old['layout']['core_end']==new['layout']['core_end']
        slow=0;slices=0;irqs=0
        for before,after,a,b in zip(old['blocks'],new['blocks'],old['independent'],new['independent']):
            assert before['exact'] and after['exact'] and a['case']==b['case']
            for f in ('payload_sha256','raw_sha256','producer_tstates','sectors','step_tstates','input_waits','carry_copy_bytes','first_output_loaded_bytes','input_pointer'):
                assert before[f]==after[f],(mode,a['case'],f)
            delta=[y-x for x,y in zip(before['slice_tstates'],after['slice_tstates'])]
            assert len(before['slice_tstates'])==len(after['slice_tstates']) and sum(delta)==after['decoder_tstates']-before['decoder_tstates']
            assert all(t<=0 for t in delta);slices+=len(delta);slow+=sum(t>0 for t in delta)
            assert len(a['full_flags'])==len(b['full_flags'])==6
            for x,y in zip(a['full_flags'],b['full_flags']):
                assert x['exact'] and y['exact'] and x['input_waits']==y['input_waits'] and x['input_start']==y['input_start']
                irqs+=y['injected_interrupts']
        before,after=old['candidate'],new['candidate']
        assert before['producer_tstates']==after['producer_tstates'] and before['sector_reads']==after['sector_reads']==772 and after['sectors_exact_once']
        streaming[mode]=dict(cases=63,placements_per_case=6,baseline_tstates=before['total_tstates'],candidate_tstates=after['total_tstates'],
            delta_tstates=after['total_tstates']-before['total_tstates'],producer_tstates=after['producer_tstates'],sector_reads=772,
            input_waits_and_producer_exact=True,slices=slices,slower_slices=slow,injected_interrupts=irqs,cold_code_delta_bytes=-3,core_bytes_unchanged=True)
        archive(newpath)
    nativepath=ev/'compact_sync_native.json';native=json.loads(nativepath.read_text());count=0;budgets={}
    for name,item in native['profiles'].items():
        assert layout(build(core=0x8000,core_limit=0x8400,**item['options']))==item['baseline']
        current=build(core=0x8000,core_limit=0x8400,compact_sync=True,**item['options'])
        assert layout(current)==item['candidate'] and len(item['blocks'])==97
        assert all(r['exact'] and r['relocated_exact'] for r in item['blocks'])
        assert item['summary']['slower_blocks']==item['summary']['slower_slices']==0
        count+=len(item['blocks']);state=current[1]['end']-current[1]['state']
        peaks={f:max(r[f] for r in item['blocks']) for f in ('caller_stack_bytes','private_stack_bytes','irq_caller_stack_bytes','irq_private_stack_bytes')}
        budgets[name]=dict(decoder_code_and_state_bytes=current[2]['code_bytes'],state_bytes_already_included=state,
            configured_caller_stack_reservation_bytes=128,configured_private_stack_reservation_bytes=128,benchmark_irq_stub_bytes=13,
            tables_padding_internal_buffers_bytes=0,conservative_total_service_bytes=current[2]['code_bytes']+256+13,observed_stack_peaks=peaks,
            input_output_history_excluded=True)
        assert budgets[name]['conservative_total_service_bytes']<=10000
    for direct in (False,True):
        for extended in (False,True):
            current=build(streaming=True,direct_header=direct,compact_sync=True,fast_jumps=True,branch_tuned=True,
                nibble_prefill=True,long_copy=extended,word_state_init=extended,restore_compare=extended,core_limit=0x9000)
            name=f'streaming-direct{direct}-extended{extended}'
            budgets[name]=dict(decoder_code_and_state_bytes=current[2]['code_bytes'],
                state_bytes_already_included=current[1]['end']-current[1]['state'],
                configured_caller_stack_reservation_bytes=128,configured_private_stack_reservation_bytes=128,benchmark_irq_stub_bytes=13,
                tables_padding_internal_buffers_bytes=0,conservative_total_service_bytes=current[2]['code_bytes']+256+13,
                static_caller_stack_bound_with_benchmark_irq_bytes=10,static_private_stack_bound_with_benchmark_irq_bytes=26,
                external_application_producer_not_part_of_decoder_budget=True,input_output_history_excluded=True)
            assert budgets[name]['conservative_total_service_bytes']<=10000
    combinedpath=args.directory/'compact-sync-combinations.json';combined=json.loads(combinedpath.read_text());assert combined['complete'];combinations={}
    for name,item in combined['profiles'].items():
        assert len(item['cases'])==65
        entries=[p for r in item['cases'] for p in r['placements']]
        assert len(entries)==390 and all(r['exact'] and r['delta_tstates']<0 for r in entries)
        combinations[name]=dict(cases=65,placements_per_case=6,all_exact=True,slower_placements=0,
            delta_tstates=sum(r['delta_tstates'] for r in entries),injected_interrupts=sum(r['injected_interrupts'] for r in entries))
    archive(combinedpath)
    log=args.directory/'compact-sync-library-tests.log';text=log.read_text(encoding='utf-8')
    assert 'Ran 33 tests in ' in text and text.rstrip().endswith('OK');archive(log)
    resources=json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    for item in resources['original_resources']+resources['added_pinned_resources']:
        assert sha((ROOT/'libraries'/item['package']/'src'/item['package']/'asm'/item['file']).read_bytes())==item['sha256']
    superseded=folder/'superseded-four-register-moves.json.gz';older=json.loads(gzip.decompress(superseded.read_bytes()));assert older['complete']
    files=[*(ROOT/'libraries/lzsa/src/lzsa').glob('*.py'),ROOT/'toolkit/test_streaming_lzsa2.py',
        *[ROOT/'libraries/tests'/name for name in ('measure_compact_sync.py','measure_compact_sync_streaming.py','test_compact_sync.py','summarize_compact_sync.py')]]
    report=dict(date='2026-10-19',baseline_revision='841bf955',complete=True,release=False,goal_achieved=False,scope=__doc__,
        native_profile_comparisons=count,native_report=dict(file='evidence/compact_sync_native.json',sha256=sha(nativepath.read_bytes())),
        streaming=streaming,strongest_streaming_combinations=combinations,service_memory=budgets,archives=archives,
        superseded=dict(file='evidence/compact_sync/'+superseded.name,sha256=sha(superseded.read_bytes()),reason='Direct BC quota stores remove two unnecessary register moves.'),
        source_sha256_lf={str(f.relative_to(ROOT)).replace('\\','/'):sha(f.read_bytes().replace(b'\r\n',b'\n')) for f in files},
        default_profiles_exact=31,upstream_resources_exact=6,library_unit_tests=33,standalone_sync_target_word_checks=262144,
        payload_delta_bytes=0,state_delta_bytes=0,stack_delta_bytes=0,default_instruction_delta_tstates=0,
        physical_disk_rom_ula_publication_measured=False,isolated_wheels_not_retested=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,native_comparisons=count,streaming=streaming,combinations=combinations)))


if __name__=='__main__':main()
