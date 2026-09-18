import unittest

import probe_mask_dictionary as codec
from probe_hybrid_tiles import read_header
from probe_motion_entropy import Reader
import test_hybrid_tiles as fixture


class MaskDictionaryTests(unittest.TestCase):
    def test_inverse_escapes_and_malformed_data(self):
        source, _, _ = fixture.HybridTileTests().mixed()
        for count in (1, 16, 255):
            table = codec.train(source, count)
            data, stats = codec.encode(source, table)
            self.assertEqual(codec.decode(data), source)
            self.assertEqual(stats['tiles'], 3*192)
            if count == 1:
                self.assertGreater(stats['escapes'], 0)
            for bad in (data[:-1], data+b'!', b'bad!'+data[4:]):
                with self.assertRaises(ValueError):
                    codec.decode(bad)
        # An index between the last entry and FF is invalid, not an escape.
        data, _ = codec.encode(source, codec.train(source, 1))
        r = Reader(b'FHT1'+data[4:]); read_header(r)
        size = r.u16(); r.take(2*size)
        r.u16(); vl = r.u16(); r.u16(); r.take(5+vl)
        bad = bytearray(data); bad[r.pos] = 1
        with self.assertRaises(ValueError):
            codec.decode(bytes(bad))
        for table in ([], [b'\0'], [b'\0\0', b'\0\0']):
            with self.assertRaises(ValueError):
                codec.encode(source, table)


if __name__ == '__main__':
    unittest.main()
