"""Check one-ready-slot admission independently, including all-loaded bypass."""
import itertools
import unittest
from z80 import Z80Machine
import resumable_lzsa2
import streaming_slot_queue
from pipelined_frame_z80 import PAGE


def fixture(early):
    _,z,_=resumable_lzsa2.build(core=0x8d74,core_limit=0x8e80,streaming=True,direct_header=True)
    p=dict(begin=0x7000,step=0x7010,page_slot=0x7020)
    regions,q,_=streaming_slot_queue.build(z,p,8,demand_decode=True,defer_while_buffered=True,early_prefix=early)
    m=Z80Machine()
    for at,data in regions:m.set_memory_block(at,data)
    m.set_memory_block(PAGE,b'\xc9')
    return m,z,p,q


class EarlyPrefixTests(unittest.TestCase):
    def test_count_admission_and_exact_cost(self):
        for early,count in itertools.product((False,True),range(4)):
            m,z,p,q=fixture(early);m.memory[q['count']]=count;m.pc=q['prefix_admission']
            m.set_breakpoint(q['worked']);m.set_breakpoint(q['begin_ready']);m.ticks_to_stop=10000
            while m.pc not in (q['worked'],q['begin_ready']):
                self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
            self.assertEqual(m.pc==q['begin_ready'],count<=(1 if early else 0))
            self.assertEqual(10000-m.ticks_to_stop,30 if early else 27)

    def test_complete_input_and_unavailable_prefix(self):
        for early,count,complete,available in itertools.product((False,True),range(4),(0,1),(0,1)):
            m,z,p,q=fixture(early)
            m.set_memory_block(p['step'],bytes([0x3e,available,0xc9]))
            m.memory[q['phase']]=1;m.memory[q['count']]=count;m.memory[z['all_loaded']]=complete
            m.pc=q['step'];m.sp=0x9df0
            m.set_breakpoint(q['worked']);m.set_breakpoint(q['begin_ready']);m.ticks_to_stop=10000
            while m.pc not in (q['worked'],q['begin_ready']):
                self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
            self.assertEqual(m.pc==q['begin_ready'],bool(available and (complete or count<=(1 if early else 0))))
            self.assertEqual(m.sp,0x9df0)
            self.assertEqual(m.memory[q['count']],count)


if __name__=='__main__':unittest.main()
