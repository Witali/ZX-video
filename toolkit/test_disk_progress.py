import unittest

import disk_progress_z80 as progress
from benchmark_disk_progress import Harness as ProgressHarness,measure_disk
from bulk_frame_stream import pack
from test_frame_stream_z80 import source,ring
from frame_stream_harness import Harness
from frame_output_pipeline import frames,display_screen
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from benchmark_context_huffman import word
import ay_interrupt


class DiskProgressTests(unittest.TestCase):
    def test_disk_boundaries_and_reset(self):
        h = ProgressHarness()
        for count in (1,63,64,65,1000,999):
            result = measure_disk(h,count)
            self.assertEqual(result['events'][-1]['frame'],count)
            self.assertEqual(result['events'][-1]['steps'],64)
            self.assertLessEqual(result['end'],0xde00)

    def test_invalid_lengths(self):
        for count in (0,-1,16321,1.5):
            with self.assertRaises(ValueError): progress.build(count)

    def test_pipeline_changes_only_bar_and_publication_cost(self):
        states,cells,fap1,ticks = source(4,constant_attribute_borders=True)
        raw,_ = pack(fap1,stored_guards=False)
        tables,mapping,_ = frames(cells)
        r = Reader(raw); read_header(r,magic=b'FAP3')
        options = dict(bulk=True,stored_guards=False,zero_copy=True,skip_noop_runs=True,
            constant_attribute_borders=True,skip_black_borders=True)
        old = Harness(ring(raw,509,True),tables,mapping,len(states),**options)
        new = Harness(ring(raw,509,True),tables,mapping,len(states),progress_frames=len(states),**options)
        self.assertEqual(new.progress_init_result['tstates'],4298)
        for h in (old,new): h.consume_header(raw[:r.pos])
        for i,state in enumerate(states):
            before,after = old.prepare(),new.prepare()
            self.assertEqual(before,after)
            before,after = old.publish(),new.publish()
            expected_ticks = progress.expected_tick_tstates(i*16,(i+1)*16)
            self.assertEqual(after['tstates']-before['tstates'],27+expected_ticks)
            self.assertEqual(after['stages']['packet']-before['stages']['packet'],27)
            self.assertEqual(after['stages']['progress'],expected_ticks)
            for h in (old,new): h.drain_six(ticks[i*6:i*6+6])
            target = 7 if i%2 == 0 else 5
            new.expected_screens[target] = display_screen(state.tobytes(),black_borders=True)
            for bank in (5,7):
                new.expected_screens[bank] = progress.reference_screen(new.expected_screens[bank],i+1,len(states))
                self.assertEqual(bytes(new.cpu.banks[bank][:6912]),new.expected_screens[bank])
            self.assertEqual(new.cpu.banks[5][0x2400:0x3300],old.cpu.banks[5][0x2400:0x3300])
            self.assertEqual(new.cpu.ay,old.cpu.ay)

    def test_real_ay_irq_at_every_progress_instruction(self):
        states,cells,fap1,_ = source(1,constant_attribute_borders=True)
        raw,_ = pack(fap1,stored_guards=False)
        tables,mapping,_ = frames(cells)
        h = Harness(ring(raw),tables,mapping,1,bulk=True,stored_guards=False,zero_copy=True,
            constant_attribute_borders=True,skip_black_borders=True,progress_frames=128)
        names = ('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_b',
            'alt_c','alt_d','alt_e','alt_h','alt_l','alt_z','alt_carry','port_7ffd','sp')
        calls = 0
        def interrupt(cpu):
            nonlocal calls
            cpu.guarding = False
            cpu.write8(h.audio['audio_enabled'],1)
            word(cpu,h.audio['audio_remaining'],65535)
            index = cpu.read8(h.audio['audio_read_index'])
            slot = ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
            cpu.write8(slot,1); cpu.write8(slot+1,8); cpu.write8(slot+2,calls & 15)
            cpu.write8(h.audio['audio_write_index'],(index+1) & 31)
            before = {name:getattr(cpu,name) for name in names}
            start,pc = cpu.tstates,cpu.pc
            cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != pc:
                self.assertNotEqual(cpu.pc,h.audio['fatal']); cpu.step()
            self.assertEqual(before,{name:getattr(cpu,name) for name in names})
            self.assertEqual(cpu.ay[8],calls & 15)
            self.assertEqual(word(cpu,h.audio['audio_underruns']),0)
            calls += 1; cpu.guarding = True
            return cpu.tstates-start
        # Includes repeated LDIR in reset, both nibbles, idle, end and post-EOF.
        h.execute(h.progress['reset'],interrupt=interrupt)
        previous = {bank:bytes(h.cpu.banks[bank][:6912]) for bank in (5,7)}
        for index in range(129):
            result = h.execute(h.p['publish_bridge'],interrupt=interrupt)
            before,after = min(64,index//2),min(64,(index+1)//2)
            self.assertEqual(result['stages']['progress'],progress.expected_tick_tstates(before,after))
            for bank in (5,7):
                self.assertEqual(bytes(h.cpu.banks[bank][:6912]),
                    progress.reference_screen(previous[bank],index+1,128))
        self.assertGreater(calls,2000)


if __name__ == '__main__': unittest.main()
