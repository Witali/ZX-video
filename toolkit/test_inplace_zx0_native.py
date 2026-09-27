"""Compare native ZX0 memory accesses with exact host overlap boundaries."""
import unittest
from benchmark_inplace_zx0 import native
from inplace_zx0 import trace, layout
from zx0_speed import Token, encode


class InplaceNativeTests(unittest.TestCase):
    def test_instruction_trace_and_exact_unsafe_boundary(self):
        raw = bytes(i%251 for i in range(15872))
        packed = encode(raw, [Token(0, 251), Token(251, len(raw)-251, 251)])
        _, report = trace(packed, limit=len(raw)); minimum = report['minimum_input_start']
        reference = native(packed, raw, 0, shared=False)
        self.assertEqual(reference['minimum_input_start'], minimum)
        self.assertEqual(reference['write_input_cursors_sha256'], report['write_input_cursors_sha256'])
        self.assertEqual(native(packed, raw, minimum), reference)
        with self.assertRaisesRegex(RuntimeError, 'overwrites unread input'):
            native(packed, raw, minimum-1)
        for offset in (0, 252, 253, 254, 255):
            placement = layout(len(packed), len(raw), minimum, offset)
            for slot in (0, 1, 3):
                self.assertEqual(native(packed, raw, placement['input_start'], slot=slot), reference)

    def test_literal_only_and_pointer_wrap(self):
        for size in (1, 256, 8192, 15872):
            raw = bytes((i*71+29)&255 for i in range(size))
            packed = encode(raw, [Token(0, size)])
            _, report = trace(packed, limit=size)
            a = native(packed, raw, 16384-len(packed))
            self.assertEqual(a, native(packed, raw, 0, shared=False))
            self.assertEqual(a['minimum_input_start'], report['minimum_input_start'])


if __name__ == '__main__': unittest.main()
