"""Execute deferred disk hooks and ring wrap tests; ROM service is mocked.

T-states come from executed opcodes and are checked against each assembler
listing. Disk mechanics, ROM bodies, IRQs and ULA are excluded here.
"""
import argparse
import json
from pathlib import Path

from benchmark_context_huffman import word
from benchmark_fap3_disk import run as previous_case
import disk_layout
import fap3_disk_z80 as disk
import pipelined_frame_z80 as video
from stream_reader_harness import Harness
from test_fap3_disk import DiskCPU, install


def fixture(limit, *, sectors=900, interleaved=True,keepalive_fields=0,frame_service=False):
    image=b''.join(bytes((sector*13+i*31+(sector>>8))&255 for i in range(256)) for sector in range(2560))
    positions=list(disk_layout.positions(sectors,0)) if interleaved else list(range(sectors))
    stream=b''.join(image[(32+p)*256:(33+p)*256] for p in positions)
    h=Harness(stream,ring_start=0,token_boundaries=True,page_entry=video.PAGE,
        unrolled_copy=True,disk_refill_entry=disk.DISK)
    cpu=h.cpu; cpu.__class__=DiskCPU; cpu.iy=0; cpu.poison_rom=True; cpu.trd=image
    regions,_,vr=video.build_video(dict(saved_page=0x8000,screen_base=0x8001),
        dict(history_page=0x8002),dict(elapsed_fields=0x8003))
    for address,blob in regions: install(cpu,address,blob)
    cpu.write8(video.SHADOW,0x17)
    code,dl,dr=disk.build_disk(32+positions[256],sectors-256,fast_disk=True,
        cached_seek=True,initial_track=(32+positions[255])//16,
        interleaved=interleaved,deferred_limit=limit,keepalive_fields=keepalive_fields,elapsed_fields=0x8003)
    install(cpu,disk.DISK,code)
    code,ql,qr=disk.build_deferred(dl,limit,keepalive_fields=keepalive_fields,elapsed_fields=0x8003,
        frame_service=frame_service); install(cpu,disk.DEFERRED,code)
    code,_,sr=disk.build_cached_seek(dl); install(cpu,disk.CACHED_SEEK,code)
    cpu.write8(0x5cf5,(32+positions[255])//16)
    cpu.write8(0x5cf6,0); cpu.write8(0x5cfa,0)
    word(cpu,0x8003,0)
    return h,dl,ql,{r['address']:r for r in vr+dr+qr+sr},stream


def execute(cpu, entry, rows=None, *, stack=0x7bc0):
    cpu.sp=stack; cpu.push(0x5f00); cpu.pc=entry
    saved={name:getattr(cpu,name) for name in ('ix','iy','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l','alt_z','alt_carry')}
    before=cpu.tstates; visits={}
    while cpu.pc!=0x5f00:
        pc,start=cpu.pc,cpu.tstates; cpu.step(); ticks=cpu.tstates-start
        if rows is not None:
            wanted=rows[pc]['tstates']
            assert ticks in (wanted if isinstance(wanted,list) else [wanted]),(hex(pc),ticks,wanted)
        visits[pc]=visits.get(pc,0)+1
        assert sum(visits.values())<10000,'routine did not return'
    assert cpu.sp==stack
    assert {name:getattr(cpu,name) for name in saved}==saved
    return cpu.tstates-before


def timings(keepalive_fields=0):
    result={}
    for name,options in (
            ('partial',dict(high=0xc0)),('defer',dict(high=0xc1)),
            ('eof',dict(high=0xc1,remaining=0)),
            ('force',dict(high=0xc1,pending=7)),
            ('idle_empty',dict(idle=True)),('idle_read',dict(idle=True,pending=1)),
            ('idle_eof',dict(idle=True,pending=1,remaining=0))):
        h,dl,ql,rows,_=fixture(8,keepalive_fields=keepalive_fields); cpu=h.cpu
        # Same-track read isolates the common adapter path.
        cpu.write8(dl['cached_track'],word(cpu,dl['disk_position'])>>8)
        cpu.write8(0x5cf5,word(cpu,dl['disk_position'])>>8)
        cpu.write8(ql['pending'],options.get('pending',0))
        if 'remaining' in options: word(cpu,dl['remaining'],options['remaining'])
        cpu.set_hl(options.get('high',0xc0)*256+3)
        result[name]=execute(cpu,ql['idle'] if options.get('idle') else disk.DISK,rows)
        assert cpu.read8(ql['pending'])<=7
        if options.get('idle'): assert cpu.port_7ffd&7==7
    previous=previous_case(fast_disk=True,cached_seek=True,interleaved=True)['tstates']
    return dict(previous_same_track_read_tstates=previous, deferred_routines_tstates=result,
        forced_read_delta=result['force']-previous,
        idle_clock_extra_tstates_per_call=31,
        startup_overlay_copy_tstates=30+21*256-5)


def check_keepalive(frame_service=False):
    h,dl,ql,rows,_=fixture(8,keepalive_fields=64,frame_service=frame_service); cpu=h.cpu
    costs={}; frame_costs={}
    for track in range(160):
        for delta,last in ((63,0),(64,0),(64,65500),(256,0)):
            now=(last+delta)&65535; word(cpu,0x8003,now); word(cpu,disk.LAST_DISK_FIELDS,last)
            word(cpu,dl['remaining'],10); cpu.write8(ql['pending'],0)
            cpu.write8(dl['cached_track'],track); cpu.write8(0x5cfe,0x84)
            before_reads=cpu.dos_reads; before_seeks=len(cpu.seek_calls)
            position=word(cpu,dl['disk_position'])
            ticks=execute(cpu,ql['idle'],rows,stack=0x9df0)
            costs[str(delta)]=ticks
            assert cpu.dos_reads==before_reads and word(cpu,dl['disk_position'])==position
            assert word(cpu,dl['remaining'])==10 and cpu.read8(ql['pending'])==0
            assert cpu.port_7ffd&7==7 and cpu.read8(0x5cfe)==0x84
            assert word(cpu,disk.LAST_DISK_FIELDS)==(now if delta>=64 else last)
            if delta>=64:
                assert cpu.seek_calls[before_seeks:]==[(0x3e44,track//2,0)],cpu.seek_calls[before_seeks:]
                assert cpu.a==1
            else: assert len(cpu.seek_calls)==before_seeks and cpu.a==0
            if frame_service:
                word(cpu,disk.LAST_DISK_FIELDS,last)
                frame_costs[str(delta)]=execute(cpu,ql['no_pending'],rows,stack=0x9df0)
    word(cpu,dl['remaining'],0); word(cpu,0x8003,1000); word(cpu,disk.LAST_DISK_FIELDS,0)
    before=len(cpu.seek_calls); execute(cpu,ql['idle'],rows,stack=0x9df0)
    assert len(cpu.seek_calls)==before and cpu.a==0
    result=dict(cases=641,keepalive_fields=64,idle_tstates_by_elapsed=costs,
        ring_cursor_flags_and_registers_preserved=True,rom_mocked=True)
    if frame_service:
        # With a queued sector, maintenance must read it once instead of
        # seeking, decrement its credit, and restore bank 7 for the clock.
        word(cpu,dl['remaining'],10); word(cpu,0x8003,64); word(cpu,disk.LAST_DISK_FIELDS,0)
        cpu.write8(ql['pending'],1); track=word(cpu,dl['disk_position'])>>8
        cpu.write8(dl['cached_track'],track); cpu.write8(0x5cf5,track)
        before=cpu.dos_reads; seeks=len(cpu.seek_calls)
        result['due_read_tstates']=execute(cpu,ql['no_pending'],rows,stack=0x9df0)
        assert cpu.dos_reads==before+1 and len(cpu.seek_calls)==seeks
        assert cpu.read8(ql['pending'])==0 and word(cpu,dl['remaining'])==9
        assert cpu.port_7ffd&7==7 and word(cpu,disk.LAST_DISK_FIELDS)==64
        result['frame_service_extra_call_tstates']=17
        result['queued_service_cases']=1
        result['frame_entry_tstates_by_elapsed']=frame_costs
    return result


def ring_case(limit, idle_every, interleaved,keepalive_fields=0):
    h,dl,ql,_,expected=fixture(limit,interleaved=interleaved,keepalive_fields=keepalive_fields); cpu=h.cpu
    offset=calls=idle_calls=0; max_pending=0
    # Unaligned requests and four-byte headers also free sectors; multiple
    # bank/ring wraps force replacement before any stale byte is consumed.
    while offset<len(expected):
        count=min((4,256,17,256,255,256,1)[calls%7],len(expected)-offset)
        word(cpu,h.z['remaining'],count)
        cpu.a=0x96; cpu.set_bc(0xabcd); cpu.set_de(0x1234); cpu.carry=cpu.z=True
        execute(cpu,h.z['refill'])
        assert (cpu.a,cpu.bc(),cpu.de(),cpu.hl(),cpu.carry,cpu.z)==(0x96,0xabcd,0x1234,0xbc00,True,True)
        actual=bytes(cpu.read8(0xbc00+i) for i in range(count))
        assert actual==expected[offset:offset+count],(limit,offset,calls)
        offset+=count; calls+=1
        max_pending=max(max_pending,cpu.read8(ql['pending']))
        assert max_pending<limit
        if idle_every and calls%idle_every==0:
            execute(cpu,ql['idle'],stack=0x9df0); idle_calls+=1
            assert cpu.port_7ffd&7==7
    assert word(cpu,dl['remaining'])==0,'not all required disk sectors were acquired'
    return dict(limit=limit,idle_every=idle_every,interleaved=interleaved,
        exact_bytes=offset,consumer_calls=calls,idle_calls=idle_calls,
        max_pending=max_pending,remaining_disk_sectors=0)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--keepalive-fields',type=int,default=0,choices=(0,64))
    p.add_argument('--frame-service',action='store_true');args=p.parse_args()
    if args.frame_service and not args.keepalive_fields: p.error('frame service requires keepalive')
    costs=timings(args.keepalive_fields); print(json.dumps(costs),flush=True)
    cases=[]
    for limit,idle in ((1,0),(8,0),(8,3),(64,5),(248,0),(248,2)):
        for interleaved in (False,True):
            result=ring_case(limit,idle,interleaved,args.keepalive_fields); cases.append(result); print(json.dumps(result),flush=True)
    report=dict(baseline_commit='7aca091',complete=True,release=False,timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope=__doc__,costs=costs,cases=cases,
        new_buffer_bytes=0,new_counter_bytes=3 if args.keepalive_fields else 1,reused_bootstrap_bytes=256,
        startup_staging='A200..A2FF in the initially empty AY queue; copied before audio_init',
        physical_disk_and_frame_timing_verified=False)
    if args.keepalive_fields: report['keepalive']=check_keepalive(args.frame_service)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': main()
