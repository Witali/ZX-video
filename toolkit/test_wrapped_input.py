"""Wrapped ZX0 input keeps banks and suspended literal tails consistent."""
import random
import unittest

import blocked_stream
import build_fast_sparse_trd as codec
import packed_stream
import test_blocked_stream as reference
import zx0_codec
from test_memory_clock import OPTIONS, fixture, readword
from test_direct_ring_input import load
from test_packet_lookahead import run, word

# Upstream ZX0 2.2: 128 distinct literal bytes followed by a 6272-byte match.
LITERAL_COMPRESSED=bytes.fromhex('0003000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7fc0001555d55560')
LITERAL_DECODED=bytes(range(128))*50


def begin(cpu,labels,data,decoded,*,pointer,region=1,stored=False,target=2):
    load(cpu,labels,region,pointer,data)
    for name,value in dict(block_length=len(decoded),block_end=0x6000+len(decoded),
                           slice_output=0x6000,slice_target=0x6000+target).items():word(cpu,labels,name,value)
    cpu.write8(labels['block_stored'],int(stored));run(cpu,labels,'slice_begin')


class WrappedInputTests(unittest.TestCase):
    def test_each_compressed_input_split_resumes_literals_and_matches(self):
        self.assertEqual(zx0_codec.decompress(LITERAL_COMPRESSED),LITERAL_DECODED)
        for prefix in range(1,len(LITERAL_COMPRESSED)):
            with self.subTest(prefix=prefix):
                cpu,labels=fixture(direct_input=True,wrapped_input=True)
                region=1 if prefix&1 else 5
                begin(cpu,labels,LITERAL_COMPRESSED,LITERAL_DECODED,pointer=65536-prefix,region=region)
                for size in (17,127,128,129,257,6400):
                    cpu.set_bc(0x1234);cpu.set_de(0x5678);cpu.set_hl(0x9ABC)
                    cpu.a=73;cpu.alt_a=19;cpu.carry=True;cpu.z=True
                    word(cpu,labels,'slice_target',0x6000+size);run(cpu,labels,'slice_until')
                    self.assertEqual(bytes(cpu.read8(0x6000+i) for i in range(size)),LITERAL_DECODED[:size])
                    self.assertEqual(cpu.port_7ffd&7,7)
                self.assertEqual(readword(cpu,labels,'ring_count'),40)
                self.assertEqual(cpu.read8(labels['ring_read_region']),region)
                run(cpu,labels,'direct_release')
                self.assertEqual(readword(cpu,labels,'ring_count'),39)
                self.assertEqual(cpu.read8(labels['ring_read_region']),region%5+1)
                self.assertEqual(cpu.read8(labels['ring_read_low']),len(LITERAL_COMPRESSED)-prefix)
                self.assertEqual(cpu.dos_reads,0)
                self.assertGreaterEqual(cpu.min_sp,0x9D80)

    def test_wrapping_changes_only_input_pointer_and_current_input_bank(self):
        for region in (1,5):
            for carry in (False,True):
                cpu,labels=fixture(direct_input=True,wrapped_input=True)
                cpu.write8(labels['direct_region'],region)
                cpu.set_hl(0);cpu.set_bc(0x1234);cpu.set_de(0x6789)
                cpu.a=77;cpu.z=True;cpu.carry=carry
                run(cpu,labels,'direct_wrap')
                self.assertEqual((cpu.hl(),cpu.bc(),cpu.de(),cpu.a,cpu.z,cpu.carry),(0xC000,0x1234,0x6789,77,True,carry))
                self.assertEqual(cpu.read8(labels['direct_region']),region%5+1)
                self.assertEqual(cpu.port_7ffd&7,codec.RING_BANKS[region%5])

    def test_stored_run_keeps_original_sectors_owned_after_bank_switch(self):
        cpu,labels=fixture(direct_input=True,wrapped_input=True);data=random.Random(52).randbytes(6000)
        begin(cpu,labels,data,data,pointer=0xF00D,stored=True,target=4200)
        self.assertEqual(cpu.read8(labels['direct_region']),2)
        self.assertEqual(cpu.read8(labels['ring_read_region']),1)
        word(cpu,labels,'ring_count',320);word(cpu,labels,'disk_sectors_remaining',20)
        cpu.write8(labels['ring_write_region'],1);cpu.write8(labels['ring_write_high'],0xF0)
        banks=[bytes(cpu.banks[b]) for b in codec.RING_BANKS]
        run(cpu,labels,'producer_one')
        self.assertEqual(cpu.dos_reads,0)
        self.assertEqual([bytes(cpu.banks[b]) for b in codec.RING_BANKS],banks)
        word(cpu,labels,'slice_target',0x6000+len(data));run(cpu,labels,'slice_until')
        self.assertEqual(bytes(cpu.read8(0x6000+i) for i in range(len(data))),data)
        run(cpu,labels,'direct_release')
        self.assertEqual(readword(cpu,labels,'ring_count'),297)
        self.assertEqual(cpu.read8(labels['ring_read_low']),125)

    def test_compressed_stream_with_irq_stress(self):
        block=blocked_stream.Block(reference.EMPTY_COMPRESSED,reference.EMPTY_DECODED,500,False,0)
        reference.BlockedStreamTests().run_player([bytes(3840)]*1000,[block,block],
            **{k:v for k,v in OPTIONS.items() if k!='blocked'},direct_input=True,wrapped_input=True)

    def test_dense_stored_stream_wraps_with_irq_stress(self):
        states=[random.Random(303+i).randbytes(3840) for i in range(8)]
        _,packets=codec.make_volume_packets(states,[bytes(9)]*len(states),0,2530,packed=True)
        frames=[packed_stream.frame_bytes(p,natural_order=True) for p in packets]
        blocks=[blocked_stream.Block(f,f,1,True,0) for f in frames]
        reference.BlockedStreamTests().run_player(states,blocks,
            **{k:v for k,v in OPTIONS.items() if k!='blocked'},direct_input=True,wrapped_input=True)

    def test_wrapped_compressed_decoder_resumes_with_irq_stress(self):
        def irq_run(cpu,labels,name):
            cpu.pc=labels[name];cpu.push(0x5F00);next_irq=cpu.tstates+233;interrupts=0
            while cpu.pc!=0x5F00:
                self.assertNotEqual(cpu.pc,labels['fatal']);cpu.step()
                if cpu.iff1 and cpu.tstates>=next_irq:
                    cpu.push(cpu.pc);cpu.pc=0xBDBD;cpu.iff1=False;cpu.tstates+=19
                    next_irq=cpu.tstates+233;interrupts+=1
            self.assertEqual(cpu.sp,0xBFF0)
            return interrupts
        for prefix in (1,8,63,128):
            cpu,labels=fixture(direct_input=True,wrapped_input=True)
            load(cpu,labels,5,65536-prefix,LITERAL_COMPRESSED)
            for name,value in dict(block_length=6400,block_end=0x7900,slice_output=0x6000,slice_target=0x6002).items():word(cpu,labels,name,value)
            cpu.write8(labels['block_stored'],0);cpu.iff1=True
            interrupts=irq_run(cpu,labels,'slice_begin')
            for size in list(range(128,6400,128))+[6400]:
                word(cpu,labels,'slice_target',0x6000+size);interrupts+=irq_run(cpu,labels,'slice_until')
            self.assertGreater(interrupts,100)
            self.assertEqual(bytes(cpu.read8(0x6000+i) for i in range(6400)),LITERAL_DECODED)
            self.assertEqual(cpu.port_7ffd&7,7)
            self.assertGreaterEqual(cpu.min_sp,0x9D80)

    def test_wrapped_input_requires_direct_input(self):
        with self.assertRaises(ValueError):codec.build_player(3,2,wrapped_input=True)


if __name__=='__main__':unittest.main()
