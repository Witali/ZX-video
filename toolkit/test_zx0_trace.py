"""Optional token tracing preserves the existing ZX0 reference output."""
import unittest

from test_blocked_stream import EMPTY_COMPRESSED, EMPTY_DECODED
from zx0_codec import decompress, emit_decoder
from build_zxv_trd import MiniAssembler
from benchmark_zx0_storage import decode_block


class TraceTests(unittest.TestCase):
    def test_layout_preserves_cycles_for_identical_stream(self):
        a = MiniAssembler(0x8000)
        emit_decoder(a, 'turbo')
        code = a.resolve()
        self.assertEqual(decode_block(code, EMPTY_COMPRESSED, EMPTY_DECODED),
                         decode_block(code, EMPTY_COMPRESSED, EMPTY_DECODED, layout='bank16'))
        with self.assertRaises(ValueError):
            decode_block(code, EMPTY_COMPRESSED, EMPTY_DECODED, layout='unknown')

    def test_match_and_literal_callbacks_partition_output(self):
        tokens = []
        output = decompress(EMPTY_COMPRESSED, limit=len(EMPTY_DECODED),
            on_match=lambda pos, offset, length: tokens.append((pos, length, offset)),
            on_literals=lambda pos, length: tokens.append((pos, length, 0)))
        self.assertEqual(output, EMPTY_DECODED)
        self.assertEqual(output, decompress(EMPTY_COMPRESSED, limit=len(output)))
        cursor = 0
        for position, length, offset in tokens:
            self.assertEqual(position, cursor)
            if offset:
                self.assertLessEqual(offset, position)
                for i in range(length):
                    self.assertEqual(output[position+i], output[position+i-offset])
            cursor += length
        self.assertEqual(cursor, len(output))
        self.assertTrue(any(t[2] for t in tokens))
        self.assertTrue(any(not t[2] for t in tokens))

    def test_truncated_stream_still_rejected_with_callbacks(self):
        with self.assertRaises(ValueError):
            decompress(EMPTY_COMPRESSED[:-1], limit=len(EMPTY_DECODED), on_match=lambda *args: None)


if __name__ == '__main__':
    unittest.main()
