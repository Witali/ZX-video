"""Inline short/long paths, bank aliasing, mixed frames and AY register lifetime."""
from collections import Counter
import unittest
import ay_interrupt
import playback_schedule
from build_zxv_trd import MiniAssembler
from benchmark_context_huffman import word
from benchmark_prefix_huffman import Harness as Prefix,INPUT as PREFIX_INPUT
from benchmark_static_cache_borders import OPTIONS
from frame_output_pipeline import Harness,frames,serialized_masks,STACK,STOP
from probe_motion_entropy import codes_for
from test_prefix_huffman_z80 import candidate
from test_frame_output_pipeline import fixture
from raw_attribute_stream import pack
import uncontended_frame as move
import inline_huffman_patches as inline


def frame(tables,mapping):
    return Harness(tables,mapping,carry_huffman=True,register_fragments=True,
        cached_huffman_byte=True,metadata_mode='compiled',**dict(OPTIONS,skip_static_stripes=False))


class InlinePatchTests(unittest.TestCase):
    def test_every_bitmap_code_at_every_bit_offset(self):
        # The older 4971-frame profile leaves only 93 bytes of tail RAM.
        # Exercise all its trees in smaller batches; real current-volume
        # placement is separately checked by the complete movie benchmark.
        source,_=candidate()
        for start in range(0,len(source)-1,4):
            trees=source[start:min(start+4,len(source)-1)]
            self.check_codes(trees+[source[-1]],bytes(i%len(trees) for i in range(256)))

    def check_codes(self,tables,mapping):
        h=frame(tables,mapping);report=inline.install_stage(h,tables,mapping)
        old=Prefix(tables,mapping,carry_huffman=True,cached_byte=True);c=h.cpu
        entry,exit=report['symbol_entries'][0],report['symbol_exits'][0]
        seen=set()
        for context,table in enumerate(tables[:-1]):
            predictor=mapping.index(context)
            for value,(code,length) in enumerate(codes_for(255,table)):
                if not length:continue
                for offset in range(8):
                    encoded=(code<<((-offset-length)%8)).to_bytes((offset+length+7)//8,'big')
                    old.begin(encoded);old.cpu.write8(PREFIX_INPUT+len(encoded),0xa5)
                    old.cpu.write8(old.labels['bit_page'],0xf8+offset)
                    before=old.run([(0,predictor)],bytes([value]))['primitive_tstates']+17
                    c.guarding=False
                    for i,v in enumerate(encoded+b'\xa5'):c.write8(0xa6a0+i,v)
                    c.a=predictor;c.ix=0xa6a0;c.b=encoded[0];c.c=0xf8+offset
                    c.pc=entry;c.sp=STACK;c.input_end=0xa6a0+len(encoded)+1
                    c.phase='reconstruct';c.guarding=True;ticks=c.tstates;steps=0
                    while c.pc!=exit:
                        row=h.instructions[c.pc];start=c.tstates;c.step();steps+=1
                        wanted=row['tstates'];self.assertIn(c.tstates-start,wanted if isinstance(wanted,list) else [wanted])
                        self.assertLess(steps,300)
                    difference=c.tstates-ticks-before
                    self.assertEqual(difference,-24 if length<=8 else 8);seen.add(difference)
                    self.assertEqual(c.a,value);self.assertEqual(c.sp,STACK)
                    self.assertEqual((c.ix-0xa6a0)*8+(c.c&7),offset+length)
                    self.assertEqual(c.b,c.read8(c.ix))
        self.assertEqual(seen,{-24,8})

    def test_mixed_frames_and_ay_after_every_instruction(self):
        states,stream,_=fixture(2,constant_attribute_borders=True)
        stream,_=pack(stream,states,[True,False]);tables,mapping,packets=frames(stream)
        meta=serialized_masks(stream);old,new=[frame(tables,mapping) for _ in range(2)]
        move.install_stage(new);inline.install_stage(new,tables,mapping)
        c=new.cpu;c.guarding=False;a=MiniAssembler(0x9400);ay_interrupt.emit(a)
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
        previous=Counter()
        for i,((group,native),state) in enumerate(zip(packets,states)):
            before=old.run(group,native,state.tobytes(),i,encoded_metadata=meta[i],cache_map=b'\xff'*3)
            after=move.run_stage(new,group,native,state.tobytes(),i,meta[i],b'\xff'*3,irq)
            counts=new.inline_counts-previous;previous=new.inline_counts.copy()
            self.assertEqual(after['total_tstates']-before['total_tstates'],inline.delta(counts))
        self.assertGreater(calls,20000);self.assertGreater(new.inline_counts['symbols'],0)

    def test_refuse_overlap_with_huffman_tail(self):
        tables,mapping=candidate();h=frame(tables,mapping)
        with self.assertRaisesRegex(ValueError,'no room'):
            inline.build(h.cpu.read8,h.instructions.values(),h.recon,12288)


if __name__=='__main__':unittest.main()
