"""Disk adapter/register/ring and multi-volume bootstrap tests (ROM mocked)."""
import argparse
import json
from pathlib import Path
import unittest

import ay_interrupt
from benchmark_compact_screen import NativeCPU
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler
import fap3_disk_z80 as disk
import pipelined_frame_z80 as video
from validate_streaming_player import extract_file,parse_dir


class DiskCPU(NativeCPU):
    def __init__(self,*args):
        super().__init__(*args); self.iy=0; self.poison_rom=False

    def instruction(self):
        if self.read8(self.pc)==0xfd:
            self.pc+=1; op=self.fetch8()
            if op==0x21: self.iy=self.fetch16(); return 14
            if op==0xe5: self.push(self.iy); return 15
            if op==0xe1: self.iy=self.pop(); return 14
            raise AssertionError(f'unexpected FD {op:x}')
        return super().instruction()

    def mock_trdos(self):
        super().mock_trdos()
        if self.poison_rom:
            for name in ('ix','iy','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l'):
                setattr(self,name,0)
            self.alt_z=False; self.alt_carry=False


def install(cpu,address,blob):
    for i,x in enumerate(blob): cpu.write8(address+i,x)


class AdapterTests(unittest.TestCase):
    def test_complete_refill_before_after(self):
        import stream_reader_harness
        results=[]
        for count in (4,256):
            timings=[]
            for hooked in (False,True):
                source=bytes((i*71)&255 for i in range(1024))
                h=stream_reader_harness.Harness(source,ring_start=0,token_boundaries=True,
                    page_entry=video.PAGE,unrolled_copy=True,disk_refill_entry=disk.DISK if hooked else None)
                cpu=h.cpu; cpu.__class__=DiskCPU; cpu.iy=0; cpu.poison_rom=True; cpu.trd=bytes(655360)
                regions,_,_=video.build_video(dict(saved_page=0x8000,screen_base=0x8001),
                    dict(history_page=0x8002),dict(elapsed_fields=0x8003))
                for address,blob in regions: install(cpu,address,blob)
                code,_,_=disk.build_disk(32,10); install(cpu,disk.DISK,code)
                word(cpu,h.z['remaining'],count)
                cpu.pc=h.z['refill']; cpu.sp=0x7bc0; cpu.push(0x5f00)
                cpu.a=0x96; cpu.set_bc(0xabcd); cpu.set_de(0x1234); cpu.carry=cpu.z=True
                while cpu.pc!=0x5f00: cpu.step()
                self.assertEqual(bytes(cpu.read8(0xbc00+i) for i in range(count)),source[:count])
                self.assertEqual((cpu.a,cpu.bc(),cpu.de(),cpu.hl(),cpu.carry,cpu.z,cpu.sp),
                    (0x96,0xabcd,0x1234,0xbc00,True,True,0x7bc0))
                timings.append(cpu.tstates)
            results.append(dict(bytes=count,old_tstates=timings[0],new_tstates=timings[1],delta=timings[1]-timings[0]))
        print('REFILL_TIMINGS '+json.dumps(results),flush=True)

    def test_refill_registers_wrap_and_instruction_counts(self):
        self.results=[]
        for region,high,sector in ((0,0xc0,32),(1,0xd0,47),(2,0xff,62),(3,0xff,79)):
            with self.subTest(region=region):
                data=bytes((i*31+i//256)&255 for i in range(655360))
                cpu=DiskCPU(b'',data); cpu.port_7ffd=0x1f
                regions,_,listing=video.build_video(dict(saved_page=0x8000,screen_base=0x8001),
                    dict(history_page=0x8002),dict(elapsed_fields=0x8003))
                for address,blob in regions: install(cpu,address,blob)
                cpu.write8(video.SHADOW,0x1f)
                code,l,rows=disk.build_disk(sector,7); install(cpu,disk.DISK,code)
                cpu.write8(l['write_region'],region); cpu.write8(l['write_high'],high)
                cpu.set_hl(0xc100); cpu.sp=0x7bc0; cpu.push(0x5f00); cpu.pc=disk.DISK
                saved={name:i+1 for i,name in enumerate(('ix','iy','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l'))}
                saved.update(alt_z=True,alt_carry=True)
                for name,value in saved.items(): setattr(cpu,name,value)
                cpu.poison_rom=True
                instructions={r['address']:r for r in rows+listing}; elapsed=0
                while cpu.pc!=0x5f00:
                    pc=cpu.pc; before=cpu.tstates; cpu.step(); ticks=cpu.tstates-before
                    expected=instructions[pc]['tstates']
                    self.assertIn(ticks,expected if isinstance(expected,list) else [expected]); elapsed+=ticks
                self.assertEqual({n:getattr(cpu,n) for n in saved},saved)
                self.assertEqual(cpu.sp,0x7bc0)
                self.assertEqual(word(cpu,l['remaining']),6)
                self.assertEqual(word(cpu,l['disk_position']),disk.packed_sector(sector+1))
                self.assertEqual(cpu.read8(l['write_high']),high+1 if high<255 else 0xc0)
                self.assertEqual(cpu.read8(l['write_region']),region if high<255 else (region+1)%4)
                self.assertEqual(bytes(cpu.banks[(0,1,3,4)[region]][(high-0xc0)*256:(high-0xc0+1)*256]),data[sector*256:(sector+1)*256])
                self.assertEqual(cpu.port_7ffd&8,8)
                self.results.append(dict(region=region,write_high=high,sector=sector,adapter_tstates=elapsed))
        print('DISK_TIMINGS '+json.dumps(self.results),flush=True)

    def test_no_read_until_sector_complete_or_after_eof(self):
        for high,remaining,expected in ((0xc0,3,28),(0xc1,0,74)):
            cpu=DiskCPU(b'',b''); code,l,_=disk.build_disk(32,remaining); install(cpu,disk.DISK,code)
            cpu.set_hl(high*256+3); cpu.sp=0x7bc0; cpu.push(0x5f00); cpu.pc=disk.DISK
            while cpu.pc!=0x5f00: cpu.step()
            self.assertEqual(cpu.dos_reads,0); self.assertEqual(cpu.tstates,expected)

    def test_audio_queue_backpressure_preserves_records(self):
        a=MiniAssembler(0x9400); ay_interrupt.emit(a,backpressure=True)
        a.label('fatal'); a.emit(0x76); ay_interrupt.emit_variables(a)
        cpu=DiskCPU(b'',b''); install(cpu,0x9400,a.resolve())
        cpu.write8(a.labels['audio_enabled'],1); cpu.write8(a.labels['audio_write_index'],31)
        word(cpu,a.labels['audio_remaining'],100)
        install(cpu,0xa600,b'\0'*6); cpu.set_hl(0xa600)
        cpu.pc=a.labels['audio_enqueue_six']; cpu.sp=0x9df0; cpu.push(0x5f00)
        waits=0
        while cpu.pc!=0x5f00:
            self.assertNotEqual(cpu.pc,a.labels['fatal'])
            opcode=cpu.read8(cpu.pc); cpu.step()
            if opcode==0x76:
                waits+=1; back=cpu.pc; cpu.push(back); cpu.pc=a.labels['audio_tick']
                while cpu.pc!=back: cpu.step()
        self.assertEqual(waits,6); self.assertEqual(cpu.hl(),0xa606)
        self.assertEqual(cpu.read8(a.labels['audio_write_index']),5)
        self.assertEqual(word(cpu,a.labels['audio_ticks_played']),6)
        self.assertEqual(word(cpu,a.labels['audio_underruns']),0)


def verify_swaps(directory,output):
    reports=[]
    records=json.loads((directory/'volumes.json').read_text(encoding='utf-8'))
    names=[r.get('file',f'ZX-video-optimized-preview_part{r.get("part", i+1):02}.trd')
           for i,r in enumerate(records)]
    for part,(current_name,next_name) in enumerate(zip(names,names[1:]),1):
        current=directory/current_name
        following=directory/next_name
        m=json.loads(current.with_suffix('.json').read_text()); next_meta=json.loads(following.with_suffix('.json').read_text())
        data=current.read_bytes(); player=extract_file(data,next(e for e in parse_dir(data) if e[0]=='PLAYER'))
        cpu=DiskCPU(player,data)
        # Execute the real cold bootstrap with sector services mocked.
        while cpu.pc!=disk.DRIVER:
            cpu.step()
            if cpu.steps>3000000: raise AssertionError('bootstrap stalled')
        # Simulate arrival at EOF. Prompt and disk selection are real opcodes.
        cpu.pc=disk.WAIT_NEXT; stop=m['bootstrap_labels']['poll_next']; reads=cpu.dos_reads
        while cpu.pc!=stop: cpu.step()
        for bank in (5,7):
            for row in range(7):
                if bytes(cpu.banks[bank][0x10c0+row*256:0x10e0+row*256])!=disk.prompt_bitmap()[row*32:(row+1)*32]:
                    raise AssertionError('prompt pixels differ')
        # Wrong disk: complete one poll and remain in the wait loop.
        cpu.step()
        while cpu.pc!=stop: cpu.step()
        if cpu.dos_reads!=reads+1: raise AssertionError('incorrect poll count')
        wrong_movie=bytearray(following.read_bytes()); wrong_movie[15*256+8]^=1
        cpu.trd=bytes(wrong_movie); cpu.step()
        while cpu.pc!=stop: cpu.step()
        if cpu.dos_reads!=reads+2: raise AssertionError('different series accepted')
        cpu.trd=following.read_bytes(); cpu.step(); accepted=False
        while cpu.pc!=disk.DRIVER:
            if cpu.pc==m['bootstrap_labels']['next_disk_accepted']: accepted=True
            cpu.step()
            if cpu.steps>6000000: raise AssertionError('next disk bootstrap stalled')
        if not accepted: raise AssertionError('disk check bypassed')
        # Compare with an independent cold boot. A6A0 is intentionally used
        # as compressed startup staging, so its pre-install hash is obsolete.
        import hashlib
        expected_image=following.read_bytes()
        expected_player=extract_file(expected_image,next(e for e in parse_dir(expected_image) if e[0]=='PLAYER'))
        expected_cpu=DiskCPU(expected_player,expected_image)
        while expected_cpu.pc!=disk.DRIVER: expected_cpu.step()
        for s in next_meta['sections']:
            raw=bytes(cpu.banks[s['bank']][s['address']&16383:(s['address']&16383)+s['decoded_bytes']])
            expected=bytes(expected_cpu.banks[s['bank']][s['address']&16383:(s['address']&16383)+s['decoded_bytes']])
            if raw!=expected: raise AssertionError(('next RAM differs',part,s['bank'],s['address']))
        reports.append(dict(from_part=part,to_part=part+1,prompt_exact=True,wrong_disk_rejected=True,
            wrong_series_rejected=True,correct_disk_accepted=True,bootstrap_ram_exact=True,rom_mocked=True))
    output.write_text(json.dumps(reports,indent=2)+'\n'); print(json.dumps(reports),flush=True)


if __name__=='__main__':
    import sys
    if '--volumes' in sys.argv:
        p=argparse.ArgumentParser(); p.add_argument('--volumes',type=Path);p.add_argument('--output',type=Path,required=True)
        args=p.parse_args(); verify_swaps(args.volumes,args.output)
    else: unittest.main()
