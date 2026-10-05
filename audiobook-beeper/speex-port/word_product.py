"""Generate signed16 products from two exact unsigned byte/word partials."""


def generate():
    code='''; Exact signed HL*DE -> signed32 HL:DE. Preserve IX/IY and every
; alternate register; ordinary AF/BC and existing mul_sign are scratch.
; Normalize signs once. -32768 becomes unsigned 32768, without saturation.
_zx_mul_table::
ld a,h
or a,l
jr z,word31_zero
ld a,d
or a,e
jr nz,word31_nonzero
word31_zero:
ld hl,#0
ld de,#0
ret
word31_nonzero:
ld a,h
xor a,d
and a,#128
ld (mul_sign),a
bit 7,h
jr z,word31_a_positive
xor a,a
sub a,l
ld l,a
sbc a,a
sub a,h
ld h,a
word31_a_positive:
bit 7,d
jr z,word31_b_positive
xor a,a
sub a,e
ld e,a
sbc a,a
sub a,d
ld d,a
word31_b_positive:
; Keep the old byte shortcut: if either magnitude fits a byte, use just
; one unsigned8x16 product. Nonzero magnitudes are guaranteed here.
ld a,h
or a,a
jr z,word31_byte
ld a,d
or a,a
jr nz,word31_word
ex de,hl
word31_byte:
ld a,l
call _word31_u8_nonzero
ex de,hl
ld l,a
ld h,#0
jp word31_sign
word31_word:
; a*b = lo8(a)*b + (hi8(a)*b)<<8. The unsigned helper preserves BC/DE.
; Keep hi8(a) in B, then retain the low partial's high byte in C and its
; low word on the real stack while computing the second partial.
ld b,h
ld a,l
call _word31_u8
push hl
ld c,a
ld a,b
call _word31_u8_nonzero
; A:H:L is the high partial, C plus the stacked word is the low partial.
; E already supplies result byte 0. ADD starts the carry chain at byte 1;
; ADC merges bytes 2/3 before sign restoration. No intermediate precision loss.
ld b,a
pop de
ld a,d
add a,l
ld d,a
ld a,c
adc a,h
ld l,a
ld a,b
adc a,#0
ld h,a
word31_sign:
ld a,(mul_sign)
or a,a
ret z
xor a,a
sub a,e
ld e,a
ld a,#0
sbc a,d
ld d,a
ld a,#0
sbc a,l
ld l,a
ld a,#0
sbc a,h
ld h,a
ret

; Unsigned A8 * DE16 -> A:HL24, preserving BC/DE, IX/IY, all alternates
; and the real SP. The nonzero entry requires A!=0; the general entry
; handles a zero low byte. No data scratch or table is required.
.globl _word31_u8, _word31_u8_nonzero
_word31_u8::
or a,a
jr nz,_word31_u8_nonzero
ld h,a
ld l,a
ret
_word31_u8_nonzero::
; A initially contains multiplier bits. Skip its zero prefix, initialize
; HL with DE for the first one, then reuse A for the emerging high product.
'''
    for i in range(8):code+=f'add a,a\njr c,word31_leading_{i}\n'
    for i in range(8):
        dest=f'word31_acc_{i+1}' if i<7 else 'word31_done'
        code+=f'word31_leading_{i}:\nld h,d\nld l,e\njp {dest}\n'
    for i in range(1,8):
        code+=f'''word31_acc_{i}:
add hl,hl
rla
jr nc,word31_skip_{i}
add hl,de
adc a,#0
word31_skip_{i}:
'''
    code+='word31_done:\nret\n\n'
    return code
