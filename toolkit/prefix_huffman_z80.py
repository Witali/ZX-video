"""Eight-bit context prefix lookup, with a canonical long-code fallback.

The one-bank layout accepts up to 24 contexts when root/tail data fits below
F000. F000..FFFF holds shift/merge lookup pages. Fixed RAM holds the predicted
byte -> root-page map (B900), tail pointers (BA00), marker bytes (BAF0), and
sentinel -> bit position map (BB00). Zero-valued symbols are supported.

Entry A = predicted byte, or separate attribute entry; IX is the current
input byte, C = F0h + bit offset 0..7. Peek always reads IX and IX+1; caller
must provide one zero lookahead byte after a group. Returns the decoded byte
in A and updated IX/C. The wrapper saves IX/C between <=32-value calls.
This machine primitive is not a complete streamed player.
"""
from build_zxv_trd import MiniAssembler
from probe_motion_entropy import codes_for

CODE, TABLE, MAP, TAILS, MARKERS, POSITIONS = 0x8000, 0xc000, 0xb900, 0xba00, 0xbaf0, 0xbb00


def prepare(tables, mapping):
    if len(mapping) != 256 or not 2 <= len(tables) <= 24 or max(mapping) >= len(tables)-1:
        raise ValueError('invalid context map/count')
    depth = max(max(t) for t in tables)
    if depth > 18:
        raise ValueError('maximum code length exceeds 18')
    root_data, tail_data, counts, symbols, indices = bytearray(), bytearray(), [], [], []
    for table in tables:
        if len(table) != 256 or sum(1 << (depth-n) for n in table if n) != 1 << depth:
            raise ValueError('requires a complete canonical tree')
        values, sizes = bytearray(256), bytearray(256)
        for symbol, (code, length) in enumerate(codes_for(255, table)):
            if 0 < length <= 8:
                for prefix in range(code << (8-length), (code+1) << (8-length)):
                    values[prefix], sizes[prefix] = symbol, length
        for prefix in range(256):
            if sizes[prefix]:
                continue
            rank = 0
            for level in range(1, 9):
                rank = 2*rank+((prefix >> (8-level)) & 1)-table.count(level)
                if rank < 0:
                    raise AssertionError('unfilled short-code entry')
            values[prefix] = rank
        root_data += values+sizes
        counts.append(TABLE+len(tables)*512+len(tail_data))
        cumulative = 0
        for n in range(9, depth+1):
            amount = table.count(n)
            cumulative += amount
            tail_data += bytes([amount, cumulative])
        symbols.append(TABLE+len(tables)*512+len(tail_data))
        tail_symbols = [v for _, v in sorted((n, v) for v, n in enumerate(table) if n > 8)]
        indices.append({v: i for i, v in enumerate(tail_symbols)})
        tail_data += bytes(tail_symbols)
    data = root_data+tail_data
    if len(data) > 12288:
        raise ValueError('prefix/tail data leaves no room for the shift pages')
    body_bytes = len(data)
    data += bytes(12288-len(data))
    data += b''.join(bytes((v << r) & 255 for v in range(256)) for r in range(8))
    data += b''.join(bytes(v >> (8-r) for v in range(256)) for r in range(8))
    marker = bytes([0]+[1 << (r-1) for r in range(1, 8)])
    positions = bytes(0xf8 if not b else 0xf0 if b == 128 else 0xf1+((b & -b).bit_length()-1) for b in range(256))
    regions = [(TABLE, bytes(data)), (MAP, bytes(0xc0+2*c for c in mapping)),
               (TAILS, b''.join(p.to_bytes(2, 'little') for p in counts)),
               (MARKERS, marker), (POSITIONS, positions)]
    return dict(depth=depth, regions=regions, body_bytes=body_bytes,
                counts=counts, symbols=symbols, indices=indices)


