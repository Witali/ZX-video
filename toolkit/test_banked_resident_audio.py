"""Two-bank AY boundaries, FIFO backpressure, caller state, IRQs and T-states."""
import unittest

import ay_huffman_stream as wire
import banked_resident_audio as banked
from benchmark_resident_audio_z80 import Harness,word
from test_resident_audio_z80 import record


def records(count):
    return [record([2047,0,64,257,3,896][i%6],lambda r:(r*19+i*7)&255) for i in range(count)]


class BankedAudioTests(unittest.TestCase):
    def test_boundaries_backpressure_and_exact_registers(self):
        ticks=records(100);initial=bytes(range(11))
        for split in (1,31,32,97):
            data=banked.encode(ticks,initial,split=split)
            self.assertEqual(banked.decode(data),(initial,ticks))
            h=Harness(data,paging=True,batch=31)
            while h.consumed<len(ticks):
                h.fill_wrapped()
                if h.cpu.published>h.consumed:h.consume()
            h.finish()
            self.assertEqual(word(h.cpu,h.audio['audio_underruns']),0)

    def test_real_interrupts_across_switch_preserve_caller(self):
        ticks=records(41)
        h=Harness(banked.encode(ticks,bytes(range(11)),split=7),paging=True,batch=31)
        while h.cpu.published<len(ticks):h.fill_wrapped(h.interrupt)
        while h.consumed<len(ticks):h.consume()
        h.finish()
        self.assertGreater(h.cpu.irq_count,1000)

    def test_bridge_cycle_deltas(self):
        ticks=records(64);initial=bytes(11)
        h=Harness(banked.encode(ticks,initial,split=32),paging=True,batch=31)
        first,second=banked.segments(banked.encode(ticks,initial,split=32))
        left=Harness(first,paging=True,batch=31);right=Harness(second,paging=True,batch=31)
        self.assertEqual(h.init_tstates-left.init_tstates,40)
        for _ in range(2):
            elapsed,count=h.fill_wrapped();baseline,n=left.fill_wrapped()
            self.assertEqual((elapsed-baseline,count),(50,n))
            for _ in range(count):h.consume();left.consume()
        elapsed,count=h.fill_wrapped();baseline,n=right.fill_wrapped()
        self.assertEqual((elapsed-baseline,count),(209,n))
        for _ in range(count):h.consume();right.consume()
        elapsed,count=h.fill_wrapped();baseline,n=right.fill_wrapped()
        self.assertEqual((elapsed-baseline,count),(50,n))
        for _ in range(count):h.consume();right.consume()
        self.assertEqual(h.fill_wrapped()[0]-right.fill_wrapped()[0],80)
        h.finish();left.finish();right.finish()

    def test_discontinuous_initial_state_rejected(self):
        data=banked.encode(records(8),bytes(11))
        damaged=bytearray(data);one,two=banked.segments(data)
        damaged[12+len(one)+12]^=1
        with self.assertRaisesRegex(ValueError,'discontinuous'):banked.decode(bytes(damaged))

    def test_helper_must_stay_mapped_when_audio_bank_changes(self):
        h=Harness(banked.encode(records(8),bytes(11)),paging=True)
        for address in (0x3fff,0xbff0,0xdb80):
            with self.assertRaisesRegex(ValueError,'fixed RAM'):
                banked.hooks(address,h.build,page=0x9780)


if __name__=='__main__':unittest.main()
