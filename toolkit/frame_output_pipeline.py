"""Run one-frame FSC1/FSC2 reconstruction and cell output in one Z80/RAM instance.

CPU executes cold screen/cache clearing, frame setup, both stages, paging,
and screen publication. With --decode-metadata it also expands sparse masks.
With --cache-stream it consumes actual SC04 coverage to skip cache copies.
Host still parses headers and supplies/copies input. No ZX0/AY/ROM/disk
scheduling or frame pacing claim.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

import causal_tile_z80 as reconstruction
import cell_screen_z80 as output
import frame_metadata_z80 as metadata
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


def display_screen(state, *, black_borders=False):
    """Native reference; optional user-authorized cleanup of outside pixels."""
    if black_borders:
        state = bytes(384)+bytes(state[384:2688])+bytes(384)+bytes(state[3072:])
    return b''.join(expand_compact_screen(state))


def wrapper(recon, draw, *, origin=WRAPPER, deferred_publish=False, dynamic_source=False, dynamic_metadata=False,
            split_prepare=False,preloaded_mask=False,attribute_group_entry=None):
    if split_prepare and not deferred_publish:
        raise ValueError('split preparation requires deferred publication')
    if preloaded_mask and not (split_prepare and dynamic_metadata):
        raise ValueError('preloaded native mask requires split preparation and dynamic metadata')
    a, listing = MiniAssembler(origin), []
    a.label('run')
    def emit(name, data, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage='handoff'))
        a.emit(*data)
    def address(name, opcode, value, ticks):
        emit(name, [opcode, value & 255, value >> 8], ticks)
    def load_a(addr): address('LD A,(nn)', 0x3a, addr, 13)
    def store_a(addr): address('LD (nn),A', 0x32, addr, 13)
    for name, value in (('vectors', VECTORS), ('bitmap_masks', BITMAP), ('attribute_masks', ATTRS), ('source', INPUT)):
        if name == 'source' and dynamic_source or name == 'vectors' and dynamic_metadata:
            pointer = 'coded_pointer' if name == 'source' else 'vector_pointer'
            listing.append(dict(address=a.pc,instruction='LD HL,('+pointer+')',tstates=16,stage='handoff'))
            a.abs16(0x2a,pointer)
        else:
            address('LD HL,'+name, 0x21, value, 10)
        address('LD ('+name+'),HL', 0x22, recon[name], 16)
    listing.append(dict(address=a.pc, instruction='LD HL,(literal_pointer)', tstates=16, stage='handoff'))
    a.abs16(0x2a, 'literal_pointer')
    address('LD (literal_source),HL', 0x22, recon['literal_source'], 16)
    emit('LD A,F0h', [0x3e, 0xf0], 7); store_a(recon['bit_page'])
    listing.append(dict(address=a.pc, instruction='LD A,(cache_flag)', tstates=13, stage='handoff'))
    a.abs16(0x3a, 'cache_flag'); store_a(recon['cache_enabled'])
    if 'raw_attributes' in recon:
        listing.append(dict(address=a.pc, instruction='LD A,(raw_attribute_flag)', tstates=13, stage='handoff'))
        a.abs16(0x3a, 'raw_attribute_flag'); store_a(recon['raw_attributes'])
    address('CALL reconstruct', 0xcd, recon['frame'], 17)
    if attribute_group_entry is not None:
        address('CALL prepare attribute groups',0xcd,attribute_group_entry,17)
    if preloaded_mask:
        listing.append(dict(address=a.pc,instruction='LD HL,(native_pointer)',tstates=16,stage='handoff'))
        a.abs16(0x2a,'native_pointer')
        address('CALL save native map',0xcd,draw['copy_map'],17)
    if split_prepare:
        emit('RET (compact ready)', [0xc9], 10)
        a.label('draw_compact')
    load_a(draw['screen_base'])
    if dynamic_metadata and not preloaded_mask:
        listing.append(dict(address=a.pc,instruction='LD HL,(native_pointer)',tstates=16,stage='handoff'))
        a.abs16(0x2a,'native_pointer')
    elif not preloaded_mask:
        address('LD HL,native_map', 0x21, MAP, 10)
    address('CALL draw', 0xcd, draw['draw'], 17)
    if deferred_publish:
        emit('RET (prepared screen)', [0xc9], 10)
    a.label('publish')
    load_a(draw['saved_page']); emit('XOR 8', [0xee, 8], 7); store_a(draw['saved_page'])
    address('LD BC,7FFD', 0x01, 0x7ffd, 10)
    emit('OUT (C),A', [0xed, 0x79], 12)
    load_a(draw['screen_base']); emit('XOR 80h', [0xee, 128], 7); store_a(draw['screen_base'])
    emit('RET', [0xc9], 10)
    a.label('state')
    a.label('literal_pointer'); a.word(0)
    a.label('cache_flag'); a.emit(0)
    if 'raw_attributes' in recon:
        a.label('raw_attribute_flag'); a.emit(0)
    if dynamic_source:
        a.label('coded_pointer'); a.word(0)
    if dynamic_metadata:
        a.label('vector_pointer'); a.word(0)
        a.label('native_pointer'); a.word(0)
    a.label('end')
    if (origin == WRAPPER and (a.pc > output.CODE or recon['end'] > WRAPPER)
            or origin != WRAPPER and (origin < 0x78a0 or a.pc > INITIALIZER or recon['end'] > output.CODE)):
        raise ValueError('frame wrapper overlaps generated code')
    return a.resolve(), a.labels, listing


def initializer(draw, *, constant_attribute_borders=False):
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
    if constant_attribute_borders:
        for base in (0x5800,0xd800):
            imm('LD HL,attributes',0x21,base,10)
            imm('LD DE,attributes+1',0x11,base+1,10)
            imm('LD BC,767',0x01,767,10)
            emit('LD (HL),1',[0x36,1],10)
            emit('LDIR',[0xed,0xb0],[16,21])
    emit('LD A,16h', [0x3e, 0x16], 7)
    imm('LD (saved_page),A', 0x32, draw['saved_page'], 13)
    imm('LD BC,7FFD', 0x01, 0x7ffd, 10); emit('OUT (C),A', [0xed, 0x79], 12)
    emit('LD A,C0h', [0x3e, 0xc0], 7)
    imm('LD (screen_base),A', 0x32, draw['screen_base'], 13)
    emit('RET', [0xc9], 10)
    if a.pc > 0x7b70: raise ValueError('cold initializer overlaps private ZX0 stack')
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
            masks = self.phase == 'metadata' and (BITMAP <= address < INPUT
                or metadata.FLAGS <= address < metadata.FLAGS+64)
            states = any(first <= address < last for first, last in self.state_regions)
            if not (cold or pixels or compact or masks or states or STACK-96 <= address < STACK
                    or self.phase == 'output' and output.MASK <= address < output.MASK+80):
                raise AssertionError(f'write outside pipeline contract: {address:04x}, {self.phase}')
        # Bypass the narrower stand-alone screen guard, retaining RAM paging.
        return CPU.write8(self, address, value)


class Harness:
    def __init__(self, tables, mapping, *, raw_attributes=False, decode_metadata=False, fast_mask_dispatch=False, selective_cache=False, deferred_publish=False, dynamic_source=False, dynamic_metadata=False, skip_noop_runs=False,
                 constant_attribute_borders=False,skip_black_borders=False,encoded_noop_runs=False,skip_static_stripes=False,
                 split_prepare=False,page_entry=None,preloaded_mask=False,cache_columns=32,unrolled_cache=False,attribute_groups=False,attribute_flags=False,gray_cells=False,sparse_patches=False):
        if attribute_flags and not (decode_metadata and raw_attributes):
            raise ValueError('attribute flags require decoded metadata and the raw flag')
        if skip_black_borders and not constant_attribute_borders:
            raise ValueError('black borders require initialized constant attributes')
        if attribute_groups and not (constant_attribute_borders and decode_metadata and raw_attributes):
            raise ValueError('attribute lists require metadata, raw flag and constant borders')
        self.attribute_groups=attribute_groups
        self.raw_attributes = raw_attributes
        self.constant_attribute_borders = constant_attribute_borders
        self.skip_black_borders = skip_black_borders
        self.decode_metadata = decode_metadata
        self.fast_mask_dispatch = fast_mask_dispatch
        self.gray_cells=gray_cells
        self.selective_cache = selective_cache
        self.cache_map_bytes = 96//cache_columns
        self.encoded_noop_runs = encoded_noop_runs
        self.skip_static_stripes = skip_static_stripes
        self.recon_code, self.recon, ri, rr = reconstruction.build(tables, mapping, OFFSETS,
            hybrid=True, skip_empty=True, intra_above=True, intra_extended=True,
            fast_fragments=True, unrolled_motion=True, split_literals=True, raw_attributes=raw_attributes,
            selective_cache=selective_cache,skip_noop_runs=skip_noop_runs,encoded_noop_runs=encoded_noop_runs,
            skip_static_stripes=skip_static_stripes,cache_columns=cache_columns,unrolled_cache=unrolled_cache,
            attribute_flags=attribute_flags,sparse_patches=sparse_patches)
        if self.recon['end'] > output.CODE:
            raise ValueError('reconstruction overlaps native renderer')
        ai=[]; ar=[]; attribute_entry=None
        if attribute_groups:
            import attribute_groups_z80 as groups
            self.group_code,self.group_labels,ai,ar=groups.build(self.recon['raw_attributes'])
            attribute_entry=self.group_labels['prepare']
            ar=[(groups.CODE,self.group_code)]+ar
        self.draw_code, self.draw, di, dr = output.build(fast_mask_dispatch=fast_mask_dispatch,
            constant_attribute_borders=constant_attribute_borders,skip_black_borders=skip_black_borders,page_entry=page_entry,
            preloaded_mask=preloaded_mask,attribute_groups=attribute_groups,gray_cells=gray_cells)
        if attribute_flags:
            from attribute_mask_z80 import CODE as attribute_controller
            if self.draw['end']>attribute_controller:
                raise ValueError('native renderer overlaps attribute flag controller')
        self.wrapper_code, self.w, wi = wrapper(self.recon, self.draw, origin=0x7900 if selective_cache else WRAPPER,
                                               deferred_publish=deferred_publish,dynamic_source=dynamic_source,
                                               dynamic_metadata=dynamic_metadata,split_prepare=split_prepare,preloaded_mask=preloaded_mask,
                                               attribute_group_entry=attribute_entry)
        self.init_code, ii = initializer(self.draw,constant_attribute_borders=constant_attribute_borders)
        self.cpu = PipelineCPU(b'', b'')
        self.cpu.target_bank = None  # A saved map may precede the first native draw.
        self.cpu.port_7ffd = 0x16
        self.cpu.state_regions = [(x['state'], x['end']) for x in (self.recon, self.draw, self.w)]
        if attribute_groups:
            self.cpu.state_regions += [(base,base+groups.LIST_BYTES) for base in groups.LISTS]
            self.cpu.state_regions += [(self.group_labels['state'],self.group_labels['end'])]
        self.cpu.input_end = INPUT_END
        # Catch any dependence on clear RAM or accidental TR-DOS writes.
        self.cpu.banks[5][:0x3800] = b'\xa5'*0x3800
        self.cpu.banks[7][:6912] = b'\xa5'*6912
        regions = [(reconstruction.CODE, self.recon_code), (output.CODE, self.draw_code),
                   (self.w['run'], self.wrapper_code), (INITIALIZER, self.init_code)]+rr+dr+ar
        mi = []
        if decode_metadata:
            self.metadata_code, self.metadata_labels, mi = metadata.build()
            regions.append((metadata.CODE, self.metadata_code))
        for first, blob in regions:
            for i, value in enumerate(blob):
                self.cpu.write8(first+i, value)
        self.instructions = {}
        for phase, rows in (('reconstruct', ri), ('output', di), ('handoff', wi), ('cold_init', ii), ('metadata', mi),('attribute_groups',ai)):
            for row in rows:
                if row['address'] in self.instructions:
                    raise ValueError('overlapping instruction ranges')
                self.instructions[row['address']] = dict(row, phase=phase)
        self.histogram = Counter()
        initial_screen = bytes(6144)+bytes([int(constant_attribute_borders)])*768
        self.expected_screens = {5: initial_screen, 7: initial_screen}
        self.protected_regions = [(first, blob) for first, blob in rr+dr]
        self.init_result = self.execute(INITIALIZER)
        if (self.cpu.port_7ffd != 0x16 or bytes(self.cpu.banks[5][:6912]) != initial_screen
                or bytes(self.cpu.banks[7][:6912]) != initial_screen or any(self.cpu.banks[5][0x2400:0x3800])):
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

    def run(self, group, mask, expected, index, interrupt=None, *, encoded_metadata=None, cache_map=None):
        n, flags, bits, vectors, bitmap, attrs, encoded, literals = group
        if self.attribute_groups and index>=2 and not flags&64 and (any(attrs[:12]) or any(attrs[84:])):
            raise ValueError('attribute changes outside constant borders')
        if self.skip_static_stripes: reconstruction.validate_static_stripes(vectors,bitmap)
        if self.encoded_noop_runs:
            from vector_run_stream import encode_vectors
            vectors = encode_vectors(vectors,bitmap,inplace=self.encoded_noop_runs == 'inplace')[0]
        if flags & 64 and not self.raw_attributes:
            raise ValueError('raw attribute packet requires matching decoder')
        if n != 1 or len(mask) != 80 or len(expected) != 3840:
            raise ValueError('one-frame packet required')
        if self.constant_attribute_borders and (expected[3072:3168] != b'\1'*96 or expected[3744:] != b'\1'*96):
            raise ValueError('constant attribute borders differ')
        data = encoded+b'\0'+literals+b'\0'
        if len(data) > INPUT_END-INPUT:
            raise ValueError('frame input overlaps prefix tables')
        cpu = self.cpu; cpu.guarding = False
        target = 7 if index % 2 == 0 else 5
        page = 0x16 if target == 7 else 0x1e
        if cpu.port_7ffd != page:
            raise AssertionError('paging state not retained from prior frame')
        cpu.target_bank = target
        if self.selective_cache:
            if cache_map is None or len(cache_map) != self.cache_map_bytes:
                raise ValueError('cache coverage size differs')
            for i, value in enumerate(cache_map):
                cpu.write8(reconstruction.CACHE_MAP+i, value)
        meta_result = None
        if self.decode_metadata:
            if encoded_metadata is None or len(encoded_metadata) > INPUT_END-INPUT:
                raise ValueError('serialized metadata required')
            for i, value in enumerate(encoded_metadata):
                cpu.write8(INPUT+i, value)
            cpu.input_end = INPUT+len(encoded_metadata)
            cpu.set_hl(INPUT)
            meta_result = self.execute(metadata.CODE, interrupt)
            if (cpu.hl() != cpu.input_end or meta_result['total_tstates'] != metadata.expected_tstates(encoded_metadata)
                    or bytes(cpu.read8(BITMAP+i) for i in range(480)) != bitmap+attrs
                    or any(cpu.read8(metadata.FLAGS+60+i) for i in range(4))):
                raise AssertionError('metadata decoder differs')
            cpu.guarding = False
        for base, blob in ((VECTORS, vectors), (BITMAP, bitmap), (ATTRS, attrs), (INPUT, data), (MAP, mask)):
            if self.decode_metadata and base in (BITMAP, ATTRS):
                continue
            for i, value in enumerate(blob):
                cpu.write8(base+i, value)
        cpu.input_end = INPUT+len(data)
        word(cpu, self.w['literal_pointer'], INPUT+len(encoded)+1)
        cpu.write8(self.w['cache_flag'], int(bool(flags & 128)))
        if self.raw_attributes:
            cpu.write8(self.w['raw_attribute_flag'], int(bool(flags & 64)))
        result = self.execute(self.w['run'], interrupt)
        if bytes(cpu.read8(0x6400+i) for i in range(3840)) != expected:
            raise AssertionError('causal reconstructed frame differs')
        self.expected_screens[target] = display_screen(expected,black_borders=self.skip_black_borders)
        if any(bytes(cpu.banks[b][:6912]) != wanted for b, wanted in self.expected_screens.items()):
            raise AssertionError('screen bytes differ or preceding visible screen damaged')
        position = (word(cpu, self.recon['source'])-INPUT)*8+(cpu.read8(self.recon['bit_page']) & 7)
        group_counts=None
        if self.attribute_groups:
            from attribute_groups_z80 import LISTS
            group_counts=[cpu.read8(base) for base in LISTS]
        if (position != bits or word(cpu, self.recon['literal_source']) != INPUT+len(encoded)+1+len(literals)
                or result['stages']['output'] != output.expected_tstates(mask, fast_mask_dispatch=self.fast_mask_dispatch,
                    constant_attribute_borders=self.constant_attribute_borders,skip_black_borders=self.skip_black_borders,
                    attribute_group_counts=group_counts,gray_cells=self.gray_cells)
                or result['stages']['handoff'] != 337+26*self.raw_attributes+17*self.attribute_groups
                or cpu.port_7ffd != page ^ 8 or result['page_writes'] != [page | 1, page, page ^ 8]
                or bytes(cpu.banks[5][0x1b00:0x2400]) != b'\xa5'*0x900):
            raise AssertionError('pipeline cursor/timing/paging/TR-DOS contract differs')
        for base, blob in ((VECTORS, vectors), (BITMAP, bitmap), (ATTRS, attrs), (INPUT, data), (MAP, mask)):
            if bytes(cpu.read8(base+i) for i in range(len(blob))) != blob:
                raise AssertionError('input/metadata/map modified')
        if self.selective_cache:
            if (bytes(cpu.read8(reconstruction.CACHE_MAP+i) for i in range(self.cache_map_bytes)) != cache_map
                    or flags & 128 and (word(cpu, self.recon['cache_mask_source']) != reconstruction.CACHE_MAP+self.cache_map_bytes
                        or cpu.read8(self.recon['cache_mask_shift']) != 128)):
                raise AssertionError('selective cache cursor or map differs')
        if meta_result:
            result['total_tstates'] += meta_result['total_tstates']
            result['stages'].update(meta_result['stages'])
            result['irq_tstates'] += meta_result['irq_tstates']
            if meta_result['page_writes']:
                raise AssertionError('metadata paged memory')
        return dict(index=index, target_bank=target, coded_bytes=len(data), **result)


def frames(data):
    if data[:4] == b'FSC2':
        from raw_attribute_stream import packets
        return packets(data)[1:]
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


def serialized_masks(data):
    """Extract the actual coded mask bytes; no re-encoding or host expansion."""
    import struct
    from raw_attribute_stream import read_packet
    r = Reader(data)
    _, _, count, _, _ = read_header(r, magic=data[:4])
    masks = []
    for index in range(count):
        start = r.pos
        _, vl, ml = struct.unpack_from('<HHH', data, start)
        read_packet(r, count-index, extended=data[:4] == b'FSC2')
        masks.append(data[start+11+vl:start+11+vl+ml])
    r.end()
    return masks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stream', type=Path, required=True)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--baseline-commit', default='6103e11')
    p.add_argument('--decode-metadata', action='store_true')
    p.add_argument('--fast-mask-dispatch', action='store_true')
    p.add_argument('--cache-stream', type=Path, help='SC04 stream with actual serialized coverage maps')
    args = p.parse_args()
    data = args.stream.read_bytes()
    tables, mapping, packets = frames(data)
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    if states.shape != (len(packets), 3840):
        raise ValueError('different frame count')
    raw_attributes = data[:4] == b'FSC2'
    cache_maps = [None]*len(packets)
    if args.cache_stream:
        from probe_sparse_motion_cache import unpack as unpack_cache
        from cell_audio_stream import unpack as unpack_audio
        restored, cache_maps = unpack_cache(args.cache_stream.read_bytes(), 32, 4, return_maps=True)
        if unpack_audio(restored)[0] != data:
            raise ValueError('cache stream belongs to different video')
    h = Harness(tables, mapping, raw_attributes=raw_attributes, decode_metadata=args.decode_metadata,
                fast_mask_dispatch=args.fast_mask_dispatch, selective_cache=bool(args.cache_stream))
    masks = serialized_masks(data) if args.decode_metadata else [None]*len(packets)
    report = dict(scope=__doc__, complete=False, baseline_commit=args.baseline_commit, stream_sha256=sha(data),
        states_sha256=sha(states.tobytes()), frames_expected=len(states), frames=[],
        reconstruction_code_sha256=sha(h.recon_code), output_code_sha256=sha(h.draw_code),
        wrapper_code_hex=h.wrapper_code.hex(), wrapper_labels=h.w, wrapper_tstates=337+26*raw_attributes,
        raw_attributes=raw_attributes, fast_mask_dispatch=args.fast_mask_dispatch,
        cache_stream_sha256=sha(args.cache_stream.read_bytes()) if args.cache_stream else None,
        cache_map_supplied_by_host=bool(args.cache_stream),
        initializer_code_hex=h.init_code.hex(), cold_init=h.init_result,
        instruction_listing=list(h.instructions.values()),
        input_memory=dict(vectors=VECTORS, bitmap_masks=BITMAP, attribute_masks=ATTRS,
            values=INPUT, end_exclusive=INPUT_END, native_map=MAP,
            selective_cache_map=reconstruction.CACHE_MAP if args.cache_stream else None),
        cpu_shared_memory_verified=False, metadata_expanded_by_host=not args.decode_metadata,
        serialized_masks_supplied_by_host=args.decode_metadata,
        metadata_code_hex=h.metadata_code.hex() if args.decode_metadata else None,
        zx0_included=False, frame_pacing_verified=False, disk_delivery_verified=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf', player_changed=False)
    for index, ((group, mask), state, coded_masks, cache_map) in enumerate(zip(packets, states, masks, cache_maps)):
        report['frames'].append(h.run(group, mask, state.tobytes(), index, encoded_metadata=coded_masks, cache_map=cache_map))
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
