"""Consume a continuous ZX0 block stream from the bank ring entirely on Z80.

Four-byte block header: decoded length u16, compressed length u15/stored bit.
take: BC=count, DE=fixed-RAM destination; returns advanced DE. Zero count is
a no-op. Block parsing, resumptions, history copies and wrap handling are
real machine code. The producer of compressed ring bytes remains external.
Reader code/state lives in bank 7 DB00..DFFF; fixed block loader at 7E90.
"""
import banked_zx0
from build_zxv_trd import MiniAssembler

CODE, LOADER = 0xdb00, 0x7e90


def build(zx0):
    listing = []

    def helpers(a):
        def emit(name, data, cycles):
            listing.append(dict(address=a.pc, instruction=name, tstates=cycles, stage='stream_input'))
            a.emit(*data)
        def addr(name, opcode, target, cycles):
            listing.append(dict(address=a.pc, instruction=name, tstates=cycles, stage='stream_input'))
            if isinstance(target, str): a.abs16(opcode, target)
            else:
                a.emit(*(opcode if isinstance(opcode, tuple) else (opcode,))); a.word(target)
        return emit, addr

    a = MiniAssembler(CODE); emit, addr = helpers(a)
    a.label('take')
    emit('LD A,B', [0x78], 4); emit('OR C', [0xb1], 4); emit('RET Z', [0xc8], [5, 11])
    addr('LD (pending),BC', (0xed, 0x43), 'pending', 20)
    addr('LD (destination),DE', (0xed, 0x53), 'destination', 20)
    a.label('next')
    addr('LD HL,(block_left)', 0x2a, 'block_left', 16)
    emit('LD A,H', [0x7c], 4); emit('OR L', [0xb5], 4)
    addr('JP NZ,have_block', 0xc2, 'have_block', 10)
    addr('CALL load_block', 0xcd, LOADER, 17)
    a.label('have_block')
    addr('LD BC,(pending)', (0xed, 0x4b), 'pending', 20)
    addr('LD HL,(block_left)', 0x2a, 'block_left', 16)
    emit('OR A', [0xb7], 4); emit('SBC HL,BC', [0xed, 0x42], 15)
    addr('JP NC,fits', 0xd2, 'fits', 10)
    addr('LD BC,(block_left)', (0xed, 0x4b), 'block_left', 20)
    addr('LD HL,0', 0x21, 0, 10)
    a.label('fits')
    addr('LD (block_left),HL', 0x22, 'block_left', 16)
    addr('LD (copy_count),BC', (0xed, 0x43), 'copy_count', 20)
    addr('LD HL,(pending)', 0x2a, 'pending', 16)
    emit('OR A', [0xb7], 4); emit('SBC HL,BC', [0xed, 0x42], 15)
    addr('LD (pending),HL', 0x22, 'pending', 16)
    addr('LD HL,(position)', 0x2a, 'position', 16)
    emit('PUSH HL', [0xe5], 11); emit('ADD HL,BC', [0x09], 11)
    addr('LD (position),HL', 0x22, 'position', 16)
    addr('LD DE,E000', 0x11, banked_zx0.OUTPUT, 10)
    emit('ADD HL,DE', [0x19], 11)
    addr('LD (slice_target),HL', 0x22, zx0['slice_target'], 16)
    # Lookahead may have already produced these bytes. Compare counts, not
    # absolute addresses, so output end 0000 means 8192 rather than zero.
    addr('LD HL,(slice_output)', 0x2a, zx0['slice_output'], 16)
    addr('LD DE,2000', 0x11, 8192, 10); emit('ADD HL,DE', [0x19], 11)
    addr('LD DE,(position)', (0xed, 0x5b), 'position', 20)
    emit('OR A', [0xb7], 4); emit('SBC HL,DE', [0xed, 0x52], 15)
    addr('CALL C,slice_until', 0xdc, zx0['slice_until'], [10, 17])
    emit('POP HL', [0xe1], 10)
    addr('LD DE,E000', 0x11, banked_zx0.OUTPUT, 10); emit('ADD HL,DE', [0x19], 11)
    addr('LD DE,(destination)', (0xed, 0x5b), 'destination', 20)
    addr('LD BC,(copy_count)', (0xed, 0x4b), 'copy_count', 20)
    emit('LDIR', [0xed, 0xb0], [16, 21])
    addr('LD (destination),DE', (0xed, 0x53), 'destination', 20)
    addr('LD HL,(pending)', 0x2a, 'pending', 16)
    emit('LD A,H', [0x7c], 4); emit('OR L', [0xb5], 4)
    addr('JP NZ,next', 0xc2, 'next', 10)
    addr('LD DE,(destination)', (0xed, 0x5b), 'destination', 20)
    emit('RET', [0xc9], 10)
    a.label('state')
    for name in ('pending', 'destination', 'copy_count', 'block_left', 'position'):
        a.label(name); a.word(0)
    a.label('end')
    code, labels = a.resolve(), dict(a.labels)
    if a.pc > 0xe000: raise ValueError('reader overlaps ZX0 history')

    a = MiniAssembler(LOADER); emit, addr = helpers(a)
    a.label('load_block')
    addr('LD HL,4', 0x21, 4, 10)
    addr('LD (remaining),HL', 0x22, zx0['remaining'], 16)
    addr('CALL refill_header', 0xcd, zx0['refill'], 17)
    addr('LD HL,(header_length)', 0x2a, banked_zx0.INPUT, 16)
    emit('LD A,H', [0x7c], 4); emit('OR L', [0xb5], 4)
    addr('JP Z,fatal', 0xca, zx0['fatal'], 10)
    addr('LD (block_length),HL', 0x22, zx0['block_length'], 16)
    addr('LD (block_left),HL', 0x22, labels['block_left'], 16)
    addr('LD DE,8193', 0x11, 8193, 10)
    emit('OR A', [0xb7], 4); emit('SBC HL,DE', [0xed, 0x52], 15)
    addr('JP NC,fatal', 0xd2, zx0['fatal'], 10)
    addr('LD HL,(block_length)', 0x2a, zx0['block_length'], 16)
    addr('LD DE,E000', 0x11, banked_zx0.OUTPUT, 10); emit('ADD HL,DE', [0x19], 11)
    addr('LD (block_end),HL', 0x22, zx0['block_end'], 16)
    addr('LD HL,(header_payload)', 0x2a, banked_zx0.INPUT+2, 16)
    emit('LD A,H', [0x7c], 4); emit('AND 80h', [0xe6, 128], 7)
    addr('LD (block_stored),A', 0x32, zx0['block_stored'], 13)
    emit('RES 7,H', [0xcb, 0xbc], 8)
    addr('LD (remaining),HL', 0x22, zx0['remaining'], 16)
    emit('LD A,H', [0x7c], 4); emit('OR L', [0xb5], 4)
    addr('JP Z,fatal', 0xca, zx0['fatal'], 10)
    addr('LD A,(block_stored)', 0x3a, zx0['block_stored'], 13)
    emit('OR A', [0xb7], 4)
    addr('JP Z,compressed_length', 0xca, 'compressed_length', 10)
    addr('LD DE,(block_length)', (0xed, 0x5b), zx0['block_length'], 20)
    emit('OR A', [0xb7], 4); emit('SBC HL,DE', [0xed, 0x52], 15)
    addr('JP NZ,fatal', 0xc2, zx0['fatal'], 10)
    emit('ADD HL,DE', [0x19], 11)
    a.label('compressed_length')
    addr('LD DE,16385', 0x11, 16385, 10)
    emit('OR A', [0xb7], 4); emit('SBC HL,DE', [0xed, 0x52], 15)
    addr('JP NC,fatal', 0xd2, zx0['fatal'], 10)
    addr('LD HL,0', 0x21, 0, 10)
    addr('LD (position),HL', 0x22, labels['position'], 16)
    addr('LD HL,E000', 0x21, banked_zx0.OUTPUT, 10)
    addr('LD (slice_target),HL', 0x22, zx0['slice_target'], 16)
    # Start suspended at zero output. Later reads can resume or use lookahead.
    addr('CALL begin', 0xcd, zx0['begin'], 17)
    emit('RET', [0xc9], 10)
    a.label('end')
    if a.pc > 0x8000: raise ValueError('loader overlaps frame reconstruction')
    labels.update(loader=a.labels['load_block'], loader_end=a.labels['end'])
    return code, a.resolve(), labels, listing
