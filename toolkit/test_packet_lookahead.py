"""Packet preparation resumes safely around foreground and ROM clobbers."""
import random
import struct
import unittest

import build_fast_sparse_trd as codec
from validate_fast_sparse import CPU

OPTIONS=dict(blocked=True,clocked=True,deadline=True,fast_disk=True,irq_disk=True,
             incremental=True,fast_draw=True,prefetch_quota=3,lookahead=True)


def word(cpu,labels,name,value):
    cpu.write8(labels[name],value);cpu.write8(labels[name]+1,value>>8)


def run(cpu,labels,name):
    cpu.pc=labels[name];cpu.push(0x5F00);before=cpu.tstates;steps=cpu.steps
    while cpu.pc!=0x5F00:
        assert cpu.pc!=labels['fatal']
        assert cpu.steps-steps<200000
        cpu.step()
    assert cpu.sp==0xBFF0
    return cpu.tstates-before


class PacketLookaheadTests(unittest.TestCase):
    def test_complete_compressed_player_with_irq_stress(self):
        import blocked_stream
        import test_blocked_stream as reference
        block=blocked_stream.Block(reference.EMPTY_COMPRESSED,reference.EMPTY_DECODED,500,False,0)
        helper=reference.BlockedStreamTests()
        helper.run_player([bytes(3840)]*1000,[block,block],clocked=True,
                          **{k:v for k,v in OPTIONS.items() if k not in ('blocked','clocked')})

    def fixture(self):
        player,labels=codec.build_player(0,0,**OPTIONS)
        cpu=CPU(player,b'');cpu.sp=0xBFF0;cpu.port_7ffd=0x17
        frame=struct.pack('<H',998)+random.Random(83).randbytes(998)
        data=frame*2
        stream=struct.pack('<HH',0x8000|len(data),len(data))+data
        cpu.banks[0][:len(stream)]=stream
        for name,value in dict(ring_count=30,frames_remaining=3).items():word(cpu,labels,name,value)
        cpu.write8(labels['ring_read_region'],1);cpu.write8(labels['ring_read_high'],0xC0)
        cpu.alt_h=0x12;cpu.alt_l=0x34
        return cpu,labels,frame

    def test_quanta_resume_with_clobbered_registers_and_keep_frame_pointer(self):
        cpu,labels,frame=self.fixture();quanta=[]
        while cpu.read8(labels['ahead_state'])!=2:
            self.assertLess(len(quanta),100)
            quanta.append(run(cpu,labels,'ahead_prefetch'))
            cpu.set_bc(0x1234);cpu.set_de(0x5678);cpu.set_hl(0x9ABC)
            cpu.a=77;cpu.z=True;cpu.carry=True;cpu.alt_a=0x92
        self.assertEqual(bytes(cpu.banks[2][:len(frame)]),frame)
        self.assertEqual(cpu.read8(labels['block_frame_pointer'])|cpu.read8(labels['block_frame_pointer']+1)<<8,0x8000)
        self.assertEqual(cpu.dos_reads,0)
        self.assertEqual(cpu.alt_h*256+cpu.alt_l,0x1234)
        self.assertGreaterEqual(cpu.min_sp,0x7D00)
        self.assertLess(max(quanta),12000)
        self.assertGreater(len(quanta),8)
        run(cpu,labels,'wait_packet')
        self.assertEqual(cpu.read8(labels['ahead_state']),0)
        word(cpu,labels,'block_frame_pointer',0x8000+len(frame))
        run(cpu,labels,'ahead_prefetch')
        self.assertEqual(cpu.read8(labels['ahead_state']),1)
        run(cpu,labels,'wait_packet')
        self.assertEqual(bytes(cpu.banks[2][:len(frame)*2]),frame*2)

    def test_background_input_shortage_yields_without_io_then_resumes(self):
        cpu,labels,frame=self.fixture();word(cpu,labels,'ring_count',2)
        run(cpu,labels,'ahead_prefetch')
        self.assertEqual((cpu.a,cpu.dos_reads),(0,0))
        self.assertEqual(cpu.read8(labels['ring_read_low']),0)
        run(cpu,labels,'ahead_prefetch')
        self.assertEqual((cpu.a,cpu.dos_reads),(0,0))
        word(cpu,labels,'ring_count',30)
        run(cpu,labels,'wait_packet')
        self.assertEqual(bytes(cpu.banks[2][:len(frame)]),frame)

    def test_consuming_a_packet_during_extension_preserves_decoder_history(self):
        for complete_extension in (False,True):
            cpu,labels,frame=self.fixture()
            while cpu.read8(labels['ahead_state'])!=2:run(cpu,labels,'ahead_prefetch')
            run(cpu,labels,'ahead_prefetch')
            self.assertEqual(cpu.read8(labels['ahead_state']),3)
            if complete_extension:
                while cpu.read8(labels['ahead_state'])!=2:run(cpu,labels,'ahead_prefetch')
            run(cpu,labels,'wait_packet')
            self.assertEqual(bytes(cpu.banks[2][:len(frame)]),frame)
            word(cpu,labels,'block_frame_pointer',0x8000+len(frame))
            while cpu.read8(labels['ahead_state'])!=2:run(cpu,labels,'ahead_prefetch')
            run(cpu,labels,'wait_packet')
            self.assertEqual(bytes(cpu.banks[2][:len(frame)*2]),frame*2)

    def test_last_frame_does_not_start_another_packet(self):
        cpu,labels,_=self.fixture();word(cpu,labels,'frames_remaining',1)
        run(cpu,labels,'ahead_prefetch')
        self.assertEqual((cpu.a,cpu.read8(labels['ahead_state']),cpu.dos_reads),(0,0,0))

    def test_precopy_can_span_foreground_frames_and_finish_at_block_boundary(self):
        for finish_copy in (False,True):
            cpu,labels,frame=self.fixture();word(cpu,labels,'ring_count',40)
            next_frame=struct.pack('<H',998)+random.Random(91).randbytes(998)
            offset=4+2*len(frame)
            next_stream=struct.pack('<HH',0x8000|len(next_frame),len(next_frame))+next_frame
            cpu.banks[0][offset:offset+len(next_stream)]=next_stream
            for _ in range(100):
                run(cpu,labels,'ahead_prefetch')
                if cpu.read8(labels['ahead_state'])==4:break
            self.assertEqual(cpu.read8(labels['ahead_state']),4)
            if finish_copy:
                while cpu.read8(labels['ahead_state'])==4:run(cpu,labels,'ahead_prefetch')
                self.assertEqual(cpu.read8(labels['ahead_state']),5)
            run(cpu,labels,'wait_packet')
            word(cpu,labels,'block_frame_pointer',0x8000+len(frame))
            run(cpu,labels,'wait_packet')
            self.assertEqual(bytes(cpu.banks[2][:2*len(frame)]),frame*2)
            word(cpu,labels,'block_frame_pointer',0x8000+2*len(frame))
            run(cpu,labels,'wait_packet')
            self.assertEqual(bytes(cpu.banks[2][:len(next_frame)]),next_frame)
            self.assertEqual(cpu.read8(labels['ahead_input_ready']),0)
            self.assertEqual(cpu.dos_reads,0)

    def test_recycle_history_after_last_draw_preserves_both_screens_and_ay(self):
        from test_memory_clock import fixture, readword
        from test_blocked_stream import EMPTY_COMPRESSED, EMPTY_DECODED

        def packet(value):
            body=bytes([value])*9+bytes([codec.CMD_BITMAP_POINTS,0,1,0,value,0])
            return struct.pack('<H',len(body))+body

        def block(data,decoded,stored):
            return struct.pack('<HH',len(data)|(0x8000 if stored else 0),len(decoded))+data

        old=packet(0x11)+packet(0x22)
        for stored in (False,True):
            with self.subTest(stored=stored):
                cpu,labels=fixture()
                decoded=packet(0x33) if stored else EMPTY_DECODED
                data=decoded if stored else EMPTY_COMPRESSED
                stream=block(old,old,True)+block(data,decoded,stored)
                cpu.banks[0][:len(stream)]=stream
                word(cpu,labels,'ring_count',40);word(cpu,labels,'frames_remaining',3)
                cpu.write8(labels['ring_read_region'],1);cpu.write8(labels['ring_read_high'],0xC0)
                cpu.write8(labels['update_base'],0x40);word(cpu,labels,'attr_base',0x5800)
                run(cpu,labels,'wait_packet');run(cpu,labels,'ring_packet');run(cpu,labels,'ay_apply')
                for _ in range(100):
                    if cpu.read8(labels['ahead_state'])==5:break
                    run(cpu,labels,'ahead_prefetch')
                self.assertEqual(cpu.read8(labels['ahead_state']),5)
                self.assertLess(readword(cpu,labels,'block_frame_pointer'),readword(cpu,labels,'block_end'))
                self.assertEqual(run(cpu,labels,'ahead_prefetch'),155)
                self.assertEqual(cpu.a,0)
                self.assertEqual(bytes(cpu.read8(0x6000+i) for i in range(len(old))),old)
                self.assertEqual(cpu.read8(labels['ahead_state']),5)
                cpu.write8(labels['update_base'],0xC0);word(cpu,labels,'attr_base',0xD800)
                run(cpu,labels,'wait_packet');run(cpu,labels,'ring_packet')
                self.assertEqual(readword(cpu,labels,'block_frame_pointer'),readword(cpu,labels,'block_end'))
                screens=[bytes(cpu.banks[bank][:6912]) for bank in (5,7)]
                staged=bytes(cpu.read8(labels['ay_state']+i) for i in range(9))
                self.assertEqual(staged,bytes([0x22])*9)
                playing=bytes(cpu.ay)
                for _ in range(100):
                    run(cpu,labels,'ahead_prefetch')
                    if cpu.read8(labels['ahead_state'])==2:break
                self.assertEqual(cpu.read8(labels['ahead_state']),2)
                packet_length=int.from_bytes(decoded[:2],'little')+2
                self.assertEqual(bytes(cpu.read8(0x6000+i) for i in range(packet_length)),decoded[:packet_length])
                self.assertEqual([bytes(cpu.banks[bank][:6912]) for bank in (5,7)],screens)
                self.assertEqual(bytes(cpu.read8(labels['ay_state']+i) for i in range(9)),staged)
                self.assertEqual(bytes(cpu.ay),playing)
                self.assertEqual(cpu.dos_reads,0)
                run(cpu,labels,'ay_apply')
                cpu.write8(labels['update_base'],0x40);word(cpu,labels,'attr_base',0x5800)
                run(cpu,labels,'wait_packet');run(cpu,labels,'ring_packet')
                expected=bytes([0x33])*9 if stored else bytes(9)
                self.assertEqual(bytes(cpu.read8(labels['ay_state']+i) for i in range(9)),expected)

    def test_precopied_decoded_length_is_still_validated(self):
        for invalid in (0,11,8193):
            cpu,labels,_=self.fixture()
            cpu.write8(labels['ahead_state'],5);cpu.write8(labels['ahead_input_ready'],1)
            word(cpu,labels,'block_length',invalid)
            cpu.pc=labels['wait_packet'];cpu.push(0x5F00)
            for _ in range(1000):
                if cpu.pc in (labels['fatal'],0x5F00):break
                cpu.step()
            self.assertEqual(cpu.pc,labels['fatal'])


if __name__=='__main__':unittest.main()
