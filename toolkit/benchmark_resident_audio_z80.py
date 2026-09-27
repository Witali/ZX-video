"""Run every resident AY record on Z80, count CPU and verify FIFO/AY/guards.

This is a bank-local CPU measurement, not a disk or cadence simulation.
The real existing AY consumer is called once for each record. Fill includes
the fixed-RAM preservation/paging bridge; init is counted separately in its
already mapped bank. Initial AY writes restore a volume with unrelated RAM.
"""
from collections import Counter
import json
from pathlib import Path

import ay_huffman_stream
import ay_interrupt
from build_fap3_trd import sha
from build_zxv_trd import MiniAssembler
import playback_schedule
import pipelined_frame_z80 as video
import resident_audio_z80 as resident
from test_ay_interrupt import TraceCPU

ROOT = Path(__file__).parent
STOP, STACK = 0x5f00, 0xbff0
REGISTERS = ('a', 'b', 'c', 'd', 'e', 'h', 'l', 'ix', 'z', 'carry',
             'alt_a', 'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l',
             'alt_z', 'alt_carry', 'port_7ffd', 'sp')


def word(cpu, at, value=None):
    if value is None:
        return cpu.read8(at) | cpu.read8(at+1) << 8
    cpu.write8(at, value); cpu.write8(at+1, value >> 8)


class CheckedCPU(TraceCPU):
    def __init__(self):
        self.checking = False
        super().__init__(b'', b'')
        self.mode = None
        self.histogram = Counter()
        self.timing_histogram = Counter()
        self.published = 0
        self.payload_reads = []
        self.irq_count = 0

    def read8(self, at):
        if self.checking and at >= resident.ORIGIN:
            if self.port_7ffd & 7 != 4 or not resident.ORIGIN <= at < self.image_end:
                raise AssertionError(('unloaded audio read', at, self.pc))
            if self.payload <= at < self.image_end:
                self.payload_reads.append(at)
        return super().read8(at)

    def write8(self, at, value):
        if self.checking and self.mode in ('init', 'fill'):
            if at >= resident.ORIGIN:
                if self.port_7ffd & 7 != 4 or not self.labels['state'] <= at < self.labels['state_end']:
                    raise AssertionError(('immutable bank write', at, self.pc))
            elif ay_interrupt.QUEUE_BASE <= at < ay_interrupt.QUEUE_BASE+1024:
                index = self.read8(self.audio['audio_write_index'])
                slot = ay_interrupt.QUEUE_BASE+index*32
                if (self.mode != 'fill' or not slot <= at < slot+23 or
                        (index+1)&31 == self.read8(self.audio['audio_read_index'])):
                    raise AssertionError(('invalid FIFO write', at, self.pc))
            elif at == self.audio['audio_write_index'] and self.mode == 'fill':
                before = self.read8(at)
                if value != (before+1)&31:
                    raise AssertionError('invalid publication index')
                start = ay_interrupt.QUEUE_BASE+before*32
                record = bytes(self.read8(start+i) for i in range(1+2*self.read8(start)))
                if self.published >= len(self.records) or record != self.records[self.published]:
                    raise AssertionError(('partial or incorrect publication', self.published, record.hex()))
                self.published += 1
            elif not (0xbfa0 <= at < STACK or at in self.audio_variables or at in self.extra_mutable):
                raise AssertionError(('unexpected fixed-RAM write', at, self.pc))
        return super().write8(at, value)

    def step(self):
        pc, before = self.pc, self.tstates
        super().step()
        if self.checking and self.mode in ('init', 'fill'):
            expected = self.listing[pc]['tstates']
            if self.tstates-before not in (expected if isinstance(expected, list) else [expected]):
                raise AssertionError(('instruction timing mismatch', pc, expected, self.tstates-before))
            if self.mode == 'fill':
                self.histogram[pc] += 1
                self.timing_histogram[pc, self.tstates-before] += 1


