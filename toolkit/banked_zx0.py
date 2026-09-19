"""Bounded ZX0 from a 64 KiB bank ring through a fixed 256-byte input window.

Ring banks 0/1/3/4 map at C000; output E000..FFFF resides in bank 7.
Code 7C00, private stack below 7BE0, fixed input BC00..BCFF. The ring is
assumed to contain the complete compressed block; disk supply is external.
Targets are monotonically increasing output byte counts, with address 0000
representing the end of an 8192-byte block. No screen/table RAM is borrowed.
"""
import incremental_zx0
from build_zxv_trd import MiniAssembler

CODE, INPUT, OUTPUT = 0x7c00, 0xbc00, 0xe000
STACK_TOP, STACK_BOTTOM = 0x7be0, 0x7b70
BANKS = (0, 1, 3, 4)


def build(*, fast_literal=False, fast_refill=False):
    a = MiniAssembler(CODE)
    a.label('begin')
    a.abs16(0xcd, 'refill')
    a.abs16(0xc3, 'slice_begin')
    incremental_zx0.emit_decoder(a, output_base=OUTPUT, input_base=INPUT, stack_top=STACK_TOP,
        wrap_output=True, source_page_wrap='refill', literal_hook='literal')

    a.label('literal')
    # Split a literal run at BD00 before LDIR can leave the input page.
    if fast_literal:
        # Check HL+BC using A/AF' before paying for any pushes. Carry out
        # of the low-byte sum is included in H+B; live BC/DE/HL stay intact.
        a.emit(0x08, 0x7d, 0x81, 0x7c, 0x88, 0xfe, (INPUT >> 8)+1)
        a.abs16(0xda, 'literal_fast')
        a.emit(0x08)
    a.emit(0xf5, 0xd5, 0xe5, 0x09)
    if not fast_literal:
        a.emit(0x7c, 0xfe, (INPUT >> 8)+1)
        a.rel8(0x38, 'literal_fits')
    a.emit(0x11); a.word(INPUT+256)
    a.emit(0xb7, 0xed, 0x52)
    a.abs16(0x22, 'literal_tail')
    a.emit(0xe1, 0xd1, 0xf1)
    # Prefix = 256 - L, including the full 256 bytes when L is zero.
    a.emit(0xf5, 0x01); a.word(256)
    a.emit(0x7d, 0xb7)
    a.rel8(0x28, 'literal_prefix_ready')
    a.emit(0x06, 0, 0xed, 0x44, 0x4f)  # B=0, NEG, C=A.
    a.label('literal_prefix_ready')
    a.emit(0xf1)
    a.abs16(0xcd, 'slice_copy')
    a.abs16(0xcd, 'refill')
    a.emit(0xf5)
    a.abs16((0xed, 0x4b), 'literal_tail')
    a.emit(0x78, 0xb1)
    a.rel8(0x28, 'literal_done')
    a.emit(0xf1)
    a.abs16(0xc3, 'literal')
    a.label('literal_done'); a.emit(0xf1, 0xc9)
    if fast_literal:
        a.label('literal_fast'); a.emit(0x08)
    else:
        a.label('literal_fits'); a.emit(0xe1, 0xd1, 0xf1)
    a.abs16(0xc3, 'slice_copy')

    a.label('refill')
    # Preserve all live ZX0 inputs, including carry. HL returns to BC00.
    a.emit(0xf5, 0xc5, 0xd5)
    a.abs16(0x2a, 'remaining')
    a.emit(0x7c, 0xb5)
    a.abs16(0xca, 'refill_empty')
    a.emit(0x7c, 0xb7)
    a.rel8(0x28, 'refill_short')
    a.emit(0x01); a.word(256)
    a.rel8(0x18, 'refill_count')
    a.label('refill_short'); a.emit(0x44, 0x4d)  # BC=HL, H=0.
    a.label('refill_count')
    a.abs16((0xed, 0x43), 'valid')
    a.emit(0xb7, 0xed, 0x42)
    a.abs16(0x22, 'remaining')
    a.emit(0xc5)
    a.abs16(0xcd, 'ring_page')
    a.emit(0xc1)
    a.abs16(0x2a, 'ring_pointer')
    a.emit(0x11); a.word(INPUT)
    a.abs16(0xcd, 'ring_copy')
    a.abs16(0x22, 'ring_pointer')
    a.abs16(0x3a, 'history_page')
    a.emit(0x01); a.word(0x7ffd)
    a.emit(0xed, 0x79)
    a.label('refill_empty')
    a.emit(0x21); a.word(INPUT)
    a.emit(0xd1, 0xc1, 0xf1, 0xc9)

    a.label('ring_copy')
    # One refill (<=256 bytes) crosses at most one 16 KiB bank boundary.
    a.emit(0xd5, 0xe5, 0x09)
    a.rel8(0x30, 'ring_copy_fits')
    a.abs16(0x22, 'ring_tail')
    a.emit(0xeb, 0x60, 0x69, 0xb7, 0xed, 0x52, 0x44, 0x4d, 0xe1, 0xd1)
    if fast_refill: a.abs16(0xcd, 'ring_copy_bytes')
    else: a.emit(0xed, 0xb0)
    a.emit(0xd5)
    a.abs16(0x3a, 'ring_region')
    a.emit(0x3c, 0xe6, 3)
    a.abs16(0x32, 'ring_region')
    a.abs16(0xcd, 'ring_page')
    a.emit(0xd1, 0x21); a.word(0xc000)
    a.abs16((0xed, 0x4b), 'ring_tail')
    a.emit(0x78, 0xb1, 0xc8)
    if fast_refill: a.abs16(0xc3, 'ring_copy_bytes')
    else: a.emit(0xed, 0xb0, 0xc9)
    a.label('ring_copy_fits'); a.emit(0xe1, 0xd1)
    if fast_refill:
        a.abs16(0xc3, 'ring_copy_bytes')
        a.label('ring_copy_bytes')
        # All requests are 1..256 bytes; B!=0 therefore means exactly 256.
        a.emit(0x78, 0xb7); a.rel8(0x28, 'ring_copy_small')
        a.emit(0x3e, 8)
        a.label('ring_copy_32')
        for _ in range(32): a.emit(0xed, 0xa0)
        a.emit(0x3d); a.rel8(0x20, 'ring_copy_32'); a.emit(0xc9)
        a.label('ring_copy_small'); a.emit(0xed, 0xb0, 0xc9)
    else:
        a.emit(0xed, 0xb0, 0xc9)

    a.label('ring_page')
    a.abs16(0x3a, 'ring_region')
    a.emit(0x5f, 0x16, 0)
    a.abs16(0x21, 'ring_banks')
    a.emit(0x19, 0x5e)
    a.abs16(0x3a, 'history_page')
    a.emit(0xe6, 0xf8, 0xb3, 0x01); a.word(0x7ffd)
    a.emit(0xed, 0x79, 0xc9)

    a.label('fatal'); a.emit(0x76)
    a.label('state')
    incremental_zx0.emit_variables(a)
    for name in ('block_length', 'block_end', 'remaining', 'valid', 'ring_pointer', 'literal_tail', 'ring_tail'):
        a.label(name); a.word(0)
    for name in ('block_stored', 'ring_region', 'history_page'):
        a.label(name); a.emit(0)
    a.label('ring_banks'); a.emit(*BANKS)
    a.label('end')
    if a.pc > 0x8000:
        raise ValueError(f'banked ZX0 code overlaps reconstruction: {a.pc:04x}')
    return a.resolve(), a.labels
