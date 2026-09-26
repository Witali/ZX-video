"""Prototype local ZX0 that suspends before entering an unloaded input page.

The byte stream and output history are unchanged. Input stays contiguous in
C000..DFFF: there is no 256-byte staging copy. The caller supplies whole pages
and updates input_high/all_loaded only while the decoder is suspended.

This standalone layout at 7800 is a test allocation, NOT an integrated player
allocation. Disk producer/queue ownership and physical delivery are not modeled.
"""
from build_zxv_trd import MiniAssembler
import incremental_zx0

CODE, INPUT, OUTPUT = 0x7800, 0xc000, 0xe000
STACK_BOTTOM, STACK_TOP = 0x7b70, 0x7be0


def build():
    a=MiniAssembler(CODE)
    incremental_zx0.emit_decoder(a, output_base=OUTPUT, input_base=INPUT,
        stack_top=STACK_TOP, wrap_output=True, token_boundaries=True,
        inline_matches=True, input_pointer_label='input_pointer',
        source_page_wrap='input_next_page', literal_hook='input_literal')
    # Redirect the private stack's EOF return through an explicit completion
    # flag. Output==block_end alone is insufficient after an input suspension:
    # the EOF bits can still be in the next page.
    a.labels['core_finished']=a.labels.pop('slice_finished')
    a.label('slice_finished')
    a.emit(0x3e,1);a.abs16(0x32,'finished');a.abs16(0xc3,'core_finished')
    a.label('begin')
    a.emit(0xaf);a.abs16(0x32,'input_needed');a.abs16(0x32,'finished')
    a.abs16(0xc3,'slice_begin')
    a.label('resume')
    a.abs16(0x3a,'input_needed');a.emit(0xb7);a.abs16(0xca,'slice_until')
    # Resume input suspension even if its last output met the requested
    # target (including wrapped 8192), so pending EOF cannot be skipped.
    a.emit(0xaf);a.abs16(0x32,'input_needed')
    a.abs16(0xcd,'slice_sync_target');a.abs16(0xc3,'slice_resume')

    a.label('input_next_page')
    # Upstream INC HL became INC L / CALL Z, preserving the ZX0 carry.
    a.emit(0xf5,0x24,0xf1)
    a.label('input_check')
    a.emit(0xf5)
    a.abs16(0x3a,'all_loaded');a.emit(0xb7);a.rel8(0x20,'input_ready')
    a.abs16(0x3a,'input_high');a.emit(0xbc);a.rel8(0x20,'input_ready')
    a.emit(0x3e,1);a.abs16(0x32,'input_needed');a.emit(0xf1)
    a.abs16(0xcd,'slice_yield');a.abs16(0xc3,'input_check')
    a.label('input_ready');a.emit(0xf1,0xc9)

    a.label('input_literal')
    # A literal shorter than the rest of its current page needs no split.
    # AF' temporarily holds the live bit accumulator; BC/DE/HL stay intact.
    a.emit(0x08,0x7d,0x81,0x78,0xce,0,0xb7)
    a.rel8(0x28,'literal_fast');a.emit(0x08)
    # Tail = BC-(256-L). The fast comparison already proved BC>=256-L.
    a.emit(0xf5,0x7d,0x81,0x4f,0x78,0xce,0,0x3d,0x47)
    a.abs16((0xed,0x43),'literal_tail')
    a.emit(0x01);a.word(256)
    a.emit(0x7d,0xb7);a.rel8(0x28,'literal_prefix')
    a.emit(0x06,0,0xed,0x44,0x4f)
    a.label('literal_prefix');a.emit(0xf1)
    a.abs16(0xcd,'slice_copy')
    # LDIR already advanced H. Do not increment it a second time.
    a.abs16(0xcd,'input_check')
    a.abs16((0xed,0x4b),'literal_tail')
    a.emit(0xf5,0x78,0xb1);a.rel8(0x28,'literal_done')
    a.emit(0xf1);a.abs16(0xc3,'input_literal')
    a.label('literal_done');a.emit(0xf1,0xc9)
    a.label('literal_fast');a.emit(0x08);a.abs16(0xc3,'slice_copy')

    a.label('fatal');a.emit(0x76)
    a.label('state');incremental_zx0.emit_variables(a)
    for name in ('block_length','block_end','input_pointer','literal_tail'):
        a.label(name);a.word(0)
    for name in ('block_stored','input_high','all_loaded','input_needed','finished'):
        a.label(name);a.emit(0)
    a.label('end')
    if a.pc>STACK_BOTTOM:raise ValueError('prototype overlaps private stack')
    return a.resolve(),dict(a.labels)
