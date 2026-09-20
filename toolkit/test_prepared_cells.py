import unittest
import numpy as np

from prepared_cells_harness import Harness
import prepared_cells_z80 as machine
from benchmark_compact_screen import STACK,STOP
from benchmark_context_huffman import word
from build_zxv_trd import MiniAssembler
import ay_interrupt
import playback_schedule


def fixtures():
    rng=np.random.default_rng(4221)
    previous=[bytearray(3072)+bytearray([1]*768) for _ in range(2)]
    for i in range(8):
        active=bytes([255]*72) if i<2 else (bytes(72) if i>=6 else bytes((j+72*(i-2))%256 for j in range(72)))
        mask=bytes([255]*4)+active+bytes([255]*4); state=previous[i%2]
        for band in range(18):
            for col in range(32):
                if active[band*4+col//8]&(128>>(col%8)):
                    for row in range(4): state[(12+band*4+row)*32+col]=int(rng.integers(0,256))
        state[3168:3744]=rng.integers(0,128,576,dtype=np.uint8).tobytes()
        yield bytes(state),mask


class PreparedCellTests(unittest.TestCase):
    def test_dense_sparse_all_mask_bytes_and_empty(self):
        old,new,fast=Harness(baseline=True),Harness(),Harness(unrolled_staging=True)
        for i,(state,mask) in enumerate(fixtures()):
            before=old.run(state,mask,i); after=new.run(state,mask,i)
            self.assertEqual(before['tstates'],after['baseline_tstates'])
            self.assertEqual(new.screens,old.screens)
            fast.run(state,mask,i)
            self.assertEqual(fast.screens,old.screens)

    def test_both_bank_transitions_and_split_mask_attributes_pixels(self):
        # Position the first 90-byte map, a 96-byte attr window, and a
        # 128-byte dense pixel window across each queue-bank boundary.
        frames=list(fixtures())[:2]
        for boundary in (15360,30720):
            for distance in (1,89,90,100,665,666,667,793):
                h=Harness(start=boundary-distance,unrolled_staging=True)
                for i,(state,mask) in enumerate(frames): h.run(state,mask,i)

    def test_wrong_dirty_mask_is_detected(self):
        state,mask=next(fixtures()); h=Harness()
        with self.assertRaisesRegex(AssertionError,'native screen differs'):
            h.run(state,bytes(80),0)

    def test_ay_interrupts_preserve_source_pages_alternate_registers_and_split_windows(self):
        h=Harness(start=15359,unrolled_staging=True); cpu=h.cpu; a=MiniAssembler(0x9400)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a,dos_irq=True,full_rom_clock=True,memory_clock=True,audio_irq=True)
        ay_interrupt.emit_variables(a); a.label('elapsed_fields'); a.word(0); a.label('fatal'); a.emit(0x76)
        self.assertLessEqual(a.pc,machine.PAGE)
        for i,v in enumerate(a.resolve()): cpu.write8(0x9400+i,v)
        cpu.pc=a.labels['setup_clock']; cpu.sp=STACK; cpu.push(STOP)
        while cpu.pc!=STOP: cpu.step()
        cpu.write8(a.labels['audio_enabled'],1)
        registers=('a','b','c','d','e','h','l','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l',
            'ix','z','carry','alt_z','alt_carry','port_7ffd','sp')
        ei_follow={r['address']+1 for r in h.listing if r['instruction']=='EI'}
        calls=0
        def irq(cpu):
            nonlocal calls
            if not cpu.iff1 or cpu.pc in ei_follow: return 0
            cpu.guarding=False
            word(cpu,a.labels['audio_remaining'],65535)
            read=cpu.read8(a.labels['audio_read_index']); slot=ay_interrupt.QUEUE_BASE+read*32
            for j,v in enumerate((1,8,calls&15)): cpu.write8(slot+j,v)
            cpu.write8(a.labels['audio_write_index'],(read+1)&31)
            before={k:getattr(cpu,k) for k in registers}; start=cpu.tstates; pc=cpu.pc
            cpu.push(pc); cpu.pc=0xbdbd; cpu.iff1=False; cpu.tstates+=19
            while cpu.pc!=pc:
                self.assertNotEqual(cpu.pc,a.labels['fatal']); cpu.step()
            self.assertEqual(before,{k:getattr(cpu,k) for k in registers})
            self.assertEqual(cpu.ay[8],calls&15); self.assertEqual(word(cpu,a.labels['audio_underruns']),0)
            calls+=1; cpu.guarding=True
            return cpu.tstates-start
        for i,(state,mask) in enumerate(list(fixtures())[:3]): h.run(state,mask,i,irq)
        self.assertGreater(calls,20000)


if __name__=='__main__': unittest.main()
