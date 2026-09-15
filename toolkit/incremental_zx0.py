"""Suspend ZX0 at a requested output boundary, preserving its private stack.

The compressed stream and the 8 KiB history buffer are unchanged. Only LDIR
sites in the turbo decoder call a bounded copier. HL' belongs to the IM2 clock.
"""
import zx0_codec

STACK_TOP = 0x7DF0
STACK_BOTTOM = 0x7D80


def emit_wait(a, *, lookahead=False, output_base=0x8000, direct_input=False):
    a.label('prepare_packet' if lookahead else 'wait_packet')
    a.abs16(0x2A,'block_frame_pointer')
    a.abs16((0xED,0x5B),'block_end');a.emit(0xB7,0xED,0x52)
    a.abs16(0xC2,'slice_frame_header')
    if lookahead:
        a.abs16(0x3A,'ahead_input_ready');a.emit(0xB7)
        a.abs16(0xC2,'slice_validate_length')
        if direct_input:a.abs16(0xCD,'direct_release')
        a.abs16(0xCD,'ahead_require_input')
    a.abs16(0xCD,'load_block_header')
    if lookahead:a.label('slice_validate_length')
    a.abs16(0x2A,'block_length');a.emit(0x11);a.word(8193)
    a.emit(0xB7,0xED,0x52);a.abs16(0xD2,'fatal')
    a.abs16(0x2A,'block_length');a.emit(0x7C,0xB7)
    a.rel8(0x20,'slice_length_valid')
    a.emit(0x7D,0xFE,12);a.abs16(0xDA,'fatal')
    a.label('slice_length_valid')
    if lookahead:
        a.abs16(0x3A,'ahead_input_ready');a.emit(0xB7)
        a.rel8(0x28,'slice_copy_input')
        a.emit(0xAF);a.abs16(0x32,'ahead_input_ready')
        a.abs16(0xC3,'slice_block_loaded')
        a.label('slice_copy_input')
    a.abs16(0xCD,'load_block_body')
    if lookahead:a.label('slice_block_loaded')
    a.abs16(0x2A,'block_length');a.emit(0x11);a.word(output_base)
    a.emit(0x19);a.abs16(0x22,'block_end')
    a.emit(0x21);a.word(output_base);a.abs16(0x22,'block_frame_pointer')
    a.abs16(0x22,'slice_output');a.emit(0x23,0x23);a.abs16(0x22,'slice_target')
    a.abs16(0xCD,'slice_begin')

    a.label('slice_frame_header')
    a.abs16(0x2A,'block_frame_pointer');a.emit(0x23,0x23)
    a.abs16(0x22,'slice_target');a.abs16(0xCD,'slice_until')
    a.abs16(0x2A,'block_frame_pointer');a.emit(0x5E,0x23,0x56,0x23,0x19)
    a.abs16(0x22,'slice_target')
    a.abs16((0xED,0x5B),'block_end');a.emit(0xB7,0xED,0x52)
    a.rel8(0x28,'slice_frame_valid');a.abs16(0xD2,'fatal')
    a.label('slice_frame_valid');a.abs16(0xC3,'ahead_decode' if lookahead else 'slice_until')


