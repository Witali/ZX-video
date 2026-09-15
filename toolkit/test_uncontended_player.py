"""Relocation must preserve decoding, screens, IRQs and instruction timings."""
import random
import struct
import unittest

import blocked_stream
import build_fast_sparse_trd as codec
import packed_stream
import test_blocked_stream as reference
from test_packet_lookahead import OPTIONS, run, word
from validate_fast_sparse import CPU


def relocate(cpu, labels):
    before=cpu.tstates
    while cpu.pc!=labels['start']:
        assert cpu.steps<20
        cpu.step()
    return cpu.tstates-before


def packet_cycles(uncontended, background):
    player,labels=codec.build_player(0,0,**OPTIONS,uncontended=uncontended)
    cpu=CPU(player,b'')
    if uncontended:relocate(cpu,labels)
    cpu.sp=0xBFF0;cpu.port_7ffd=0x17
    # Two 1000-byte packets including headers, the same fixture as the
    # packet-lookahead baseline. Only preparation is timed here.
    frame=struct.pack('<H',998)+random.Random(83).randbytes(998)
    body=frame*2;stream=struct.pack('<HH',len(body)|0x8000,len(body))+body
    cpu.banks[0][:len(stream)]=stream
    word(cpu,labels,'ring_count',30);word(cpu,labels,'frames_remaining',3)
    cpu.write8(labels['ring_read_region'],1);cpu.write8(labels['ring_read_high'],0xC0)
    output=0x6000 if uncontended else 0x8000
    total=0;quanta=[]
    if background:
        while cpu.read8(labels['ahead_state'])!=2:
            quantum=run(cpu,labels,'ahead_prefetch');quanta.append(quantum);total+=quantum
        while cpu.read8(labels['slice_output'])|cpu.read8(labels['slice_output']+1)<<8 < output+len(body):
            quantum=run(cpu,labels,'ahead_prefetch');quanta.append(quantum);total+=quantum
    for index in range(2):
        total+=run(cpu,labels,'wait_packet')
        word(cpu,labels,'block_frame_pointer',output+len(frame)*(index+1))
    assert bytes(cpu.read8(output+i) for i in range(len(body)))==body
    return total,quanta


class UncontendedPlayerTests(unittest.TestCase):
    def test_bootstrap_copies_code_and_has_exact_timing(self):
        player,labels=codec.build_player(0,0,**OPTIONS,uncontended=True)
        cpu=CPU(player,b'');native=player[16:]
        self.assertEqual(relocate(cpu,labels),21*len(native)+39)
        self.assertEqual(bytes(cpu.banks[2][16:16+len(native)]),native)
        self.assertEqual(labels['start'],0x8010)
        self.assertLessEqual(0x8010+len(native),0x9D00)
        self.assertFalse(cpu.iff1)

    def test_packet_paths_keep_exact_instruction_counts(self):
        for background,expected in ((False,95963),(True,116330)):
            previous=packet_cycles(False,background)
            current=packet_cycles(True,background)
            self.assertEqual(current,previous)
            self.assertEqual(current[0],expected)

    def test_compressed_blocks_with_irq_stress(self):
        block=blocked_stream.Block(reference.EMPTY_COMPRESSED,reference.EMPTY_DECODED,500,False,0)
        reference.BlockedStreamTests().run_player([bytes(3840)]*1000,[block,block],uncontended=True,
            **{k:v for k,v in OPTIONS.items() if k!='blocked'})

    def test_dense_stored_frames_cross_screens_and_sectors_with_irq(self):
        states=[random.Random(83+i).randbytes(3840) for i in range(6)]
        _,packets=codec.make_volume_packets(states,[bytes(9)]*len(states),0,2530,packed=True)
        frames=[packed_stream.frame_bytes(p,natural_order=True) for p in packets]
        blocks=[blocked_stream.Block(frame,frame,1,True,0) for frame in frames]
        reference.BlockedStreamTests().run_player(states,blocks,uncontended=True,
            **{k:v for k,v in OPTIONS.items() if k!='blocked'})

    def test_rejects_conflicting_memory_layouts(self):
        with self.assertRaises(ValueError):codec.build_player(0,0,uncontended=True)
        with self.assertRaises(ValueError):
            codec.build_player(0,0,**OPTIONS,uncontended=True,keepalive_fields=64)


if __name__=='__main__':unittest.main()
