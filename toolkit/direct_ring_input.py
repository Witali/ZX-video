"""Borrow contiguous compressed input without releasing its ring sectors."""


def emit_load(a):
    # Header validation already proved the entire input is in the ring.
    # A block ending exactly at 10000h fits; any other carry crosses a bank.
    a.abs16(0x3A,'ring_read_high');a.emit(0x67)
    a.abs16(0x3A,'ring_read_low');a.emit(0x6F)
    a.abs16(0x22,'direct_pointer');a.abs16((0xED,0x5B),'frame_length')
    a.emit(0x19);a.rel8(0x30,'direct_fits');a.emit(0x7C,0xB5)
    a.rel8(0x20,'direct_copy_fallback')
    a.label('direct_fits')
    a.abs16(0x2A,'frame_length');a.abs16(0x22,'direct_length')
    a.abs16(0x3A,'ring_read_region');a.abs16(0x32,'direct_region');a.emit(0xC9)
    a.label('direct_copy_fallback')
    a.emit(0x21);a.word(0xA000);a.abs16(0x22,'direct_pointer')
    a.emit(0xAF);a.abs16(0x32,'direct_region')
    # Fall through to the existing sector-by-sector copy.


def emit_helpers(a):
    a.label('direct_release')
    # Only called after the old block is completely decoded, before checking
    # availability of a new header. A preselected next block must stay held.
    a.abs16(0x3A,'direct_region');a.emit(0xB7,0xC8)
    a.emit(0xAF);a.abs16(0x32,'direct_region')
    a.abs16(0x2A,'direct_pointer');a.abs16((0xED,0x5B),'direct_length');a.emit(0x19)
    a.emit(0x7D);a.abs16(0x32,'ring_read_low')
    a.abs16(0x3A,'ring_read_high');a.emit(0x47,0x7C,0x90,0x47,0xC8)
    a.label('direct_release_sector')
    a.emit(0xC5);a.abs16(0xCD,'consume_sector');a.emit(0xC1)
    a.rel8(0x10,'direct_release_sector');a.emit(0xC9)

    a.label('direct_page')
    a.abs16(0x3A,'direct_region');a.emit(0xB7,0xC8)
    a.abs16(0xC3,'page_queue_region')


def emit_variables(a):
    a.label('direct_region');a.emit(0)
    a.label('direct_pointer');a.word(0xA000)
    a.label('direct_length');a.word(0)
