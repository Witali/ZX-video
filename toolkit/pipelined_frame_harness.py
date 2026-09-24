"""Instruction-level IM2 fixture for compact lookahead and IRQ publication.

Ideal 64-KiB ring producer. No ULA, TR-DOS ROM or physical disk timing.
The observer only checks RAM/ports; it never supplies decoded frame bytes.
"""
from collections import Counter

import ay_interrupt
import banked_zx0
import frame_stream_harness
import pipelined_frame_z80 as machine
import stream_reader_harness as stream
from benchmark_context_huffman import word
from frame_clock_harness import FIELD
from validate_fast_sparse import CPU


class PipelineClockCPU(frame_stream_harness.FrameStreamCPU):
    irq_active=False

    def write8(self,address,value):
        if self.guarding and self.irq_active:
            if not (self.audio_state<=address<self.audio_end
                    or machine.STATE<=address<machine.STATE_END
                    or address in self.irq_draw_state
                    or address==self.z_labels['history_page']
                    or stream.STACK-96<=address<stream.STACK
                    or banked_zx0.STACK_BOTTOM<=address<banked_zx0.STACK_TOP):
                raise AssertionError(f'IRQ write outside contract {address:04x}')
            return CPU.write8(self,address,value)
        if self.guarding and self.phase=='schedule':
            if (self.clock_state<=address<self.clock_end and self.port_7ffd&7==7
                    or machine.STATE<=address<machine.STATE_END
                    or address==self.audio_enabled_address):
                return CPU.write8(self,address,value)
        if self.guarding and self.phase=='output':
            screen_bank = (5 if 0x4000<=address<0x5b00 else
                7 if 0xc000<=address<0xdb00 and self.port_7ffd&7==7 else None)
            if screen_bank==(7 if self.port_7ffd&8 else 5):
                raise AssertionError('native output wrote the visible screen')
        return super().write8(address,value)


