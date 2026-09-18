"""Z80 canonical context Huffman primitive and bounded value-only wrapper.

Bitmap entry: A = predicted byte; attribute entry ignores A. IX points at
MSB-first coded bytes, B is a sentinel reservoir (initially 80h). Return A
is one nonzero correction; B/IX retain unread input. C and alternate
registers survive; A/flags/DE/HL are scratch. No DI or self-modifying code.

Count records contain (leaves at depth, cumulative leaves through depth).
Subtracting a count either leaves an unresolved rank or borrows for a leaf.
On borrow, adding the cumulative count gives the leaf's symbol index modulo
256. Complete trees with <=255 leaves need only eight-bit rank arithmetic.

The wrapper takes alternate HL = pairs (attribute flag, predicted byte),
DE = output and BC = count (caller bounds it to 32). It saves B/IX in three
state bytes, so registers may be clobbered between calls. The predictor
pairs are a benchmark input, NOT an implemented motion/mask producer.
Input is a contiguous group; split ZX0 windows are not handled here yet.
"""
from build_zxv_trd import MiniAssembler
from profile_context_tree_memory import shared_tree

CODE, TABLE, LOOKUP = 0x8000, 0xc000, 0xb900


def prepare(tables, mapping, variant):
    if variant not in ('compact', 'direct', 'unrolled'):
        raise ValueError('unknown variant')
    if len(mapping) != 256 or not 2 <= len(tables) <= 128 or max(mapping) >= len(tables)-1:
        raise ValueError('invalid mapping or context count')
    shared_tree(tables)  # Reject incomplete trees and coded zero symbols.
    depth = max(max(t) for t in tables)
    if not 1 <= depth <= 24:
        raise ValueError('unsupported depth')
    compact = variant == 'compact'
    base = TABLE+256+2*len(tables) if compact else TABLE
    counts, symbols, blob = [], [], bytearray()
    for lengths in tables:
        counts.append(base+len(blob))
        cumulative = 0
        for n in range(1, depth+1):
            count = lengths.count(n)
            cumulative += count
            blob += bytes([count, cumulative])
        symbols.append(base+len(blob))
        blob += bytes(value for _, value in sorted((n, v) for v, n in enumerate(lengths) if n))
    if base+len(blob) > 65536:
        raise ValueError('table data exceeds one bank')
    if compact:
        pointers = b''.join(address.to_bytes(2, 'little') for address in counts)
        regions = [(TABLE, bytes(mapping)+pointers+blob)]
    else:
        columns = [bytes((addresses[c] >> shift) & 255 for c in mapping)
                   for addresses, shift in ((counts, 0), (counts, 8), (symbols, 0), (symbols, 8))]
        regions = [(LOOKUP, b''.join(columns)), (TABLE, bytes(blob))]
    return depth, counts, symbols, regions


