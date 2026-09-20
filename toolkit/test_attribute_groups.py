import unittest

import numpy as np
import attribute_groups_z80 as machine
import ay_interrupt
import playback_schedule
from attribute_update_stream import encode_attributes,apply_attributes
from benchmark_attribute_groups import Harness
from benchmark_compact_screen import STACK,STOP
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler
from frame_output_pipeline import Harness as Pipeline,frames,serialized_masks
from probe_sparse_motion_cache import coverage
from raw_attribute_stream import pack
from test_frame_output_pipeline import fixture


class AttributeGroupTests(unittest.TestCase):
    def test_pc_records_sparse_full_and_malformed(self):
        previous=b'\1'*768; current=bytearray(previous)
        for at in (96,103,104,255,256,511,512,671): current[at]=71
        for full in (False,True):
            record=encode_attributes(previous,bytes(current),force_full=full)
            self.assertEqual(apply_attributes(previous,record),current)
        with self.assertRaisesRegex(ValueError,'unordered or empty'):
            apply_attributes(previous,bytes([3,0,1,72,1]))

    def test_all_flag_patterns_and_group_boundaries(self):
        h=Harness(); attrs=bytearray(b'\1'*768); index=0
        for _ in range(2): h.run(bytes(attrs),bytes(96),False,index); index+=1
        # Each block of eight mask groups, including the clipped edge blocks.
        for block in range(1,11):
            for pattern in range(256):
                masks=bytearray(96)
                for bit in range(8):
                    group=block*8+bit
                    if pattern&(128>>bit) and 12<=group<84:
                        masks[group]=128>>(pattern%8); attrs[group*8+pattern%8]^=0x11
                h.run(bytes(attrs),bytes(masks),False,index); index+=1
        # Raw frames use a marker; the following two sparse frames must
        # retire it correctly before index-based output resumes.
        attrs[96:672]=b'\x47'*576
        h.run(bytes(attrs),bytes(96),True,index); index+=1
        for _ in range(3): h.run(bytes(attrs),bytes(96),False,index); index+=1

    def test_pipeline_reconstruction_both_screens_and_cycle_delta(self):
        states,stream,_=fixture(4,constant_attribute_borders=True)
        stream,_=pack(stream,states,[True,False,True,False]); tables,mapping,packets=frames(stream)
        meta=serialized_masks(stream)
        opts=dict(raw_attributes=True,decode_metadata=True,fast_mask_dispatch=True,
            selective_cache=True,constant_attribute_borders=True)
        old=Pipeline(tables,mapping,**opts); new=Pipeline(tables,mapping,attribute_groups=True,**opts)
        for i,((group,mask),state) in enumerate(zip(packets,states)):
            cache=np.packbits(coverage(group[3],32).reshape(24,4).any(axis=1)).tobytes()
            a=old.run(group,mask,state.tobytes(),i,encoded_metadata=meta[i],cache_map=cache)
            b=new.run(group,mask,state.tobytes(),i,encoded_metadata=meta[i],cache_map=cache)
            counts=[new.cpu.read8(base) for base in machine.LISTS]
            self.assertEqual(b['total_tstates']-a['total_tstates'],
                17+b['stages']['attribute_groups']+machine.draw_tstates(counts)-9778)

    def test_sparse_and_full_irq_after_each_instruction(self):
        h=Harness(); attrs=bytearray(b'\1'*768)
        for i in range(3): h.run(bytes(attrs),bytes(96),False,i)
        a=MiniAssembler(0x9400); ay_interrupt.emit(a)
        playback_schedule.emit_clock(a,dos_irq=True,full_rom_clock=True,memory_clock=True,audio_irq=True)
        ay_interrupt.emit_variables(a); a.label('elapsed_fields'); a.word(0); a.label('fatal'); a.emit(0x76)
        cpu=h.cpu; cpu.guarding=False
        for i,v in enumerate(a.resolve()): cpu.write8(0x9400+i,v)
        cpu.pc,cpu.sp=a.labels['setup_clock'],STACK; cpu.push(STOP)
        while cpu.pc!=STOP: cpu.step()
        cpu.write8(a.labels['audio_enabled'],1)
        names=('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_b','alt_c','alt_d','alt_e',
            'alt_h','alt_l','alt_z','alt_carry','port_7ffd','sp')
        calls=0
        def interrupt(cpu):
            nonlocal calls
            cpu.guarding=False; word(cpu,a.labels['audio_remaining'],65535)
            index=cpu.read8(a.labels['audio_read_index']); slot=ay_interrupt.QUEUE_BASE+32*index
            for i,v in enumerate((1,8,calls&15)): cpu.write8(slot+i,v)
            cpu.write8(a.labels['audio_write_index'],(index+1)&31)
            before={n:getattr(cpu,n) for n in names}; pc,start=cpu.pc,cpu.tstates
            cpu.push(pc); cpu.pc=0xbdbd; cpu.iff1=False; cpu.tstates+=19
            while cpu.pc!=pc:
                self.assertNotEqual(cpu.pc,a.labels['fatal']); cpu.step()
            self.assertEqual(before,{n:getattr(cpu,n) for n in names})
            self.assertEqual(cpu.ay[8],calls&15); self.assertEqual(cpu.tstates-start,583)
            calls+=1; self.assertEqual(word(cpu,a.labels['audio_underruns']),0)
            cpu.guarding=True; return cpu.tstates-start
        steps_before=sum(h.histogram.values()); h.interrupt=interrupt
        masks=bytearray(96); masks[12]=128; masks[83]=1; attrs[96]=71; attrs[671]=120
        h.run(bytes(attrs),bytes(masks),False,3)
        h.run(bytes(attrs),bytes(96),True,4)
        # Two stages per frame: the final instruction of each returns to
        # the host before an IRQ can be injected. Every other one is covered.
        self.assertEqual(calls,sum(h.histogram.values())-steps_before-4)
        self.assertGreater(calls,0)
        executed={address for address,_ in h.histogram}
        self.assertIn(h.h.draw['attribute_group'],executed)
        self.assertIn(h.h.draw['attribute_full'],executed)


if __name__=='__main__': unittest.main()