class Clock:
    def __init__(self,harness,expected_ticks,*,lookahead=False,observer=None,record_underruns=False):
        if harness.video is None: raise ValueError('pipelined harness required')
        self.h,self.expected,self.observer=harness,expected_ticks,observer
        self.record_underruns,self.underruns=record_underruns,[]
        cpu=harness.cpu; cpu.__class__=PipelineClockCPU; cpu.guarding=False
        self.code,self.labels,self.listing=machine.build_clock(harness.p,harness.audio,harness.frames,
            zx0=harness.z,progress_entry=harness.progress['tick'] if harness.progress else None,lookahead=lookahead,
            packet_ahead=harness.packet_ahead)
        for i,value in enumerate(self.code): cpu.write8(machine.CODE+i,value)
        harness.regions.append((machine.CODE,self.code))
        harness.instructions.update({r['address']:r for r in self.listing})
        cpu.clock_state,cpu.clock_end=self.labels['state'],self.labels['end']
        cpu.audio_enabled_address=harness.audio['audio_enabled']
        cpu.irq_draw_state={harness.frame.draw[n] for n in ('saved_page','screen_base')}
        self.next_field=cpu.tstates+FIELD
        self.halts,self.ticks,self.irq_tstates,self.idle_tstates=cpu.halts,0,0,0
        self.publications=[]; self.events=[]; self.irq_histogram=Counter()
        self.saved=('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_b',
            'alt_c','alt_d','alt_e','alt_h','alt_l','alt_z','alt_carry','sp')
        self.event_pc={r['address']:event for event,name in
            (('compact','RET (compact ready)'),('native','RET (prepared screen)'))
            for r in harness.instructions.values() if r['instruction']==name}
        if harness.packet_ahead: self.event_pc[harness.p['packet_ready']]='packet'

    def event(self,kind):
        cpu=self.h.cpu
        event=dict(kind=kind,tstates=cpu.tstates,fields=word(cpu,self.h.audio['elapsed_fields']),
            phase=cpu.phase,bank=7 if cpu.port_7ffd&8 else 5)
        self.events.append(event)
        if self.observer: self.observer(kind,self)

    def run_irq(self):
        cpu=self.h.cpu; h=self.h
        enabled=cpu.read8(h.audio['audio_enabled']); wanted=bytearray(cpu.ay)
        empty=enabled and cpu.read8(h.audio['audio_read_index'])==cpu.read8(h.audio['audio_write_index'])
        if empty:
            if not self.record_underruns: raise AssertionError(('scheduled AY underrun',self.ticks))
            self.underruns.append(dict(tstates=cpu.tstates,after_audio_ticks=self.ticks))
        if enabled and not empty:
            if self.ticks>=len(self.expected): raise AssertionError('unexpected audio tick')
            tick=self.expected[self.ticks]; slot=ay_interrupt.QUEUE_BASE+32*cpu.read8(h.audio['audio_read_index'])
            if bytes(cpu.read8(slot+i) for i in range(len(tick)))!=tick:
                raise AssertionError(('scheduled AY queue differs',self.ticks))
            for i in range(tick[0]): wanted[tick[1+2*i]]=tick[2+2*i]
        before={n:getattr(cpu,n) for n in self.saved}; page=cpu.port_7ffd
        if cpu.read8(machine.SHADOW)!=page: raise AssertionError('stale paging shadow before IRQ')
        pc,start=cpu.pc,cpu.tstates; cpu.irq_active=True
        cpu.push(pc); cpu.pc=0xbdbd; cpu.iff1=False; cpu.tstates+=19
        while cpu.pc!=pc:
            at,t=cpu.pc,cpu.tstates
            if not (0x9400<=at<h.audio['state'] or 0xbd00<=at<0xbdc0
                    or machine.VIDEO<=at<h.video['video_end'] or at==0x3d2f):
                raise AssertionError(f'IRQ executed unexpected code {at:04x}')
            cpu.step(); elapsed=cpu.tstates-t; self.irq_histogram[at,elapsed]+=1
            row=h.instructions.get(at)
            if row and elapsed!=row['tstates']: raise AssertionError(('video IRQ timing',row,elapsed))
            if at==h.video['publish_out']:
                self.publications.append(dict(tstates=cpu.tstates,fields=word(cpu,h.audio['elapsed_fields']),
                    audio_ticks=self.ticks,late_fields=word(cpu,machine.LATE),
                    interrupt_entry_tstates=start,interrupted_pc=pc,interrupted_phase=cpu.phase,
                    interrupted_bank=page&7))
                self.event('publish')
        cpu.irq_active=False
        if ({n:getattr(cpu,n) for n in self.saved}!=before or (cpu.port_7ffd^page)&~8
                or cpu.read8(machine.SHADOW)!=cpu.port_7ffd):
            raise AssertionError('IRQ corrupted foreground registers/bank/shadow')
        if bytes(cpu.ay)!=wanted or (word(cpu,h.audio['audio_underruns']) and not self.record_underruns):
            raise AssertionError('scheduled AY output or underrun')
        if enabled and not empty: self.ticks+=1
        return cpu.tstates-start

    def interrupt(self,cpu):
        if cpu.last_instruction in self.event_pc: self.event(self.event_pc[cpu.last_instruction])
        idle=irq=0
        halted=cpu.halts!=self.halts; self.halts=cpu.halts
        if halted:
            if not cpu.iff1: raise AssertionError('HALT with disabled interrupts')
            idle=max(0,self.next_field-cpu.tstates); cpu.tstates+=idle
        ei=CPU.read8(cpu,cpu.last_instruction)==0xfb
        if cpu.tstates>=self.next_field and cpu.iff1 and not ei:
            if cpu.tstates-self.next_field>=FIELD: raise AssertionError('missed an entire IRQ field')
            self.next_field+=FIELD
            irq=self.run_irq()
        self.irq_tstates+=irq; self.idle_tstates+=idle
        return dict(irq=irq,idle=idle)

    def prime(self): return self.h.execute(self.labels['prime'],interrupt=self.interrupt)
    def start(self): return self.h.execute(self.labels['start'],interrupt=self.interrupt)
    def play_one(self): return self.h.execute(self.labels['play_one'],interrupt=self.interrupt)
    def drain(self): return self.h.execute(self.h.audio['audio_drain'],interrupt=self.interrupt)
