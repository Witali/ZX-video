"""Nine-byte AY extension used by the interleaved ZXFC v10 player.

R6 low four bits live in byte 1[7:4], R6 bit 4 in byte 3[4].
Zero selects three tones; 1..31 selects noise-only B, tones A and C.
Tone register high bytes are masked before sending them to the chip.
"""

VERSION = 10
# Instruction-table counts, entry through RET, no CALL/IRQ/ULA/ROM time.
APPLY_TSTATES = {'legacy': 624, 'extended_tones': 790, 'extended_noise': 792}


def emit_apply(a, extended=False):
    a.label('ay_apply')
    if extended:
        a.abs16(0x21, 'ay_state')                   # LD HL,state: 10
        a.emit(0x23, 0x7E, 0x0F, 0x0F, 0x0F, 0x0F)  # INC 6, LD 7, 4*RRCA 16
        a.emit(0xE6, 15, 0x5F, 0x23, 0x23, 0x7E)  # AND 7, LD 4, 2*INC 12, LD 7
        a.emit(0xE6, 16, 0xB3, 0x5F, 0x16, 0x38)  # AND 7, OR 4, LD 4, LD 7
        a.rel8(0x28, 'ay_mixer_ready')              # JR Z: 12 / 7
        a.emit(0x16, 0x2A)                         # LD D,n: 7 (noise only)
        a.label('ay_mixer_ready')
        for register, load in ((6, 0x7B), (7, 0x7A)):
            a.emit(0x3E, register, 0x01); a.word(0xFFFD)
            a.emit(0xED, 0x79, load, 0x06, 0xBF, 0xED, 0x79)  # 52 each
    else:
        a.emit(0x3E, 7, 0x01); a.word(0xFFFD); a.emit(0xED, 0x79)
        a.emit(0x3E, 0x38, 0x06, 0xBF, 0xED, 0x79)  # 55
    a.abs16(0x21, 'ay_state')                       # 10
    for register in (0, 1, 2, 3, 4, 5, 8, 9, 10):
        a.emit(0x3E, register, 0x01); a.word(0xFFFD)
        a.emit(0xED, 0x79, 0x7E, 0x23)             # 7+10+12+7+6
        if extended and register in (1, 3): a.emit(0xE6, 15)  # 7 each
        a.emit(0x06, 0xBF, 0xED, 0x79)              # 7+12 => 61/register
    a.emit(0xC9)                                   # 10
