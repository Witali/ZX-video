"""Stream-pointer implementations of unchanged bitmap commands.

HL reads the stream, BC addresses dither tables, DE addresses the top row.
AF prime holds a mask or counter. HL prime remains reserved for the IRQ clock.
UM0080 T-states, entry through JP command_loop, dispatch excluded:
mask: 1287+68*N -> 984+60*N; points: 220+189*N -> 207+114*N (N>0),
empty points: 220 -> 217; spans: 220+178*R+126*N -> 243+122*R+90*N.
RLE: 208+95*L+152*R+183*NL+167*NR -> 189+50*L+147*R+90*NL+47*NR;
L/R are literal/repeat token counts, NL/NR their output lengths (sum 32).
ROM, contention and IRQ execution are measured separately in Fuse.
"""


def row_address(a):
    # Transfer the packet pointer once per command, then preserve it while
    # looking up the native row address. Native row pairs differ by 0100h.
    a.emit(0xDD,0xE5,0xE1,0x7E,0x23,0xE5,0x6F,0x26,0,0x29)
    a.abs16(0x01,'row_addresses');a.emit(0x09,0x5E,0x23,0x56)
    a.abs16(0x3A,'update_base');a.emit(0x82,0x57,0xE1)
    a.abs16(0x01,'dither_top')


def value(a):
    a.emit(0x4E,0x23,0x0A,0x12,0x04,0x14,0x0A,0x12,0x05,0x15)


def finish(a):
    a.emit(0xE5,0xDD,0xE1);a.abs16(0xC3,'command_loop')


def emit_mask(a):
    a.label('command_row');row_address(a)
    for name in ('mask0','mask1','mask2','mask3'):
        a.emit(0x7E,0x23);a.abs16(0x32,name)
    for group in range(4):
        a.abs16(0x3A,f'mask{group}')
        for bit in range(8):
            skip=f'unchanged_{group}_{bit}'
            a.emit(0x87);a.rel8(0x30,skip)
            a.emit(0x08);value(a);a.emit(0x08)
            a.label(skip);a.emit(0x1C)
    finish(a)


def emit_points(a):
    a.label('command_points');row_address(a)
    a.emit(0x7E,0x23,0xB7);a.rel8(0x28,'points_finished');a.emit(0x08)
    a.label('point_loop')
    # Replace the five column bits; logical rows are 32-byte aligned.
    a.emit(0x7B,0xE6,0xE0,0xB6,0x5F,0x23)
    value(a)
    a.emit(0x08,0x3D);a.rel8(0x28,'points_finished');a.emit(0x08)
    a.abs16(0xC3,'point_loop')
    a.label('points_finished');finish(a)


def emit_spans(a):
    a.label('command_spans');row_address(a)
    a.emit(0x7E,0x23);a.abs16(0x32,'span_count')
    a.label('span_token_loop')
    a.abs16(0x3A,'span_count');a.emit(0xB7);a.rel8(0x28,'spans_finished')
    a.emit(0x7E,0x23,0x4F,0xE6,0x0F,0x3C,0x08)
    a.emit(0x79,0x0F,0x0F,0x0F,0x0F,0xE6,0x0F,0x83,0x5F)
    a.label('span_value_loop');value(a);a.emit(0x1C,0x08,0x3D)
    a.rel8(0x28,'span_finished');a.emit(0x08);a.abs16(0xC3,'span_value_loop')
    a.label('span_finished')
    a.abs16(0x3A,'span_count');a.emit(0x3D);a.abs16(0x32,'span_count')
    a.abs16(0xC3,'span_token_loop')
    a.label('spans_finished');finish(a)


def emit_rle(a):
    a.label('command_row_rle');row_address(a)
    a.emit(0x23)  # Encoded byte length; the output boundary is 32 columns.
    a.label('rle_token_loop')
    a.emit(0x7E,0x23,0xCB,0x7F);a.rel8(0x20,'rle_run')
    a.emit(0x3C,0x08)
    a.label('rle_literal_loop');value(a);a.emit(0x1C,0x08,0x3D)
    a.rel8(0x28,'rle_after_token');a.emit(0x08);a.abs16(0xC3,'rle_literal_loop')
    a.label('rle_run')
    a.emit(0xE6,0x7F,0xC6,2,0x08,0x4E,0x23,0xE5)
    # Expand one colour into H/L once. The stream pointer is on the stack;
    # B counts repeats, DE writes both native rows without a table lookup.
    a.emit(0x0A,0x67,0x04,0x0A,0x6F,0x08,0x47)
    a.label('rle_run_loop')
    a.emit(0x7C,0x12,0x14,0x7D,0x12,0x15,0x1C)
    a.rel8(0x10,'rle_run_loop')
    a.emit(0xE1);a.abs16(0x01,'dither_top')
    a.label('rle_after_token')
    a.emit(0x7B,0xE6,0x1F);a.rel8(0x20,'rle_token_loop')
    finish(a)
