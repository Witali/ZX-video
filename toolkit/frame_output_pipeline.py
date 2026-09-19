"""Run one-frame FSC1 reconstruction and cell output in one Z80/RAM instance.

CPU executes cold screen/cache clearing, frame setup, both stages, paging,
and screen publication. Host still parses/expands metadata and supplies
decompressed packets. No ZX0/AY/ROM/disk scheduling or frame pacing claim.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

import causal_tile_z80 as reconstruction
import cell_screen_z80 as output
from build_zxv_trd import MiniAssembler
from benchmark_context_huffman import word
from benchmark_compact_screen import NativeCPU, STACK, STOP
from build_long_video_trd import expand_compact_screen
from cell_output_stream import unpack
from probe_spatial_contexts import read_header, read_group, OFFSETS
from probe_motion_entropy import Reader
from probe_fast_fragments import SIZES
from probe_lossless_layouts import sha
from validate_fast_sparse import CPU

VECTORS, BITMAP, ATTRS, INPUT, INPUT_END = 0xa400, 0xa4c0, 0xa640, 0xa6a0, 0xb900
MAP, WRAPPER, INITIALIZER = 0x7300, 0x8f60, 0x7b00


def wrapper(recon, draw):
    a, listing = MiniAssembler(WRAPPER), []
    def emit(name, data, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage='handoff'))
        a.emit(*data)
    def address(name, opcode, value, ticks):
        emit(name, [opcode, value & 255, value >> 8], ticks)
    def load_a(addr): address('LD A,(nn)', 0x3a, addr, 13)
    def store_a(addr): address('LD (nn),A', 0x32, addr, 13)
    for name, value in (('vectors', VECTORS), ('bitmap_masks', BITMAP), ('attribute_masks', ATTRS), ('source', INPUT)):
        address('LD HL,'+name, 0x21, value, 10)
        address('LD ('+name+'),HL', 0x22, recon[name], 16)
    listing.append(dict(address=a.pc, instruction='LD HL,(literal_pointer)', tstates=16, stage='handoff'))
    a.abs16(0x2a, 'literal_pointer')
    address('LD (literal_source),HL', 0x22, recon['literal_source'], 16)
    emit('LD A,F0h', [0x3e, 0xf0], 7); store_a(recon['bit_page'])
    listing.append(dict(address=a.pc, instruction='LD A,(cache_flag)', tstates=13, stage='handoff'))
    a.abs16(0x3a, 'cache_flag'); store_a(recon['cache_enabled'])
    address('CALL reconstruct', 0xcd, recon['frame'], 17)
    load_a(draw['screen_base'])
    address('LD HL,native_map', 0x21, MAP, 10)
    address('CALL draw', 0xcd, draw['draw'], 17)
    a.label('publish')
    load_a(draw['saved_page']); emit('XOR 8', [0xee, 8], 7); store_a(draw['saved_page'])
    address('LD BC,7FFD', 0x01, 0x7ffd, 10)
    emit('OUT (C),A', [0xed, 0x79], 12)
    load_a(draw['screen_base']); emit('XOR 80h', [0xee, 128], 7); store_a(draw['screen_base'])
    emit('RET', [0xc9], 10)
    a.label('state')
    a.label('literal_pointer'); a.word(0)
    a.label('cache_flag'); a.emit(0)
    a.label('end')
    if a.pc > output.CODE or recon['end'] > WRAPPER:
        raise ValueError('frame wrapper overlaps generated code')
    return a.resolve(), a.labels, listing


def initializer(draw):
    a, listing = MiniAssembler(INITIALIZER), []
    def emit(name, data, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage='cold_init'))
        a.emit(*data)
    def imm(name, opcode, value, ticks):
        emit(name, [opcode, value & 255, value >> 8], ticks)
    emit('LD A,17h', [0x3e, 0x17], 7)
    imm('LD BC,7FFD', 0x01, 0x7ffd, 10); emit('OUT (C),A', [0xed, 0x79], 12)
    for address, count in ((0x4000, 6912), (0xc000, 6912), (0x6400, 5120)):
        imm('LD HL,clear_start', 0x21, address, 10)
        imm('LD DE,clear_start+1', 0x11, address+1, 10)
        imm('LD BC,clear_length-1', 0x01, count-1, 10)
        emit('LD (HL),0', [0x36, 0], 10)
        emit('LDIR', [0xed, 0xb0], [16, 21])
    emit('LD A,16h', [0x3e, 0x16], 7)
    imm('LD (saved_page),A', 0x32, draw['saved_page'], 13)
    imm('LD BC,7FFD', 0x01, 0x7ffd, 10); emit('OUT (C),A', [0xed, 0x79], 12)
    emit('LD A,C0h', [0x3e, 0xc0], 7)
    imm('LD (screen_base),A', 0x32, draw['screen_base'], 13)
    emit('RET', [0xc9], 10)
    return a.resolve(), listing


class PipelineCPU(NativeCPU):
    def read8(self, address):
        if self.guarding and INPUT <= address < INPUT_END and address >= self.input_end:
            raise AssertionError(f'coded input overread: {address:04x}')
        return super().read8(address)

    def write8(self, address, value):
        if self.guarding:
            screen5 = 0x4000 <= address < 0x5b00
            screen7 = 0xc000 <= address < 0xdb00 and self.port_7ffd & 7 == 7
            cold = self.phase == 'cold_init' and (screen5 or screen7 or 0x6400 <= address < 0x7800)
            pixels = self.phase == 'output' and ((self.target_bank == 5 and screen5) or (self.target_bank == 7 and screen7))
            compact = self.phase == 'reconstruct' and (0x6400 <= address < 0x7300
                or 0x7400 <= address < 0x7800 and 1 <= (address & 63) <= 32)
            states = any(first <= address < last for first, last in self.state_regions)
            if not (cold or pixels or compact or states or STACK-96 <= address < STACK
                    or self.phase == 'output' and output.MASK <= address < output.MASK+80):
                raise AssertionError(f'write outside pipeline contract: {address:04x}, {self.phase}')
        # Bypass the narrower stand-alone screen guard, retaining RAM paging.
        return CPU.write8(self, address, value)


class Harness:
    def __init__(self, tables, mapping):
        self.recon_code, self.recon, ri, rr = reconstruction.build(tables, mapping, OFFSETS,
            hybrid=True, skip_empty=True, intra_above=True, intra_extended=True,
            fast_fragments=True, unrolled_motion=True, split_literals=True)
        self.draw_code, self.draw, di, dr = output.build()
        self.wrapper_code, self.w, wi = wrapper(self.recon, self.draw)
        self.init_code, ii = initializer(self.draw)
        self.cpu = PipelineCPU(b'', b'')
        self.cpu.port_7ffd = 0x16
        self.cpu.state_regions = [(x['state'], x['end']) for x in (self.recon, self.draw, self.w)]
        self.cpu.input_end = INPUT_END
        # Catch any dependence on clear RAM or accidental TR-DOS writes.
        self.cpu.banks[5][:0x3800] = b'\xa5'*0x3800
        self.cpu.banks[7][:6912] = b'\xa5'*6912
        regions = [(reconstruction.CODE, self.recon_code), (output.CODE, self.draw_code),
                   (WRAPPER, self.wrapper_code), (INITIALIZER, self.init_code)]+rr+dr
        for first, blob in regions:
            for i, value in enumerate(blob):
                self.cpu.write8(first+i, value)
        self.instructions = {}
        for phase, rows in (('reconstruct', ri), ('output', di), ('handoff', wi), ('cold_init', ii)):
            for row in rows:
                if row['address'] in self.instructions:
                    raise ValueError('overlapping instruction ranges')
                self.instructions[row['address']] = dict(row, phase=phase)
        self.histogram = Counter()
        self.expected_screens = {5: bytes(6912), 7: bytes(6912)}
        self.protected_regions = [(first, blob) for first, blob in rr+dr]
        self.init_result = self.execute(INITIALIZER)
        if (self.cpu.port_7ffd != 0x16 or any(self.cpu.banks[5][:6912])
                or any(self.cpu.banks[7][:6912]) or any(self.cpu.banks[5][0x2400:0x3800])):
            raise AssertionError('cold initialization differs')
        self.histogram.clear()

    def execute(self, entry, interrupt=None):
        cpu = self.cpu
        cpu.pc, cpu.sp = entry, STACK
        cpu.guarding = False; cpu.push(STOP); cpu.guarding = True
        before, irq, steps = cpu.tstates, 0, 0
        stages, pages = Counter(), []
        while cpu.pc != STOP:
            pc, ticks, page = cpu.pc, cpu.tstates, cpu.port_7ffd
            row = self.instructions[pc]
            cpu.phase = row['phase']
            cpu.step(); steps += 1
            elapsed, wanted = cpu.tstates-ticks, row['tstates']
            if elapsed not in (wanted if isinstance(wanted, list) else [wanted]):
                raise AssertionError(('instruction timing', row, elapsed))
            stages[row['phase']] += elapsed; self.histogram[pc, elapsed] += 1
            if page != cpu.port_7ffd:
                pages.append(cpu.port_7ffd)
            if steps > 2000000:
                raise AssertionError('pipeline did not return')
            if interrupt and cpu.pc != STOP:
                irq += interrupt(cpu)
        if cpu.sp != STACK or sum(stages.values()) != cpu.tstates-before-irq:
            raise AssertionError('stack/timing mismatch')
        return dict(total_tstates=sum(stages.values()), stages=dict(stages), page_writes=pages, irq_tstates=irq)

    def run(self, group, mask, expected, index, interrupt=None):
        n, flags, bits, vectors, bitmap, attrs, encoded, literals = group
        if n != 1 or len(mask) != 80 or len(expected) != 3840:
            raise ValueError('one-frame packet required')
        data = encoded+b'\0'+literals+b'\0'
        if len(data) > INPUT_END-INPUT:
            raise ValueError('frame input overlaps prefix tables')
        cpu = self.cpu; cpu.guarding = False
        target = 7 if index % 2 == 0 else 5
        page = 0x16 if target == 7 else 0x1e
        if cpu.port_7ffd != page:
            raise AssertionError('paging state not retained from prior frame')
        cpu.target_bank = target
        for base, blob in ((VECTORS, vectors), (BITMAP, bitmap), (ATTRS, attrs), (INPUT, data), (MAP, mask)):
            for i, value in enumerate(blob):
                cpu.write8(base+i, value)
        cpu.input_end = INPUT+len(data)
        word(cpu, self.w['literal_pointer'], INPUT+len(encoded)+1)
        cpu.write8(self.w['cache_flag'], int(bool(flags & 128)))
        result = self.execute(WRAPPER, interrupt)
        if bytes(cpu.read8(0x6400+i) for i in range(3840)) != expected:
            raise AssertionError('causal reconstructed frame differs')
        self.expected_screens[target] = b''.join(expand_compact_screen(expected))
        if any(bytes(cpu.banks[b][:6912]) != wanted for b, wanted in self.expected_screens.items()):
            raise AssertionError('screen bytes differ or preceding visible screen damaged')
        position = (word(cpu, self.recon['source'])-INPUT)*8+(cpu.read8(self.recon['bit_page']) & 7)
        if (position != bits or word(cpu, self.recon['literal_source']) != INPUT+len(encoded)+1+len(literals)
                or result['stages']['output'] != output.expected_tstates(mask)
                or result['stages']['handoff'] != 337
                or cpu.port_7ffd != page ^ 8 or result['page_writes'] != [page | 1, page, page ^ 8]
                or bytes(cpu.banks[5][0x1b00:0x2400]) != b'\xa5'*0x900):
            raise AssertionError('pipeline cursor/timing/paging/TR-DOS contract differs')
        for base, blob in ((VECTORS, vectors), (BITMAP, bitmap), (ATTRS, attrs), (INPUT, data), (MAP, mask)):
            if bytes(cpu.read8(base+i) for i in range(len(blob))) != blob:
                raise AssertionError('input/metadata/map modified')
        return dict(index=index, target_bank=target, coded_bytes=len(data), **result)


def frames(data):
    fsf, masks, _ = unpack(data)
    r = Reader(fsf)
    model, _, count, mapping, tables = read_header(r, magic=b'FSF1')
    if model != 0:
        raise ValueError('unsupported FSC1 model')
    result, index = [], 0
    while index < count:
        group = read_group(r, count-index, fast_fragments=True)
        literal = r.take(sum(SIZES.get(v, 0) for v in group[3]))
        if group[0] != 1:
            raise ValueError('one-frame FSC1 required')
        result.append(((*group, literal), masks[index*80:index*80+80])); index += 1
    r.end()
    return tables, mapping, result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stream', type=Path, required=True)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    data = args.stream.read_bytes()
    tables, mapping, packets = frames(data)
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    if states.shape != (len(packets), 3840):
        raise ValueError('different frame count')
    h = Harness(tables, mapping)
    report = dict(scope=__doc__, complete=False, baseline_commit='6103e11', stream_sha256=sha(data),
        states_sha256=sha(states.tobytes()), frames_expected=len(states), frames=[],
        reconstruction_code_sha256=sha(h.recon_code), output_code_sha256=sha(h.draw_code),
        wrapper_code_hex=h.wrapper_code.hex(), wrapper_labels=h.w, wrapper_tstates=337,
        initializer_code_hex=h.init_code.hex(), cold_init=h.init_result,
        instruction_listing=list(h.instructions.values()),
        input_memory=dict(vectors=VECTORS, bitmap_masks=BITMAP, attribute_masks=ATTRS,
            values=INPUT, end_exclusive=INPUT_END, native_map=MAP),
        cpu_shared_memory_verified=False, metadata_expanded_by_host=True,
        zx0_included=False, frame_pacing_verified=False, disk_delivery_verified=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf', player_changed=False)
    for index, ((group, mask), state) in enumerate(zip(packets, states)):
        report['frames'].append(h.run(group, mask, state.tobytes(), index))
        if index % 250 == 0:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'Shared pipeline Z80 verified {index+1}/{len(states)}', flush=True)
    for base, blob in h.protected_regions:
        if bytes(h.cpu.read8(base+i) for i in range(len(blob))) != blob:
            raise AssertionError('lookup table modified')
    totals = [r['total_tstates'] for r in report['frames']]
    report['instruction_histogram'] = [dict(address=a, tstates=t, count=n) for (a, t), n in sorted(h.histogram.items())]
    if sum(r['count']*r['tstates'] for r in report['instruction_histogram']) != sum(totals):
        raise AssertionError('histogram differs')
    report['summary'] = dict(frames=len(states), total_tstates=sum(totals), mean_tstates=sum(totals)/len(states),
        max_tstates=max(totals), worst_frame=totals.index(max(totals)),
        frames_over_nominal_425448=sum(v > 425448 for v in totals),
        max_coded_input_bytes=max(r['coded_bytes'] for r in report['frames']))
    report['complete'] = report['cpu_shared_memory_verified'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