def build(tables, mapping, variant='unrolled'):
    depth, counts, symbols, regions = prepare(tables, mapping, variant)
    asm = MiniAssembler(CODE)
    listing = []

    def emit(name, data, cycles):
        listing.append(dict(address=asm.pc, instruction=name, tstates=cycles))
        asm.emit(*data)

    def jump(name, op, target, cycles, relative=False):
        listing.append(dict(address=asm.pc, instruction=name, tstates=cycles))
        (asm.rel8 if relative else asm.abs16)(op, target)

    def wordop(name, op, word, cycles):
        emit(name, [op, word & 255, word >> 8], cycles)

    asm.label('attribute')
    wordop('LD HL,attribute_counts', 0x21, counts[-1], 10)
    wordop('LD DE,attribute_symbols', 0x11, symbols[-1], 10)
    jump('JP begin', 0xc3, 'begin', 10)
    asm.label('bitmap')
    if variant == 'compact':
        emit('LD L,A', [0x6f], 4)
        emit('LD H,C0h', [0x26, TABLE >> 8], 7)
        emit('LD A,(HL)', [0x7e], 7)
        emit('ADD A,A', [0x87], 4)
        emit('LD L,A', [0x6f], 4)
        emit('INC H', [0x24], 4)
        emit('LD E,(HL)', [0x5e], 7)
        emit('INC L', [0x2c], 4)
        emit('LD D,(HL)', [0x56], 7)
        emit('EX DE,HL', [0xeb], 4)
        emit('LD A,L', [0x7d], 4)
        emit('ADD A,count_record_bytes', [0xc6, 2*depth], 7)
        emit('LD E,A', [0x5f], 4)
        emit('LD A,H', [0x7c], 4)
        emit('ADC A,0', [0xce, 0], 7)
        emit('LD D,A', [0x57], 4)
    else:
        emit('LD L,A', [0x6f], 4)
        emit('LD H,lookup_page', [0x26, LOOKUP >> 8], 7)
        emit('LD E,(HL)', [0x5e], 7)
        emit('INC H', [0x24], 4)
        emit('LD D,(HL)', [0x56], 7)
        emit('INC H', [0x24], 4)
        emit('LD A,(HL)', [0x7e], 7)
        emit('INC H', [0x24], 4)
        emit('LD H,(HL)', [0x66], 7)
        emit('LD L,A', [0x6f], 4)
        emit('EX DE,HL', [0xeb], 4)
    asm.label('begin')
    emit('XOR A', [0xaf], 4)
    asm.label('bit')
    for level in range(depth if variant == 'unrolled' else 1):
        emit('SLA B', [0xcb, 0x20], 8)
        jump('JR NZ,have_bit', 0x20, f'have_bit_{level}', [7, 12], True)
        emit('LD B,(IX+0)', [0xdd, 0x46, 0], 19)
        emit('INC IX', [0xdd, 0x23], 10)
        emit('RL B', [0xcb, 0x10], 8)
        asm.label(f'have_bit_{level}')
        emit('RLA', [0x17], 4)
        emit('SUB (HL)', [0x96], 7)
        emit('INC HL', [0x23], 6)
        if variant == 'unrolled':
            jump('JP C,leaf', 0xda, 'leaf', 10)
        else:
            jump('JR C,leaf', 0x38, 'leaf', [7, 12], True)
        emit('INC HL', [0x23], 6)
    if variant != 'unrolled':
        jump('JR bit', 0x18, 'bit', 12, True)
    else:
        # A complete validated tree always finds a leaf by max depth.
        asm.label('invalid')
        emit('HALT (invalid tree/input)', [0x76], 4)
    asm.label('leaf')
    emit('ADD A,(HL)', [0x86], 7)
    emit('ADD A,E', [0x83], 4)
    emit('LD E,A', [0x5f], 4)
    jump('JR NC,symbol', 0x30, 'symbol', [7, 12], True)
    emit('INC D', [0x14], 4)
    asm.label('symbol')
    emit('LD A,(DE)', [0x1a], 7)
    emit('RET', [0xc9], 10)
    asm.label('primitive_end')

    # The caller supplies a bounded count and causal predictor pairs.
    asm.label('chunk')
    emit('EXX', [0xd9], 4)
    emit('LD A,B', [0x78], 4)
    emit('OR C', [0xb1], 4)
    emit('EXX', [0xd9], 4)
    emit('RET Z', [0xc8], [5, 11])
    listing.append(dict(address=asm.pc, instruction='LD IX,(source)', tstates=20))
    asm.emit(0xdd); asm.abs16(0x2a, 'source')
    jump('LD A,(reservoir)', 0x3a, 'reservoir', 13)
    emit('LD B,A', [0x47], 4)
    asm.label('next_value')
    emit('EXX', [0xd9], 4)
    emit('LD A,(HL)', [0x7e], 7)
    emit('INC HL', [0x23], 6)
    emit('OR A', [0xb7], 4)
    emit('LD A,(HL)', [0x7e], 7)
    emit('INC HL', [0x23], 6)
    emit('EXX', [0xd9], 4)
    jump('JR NZ,attribute_call', 0x20, 'attribute_call', [7, 12], True)
    jump('CALL bitmap', 0xcd, 'bitmap', 17)
    jump('JR produced', 0x18, 'produced', 12, True)
    asm.label('attribute_call')
    jump('CALL attribute', 0xcd, 'attribute', 17)
    asm.label('produced')
    emit('EXX', [0xd9], 4)
    emit('LD (DE),A', [0x12], 7)
    emit('INC DE', [0x13], 6)
    emit('DEC BC', [0x0b], 6)
    emit('LD A,B', [0x78], 4)
    emit('OR C', [0xb1], 4)
    emit('EXX', [0xd9], 4)
    jump('JP NZ,next_value', 0xc2, 'next_value', 10)
    listing.append(dict(address=asm.pc, instruction='LD (source),IX', tstates=20))
    asm.emit(0xdd); asm.abs16(0x22, 'source')
    emit('LD A,B', [0x78], 4)
    jump('LD (reservoir),A', 0x32, 'reservoir', 13)
    emit('RET', [0xc9], 10)
    asm.label('state')
    asm.label('source'); asm.word(0)
    asm.label('reservoir'); asm.emit(0x80)
    asm.label('end')
    return asm.resolve(), dict(asm.labels), listing, regions
