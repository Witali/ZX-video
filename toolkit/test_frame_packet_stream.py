import unittest

from cell_audio_stream import pack as audio
from frame_packet_stream import pack, unpack
from probe_sparse_motion_cache import pack as cache
from raw_attribute_stream import pack as attributes
from test_frame_output_pipeline import fixture
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header


class FramePacketStreamTests(unittest.TestCase):
    def test_roundtrip_and_inconsistent_lengths(self):
        states, cells, _ = fixture(3)
        cells, _ = attributes(cells, states, [True, False, True])
        source, _ = cache(audio(cells, b'\0'*18), states, 32, 4)
        encoded, rows = pack(source)
        self.assertEqual(unpack(encoded), source)
        self.assertEqual(len(encoded)-len(source), -4*len(states))
        r = Reader(encoded); read_header(r, magic=b'FAP1')
        # Six empty AY ticks precede the first header.
        first = r.pos+6
        bad_flag = bytearray(encoded); bad_flag[first] |= 8
        bad_length = bytearray(encoded); bad_length[first+5] ^= 1
        for bad in (encoded[:-1], encoded+b'!', bad_flag, bad_length):
            with self.assertRaises(ValueError): unpack(bad)


if __name__ == '__main__':
    unittest.main()
