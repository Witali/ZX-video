import unittest

from benchmark_context_huffman import word
from test_direct_slot_input import fixture, literal
from test_slot_queue import QueueHarness
from zx0_speed import Token, encode


def long_block():
    raw = bytes((i*37+9) % 251 for i in range(8192))
    tokens = [Token(0, 256)]+[Token(i, min(64, len(raw)-i), 251)
                             for i in range(256, len(raw), 64)]
    return encode(raw, tokens), raw


class PartialSlotTests(unittest.TestCase):
    def test_prefix_returns_before_eof_and_history_is_retained(self):
        block = long_block()
        q = QueueHarness(fixture([block]), 1, partial_consumption=True)
        c = q.cpu
        self.assertEqual(q.take(2), block[1][:2])
        self.assertEqual(c.read8(q.q['phase']), 2)
        self.assertEqual(c.read8(q.q['count']), 0)
        self.assertEqual(word(c, q.q['position']), 2)
        self.assertEqual(word(c, q.q['blocks_left']), 1)
        self.assertEqual(word(c, q.h.decoder.labels['slice_output']), 0xe100)
        saved = bytes(c.banks[0][8192:8448])
        before = c.tstates
        self.assertEqual(q.take(254), block[1][2:256])
        self.assertLess(c.tstates-before, 6000)
        self.assertEqual(bytes(c.banks[0][8192:8448]), saved)
        self.assertEqual(word(c, q.q['position']), 256)
        self.assertEqual(c.read8(q.q['count']), 0)
        self.assertEqual(q.take(1), block[1][256:257])
        self.assertGreater(word(c, q.h.decoder.labels['slice_output']), 0xe100)
        self.assertEqual(c.read8(q.q['count']), 0)
        q.call(q.q['prefill'])
        self.assertEqual(c.read8(q.q['count']), 1)
        self.assertEqual(word(c, q.q['position']), 257)
        at = 257
        while at < len(block[1]):
            n = min(777, len(block[1])-at)
            self.assertEqual(q.take(n), block[1][at:at+n])
            at += n
        self.assertEqual(c.read8(q.q['count']), 0)
        self.assertEqual(word(c, q.q['blocks_left']), 0)
        self.assertEqual(word(c, q.q['position']), 0)
        self.assertEqual(bytes(c.banks[0][8192:]), block[1])
        with self.assertRaises(AssertionError):
            q.take(1)

    def test_crossing_active_and_completed_slots_matches_full_queue(self):
        blocks = [long_block(), literal(5), long_block(), literal(2100), literal(1), long_block()]
        expected = b''.join(raw for _, raw in blocks)
        for background in (False, True):
            q = QueueHarness(fixture(blocks, 63), len(blocks), partial_consumption=True)
            q.cpu.write8(0x97ca, 0x1f)
            out = bytearray()
            sizes = (1, 2, 255, 256, 257, 1000, 3999)
            i = 0
            while len(out) < len(expected):
                if background:
                    q.call(q.q['step'])
                n = min(sizes[i % len(sizes)], len(expected)-len(out))
                out += q.take(n)
                self.assertEqual(q.cpu.port_7ffd & 8, 8)
                i += 1
            self.assertEqual(bytes(out), expected)
            self.assertEqual([r['sector'] for r in q.cpu.reads], q.h.positions)
            self.assertEqual(q.cpu.read8(q.q['count']), 0)
            self.assertEqual(word(q.cpu, q.q['blocks_left']), 0)

    def test_completed_path_cpu_delta_is_only_release_check(self):
        costs = []
        for partial in (False, True):
            q = QueueHarness(fixture([literal(700)]), 1, partial_consumption=partial)
            q.call(q.q['prefill'])
            self.assertEqual(q.take(10), bytes(range(10)))
            retained = q.calls[-1][1]
            q.take(690)
            costs.append((retained, q.calls[-1][1]))
        self.assertEqual(costs[1][0]-costs[0][0], 0)
        self.assertEqual(costs[1][1]-costs[0][1], 27)


if __name__ == '__main__':
    unittest.main()
