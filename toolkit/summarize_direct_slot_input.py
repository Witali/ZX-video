"""Archive and summarize complete CPU/Fuse evidence for the direct input fixture."""
import argparse
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cpu','baseline','fuse','evidence','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();cpu,old=[json.loads(path.read_bytes()) for path in (args.cpu,args.baseline)]
    if not cpu['complete'] or not old['complete'] or cpu['baseline_report_sha256']!=sha(args.baseline.read_bytes()):
        raise ValueError('partial or different CPU baseline')
    args.evidence.mkdir(parents=True,exist_ok=True)
    volumes=[];files=[]
    for part,(c,b) in enumerate(zip(cpu['volumes'],old['volumes']),1):
        path=args.fuse/f'part{part:02}.json';f=json.loads(path.read_bytes())
        if (not f['complete'] or not f['trace_nonce_exact'] or not f['all_output_bytes_compared']
                or f['trd_sha256']!=c['trd_sha256'] or f['stream_sha256']!=c['stream_sha256']
                or len(f['blocks'])!=len(c['blocks']) or f['accepted_sectors']!=c['summary']['sector_reads']):
            raise ValueError('incomplete or different Fuse run')
        for target in (path,path.with_suffix('.debugger.txt'),path.with_suffix('.trace.txt')):
            data=target.read_bytes()
            if target.suffix=='.txt':
                key='trace_sha256' if target.name.endswith('.trace.txt') else 'debugger_script_sha256'
                if sha(data)!=f[key]:raise ValueError('evidence hash differs')
            dest=args.evidence/(target.name+'.gz' if target.name.endswith('.trace.txt') else target.name)
            dest.write_bytes(gzip.compress(data,mtime=0) if dest.suffix=='.gz' else data)
            files.append(dict(file=dest.name,bytes=dest.stat().st_size,sha256=sha(dest.read_bytes()),
                uncompressed_sha256=sha(data)))
        before=sum(r['baseline_tstates'] for r in b['blocks'])
        core=c['summary']['decoder_tstates'];producer=c['summary']['producer_tstates']
        volumes.append(dict(part=part,blocks=len(c['blocks']),raw_bytes=f['decoded_bytes'],
            baseline_banked_decoder_only_tstates=before,dynamic_local_decoder_tstates=core,
            direct_producer_cpu_tstates=producer,component_cpu_tstates=core+producer,
            conservative_delta_tstates=core+producer-before,carry_copy_bytes=c['summary']['carry_copy_bytes'],
            runtime_sectors=f['accepted_sectors'],fuse_retries=f['retries'],
            fuse_all_decoded_bytes_exact=True,fuse_all_sector_bytes_exact=True,
            fuse_producer_elapsed_tstates=f['producer_elapsed_tstates'],
            fuse_decoder_elapsed_tstates=f['decoder_elapsed_tstates'],
            fuse_read_service_tstates=f['read_service_tstates'],fuse_seek_service_tstates=f['seek_service_tstates'],
            max_cpu_input_step_tstates=c['summary']['max_step_cpu_tstates'],input_window_used_max=c['summary']['input_end_max']))
    if len(volumes)!=3 or sum(v['blocks'] for v in volumes)!=378:raise ValueError('partial movie evidence')
    totals={k:sum(v[k] for v in volumes) for k in volumes[0] if isinstance(volumes[0][k],int)
        and not isinstance(volumes[0][k],bool) and k not in ('part','max_cpu_input_step_tstates','input_window_used_max')}
    result=dict(complete=True,release=False,baseline_commit='03013e3',scope=__doc__,
        comparison='New producer includes header parsing, carry copies, adapter/paging and mocked CALL/JP; '
            'old side contains only the bounded banked decoder. Old disk adapter/header costs are not subtracted as a new saving.',
        full_player_integrated=False,actual_video_and_ay_schedule_verified=False,
        smaller_buffer_sustained_frame_delivery_verified=False,physical_drive_verified=False,
        cpu_excludes='TR-DOS execution, hardware IRQ, ULA and physical latency; outer request setup/CALLs remain host work.',
        fuse_includes='Real TR-DOS/controller/ULA and IRQ with AY disabled; fixture driver included, byte-export loops excluded.',
        fuse_delta_must_not_be_called_physical_disk_latency=True,
        memory=dict(slot_banks=[0,1,3,4],compressed_half_bytes=8192,decoded_half_bytes=8192,
            decoded_capacity_bytes=32768,additional_disk_ring_bytes=0,fixed_carry=[0xbc00,0xbd00],
            decoder=[0x7c00,0x7d4a],producer=[0x7d50,0x7ec0],
            original_stream_reader_replacement_required=True,queue_reader_and_scheduler_not_implemented=True),
        volumes=volumes,totals=totals,evidence=files,
        cpu_report_sha256=sha(args.cpu.read_bytes()),baseline_report_sha256=sha(args.baseline.read_bytes()))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(totals),flush=True)


if __name__=='__main__':main()
