"""Exercise exact overlap boundaries, EOF bytes and shared-sector placement."""
import unittest
from inplace_zx0 import trace, layout, OverlapError
from zx0_speed import Token, encode


class InplaceZX0Tests(unittest.TestCase):
    def check(self, raw, tokens):
        payload = encode(raw, tokens)
        result, report = trace(payload, limit=len(raw))
        self.assertEqual(result, raw)
        safe = report['minimum_input_start']
        self.assertGreaterEqual(safe, 0)
        result, replay = trace(payload, limit=len(raw), input_start=safe,
                               bank_bytes=report['minimum_footprint'])
        self.assertEqual(result, raw)
        self.assertEqual(replay['write_input_cursors_sha256'], report['write_input_cursors_sha256'])
        if safe:
            with self.assertRaises(OverlapError):
                trace(payload, limit=len(raw), input_start=safe-1,
                      bank_bytes=report['minimum_footprint'])
        for bad in (payload[:-1], payload+b'!'):
            with self.assertRaises(ValueError): trace(bad, limit=len(raw))
        return payload, report

    def test_literal_and_match_boundaries(self):
        for size in (1, 2, 127, 128, 255, 256, 257, 8192, 15872, 16384):
            raw = bytes(i%251 for i in range(size))
            self.check(raw, [Token(0, size)])
            if size > 251:
                self.check(raw, [Token(0, 251), Token(251, size-251, 251)])

    def test_compressible_prefix_then_literal_tail_and_new_offset(self):
        seed = bytes(range(256))*2
        raw = seed+seed+bytes((i*71+29)&255 for i in range(4096))
        self.check(raw, [Token(0, 512), Token(512, 512, 512), Token(1024, 4096)])
        self.check(b'abcabcab', [Token(0, 3), Token(3, 3, 3), Token(6, 2, 3)])

    def test_eof_and_full_bank_output(self):
        raw = b'A'*16384
        payload, report = self.check(raw, [Token(0, 1), Token(1, 16383, 1)])
        self.assertGreater(report['minimum_footprint'], len(raw))
        self.assertGreater(report['input_bytes_after_last_write'], 0)
        self.assertFalse(layout(len(payload), len(raw), report['minimum_input_start'], 0)['exact_end_fits'])

    def test_every_header_alignment_and_shared_tail(self):
        raw = bytes(i%251 for i in range(15872))
        payload, report = self.check(raw, [Token(0, 251), Token(251, len(raw)-251, 251)])
        for offset in range(256):
            plan = layout(len(payload), len(raw), report['minimum_input_start'], offset)
            self.assertTrue(plan['sector_aligned_fits'])
            self.assertEqual(plan['sector_span_bytes']%256, 0)
            self.assertEqual(plan['input_start']%256, (offset+4)%256)
            self.assertEqual(plan['input_start']+len(payload)+plan['trailing_bytes'], 16384)
            self.assertEqual(trace(payload, limit=len(raw), input_start=plan['input_start'])[0], raw)
        with self.assertRaises(ValueError): trace(payload, limit=len(raw), input_start=-1)


if __name__ == '__main__': unittest.main()