class Harness:
    def __init__(self, blob, batch=6, *, paging=False):
        self.paging = paging
        self.initial, self.records = ay_huffman_stream.decode(blob)
        a = MiniAssembler(0xa500)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True,
                                     memory_clock=True, audio_irq=True,
                                     video_irq=video.VIDEO if paging else None)
        a.label('audio_variables')
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('audio_variables_end')
        a.label('fatal'); a.emit(0x76)
        if a.pc >= 0xb900: raise AssertionError('test AY placement overlaps clock/stack')
        self.audio = a.labels
        self.build = resident.build(blob, self.audio, batch=batch)
        self.labels = self.build['labels']
        c = self.cpu = CheckedCPU()
        # Dirty all RAM first. Only the explicit code/data sections get loaded.
        for bank in c.banks: bank[:] = b'\xa5'*16384
        c.port_7ffd, c.sp = 0x14, STACK
        for i, v in enumerate(a.resolve()): c.write8(0xa500+i, v)
        image = bytes.fromhex(self.build['image_hex'])
        for i, v in enumerate(image): c.write8(resident.ORIGIN+i, v)
        extra_listing = []
        c.extra_mutable = set()
        if paging:
            regions, _, extra_listing = video.build_video(
                dict(saved_page=0x9400,screen_base=0x9401), {}, self.audio, irq_safe_paging=True)
            for address, data in regions:
                for i, v in enumerate(data): c.write8(address+i, v)
            c.write8(video.SHADOW, c.port_7ffd)
            c.extra_mutable = {video.REQUEST_OPERAND,video.SHADOW}
            self.bridge = resident.bridge(0x9300, self.labels['fill'], page=video.PAGE, shadow=video.SHADOW)
            for i, v in enumerate(bytes.fromhex(self.bridge['code_hex'])): c.write8(0x9300+i, v)
            extra_listing = [dict(row,stage='paging') for row in extra_listing]+self.bridge['listing']
        self.run('setup_clock', self.audio, check=False)
        c.labels, c.audio = self.labels, self.audio
        c.records = self.records
        c.audio_variables = set(range(self.audio['audio_variables'], self.audio['audio_variables_end']))
        c.image_end, c.payload = resident.ORIGIN+len(image), self.build['payload_address']
        c.listing = {row['address']: row for row in self.build['listing']+extra_listing}
        c.checking = True
        self.init_tstates = self.run('init')
        if bytes(c.ay[:11]) != self.initial or c.writes != list(enumerate(self.initial)):
            raise AssertionError('initial registers not written exactly')
        c.writes.clear()
        c.write8(self.audio['audio_enabled'], int(bool(self.records)))
        self.consumed = 0
        self.expected_ay = bytearray(self.initial)

    def run(self, name, labels=None, hook=None, check=True):
        c = self.cpu
        c.pc = (labels or self.labels)[name]; c.push(STOP)
        before, steps = c.tstates, c.steps
        old_mode = c.mode
        c.mode = name if check else None
        irq_tstates = 0
        while c.pc != STOP:
            if c.pc == self.audio['fatal'] or c.steps-steps > 1000000:
                raise AssertionError('resident routine did not return')
            c.step()
            if hook and c.pc != STOP: irq_tstates += hook()
        c.mode = old_mode
        if c.sp != STACK: raise AssertionError('stack not restored')
        return c.tstates-before-irq_tstates

    def fill(self, hook=None):
        before = self.cpu.published
        elapsed = self.run('fill', hook=hook)
        if self.cpu.a != self.cpu.published-before or self.cpu.a > self.build['batch']:
            raise AssertionError('batch limit or result differs')
        return elapsed, self.cpu.a

    def fill_wrapped(self, hook=None):
        c = self.cpu
        before = {name:getattr(c,name) for name in REGISTERS}
        published = c.published
        elapsed = self.run('fill', self.bridge['labels'], hook=hook)
        after = {name:getattr(c,name) for name in REGISTERS}
        if before != after: raise AssertionError('bank wrapper corrupted caller state')
        count = c.published-published
        if count > self.build['batch']: raise AssertionError('wrapper batch exceeded')
        return elapsed, count

    def consume(self):
        c = self.cpu
        if self.consumed >= len(self.records): raise AssertionError('consume beyond EOF')
        record = self.records[self.consumed]
        expected = list(zip(record[1::2], record[2::2]))
        c.writes.clear()
        cycles = self.run('audio_tick', self.audio, check=False)
        if c.writes != expected: raise AssertionError(('AY writes differ', self.consumed))
        for reg, value in expected: self.expected_ay[reg] = value
        if bytes(c.ay[:11]) != self.expected_ay: raise AssertionError('AY state differs')
        self.consumed += 1
        if word(c, self.audio['audio_ticks_played']) != self.consumed:
            raise AssertionError('lost or duplicated tick')
        expected_cycles = (367+83*record[0] if record[0] else 377)
        if self.consumed == len(self.records): expected_cycles += 24
        if cycles != expected_cycles: raise AssertionError('existing consumer cycles differ')
        return cycles

    def interrupt(self, *, consume=True):
        """Inject the real fast IM2 ISR, preserving the interrupted instruction state."""
        c = self.cpu
        before = {name: getattr(c, name) for name in REGISTERS}
        start, pc, mode = c.tstates, c.pc, c.mode
        enabled = c.read8(self.audio['audio_enabled'])
        available = c.read8(self.audio['audio_read_index']) != c.read8(self.audio['audio_write_index'])
        if not consume and available: raise AssertionError('unexpected available record')
        expected = []
        if enabled and available:
            record = self.records[self.consumed]
            expected = list(zip(record[1::2], record[2::2]))
            routine = 367+83*record[0] if record[0] else 377
            if self.consumed+1 == len(self.records): routine += 24
        else:
            routine = 205 if enabled else 58
        c.mode = None; c.writes.clear(); c.push(pc); c.pc = 0xbdbd
        c.iff1 = False; c.tstates += 19
        while c.pc != pc: c.step()
        if before != {name: getattr(c, name) for name in REGISTERS}:
            raise AssertionError('IRQ corrupted decoder registers')
        if c.writes != expected: raise AssertionError('IRQ applied a partial or wrong record')
        for reg, value in expected: self.expected_ay[reg] = value
        if enabled and available: self.consumed += 1
        if bytes(c.ay[:11]) != self.expected_ay: raise AssertionError('IRQ AY state differs')
        if word(c, self.audio['audio_ticks_played']) != self.consumed:
            raise AssertionError('IRQ lost or duplicated tick')
        if c.tstates-start != 133+routine+(75 if self.paging else 0):
            raise AssertionError('IRQ cycle count differs')
        c.irq_count += 1
        if word(c, self.audio['elapsed_fields']) != c.irq_count or not c.iff1:
            raise AssertionError('IRQ clock differs')
        c.mode = mode
        return c.tstates-start

    def finish(self):
        c = self.cpu
        if self.consumed != len(self.records) or c.published != len(self.records):
            raise AssertionError('incomplete record coverage')
        bank = c.banks[4]
        def state_word(name):
            at = self.labels[name]-resident.ORIGIN
            return bank[at] | bank[at+1]<<8
        if state_word('remaining') or word(c, self.audio['audio_remaining']):
            raise AssertionError('remaining records at EOF')
        if c.read8(self.audio['audio_enabled']): raise AssertionError('AY still enabled at EOF')
        source = state_word('source')
        buffer = bank[self.labels['bit_buffer']-resident.ORIGIN]
        if not buffer: raise AssertionError('lost bit sentinel')
        unread = 7-((buffer & -buffer).bit_length()-1)
        consumed_bits = ((source-self.build['payload_address'])&65535)*8-unread
        if consumed_bits != self.build['input_bits'] or source != self.build['payload_end']&65535:
            raise AssertionError('input cursor/bit consumption differs')
        expected_reads = list(range(self.build['payload_address'], self.build['payload_end']))
        if c.payload_reads != expected_reads: raise AssertionError('payload read more than once or out of bounds')
        if c.sp != STACK or c.min_sp < 0xbfa0: raise AssertionError('stack bound exceeded')


