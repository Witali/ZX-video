"""Metadata inverse, short final group, runs/presence padding and corruption."""
import struct
import unittest

from probe_motion_metadata import transform, restore, encode, decode, split
from probe_motion_entropy import encode as fpe_encode, groups, huffman_lengths


class MetadataTests(unittest.TestCase):
    def test_complete_container_and_short_final_group(self):
        symbols = bytes(p ^ c for p in range(4) for c in range(4))
        original = b'FPR1'+symbols+b'FMO1\x08FMR1'+struct.pack('<BBIbb', 8, 1, 3, 0, 0)
        for count in (2, 1):
            original += struct.pack('<H', count)+bytes(192*count)
            original += b'\x80'+bytes(480*count-1)+b'\x01'
        header, parsed = groups(original)
        source, _ = fpe_encode(header, parsed, 255, huffman_lengths({1: 2}))
        header, parsed = split(source)
        for vm in (0, 1, 2, 6):
            for mm in range(6):
                data = encode(header, parsed, vm, mm)
                self.assertEqual(decode(data), source)
                for bad in (data[:-1], data+b'\0'):
                    with self.assertRaises(ValueError):
                        decode(bad)

    def test_every_field_mode_and_group_size(self):
        for n in (1, 3, 8):
            for width in (192, 480):
                data = (bytes([0]*70+[255]*71+[0, 1, 2, 3, 0, 128, 64])*100)[:n*width]
                for mode in range(7 if width == 192 else 6):
                    encoded = transform(data, width, mode)
                    self.assertEqual(restore(encoded, n, width, mode), data)
                    with self.assertRaises(ValueError):
                        restore(encoded+b'\0', n, width, mode)
                    with self.assertRaises(ValueError):
                        restore(encoded[:-1], n, width, mode)

    def test_rejects_bad_run_and_presence_padding(self):
        with self.assertRaises(ValueError):
            restore(bytes([192]), 1, 192, 5)
        with self.assertRaises(ValueError):
            restore(bytes([127])*4, 1, 192, 5)
        # Three frames of masks have 180 presence bytes and 23 upper bytes.
        with self.assertRaises(ValueError):
            restore(bytes(22)+b'\x01', 3, 480, 4)


if __name__ == '__main__':
    unittest.main()
