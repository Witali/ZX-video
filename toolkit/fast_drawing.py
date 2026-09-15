"""Register-based implementations of unchanged v6 bitmap commands.

Zilog UM0080 T-states, command entry through JP command_loop, no dispatch:
mask: 2067+64*N -> 1287+68*N (delta -780+4*N);
points: 260+265*N -> 220+189*N (delta -40-76*N).
Memory contention, IRQs, ROM and disk latency are measured separately in Fuse.
"""


def row_address(a):
    a.abs16(0x3A,'row_index')
    a.emit(0x6F,0x26,0,0x29)
    a.abs16(0x11,'row_addresses')
    a.emit(0x19,0x4E,0x23,0x46)
    a.abs16(0x3A,'update_base'); a.emit(0x80,0x47,0x3C,0x57,0x59)


def emit_mask(a):
    a.label('command_row')
    a.emit(0xDD,0x7E,0,0xDD,0x23); a.abs16(0x32,'row_index')
    for name in ('mask0','mask1','mask2','mask3'):
        a.emit(0xDD,0x7E,0,0xDD,0x23); a.abs16(0x32,name)
    row_address(a)
    a.abs16(0x21,'dither_top')
    for group in range(4):
        a.abs16(0x3A,f'mask{group}')
        for bit in range(8):
            skip=f'unchanged_{group}_{bit}'
            a.emit(0x87); a.rel8(0x30,skip)
            # AF' holds the shifted mask while A reads the dither lookup table.
            a.emit(0x08,0xDD,0x6E,0,0xDD,0x23,0x7E,0x02,0x24,0x7E,0x12,0x25,0x08)
            a.label(skip);a.emit(0x03,0x13)
    a.abs16(0xC3,'command_loop')


def emit_points(a):
    a.label('command_points')
    a.emit(0xDD,0x7E,0,0xDD,0x23);a.abs16(0x32,'row_index')
    a.emit(0xDD,0x7E,0,0xDD,0x23);a.abs16(0x32,'point_count')
    row_address(a)
    a.label('point_loop')
    a.abs16(0x3A,'point_count');a.emit(0xB7);a.abs16(0xCA,'command_loop')
    a.emit(0xDD,0x6E,0,0xDD,0x23)
    # Rows are 32-byte aligned; retain the row base and replace only column bits.
    a.emit(0x79,0xE6,0xE0,0xB5,0x4F,0x5F)
    a.emit(0xDD,0x6E,0,0xDD,0x23,0x26,0)
    table_high_pos=len(a.code)-1
    a.emit(0x7E,0x02,0x24,0x7E,0x12)
    a.abs16(0x3A,'point_count');a.emit(0x3D);a.abs16(0x32,'point_count')
    a.rel8(0x18,'point_loop')
    return table_high_pos
