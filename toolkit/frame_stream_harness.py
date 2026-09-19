"""One RAM/CPU fixture for FAP1, banked ZX0, reconstruction, screen and AY.

Host installs startup tables and an ideal raw-ring producer. Per-frame
headers, lengths, maps, audio and values are all read by Z80 instructions.
Manual AY draining here verifies data, not a 50-Hz delivery schedule.
"""
from collections import Counter

import ay_interrupt
import banked_zx0
import frame_metadata_z80
import frame_output_pipeline as pipeline
import frame_stream_z80 as packet
import playback_schedule
import stream_reader_harness as stream
from build_zxv_trd import MiniAssembler
from benchmark_context_huffman import word
from validate_fast_sparse import CPU


class FrameStreamCPU(stream.StreamCPU):
    def read8(self, address):
        if (self.guarding and self.bulk and self.phase in ('packet','audio')
                and pipeline.INPUT <= address < pipeline.INPUT_END and address >= self.packet_end):
            raise AssertionError(f'bulk packet overread {address:04x}')
        if (self.guarding and self.phase in ('metadata', 'reconstruct')
                and pipeline.INPUT <= address < pipeline.INPUT_END and address >= self.input_end):
            raise AssertionError(f'packet value overread {address:04x}')
        return super().read8(address)

    def write8(self, address, value):
        if self.guarding:
            if self.phase in ('metadata', 'reconstruct', 'output', 'handoff'):
                return pipeline.PipelineCPU.write8(self, address, value)
            if self.phase == 'packet':
                allowed = (packet.HEADER <= address < packet.HEADER+7
                    or self.p_labels['state'] <= address < self.p_labels['end'] and self.port_7ffd & 7 == 7
                    or any(lo <= address < hi for lo,hi in self.wrapper_state)
                    or pipeline.INPUT <= address < self.input_end
                    or address == self.z_labels['history_page'])
                if self.bulk:
                    allowed |= (pipeline.VECTORS <= address < pipeline.VECTORS+192
                        or pipeline.MAP <= address < pipeline.MAP+80
                        or packet.CACHE_MAP <= address < packet.CACHE_MAP+3)
                if allowed: return CPU.write8(self, address, value)
            if self.phase == 'audio':
                if (ay_interrupt.QUEUE_BASE <= address < ay_interrupt.QUEUE_BASE+1024
                        or self.audio_state <= address < self.audio_end):
                    return CPU.write8(self, address, value)
        return super().write8(address, value)


