"""Generate Q14 products with one coefficient normalization and exact rounding."""
from word_product import generate as word_generate


def unsigned_product():
    source=word_generate()
    body=source.split('word31_b_positive:\n',1)[1].split('word31_sign:\n',1)[0]
    for name in ('byte','word','sign'):body=body.replace('word31_'+name,'q14u_'+name)
    return '''; Unsigned HL16*DE16 -> unsigned32 HL:DE. Same byte/word partials as
; the public signed kernel, without normalization or sign restoration.
; Preserve IX/IY, all alternates and SP. Clobber ordinary AF/BC; no scratch.
.globl _q14_unsigned
_q14_unsigned::
ld a,h
or a,l
jr z,q14u_zero
ld a,d
or a,e
jr nz,q14u_nonzero
q14u_zero:
ld hl,#0
ld de,#0
ret
q14u_nonzero:
'''+body+'q14u_sign:\nret\n\n'


def q14():
    finish='''; P is unsigned and below 2^29. Extract floor(P/16384) into DE;
; it fits a nonnegative signed16 word, so the upper result word is zero.
add hl,hl
add hl,hl
ld a,d
rlca
rlca
and a,#3
or a,l
ld l,a
ex de,hl
ld hl,#0
ld bc,(qtemp)
ex de,hl
add hl,bc
ex de,hl
ld bc,(qtemp+2)
adc hl,bc
'''
    return '''; Exact MULT16_32_Q14: a*int16(b>>14) + floor(a*(b&16383)/16384).
; Input HL=signed16 a, DE=pointer to little-endian signed32 b.
; Return signed32 HL:DE with the upstream high-part truncation.
; Prepare |a| once, retaining the coefficient sign in the existing unused
; s8_sign slot. The current signed8 implementation keeps its sign in C.
; Keep the high argument's intentional signed16 truncation, including wrap.
; Clobber ordinary AF/BC/DE/HL and qcoef/qarg/qtemp/sign; preserve IX/IY,
; all alternate registers and the real SP. Like the old scratch path, nonreentrant.
.globl _q14_unsigned, _q14_sign, _q14_scratch_start, _q14_scratch_end
_q14_sign = s8_sign
_q14_scratch_start = qcoef
_q14_scratch_end = qtemp+4
mulq14:
ld a,h
and a,#128
ld (_q14_sign),a
bit 7,h
jr z,q14_coefficient_positive
xor a,a
sub a,l
ld l,a
sbc a,a
sub a,h
ld h,a
q14_coefficient_positive:
ld (qcoef),hl
ex de,hl
ld de,#qarg
ld bc,#4
ldir
ld hl,(qarg+2)
add hl,hl
add hl,hl
ld a,(qarg+1)
rlca
rlca
and a,#3
or a,l
ld l,a
ld de,(qcoef)
; Compute signed hi*|a|. Duplicate the short call path instead of storing
; and reloading a second sign flag. Unsigned magnitude 32768 remains valid.
bit 7,h
jr z,q14_high_positive
xor a,a
sub a,l
ld l,a
sbc a,a
sub a,h
ld h,a
call _q14_unsigned
call neg32
jp q14_high_ready
q14_high_positive:
call _q14_unsigned
q14_high_ready:
ld (qtemp),de
ld (qtemp+2),hl
ld hl,(qarg)
ld a,h
and a,#63
ld h,a
ld de,(qcoef)
call _q14_unsigned
; For negative a the final result is -(hi*|a| + ceil(P/16384)).
; Select a tail before discarding P's low 14 bits: remainder zero needs
; ordinary negation, otherwise use an initial borrow to compute -sum-1.
; Tail duplication avoids storing/reloading the remainder or coefficient sign.
ld a,(_q14_sign)
or a,a
jp z,q14_positive_tail
ld a,d
and a,#63
or a,e
jp z,q14_negative_exact
q14_negative_fractional:
'''+finish+'''scf
ld a,#0
sbc a,e
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
q14_negative_exact:
'''+finish+'''jp neg32
q14_positive_tail:
'''+finish+'ret\n\n'
