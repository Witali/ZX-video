"""70908-T IM2 fixture. Ideal disk producer, no ULA or ROM latency.

HALT waits advance to the next field; EI defers IRQ for one instruction.
IRQ executes real code and verifies preservation of foreground registers.
"""
import ay_interrupt
import frame_clock_z80
import frame_stream_harness
from benchmark_context_huffman import word
from validate_fast_sparse import CPU

FIELD = 70908


class ClockCPU(frame_stream_harness.FrameStreamCPU):
    def write8(self, address, value):
        if (self.guarding and self.phase == 'schedule' and self.port_7ffd & 7 == 7
                and self.clock_state <= address < self.clock_end):
            return CPU.write8(self,address,value)
        return super().write8(address,value)


class Clock:
    def __init__(self, harness, expected_ticks, *, lookahead=False):
        self.h, self.expected = harness, expected_ticks
        cpu = harness.cpu
        # A single clock fixture owns this CPU for the remainder of the run.
        cpu.__class__ = ClockCPU
        code, self.labels, listing = frame_clock_z80.build(harness.p,harness.audio,zx0=harness.z,lookahead=lookahead)
        cpu.guarding = False
        for i,value in enumerate(code): cpu.write8(frame_clock_z80.CODE+i,value)
        cpu.clock_state, cpu.clock_end = self.labels['state'], self.labels['end']
        harness.instructions.update({row['address']:row for row in listing})
        self.code, self.listing = code, listing
        self.next_field = cpu.tstates+FIELD
        self.halts, self.ticks, self.irq_tstates, self.idle_tstates = cpu.halts, 0, 0, 0
        self.publications = []
        self.publish_pc = next(row['address'] for row in harness.instructions.values()
            if row['phase'] == 'handoff' and row['address'] >= harness.frame.w['publish']
            and row['instruction'] == 'OUT (C),A')
        self.saved = ('a','b','c','d','e','h','l','ix','z','carry','alt_a','alt_b',
            'alt_c','alt_d','alt_e','alt_h','alt_l','alt_z','alt_carry','port_7ffd','sp')

    def interrupt(self,cpu):
        idle = irq = 0
        if cpu.last_instruction == self.publish_pc:
            pos = self.labels['late_fields']-0xc000
            late = cpu.banks[7][pos] | cpu.banks[7][pos+1] << 8
            self.publications.append(dict(tstates=cpu.tstates,fields=word(cpu,self.h.audio['elapsed_fields']),
                audio_ticks=self.ticks,late_fields=late))
        halted = cpu.halts != self.halts; self.halts = cpu.halts
        if halted:
            if not cpu.iff1: raise AssertionError('HALT with disabled interrupts')
            idle = max(0,self.next_field-cpu.tstates); cpu.tstates += idle
        # EI itself cannot accept an interrupt; the following instruction can.
        ei = CPU.read8(cpu,cpu.last_instruction) == 0xfb
        if cpu.tstates >= self.next_field and cpu.iff1 and not ei:
            if cpu.tstates-self.next_field >= FIELD: raise AssertionError('missed an entire IRQ field')
            self.next_field += FIELD
            cpu.guarding = False
            enabled = cpu.read8(self.h.audio['audio_enabled'])
            wanted = bytearray(cpu.ay)
            if enabled:
                if self.ticks >= len(self.expected): raise AssertionError('unexpected audio tick')
                if cpu.read8(self.h.audio['audio_read_index']) == cpu.read8(self.h.audio['audio_write_index']):
                    raise AssertionError(('scheduled AY underrun',self.ticks))
                tick = self.expected[self.ticks]
                slot = ay_interrupt.QUEUE_BASE+32*cpu.read8(self.h.audio['audio_read_index'])
                if bytes(cpu.read8(slot+i) for i in range(len(tick))) != tick:
                    raise AssertionError(('scheduled AY queue differs',self.ticks))
                for i in range(tick[0]): wanted[tick[1+2*i]] = tick[2+2*i]
            before = {name:getattr(cpu,name) for name in self.saved}
            pc, start = cpu.pc, cpu.tstates
            cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != pc: cpu.step()
            irq = cpu.tstates-start
            if {name:getattr(cpu,name) for name in self.saved} != before:
                raise AssertionError('IRQ corrupted foreground state')
            if bytes(cpu.ay) != wanted or word(cpu,self.h.audio['audio_underruns']):
                raise AssertionError('scheduled AY output or underrun')
            if enabled: self.ticks += 1
            cpu.guarding = True
        self.irq_tstates += irq; self.idle_tstates += idle
        return dict(irq=irq,idle=idle)

    def start(self):
        return self.h.execute(self.labels['start'],interrupt=self.interrupt)

    def play_one(self):
        return self.h.execute(self.labels['play_one'],interrupt=self.interrupt)

    def drain(self):
        return self.h.execute(self.h.audio['audio_drain'],interrupt=self.interrupt)
