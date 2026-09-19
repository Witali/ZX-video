import struct
import unittest

from bulk_frame_stream import pack,unpack,read_packet
from test_frame_stream_z80 import source
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header


class BulkFrameStreamTests(unittest.TestCase):
    def test_roundtrip_and_bounds(self):
        states, _, fap1, _ = source(4)
        raw, rows = pack(fap1)
        self.assertEqual(unpack(raw),fap1)
        self.assertEqual(len(raw)-len(fap1),2*len(states))
        r = Reader(raw); read_header(r,magic=b'FAP2')
        for row in rows:
            _, detail = read_packet(r)
            self.assertEqual(len(detail['payload']),row['payload_bytes'])
            self.assertEqual(detail['coded_offset'],row['coded_offset'])
            self.assertEqual(detail['literal_offset'],row['literal_offset'])
        r.end()
        first = rows[0]
        bads = []
        for value in (0,295,4705,65535):
            bad = bytearray(raw); struct.pack_into('<H',bad,first['offset'],value); bads.append(bad)
        for offset in (first['coded_offset']+first['coded_bytes'],first['payload_bytes']-1):
            bad = bytearray(raw); bad[first['offset']+2+offset] = 1; bads.append(bad)
        for bad in (*bads,raw[:-1],raw+b'!'):
            with self.assertRaises(ValueError): unpack(bad)


if __name__ == '__main__': unittest.main()
