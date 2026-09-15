"""RAM clock ticks preserve live registers, survive ROM and wrap at 65536."""
import random
import unittest

import blocked_stream
import build_fast_sparse_trd as codec
import packed_stream
import test_blocked_stream as reference
import playback_schedule
from test_packet_lookahead import OPTIONS as PACKET_OPTIONS, run, word
from test_uncontended_player import relocate
from validate_fast_sparse import CPU

OPTIONS=dict(**PACKET_OPTIONS,uncontended=True,full_rom_clock=True,cached_seek=True,
             keepalive_fields=64,read_reserve=64,memory_clock=True)


def fixture(cpu_type=CPU):
    player,labels=codec.build_player(3,2,**OPTIONS)
    cpu=cpu_type(player,bytes(2560*256));relocate(cpu,labels)
    cpu.sp=0xBFF0;cpu.port_7ffd=0x17;run(cpu,labels,'setup_clock')
    return cpu,labels


def readword(cpu,labels,name):
    return cpu.read8(labels[name])|cpu.read8(labels[name]+1)<<8


class MemoryClockTests(unittest.TestCase):
    def test_fast_irq_wrap_preserves_all_registers_and_costs_116_tstates(self):
        for count in (0,255,65535):
            cpu,labels=fixture();word(cpu,labels,'elapsed_fields',count)
            cpu.set_bc(0x1234);cpu.set_de(0x5678);cpu.set_hl(0x9ABC);cpu.ix=0x8142
            cpu.a=77;cpu.z=True;cpu.carry=True;cpu.alt_a=54
            cpu.alt_b=9;cpu.alt_c=8;cpu.alt_d=7;cpu.alt_e=6;cpu.alt_h=5;cpu.alt_l=4
            names=('a','b','c','d','e','h','l','ix','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l','z','carry')
            original={name:getattr(cpu,name) for name in names}
            start=cpu.tstates;cpu.pc=0xBDBD;cpu.push(0x5F00)
            while cpu.pc!=0x5F00:cpu.step()
            self.assertEqual(cpu.tstates-start+19,116)
            self.assertEqual(readword(cpu,labels,'elapsed_fields'),(count+1)&65535)
            self.assertEqual({name:getattr(cpu,name) for name in names},original)
            self.assertEqual(cpu.sp,0xBFF0)

    def test_slow_irq_preserves_break_routing_and_exact_cycles(self):
        for return_pc,total in ((0x8001,184),(0x1F53,211),(0x1F54,210),(0x1F5F,210),(0x1F60,225)):
            cpu,labels=fixture()
            for i,value in enumerate(bytes.fromhex('c300bd')):cpu.write8(0xBDBD+i,value)
            word(cpu,labels,'elapsed_fields',65535)
            cpu.set_hl(0x1234);cpu.a=77;cpu.z=True;cpu.carry=True
            cpu.alt_h=0x56;cpu.alt_l=0x78
            start=cpu.tstates;cpu.pc=0xBDBD;cpu.push(return_pc);mapper=False
            while cpu.pc!=return_pc:
                if cpu.read8(cpu.pc)==0xC3 and cpu.read8(cpu.pc+1)==0x2F:mapper=True
                cpu.step()
            self.assertEqual(cpu.tstates-start+19,total)
            self.assertEqual(readword(cpu,labels,'elapsed_fields'),0)
            self.assertEqual((cpu.hl(),cpu.a,cpu.z,cpu.carry,cpu.alt_h,cpu.alt_l),(0x1234,77,True,True,0x56,0x78))
            self.assertEqual(mapper,not 0x1F54<=return_pc<0x1F60)

    def test_rom_reads_preserve_ticks_restore_vector_and_enable_irq(self):
        class TickingROM(CPU):
            def mock_trdos(self):
                super().mock_trdos()
                word(self,self.labels,'elapsed_fields',readword(self,self.labels,'elapsed_fields')+3)
        for cached in (255,2,3):
            cpu,labels=fixture(TickingROM);cpu.labels=labels
            vector=bytes(cpu.read8(0xBDBD+i) for i in range(13))
            word(cpu,labels,'elapsed_fields',255);cpu.alt_h=0x12;cpu.alt_l=0x34
            for name,value in dict(disk_track=3,disk_sector=2,fast_disk_track=cached).items():cpu.write8(labels[name],value)
            cpu.write8(0x5CF5,3);cpu.set_hl(0xC000);cpu.b=1
            run(cpu,labels,'read_n')
            self.assertEqual(cpu.dos_reads,1)
            self.assertEqual(readword(cpu,labels,'elapsed_fields'),258)
            self.assertEqual(readword(cpu,labels,'last_disk_fields'),258)
            self.assertEqual(bytes(cpu.read8(0xBDBD+i) for i in range(13)),vector)
            self.assertTrue(cpu.iff1)
            self.assertEqual((cpu.alt_h,cpu.alt_l),(0x12,0x34))

    def test_keepalive_preserves_memory_clock_and_restores_fast_vector(self):
        cpu,labels=fixture();vector=bytes(cpu.read8(0xBDBD+i) for i in range(13))
        word(cpu,labels,'elapsed_fields',100);word(cpu,labels,'disk_sectors_remaining',20)
        cpu.write8(labels['fast_disk_track'],10);cpu.alt_h=0x12;cpu.alt_l=0x34
        run(cpu,labels,'motor_keepalive')
        self.assertEqual(readword(cpu,labels,'elapsed_fields'),100)
        self.assertEqual(readword(cpu,labels,'last_disk_fields'),100)
        self.assertEqual(bytes(cpu.read8(0xBDBD+i) for i in range(13)),vector)
        self.assertTrue(cpu.iff1)
        self.assertEqual(cpu.dos_reads,0)

    def test_handler_switch_tolerates_irq_at_each_instruction_boundary(self):
        for slow in (False,True):
            for boundary in (0,1,2):
                cpu,labels=fixture()
                code=codec.base.MiniAssembler(0x5E00)
                playback_schedule.select_rom_clock(code,slow,True);code.emit(0xC9)
                for i,value in enumerate(code.resolve()):cpu.write8(0x5E00+i,value)
                cpu.pc=0x5E00;cpu.push(0x5F00);cpu.iff1=True
                for _ in range(boundary):cpu.step()
                return_pc=cpu.pc;cpu.push(return_pc);cpu.pc=0xBDBD
                while cpu.pc!=return_pc:cpu.step()
                while cpu.pc!=0x5F00:cpu.step()
                self.assertEqual(cpu.read8(0xBDBD),0xC3)
                self.assertEqual(cpu.read8(0xBDBE)|cpu.read8(0xBDBF)<<8,0xBD00 if slow else 0xBD80)
                self.assertEqual(readword(cpu,labels,'elapsed_fields'),1)
                self.assertTrue(cpu.iff1)

    def test_short_read_retry_restores_im2_and_fast_handler(self):
        class ShortRead(CPU):
            def instruction(self):
                before=self.pc;cycles=super().instruction()
                if before==self.labels['fast_read_enter']:self.set_hl(0xC001)
                return cycles
        # setup_clock runs before the helper needs the final labels.
        ShortRead.labels={'fast_read_enter':-1}
        cpu,labels=fixture(ShortRead);cpu.labels=labels
        for name,value in dict(disk_track=3,disk_sector=2,fast_disk_track=3).items():cpu.write8(labels[name],value)
        cpu.write8(0x5CF5,3);cpu.set_hl(0xC000);cpu.b=1
        run(cpu,labels,'read_n')
        self.assertEqual(cpu.dos_reads,2)
        self.assertEqual((cpu.i,cpu.im,cpu.iff1),(0xBE,2,True))
        self.assertEqual(cpu.read8(0xBDBE)|cpu.read8(0xBDBF)<<8,0xBD80)

    def test_complete_compressed_blocks_with_irq_stress(self):
        block=blocked_stream.Block(reference.EMPTY_COMPRESSED,reference.EMPTY_DECODED,500,False,0)
        reference.BlockedStreamTests().run_player([bytes(3840)]*1000,[block,block],
            **{k:v for k,v in OPTIONS.items() if k!='blocked'})

    def test_dense_stored_frames_with_irq_stress(self):
        states=[random.Random(83+i).randbytes(3840) for i in range(6)]
        _,packets=codec.make_volume_packets(states,[bytes(9)]*len(states),0,2530,packed=True)
        frames=[packed_stream.frame_bytes(p,natural_order=True) for p in packets]
        blocks=[blocked_stream.Block(frame,frame,1,True,0) for frame in frames]
        reference.BlockedStreamTests().run_player(states,blocks,
            **{k:v for k,v in OPTIONS.items() if k!='blocked'})


if __name__=='__main__':unittest.main()
