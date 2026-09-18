import unittest

from probe_direct_values import encode
from probe_split_metadata import split, join
import test_direct_values as fixture


class SplitMetadataTests(unittest.TestCase):
    def test_full_inverse_short_last_group_and_corruption(self):
        raw, _, prediction, matrices, _ = fixture.DirectValueTests().source()
        data, _ = encode(raw, prediction, matrices[2], 2, [0]*256, [bytes([8]*256)]*2)
        metadata, values = split(data)
        self.assertEqual(join(metadata, values), data)
        self.assertEqual(len(metadata)+len(values), len(data)+10)
        for meta, vals in ((metadata[:-1], values), (metadata+b'!', values),
                           (metadata, values[:-1]), (metadata, values+b'!')):
            with self.assertRaises(ValueError):
                join(meta, vals)
        for bad in (data[:-1], data+b'!', b'XXXX'+data[4:]):
            with self.assertRaises(ValueError):
                split(bad)


if __name__ == '__main__':
    unittest.main()
