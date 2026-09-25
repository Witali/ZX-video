"""Relocated metadata, mixed prediction and AY at every instruction boundary."""
import unittest
import ay_interrupt
import playback_schedule
from build_zxv_trd import MiniAssembler
from benchmark_context_huffman import word
from benchmark_static_cache_borders import OPTIONS
from frame_output_pipeline import Harness,frames,serialized_masks,STACK,STOP
from probe_motion_metadata import transform
from test_frame_output_pipeline import fixture
from raw_attribute_stream import pack
import uncontended_frame as move


def harness(tables,mapping):
    options=dict(OPTIONS,skip_static_stripes=False)
    return Harness(tables,mapping,carry_huffman=True,register_fragments=True,**options)


class UncontendedFrameTests(unittest.TestCase):
    def test_every_presence_pattern_in_relocated_mask_pages(self):
        h=harness([bytes([8]*256)]*2,bytes(256));move.install_stage(h);c=h.cpu
        from frame_metadata_z80 import expected_tstates
        for mask in range(256):
            values=bytes((i%255+1) if mask&(128>>(i%8)) else 0 for i in range(480))
            encoded=transform(values,480,4);c.guarding=False
            for i,v in enumerate(encoded):c.write8(move.INPUT+i,v)
            c.input_end=move.INPUT+len(encoded);c.set_hl(move.INPUT)
            result=h.execute(0x7800)
            self.assertEqual(result['total_tstates'],expected_tstates(encoded))
            self.assertEqual(c.hl(),c.input_end)
            self.assertEqual(bytes(c.read8(move.MASKS+i) for i in range(480)),values)
            self.assertEqual(bytes(c.read8(0xbfbc+i) for i in range(4)),bytes(4))

    def test_mixed_frames_and_ay_after_every_instruction(self):
        states,stream,_=fixture(2,constant_attribute_borders=True)
        stream,_=pack(stream,states,[True,False])
        tables,mapping,packets=frames(stream);meta=serialized_masks(stream)
        old,new=[harness(tables,mapping) for _ in range(2)];move.install_stage(new)
        c=new.cpu;c.guarding=False
        a=MiniAssembler(0x9400);ay_interrupt.emit(a)
        playback_schedule.emit_clock(a,dos_irq=True,full_rom_clock=True,memory_clock=True,audio_irq=True)
        ay_interrupt.emit_variables(a);a.label('elapsed_fields');a.word(0);a.label('fatal');a.emit(0x76)
        for i,v in enumerate(a.resolve()):c.write8(0x9400+i,v)
        c.pc=a.labels['setup_clock'];c.sp=STACK;c.push(STOP)
        while c.pc!=STOP:c.step()
        c.write8(a.labels['audio_enabled'],1)
        names=('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_b','alt_c','alt_d','alt_e',
               'alt_h','alt_l','alt_z','alt_carry','port_7ffd','sp')
        calls=0
        def irq(c):
            nonlocal calls
            c.guarding=False;word(c,a.labels['audio_remaining'],65535)
            i=c.read8(a.labels['audio_read_index']);slot=ay_interrupt.QUEUE_BASE+i*ay_interrupt.SLOT_BYTES
            c.write8(slot,1);c.write8(slot+1,8);c.write8(slot+2,calls&15)
            c.write8(a.labels['audio_write_index'],(i+1)&31)
            before=tuple(getattr(c,n) for n in names);start,pc=c.tstates,c.pc
            c.push(pc);c.pc=0xbdbd;c.iff1=False;c.tstates+=19
            while c.pc!=pc:
                self.assertNotEqual(c.pc,a.labels['fatal']);c.step()
            self.assertEqual(tuple(getattr(c,n) for n in names),before)
            self.assertEqual(c.ay[8],calls&15);self.assertEqual(c.tstates-start,583)
            self.assertEqual(word(c,a.labels['audio_underruns']),0)
            calls+=1;c.guarding=True;return c.tstates-start
        for i,((group,native),state) in enumerate(zip(packets,states)):
            before=old.run(group,native,state.tobytes(),i,encoded_metadata=meta[i],cache_map=b'\xff'*3)
            after=move.run_stage(new,group,native,state.tobytes(),i,meta[i],b'\xff'*3,irq)
            self.assertEqual(before['total_tstates'],after['total_tstates'])
        self.assertGreater(calls,20000)


if __name__=='__main__':unittest.main()
