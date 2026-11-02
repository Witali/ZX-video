"""Extract the 256x160 illustration from a static Spectrum SCR.

The common footer is stored separately. Each column contains 160 raster
bytes followed by 20 attributes; complete ZX0 blocks decode to this layout.
"""
def bitmap_offset(column,y):
    return ((y&0xC0)<<5)|((y&7)<<8)|((y&0x38)<<2)|column


def picture_columns(screen):
    if len(screen)!=6912 or any(a&128 for a in screen[6144:]):
        raise ValueError('Expected a static 6912-byte Spectrum screen')
    return [bytes(screen[bitmap_offset(x,y)] for y in range(160))
            +bytes(screen[6144+y*32+x] for y in range(20)) for x in range(32)]
