"""Cooperatively prepare a packet in bounded copy/decode quanta.

The outer preparation stack is separate from ZX0's suspended decoder stack.
Screen writes and AY remain in the foreground, after wait_packet consumes it.
"""
STACK_BOTTOM=0x7D00
STACK_TOP=0x7D70
DECODE_QUANTUM=128


def emit(a):
    a.label('wait_packet')
    a.abs16(0x3A,'ahead_state');a.emit(0xFE,4);a.rel8(0x38,'ahead_wait_regular')
    # During pre-copy, the complete current block is still in 8000..9FFF.
    # Its frames can be drawn without resuming or discarding the copy stack.
    a.abs16(0x2A,'block_frame_pointer');a.abs16((0xED,0x5B),'block_end')
    a.emit(0xB7,0xED,0x52,0xC0)
    a.emit(0x3E,1);a.abs16(0x32,'ahead_force')
    a.abs16(0x3A,'ahead_state');a.emit(0xFE,4)
    a.abs16(0xCC,'ahead_run')
    a.emit(0xAF);a.abs16(0x32,'ahead_state')
    a.label('ahead_wait_regular')
    # A completed next packet is usable even when later bytes of this block
    # are being decoded. Only the outer extension stack is discarded; ZX0's
    # own stack and all output/history bytes remain valid.
    a.abs16(0x3A,'ahead_state');a.emit(0xFE,2);a.rel8(0x30,'ahead_consume')
    a.emit(0x3E,1);a.abs16(0x32,'ahead_force')
    a.abs16(0xCD,'ahead_run')
    a.label('ahead_consume')
    a.emit(0xAF);a.abs16(0x32,'ahead_state');a.emit(0xC9)

    a.label('ahead_prefetch')
    # frames_remaining includes the image that is already prepared for flip.
    a.abs16(0x2A,'frames_remaining');a.emit(0x2B,0x7C,0xB5,0xC8)
    a.emit(0xAF);a.abs16(0x32,'ahead_force')
    a.abs16(0x3A,'ahead_state');a.emit(0xFE,5)
    a.rel8(0x20,'ahead_prefetch_active');a.emit(0xAF,0xC9)
    a.label('ahead_prefetch_active');a.emit(0xFE,2)
    a.abs16(0xCA,'ahead_extend')

    a.label('ahead_run')
    a.abs16(0x3A,'ahead_state');a.emit(0xB7)
    a.abs16((0xED,0x73),'ahead_caller_sp')
    a.abs16(0xC2,'ahead_resume')
    a.emit(0x3E,1);a.abs16(0x32,'ahead_state')
    a.emit(0x31);a.word(STACK_TOP)
    a.abs16(0x21,'ahead_done');a.emit(0xE5)
    a.abs16(0xC3,'prepare_packet')
    a.label('ahead_done')
    a.emit(0x3E,2);a.abs16(0x32,'ahead_state')
    a.abs16((0xED,0x7B),'ahead_caller_sp');a.emit(0x3E,1,0xC9)

    a.label('ahead_extend')
    a.abs16(0x2A,'slice_output');a.abs16((0xED,0x5B),'block_end')
    a.emit(0xB7,0xED,0x52);a.rel8(0x38,'ahead_extend_begin')
    a.abs16(0xC3,'ahead_precopy')
    a.label('ahead_extend_begin')
    a.abs16((0xED,0x73),'ahead_caller_sp')
    a.emit(0x3E,3);a.abs16(0x32,'ahead_state')
    a.emit(0x31);a.word(STACK_TOP)
    a.abs16(0x21,'ahead_done');a.emit(0xE5,0xEB)
    a.abs16(0x22,'slice_target');a.abs16(0xC3,'ahead_decode')

    a.label('ahead_precopy')
    # This threshold also excludes final padding after the last block.
    a.abs16(0x2A,'ring_count');a.emit(0x11);a.word(30)
    a.emit(0xB7,0xED,0x52);a.rel8(0x30,'ahead_precopy_begin')
    a.emit(0xAF,0xC9)
    a.label('ahead_precopy_begin')
    a.abs16((0xED,0x73),'ahead_caller_sp')
    a.emit(0x3E,4);a.abs16(0x32,'ahead_state')
    a.emit(0x31);a.word(STACK_TOP)
    a.abs16(0xCD,'load_block_header');a.abs16(0xCD,'load_block_body')
    a.emit(0x3E,1);a.abs16(0x32,'ahead_input_ready')
    a.emit(0x3E,5);a.abs16(0x32,'ahead_state')
    a.abs16((0xED,0x7B),'ahead_caller_sp');a.emit(0x3E,1,0xC9)

    a.label('ahead_checkpoint')
    a.emit(0xF5);a.abs16(0x3A,'ahead_force');a.emit(0xB7)
    a.rel8(0x28,'ahead_pause');a.emit(0xF1,0xC9)
    a.label('ahead_pause');a.emit(0xC5,0xD5,0xE5,0x3E,1)
    a.label('ahead_suspend')
    a.abs16((0xED,0x73),'ahead_saved_sp')
    a.abs16((0xED,0x7B),'ahead_caller_sp');a.emit(0xC9)
    a.label('ahead_resume')
    a.abs16((0xED,0x7B),'ahead_saved_sp')
    a.emit(0xE1,0xD1,0xC1,0xF1,0xC9)

    # A background quantum must never wait for input or invoke the ROM.
    # 30 sectors cover the maximum 7424-byte block, header and partial sector.
    a.label('ahead_require_input')
    a.abs16(0x3A,'ahead_force');a.emit(0xB7,0xC0)
    a.abs16(0x2A,'ring_count');a.emit(0x11);a.word(30)
    a.emit(0xB7,0xED,0x52,0xD0)
    a.abs16(0xCD,'ahead_yield_idle')
    a.abs16(0xC3,'ahead_require_input')
    a.label('ahead_yield_idle');a.emit(0xF5,0xC5,0xD5,0xE5,0xAF)
    a.abs16(0xC3,'ahead_suspend')

    a.label('ahead_decode')
    a.abs16(0x2A,'slice_target');a.abs16(0x22,'ahead_decode_end')
    a.label('ahead_decode_loop')
    a.abs16(0x3A,'ahead_force');a.emit(0xB7);a.rel8(0x28,'ahead_decode_bounded')
    a.abs16(0x2A,'ahead_decode_end');a.abs16(0x22,'slice_target')
    a.abs16(0xC3,'slice_until')
    a.label('ahead_decode_bounded')
    a.abs16(0x2A,'slice_output');a.emit(0x11);a.word(DECODE_QUANTUM)
    a.emit(0x19)
    a.abs16((0xED,0x5B),'ahead_decode_end');a.emit(0xE5,0xB7,0xED,0x52,0xE1)
    a.rel8(0x38,'ahead_target_ready');a.emit(0xEB)
    a.label('ahead_target_ready');a.abs16(0x22,'slice_target')
    a.abs16(0xCD,'slice_until')
    a.abs16(0x2A,'slice_output');a.abs16((0xED,0x5B),'ahead_decode_end')
    a.emit(0xB7,0xED,0x52,0xD0)
    a.abs16(0xCD,'ahead_checkpoint');a.abs16(0xC3,'ahead_decode_loop')


def emit_variables(a):
    for name in ('ahead_state','ahead_force','ahead_input_ready'):
        a.label(name);a.emit(0)
    for name in ('ahead_caller_sp','ahead_saved_sp','ahead_decode_end'):
        a.label(name);a.word(0)