def measure(blob):
    h = Harness(blob, paging=True)
    # Runtime calls are made from fixed RAM with bank 7 originally selected.
    h.cpu.port_7ffd = 0x17
    h.cpu.write8(video.SHADOW, 0x17)
    calls, consumer, sums = [], 0, []
    for start in range(0, len(h.records), h.build['batch']):
        elapsed, emitted = h.fill_wrapped()
        if emitted != min(h.build['batch'], len(h.records)-start):
            raise AssertionError('batch failed without backpressure')
        calls.append(elapsed)
        for _ in range(emitted): consumer += h.consume()
    h.finish()
    if word(h.cpu, h.audio['audio_underruns']): raise AssertionError('unexpected manual-drain underrun')
    instructions = [dict(h.cpu.listing[pc], executions=count)
                    for pc, count in sorted(h.cpu.histogram.items())]
    stages = Counter()
    dynamic_counts = []
    for (pc,ticks), count in sorted(h.cpu.timing_histogram.items()):
        stages[h.cpu.listing[pc]['stage']] += ticks*count
        dynamic_counts.append(dict(address=pc,tstates=ticks,executions=count))
    if sum(stages.values()) != sum(calls): raise AssertionError('stage timing differs')
    # The branch instruction cost depends on direction. Save aggregate dynamic
    # timing separately; all individual execution costs were checked above.
    for start in range(0, len(h.records), 6):
        group = h.records[start:start+6]
        if len(group) != 6: raise ValueError('baseline requires complete six-record frame groups')
        sums.append(1705+42*sum(record[0] for record in group))
    writes = sum(r[0] for r in h.records)
    payload = resident.tables(blob)[3]
    ones = sum(v.bit_count() for v in payload)  # Final padding is validated zero.
    formula = 109*len(calls)+789*len(h.records)+137*writes+71*h.build['input_bits']+17*ones+32*len(payload)
    wrapper_cost = h.bridge['overhead_tstates']*len(calls)
    if sum(calls) != formula+wrapper_cost: raise AssertionError('independent instruction formula differs')
    return dict(build={k: v for k, v in h.build.items() if k not in ('image_hex', 'listing')},
        bridge={k:v for k,v in h.bridge.items() if k not in ('code_hex','listing')},
        records=len(h.records), register_writes=sum(r[0] for r in h.records),
        raw_sha256=sha(b''.join(h.records)), initial_registers=h.initial.hex(),
        init_tstates=h.init_tstates, fill_tstates=sum(calls), old_enqueue_tstates=sum(sums),
        bank_local_fill_tstates=formula, wrapper_tstates=wrapper_cost,
        stage_tstates=dict(stages), coded_one_bits=ones, formula_matches=True,
        delta_producer_tstates=sum(calls)-sum(sums), fill_calls=len(calls),
        fill_call_min_tstates=min(calls), fill_call_max_tstates=max(calls),
        existing_consumer_tstates=consumer, fill_call_tstates=calls,
        instructions=instructions, dynamic_instruction_counts=dynamic_counts,
        max_stack_bytes=STACK-h.cpu.min_sp,
        all_instruction_timings_checked=True, all_records_and_ay_exact=True,
        all_payload_bytes_read_once=True, guarded_writes=True)


