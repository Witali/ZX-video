import struct
import unittest
from hashlib import sha256

import bank_local_zx0
import disk_layout
import pipelined_frame_z80 as video
from benchmark_direct_slot_input import Harness
from zx0_speed import Token,encode


def literal(n):
    raw=bytes(i%251 for i in range(n))
    return encode(raw,[Token(0,n)]),raw


def fixture(blocks,first=53):
    stream=b''.join(struct.pack('<HH',len(raw),len(payload))+payload for payload,raw in blocks)
    padded=stream+bytes((-len(stream))%256)
    image=bytearray(655360);physical=disk_layout.arrange(padded,first%16)
    image[first*256:first*256+len(physical)]=physical
    return Harness(bytes(image),first,len(padded)//256)


class DirectSlotTests(unittest.TestCase):
    def test_default_core_bytes_unchanged(self):
        self.assertEqual(sha256(bank_local_zx0.build()[0]).hexdigest(),
            '0f9e6c25f57b654887e742bb5e13bea2c80d11559447c1e3b3cbdbe4da75c455')

    def test_header_crossings_and_first_track_layout(self):
        candidates={}
        for n in range(1,520):
            payload,raw=literal(n);candidates.setdefault((len(payload)+4)%256,(payload,raw))
        for first in (32,47,53,63):
            for offset in (0,1,252,253,254,255):
                with self.subTest(first=first,offset=offset):
                    blocks=[candidates[offset],literal(1700),literal(11),literal(280),literal(1)]
                    h=fixture(blocks,first)
                    h.cpu.write8(video.SHADOW,0x1f)
                    for i,(payload,raw) in enumerate(blocks):
                        h.block(payload,raw,i)
                        self.assertEqual(h.cpu.port_7ffd&8,8)
                    self.assertEqual(h.results[1]['input_offset'],offset+4)
                    self.assertTrue(h.finish()['sectors_exact_once_in_original_order'])

    def test_many_blocks_sharing_one_sector_and_short_read_retry(self):
        blocks=[literal(800)]+[literal(1)]*36
        h=fixture(blocks,47)
        for i,(payload,raw) in enumerate(blocks):h.block(payload,raw,i,short=i==0)
        result=h.finish()
        self.assertEqual(sum(n for (pc,_),n in h.histogram.items() if pc==h.d['fast_read_retry']),1)
        self.assertLess(result['sector_reads'],len(blocks))
        self.assertGreater(sum(r['sector_reads']==0 for r in h.results),20)

    def test_reject_zero_length_and_input_overflow_before_decode(self):
        for length,size in ((0,10),(8193,10),(100,0),(100,8192)):
            stream=struct.pack('<HH',length,size)+bytes(size)
            image=bytearray(655360);physical=disk_layout.arrange(stream+bytes((-len(stream))%256),0)
            image[32*256:32*256+len(physical)]=physical
            h=Harness(bytes(image),32,(len(stream)+255)//256)
            with self.assertRaises(AssertionError):h.block(bytes(size),bytes(length),0)


if __name__=='__main__':unittest.main()
