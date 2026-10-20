"""Authenticate guarded-native, exact producer, package and whole-service RAM."""
import argparse
import gzip
import json
from pathlib import Path
import zipfile

from measure_long_copy import ROOT,sha
from wide_guarded_support import wide_profile
from lzsa.resumable import build as old_build
import fap3_disk_z80 as disk
import pipelined_frame_z80 as video


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    native_path=ROOT/'libraries/evidence/wide_guarded_native.json.gz'
    native=json.loads(gzip.decompress(native_path.read_bytes()))
    assert native['complete'] and native['native_cases']==95 and native['directed_cases']==580
    source_archive=ROOT/'libraries/evidence/wide_guarded/consumer-before-metadata-clarification.py.gz'
    clarified_source='libraries/lzsa/src/lzsa/wide_coroutine.py'
    clarification_used=False
    for name,expected in native['source_sha256_lf'].items():
        actual=sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))
        if actual!=expected:
            assert name==clarified_source
            assert sha(gzip.decompress(source_archive.read_bytes()))==expected
            clarification_used=True
    moved_path=ROOT/'libraries/evidence/wide_guarded_relocation.json.gz'
    moved=json.loads(gzip.decompress(moved_path.read_bytes()))
    assert moved['complete'] and moved['original_native_sha256']==sha(native_path.read_bytes())
    for name,expected in moved['source_sha256_lf'].items():
        assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==expected
    unit=(args.directory/'wide-guarded-unit.log').read_bytes()
    assert b'Ran 31 tests' in unit and unit.rstrip().endswith(b'OK')
    smoke=json.loads((args.directory/'guarded-smoke/report.json').read_text())
    assert smoke['independent_wheel'] and not smoke['external_encoder']
    assert len(smoke['wide_profiles'])==8
    assert sum('guarded' in p['variant'] for p in smoke['wide_profiles'])==4
    wheel=next((args.directory/'guarded-wheels').glob('*.whl'))
    members=[]
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if not name.startswith('lzsa/') or name.endswith('/'):continue
            blob=archive.read(name)
            assert blob==(ROOT/'libraries/lzsa/src'/name).read_bytes()
            assert blob==(args.directory/'guarded-installed'/name).read_bytes()
            members.append(dict(path=name,sha256=sha(blob)))
    code,z,_=disk.build_disk(57,772,fast_disk=True,cached_seek=True,interleaved=True)
    seek,_,_=disk.build_cached_seek(z)
    vr,_,_=video.build_video(dict(saved_page=0x8000,screen_base=0x8001),
        dict(history_page=0x8002),dict(elapsed_fields=0x8003),irq_safe_paging=True)
    # Video presentation code is not called by this component. Include the
    # whole paging state and retained descriptor/clock words conservatively.
    io=[dict(address=disk.DISK,bytes=len(code),purpose='reference disk adapter code/state'),
        dict(address=disk.CACHED_SEEK,bytes=len(seek),purpose='reference cached-seek code'),
        *[dict(address=at,bytes=len(blob),purpose='reference atomic paging code/state')
          for at,blob in vr if at!=video.VIDEO],
        dict(address=0x8000,bytes=8,purpose='reference descriptor/clock words')]
    io_bytes=sum(p['bytes'] for p in io)
    profiles={}
    for key,p in native['profiles'].items():
        generated=wide_profile(shared='shared' in key,direct='direct' in key)
        assert all(generated[2][name]==value for name,value in p['metadata'].items())
        assert generated[2]['consumer_service_memory_bytes']==p['metadata']['service_memory_bytes']
        assert [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in generated[0]]==p['regions']
        service=p['service'];metadata=p['metadata']
        assert metadata['service_memory_bytes']==metadata['code_bytes']+24+4
        assert metadata['guard_update_code_bytes'] in (54,57)
        assert p['summary']['actual_native_private_stack_bytes']==24
        assert p['summary']['actual_native_caller_stack_bytes']==4
        assert len(p['native_blocks'])==675
        assert moved['profiles'][key]['cases']==675
        assert moved['profiles'][key]['dispatch_low']==0x9e00
        assert moved['profiles'][key]['metadata']['service_memory_bytes']==metadata['service_memory_bytes']
        current_moved=wide_profile(shared='shared' in key,direct='direct' in key,core=0x9e00)
        assert [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in current_moved[0]]==moved['profiles'][key]['regions']
        assert all(len(r['placements'])==6 for r in p['native_blocks'])
        assert p['reference_producer_summary']['sector_reads']==772
        assert p['reference_producer_summary']['producer_tstates']==p['baseline_producer_summary']['producer_tstates']
        assert p['histogram']['instruction_table_checked']
        total=service['consumer_plus_producer_carry_stacks_bytes']+io_bytes
        # Reserve all 5B00..5FFF as additional external reference workspace.
        # This is a RAM reservation, not evidence that the mocked ROM executed.
        reserved_workspace=1280
        with_workspace=total+reserved_workspace
        with_probe_irq=with_workspace+13+6*3
        assert with_probe_irq<=10000,(key,with_probe_irq)
        regions=[dict(address=at,bytes=len(blob),purpose='consumer region') for at,blob in generated[0]]
        regions+=service['reference_producer_regions']+io
        regions+=[dict(address=0xbc00,bytes=256,purpose='shared-sector carry'),
            dict(address=0x38,bytes=13,purpose='flat native IM1 probe handler; actual application IRQ/vector placement is additional'),
            dict(address=0x5b00,bytes=reserved_workspace,purpose='conservative reference workspace reservation'),
            dict(address=0x7be0-30,bytes=30,purpose='private stack including six IRQ bytes'),
            dict(address=0x9df0-service['reference_stacks']['0x9df0']-6,
                 bytes=service['reference_stacks']['0x9df0']+6,purpose='caller stack including six IRQ bytes'),
            dict(address=0x9c00-service['reference_stacks']['0x9c00']-6,
                 bytes=service['reference_stacks']['0x9c00']+6,purpose='disk stack including six IRQ bytes')]
        assert sum(region['bytes'] for region in regions)==with_probe_irq
        for i,a in enumerate(regions):
            for b in regions[i+1:]:
                assert a['address']+a['bytes']<=b['address'] or b['address']+b['bytes']<=a['address'],(key,a,b)
        profiles[key]=dict(**service,additional_reference_io_code_state_bytes=io_bytes,
            consumer_metadata=generated[2],
            consumer_producer_carry_io_stacks_bytes=total,
            conservative_reference_workspace_bytes=reserved_workspace,
            aligned_with_reference_workspace_bytes=with_workspace,
            aligned_with_reference_workspace_and_probe_irq_example_bytes=with_probe_irq,
            remaining_aligned_service_bytes=10000-with_probe_irq,
            reserved_region_inventory=regions,
            compressed_input_bytes=max(r['compressed_input_bytes'] for r in p['native_blocks']),
            output_history_bytes=max(r['output_history_bytes'] for r in p['native_blocks']),
            summary=p['summary'])
        real=[r for r in p['reference_producer_blocks'] if r['case'].startswith('real-')]
        producer_t=sum(r['baseline']['producer_tstates'] for r in real)
        before=p['summary']['real_decoder_baseline_tstates']+producer_t
        after=p['summary']['real_decoder_candidate_tstates']+producer_t
        profiles[key]['additional_summary']=dict(real_producer_tstates=producer_t,
            live_relocation_cases=moved['profiles'][key]['cases'],
            live_relocation_core=moved['core'],
            live_relocation_shift_bytes=moved['profiles'][key]['live_code_shift_bytes'],
            live_relocation_injected_interrupts=moved['profiles'][key]['injected_interrupts'],
            real_combined_baseline_tstates=before,real_combined_candidate_tstates=after,
            real_combined_percent_saved=100*(before-after)/before,
            reference_real_slower_slices=[dict(case=r['case'],slice=i,delta_tstates=d)
                for r in real for i,d in enumerate(r['slice_deltas']) if d>0],
            native_real_slower_slices=[dict(case=r['case'],offset=v['offset'],slice=i,delta_tstates=d)
                for r in p['native_blocks'] if r['case'].startswith('real-')
                for v in r['placements'] for i,d in enumerate(v['slice_deltas']) if d>0],
            native_real_slower_blocks=[dict(case=r['case'],offset=v['offset'],delta_tstates=v['delta_tstates'])
                for r in p['native_blocks'] if r['case'].startswith('real-')
                for v in r['placements'] if v['delta_tstates']>0])
    destination=ROOT/'libraries/evidence/wide_guarded'
    destination.mkdir(exist_ok=True)
    archives=[]
    for filename in ('wide-guarded-unit.log','wide-guarded-rejected-placement.log',
                     'wide-guarded-rejected-histogram.log','wide-guarded-rejected-C6.log'):
        source=args.directory/filename
        blob=gzip.compress(source.read_bytes(),mtime=0)
        path=destination/(filename+'.gz');path.write_bytes(blob)
        archives.append(dict(path=str(path.relative_to(ROOT)).replace('\\','/'),sha256=sha(blob)))
    baseline_profiles={}
    for direct in (False,True):
        regions,z,metadata=old_build(core=0x8d74,core_limit=0x8e80,streaming=True,
                                    direct_header=direct,fast_jumps=True)
        baseline_profiles['direct' if direct else 'call']=dict(metadata=metadata,
            regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in regions])
    report=dict(date='2026-10-20',complete=True,release=False,goal_achieved=False,
        storage_budget_bytes=10000,default_profiles=31,upstream_resources=6,library_tests=31,
        live_relocation_sha256=sha(moved_path.read_bytes()),
        native_sha256=sha(native_path.read_bytes()),native_cases_per_profile=675,
        native_placements_per_case=6,profiles=profiles,archives=archives,baseline_profiles=baseline_profiles,
        baseline_resumable_source_sha256_lf=sha((ROOT/'libraries/lzsa/src/lzsa/resumable.py').read_bytes().replace(b'\r\n',b'\n')),
        metadata_clarification=dict(instruction_delta_tstates=0,all_proven_regions_byte_identical=True,
            executed_source_archive=(str(source_archive.relative_to(ROOT)).replace('\\','/')
                                     if clarification_used else None),
            executed_source_sha256_lf=native['source_sha256_lf'][clarified_source],
            current_source_sha256_lf=sha((ROOT/clarified_source).read_bytes().replace(b'\r\n',b'\n')),
            current_consumer_supplier_scope_explicit=True),
        wheel=dict(filename=wheel.name,sha256=sha(wheel.read_bytes()),exact_members=members,smoke=smoke),
        source_sha256_lf=native['source_sha256_lf'],
        limitations=['Counts use flat memory and a ROM-mocked reference producer; no physical disk/ROM/ULA or movie timing proof.',
            'The aligned full reference-service reservation is under10000 bytes. Additional arbitrary alignment/IRQ/application work must be counted and may exceed remaining headroom.',
            'The 1280-byte external workspace is reserved, but actual TR-DOS ROM execution/maximum stack use remains unmeasured.',
            'The13-byte/six-byte-stack interrupt probe is an explicit example; application IRQ code, vectors and stack requirements are additional unless already reserved.',
            'Compressed input and complete output/history are explicitly separate; carry and both guard patchers are counted.'])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:dict(service=p['consumer_bytes'],reference_and_workspace_irq=p['aligned_with_reference_workspace_and_probe_irq_example_bytes'])
        for k,p in profiles.items()}))


if __name__=='__main__':main()