def emit_decoder(a, *, output_base=0x8000, stack_top=STACK_TOP, direct_input=False, wrapped_input=False):
    a.label('slice_until')
    a.abs16(0xCD,'slice_sync_target')
    a.abs16(0x2A,'slice_output');a.abs16((0xED,0x5B),'slice_target')
    a.emit(0xB7,0xED,0x52,0xD0)  # RET NC: enough output already exists.
    a.label('slice_resume')
    if direct_input:a.abs16(0xCD,'direct_page')
    a.abs16((0xED,0x73),'slice_caller_sp')
    a.abs16((0xED,0x7B),'slice_decoder_sp')
    a.emit(0xE1,0xD1,0xC1,0xF1,0xC9)

    a.label('slice_begin')
    if direct_input:a.abs16(0xCD,'direct_page')
    a.abs16(0xCD,'slice_sync_target')
    a.abs16((0xED,0x73),'slice_caller_sp')
    a.emit(0x31);a.word(stack_top)
    a.abs16(0x21,'slice_finished');a.emit(0xE5)
    if direct_input:a.abs16(0x2A,'direct_pointer')
    else:a.emit(0x21);a.word(0xA000)
    a.emit(0x11);a.word(output_base)
    a.abs16(0x3A,'block_stored');a.emit(0xB7)
    if wrapped_input:
        a.rel8(0x20,'slice_stored')
        a.abs16(0x3A,'direct_cross');a.emit(0xB7);a.abs16(0xC2,'wrap_dzx0_turbo')
        a.abs16(0xC3,'dzx0_turbo')
        a.label('slice_stored')
    else:a.abs16(0xCA,'dzx0_turbo')
    a.abs16((0xED,0x4B),'block_length');a.abs16(0xCD,'wrapped_literal' if wrapped_input else 'slice_copy')
    a.emit(0xC9)

    a.label('slice_finished')
    a.abs16(0x2A,'block_end');a.emit(0xB7,0xED,0x52)
    a.abs16(0xC2,'fatal')
    a.abs16((0xED,0x53),'slice_output')
    a.abs16((0xED,0x7B),'slice_caller_sp')
    if direct_input:a.abs16(0xC3,'page_bank7')
    else:a.emit(0xC9)

    a.label('slice_yield')
    a.abs16((0xED,0x53),'slice_output')
    a.emit(0xF5,0xC5,0xD5,0xE5)
    a.abs16((0xED,0x73),'slice_decoder_sp')
    a.abs16((0xED,0x7B),'slice_caller_sp')
    if direct_input:a.abs16(0xC3,'page_bank7')
    else:a.emit(0xC9)

    a.label('slice_copy')
    # The usual run fits entirely. Compare DE+BC with patched target bytes,
    # preserving the ZX0 bit accumulator in AF' without borrowing HL.
    a.emit(0x08,0x7B,0x81,0x7A,0x88)
    a.label('slice_compare_high');a.emit(0xFE,0)
    a.rel8(0x38,'slice_copy_fast');a.rel8(0x20,'slice_copy_slow')
    a.emit(0x7B,0x81)
    a.label('slice_compare_low');a.emit(0xFE,0)
    a.rel8(0x38,'slice_copy_fast');a.rel8(0x28,'slice_copy_fast')
    a.label('slice_copy_slow');a.emit(0x08)
    a.emit(0xF5,0xE5,0xC5)
    a.abs16(0x2A,'slice_target');a.emit(0xB7,0xED,0x52)
    a.rel8(0x28,'slice_no_space')
    a.emit(0xD5,0x50,0x59,0xB7,0xED,0x52,0xD1)
    a.rel8(0x30,'slice_copy_full')
    # HL = available - run length. Split the run at the frame boundary.
    a.emit(0x09,0x44,0x4D,0xE1,0xB7,0xED,0x42,0xE3,0xED,0xB0,0xC1,0xF1)
    a.rel8(0x18,'slice_pause')
    a.label('slice_no_space');a.emit(0xC1,0xE1,0xF1)
    a.label('slice_pause');a.abs16(0xCD,'slice_yield');a.abs16(0xC3,'slice_copy')
    a.label('slice_copy_full');a.emit(0xC1,0xE1,0xED,0xB0,0xF1,0xC9)
    a.label('slice_copy_fast');a.emit(0x08,0xED,0xB0,0xC9)
    a.label('slice_sync_target')
    a.abs16(0x2A,'slice_target');a.emit(0x7C);a.abs16(0x32,'slice_high_operand')
    a.emit(0x7D);a.abs16(0x32,'slice_low_operand');a.emit(0xC9)
    a.labels['slice_high_operand']=a.labels['slice_compare_high']+1
    a.labels['slice_low_operand']=a.labels['slice_compare_low']+1
    zx0_codec.emit_decoder(a,'turbo',copy_hook='slice_copy')
    if wrapped_input:
        zx0_codec.emit_decoder(a,'turbo',copy_hook='slice_copy',literal_hook='wrapped_literal',
                              source_wrap='direct_wrap',label_prefix='wrap_')


def emit_variables(a):
    for name in ('slice_output','slice_target','slice_caller_sp','slice_decoder_sp'):
        a.label(name);a.word(0)
