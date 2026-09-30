"""Reject streams that could execute the motion code reused by literal bridges."""
import struct
import unittest
from borrowed_literals import validate_video


class ContractTests(unittest.TestCase):
    def packet(self):
        body=bytearray(288);body[:5]=struct.pack('<BHH',0,8,0)
        return bytearray(struct.pack('<H',len(body))+body)

    def test_supported_packet(self):
        rows=validate_video(self.packet())
        self.assertEqual((len(rows),rows[0]['prefix_bytes'],rows[0]['literal_bytes']),(1,288,0))

    def test_motion_and_spatial_commands_rejected(self):
        for vector in (1,40,81,82,83,84,89,255):
            with self.subTest(vector=vector):
                blob=self.packet();blob[2+8+100]=vector
                with self.assertRaises(ValueError):validate_video(blob)

    def test_motion_cache_rejected(self):
        blob=self.packet();blob[2]=128
        with self.assertRaises(ValueError):validate_video(blob)

    def test_incomplete_body_rejected(self):
        with self.assertRaises(ValueError):validate_video(self.packet()[:-1])

    def test_prefix_overflow_rejected(self):
        blob=self.packet();struct.pack_into('<H',blob,3,65535)
        with self.assertRaises(ValueError):validate_video(blob)


if __name__=='__main__':unittest.main()
