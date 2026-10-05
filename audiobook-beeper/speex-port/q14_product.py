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


def q14_signed_tails():
    """Dispatch on coefficient sign once and add/subtract the low fraction."""
    prepare='''ld (qcoef),hl
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
'''
    negate16='xor a,a\nsub a,l\nld l,a\nsbc a,a\nsub a,h\nld h,a\n'
    fractional='''ld (qtemp),de
ld (qtemp+2),hl
ld hl,(qarg)
ld a,h
and a,#63
ld h,a
ld de,(qcoef)
call _q14_unsigned
; P=c*lo is below 2^29. Extract Q=floor(P/16384) into HL.
; DE retains the original low word, including all 14 remainder bits.
add hl,hl
add hl,hl
ld a,d
rlca
rlca
and a,#3
or a,l
ld l,a
'''
    return '''; Exact MULT16_32_Q14: a*int16(b>>14) + floor(a*(b&16383)/16384).
; Input HL=signed16 a, DE=pointer to little-endian signed32 b; return HL:DE.
; Split once on a's sign. Both bodies prepare |a| once and restore only the
; sign of the high product. The negative body subtracts ceil(|a|*lo/16384),
; avoiding the old high-product negation followed by whole-result negation.
; Preserve IX/IY, alternate AF/BC/DE/HL and caller SP. Clobber ordinary
; AF/BC/DE/HL and qcoef/qarg/qtemp. Nonreentrant, as in the prior scratch path.
; _q14_sign aliases the old unused slot for checker compatibility; no access.
.globl _q14_unsigned, _q14_sign, _q14_scratch_start, _q14_scratch_end
_q14_sign = s8_sign
_q14_scratch_start = qcoef
_q14_scratch_end = qtemp+4
mulq14:
bit 7,h
jp nz,q33_negative
; a >= 0: high product has hi's sign; the fractional term is nonnegative.
'''+prepare+'''bit 7,h
jr z,q33_positive_high_positive
'''+negate16+'''call _q14_unsigned
call neg32
jp q33_positive_high_ready
q33_positive_high_positive:
call _q14_unsigned
q33_positive_high_ready:
'''+fractional+'''; Add unsigned Q to the signed32 high product. Only low-word overflow can
; change the upper word. EX/LD preserve carry; INC HL is modulo16, as needed.
ld de,(qtemp)
add hl,de
ex de,hl
ld hl,(qtemp+2)
jr nc,q33_positive_return
inc hl
q33_positive_return:
ret
q33_negative:
; a < 0: |a|=32768 remains a valid unsigned magnitude. For hi < 0 the
; high product is already positive; negate it only when hi is nonnegative.
'''+negate16+prepare+'''bit 7,h
jr nz,q33_negative_high_negative
call _q14_unsigned
call neg32
jp q33_negative_high_ready
q33_negative_high_negative:
'''+negate16+'''call _q14_unsigned
q33_negative_high_ready:
'''+fractional+'''; Subtract ceil(P/16384) from signed32 a*hi. Keep Q in BC and form
; R=(D&63)|E from the untouched low product word. ADD A,255 sets carry
; exactly when R != 0, supplying the rounding borrow for the low SBC.
; The upper SBC propagates its borrow. All intervening LD/EX preserve it.
; This handles exact fractions and a=-32768 without special saturation.
ld b,h
ld c,l
ld hl,(qtemp)
ld a,d
and a,#63
or a,e
add a,#255
sbc hl,bc
ex de,hl
ld hl,(qtemp+2)
ld bc,#0
sbc hl,bc
ret

'''
