"""Independent bitstream checks, including corrupt/truncated frame boundaries."""
from pathlib import Path
import json
import struct
import unittest

from lpc2_stream import read_stream

HERE = Path(__file__).resolve().parent


class StreamTests(unittest.TestCase):
    def test_complete_baseline_and_quality_candidates(self):
        for folder,hop,count in (('lpc-detail/baseline',160,1200),('lpc-detail/detail',80,2400),
                                 ('ym2149-preview/lpc',160,1200)):
            with self.subTest(folder=folder):
                directory = HERE/folder
                analysis = json.loads((directory/'lpc2-analysis.json').read_bytes())
                actual = read_stream((directory/'reference.lp2').read_bytes())
                self.assertEqual((actual['hop'],actual['frames'],actual['samples']),(hop,count,192000))
                self.assertEqual(actual['quantized_frames_sha256'],analysis['quantized_frames_sha256'])

    def test_reject_truncated_trailing_and_malformed_streams(self):
        blob = (HERE/'lpc-probe/reference.lp2').read_bytes()
        for data in (blob[:35],blob[:-1],blob+b'\0'):
            with self.assertRaises(ValueError): read_stream(data)
        wrong_count = bytearray(blob)
        struct.pack_into('<I',wrong_count,12,1201)
        with self.assertRaises(ValueError): read_stream(wrong_count)
        # The first frame cannot repeat coefficients that were never supplied.
        repeat = bytearray(37)
        struct.pack_into('<4sBBHHHIIIffI',repeat,0,b'LPC2',1,10,8000,160,256,1,160,8,.85,.38,0)
        repeat[36] = 0x81  # energy=1, mode=noise, repeat=1
        with self.assertRaises(ValueError): read_stream(repeat)


if __name__ == '__main__':
    unittest.main()