def build(tables, mapping):
    layout = prepare(tables, mapping)
    a, listing = MiniAssembler(CODE), []

    def emit(name, data, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks)); a.emit(*data)

    def jump(name, opcode, target, ticks, relative=False):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks))
        (a.rel8 if relative else a.abs16)(opcode, target)

    a.label('attribute')
    emit('LD D,attribute_root_page', [0x16, 0xc0+2*(len(tables)-1)], 7)
    jump('JP peek', 0xc3, 'peek', 10)
    a.label('bitmap')
    emit('LD L,A', [0x6f], 4)
    emit('LD H,map_page', [0x26, MAP >> 8], 7)
    emit('LD D,(HL)', [0x56], 7)
    a.label('peek')
    emit('LD H,C', [0x61], 4)
    emit('LD L,(IX+0)', [0xdd, 0x6e, 0], 19)
    emit('LD A,(HL)', [0x7e], 7)
    emit('SET 3,H', [0xcb, 0xdc], 8)
    emit('LD L,(IX+1)', [0xdd, 0x6e, 1], 19)
    emit('OR (HL)', [0xb6], 7)
    emit('LD L,A', [0x6f], 4)
    emit('LD H,D', [0x62], 4)
    emit('LD E,(HL)', [0x5e], 7)
    emit('INC H', [0x24], 4)
    emit('LD A,(HL)', [0x7e], 7)
    emit('OR A', [0xb7], 4)
    jump('JR Z,long', 0x28, 'long', [7, 12], True)
    emit('ADD A,C', [0x81], 4)
    emit('BIT 3,A', [0xcb, 0x5f], 8)
    jump('JR Z,short_position', 0x28, 'short_position', [7, 12], True)
    emit('INC IX', [0xdd, 0x23], 10)
    a.label('short_position')
    emit('AND F7h', [0xe6, 0xf7], 7)
    emit('LD C,A', [0x4f], 4)
    emit('LD A,E', [0x7b], 4)
    emit('RET', [0xc9], 10)
    a.label('long')
    emit('INC IX', [0xdd, 0x23], 10)
    emit('LD B,E', [0x43], 4)
    emit('PUSH BC', [0xc5], 11)  # Saved rank in high byte, bit page in low.
    emit('LD A,C', [0x79], 4)
    emit('CP F0h', [0xfe, 0xf0], 7)
    jump('JR Z,aligned', 0x28, 'aligned', [7, 12], True)
    emit('LD H,C', [0x61], 4)
    emit('LD L,(IX+0)', [0xdd, 0x6e, 0], 19)
    emit('LD A,(HL)', [0x7e], 7)
    emit('LD E,A', [0x5f], 4)
    emit('LD L,C', [0x69], 4)
    emit('LD H,marker_page', [0x26, MARKERS >> 8], 7)
    emit('LD A,(HL)', [0x7e], 7)
    emit('OR E', [0xb3], 4)
    emit('LD B,A', [0x47], 4)
    emit('INC IX', [0xdd, 0x23], 10)
    jump('JR ready', 0x18, 'ready', 12, True)
    a.label('aligned')
    emit('LD B,80h', [0x06, 0x80], 7)
    a.label('ready')
    emit('LD A,D', [0x7a], 4)
    emit('SUB C0h', [0xd6, 0xc0], 7)
    emit('LD L,A', [0x6f], 4)
    emit('LD H,tail_pointer_page', [0x26, TAILS >> 8], 7)
    emit('LD E,(HL)', [0x5e], 7)
    emit('INC L', [0x2c], 4)
    emit('LD D,(HL)', [0x56], 7)
    emit('EX DE,HL', [0xeb], 4)
    emit('LD A,L', [0x7d], 4)
    emit('ADD A,tail_header_bytes', [0xc6, 2*max(0, layout['depth']-8)], 7)
    emit('LD E,A', [0x5f], 4)
    emit('LD A,H', [0x7c], 4)
    emit('ADC A,0', [0xce, 0], 7)
    emit('LD D,A', [0x57], 4)
    emit('POP AF', [0xf1], 10)  # A is the rank after eight bits.
    for level in range(8, layout['depth']):
        emit('SLA B', [0xcb, 0x20], 8)
        jump('JR NZ,have_bit', 0x20, f'have_{level}', [7, 12], True)
        emit('LD B,(IX+0)', [0xdd, 0x46, 0], 19)
        emit('INC IX', [0xdd, 0x23], 10)
        emit('RL B', [0xcb, 0x10], 8)
        a.label(f'have_{level}')
        emit('RLA', [0x17], 4)
        emit('SUB (HL)', [0x96], 7)
        emit('INC HL', [0x23], 6)
        jump('JP C,tail_leaf', 0xda, 'tail_leaf', 10)
        emit('INC HL', [0x23], 6)
    a.label('invalid'); emit('HALT invalid code', [0x76], 4)
    a.label('tail_leaf')
    emit('ADD A,(HL)', [0x86], 7)
    emit('ADD A,E', [0x83], 4)
    emit('LD E,A', [0x5f], 4)
    jump('JR NC,tail_symbol', 0x30, 'tail_symbol', [7, 12], True)
    emit('INC D', [0x14], 4)
    a.label('tail_symbol')
    emit('LD A,(DE)', [0x1a], 7)
    emit('PUSH AF', [0xf5], 11)
    emit('LD A,B', [0x78], 4)
    emit('LD L,A', [0x6f], 4)
    emit('LD H,position_page', [0x26, POSITIONS >> 8], 7)
    emit('LD C,(HL)', [0x4e], 7)
    emit('LD A,C', [0x79], 4)
    emit('CP F0h', [0xfe, 0xf0], 7)
    jump('JR Z,position_ready', 0x28, 'position_ready', [7, 12], True)
    emit('DEC IX', [0xdd, 0x2b], 10)
    a.label('position_ready')
    emit('POP AF', [0xf1], 10)
    emit('RET', [0xc9], 10)
    a.label('primitive_end')

    a.label('chunk')
    for name, code in [('EXX', 0xd9), ('LD A,B', 0x78), ('OR C', 0xb1), ('EXX', 0xd9)]:
        emit(name, [code], 4)
    emit('RET Z', [0xc8], [5, 11])
    listing.append(dict(address=a.pc, instruction='LD IX,(source)', tstates=20))
    a.emit(0xdd); a.abs16(0x2a, 'source')
    jump('LD A,(bit_page)', 0x3a, 'bit_page', 13)
    emit('LD C,A', [0x4f], 4)
    a.label('next')
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
    a.label('attribute_call'); jump('CALL attribute', 0xcd, 'attribute', 17)
    a.label('produced')
    for name, code, ticks in [('EXX', 0xd9, 4), ('LD (DE),A', 0x12, 7), ('INC DE', 0x13, 6),
                              ('DEC BC', 0x0b, 6), ('LD A,B', 0x78, 4), ('OR C', 0xb1, 4), ('EXX', 0xd9, 4)]:
        emit(name, [code], ticks)
    jump('JP NZ,next', 0xc2, 'next', 10)
    listing.append(dict(address=a.pc, instruction='LD (source),IX', tstates=20))
    a.emit(0xdd); a.abs16(0x22, 'source')
    emit('LD A,C', [0x79], 4)
    jump('LD (bit_page),A', 0x32, 'bit_page', 13)
    emit('RET', [0xc9], 10)
    a.label('state'); a.label('source'); a.word(0)
    a.label('bit_page'); a.emit(0xf0)
    a.label('end')
    return a.resolve(), dict(a.labels), listing, layout
