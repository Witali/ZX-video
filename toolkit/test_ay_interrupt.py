"""Actual Z80 queue consumption, no redundant AY writes, IRQ-safe publication."""
import unittest

import ay_interrupt as audio
import build_zxv_trd as base
import build_long_video_trd as video
from test_packet_lookahead import run, word
from validate_fast_sparse import CPU


class TraceCPU(CPU):
    def __init__(self,*args):
        super().__init__(*args);self.writes=[]

    def instruction(self):
        if self.read8(self.pc)==0xED and self.read8(self.pc+1)==0x79 and self.bc()==0xBFFD:
            self.writes.append((self.ay_register,self.a))
        # LDIR can be interrupted between byte transfers on real hardware.
        if self.read8(self.pc)==0xED and self.read8(self.pc+1)==0xB0 and self.bc()>1:
            self.write8(self.de(),self.read8(self.hl()))
            self.set_hl(self.hl()+1);self.set_de(self.de()+1);self.set_bc(self.bc()-1)
            return 21
        return super().instruction()


def fixture(frames=1):
    a=base.MiniAssembler(0x6000);audio.emit(a);audio.emit_variables(a)
    a.label('fatal');a.emit(0x76)
    cpu=TraceCPU(a.resolve(),b'');cpu.sp=0xBFF0;cpu.port_7ffd=0x17
    cpu.set_hl(frames);run(cpu,a.labels,'audio_init')
    return cpu,a.labels


def stage(cpu,labels,records):
    data=b''.join(records)
    for i,b in enumerate(data):cpu.write8(0x8000+i,b)
    cpu.set_hl(0x8000)
    return run(cpu,labels,'audio_enqueue_six')


def arm(cpu,labels):cpu.write8(labels['audio_enabled'],1)


def word_at(cpu,labels,name):return cpu.read8(labels[name])+256*cpu.read8(labels[name]+1)


class AyInterruptTests(unittest.TestCase):
    def test_timing_table_counts_for_every_write_count(self):
        for count in range(12):
            for final in (False,True):
                cpu,labels=fixture(2)
                record=bytes([count])+b''.join(bytes([i,0]) for i in range(count))
                cycles=stage(cpu,labels,[record]+[b'\0']*5)
                self.assertEqual(cycles,1705+42*count)
                arm(cpu,labels)
                if final:word(cpu,labels,'audio_remaining',1)
                cycles=run(cpu,labels,'audio_tick')
                self.assertEqual(cycles,(367+83*count if count else 377)+(24 if final else 0))
        cpu,labels=fixture()
        self.assertEqual(run(cpu,labels,'audio_tick'),58)
        arm(cpu,labels)
        self.assertEqual(run(cpu,labels,'audio_tick'),205)

    def test_empty_changes_do_no_io_and_noise_transitions_are_exact(self):
        tone=video.AyFrame((300,400,500),(10,12,14))
        noise=video.AyFrame(tone.periods,(10,9,14),19)
        frames=[tone,tone,noise,noise,tone,tone]
        records=audio.encode_ticks(frames)
        self.assertEqual([r[0] for r in records],[11,0,3,0,3,0])
        cpu,labels=fixture();stage(cpu,labels,records);arm(cpu,labels)
        for frame,record in zip(frames,records):
            cpu.writes=[];run(cpu,labels,'audio_tick')
            self.assertEqual(bytes(cpu.ay[:11]),audio.registers(frame))
            self.assertEqual(cpu.writes,list(zip(record[1::2],record[2::2])))
        self.assertEqual(word_at(cpu,labels,'audio_ticks_played'),6)
        self.assertEqual(word_at(cpu,labels,'audio_underruns'),0)
        self.assertEqual(cpu.read8(labels['audio_enabled']),0)
        cpu.writes=[];run(cpu,labels,'audio_tick');self.assertFalse(cpu.writes)

    def test_index_wrap_and_register_preservation(self):
        frames=[video.AyFrame((200+i,400,700),(i%16,12,14),i%32) for i in range(120)]
        records=audio.encode_ticks(frames)
        cpu,labels=fixture(20);arm(cpu,labels)
        for start in range(0,120,6):
            stage(cpu,labels,records[start:start+6])
            for frame in frames[start:start+6]:
                cpu.a=0xAB;cpu.set_bc(0x1234);cpu.set_de(0x5678);cpu.set_hl(0x9ABC)
                cpu.z=True;cpu.carry=True;cpu.ix=0x9876
                run(cpu,labels,'audio_tick')
                self.assertEqual((cpu.a,cpu.bc(),cpu.de(),cpu.hl(),cpu.z,cpu.carry,cpu.ix),
                                 (0xAB,0x1234,0x5678,0x9ABC,True,True,0x9876))
                self.assertEqual(bytes(cpu.ay[:11]),audio.registers(frame))
        self.assertEqual(word_at(cpu,labels,'audio_ticks_played'),120)
        self.assertEqual(word_at(cpu,labels,'audio_underruns'),0)

    def test_underrun_does_not_read_unpublished_memory(self):
        cpu,labels=fixture();arm(cpu,labels)
        for i in range(1024):cpu.write8(audio.QUEUE_BASE+i,255)
        run(cpu,labels,'audio_tick')
        self.assertFalse(cpu.writes)
        self.assertEqual(word_at(cpu,labels,'audio_underruns'),1)
        self.assertEqual(word_at(cpu,labels,'audio_remaining'),6)

    def test_publication_is_safe_at_every_instruction_and_ldir_byte(self):
        frames=[video.AyFrame((300+i,400,500),(10,12,14),i) for i in range(6)]
        records=audio.encode_ticks(frames)
        reference,labels=fixture();before=reference.steps;stage(reference,labels,records)
        for boundary in range(reference.steps-before):
            cpu,labels=fixture();arm(cpu,labels)
            for i,b in enumerate(b''.join(records)):cpu.write8(0x8000+i,b)
            cpu.set_hl(0x8000);cpu.pc=labels['audio_enqueue_six'];cpu.push(0x5F00)
            for _ in range(boundary):cpu.step()
            interrupted=cpu.pc
            cpu.push(interrupted);cpu.pc=labels['audio_tick']
            while cpu.pc!=interrupted:cpu.step()
            while cpu.pc!=0x5F00:cpu.step()
            while cpu.read8(labels['audio_enabled']):run(cpu,labels,'audio_tick')
            self.assertEqual(bytes(cpu.ay[:11]),audio.registers(frames[-1]))
            self.assertEqual(word_at(cpu,labels,'audio_ticks_played'),6)
            self.assertEqual(cpu.sp,0xBFF0)


if __name__=='__main__':unittest.main()

