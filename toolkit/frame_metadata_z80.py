"""Expand FSC two-level sparse masks in the actual frame memory layout.

HL points to one contiguous encoded mask blob; output A4C0..A69F contains
384 bitmap and 96 attribute flags. BF80..BFBF holds 64 intermediate flags
(last four zero padding). Code at 7800 leaves cold initializer 7B00 intact.
This stage does not fetch bytes from ZX0 or parse a full packet header.
"""
from build_zxv_trd import MiniAssembler

CODE, MASKS, FLAGS = 0x7800, 0xa4c0, 0xbf80


def build():
    a, listing = MiniAssembler(CODE), []

    def emit(name, data, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage='metadata'))
        a.emit(*data)

    def word(name, opcode, value, ticks):
        emit(name, [opcode, value & 255, value >> 8], ticks)

    def jump(name, opcode, target, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage='metadata'))
        a.abs16(opcode, target)

    a.label('decode')
    emit('PUSH HL', [0xe5], 11); emit('POP IX', [0xdd, 0xe1], 14)
    word('LD DE,8', 0x11, 8, 10); emit('ADD HL,DE', [0x19], 11)
    word('LD DE,FLAGS', 0x11, FLAGS, 10); emit('LD B,8', [0x06, 8], 7)
    jump('CALL sparse_groups', 0xcd, 'sparse_groups', 17)
    emit('LD IX,FLAGS', [0xdd, 0x21, FLAGS & 255, FLAGS >> 8], 14)
    word('LD DE,MASKS', 0x11, MASKS, 10); emit('LD B,60', [0x06, 60], 7)
    jump('CALL sparse_groups', 0xcd, 'sparse_groups', 17)
    emit('RET', [0xc9], 10)

    a.label('sparse_groups')
    emit('LD A,(IX+0)', [0xdd, 0x7e, 0], 19); emit('INC IX', [0xdd, 0x23], 10)
    emit('LD C,A', [0x4f], 4); emit('OR A', [0xb7], 4)
    jump('JP Z,zero_group', 0xca, 'zero_group', 10)
    emit('CP FFh', [0xfe, 255], 7); jump('JP Z,full_group', 0xca, 'full_group', 10)
    for field in range(8):
        emit('XOR A', [0xaf], 4); emit('RLC C', [0xcb, 1], 8)
        listing.append(dict(address=a.pc, instruction='JR NC,zero_value', tstates=[7, 12], stage='metadata'))
        a.rel8(0x30, f'zero_value_{field}')
        emit('LD A,(HL)', [0x7e], 7); emit('INC HL', [0x23], 6)
        a.label(f'zero_value_{field}')
        emit('LD (DE),A', [0x12], 7)
        emit('INC E' if field < 7 else 'INC DE', [0x1c if field < 7 else 0x13], 4 if field < 7 else 6)
    jump('JP next_group', 0xc3, 'next_group', 10)
    a.label('zero_group')
    for field in range(8):
        emit('LD (DE),A', [0x12], 7)
        emit('INC E' if field < 7 else 'INC DE', [0x1c if field < 7 else 0x13], 4 if field < 7 else 6)
    jump('JP next_group', 0xc3, 'next_group', 10)
    a.label('full_group')
    emit('PUSH BC', [0xc5], 11)
    for _ in range(8):
        emit('LDI', [0xed, 0xa0], 16)
    emit('POP BC', [0xc1], 10)
    a.label('next_group')
    emit('DEC B', [0x05], 4); jump('JP NZ,sparse_groups', 0xc2, 'sparse_groups', 10)
    emit('RET', [0xc9], 10)
    a.label('end')
    if a.pc > 0x7b00:
        raise ValueError('metadata code overlaps initializer')
    return a.resolve(), a.labels, listing


def expected_tstates(encoded):
    """Entry through RET, excluding external CALL and pointer setup."""
    upper = encoded[:8]
    if len(upper) != 8 or upper[-1] & 15:
        raise ValueError('invalid upper masks')
    position, lower = 8, bytearray()
    for flags in upper:
        for bit in range(8):
            value = 0
            if flags & (128 >> bit):
                value = encoded[position]; position += 1
            lower.append(value)
    if position+sum(flag.bit_count() for flag in lower[:60]) != len(encoded):
        raise ValueError('incorrect mask payload length')
    def cost(flag):
        return 161 if flag == 0 else 227 if flag == 255 else 370+8*flag.bit_count()
    # Setup 138 T, plus the RET of each of the two helper calls (20 T).
    return 158+sum(map(cost, upper))+sum(map(cost, lower[:60]))
