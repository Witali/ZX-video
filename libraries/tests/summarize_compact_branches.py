"""Authenticate the Case11x compact policy, guarded producer invariants and RAM."""
import argparse,gzip,json,re
from pathlib import Path
from measure_long_copy import ROOT,sha
from measure_fast_jumps import layout
from test_libraries import profiles
from lzsa.block import build as block
from lzsa.resumable import build
from lzsa._z80 import MiniAssembler
from lzsa.streaming import emit_guard_update


def guarded_memory(profile):
    """Count guard patcher/carry, then the separately composed mocked feeder.

    Stack bounds include caller returns. Literal wait: finish return 2,
    guard_literals return 2, input_wait return 2, saved AF 2, yield return 2,
    saved AF/AF'/BC/DE/HL 10 = 20 private bytes. The public caller peaks at
    4 during CALL sync. The reference feeder peaks at 10 main /20 disk bytes
    before ROM (whose body is mocked, so it adds no hidden stack here).
    """
    regions,z,meta=profile
    a=MiniAssembler(0x7000);emit_guard_update(a,z);a.emit(0xc9);patcher=len(a.resolve())
    code=meta['code_bytes'];plain=code+patcher+256+4+20
    item=dict(emitted_code_and_state_bytes=code,state_bytes_already_included=z['end']-z['state'],
        standalone_guard_patcher_with_ret_bytes=patcher,shared_sector_carry_scratch_bytes=256,
        required_caller_stack_bytes=4,required_private_stack_bytes=20,
        static_private_stack_derivation_bytes=[2,2,2,2,2,10],
        component_total_service_bytes=plain,
        benchmark_irq_stub_bytes=13,irq_extra_bytes_per_stack=6,
        component_total_service_with_benchmark_irq_bytes=plain+13+12,
        configured_test_caller_stack_reservation_bytes=128,configured_test_private_stack_reservation_bytes=128,
        tables_required_padding_bytes=0,input_output_history_excluded=True)
    import fap3_disk_z80 as disk,pipelined_frame_z80 as video
    from inplace_streaming_core import input_prefix
    dcode,d,_=disk.build_disk(57,772,fast_disk=True,cached_seek=True,interleaved=True)
    seek,_,_=disk.build_cached_seek(d)
    prefix,_,_=input_prefix(z,d,elapsed_fields=0x8005,origin=meta['prefix_end'],patch_guards=True)
    vregions,_,_=video.build_video(dict(saved_page=0x8000,screen_base=0x8001),dict(history_page=0x8002),dict(elapsed_fields=0x8003),irq_safe_paging=True)
    # Only the atomic paging region and page shadow are called by the feeder;
    # retain all generated video code/state as an explicitly conservative cost.
    supplier=sum(len(blob) for _,blob in prefix)+len(dcode)+len(seek)+sum(len(blob) for _,blob in vregions)
    item['reference_supplier']=dict(producer_with_embedded_guard_patcher_bytes=sum(len(blob) for _,blob in prefix),
        disk_adapter_and_state_bytes=len(dcode),cached_seek_bytes=len(seek),
        full_generated_video_paging_and_state_bytes=sum(len(blob) for _,blob in vregions),
        emitted_code_and_state_total_bytes=supplier,required_main_stack_bytes=10,required_disk_stack_bytes=20,
        configured_mock_rom_workspace_bytes=258,configured_mock_rom_workspace_start=0x5c00,
        irq_vector_word_bytes=2,elapsed_counter_bytes=2,
        physical_rom_body_and_its_workspace_not_measured=True)
    # Standalone guard patcher is replaced by its embedded reference version;
    # the supplier shares the caller stack, which grows from 4 to 10 bytes.
    item['combined_reference_total_service_bytes']=code+supplier+256+10+20+20+258+2+2
    item['combined_reference_total_with_benchmark_irq_bytes']=item['combined_reference_total_service_bytes']+13+18
    assert item['combined_reference_total_with_benchmark_irq_bytes']<=10000
    return item


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    folder=ROOT/'libraries/evidence/compact_branches';folder.mkdir(exist_ok=True)
    archives=[]
    def archive(path):
        raw=path.read_bytes();blob=gzip.compress(raw,mtime=0);dest=folder/(path.name+'.gz');dest.write_bytes(blob)
        archives.append(dict(file=str(dest.relative_to(ROOT/'libraries')).replace('\\','/'),sha256=sha(blob),decoded_sha256=sha(raw)))
    assert profiles()==json.loads((ROOT/'libraries/tests/decoder_baseline.json').read_text())['profiles']
    previous=json.loads((ROOT/'libraries/second_pass_verification.json').read_text())
    resources=previous['original_resources']+previous['added_pinned_resources']
    for r in resources:assert sha((ROOT/'libraries'/r['package']/'src'/r['package']/'asm'/r['file']).read_bytes())==r['sha256']
    nativepath=ROOT/'libraries/evidence/compact_branches_native.json';native=json.loads(nativepath.read_text())
    assert native['complete'] and native['date']=='2026-10-20'
    native_profiles={};budgets={};count=0
    for name,item in native['profiles'].items():
        resident=name.startswith('block');builder=block if resident else build
        old=builder(core=0x8000,core_limit=0x8400,**item['options'])
        new=builder(core=0x8000,core_limit=0x8400,compact_branches=True,**item['options'])
        assert layout(old)==item['baseline'] and layout(new)==item['candidate']
        assert len(item['blocks'])==97 and new[2]['code_bytes']==old[2]['code_bytes']-1
        assert all(r['exact'] and r['relocated_exact'] for r in item['blocks'])
        assert all(r['delta_tstates']<0 for r in item['blocks'] if r['case'].startswith('real-'))
        count+=97
        peaks={f:max(r[f] for r in item['blocks']) for f in (('stack_bytes','irq_stack_bytes') if resident else ('caller_stack_bytes','private_stack_bytes','irq_caller_stack_bytes','irq_private_stack_bytes'))}
        stacks=4 if resident else 18
        budgets[name]=dict(emitted_code_and_state_bytes=new[2]['code_bytes'],state_bytes_already_included=0 if resident else new[1]['end']-new[1]['state'],
            required_caller_stack_bytes=4,required_private_stack_bytes=0 if resident else 14,
            benchmark_irq_stub_bytes=13,irq_extra_bytes_per_stack=6,
            tables_padding_internal_buffers_bytes=0,total_service_bytes=new[2]['code_bytes']+stacks,
            total_service_with_benchmark_irq_bytes=new[2]['code_bytes']+stacks+13+(6 if resident else 12),
            configured_test_caller_stack_reservation_bytes=128,configured_test_private_stack_reservation_bytes=0 if resident else 128,
            observed_stack_peaks=peaks,input_output_history_excluded=True)
        assert budgets[name]['total_service_with_benchmark_irq_bytes']<=10000
        native_profiles[name]=dict(summary=item['summary'],slower_blocks=[dict(case=r['case'],delta_tstates=r['delta_tstates']) for r in item['blocks'] if r['delta_tstates']>0],
            max_slower_block_tstates=max(r['delta_tstates'] for r in item['blocks']),
            max_slower_slice_tstates=max(r.get('largest_slice_delta',0) for r in item['blocks']))
    streaming={}
    for mode in ('call','direct'):
        beforepath=args.directory/f'compact-branches-{mode}-before.json';afterpath=args.directory/f'compact-branches-{mode}-after.json'
        old=json.loads(beforepath.read_text());new=json.loads(afterpath.read_text())
        assert old['complete'] and new['complete'] and old['cases']==new['cases']==63
        assert old['stream_sha256']==new['stream_sha256'] and old['baseline']==new['baseline']
        assert old['layout']['code_bytes']==new['layout']['code_bytes']+1
        assert old['layout']['prefix_end']==new['layout']['prefix_end']
        slices=[];slower_blocks=[];irqs=0
        for before,after,a,b in zip(old['blocks'],new['blocks'],old['independent'],new['independent']):
            assert before['exact'] and after['exact'] and a['case']==b['case']
            for f in ('payload_sha256','raw_sha256','producer_tstates','sectors','step_tstates','input_waits','carry_copy_bytes','first_output_loaded_bytes','input_pointer'):
                assert before[f]==after[f],(mode,a['case'],f)
            delta=[y-x for x,y in zip(before['slice_tstates'],after['slice_tstates'])]
            assert len(before['slice_tstates'])==len(after['slice_tstates']) and sum(delta)==after['decoder_tstates']-before['decoder_tstates']
            slices.extend(delta)
            if sum(delta)>0:slower_blocks.append(dict(case=a['case'],delta_tstates=sum(delta)))
            assert len(a['full_flags'])==len(b['full_flags'])==6
            for x,y in zip(a['full_flags'],b['full_flags']):
                assert x['exact'] and y['exact'] and x['input_waits']==y['input_waits'] and x['input_start']==y['input_start'];irqs+=y['injected_interrupts']
        before,after=old['candidate'],new['candidate']
        assert before['producer_tstates']==after['producer_tstates'] and before['sector_reads']==after['sector_reads']==772 and after['sectors_exact_once']
        streaming[mode]=dict(cases=63,placements_per_case=6,baseline_tstates=before['total_tstates'],candidate_tstates=after['total_tstates'],
            delta_tstates=after['total_tstates']-before['total_tstates'],producer_tstates=after['producer_tstates'],sector_reads=772,
            input_waits_and_producer_exact=True,slices=len(slices),slower_slices=sum(t>0 for t in slices),maximum_slower_slice_tstates=max(slices),
            slower_blocks=slower_blocks,injected_interrupts=irqs,core_code_delta_bytes=-1,cold_code_unchanged=True)
        archive(beforepath);archive(afterpath)
        budgets['guarded-'+mode]=guarded_memory(build(streaming=True,direct_header=mode=='direct',compact_branches=True,
            compact_sync=True,fast_jumps=True,nibble_prefill=True,core_limit=0x9000))
    combinedpath=args.directory/'compact-branches-combinations.json';combined=json.loads(combinedpath.read_text());assert combined['complete'];combinations={}
    for name,item in combined['profiles'].items():
        assert len(item['cases'])==65;entries=[p for r in item['cases'] for p in r['placements']]
        assert len(entries)==390 and all(r['exact'] for r in entries)
        combinations[name]=dict(cases=65,placements_per_case=6,all_exact=True,slower_placements=sum(r['delta_tstates']>0 for r in entries),
            largest_delta_tstates=max(r['delta_tstates'] for r in entries),delta_tstates=sum(r['delta_tstates'] for r in entries),
            injected_interrupts=sum(r['injected_interrupts'] for r in entries))
        current=build(streaming=True,compact_branches=True,core_limit=0x9000,**item['options'])
        budgets['guarded-strong-'+name]=guarded_memory(current)
    archive(combinedpath)
    log=args.directory/'compact-branches-library-tests.log';content=log.read_text(encoding='utf-8')
    tests=int(re.search(r'Ran (\d+) tests in ',content).group(1));assert tests>=36 and content.rstrip().endswith('OK');archive(log)
    wheelpath=args.directory/'compact-branches-wheel-installed/report.json';wheel=json.loads(wheelpath.read_text());assert wheel['complete'] and wheel['independent_installed_wheel'];archive(wheelpath)
    built_wheels=list((args.directory/'compact-branches-wheel').glob('zxvideo_lzsa-*.whl'));assert len(built_wheels)==1
    for source in (ROOT/'libraries/lzsa/src/lzsa').glob('*.py'):
        installed=args.directory/'compact-branches-installed/lzsa'/source.name
        assert source.read_bytes().replace(b'\r\n',b'\n')==installed.read_bytes().replace(b'\r\n',b'\n')
    archive(args.directory/'compact-branches-wheel-build.log');archive(args.directory/'compact-branches-wheel-smoke.log')
    frozen=json.loads((ROOT/'libraries/evidence/ten_percent_branch_mix.json').read_text())
    branch=next(r for r in frozen['profiles']['lzsa2-fast']['branches'] if r['labels']==['Case11x'])
    assert branch['taken']==6192 and branch['not_taken']==17608 and 2*branch['taken']-3*branch['not_taken']==-40440
    assert {r['payload_sha256'] for r in frozen['profiles']['lzsa2-fast']['blocks']}=={r['payload_sha256'] for r in native['profiles']['block1']['blocks'] if r['case'].startswith('real-')}
    interrupted=[]
    for f in sorted((folder/'interrupted-2026-10-19').glob('*.gz')):
        data=json.loads(gzip.decompress(f.read_bytes()));assert data['complete'];interrupted.append(dict(file=str(f.relative_to(ROOT/'libraries')).replace('\\','/'),sha256=sha(f.read_bytes())))
    assert len(interrupted)==5
    sourcefiles=[*(ROOT/'libraries/lzsa/src/lzsa').glob('*.py'),ROOT/'toolkit/test_streaming_lzsa2.py',
        *[ROOT/'libraries/tests'/name for name in ('measure_compact_branches.py','measure_compact_branches_streaming.py','test_compact_branches.py','summarize_compact_branches.py','smoke_compact_branches.py')]]
    report=dict(date='2026-10-20',baseline_revision='bb687f71',goal_baseline_revision='f5a0362c',complete=True,release=False,goal_achieved=False,
        native_profile_comparisons=count,native_report=dict(file='evidence/compact_branches_native.json',sha256=sha(nativepath.read_bytes())),native_profiles=native_profiles,
        policy=dict(before='JP NC,Case11x',before_tstates=10,after='JR NC,Case11x',after_tstates_not_taken=7,after_tstates_taken=12,
            code_delta_bytes=-1,real_taken=branch['taken'],real_not_taken=branch['not_taken'],real_delta_tstates=-40440),
        streaming=streaming,strongest_streaming_combinations=combinations,service_memory=budgets,archives=archives,interrupted_2026_10_19=interrupted,
        source_sha256_lf={str(f.relative_to(ROOT)).replace('\\','/'):sha(f.read_bytes().replace(b'\r\n',b'\n')) for f in sourcefiles},
        default_profiles_exact=31,upstream_resources_exact=len(resources),library_unit_tests=tests,isolated_lzsa_wheel=True,
        wheel=dict(file=built_wheels[0].name,sha256=sha(built_wheels[0].read_bytes()),installed_python_sources_exact=True),
        payload_delta_bytes=0,state_delta_bytes=0,stack_delta_bytes=0,default_instruction_delta_tstates=0,
        existing_branch_tuned_bytes_frozen=True,physical_disk_rom_ula_publication_measured=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,native_comparisons=count,streaming=streaming,combinations=combinations)))


if __name__=='__main__':main()
