"""Demand-sized ZX0 work: contiguous copies, retained history, EOF and background work."""
import unittest
from unittest.mock import patch

from benchmark_context_huffman import word
from benchmark_direct_slot_input import Harness as Producer
from benchmark_partial_slots import install_copy_guard
import test_direct_slot_input as input_tests
import test_partial_slot_consumption as partial_tests
from test_slot_queue import QueueHarness


def fixture(blocks, first=53):
    with patch.object(input_tests,'Harness',lambda *a,**kw:Producer(*a,**kw,inline_literals=True)):
        return input_tests.fixture(blocks,first)


class DemandTests(unittest.TestCase):
    def test_one_copy_per_requested_prefix_without_releasing_history(self):
        block=partial_tests.long_block();q=QueueHarness(fixture([block]),1,demand_decode=True)
        guard=install_copy_guard(q);at=0
        for count in (2,2000,1,3000,3189):
            copies=lambda:sum(n for (pc,_),n in q.histogram.items() if pc==q.q['bridge']['copy'])
            before=copies()
            self.assertEqual(q.take(count),block[1][at:at+count]);at+=count
            self.assertEqual(copies()-before,1)
            if at<len(block[1]):
                self.assertEqual(q.cpu.read8(q.q['count']),0)
                self.assertEqual(q.cpu.read8(q.q['phase']),2)
                self.assertEqual(word(q.cpu,q.q['blocks_left']),1)
                self.assertEqual(word(q.cpu,q.q['position']),at)
        self.assertEqual(guard['checked_copy_bytes'],8192)
        self.assertEqual(word(q.cpu,q.q['blocks_left']),0)
        self.assertEqual(q.cpu.read8(q.q['count']),0)
        self.assertEqual(word(q.cpu,q.q['position']),0)
        self.assertEqual(bytes(q.cpu.banks[0][8192:]),block[1])
        with self.assertRaises(AssertionError):q.take(1)

    def test_background_completion_and_cross_slot_requests(self):
        def factory(*args,**kw):return QueueHarness(*args,**kw,demand_decode=True)
        with patch.object(partial_tests,'QueueHarness',factory),patch.object(partial_tests,'fixture',fixture):
            partial_tests.PartialSlotTests().test_prefix_returns_before_eof_and_history_is_retained()
            partial_tests.PartialSlotTests().test_crossing_active_and_completed_slots_matches_full_queue()

    def test_full_slot_retained_path_and_release_cost(self):
        costs=[]
        for demand in (False,True):
            q=QueueHarness(fixture([input_tests.literal(700)]),1,demand_decode=demand)
            q.call(q.q['prefill']);q.take(10);retained=q.calls[-1][1]
            q.take(690);costs.append((retained,q.calls[-1][1]))
        self.assertEqual(costs[1][0]-costs[0][0],0)
        self.assertEqual(costs[1][1]-costs[0][1],27)

    def test_large_pending_clamps_before_absolute_address_wrap(self):
        q=QueueHarness(fixture([partial_tests.long_block()]),1,demand_decode=True)
        for position,pending,wanted in ((0,1,1),(1,8191,8192),(5000,65535,8192),(255,1000,1255)):
            c=q.cpu;word(c,q.q['position'],position);word(c,q.q['pending'],pending)
            word(c,q.h.decoder.labels['block_length'],8192)
            c.pc=q.q['demand']
            while c.pc!=q.q['demand_target']:c.step()
            self.assertEqual(c.hl(),wanted)

    def test_demand_helper_absolute_instruction_cost(self):
        for pending,stop,cost in ((10,'take_available',261),(2000,'run_decode',266)):
            q=QueueHarness(fixture([partial_tests.long_block()]),1,demand_decode=True)
            q.take(2)  # actual decoder has produced 256, of which two consumed
            c=q.cpu;word(c,q.q['pending'],pending);c.pc=q.q['demand']
            start=c.tstates
            while c.pc!=q.q[stop]:c.step()
            self.assertEqual(c.tstates-start,cost)


if __name__=='__main__':unittest.main()