class Harness:
    def __init__(self, ring, tables, mapping, frames, *, ring_start=0xfff0, bulk=False, zero_copy=False):
        if zero_copy and not bulk: raise ValueError('zero-copy metadata requires bulk packets')
        self.bulk = bulk
        f = self.frame = pipeline.Harness(tables, mapping, raw_attributes=True, decode_metadata=True,
            fast_mask_dispatch=True, selective_cache=True, deferred_publish=True,dynamic_source=bulk,
            dynamic_metadata=zero_copy)
        s = stream.Harness(ring, ring_start=ring_start)
        self.z, self.r, self.blocks = s.z, s.r, 0
        cpu = self.cpu = FrameStreamCPU(b'', b'')
        cpu.__dict__.update(f.cpu.__dict__); cpu.guarding = False
        cpu.bulk, cpu.packet_end = bulk, pipeline.INPUT_END
        for name in ('z_labels','r_labels','patches','ring_data','ring_start','consumed','produced','dest_first','dest_end'):
            setattr(cpu, name, getattr(s.cpu, name))
        for bank in banked_zx0.BANKS: cpu.banks[bank][:] = s.cpu.banks[bank]
        cpu.port_7ffd = 0x17
        for base, blob in s.regions:
            for i, value in enumerate(blob): cpu.write8(base+i, value)
        for name in ('ring_pointer',): word(cpu, self.z[name], word(s.cpu, self.z[name]))
        for name in ('ring_region','history_page'): cpu.write8(self.z[name], s.cpu.read8(self.z[name]))
        a = MiniAssembler(0x9400)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True, memory_clock=True, audio_irq=True)
        a.label('state'); ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76); a.label('end')
        self.audio, audio_code = dict(a.labels), a.resolve()
        if a.pc > 0x9800: raise ValueError('AY overlaps motion tables')
        if bulk:
            import bulk_frame_z80 as builder
        else:
            builder = packet
        code, bridge, self.p, listing = builder.build(self.z, self.r, f.w, f.draw, f.metadata_labels, self.audio)
        cpu.p_labels = self.p; cpu.audio_state, cpu.audio_end = self.audio['state'], self.audio['end']
        cpu.wrapper_state = [(f.w['state'], f.w['end'])]
        self.regions = s.regions+[(packet.CODE, code), (packet.BRIDGE, bridge), (0x9400, audio_code)]
        for base, blob in self.regions[3:]:
            for i, value in enumerate(blob): cpu.write8(base+i, value)
        self.instructions = dict(f.instructions)
        self.instructions.update({pc:dict(row, phase='stream_input') for pc,row in s.instructions.items()})
        self.instructions.update({row['address']:dict(row, phase='packet') for row in listing})
        self.histogram, self.rows = Counter(), []
        cpu.set_hl(frames)
        self.initialize(self.audio['audio_init']); self.initialize(self.audio['setup_clock'])
        self.frames, self.index = frames, 0
        self.expected_screens = {5: bytes(6912), 7: bytes(6912)}
        cpu.input_end = pipeline.INPUT_END

    def initialize(self, entry):
        cpu = self.cpu; cpu.guarding = False
        cpu.pc, cpu.sp = entry, stream.STACK; cpu.push(stream.STOP)
        while cpu.pc != stream.STOP:
            if cpu.pc == self.audio['fatal']: raise AssertionError('startup fatal')
            cpu.step()
        if cpu.sp != stream.STACK: raise AssertionError('startup stack')

    def execute(self, entry, *, interrupt=None):
        cpu = self.cpu; cpu.guarding = False
        cpu.pc, cpu.sp = entry, stream.STACK; cpu.push(stream.STOP)
        start, irq, idle, steps = cpu.tstates, 0, 0, cpu.steps
        stages, pages = Counter(), []
        cpu.guarding = True
        while cpu.pc != stream.STOP:
            pc, ticks, page = cpu.pc, cpu.tstates, cpu.port_7ffd
            if pc in (self.z['fatal'], self.audio['fatal']): raise AssertionError(f'packet fatal {pc:04x}')
            if pc == self.z['begin']: cpu.produced = 0; self.blocks += 1
            if pc == self.r['take']:
                first, last = cpu.de(), cpu.de()+cpu.bc()
                regions = ((pipeline.INPUT, pipeline.INPUT_END), (pipeline.MAP, pipeline.MAP+80),
                    (pipeline.VECTORS, pipeline.VECTORS+192), (packet.CACHE_MAP, packet.CACHE_MAP+3),
                    (packet.HEADER, packet.HEADER+7))
                if self.bulk: regions += ((0xba58,0xba5a),)
                if not any(lo <= first <= last <= hi for lo,hi in regions):
                    raise AssertionError(f'invalid stream destination {first:04x}..{last:04x}')
                cpu.dest_first, cpu.dest_end = first, last
            if pc == self.frame.metadata_labels['decode']:
                cpu.input_end = cpu.hl()+word(cpu, packet.HEADER+1)
            if self.bulk and pc == self.audio['audio_enqueue_six']:
                cpu.packet_end = word(cpu,self.p['payload_end'])
            if pc == self.frame.w['run']:
                cpu.input_end = (cpu.packet_end if self.bulk else
                    pipeline.INPUT+word(cpu,packet.HEADER+3)+word(cpu,packet.HEADER+5)+2)
            if pc == self.frame.draw['draw']:
                cpu.target_bank = 7 if cpu.a == 0xc0 else 5
            row = self.instructions.get(pc)
            if row:
                phase = row['phase']
            elif banked_zx0.CODE <= pc < self.z['state']: phase = 'banked_zx0'
            elif 0x9400 <= pc < self.audio['state']: phase = 'audio'
            else: raise AssertionError(f'unknown instruction {pc:04x}, page {page:02x}')
            cpu.phase = phase
            # Parser's zero guard writes are constrained by the actual header.
            if phase == 'packet':
                cpu.input_end = pipeline.INPUT_END
            cpu.last_instruction = pc
            cpu.step(); elapsed = cpu.tstates-ticks
            if row:
                wanted = row['tstates']
                if elapsed not in (wanted if isinstance(wanted,list) else [wanted]):
                    raise AssertionError(('instruction timing', row, elapsed))
            stages[phase] += elapsed; self.histogram[pc,elapsed] += 1
            if page != cpu.port_7ffd: pages.append(cpu.port_7ffd)
            if cpu.steps-steps > 2000000: raise AssertionError('packet failed to return')
            if interrupt and cpu.pc != stream.STOP:
                injected = interrupt(cpu)
                if isinstance(injected, dict):
                    irq += injected['irq']; idle += injected['idle']
                else: irq += injected
        cpu.guarding = False
        if cpu.sp != stream.STACK or cpu.port_7ffd & 7 != 7 or sum(stages.values()) != cpu.tstates-start-irq-idle:
            raise AssertionError('combined stack/paging/timing differs')
        return dict(tstates=sum(stages.values()), stages=dict(stages), irq_tstates=irq, idle_tstates=idle, page_writes=pages,
                    ring_bytes_consumed=cpu.consumed)

    def consume_header(self, expected):
        out, results = bytearray(), []
        for pos in range(0, len(expected), pipeline.INPUT_END-pipeline.INPUT):
            part = expected[pos:pos+pipeline.INPUT_END-pipeline.INPUT]
            self.cpu.set_bc(len(part)); self.cpu.set_de(pipeline.INPUT)
            results.append(self.execute(self.r['take']))
            out += bytes(self.cpu.read8(pipeline.INPUT+i) for i in range(len(part)))
        if out != expected: raise AssertionError('startup stream header differs')
        return results

    def prepare(self):
        old_page = self.cpu.port_7ffd
        front = 7 if old_page & 8 else 5
        previous = bytes(self.cpu.banks[front][:6912])
        result = self.execute(self.p['next_frame'])
        if self.cpu.port_7ffd != old_page or bytes(self.cpu.banks[front][:6912]) != previous:
            raise AssertionError('preparation changed visible screen')
        return result

    def publish(self):
        old_page = self.cpu.port_7ffd
        result = self.execute(self.p['publish_bridge'])
        if self.cpu.port_7ffd != old_page ^ 8: raise AssertionError('wrong published screen')
        return result

    def drain_six(self, expected_ticks):
        """Real ISR, manually triggered six times. Not a cadence measurement."""
        cpu = self.cpu; cpu.guarding = False
        cpu.write8(self.audio['audio_enabled'], 1)
        start = cpu.tstates
        for tick in expected_ticks:
            slot = ay_interrupt.QUEUE_BASE+32*cpu.read8(self.audio['audio_read_index'])
            if bytes(cpu.read8(slot+i) for i in range(len(tick))) != tick:
                raise AssertionError('queued AY record differs')
            before_ay = bytes(cpu.ay)
            wanted = bytearray(before_ay)
            for i in range(tick[0]): wanted[tick[1+2*i]] = tick[2+2*i]
            pc, sp = stream.STOP, cpu.sp
            cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != pc: cpu.step()
            if bytes(cpu.ay) != wanted or cpu.sp != sp or word(cpu, self.audio['audio_underruns']):
                raise AssertionError('AY output/stack/queue differs')
        return cpu.tstates-start
