"""Run the direct input/core fixture through all three streams in real Fuse.

Each original TRD cold-boots normally. Before its frame driver starts, the
debugger installs the experimental producer/core and a fixed-RAM test loop.
It resets the disk cursor to the stream start and disables video/AY output.
All subsequent reads execute the real TR-DOS ROM; all decoded bytes are
exported and compared. Dump-loop time is excluded from producer/core totals.
This is NOT a release image, queue schedule, AY/video or physical-drive test.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time

import ay_interrupt
import bank_local_zx0
import direct_slot_input_z80 as producer
import fap3_disk_z80 as disk
import pipelined_frame_z80 as video
import playback_schedule
from benchmark_bank_local_zx0 import disk_blocks,sha
from build_zxv_trd import MiniAssembler
from smoke_test_fuse import hidden_startupinfo

DRIVER=0x6100


def audio_labels():
    a=MiniAssembler(0x9400)
    ay_interrupt.emit(a,backpressure=True)
    playback_schedule.emit_clock(a,dos_irq=True,full_rom_clock=True,memory_clock=True,
        audio_irq=True,video_irq=video.VIDEO)
    a.label('state');ay_interrupt.emit_variables(a)
    a.label('elapsed_fields');a.word(0)
    a.label('fatal');a.emit(0x76);a.label('end')
    return a.resolve(),a.labels


def runner(z,p,audio,count):
    a=MiniAssembler(DRIVER)
    def load(name):a.abs16(0x3a,name)
    def store(name):a.abs16(0x32,name)
    def call(addr):a.emit(0xcd);a.word(addr)
    a.label('entry');a.emit(0x31);a.word(0x9df0)
    a.emit(0xaf);a.emit(0x32);a.word(audio['audio_enabled'])
    a.emit(0x32);a.word(video.ENABLED)
    call(audio['setup_clock']);a.emit(0xfb)
    a.label('block_loop');load('slot');call(p['begin'])
    a.label('input_step');call(p['step']);a.emit(0xb7);a.abs16(0xca,'input_step')
    a.label('input_ready')
    a.emit(0x2a);a.word(z['block_length']);a.abs16(0x22,'left')
    a.emit(0x21);a.word(0xe000);a.emit(0x22);a.word(z['slice_target'])
    a.emit(0x3e,1);store('first')
    a.label('decode_loop');a.abs16(0x2a,'left');a.emit(0x11);a.word(256)
    a.emit(0xb7,0xed,0x52);a.abs16(0xda,'last_quota');a.abs16(0x22,'left')
    a.emit(0x2a);a.word(z['slice_target']);a.emit(0x24);a.abs16(0xc3,'quota_ready')
    a.label('last_quota');a.emit(0x21);a.word(0);a.abs16(0x22,'left')
    a.emit(0x2a);a.word(z['block_end'])
    a.label('quota_ready');a.emit(0x22);a.word(z['slice_target'])
    load('first');a.emit(0xb7);a.abs16(0xca,'resume')
    a.emit(0xaf);store('first');call(z['begin']);a.abs16(0xc3,'decoded_quota')
    a.label('resume');call(z['slice_until'])
    a.label('decoded_quota');a.abs16(0x2a,'left');a.emit(0x7c,0xb5);a.abs16(0xc2,'decode_loop')
    a.label('block_ready');a.emit(0x00)
    a.label('dump_loop');a.emit(0x00)
    a.label('dump_site');a.abs16(0xc3,'dump_loop')
    a.label('after_dump');a.abs16(0x2a,'blocks_left');a.emit(0x2b);a.abs16(0x22,'blocks_left')
    a.emit(0x7c,0xb5);a.abs16(0xca,'finished')
    load('slot');a.emit(0x3c,0xe6,3);store('slot');a.abs16(0xc3,'block_loop')
    a.label('finished');a.emit(0x76)
    a.label('state');a.label('slot');a.emit(0);a.label('first');a.emit(0)
    a.label('left');a.word(0);a.label('blocks_left');a.word(count);a.label('end')
    if a.pc>disk.WAIT_NEXT:raise ValueError('fixture overwrites disk-change prompt')
    return a.resolve(),dict(a.labels)


def run(fuse,directory,part,output,timeout):
    meta,stream,blocks=disk_blocks(directory,part)
    trd=directory/f'ZX-video-huffman-preview_part{part:02}.trd'
    image=trd.read_bytes()
    zcode,z=bank_local_zx0.build(dynamic_input=True)
    dcode,d,_=disk.build_disk(meta['video_start_sector'],meta['video_sectors'],
        fast_disk=True,cached_seek=True,interleaved=True)
    scode,seek,_=disk.build_cached_seek(d)
    pcode,p,_=producer.build(z,d);_,al=audio_labels()
    if any(al[name]!=meta['player_labels'][name] for name in
           ('elapsed_fields','audio_ticks_played','audio_underruns')):
        raise ValueError('existing IRQ assembly layout differs')
    code,driver=runner(z,p,al,len(blocks))
    patches=[(bank_local_zx0.CODE,zcode),(producer.CODE,pcode),(disk.DISK,dcode),
        (disk.CACHED_SEEK,scode),(DRIVER,code)]
    lines=['base 10','set $running 0','set $dump 65536','set $end 65536'];widths={};events=0
    stamp='spectrum:frames*70908+ula:tstates'
    word=lambda addr:f'[{addr}]+256*[{addr+1}]'
    def event(pc,tag,expressions=(),after=(),condition=None,stop=False):
        nonlocal events
        events+=1;widths[tag]=len(expressions)
        lines.extend([f'breakpoint {pc}',f'commands {events}',f'print {tag}'])
        lines.extend('print '+e for e in expressions);lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
        lines.append(f'condition {events} '+(condition or '$running == 1'))
    install=[f'set {base+i} {v}' for base,blob in patches for i,v in enumerate(blob)]
    install+=['set $running 1',f'set z80:pc {DRIVER}']
    nonce=secrets.randbits(30)
    event(disk.DRIVER,90,[stamp,str(nonce)],install,condition='$running == 0')
    event(driver['block_loop'],100,[stamp,'['+str(driver['blocks_left'])+']'])
    event(driver['input_ready'],110,[stamp,word(z['block_length']),word(z['input_pointer'])])
    event(driver['block_ready'],120,[stamp],after=[f'set $dump 57344',f'set $end 57344+{word(z["block_length"])}'])
    expr='[$dump]+256*[$dump+1]+65536*[$dump+2]+16777216*[$dump+3]'
    # Export all output bytes without adding a screen-copy path to the core.
    event(driver['dump_site'],121,[expr],after=['set $dump $dump+4',f'set z80:pc {driver["dump_loop"]}'],
        condition='$running == 1 && $dump < $end')
    event(driver['dump_site'],122,[],after=[f'set z80:pc {driver["after_dump"]}'],
        condition='$running == 1 && $dump >= $end')
    event(driver['finished'],199,[stamp,word(d['remaining']),word(al['elapsed_fields']),f'[{al["audio_enabled"]}]'],stop=True)
    event(0xbdbd,135,[stamp])
    for pc in (z['fatal'],p['fatal']):event(pc,198,[stamp,'z80:pc'],stop=True)
    for name,tag in (('disk_full_call',130),('fast_read_enter',132)):
        event(d[name],tag,[stamp,word(d['disk_position']),f'[{d["write_high"]}]','ula:mem7ffd'],
            after=[f'set $base 256*[{d["write_high"]}]'])
    base='$base'
    data=['+'.join(f'{256**k}*[{base}+{i+k}]' for k in range(4)) for i in range(0,256,4)]
    for name,tag in (('disk_return',131),('fast_disk_return',133)):event(d[name],tag,[stamp]+data)
    event(d['fast_read_retry'],134,[stamp])
    for name,tag in (('seek_side_enter',140),('seek_side_return',141),('seek_enter',142),('seek_return',143)):
        event(seek[name],tag,[stamp])
    script='\n'.join(lines)
    if len(script)>29000:raise ValueError(f'debugger command too long: {len(script)}')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.with_suffix('.debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    command=[str(fuse),'--no-sound','--no-autosave-settings','--no-confirm-actions',
        '--speed','10000','--machine','128','--beta128','--debugger-command',script,str(trd.resolve())]
    start=time.monotonic();epoch=time.time()
    done=subprocess.run(command,cwd=fuse.parent,env=dict(os.environ,SDL_VIDEODRIVER='dummy'),
        capture_output=True,startupinfo=hidden_startupinfo(),timeout=timeout)
    trace=done.stdout.decode(errors='replace')
    output.with_suffix('.stderr.txt').write_text(done.stderr.decode(errors='replace'),encoding='utf-8')
    if (not re.search(r'^\s*\d+\s*$',trace,re.M) and (fuse.parent/'stdout.txt').exists()
            and (fuse.parent/'stdout.txt').stat().st_mtime>=epoch-2):
        trace=(fuse.parent/'stdout.txt').read_text(errors='replace')
    output.with_suffix('.trace.txt').write_text(trace,encoding='utf-8',newline='\n')
    if not trace.strip():raise RuntimeError(('empty Fuse trace',done.returncode,done.stderr.decode(errors='replace')))
    nums=[int(v,0) for v in trace.splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',v.strip())]
    at=0;parsed=[]
    while at<len(nums):
        tag=nums[at];at+=1
        if tag not in widths or at+widths[tag]>len(nums):raise ValueError('invalid trace')
        parsed.append((tag,nums[at:at+widths[tag]]));at+=widths[tag]
    decoded=[];reads=[];seeks=[];pending=None;spending=None;current=None;dump=bytearray();failure=None;final=None;nonces=[];irq=[]
    for tag,v in parsed:
        if tag==90:nonces.append(v[1])
        elif tag==100:current=dict(index=len(decoded),producer_start=v[0])
        elif tag==110:current.update(decode_start=v[0],raw_bytes=v[1],input_pointer=v[2])
        elif tag==120:current['decode_end']=v[0];dump=bytearray()
        elif tag==121:dump+=(v[0]&0xffffffff).to_bytes(4,'little')
        elif tag==122:
            wanted=blocks[len(decoded)][1]
            if len(dump)!=4*((len(wanted)+3)//4) or dump[:len(wanted)]!=wanted:
                raise AssertionError(('Fuse decoded block differs',len(decoded),len(dump),len(wanted)))
            current.update(raw_sha256=sha(wanted),all_decoded_bytes_exact=True,
                producer_elapsed_tstates=current['decode_start']-current['producer_start'],
                decode_elapsed_tstates=current['decode_end']-current['decode_start'])
            decoded.append(current);current=None
        elif tag in (130,132):
            if pending is not None:raise AssertionError('overlapping reads')
            pending=(tag,v)
        elif tag in (131,133):
            if pending is None and tag==131:continue
            if pending is None:raise AssertionError('unexpected read return')
            kind,b=pending;pending=None;sector=(b[1]>>8)*16+(b[1]&255)
            actual=b''.join((n&0xffffffff).to_bytes(4,'little') for n in v[1:])
            reads.append(dict(sector=sector,bank=b[3]&7,destination=b[2]*256,
                kind='full' if kind==130 else 'direct503',tstates=v[0]-b[0],
                bytes_exact=actual==image[sector*256:(sector+1)*256],retried=False))
        elif tag==134:reads[-1]['retried']=True
        elif tag==135:irq.append(v[0])
        elif tag in (140,142):spending=(tag,v[0])
        elif tag in (141,143):
            if spending is None or spending[0]!=tag-1:raise AssertionError('seek mismatch')
            seeks.append(dict(kind='side' if tag==141 else 'seek',tstates=v[0]-spending[1]));spending=None
        elif tag==198:failure=v
        elif tag==199:final=v
    import disk_layout
    wanted=[meta['video_start_sector']+p for p in disk_layout.positions(meta['video_sectors'],meta['video_start_sector']%16)]
    accepted=[r for r in reads if not r['retried']]
    complete=(done.returncode==77 and nonces==[nonce] and final is not None and final[1]==0
        and final[2]==len(irq)>0 and final[3]==0 and failure is None
        and len(decoded)==len(blocks) and current is None and pending is None and spending is None
        and [r['sector'] for r in accepted]==wanted and all(r['bytes_exact'] for r in accepted))
    result=dict(complete=complete,release=False,scope=__doc__,part=part,trd_sha256=sha(image),stream_sha256=sha(stream),
        returncode=done.returncode,run_nonce=nonce,trace_nonce_exact=nonces==[nonce],failure=failure,wall_seconds=time.monotonic()-start,
        measured_from_original_cold_boot=True,fixture_installed_by_debugger=True,
        preloaded_boot_stream_sectors_excluded=min(256,meta['video_sectors']),
        all_output_bytes_compared=complete,decoded_bytes=sum(len(raw) for _,raw in blocks),
        irq_active_with_audio_disabled=bool(irq) and final is not None and final[3]==0,
        irq_entries=len(irq),elapsed_fields=final[2] if final is not None else None,
        video_output_enabled=False,actual_frame_schedule_verified=False,
        producer_elapsed_tstates=sum(r['producer_elapsed_tstates'] for r in decoded),
        decoder_elapsed_tstates=sum(r['decode_elapsed_tstates'] for r in decoded),
        read_attempts=len(reads),accepted_sectors=len(accepted),retries=sum(r['retried'] for r in reads),
        read_service_tstates=sum(r['tstates'] for r in reads),seek_service_tstates=sum(r['tstates'] for r in seeks),
        sector_order_exact=[r['sector'] for r in accepted]==wanted,blocks=decoded,reads=reads,seeks=seeks,
        trace_sha256=sha(output.with_suffix('.trace.txt').read_bytes()),debugger_script_sha256=sha(script.encode()))
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    if not complete:raise AssertionError(('incomplete Fuse fixture',part,done.returncode,failure,len(decoded),len(reads)))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('fuse','directory','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--parts',default='1,2,3');p.add_argument('--timeout',type=float,default=300)
    args=p.parse_args();fuse=args.fuse.resolve()
    if sha((fuse.parent/'roms/trdos.rom').read_bytes())!=disk.TRDOS_503_SHA256:raise ValueError('different ROM')
    for part in map(int,args.parts.split(',')):
        print(f'Actual Fuse direct producer: disk {part}',flush=True)
        r=run(fuse,args.directory,part,args.output/f'part{part:02}.json',args.timeout)
        print(json.dumps({k:v for k,v in r.items() if k not in ('blocks','reads','seeks','scope')}),flush=True)


if __name__=='__main__':main()
