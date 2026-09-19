"""Render marked 8x8 native cells or dense four-row bands on Z80.

Entry A=40/C0 selects the back screen, HL points to 80 map bytes.
The map is copied to BF20..BF6F before bank 7 is paged. Compact screens
remain at 6400; rows outside 8..87 must be zero. Map bits refer to n-2.
All attributes are copied by default. constant_attribute_borders copies only
rows 3..20; the caller must first initialize all attributes in both screens
to 1 and prove that omitted rows stay 1. No screen flip, disk, IRQ or ULA
cost is hidden.
"""
from build_zxv_trd import MiniAssembler
from build_long_video_trd import build_player_dither_tables

CODE, FRAME, TABLE, MASK = 0x9000, 0x6400, 0x9e00, 0xbf20


def expected_tstates(mask, *, fast_mask_dispatch=False, constant_attribute_borders=False, skip_black_borders=False):
    if len(mask) != 80:
        raise ValueError('expected 80 cell-mask bytes')
    if skip_black_borders and not fast_mask_dispatch:
        raise ValueError('black-border omission requires fast mask dispatch')
    first, bands = (1,18) if skip_black_borders else (0,20)
    dense = odd_dense = partial_cells = zero_masks = 0
    for band in range(first,first+bands):
        flags = mask[band*4:band*4+4]
        if flags == b'\xff'*4:
            dense += 1
            odd_dense += band & 1
        else:
            partial_cells += sum(v.bit_count() for v in flags)
            zero_masks += flags.count(0)
    # 80 LDI map transfers and 768 attrs (576 with constant borders); external CALL,
    # IRQ/ULA, mask ZX0 and disk delivery excluded. See instruction listing.
    if fast_mask_dispatch:
        return 37584-2308*skip_black_borders+5853*dense+4*odd_dense+296*partial_cells-136*zero_masks-3240*constant_attribute_borders
    return 58784+4793*dense+4*odd_dense+277*partial_cells-3240*constant_attribute_borders


