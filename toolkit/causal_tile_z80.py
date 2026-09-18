"""Causal in-place FPD1 frame reconstruction with a 16-row motion cache.

Consumes expanded frame vectors/bitmaps/attribute masks and contiguous
Huffman input. The entire motion predictor and masked value application
execute on Z80. History is one 3840-byte compact frame; 1024 cache bytes
hold 16 rows with horizontal zero padding. No host-generated predictions.
Optional hybrid=True accepts FHT1 inline literals, raster-order attributes
and a validated per-frame motion-cache flag. Default FPD1 code is unchanged.
This is not yet a streamed/displaying player: metadata/ZX0 decoding,
window refill, screen expansion, paging and disk delivery are separate.
"""
from build_zxv_trd import MiniAssembler
import prefix_huffman_z80 as prefix

CODE, FRAME, CACHE = prefix.CODE, 0x6400, 0x7400
VECTOR_X, VECTOR_Y, VECTOR_PHASE, ROW_LOW, ROW_HIGH = 0x9800, 0x9900, 0x9a00, 0x9b00, 0x9c00


def build(tables, mapping, offsets, *, skip_empty=False, hybrid=False, raw_kind=None):
    if raw_kind is not None and (raw_kind not in (0, 1) or not hybrid or not skip_empty):
        raise ValueError('raw direct/XOR patches require hybrid and empty-half skips')
    if len(offsets) != 81 or offsets[0] != (0, 0) or set(offsets) != {(x, y) for x in range(-4, 5) for y in range(-4, 5)}:
        raise ValueError('expected the complete +/-4 motion alphabet')
    original, labels, instructions, layout = prefix.build(tables, mapping)
    end = labels['primitive_end']
    a = MiniAssembler(CODE)
    a.emit(*original[:end-CODE])
    a.labels.update({name: address for name, address in labels.items() if address < end})
    listing = [dict(row, stage='huffman') for row in instructions if row['address'] < end]
    stage = 'control'

    def emit(name, data, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage=stage)); a.emit(*data)

    def wordop(name, opcode, value, ticks):
        emit(name, [opcode, value & 255, value >> 8], ticks)

    def jump(name, opcode, target, ticks, relative=False):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage=stage))
        (a.rel8 if relative else a.abs16)(opcode, target)

    def load(name, opcode, target, ticks):
        jump(name, opcode, target, ticks)

    def cache_advance(tag, amount):
        # Source/cache column is 0..34, so only crossing a 256-byte page
        # requires wrapping the cache's high byte. Padding avoids edge reads.
        emit('LD A,E', [0x7b], 4); emit(f'ADD A,{amount}', [0xc6, amount], 7)
        emit('LD E,A', [0x5f], 4)
        jump('JR NC,cache_page_ready', 0x30, tag, [7, 12], True)
        emit('INC D', [0x14], 4); emit('LD A,D', [0x7a], 4)
        emit('AND 3', [0xe6, 3], 7); emit('OR cache_page', [0xf6, CACHE >> 8], 7)
        emit('LD D,A', [0x57], 4); a.label(tag)

    def next_output_row():
        emit('LD A,L', [0x7d], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD L,A', [0x6f], 4)

    a.label('frame')
    load('LD IX,(source)', (0xdd, 0x2a), 'source', 20)
    load('LD A,(bit_page)', 0x3a, 'bit_page', 13)
    emit('EXX', [0xd9], 4); emit('LD C,A', [0x4f], 4); emit('EXX', [0xd9], 4)
    wordop('LD HL,compact_frame', 0x21, FRAME, 10); load('LD (target),HL', 0x22, 'target', 16)
    if not hybrid:
        wordop('LD HL,attributes', 0x21, FRAME+3072, 10); load('LD (attr_target),HL', 0x22, 'attr_target', 16)
    emit('XOR A', [0xaf], 4); load('LD (stripe_y),A', 0x32, 'stripe_y', 13)
    emit('LD A,12', [0x3e, 12], 7); load('LD (stripes_left),A', 0x32, 'stripes_left', 13)
    if hybrid:
        load('LD A,(cache_enabled)', 0x3a, 'cache_enabled', 13)
        emit('OR A', [0xb7], 4); jump('JP Z,stripe', 0xca, 'stripe', 10)
    # The top four virtual rows are black. Padding columns stay zero from
    # cache initialization; no routine writes them.
    wordop('LD DE,top_virtual_cache_rows', 0x11, CACHE+12*64+1, 10)
    emit('LD B,4', [0x06, 4], 7); jump('CALL cache_zero', 0xcd, 'cache_zero', 17)
    wordop('LD HL,compact_frame', 0x21, FRAME, 10)
    wordop('LD DE,cache_first_visible', 0x11, CACHE+1, 10)
    emit('LD B,12', [0x06, 12], 7); jump('CALL cache_copy', 0xcd, 'cache_copy', 17)
    a.label('save_cache')
    load('LD (cache_read),HL', 0x22, 'cache_read', 16)
    load('LD (cache_write),DE', (0xed, 0x53), 'cache_write', 20)
    a.label('stripe')
    emit('LD A,16', [0x3e, 16], 7); load('LD (tiles_left),A', 0x32, 'tiles_left', 13)
    a.label('tile')
    load('LD HL,(vectors)', 0x2a, 'vectors', 16)
    emit('LD A,(HL)', [0x7e], 7); emit('INC HL', [0x23], 6)
    load('LD (vectors),HL', 0x22, 'vectors', 16)
    if raw_kind is not None:
        emit('PUSH AF', [0xf5], 11); emit('AND 7Fh', [0xe6, 127], 7)
        jump('CALL NZ,motion', 0xc4, 'motion', [10, 17])
        emit('POP AF', [0xf1], 10); emit('BIT 7,A', [0xcb, 0x7f], 8)
        jump('JP NZ,raw_tile', 0xc2, 'raw_tile', 10)
        jump('CALL patches', 0xcd, 'patches', 17)
        jump('JP tile_done', 0xc3, 'tile_done', 10)
        a.label('raw_tile'); jump('CALL raw_patches', 0xcd, 'raw_patches', 17)
        a.label('tile_done')
    elif hybrid:
        emit('CP literal_vector', [0xfe, 82], 7)
        jump('JP Z,literal_tile', 0xca, 'literal_tile', 10)
    if raw_kind is None:
        emit('OR A', [0xb7], 4); jump('CALL NZ,motion', 0xc4, 'motion', [10, 17])
        jump('CALL patches', 0xcd, 'patches', 17)
    if hybrid and raw_kind is None:
        jump('JP tile_done', 0xc3, 'tile_done', 10)
        a.label('literal_tile')
        load('LD HL,(bitmap_masks)', 0x2a, 'bitmap_masks', 16)
        emit('INC HL', [0x23], 6); emit('INC HL', [0x23], 6)
        load('LD (bitmap_masks),HL', 0x22, 'bitmap_masks', 16)
        jump('CALL literal', 0xcd, 'literal', 17)
        a.label('tile_done')
    load('LD HL,(target)', 0x2a, 'target', 16)
    emit('INC L', [0x2c], 4); emit('INC L', [0x2c], 4)
    load('LD (target),HL', 0x22, 'target', 16)
    if not hybrid:
        load('LD HL,(attr_target)', 0x2a, 'attr_target', 16)
        emit('INC HL', [0x23], 6); emit('INC HL', [0x23], 6)
        load('LD (attr_target),HL', 0x22, 'attr_target', 16)
    load('LD HL,tiles_left', 0x21, 'tiles_left', 10)
    emit('DEC (HL)', [0x35], 11); jump('JP NZ,tile', 0xc2, 'tile', 10)
    load('LD HL,stripes_left', 0x21, 'stripes_left', 10)
    emit('DEC (HL)', [0x35], 11); jump('JP Z,frame_done', 0xca, 'frame_done', 10)
    load('LD HL,(target)', 0x2a, 'target', 16); wordop('LD DE,224', 0x11, 224, 10)
    emit('ADD HL,DE', [0x19], 11); load('LD (target),HL', 0x22, 'target', 16)
    if not hybrid:
        load('LD HL,(attr_target)', 0x2a, 'attr_target', 16); wordop('LD DE,32', 0x11, 32, 10)
        emit('ADD HL,DE', [0x19], 11); load('LD (attr_target),HL', 0x22, 'attr_target', 16)
    load('LD A,(stripe_y)', 0x3a, 'stripe_y', 13)
    emit('ADD A,8', [0xc6, 8], 7); load('LD (stripe_y),A', 0x32, 'stripe_y', 13)
    if hybrid:
        load('LD A,(cache_enabled)', 0x3a, 'cache_enabled', 13)
        emit('OR A', [0xb7], 4); jump('JP Z,stripe', 0xca, 'stripe', 10)
    load('LD HL,(cache_read)', 0x2a, 'cache_read', 16)
    load('LD DE,(cache_write)', (0xed, 0x5b), 'cache_write', 20)
    load('LD A,(stripes_left)', 0x3a, 'stripes_left', 13)
    emit('CP 1', [0xfe, 1], 7); jump('JR Z,last_prefetch', 0x28, 'last_prefetch', [7, 12], True)
    emit('LD B,8', [0x06, 8], 7); jump('CALL cache_copy', 0xcd, 'cache_copy', 17)
    jump('JP save_cache', 0xc3, 'save_cache', 10)
    a.label('last_prefetch')
    emit('LD B,4', [0x06, 4], 7); jump('CALL cache_copy', 0xcd, 'cache_copy', 17)
    emit('LD B,4', [0x06, 4], 7); jump('CALL cache_zero', 0xcd, 'cache_zero', 17)
    jump('JP save_cache', 0xc3, 'save_cache', 10)
    a.label('frame_done')
    if hybrid:
        jump('CALL attribute_pass', 0xcd, 'attribute_pass', 17)
    load('LD (source),IX', (0xdd, 0x22), 'source', 20)
    emit('EXX', [0xd9], 4); emit('LD A,C', [0x79], 4); emit('EXX', [0xd9], 4)
    load('LD (bit_page),A', 0x32, 'bit_page', 13); emit('RET', [0xc9], 10)

    if hybrid and raw_kind is None:
        stage = 'literal'
        a.label('literal')
        # IX points at the current Huffman byte. Skip its unused low bits;
        # the format requires those bits to be zero. Use the alternate bank
        # so LDI cannot destroy traversal registers, and preserve reservoir C.
        emit('EXX', [0xd9], 4); emit('LD A,C', [0x79], 4)
        emit('AND 7', [0xe6, 7], 7); jump('JP Z,literal_aligned', 0xca, 'literal_aligned', 10)
        emit('INC IX', [0xdd, 0x23], 10); a.label('literal_aligned')
        emit('LD C,F0h', [0x0e, 0xf0], 7); emit('PUSH BC', [0xc5], 11)
        emit('PUSH IX', [0xdd, 0xe5], 15); emit('POP HL', [0xe1], 10)
        load('LD DE,(target)', (0xed, 0x5b), 'target', 20)
        for row in range(8):
            emit('LDI', [0xed, 0xa0], 16); emit('LDI', [0xed, 0xa0], 16)
            if row < 7:
                emit('LD A,E', [0x7b], 4); emit('ADD A,30', [0xc6, 30], 7); emit('LD E,A', [0x5f], 4)
        emit('PUSH HL', [0xe5], 11); emit('POP IX', [0xdd, 0xe1], 14)
        emit('POP BC', [0xc1], 10); emit('EXX', [0xd9], 4); emit('RET', [0xc9], 10)

    if raw_kind is not None:
        stage = 'raw_patch'
        a.label('raw_patches')
        load('LD HL,(bitmap_masks)', 0x2a, 'bitmap_masks', 16)
        emit('LD B,(HL)', [0x46], 7); emit('INC HL', [0x23], 6)
        emit('LD C,(HL)', [0x4e], 7); emit('INC HL', [0x23], 6)
        load('LD (bitmap_masks),HL', 0x22, 'bitmap_masks', 16)
        # Cache/motion have already formed the predictor. Align the shared
        # bit input, then read raw bytes with HL while primary BC keeps masks.
        emit('EXX', [0xd9], 4); emit('LD A,C', [0x79], 4)
        emit('AND 7', [0xe6, 7], 7); jump('JP Z,raw_aligned', 0xca, 'raw_aligned', 10)
        emit('INC IX', [0xdd, 0x23], 10); a.label('raw_aligned')
        emit('LD C,F0h', [0x0e, 0xf0], 7); emit('EXX', [0xd9], 4)
        emit('PUSH IX', [0xdd, 0xe5], 15); emit('POP HL', [0xe1], 10)
        load('LD DE,(target)', (0xed, 0x5b), 'target', 20)
        for field in range(16):
            if field == 8:
                a.label('raw_skip_half_0')
                emit('LD A,E', [0x7b], 4); emit('ADD A,128', [0xc6, 128], 7); emit('LD E,A', [0x5f], 4)
                a.label('raw_second_half'); emit('LD B,C', [0x41], 4)
            if field in (0, 8):
                emit('LD A,B', [0x78], 4); emit('OR A', [0xb7], 4)
                jump('JP Z,raw_empty_half', 0xca, 'raw_skip_half_0' if field == 0 else 'raw_done', 10)
            emit('SLA B', [0xcb, 0x20], 8); jump('JP NC,raw_keep', 0xd2, f'raw_keep_{field}', 10)
            a.label(f'raw_value_{field}')
            if raw_kind == 1:
                emit('LD A,(DE)', [0x1a], 7); emit('XOR (HL)', [0xae], 7)
            else:
                emit('LD A,(HL)', [0x7e], 7)
            emit('INC HL', [0x23], 6); emit('LD (DE),A', [0x12], 7)
            a.label(f'raw_keep_{field}')
            if field < 15:
                if not field % 2:
                    emit('INC E', [0x1c], 4)
                else:
                    emit('LD A,E', [0x7b], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD E,A', [0x5f], 4)
            if field == 7:
                jump('JP raw_second_half', 0xc3, 'raw_second_half', 10)
        a.label('raw_done')
        emit('PUSH HL', [0xe5], 11); emit('POP IX', [0xdd, 0xe1], 14); emit('RET', [0xc9], 10)

    stage = 'cache'
    for zero in (False, True):
        name = 'cache_zero' if zero else 'cache_copy'
        a.label(name)
        if zero:
            emit('XOR A', [0xaf], 4)
            for _ in range(32):
                emit('LD (DE),A', [0x12], 7); emit('INC E', [0x1c], 4)
        else:
            emit('PUSH BC', [0xc5], 11)
            for _ in range(32):
                emit('LDI', [0xed, 0xa0], 16)
            emit('POP BC', [0xc1], 10)
        cache_advance(name+'_advanced', 32)
        jump('DJNZ cache_row', 0x10, name, [8, 13], True)
        emit('RET', [0xc9], 10)

    stage = 'motion'
    a.label('motion')
    emit('CP zero_vector', [0xfe, len(offsets)], 7)
    jump('JP Z,clear_tile', 0xca, 'clear_tile', 10)
    emit('LD L,A', [0x6f], 4); emit('LD H,vector_x', [0x26, VECTOR_X >> 8], 7)
    emit('LD A,(HL)', [0x7e], 7); emit('LD B,A', [0x47], 4)
    load('LD A,(target_low)', 0x3a, 'target', 13)
    emit('AND 31', [0xe6, 31], 7); emit('ADD A,B', [0x80], 4); emit('INC A', [0x3c], 4)
    emit('LD C,A', [0x4f], 4)
    emit('INC H', [0x24], 4); emit('LD B,(HL)', [0x46], 7)
    emit('INC H', [0x24], 4); emit('LD A,(HL)', [0x7e], 7)
    load('LD (phase),A', 0x32, 'phase', 13)
    load('LD A,(stripe_y)', 0x3a, 'stripe_y', 13)
    emit('ADD A,B', [0x80], 4); emit('AND 15', [0xe6, 15], 7)
    emit('LD L,A', [0x6f], 4); emit('LD H,row_low', [0x26, ROW_LOW >> 8], 7)
    emit('LD A,(HL)', [0x7e], 7); emit('ADD A,C', [0x81], 4); emit('LD E,A', [0x5f], 4)
    emit('INC H', [0x24], 4); emit('LD D,(HL)', [0x56], 7)
    load('LD HL,(target)', 0x2a, 'target', 16)
    emit('LD B,8', [0x06, 8], 7); load('LD A,(phase)', 0x3a, 'phase', 13)
    for phase in (0, 2, 4):
        emit(f'CP {phase}', [0xfe, phase], 7)
        jump(f'JP Z,predict_{phase}', 0xca, f'predict_{phase}', 10)
    jump('JP predict_6', 0xc3, 'predict_6', 10)
    for phase in (0, 2, 4, 6):
        a.label(f'predict_{phase}')
        if not phase:
            emit('LD A,(DE)', [0x1a], 7); emit('LD (HL),A', [0x77], 7)
            emit('INC E', [0x1c], 4); emit('INC L', [0x2c], 4)
            emit('LD A,(DE)', [0x1a], 7); emit('LD (HL),A', [0x77], 7)
        else:
            emit('PUSH BC', [0xc5], 11); emit('PUSH HL', [0xe5], 11)
            emit('LD A,(DE)', [0x1a], 7); emit('INC E', [0x1c], 4); emit('LD L,A', [0x6f], 4)
            emit('LD H,left_shift', [0x26, 0xf0+phase], 7); emit('LD B,(HL)', [0x46], 7)
            emit('LD A,(DE)', [0x1a], 7); emit('LD L,A', [0x6f], 4)
            emit('LD H,right_shift', [0x26, 0xf8+phase], 7); emit('LD A,(HL)', [0x7e], 7)
            emit('OR B', [0xb0], 4); emit('LD B,A', [0x47], 4)
            emit('LD H,left_shift', [0x26, 0xf0+phase], 7); emit('LD C,(HL)', [0x4e], 7)
            emit('INC E', [0x1c], 4); emit('LD A,(DE)', [0x1a], 7); emit('LD L,A', [0x6f], 4)
            emit('LD H,right_shift', [0x26, 0xf8+phase], 7); emit('LD A,(HL)', [0x7e], 7)
            emit('OR C', [0xb1], 4); emit('POP HL', [0xe1], 10)
            emit('LD (HL),B', [0x70], 7); emit('INC L', [0x2c], 4); emit('LD (HL),A', [0x77], 7)
            emit('POP BC', [0xc1], 10)
        cache_advance(f'predict_{phase}_advanced', 63 if not phase else 62)
        next_output_row()
        jump('DJNZ predict_row', 0x10, f'predict_{phase}', [8, 13], True)
        emit('RET', [0xc9], 10)
    a.label('clear_tile')
    load('LD HL,(target)', 0x2a, 'target', 16); emit('LD B,8', [0x06, 8], 7)
    a.label('clear_row'); emit('XOR A', [0xaf], 4)
    emit('LD (HL),A', [0x77], 7); emit('INC L', [0x2c], 4); emit('LD (HL),A', [0x77], 7)
    next_output_row(); jump('DJNZ clear_row', 0x10, 'clear_row', [8, 13], True); emit('RET', [0xc9], 10)

    stage = 'patch'
    a.label('patches')
    load('LD HL,(bitmap_masks)', 0x2a, 'bitmap_masks', 16)
    emit('LD B,(HL)', [0x46], 7); emit('INC HL', [0x23], 6)
    emit('LD C,(HL)', [0x4e], 7); emit('INC HL', [0x23], 6)
    load('LD (bitmap_masks),HL', 0x22, 'bitmap_masks', 16)
    emit('LD A,B', [0x78], 4); emit('OR C', [0xb1], 4)
    jump('JP Z,attributes', 0xca, 'attributes', 10)
    load('LD DE,(target)', (0xed, 0x5b), 'target', 20)
    for field in range(16):
        if field == 8:
            if skip_empty:
                a.label('skip_half_0')
                # A skipped first half still advances the raster by four rows.
                # Normal first-half traversal already arrived here via JP.
                emit('LD A,E', [0x7b], 4); emit('ADD A,128', [0xc6, 128], 7); emit('LD E,A', [0x5f], 4)
                a.label('second_half')
            emit('LD B,C', [0x41], 4)
        if skip_empty and field in (0, 8):
            emit('LD A,B', [0x78], 4); emit('OR A', [0xb7], 4)
            jump('JP Z,empty_bitmap_half', 0xca, 'skip_half_0' if field == 0 else 'attributes', 10)
        emit('SLA B', [0xcb, 0x20], 8); jump('JP NC,keep_bitmap', 0xd2, f'keep_bm_{field}', 10)
        emit('LD A,(DE)', [0x1a], 7); emit('EXX', [0xd9], 4)
        jump('CALL bitmap', 0xcd, 'bitmap', 17); emit('EXX', [0xd9], 4); emit('LD (DE),A', [0x12], 7)
        a.label(f'keep_bm_{field}')
        if field < 15:
            if not field % 2:
                emit('INC E', [0x1c], 4)
            else:
                emit('LD A,E', [0x7b], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD E,A', [0x5f], 4)
        if skip_empty and field == 7:
            jump('JP second_half', 0xc3, 'second_half', 10)
    a.label('attributes')
    if hybrid:
        emit('RET', [0xc9], 10)
        stage = 'attribute_pass'
        a.label('attribute_pass')
        load('LD HL,(attribute_masks)', 0x2a, 'attribute_masks', 16)
        wordop('LD DE,attributes', 0x11, FRAME+3072, 10)
        a.label('attribute_mask')
        emit('LD A,(HL)', [0x7e], 7); emit('INC HL', [0x23], 6)
        emit('OR A', [0xb7], 4); jump('JP Z,attribute_empty', 0xca, 'attribute_empty', 10)
        emit('LD B,A', [0x47], 4)
        for field in range(8):
            emit('SLA B', [0xcb, 0x20], 8); jump('JP NC,keep_attribute', 0xd2, f'keep_raster_{field}', 10)
            emit('LD A,(DE)', [0x1a], 7); emit('LD C,A', [0x4f], 4); emit('EXX', [0xd9], 4)
            jump('CALL attribute', 0xcd, 'attribute', 17); emit('EXX', [0xd9], 4)
            emit('XOR C', [0xa9], 4); emit('LD (DE),A', [0x12], 7)
            a.label(f'keep_raster_{field}')
            emit('INC E' if field < 7 else 'INC DE', [0x1c if field < 7 else 0x13], 4 if field < 7 else 6)
        jump('JP attribute_next', 0xc3, 'attribute_next', 10)
        a.label('attribute_empty')
        emit('LD A,E', [0x7b], 4); emit('ADD A,8', [0xc6, 8], 7); emit('LD E,A', [0x5f], 4)
        jump('JR NC,attribute_next', 0x30, 'attribute_next', [7, 12], True)
        emit('INC D', [0x14], 4)
        a.label('attribute_next')
        emit('LD A,D', [0x7a], 4); emit('CP attribute_end', [0xfe, (FRAME+3840) >> 8], 7)
        jump('JP NZ,attribute_mask', 0xc2, 'attribute_mask', 10)
        load('LD (attribute_masks),HL', 0x22, 'attribute_masks', 16); emit('RET', [0xc9], 10)
    else:
        emit_tile_attributes(a, emit, load, jump, skip_empty)
    a.label('state')
    for name in ('source', 'vectors', 'bitmap_masks', 'attribute_masks', 'target', 'attr_target', 'cache_read', 'cache_write'):
        a.label(name); a.word(0)
    for name, value in [('bit_page', 0xf0), ('stripe_y', 0), ('stripes_left', 0), ('tiles_left', 0), ('phase', 0), ('attr_bits', 0)]:
        a.label(name); a.emit(value)
    if hybrid:
        a.label('cache_enabled'); a.emit(1)
    a.label('end')
    if a.pc > VECTOR_X:
        raise ValueError('frame code collides with motion tables')
    regions = layout['regions']+[
        (VECTOR_X, bytes((-dx//4) & 255 for dx, _ in offsets)),
        (VECTOR_Y, bytes((-dy) & 255 for _, dy in offsets)),
        (VECTOR_PHASE, bytes(2*((-dx) % 4) for dx, _ in offsets)),
        (ROW_LOW, bytes((row*64) & 255 for row in range(16))),
        (ROW_HIGH, bytes((CACHE+row*64) >> 8 for row in range(16)))]
    return a.resolve(), dict(a.labels), listing, regions


def emit_tile_attributes(a, emit, load, jump, skip_empty):
    """Unchanged FPD1 path, retained byte-for-byte for baseline timings."""
    load('LD A,(tiles_left)', 0x3a, 'tiles_left', 13); emit('AND 1', [0xe6, 1], 7)
    jump('JR NZ,reuse_attr_bits', 0x20, 'reuse_attr_bits', [7, 12], True)
    load('LD HL,(attribute_masks)', 0x2a, 'attribute_masks', 16)
    emit('LD B,(HL)', [0x46], 7); emit('INC HL', [0x23], 6)
    load('LD (attribute_masks),HL', 0x22, 'attribute_masks', 16)
    jump('JR attr_ready', 0x18, 'attr_ready', 12, True)
    a.label('reuse_attr_bits'); load('LD A,(attr_bits)', 0x3a, 'attr_bits', 13); emit('LD B,A', [0x47], 4)
    a.label('attr_ready')
    if skip_empty:
        emit('LD A,B', [0x78], 4); emit('AND F0h', [0xe6, 0xf0], 7)
        jump('JP Z,empty_attr_nibble', 0xca, 'empty_attr_nibble', 10)
    load('LD DE,(attr_target)', (0xed, 0x5b), 'attr_target', 20)
    for field in range(4):
        emit('SLA B', [0xcb, 0x20], 8); jump('JP NC,keep_attribute', 0xd2, f'keep_at_{field}', 10)
        emit('LD A,(DE)', [0x1a], 7); emit('LD C,A', [0x4f], 4); emit('EXX', [0xd9], 4)
        jump('CALL attribute', 0xcd, 'attribute', 17); emit('EXX', [0xd9], 4)
        emit('XOR C', [0xa9], 4); emit('LD (DE),A', [0x12], 7)
        a.label(f'keep_at_{field}')
        if field in (0, 2):
            emit('INC E', [0x1c], 4)
        elif field == 1:
            emit('LD A,E', [0x7b], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD E,A', [0x5f], 4)
    emit('LD A,B', [0x78], 4); load('LD (attr_bits),A', 0x32, 'attr_bits', 13); emit('RET', [0xc9], 10)
    if skip_empty:
        a.label('empty_attr_nibble')
        emit('LD A,B', [0x78], 4)
        for _ in range(4):
            emit('ADD A,A', [0x87], 4)
        load('LD (attr_bits),A', 0x32, 'attr_bits', 13); emit('RET', [0xc9], 10)
