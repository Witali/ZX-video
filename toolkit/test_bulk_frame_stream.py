import struct
import unittest

from bulk_frame_stream import pack,unpack,read_packet
from test_frame_stream_z80 import source
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header


class BulkFrameStreamTests(unittest.TestCase):
    def test_fap3_roundtrip_boundaries_and_truncation(self):
        states, _, fap1, _ = source(4)
        raw, rows = pack(fap1,stored_guards=False)
        self.assertEqual(raw[:4],b'FAP3')
        self.assertEqual(unpack(raw),fap1)
        self.assertEqual(len(raw),len(fap1))
        guarded,_ = pack(fap1)
        self.assertEqual(len(guarded)-len(raw),2*len(states))
        r = Reader(raw); read_header(r,magic=b'FAP3')
        for row in rows:
            _,detail = read_packet(r,stored_guards=False)
            self.assertEqual(detail['literal_offset'],row['coded_offset']+row['coded_bytes'])
            self.assertEqual(detail['payload'],raw[row['offset']+2:row['offset']+2+row['payload_bytes']])
        r.end()
        first = rows[0]; bads = []
        for value in (0,293,4704,65535):
            bad = bytearray(raw); struct.pack_into('<H',bad,first['offset'],value); bads.append(bad)
        for bad in (*bads,raw[:-1],raw+b'!',b'FAP9'+raw[4:]):
            with self.assertRaises(ValueError): unpack(bad)

        # Full final-byte reserve is part of the format, independently of
        # the particular film's much smaller maximum packet.
        minimal = bytes(6)+struct.pack('<BHH',0,8,0)+bytes(3+192+8+80)
        for length in (294,4703):
            body = minimal+bytes(length-len(minimal))
            _,detail = read_packet(Reader(struct.pack('<H',length)+body),stored_guards=False)
            self.assertEqual(len(detail['payload']),length)

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