def main():
    source = ROOT/'resident_audio_probe.json'
    report = json.loads(source.read_bytes())
    volumes = []
    for row in report['volumes']:
        blob = bytes.fromhex(row['coded_hex'])
        if sha(blob) != row['coded_sha256']: raise ValueError('source AY bytes changed')
        result = dict(part=row['part'], **measure(blob))
        if result['raw_sha256'] != row['raw_sha256']: raise AssertionError('decoded source hash differs')
        volumes.append(result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('build','bridge','instructions','dynamic_instruction_counts','fill_call_tstates')}), flush=True)
        print(json.dumps({k:v for k,v in result['build'].items() if k not in ('labels','clobbers')}), flush=True)
    names = ('resident_audio_z80.py', 'benchmark_resident_audio_z80.py',
             'test_resident_audio_z80.py', 'ay_huffman_stream.py', 'ay_interrupt.py',
             'playback_schedule.py', 'pipelined_frame_z80.py', 'test_ay_interrupt.py',
             'build_zxv_trd.py', 'validate_fast_sparse.py', 'validate_streaming_player.py')
    result = dict(complete=True, release=False, scope=__doc__, baseline_commit='1cdb5f1',
        volumes=volumes, records=sum(v['records'] for v in volumes),
        fill_tstates=sum(v['fill_tstates'] for v in volumes),
        old_enqueue_tstates=sum(v['old_enqueue_tstates'] for v in volumes),
        delta_producer_tstates=sum(v['delta_producer_tstates'] for v in volumes),
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names},
        reference_sha256={source.name:sha(source.read_bytes())},
        new_trds_built=False, full_cadence_verified=False, paging_wrapper_measured=True,
        warning='Manual FIFO consumption is not 50-Hz cadence. Fill includes all-register preservation and two paging calls, excludes outer CALL, IRQ/ULA, video integration, ROM and disk latency. Fixed-RAM wrapper test placement is not an integrated allocation.')
    (ROOT/'resident_audio_z80.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__': main()
