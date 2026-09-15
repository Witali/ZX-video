"""Defer the read quota near presentation, retaining debt and a queue reserve."""


def emit(a, quota, reserve, *, keepalive=False):
    a.label('prefetch_loop')
    # Saturate the debt at ring capacity; filling the ring clears it anyway.
    a.abs16(0x2A,'read_debt');a.emit(0x11);a.word(quota);a.emit(0x19)
    a.emit(0x11);a.word(320);a.emit(0xE5,0xB7,0xED,0x52,0xE1)
    a.rel8(0x38,'debt_added');a.emit(0xEB)
    a.label('debt_added');a.abs16(0x22,'read_debt')
    a.label('prefetch_check')
    a.emit(0xD9);a.abs16(0x22,'elapsed_fields');a.emit(0xD9)
    a.label('clock_check')
    # Enforce the reserve even when late. EOF is allowed to drain the ring.
    a.abs16(0x2A,'disk_sectors_remaining');a.emit(0x7C,0xB5)
    a.rel8(0x28,'debt_deadline')
    a.abs16(0x2A,'ring_count');a.emit(0x11);a.word(reserve)
    a.emit(0xB7,0xED,0x52);a.abs16(0xDA,'debt_read')
    a.label('debt_deadline')
    a.abs16(0x2A,'elapsed_fields');a.abs16((0xED,0x5B),'next_frame_field')
    a.emit(0xB7,0xED,0x52,0xCB,0x7C);a.abs16(0xCA,'frame_due')
    # Do not run a whole quantum in the final partial field.
    a.emit(0x23,0x7C,0xB5);a.abs16(0xCA,'debt_wait')
    a.abs16(0x3A,'disk_track');a.emit(0x47)
    a.abs16(0x3A,'fast_disk_track');a.emit(0xB8);a.rel8(0x28,'debt_read_window')
    # At least three complete fields for side/track change plus head settling.
    a.emit(0x23,0x7C,0xB5);a.rel8(0x28,'debt_decode_only')
    a.emit(0x23,0x7C,0xB5);a.rel8(0x28,'debt_decode_only')
    a.label('debt_read_window');a.emit(0x3E,1);a.abs16(0x32,'read_window')
    a.abs16(0x2A,'read_debt');a.emit(0x7C,0xB5);a.rel8(0x20,'debt_read')
    a.rel8(0x18,'debt_decode')
    a.label('debt_decode_only');a.emit(0xAF);a.abs16(0x32,'read_window')
    a.label('debt_decode')
    a.emit(0xFB);a.label('ahead_call');a.abs16(0xCD,'ahead_prefetch')
    a.label('ahead_return');a.emit(0xF3,0xB7);a.abs16(0xC2,'prefetch_check')
    a.abs16(0x3A,'read_window');a.emit(0xB7);a.rel8(0x28,'debt_wait')
    a.label('debt_read')
    a.abs16(0xCD,'producer_one');a.emit(0xB7);a.rel8(0x28,'debt_idle')
    a.abs16(0x2A,'read_debt');a.emit(0x7C,0xB5);a.abs16(0xCA,'prefetch_check')
    a.emit(0x2B);a.abs16(0x22,'read_debt');a.abs16(0xC3,'prefetch_check')
    a.label('debt_idle');a.emit(0x21);a.word(0);a.abs16(0x22,'read_debt')
    a.label('debt_wait');a.abs16(0xCD,'wait_field');a.abs16(0xC3,'prefetch_check')
    a.label('frame_due')
    if keepalive:a.abs16(0xCD,'motor_keepalive')
    a.abs16(0x2A,'next_frame_field');a.emit(0x11);a.word(6)
    a.emit(0x19);a.abs16(0x22,'next_frame_field')


def emit_variables(a):
    a.label('read_debt');a.word(0)
    a.label('read_window');a.emit(0)
