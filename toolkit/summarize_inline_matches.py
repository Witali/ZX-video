"""Verify absolute inline-copy costs and compare complete disk measurements."""
import argparse
import json
from pathlib import Path
import banked_zx0
from benchmark_banked_zx0 import STACK,STOP
from benchmark_context_huffman import word
from validate_fast_sparse import CPU


def copy_costs():
    result=[]
    for name,destination,count,target in (('lower_high_byte',0xe020,3,0xe300),
            ('same_high_byte',0xe020,3,0xe080),('last_byte_wrap',0xffff,1,0)):
        pair=[]
        for inline in (False,True):
            code,labels=banked_zx0.build(fast_literal=True,fast_refill=True,token_boundaries=True,inline_matches=inline)
            cpu=CPU(b'',b'');cpu.port_7ffd=0x17
            for i,v in enumerate(code):cpu.write8(banked_zx0.CODE+i,v)
            word(cpu,labels['slice_target'],target)
            cpu.pc=labels['slice_sync_target'];cpu.sp=STACK;cpu.push(STOP);before=cpu.tstates
            while cpu.pc!=STOP:cpu.step()
            sync=cpu.tstates-before
            for i in range(count):cpu.write8(banked_zx0.INPUT+i,19+i)
            cpu.set_hl(banked_zx0.INPUT);cpu.set_de(destination);cpu.set_bc(count)
            cpu.a,cpu.carry=0x93,True;cpu.sp=STACK
            cpu.pc=labels['match_copy' if inline else 'slice_copy']
            if not inline:cpu.push(STOP)
            stop=labels['match_copy_fast']+3 if inline else STOP;before=cpu.tstates
            while cpu.pc!=stop:cpu.step()
            if (cpu.a!=0x93 or not cpu.carry or cpu.bc() or cpu.sp!=STACK
                    or cpu.de()!=(destination+count)&65535):raise AssertionError('copy registers/flags differ')
            if bytes(cpu.read8((destination+i)&65535) for i in range(count))!=bytes(19+i for i in range(count)):
                raise AssertionError('copy output differs')
            pair.append(dict(sync_tstates=sync,copy_with_dispatch_tstates=cpu.tstates-before+(0 if inline else 17)))
        result.append(dict(path=name,length=count,baseline=pair[0],inline=pair[1],
            copy_delta=pair[1]['copy_with_dispatch_tstates']-pair[0]['copy_with_dispatch_tstates'],
            sync_delta=pair[1]['sync_tstates']-pair[0]['sync_tstates']))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,default=Path(__file__).parent)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();root=args.directory
    def load(name):return json.loads((root/name).read_text(encoding='utf-8'))
    before=load('token_boundary_fast_banked_cpu.json');after=load('inline_matches_banked_cpu.json')
    frames=load('inline_matches_frames_cpu.json');disks=load('inline_matches_disk_summary.json')
    if not all(r['complete'] for r in (before,after,frames,disks)):raise ValueError('unfinished input report')
    if not before['input_sha256']==after['input_sha256']==frames['raw_sha256']==disks['raw_sha256']:
        raise ValueError('different streams')
    for old,new in zip(before['blocks'],after['blocks'],strict=True):
        for key in ('ring_start','compressed_bytes','decoded_bytes'):
            if old[key]!=new[key]:raise ValueError('block boundaries or ring offsets differ')
    counts=lambda label:sum(h['count'] for h in after['instruction_histogram'] if h['address']==after['labels'][label])
    matches,syncs=counts('dzx0t_copy'),counts('slice_sync_target')
    predicted=39*syncs-27*matches
    if after['summary']['total_tstates']-before['summary']['total_tstates']!=predicted:
        raise AssertionError('whole-stream instruction delta does not match counted events')
    result=dict(complete=True,release=False,baseline_commit='80ab9d9',copy_paths=copy_costs(),
        input_sha256=after['input_sha256'],matches=matches,target_syncs=syncs,
        theoretical_delta_tstates=predicted,baseline_decoder=before['summary'],inline_decoder=after['summary'],
        slower_blocks=sum(b['delta_tstates']>0 for b in after['blocks']),
        decoder_gain_percent=-100*predicted/before['summary']['total_tstates'],
        code_extra_bytes=after['summary']['code_bytes']-before['summary']['code_bytes'],
        stream_extra_bytes=0,buffer_extra_bytes=0,cpu_samples=[],disks=[])
    for r in frames['ranges']:
        result['cpu_samples'].append(dict(start=r['start'],end=r['end'],
            baseline_tstates=r['baseline']['foreground_tstates'],inline_tstates=r['inline']['foreground_tstates'],
            delta_tstates=r['foreground_delta'],old_missed=r['old_missed'],new_missed=r['new_missed']))
    baseline_paths={0:'fap3_deferred_summary.json',248:'fap3_deferred_frame_service_summary.json'}
    for variant in disks['variants']:
        limit=variant['limit'];source=load(baseline_paths[limit])
        old_variant=next(v for v in source['variants'] if v['limit']==limit)
        if not source['complete'] or source['ends']!=disks['ends'] or source['raw_sha256']!=disks['raw_sha256']:
            raise ValueError('different disk baseline')
        for old,new in zip(old_variant['volumes'],variant['volumes'],strict=True):
            if (old['part'],old['frames'],old['video_bytes'])!=(new['part'],new['frames'],new['video_bytes']):
                raise ValueError('different volume data')
            result['disks'].append(dict(limit=limit,part=new['part'],frames=new['frames'],
                baseline_source=baseline_paths[limit],baseline_trd_sha256=old['trd_sha256'],inline_trd_sha256=new['trd_sha256'],
                baseline_used_sectors=old['used_sectors'],inline_used_sectors=new['used_sectors'],
                baseline=old['timing'],inline=new['timing'],
                read_attempts=new['read_attempts'],fast_read_retries=new['fast_read_retries']))
    generic_before=load('generic_converter_checks.json');generic_after=load('inline_matches_generic.json')
    if not generic_before['complete'] or not generic_after['complete']:raise ValueError('partial generic checks')
    result['generic_cases']=[]
    for old,new in zip(generic_before['cases'],generic_after['cases'],strict=True):
        if (old['source'],old['frames'],old['stream_sha256'])!=(new['source'],new['frames'],new['stream_sha256']):
            raise ValueError('generic FAP3 changed')
        result['generic_cases'].append(dict(source=new['source'],frames=new['frames'],ay_ticks=new['ay_ticks'],
            identical_fap3=True,cpu_complete=all(c['complete'] for c in new['cpu']),
            full_fuse_complete=new['timing']['complete'],nominal_deadlines_met=new['timing']['all_nominal_deadlines_met']))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(copy_paths=result['copy_paths'],matches=matches,target_syncs=syncs,
        decoder_gain_percent=result['decoder_gain_percent'],cpu_frames=sum(r['end']-r['start'] for r in frames['ranges'])),indent=2))


if __name__=='__main__':main()