def build(*, fast_mask_dispatch=False, constant_attribute_borders=False, skip_black_borders=False,page_entry=None):
    if skip_black_borders and not (fast_mask_dispatch and constant_attribute_borders):
        raise ValueError('black-border omission requires fast dispatch and initialized constant attributes')
    a, listing = MiniAssembler(CODE), []

    def emit(name, data, ticks, stage):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage=stage))
        a.emit(*data)

    def ref(name, opcode, label, ticks, stage):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage=stage))
        a.abs16(opcode, label)

    def imm(name, opcode, value, ticks, stage):
        emit(name, [opcode, value & 255, value >> 8], ticks, stage)

    def adjust(reg, amount, stage):
        emit('LD A,'+reg, [{'D': 0x7a, 'E': 0x7b, 'L': 0x7d}[reg]], 4, stage)
        emit(f'ADD A,{amount}' if amount >= 0 else f'SUB {-amount}',
             [0xc6 if amount >= 0 else 0xd6, abs(amount)], 7, stage)
        emit('LD '+reg+',A', [{'D': 0x57, 'E': 0x5f, 'L': 0x6f}[reg]], 4, stage)

    def pixel(reverse=False, advance=False, stage='cell_pixels'):
        emit('LD C,(HL)', [0x4e], 7, stage)
        emit('LD A,(BC)', [0x0a], 7, stage)
        emit('LD (DE),A', [0x12], 7, stage)
        emit('DEC B' if reverse else 'INC B', [0x05 if reverse else 0x04], 4, stage)
        emit('DEC D' if reverse else 'INC D', [0x15 if reverse else 0x14], 4, stage)
        emit('LD A,(BC)', [0x0a], 7, stage)
        emit('LD (DE),A', [0x12], 7, stage)
        if advance:
            emit('INC E', [0x1c], 4, stage)
            emit('INC L', [0x2c], 4, stage)

    a.label('draw')
    ref('LD (screen_base),A', 0x32, 'screen_base', 13, 'control')
    imm('LD DE,map', 0x11, MASK, 10, 'map_copy')
    imm('LD BC,80', 0x01, 80, 10, 'map_copy')
    for _ in range(80):
        emit('LDI', [0xed, 0xa0], 16, 'map_copy')
    ref('LD A,(saved_page)', 0x3a, 'saved_page', 13, 'paging')
    emit('OR 1', [0xf6, 1], 7, 'paging')
    imm('LD BC,7FFD', 0x01, 0x7ffd, 10, 'paging')
    if page_entry is None: emit('OUT (C),A', [0xed, 0x79], 12, 'paging')
    else: imm('CALL atomic_page',0xcd,page_entry,17,'paging')
    emit('EXX', [0xd9], 4, 'control')
    imm('LD HL,map', 0x21, MASK+4*skip_black_borders, 10, 'control')
    emit('EXX', [0xd9], 4, 'control')
    imm('LD HL,compact_first_row', 0x21, FRAME+(384 if skip_black_borders else 256), 10, 'control')
    ref('LD A,(screen_base)', 0x3a, 'screen_base', 13, 'control')
    emit('LD D,A', [0x57], 4, 'control')
    emit('LD E,first screen row', [0x1e, 96 if skip_black_borders else 64], 7, 'control')
    emit('LD B,dither_top_page', [0x06, TABLE >> 8], 7, 'control')
    emit('LD A,band count', [0x3e, 18 if skip_black_borders else 20], 7, 'control')
    ref('LD (bands_left),A', 0x32, 'bands_left', 13, 'control')
    a.label('band')
    emit('EXX', [0xd9], 4, 'band_dispatch')
    for i in range(4):
        emit('LD A,(HL)' if i == 0 else 'AND (HL)', [0x7e if i == 0 else 0xa6], 7, 'band_dispatch')
        emit('INC HL', [0x23], 6, 'band_dispatch')
    emit('CP 255', [0xfe, 255], 7, 'band_dispatch')
    emit('EXX', [0xd9], 4, 'band_dispatch')
    ref('JP Z,dense', 0xca, 'dense', 10, 'band_dispatch')
    emit('EXX', [0xd9], 4, 'partial_control')
    for _ in range(4):
        emit('DEC HL', [0x2b], 6, 'partial_control')
    emit('LD C,4', [0x0e, 4], 7, 'partial_control')
    emit('EXX', [0xd9], 4, 'partial_control')
    a.label('mask_byte')
    emit('EXX', [0xd9], 4, 'partial_control')
    emit('LD A,(HL)' if fast_mask_dispatch else 'LD B,(HL)',
         [0x7e if fast_mask_dispatch else 0x46], 7, 'partial_control')
    emit('INC HL', [0x23], 6, 'partial_control')
    if not fast_mask_dispatch:
        emit('LD E,8', [0x1e, 8], 7, 'partial_control')
    emit('EXX', [0xd9], 4, 'partial_control')
    if fast_mask_dispatch:
        emit('OR A', [0xb7], 4, 'mask_dispatch')
        ref('JP Z,empty_mask', 0xca, 'empty_mask', 10, 'mask_dispatch')
        # A holds all eight flags; the cell routine preserves it through AF'.
        # No bit-loop counter or EXX is needed between columns.
        for _ in range(8):
            emit('ADD A,A', [0x87], 4, 'cell_dispatch')
            ref('CALL C,draw_cell', 0xdc, 'draw_cell', [10, 17], 'cell_dispatch')
            emit('INC L', [0x2c], 4, 'cell_address')
            emit('INC E', [0x1c], 4, 'cell_address')
    else:
        a.label('cell')
        emit('EXX', [0xd9], 4, 'cell_dispatch')
        emit('SLA B', [0xcb, 0x20], 8, 'cell_dispatch')
        emit('EXX', [0xd9], 4, 'cell_dispatch')
        ref('JP NC,skip_cell', 0xd2, 'skip_cell', 10, 'cell_dispatch')
        for row in range(4):
            pixel(reverse=bool(row & 1))
            if row != 3:
                adjust('L', 32, 'cell_address')
                emit('INC D', [0x14], 4, 'cell_address')
                emit('INC D', [0x14], 4, 'cell_address')
        adjust('L', -95, 'cell_address')
        adjust('D', -6, 'cell_address')
        emit('INC E', [0x1c], 4, 'cell_address')
        ref('JP cell_done', 0xc3, 'cell_done', 10, 'cell_address')
        a.label('skip_cell')
        emit('INC L', [0x2c], 4, 'cell_skip')
        emit('INC E', [0x1c], 4, 'cell_skip')
        a.label('cell_done')
        emit('EXX', [0xd9], 4, 'cell_control')
        emit('DEC E', [0x1d], 4, 'cell_control')
        emit('EXX', [0xd9], 4, 'cell_control')
        ref('JP NZ,cell', 0xc2, 'cell', 10, 'cell_control')
    a.label('mask_done')
    emit('EXX', [0xd9], 4, 'partial_control')
    emit('DEC C', [0x0d], 4, 'partial_control')
    emit('EXX', [0xd9], 4, 'partial_control')
    ref('JP NZ,mask_byte', 0xc2, 'mask_byte', 10, 'partial_control')
    imm('LD BC,96', 0x01, 96, 10, 'partial_control')
    emit('ADD HL,BC', [0x09], 11, 'partial_control')
    emit('LD B,dither_top_page', [0x06, TABLE >> 8], 7, 'partial_control')
    ref('JP band_done', 0xc3, 'band_done', 10, 'partial_control')
    a.label('dense')
    emit('LD A,4', [0x3e, 4], 7, 'dense_control')
    ref('LD (dense_rows_left),A', 0x32, 'dense_rows_left', 13, 'dense_control')
    a.label('dense_row')
    for column in range(32):
        pixel(reverse=bool(column & 1), advance=True, stage='dense_pixels')
    ref('JP NZ,dense_page_ready', 0xc2, 'dense_page_ready', 10, 'dense_control')
    emit('INC H', [0x24], 4, 'dense_control')
    a.label('dense_page_ready')
    ref('LD A,(dense_rows_left)', 0x3a, 'dense_rows_left', 13, 'dense_control')
    emit('DEC A', [0x3d], 4, 'dense_control')
    ref('LD (dense_rows_left),A', 0x32, 'dense_rows_left', 13, 'dense_control')
    ref('JP Z,dense_done', 0xca, 'dense_done', 10, 'dense_control')
    adjust('E', -32, 'dense_address')
    emit('INC D', [0x14], 4, 'dense_address')
    emit('INC D', [0x14], 4, 'dense_address')
    ref('JP dense_row', 0xc3, 'dense_row', 10, 'dense_control')
    a.label('dense_done')
    adjust('D', -6, 'dense_address')
    a.label('band_done')
    emit('LD A,E', [0x7b], 4, 'band_control')
    emit('OR A', [0xb7], 4, 'band_control')
    ref('JP NZ,band_page_ready', 0xc2, 'band_page_ready', 10, 'band_control')
    adjust('D', 8, 'band_control')
    a.label('band_page_ready')
    ref('LD A,(bands_left)', 0x3a, 'bands_left', 13, 'band_control')
    emit('DEC A', [0x3d], 4, 'band_control')
    ref('JP Z,attributes', 0xca, 'attributes', 10, 'band_control')
    ref('LD (bands_left),A', 0x32, 'bands_left', 13, 'band_control')
    ref('JP band', 0xc3, 'band', 10, 'band_control')
    a.label('attributes')
    first,count = (96,576) if constant_attribute_borders else (0,768)
    imm('LD HL,compact_attributes', 0x21, 0x7000+first, 10, 'attributes')
    ref('LD A,(screen_base)', 0x3a, 'screen_base', 13, 'attributes')
    emit('OR 18h', [0xf6, 0x18], 7, 'attributes')
    emit('LD D,A', [0x57], 4, 'attributes')
    emit('LD E,first attribute', [0x1e, first], 7, 'attributes')
    imm('LD BC,attribute count', 0x01, count, 10, 'attributes')
    emit('LD A,attribute chunks', [0x3e, count//16], 7, 'attributes')
    a.label('attribute_chunk')
    for _ in range(16):
        emit('LDI', [0xed, 0xa0], 16, 'attributes')
    emit('DEC A', [0x3d], 4, 'attributes')
    ref('JP NZ,attribute_chunk', 0xc2, 'attribute_chunk', 10, 'attributes')
    a.label('attribute_end')
    ref('LD A,(saved_page)', 0x3a, 'saved_page', 13, 'paging')
    imm('LD BC,7FFD', 0x01, 0x7ffd, 10, 'paging')
    if page_entry is None: emit('OUT (C),A', [0xed, 0x79], 12, 'paging')
    else: imm('CALL atomic_page',0xcd,page_entry,17,'paging')
    emit('RET', [0xc9], 10, 'control')
    if fast_mask_dispatch:
        a.label('empty_mask')
        adjust('L', 8, 'mask_skip')
        adjust('E', 8, 'mask_skip')
        ref('JP mask_done', 0xc3, 'mask_done', 10, 'mask_skip')
        a.label('draw_cell')
        emit("EX AF,AF'", [0x08], 4, 'cell_control')
        for row in range(4):
            pixel(reverse=bool(row & 1))
            if row != 3:
                adjust('L', 32, 'cell_address')
                emit('INC D', [0x14], 4, 'cell_address')
                emit('INC D', [0x14], 4, 'cell_address')
        adjust('L', -96, 'cell_address')
        adjust('D', -6, 'cell_address')
        emit("EX AF,AF'", [0x08], 4, 'cell_control')
        emit('RET', [0xc9], 10, 'cell_control')
    a.label('state')
    for name in ('screen_base', 'saved_page', 'bands_left', 'dense_rows_left'):
        a.label(name); a.emit(0)
    a.label('end')
    if a.pc > 0x9400:
        raise ValueError('renderer overlaps AY code')
    top, bottom = build_player_dither_tables()
    return a.resolve(), a.labels, listing, [(TABLE, top+bottom)]
