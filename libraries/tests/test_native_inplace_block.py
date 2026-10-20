"""Exercise the live overlap guard separately from ordinary match history."""
from pathlib import Path
import sys
import unittest

LIBRARIES = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(LIBRARIES/'zx0/src'), str(LIBRARIES/'lzsa/src')]

from native_inplace_block import execute, host_trace
from native_block import execute as disjoint_execute


class NativeInplaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from zx0.maximum import build as zx_build
        from lzsa.hybrid import build as lz_build
        cls.profiles = dict(zx0=zx_build(prefix_cap=228, shared_prefixes=True),
                            lzsa2=lz_build(profile='fast'))

    def cases(self):
        from zx0.tokens import Token, encode as zx_encode
        from lzsa import encode as lz_encode
        raw = b'A'*8192
        yield 'zx0', zx_encode(raw, [Token(0,1), Token(1,len(raw)-1,1)]), raw
        yield 'lzsa2', lz_encode(raw, [(1,len(raw)-1,1)]), raw

    def test_minimum_safe_overlap_and_unsafe_one_byte_boundary(self):
        for codec, payload, raw in self.cases():
            with self.subTest(codec=codec):
                proof = host_trace(codec, payload, raw)
                self.assertGreater(proof['minimum_input_start'], 0)
                result = execute(self.profiles[codec], payload, raw, codec=codec)
                self.assertTrue(result['host_read_order_exact'])
                self.assertGreater(result['actual_overlap_bytes'], 0)
                self.assertGreater(result['history_reads'], 0)
                with self.assertRaisesRegex(AssertionError, 'overwrites unread input'):
                    execute(self.profiles[codec], payload, raw, codec=codec,
                            source=0xc000+proof['minimum_input_start']-1)

    def test_tstates_equal_disjoint_plain_and_irq(self):
        for codec, payload, raw in self.cases():
            for interrupts in (False, True):
                with self.subTest(codec=codec, interrupts=interrupts):
                    result = execute(self.profiles[codec], payload, raw, codec=codec,
                                     interrupts=interrupts)
                    reference = disjoint_execute(self.profiles[codec], payload, raw,
                                                 interrupts=interrupts)
                    self.assertEqual(result['tstates'], reference['tstates'])
                    self.assertEqual(result['stack_bytes'], reference['stack_bytes'])
                    self.assertTrue(result['raw_abi_exact'])

    def test_literal_only_same_arena_and_single_nibble_eof(self):
        from zx0.tokens import Token, encode as zx_encode
        from lzsa import encode as lz_encode
        raw = bytes(range(127))
        for codec, payload, expected in (
            ('zx0', zx_encode(raw, [Token(0,len(raw))]), raw),
            ('lzsa2', lz_encode(raw, []), raw),
            ('lzsa2', bytes.fromhex('e7 f0 e8'), b''),
            ('lzsa2', bytes.fromhex('ef 41 f0 e8'), b'A')):
            with self.subTest(codec=codec, output=len(expected)):
                result = execute(self.profiles[codec], payload, expected, codec=codec)
                self.assertTrue(result['host_read_order_exact'])
                self.assertEqual(result['host_minimum_input_start'], 0)
                self.assertEqual(result['actual_overlap_bytes'], len(expected))

    def test_service_code_and_stack_overlap_rejected(self):
        codec, payload, raw = next(self.cases())
        for source, output in ((0x8000, 0x8000), (0xbfee, 0xbfe0)):
            with self.subTest(source=source, output=output):
                with self.assertRaises(AssertionError):
                    execute(self.profiles[codec], payload, raw, codec=codec,
                            source=source, output=output)

    def test_live_parser_eof_and_code_write_guards(self):
        payload = bytes.fromhex('e7 f0 e8')
        probes = (
            # Consume the three valid bytes, then fetch past exact EOF.
            (bytes.fromhex('7e237e237e237ec9'), 'EOF overread'),
            # An undeclared self-modification must fail at the write itself.
            (bytes.fromhex('320080c9'), 'write outside stack/output'),
        )
        for blob, message in probes:
            profile = ([(0x8000, blob)], {'start':0x8000}, {'entry':'start'})
            with self.subTest(message=message):
                with self.assertRaisesRegex(AssertionError, message):
                    execute(profile, payload, b'', codec='lzsa2')


if __name__ == '__main__':
    unittest.main()
