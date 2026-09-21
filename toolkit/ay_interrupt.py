"""Single-producer/single-consumer queue for AY register changes at 50 Hz.

Foreground copies complete records, then publishes one byte (write index).
IM2 consumes at most one record. Empty records advance time without I/O.
The 32 slots of 32 bytes occupy A000h..A3FFh, available only with wrapped
direct input. The ISR does not page RAM, parse video, decompress, or read disk.
"""
from __future__ import annotations

QUEUE_BASE = 0xA000
QUEUE_SLOTS = 32
SLOT_BYTES = 32
VERSION = 11
# Zilog UM0080, routine entry through RET, excluding its CALL and IRQ entry.
# Enabled tick with n>0 changed registers: 367+83*n T; last tick adds 24 T.
# Enqueue six records with n total register writes: 1705+42*n T.
TSTATES = dict(disabled=58,underrun=205,unchanged=377,
               changed_base=367,per_register=83,last_tick_extra=24,
               enqueue_six_base=1705,enqueue_per_register=42,
               previous_fast_irq=116,irq_call=17)


def registers(frame):
    result=[]
    for period in frame.periods:result.extend((period&255,(period>>8)&15))
    return bytes((*result,frame.noise_period,frame.mixer,*frame.volumes))


def encode_ticks(frames):
    """Count, then (register,value) pairs. The first tick initializes all R0..10."""
    previous=None;result=[]
    for frame in frames:
        current=registers(frame)
        changed=[i for i in range(11) if previous is None or current[i]!=previous[i]]
        result.append(bytes([len(changed)])+b''.join(bytes((i,current[i])) for i in changed))
        previous=current
    return result


def emit_slot_address(a):
    # A=index (0..31) -> HL=A000h+32*index. 49 T, AF/HL clobbered.
    a.emit(0x0F,0x0F,0x0F,0x6F,0xE6,3,0xF6,0xA0,0x67,0x7D,0xE6,0xE0,0x6F)


def emit(a, *, backpressure=False):
    a.label('audio_init')
    # Input HL=number of video frames, six audio ticks per video frame.
    a.emit(0xE5,0x54,0x5D,0x29,0x19,0x29)
    a.abs16(0x22,'audio_remaining')
    a.emit(0xAF)
    for name in ('audio_enabled','audio_read_index','audio_write_index'):
        a.abs16(0x32,name)
    a.emit(0x21);a.word(0)
    for name in ('audio_underruns','audio_ticks_played'):a.abs16(0x22,name)
    a.emit(0xE1,0xC9)

    a.label('audio_enqueue_six')
    # Input HL=first record, output HL=first screen command.
    a.emit(0x3E,6);a.abs16(0x32,'audio_enqueue_left')
    a.label('audio_enqueue_one')
    a.abs16(0x3A,'audio_write_index');a.emit(0x3C,0xE6,31,0x47)
    a.abs16(0x3A,'audio_read_index');a.emit(0xB8)
    if backpressure:
        a.abs16(0xC2,'audio_enqueue_space')
        # Slow disk delivery can leave video behind the AY queue. Wait for
        # one complete slot, retaining every original sound record.
        a.emit(0xFB,0x76);a.abs16(0xC3,'audio_enqueue_one')
        a.label('audio_enqueue_space')
    else: a.abs16(0xCA,'fatal')
    a.emit(0xE5);a.abs16(0x3A,'audio_write_index');emit_slot_address(a)
    a.emit(0xEB,0xE1,0x7E,0xFE,12);a.abs16(0xD2,'fatal')
    a.emit(0x87,0x3C,0x4F,0x06,0,0xED,0xB0)
    # Publication after LDIR is atomic; interrupt cannot consume a partial slot.
    a.abs16(0x3A,'audio_write_index');a.emit(0x3C,0xE6,31)
    a.abs16(0x32,'audio_write_index')
    a.abs16(0x3A,'audio_enqueue_left');a.emit(0x3D)
    a.abs16(0x32,'audio_enqueue_left');a.rel8(0x20,'audio_enqueue_one')
    a.emit(0xC9)

    a.label('audio_start')
    # EI/HALT admits exactly the first audio IRQ before resetting video time.
    a.emit(0xF3,0x3E,1);a.abs16(0x32,'audio_enabled');a.emit(0xFB,0x76,0xC9)
    a.label('audio_drain')
    a.abs16(0x3A,'audio_enabled');a.emit(0xB7,0xC8,0xFB,0x76)
    a.rel8(0x18,'audio_drain')

    a.label('audio_tick')
    a.emit(0xF5);a.abs16(0x3A,'audio_enabled');a.emit(0xB7)
    a.abs16(0xCA,'audio_tick_disabled')
    a.emit(0xC5,0xD5,0xE5)
    a.abs16(0x3A,'audio_write_index');a.emit(0x47)
    a.abs16(0x3A,'audio_read_index');a.emit(0xB8)
    a.rel8(0x28,'audio_tick_empty')
    emit_slot_address(a)
    a.emit(0x56,0x23,0x7A,0xB7);a.rel8(0x28,'audio_tick_done')
    a.label('audio_write_loop')
    a.emit(0x7E,0x23,0x01);a.word(0xFFFD);a.emit(0xED,0x79)
    a.emit(0x7E,0x23,0x06,0xBF,0xED,0x79,0x15)
    a.rel8(0x20,'audio_write_loop')
    a.label('audio_tick_done')
    a.abs16(0x3A,'audio_read_index');a.emit(0x3C,0xE6,31)
    a.abs16(0x32,'audio_read_index')
    a.abs16(0x2A,'audio_ticks_played');a.emit(0x23);a.abs16(0x22,'audio_ticks_played')
    a.abs16(0x2A,'audio_remaining');a.emit(0x2B);a.abs16(0x22,'audio_remaining')
    a.emit(0x7C,0xB5);a.rel8(0x20,'audio_tick_return')
    a.emit(0xAF);a.abs16(0x32,'audio_enabled')
    a.rel8(0x18,'audio_tick_return')
    a.label('audio_tick_empty')
    a.abs16(0x2A,'audio_underruns');a.emit(0x23);a.abs16(0x22,'audio_underruns')
    a.label('audio_tick_return');a.emit(0xE1,0xD1,0xC1)
    a.label('audio_tick_disabled');a.emit(0xF1,0xC9)


def emit_variables(a):
    for name in ('audio_enabled','audio_read_index','audio_write_index','audio_enqueue_left'):
        a.label(name);a.emit(0)
    for name in ('audio_remaining','audio_underruns','audio_ticks_played'):
        a.label(name);a.word(0)

