"""Strict CPU fixture for continuous stream input; ring supply has zero cost.

The host preloads 64 KiB and replaces each consumed 256-byte segment with
the next raw ring bytes. It does not parse headers or feed decoded bytes.
This is an ideal producer for CPU/memory verification, not a disk schedule.
"""
from collections import Counter

import banked_zx0 as zx0
import stream_reader_z80 as reader
from benchmark_compact_screen import NativeCPU
from benchmark_context_huffman import word
from validate_fast_sparse import CPU

STACK, STOP, DESTINATION, WINDOW_END = 0x9df0, 0x93f0, 0xa6a0, 0xb900


class StreamCPU(NativeCPU):
    def read8(self, address):
        if self.guarding:
            bank = self.port_7ffd & 7
            if address >= 0xc000 and bank in zx0.BANKS:
                position = zx0.BANKS.index(bank)*16384+address-0xc000
                wanted = (self.ring_start+self.consumed) % 65536
                if position != wanted or self.consumed >= len(self.ring_data):
                    raise AssertionError('ring overread or out-of-order consumption')
                value = CPU.read8(self, address)
                if value != self.ring_data[self.consumed]:
                    raise AssertionError('ring bytes differ')
                self.consumed += 1
                if self.consumed % 256 == 0:
                    for offset in range(self.consumed-256, self.consumed):
                        following = offset+65536
                        if following < len(self.ring_data):
                            slot = (self.ring_start+offset) % 65536
                            region, index = divmod(slot, 16384)
                            self.banks[zx0.BANKS[region]][index] = self.ring_data[following]
                return value
            if zx0.INPUT <= address < zx0.INPUT+256:
                if address >= zx0.INPUT+word(self, self.z_labels['valid']):
                    raise AssertionError('fixed input window overread')
            if address >= zx0.OUTPUT and bank == 7:
                if address >= zx0.OUTPUT+self.produced:
                    raise AssertionError('unproduced history read')
        return CPU.read8(self, address)

    def write8(self, address, value):
        if self.guarding:
            bank = self.port_7ffd & 7
            history = bank == 7 and address >= zx0.OUTPUT
            if history:
                if address != zx0.OUTPUT+self.produced or self.produced >= word(self, self.z_labels['block_length']):
                    raise AssertionError('nonsequential or excessive history output')
                self.produced += 1
            allowed = (history or zx0.STACK_BOTTOM <= address < zx0.STACK_TOP
                or STACK-96 <= address < STACK or zx0.INPUT <= address < zx0.INPUT+256
                or self.z_labels['state'] <= address < self.z_labels['ring_banks'] or address in self.patches
                or bank == 7 and self.r_labels['state'] <= address < self.r_labels['end']
                or self.dest_first <= address < self.dest_end)
            if not allowed:
                raise AssertionError(f'stream write outside contract: {address:04x}, bank {bank}')
        return CPU.write8(self, address, value)


class Harness:
    def __init__(self, stream, *, ring_start=0xfff0, page=0x17,token_boundaries=False,page_entry=None,
                 unrolled_copy=False,disk_refill_entry=None):
        if page not in (0x17, 0x1f): raise ValueError('bank 7 required')
        zcode, self.z = zx0.build(fast_literal=True, fast_refill=True,token_boundaries=token_boundaries,page_entry=page_entry,
            disk_refill_entry=disk_refill_entry)
        rcode, loader, self.r, listing = reader.build(self.z,unrolled_copy=unrolled_copy)
        cpu = self.cpu = StreamCPU(b'', b'')
        for bank in cpu.banks: bank[:] = b'\xa5'*16384
        cpu.z_labels, cpu.r_labels = self.z, self.r
        cpu.port_7ffd = page
        for base, blob in ((zx0.CODE, zcode), (reader.CODE, rcode), (reader.LOADER, loader)):
            for i, value in enumerate(blob): cpu.write8(base+i, value)
        self.regions = [(zx0.CODE, zcode), (reader.CODE, rcode), (reader.LOADER, loader)]
        cpu.patches = {self.z['slice_high_operand'], self.z['slice_low_operand'],
                       self.z['dzx0t_last_offset']+1, self.z['dzx0t_last_offset']+2}
        if token_boundaries: cpu.patches.add(self.z['slice_equal_branch'])
        if unrolled_copy: cpu.patches.add(self.r['copy_jump_operand'])
        cpu.ring_data, cpu.ring_start, cpu.consumed = stream, ring_start % 65536, 0
        cpu.produced, cpu.dest_first, cpu.dest_end = 0, DESTINATION, DESTINATION
        for i, value in enumerate(stream[:65536]):
            region, index = divmod((cpu.ring_start+i) % 65536, 16384)
            cpu.banks[zx0.BANKS[region]][index] = value
        region, offset = divmod(cpu.ring_start, 16384)
        word(cpu, self.z['ring_pointer'], 0xc000+offset)
        cpu.write8(self.z['ring_region'], region); cpu.write8(self.z['history_page'], page)
        self.instructions = {r['address']: r for r in listing}
        self.histogram, self.rows = Counter(), []
        self.blocks = 0

    def execute(self, entry, *, interrupt=None):
        cpu = self.cpu; cpu.guarding = False
        cpu.pc, cpu.sp = entry, STACK; cpu.push(STOP)
        before, irq, steps = cpu.tstates, 0, cpu.steps
        stages = Counter(); cpu.guarding = True
        while cpu.pc != STOP:
            pc, ticks = cpu.pc, cpu.tstates
            if pc == self.z['fatal']: raise AssertionError('invalid block header or ZX0')
            if pc == self.z['begin']: cpu.produced = 0; self.blocks += 1
            cpu.step()
            elapsed = cpu.tstates-ticks
            if pc in self.instructions:
                allowed = self.instructions[pc]['tstates']
                if elapsed not in (allowed if isinstance(allowed, list) else [allowed]):
                    raise AssertionError('reader instruction timing differs')
                stage = 'reader'
            else:
                if not zx0.CODE <= pc < self.z['state']:
                    raise AssertionError(f'unknown executed code: {pc:04x}')
                stage = 'banked_zx0'
            stages[stage] += elapsed; self.histogram[pc, elapsed] += 1
            if cpu.steps-steps > 3000000: raise AssertionError('reader failed to return')
            if interrupt and cpu.pc != STOP: irq += interrupt(cpu)
        cpu.guarding = False
        if cpu.sp != STACK or cpu.port_7ffd & 7 != 7 or cpu.tstates-before-irq != sum(stages.values()):
            raise AssertionError('reader stack/paging/timing differs')
        return dict(tstates=sum(stages.values()), irq_tstates=irq, stages=dict(stages))

    def take(self, count, *, interrupt=None):
        if not 0 <= count <= WINDOW_END-DESTINATION: raise ValueError('request exceeds fixed output window')
        cpu = self.cpu
        cpu.dest_first, cpu.dest_end = DESTINATION, DESTINATION+count
        cpu.set_bc(count); cpu.set_de(DESTINATION)
        result = self.execute(self.r['take'], interrupt=interrupt)
        if cpu.de() != DESTINATION+count: raise AssertionError('wrong destination cursor')
        self.rows.append(dict(count=count, **result))
        if bytes(cpu.banks[5][:0x3800]) != b'\xa5'*0x3800 or bytes(cpu.banks[6]) != b'\xa5'*16384 or bytes(cpu.banks[7][:6912]) != b'\xa5'*6912:
            raise AssertionError('screen/frame/tables overwritten')
        return bytes(cpu.read8(DESTINATION+i) for i in range(count))
