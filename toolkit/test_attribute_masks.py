import unittest

import numpy as np
import ay_interrupt
import playback_schedule
from attribute_mask_z80 import delta_tstates
from benchmark_attribute_masks import Harness
from benchmark_compact_screen import STACK,STOP
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler
from frame_output_pipeline import Harness as Pipeline,frames,serialized_masks
from raw_attribute_stream import pack
from test_frame_output_pipeline import fixture
from probe_sparse_motion_cache import coverage
from probe_motion_entropy import codes_for


class AttributeMaskTests(unittest.TestCase):
    def test_all_flags_boundaries_and_raw(self):
        old,new=Harness(),Harness(flags=True)
        previous=bytes(768)
        for block in range(12):
            for bits in range(256):
                masks=bytearray(96); current=bytearray(previous); coded=bytearray()
                for group in range(8):
                    if bits&(128>>group):
                        at=8*block+group; masks[at]=128>>(bits%8)
                        value=(bits+group)%255+1; current[8*at+bits%8]=value; coded.append(value)
                args=(previous,bytes(current),bytes(masks),bytes(coded),b'',0,8*len(coded),False)
                a,b=old.run(*args),new.run(*args)
                self.assertEqual(b-a,delta_tstates(masks))
        masks=b'\xff'*96; current=bytes((i%255)+1 for i in range(768))
        for raw in (False,True):
            args=(previous,current,bytes(96) if raw else masks,b'' if raw else current,current if raw else b'',0,0 if raw else 6144,raw)
            self.assertEqual(new.run(*args)-old.run(*args),delta_tstates(args[2],raw))

    def test_integrated_reconstruction_and_two_native_screens(self):
        states,stream,_=fixture(4,constant_attribute_borders=True)
        stream,_=pack(stream,states,[True,False,True,False]); tables,mapping,packets=frames(stream)
        metadata=serialized_masks(stream)
        options=dict(raw_attributes=True,decode_metadata=True,fast_mask_dispatch=True,
            selective_cache=True,constant_attribute_borders=True,attribute_groups=True)
        old=Pipeline(tables,mapping,**options); new=Pipeline(tables,mapping,attribute_flags=True,**options)
        for i,((group,mask),state) in enumerate(zip(packets,states)):
            cache=np.packbits(coverage(group[3],32).reshape(24,4).any(axis=1)).tobytes()
            a=old.run(group,mask,state.tobytes(),i,encoded_metadata=metadata[i],cache_map=cache)
            b=new.run(group,mask,state.tobytes(),i,encoded_metadata=metadata[i],cache_map=cache)
            self.assertEqual(b['total_tstates']-a['total_tstates'],delta_tstates(group[5],bool(group[1]&64)))

    def test_irq_after_every_instruction_including_long_codes(self):
        table=bytes(list(range(1,18))+[18,18]+[0]*237)
        h=Harness([bytes([8]*256),table],bytes(256),flags=True)
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
            saved={name:getattr(cpu,name) for name in names}; pc,start=cpu.pc,cpu.tstates
            cpu.push(pc); cpu.pc=0xbdbd; cpu.iff1=False; cpu.tstates+=19
            while cpu.pc!=pc:
                self.assertNotEqual(cpu.pc,a.labels['fatal']); cpu.step()
            self.assertEqual(saved,{name:getattr(cpu,name) for name in names})
            self.assertEqual(cpu.ay[8],calls&15); self.assertEqual(cpu.tstates-start,583)
            self.assertEqual(word(cpu,a.labels['audio_underruns']),0)
            calls+=1; cpu.guarding=True; return cpu.tstates-start
        previous=bytes(768); start_steps=sum(h.h.histogram.values())
        for positions in ((0,255,512,767),tuple(range(0,768,8))):
            current=bytearray(previous); value=0; bits=7
            for at in positions:
                current[at]=18; code,n=codes_for(255,table)[18]; value=(value<<n)|code; bits+=n
            coded=(value<<((-bits)&7)).to_bytes((bits+7)//8,'big')
            masks=np.packbits(np.frombuffer(current,dtype=np.uint8)!=0).tobytes()
            h.run(previous,bytes(current),masks,coded,b'',7,bits,False,interrupt)
        h.run(previous,bytes(current),bytes(96),b'',bytes(current),0,0,True,interrupt)
        self.assertEqual(calls,sum(h.h.histogram.values())-start_steps-3)
        self.assertGreater(calls,0)


if __name__=='__main__': unittest.main()
