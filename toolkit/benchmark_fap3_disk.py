"""Instruction timing of the FAP3 disk adapter, excluding ROM/IRQ/ULA/disk.

Same-track fast reads use the previously verified TR-DOS 5.03 entry. Failed
short reads deliberately corrupt a prefix, then exercise the full fallback.
"""
import argparse
import json
from pathlib import Path

from benchmark_context_huffman import word
import fap3_disk_z80 as disk
import pipelined_frame_z80 as video
from test_fap3_disk import DiskCPU,install


class ShortReadCPU(DiskCPU):
    short_once=False

    def instruction(self):
        if (self.short_once and self.read8(self.pc)==0xc3
                and word(self,self.pc+1)==0x3d2f and word(self,self.sp)==0x3f17):
            self.short_once=False; self.pop(); self.pop()
            target=word(self,0x5d00)
            for i in range(17): self.write8(target+i,0xee)
            self.set_hl(target+17); self.pc=self.pop()
            return 10  # JP only, as in the existing CPU ROM stub.
        return super().instruction()


def run(*,fast_disk,track=3,sector=1,region=0,high=0xc0,cached=3,short=False,cached_seek=False,drive=0,interleaved=False,irq_safe_paging=False):
    data=b''.join(bytes([i%251])*256 for i in range(2560))
    cpu=ShortReadCPU(b'',data);cpu.poison_rom=True;cpu.short_once=short;cpu.port_7ffd=0x1f
    regions,_,vl=video.build_video(dict(saved_page=0x8000,screen_base=0x8001),
        dict(history_page=0x8002),dict(elapsed_fields=0x8003),irq_safe_paging=irq_safe_paging)
    for address,blob in regions: install(cpu,address,blob)
    cpu.write8(video.SHADOW,0x1f)
    code,l,rows=disk.build_disk(track*16+sector,7,fast_disk=fast_disk,cached_seek=cached_seek,interleaved=interleaved)
    install(cpu,disk.DISK,code)
    seek_bytes=0
    if cached_seek:
        seek_code,seek_labels,seek_rows=disk.build_cached_seek(l)
        install(cpu,disk.CACHED_SEEK,seek_code); rows+=seek_rows; seek_bytes=len(seek_code)
    cpu.write8(l['write_region'],region);cpu.write8(l['write_high'],high)
    if fast_disk: cpu.write8(l['cached_track'],cached)
    cpu.write8(0x5cf5,track)
    cpu.write8(0x5cf6,drive); cpu.write8(0x5cfa+drive,0x80|drive)
    cpu.set_hl(0xc100);cpu.sp=0x7bc0;cpu.push(0x5f00);cpu.pc=disk.DISK
    saved={name:i+1 for i,name in enumerate(('ix','iy','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l'))}
    saved.update(alt_z=True,alt_carry=True)
    for name,value in saved.items(): setattr(cpu,name,value)
    instructions={r['address']:r for r in rows+vl}; visits={}
    while cpu.pc!=0x5f00:
        pc=cpu.pc;before=cpu.tstates;cpu.step();ticks=cpu.tstates-before
        wanted=instructions[pc]['tstates']
        assert ticks in (wanted if isinstance(wanted,list) else [wanted]),(hex(pc),ticks,wanted)
        visits[pc]=visits.get(pc,0)+1
        assert cpu.steps<500
    assert {n:getattr(cpu,n) for n in saved}==saved
    assert cpu.sp==0x7bc0 and word(cpu,l['remaining'])==6
    if interleaved:
        next_sector=(sector+8 if sector<8 else sector-7) if sector<15 else 16
        assert word(cpu,l['disk_position'])==(track+next_sector//16)*256+next_sector%16
    else:
        assert word(cpu,l['disk_position'])==disk.packed_sector(track*16+sector+1)
    assert cpu.read8(l['write_high'])==(high+1 if high<255 else 0xc0)
    assert cpu.read8(l['write_region'])==(region if high<255 else (region+1)%4)
    assert bytes(cpu.banks[(0,1,3,4)[region]][(high-0xc0)*256:(high-0xc0+1)*256])==data[(track*16+sector)*256:(track*16+sector+1)*256]
    assert cpu.port_7ffd&8 and word(cpu,0xbdbe)==0xbd80
    if fast_disk: assert cpu.read8(l['cached_track'])==track
    if cached_seek and cached not in (255,track):
        assert [c[0] for c in cpu.seek_calls]==[0x1ff6 if track&1 else 0x1feb,0x3e44],cpu.seek_calls
        assert cpu.seek_calls[-1][1:]==(track//2,drive),cpu.seek_calls
        if not short: assert cpu.read8(0x5cfe)==0x84
    else: assert not cpu.seek_calls
    return dict(tstates=cpu.tstates,code_bytes=len(code),
        seek_bytes=seek_bytes,
        full_calls=visits.get(l['disk_full_call'],0),
        direct_calls=visits.get(l.get('fast_read_enter'),0),
        fallback_calls=visits.get(l.get('fast_read_retry'),0))


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    rows={}
    for name,options in [('same_track',{}),('cold',dict(cached=255)),('next_track',dict(cached=2)),
        ('track_wrap',dict(sector=15)),('ring_wrap',dict(region=3,high=255)),('short_retry',dict(short=True))]:
        old=run(fast_disk=False,**{k:v for k,v in options.items() if k!='short'})
        new=run(fast_disk=True,**options)
        rows[name]=dict(previous=old,current=new,delta_tstates=new['tstates']-old['tstates'])
    # All 160 logical tracks; every ring bank, including both boundary types.
    for track in range(160):
        for region in range(4):
            run(fast_disk=True,track=track,sector=15,region=region,high=255,cached=track)
            run(fast_disk=True,track=track,sector=0,region=region,cached=track^1)
    report=dict(baseline_commit='63cc07d',scope=__doc__,complete=True,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',routines=rows,
        geometry_cases=1280,rom_execution_verified=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__': main()
