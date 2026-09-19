"""Z80 FAP1 packet reader: ZX0 input -> AY queue -> prepared native screen.

Code in bank 7 DC00..DFFF; paging bridges in fixed RAM 7F00..7FFF.
next_frame does not publish the screen: publish_bridge is a separate call
so a later scheduler can wait for the six-field boundary before switching.
Global Huffman tables are initialized separately at startup.
"""
from build_zxv_trd import MiniAssembler
from frame_output_pipeline import INPUT, INPUT_END, VECTORS, MAP
from causal_tile_z80 import CACHE_MAP

CODE, BRIDGE, HEADER = 0xdc00, 0x7f00, 0xba50


def build(zx0, reader, wrapper, draw, metadata, audio):
    listing = []

    def helpers(a):
        def emit(name, data, ticks):
            listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage='packet'))
            a.emit(*data)
        def addr(name, opcode, value, ticks):
            listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage='packet'))
            if isinstance(value, str): a.abs16(opcode, value)
            else:
                a.emit(*(opcode if isinstance(opcode, tuple) else (opcode,))); a.word(value)
        def take(count, destination=None):
            if destination is not None: addr('LD DE,destination', 0x11, destination, 10)
            addr('LD BC,count', 0x01, count, 10)
            addr('CALL take', 0xcd, reader['take'], 17)
        return emit, addr, take

    a = MiniAssembler(BRIDGE); emit, addr, take = helpers(a)
    a.label('prepare_bridge')
    addr('LD A,(saved_page)', 0x3a, draw['saved_page'], 13)
    addr('LD BC,7FFD', 0x01, 0x7ffd, 10); emit('OUT (C),A', [0xed, 0x79], 12)
    addr('CALL prepare', 0xcd, wrapper['run'], 17)
    addr('JP restore_bank7', 0xc3, 'restore_bank7', 10)
    a.label('publish_bridge')
    addr('CALL publish', 0xcd, wrapper['publish'], 17)
    a.label('restore_bank7')
    addr('LD A,(saved_page)', 0x3a, draw['saved_page'], 13)
    emit('OR 1', [0xf6, 1], 7)
    addr('LD (history_page),A', 0x32, zx0['history_page'], 13)
    addr('LD BC,7FFD', 0x01, 0x7ffd, 10); emit('OUT (C),A', [0xed, 0x79], 12)
    emit('RET', [0xc9], 10)
    a.label('end')
    bridge, labels = a.resolve(), dict(a.labels)
    if a.pc > 0x8000: raise ValueError('paging bridge overlaps reconstruction')

    a = MiniAssembler(CODE); emit, addr, take = helpers(a)
    a.label('next_frame')
    emit('LD A,6', [0x3e, 6], 7); addr('LD (ay_left),A', 0x32, 'ay_left', 13)
    addr('LD DE,AY scratch', 0x11, INPUT, 10)
    a.label('read_tick')
    take(1)
    emit('DEC DE', [0x1b], 6); emit('LD A,(DE)', [0x1a], 7); emit('INC DE', [0x13], 6)
    emit('CP 12', [0xfe, 12], 7); addr('JP NC,fatal', 0xd2, zx0['fatal'], 10)
    emit('ADD A,A', [0x87], 4); emit('LD C,A', [0x4f], 4); emit('LD B,0', [0x06, 0], 7)
    addr('CALL take pairs', 0xcd, reader['take'], 17)
    addr('LD A,(ay_left)', 0x3a, 'ay_left', 13); emit('DEC A', [0x3d], 4)
    addr('LD (ay_left),A', 0x32, 'ay_left', 13); addr('JP NZ,read_tick', 0xc2, 'read_tick', 10)
    addr('LD HL,AY scratch', 0x21, INPUT, 10)
    addr('CALL audio_enqueue_six', 0xcd, audio['audio_enqueue_six'], 17)
    take(7, HEADER)
    addr('LD A,(flags)', 0x3a, HEADER, 13); emit('AND 38h', [0xe6, 0x38], 7)
    addr('JP NZ,fatal', 0xc2, zx0['fatal'], 10)
    addr('LD A,(flags)', 0x3a, HEADER, 13); emit('AND 80h', [0xe6, 0x80], 7)
    addr('LD (cache_flag),A', 0x32, wrapper['cache_flag'], 13)
    addr('LD A,(flags)', 0x3a, HEADER, 13); emit('AND 40h', [0xe6, 0x40], 7)
    addr('LD (raw_attribute_flag),A', 0x32, wrapper['raw_attribute_flag'], 13)
    addr('LD HL,(mask_length)', 0x2a, HEADER+1, 16)
    addr('LD DE,8', 0x11, 8, 10); emit('OR A', [0xb7], 4); emit('SBC HL,DE', [0xed, 0x52], 15)
    addr('JP C,fatal', 0xda, zx0['fatal'], 10)
    addr('LD DE,541', 0x11, 541, 10); emit('OR A', [0xb7], 4); emit('SBC HL,DE', [0xed, 0x52], 15)
    addr('JP NC,fatal', 0xd2, zx0['fatal'], 10)
    addr('LD HL,(coded_length)', 0x2a, HEADER+3, 16)
    addr('LD DE,(literal_length)', (0xed, 0x5b), HEADER+5, 20)
    emit('ADD HL,DE', [0x19], 11); addr('JP C,fatal', 0xda, zx0['fatal'], 10)
    addr('LD DE,value_capacity-1', 0x11, INPUT_END-INPUT-1, 10)
    emit('OR A', [0xb7], 4); emit('SBC HL,DE', [0xed, 0x52], 15)
    addr('JP NC,fatal', 0xd2, zx0['fatal'], 10)
    take(3, CACHE_MAP); take(192, VECTORS)
    addr('LD DE,mask_scratch', 0x11, INPUT, 10)
    addr('LD BC,(mask_length)', (0xed, 0x4b), HEADER+1, 20)
    addr('CALL take masks', 0xcd, reader['take'], 17)
    addr('LD HL,mask_scratch', 0x21, INPUT, 10)
    addr('CALL expand_masks', 0xcd, metadata['decode'], 17)
    take(80, MAP)
    addr('LD DE,values', 0x11, INPUT, 10)
    addr('LD BC,(coded_length)', (0xed, 0x4b), HEADER+3, 20)
    addr('CALL take coded', 0xcd, reader['take'], 17)
    emit('XOR A', [0xaf], 4); emit('LD (DE),A', [0x12], 7); emit('INC DE', [0x13], 6)
    addr('LD (literal_pointer),DE', (0xed, 0x53), wrapper['literal_pointer'], 20)
    addr('LD BC,(literal_length)', (0xed, 0x4b), HEADER+5, 20)
    addr('CALL take literals', 0xcd, reader['take'], 17)
    emit('XOR A', [0xaf], 4); emit('LD (DE),A', [0x12], 7)
    addr('CALL prepare_bridge', 0xcd, labels['prepare_bridge'], 17)
    emit('RET', [0xc9], 10)
    a.label('state'); a.label('ay_left'); a.emit(0); a.label('end')
    if a.pc > 0xe000: raise ValueError('packet reader overlaps ZX0 history')
    labels = dict(**a.labels, prepare_bridge=labels['prepare_bridge'], publish_bridge=labels['publish_bridge'],
                  bridge_end=labels['end'])
    return a.resolve(), bridge, labels, listing
