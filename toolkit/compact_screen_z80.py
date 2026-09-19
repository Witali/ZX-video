"""Expand the existing compact frame to a Spectrum back screen on Z80.

Entry A=40h/C0h selects bank 5/7 screen; saved_page contains the current
7FFD value with bank 6 selected and paging unlocked. The routine temporarily
maps bank 7, preserves the display bit, then restores saved_page. It never
flips the visible screen. Source is the causal decoder's frame at 6400h.
Rows outside the configured range must already be zero in both screens.
All 768 attributes are copied. No metadata, disk, IRQ or ULA cost is hidden
in the deterministic CPU count. Production integration is still separate.
"""
from build_zxv_trd import MiniAssembler, spectrum_bitmap_offset
from build_long_video_trd import build_player_dither_tables

CODE, FRAME, TABLE, ROWS = 0x9000, 0x6400, 0x9e00, 0xbc00


def expected_tstates(first=0, rows=96, *, paired=True, unrolled_attrs=True):
    if not 0 <= first < 96 or not 1 <= rows <= 96-first:
        raise ValueError('invalid row range')
    # Raster includes table loads, source-page carry, loop and 32 expansions.
    carries = (first+rows)//8-first//8
    pixels = 32*rows*(51 if paired else 59)
    # Constant and per-row overhead are sums of the listing below.
    attrs = 48*(16*16+4+10)+7 if unrolled_attrs else 21*768-5
    return 106 + rows*129 + carries*4 + pixels + 51 + attrs + 45


def build(*, first=0, rows=96, paired=True, unrolled_attrs=True):
    expected_tstates(first, rows, paired=paired, unrolled_attrs=unrolled_attrs)
    a, listing = MiniAssembler(CODE), []

    def emit(name, data, ticks, stage):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage=stage))
        a.emit(*data)

    def ref(name, opcode, label, ticks, stage):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage=stage))
        a.abs16(opcode, label)

    a.label('draw')
    ref('LD (screen_base),A', 0x32, 'screen_base', 13, 'control')
    ref('LD A,(saved_page)', 0x3a, 'saved_page', 13, 'paging')
    emit('OR 1', [0xf6, 1], 7, 'paging')
    emit('LD BC,7FFD', [0x01, 0xfd, 0x7f], 10, 'paging')
    emit('OUT (C),A', [0xed, 0x79], 12, 'paging')
    emit('LD HL,compact_first_row', [0x21, (FRAME+32*first) & 255, (FRAME+32*first) >> 8], 10, 'control')
    emit('LD IX,row_addresses', [0xdd, 0x21, ROWS & 255, ROWS >> 8], 14, 'control')
    emit('LD B,dither_top_page', [0x06, TABLE >> 8], 7, 'control')
    emit('LD A,row_count', [0x3e, rows], 7, 'control')
    ref('LD (rows_left),A', 0x32, 'rows_left', 13, 'control')
    a.label('row')
    emit('LD E,(IX+0)', [0xdd, 0x5e, 0], 19, 'row_address')
    emit('LD D,(IX+1)', [0xdd, 0x56, 1], 19, 'row_address')
    emit('INC IX', [0xdd, 0x23], 10, 'row_address')
    emit('INC IX', [0xdd, 0x23], 10, 'row_address')
    ref('LD A,(screen_base)', 0x3a, 'screen_base', 13, 'row_address')
    emit('OR D', [0xb2], 4, 'row_address')
    emit('LD D,A', [0x57], 4, 'row_address')
    for column in range(32):
        emit('LD C,(HL)', [0x4e], 7, 'bitmap')
        emit('LD A,(BC)', [0x0a], 7, 'bitmap')
        emit('LD (DE),A', [0x12], 7, 'bitmap')
        reverse = paired and column % 2
        emit('DEC B' if reverse else 'INC B', [0x05 if reverse else 0x04], 4, 'bitmap')
        emit('DEC D' if reverse else 'INC D', [0x15 if reverse else 0x14], 4, 'bitmap')
        emit('LD A,(BC)', [0x0a], 7, 'bitmap')
        emit('LD (DE),A', [0x12], 7, 'bitmap')
        if not paired:
            emit('DEC B', [0x05], 4, 'bitmap')
            emit('DEC D', [0x15], 4, 'bitmap')
        emit('INC E', [0x1c], 4, 'bitmap')
        # Last INC L supplies Z for the page carry, without touching D/B.
        emit('INC L', [0x2c], 4, 'bitmap')
    ref('JP NZ,source_page_ready', 0xc2, 'source_page_ready', 10, 'control')
    emit('INC H', [0x24], 4, 'control')
    a.label('source_page_ready')
    ref('LD A,(rows_left)', 0x3a, 'rows_left', 13, 'control')
    emit('DEC A', [0x3d], 4, 'control')
    ref('LD (rows_left),A', 0x32, 'rows_left', 13, 'control')
    ref('JP NZ,row', 0xc2, 'row', 10, 'control')
    emit('LD HL,compact_attributes', [0x21, 0, 0x70], 10, 'attributes')
    ref('LD A,(screen_base)', 0x3a, 'screen_base', 13, 'attributes')
    emit('OR 18h', [0xf6, 0x18], 7, 'attributes')
    emit('LD D,A', [0x57], 4, 'attributes')
    emit('LD E,0', [0x1e, 0], 7, 'attributes')
    emit('LD BC,768', [0x01, 0, 3], 10, 'attributes')
    if unrolled_attrs:
        emit('LD A,48', [0x3e, 48], 7, 'attributes')
        a.label('attribute_chunk')
        for _ in range(16):
            emit('LDI', [0xed, 0xa0], 16, 'attributes')
        emit('DEC A', [0x3d], 4, 'attributes')
        ref('JP NZ,attribute_chunk', 0xc2, 'attribute_chunk', 10, 'attributes')
    else:
        emit('LDIR', [0xed, 0xb0], [16, 21], 'attributes')
    ref('LD A,(saved_page)', 0x3a, 'saved_page', 13, 'paging')
    emit('LD BC,7FFD', [0x01, 0xfd, 0x7f], 10, 'paging')
    emit('OUT (C),A', [0xed, 0x79], 12, 'paging')
    emit('RET', [0xc9], 10, 'control')
    a.label('state')
    for label in ('screen_base', 'saved_page', 'rows_left'):
        a.label(label); a.emit(0)
    a.label('end')
    if a.pc > 0x9400:
        raise ValueError('renderer overlaps AY fixture')
    addresses = b''.join(spectrum_bitmap_offset(0, y*2).to_bytes(2, 'little')
                         for y in range(first, first+rows))
    top, bottom = build_player_dither_tables()
    return a.resolve(), a.labels, listing, [(TABLE, top+bottom), (ROWS, addresses)]
