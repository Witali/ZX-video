"""Input ownership, bank crossings and decoder resumes for borrowed ring data."""
import random
import unittest

import blocked_stream
import build_fast_sparse_trd as codec
import packed_stream
import test_blocked_stream as reference
from test_memory_clock import OPTIONS, fixture, readword
from test_packet_lookahead import run, word


def place(cpu,region,pointer,data):
    start=(region-1)*16384+(pointer-0xC000)
    for i,value in enumerate(data):
        offset=(start+i)%(5*16384)
        cpu.banks[codec.RING_BANKS[offset//16384]][offset%16384]=value


def load(cpu,labels,region,pointer,data):
    place(cpu,region,pointer,data)
    cpu.write8(labels['ring_read_region'],region)
    cpu.write8(labels['ring_read_high'],pointer>>8)
    cpu.write8(labels['ring_read_low'],pointer&255)
    word(cpu,labels,'ring_count',40);word(cpu,labels,'frame_length',len(data))
    cpu.write8(labels['ahead_force'],1)
    run(cpu,labels,'load_block_body')


class DirectRingInputTests(unittest.TestCase):
    def test_borrow_and_release_partial_exact_and_crossing_bank_boundaries(self):
        for region,pointer,length in ((1,0xC004,1000),(3,0xFBF0,1040),(5,0xFFF6,10),
                                      (1,0xFBF0,1041),(5,0xFFF6,12),(1,0xC003,12)):
            with self.subTest(region=region,pointer=pointer,length=length):
                cpu,labels=fixture(direct_input=True);data=random.Random(23).randbytes(length)
                load(cpu,labels,region,pointer,data)
                fits=pointer+length<=65536
                self.assertEqual(cpu.read8(labels['direct_region']),region if fits else 0)
                if fits:
                    self.assertEqual(cpu.read8(labels['ring_read_low']),pointer&255)
                    self.assertEqual(readword(cpu,labels,'ring_count'),40)
                    self.assertEqual(readword(cpu,labels,'direct_pointer'),pointer)
                    run(cpu,labels,'direct_release')
                else:
                    self.assertEqual(bytes(cpu.read8(0xA000+i) for i in range(length)),data)
                consumed=((pointer&255)+length)//256
                end=(region-1)*16384+(pointer-0xC000)+length
                self.assertEqual(cpu.read8(labels['ring_read_region']),(end//16384)%5+1)
                self.assertEqual(cpu.read8(labels['ring_read_high']),0xC0+(end%16384)//256)
                self.assertEqual(cpu.read8(labels['ring_read_low']),end%256)
                self.assertEqual(readword(cpu,labels,'ring_count'),40-consumed)
                self.assertEqual(cpu.read8(labels['direct_region']),0)
                self.assertEqual(cpu.port_7ffd&7,7)
                self.assertEqual(cpu.dos_reads,0)

    def test_full_ring_producer_cannot_overwrite_borrowed_input(self):
        cpu,labels=fixture(direct_input=True);data=random.Random(55).randbytes(6000)
        load(cpu,labels,1,0xC004,data)
        word(cpu,labels,'ring_count',320);word(cpu,labels,'disk_sectors_remaining',20)
        cpu.write8(labels['ring_write_region'],1);cpu.write8(labels['ring_write_high'],0xC0)
        before=bytes(cpu.banks[0]);run(cpu,labels,'producer_one')
        self.assertEqual(cpu.dos_reads,0)
        self.assertEqual(readword(cpu,labels,'ring_count'),320)
        self.assertEqual(bytes(cpu.banks[0]),before)

    def test_precopy_checks_available_input_after_releasing_held_sectors(self):
        cpu,labels=fixture(direct_input=True);load(cpu,labels,1,0xC000,bytes(7424))
        word(cpu,labels,'ring_count',30);word(cpu,labels,'frames_remaining',3)
        word(cpu,labels,'slice_output',0x8000);word(cpu,labels,'block_end',0x8000)
        cpu.write8(labels['ahead_state'],2)
        run(cpu,labels,'ahead_prefetch')
        self.assertEqual(readword(cpu,labels,'ring_count'),1)
        self.assertEqual(cpu.read8(labels['direct_region']),0)
        self.assertEqual(cpu.read8(labels['ahead_state']),2)
        self.assertEqual((cpu.a,cpu.dos_reads),(0,0))

    def test_compressed_blocks_decode_with_frequent_irq_and_shared_sector(self):
        block=blocked_stream.Block(reference.EMPTY_COMPRESSED,reference.EMPTY_DECODED,500,False,0)
        reference.BlockedStreamTests().run_player([bytes(3840)]*1000,[block,block],
            **{k:v for k,v in OPTIONS.items() if k!='blocked'},direct_input=True)

    def test_dense_stored_blocks_and_crossing_fallback_with_irq(self):
        states=[random.Random(133+i).randbytes(3840) for i in range(8)]
        _,packets=codec.make_volume_packets(states,[bytes(9)]*len(states),0,2530,packed=True)
        frames=[packed_stream.frame_bytes(p,natural_order=True) for p in packets]
        blocks=[blocked_stream.Block(f,f,1,True,0) for f in frames]
        reference.BlockedStreamTests().run_player(states,blocks,
            **{k:v for k,v in OPTIONS.items() if k!='blocked'},direct_input=True)

    def test_direct_input_requires_relocated_lookahead(self):
        with self.assertRaises(ValueError):codec.build_player(3,2,direct_input=True)


if __name__=='__main__':unittest.main()
