"""Generate the exact negative Q14 product consumed by the LPC recurrence."""


def generate():
    prepare = """ld (qcoef),hl
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
"""
    negate16 = 'xor a,a\nsub a,l\nld l,a\nsbc a,a\nsub a,h\nld h,a\n'
    fraction = """ld (qtemp),de
ld (qtemp+2),hl
ld hl,(qarg)
ld a,h
and a,#63
ld h,a
ld de,(qcoef)
call _q14_unsigned
; Extract Q=floor(|a|*lo/16384) into HL. DE retains the original low word
; for the exact remainder test. P<2^29 and Q fits a nonnegative signed16.
add hl,hl
add hl,hl
ld a,d
rlca
rlca
and a,#3
or a,l
ld l,a
"""
    return """; Private LPC entry: return -MULT16_32_Q14(a,b) modulo32 in HL:DE.
; Input HL=signed16 a, DE=pointer to signed32 b. Preserve the original
; hi=int16(b>>14) truncation and lo=b&16383, even when hi wraps.
; For a>=0 return -a*hi-floor(a*lo/16384). For a<0 return
; |a|*hi+ceil(|a|*lo/16384). Do not negate the signed16 coefficient:
; its -32768 magnitude and the floor/ceiling distinction must remain exact.
; Preserve IX/IY, all alternate registers and caller SP. Clobber ordinary
; AF/BC/DE/HL and the existing qcoef/qarg/qtemp scratch (10 bytes).
; Nonreentrant like mulq14; the ordinary public Q14 entry remains unchanged.
.globl _q14_negated
_q14_negated::
bit 7,h
jp nz,q37_negative
; a>=0: restore the opposite of hi's sign, then subtract the low floor.
"""+prepare+"""bit 7,h
jr z,q37_positive_high_positive
"""+negate16+"""call _q14_unsigned
jp q37_positive_high_ready
q37_positive_high_positive:
call _q14_unsigned
call neg32
q37_positive_high_ready:
"""+fraction+"""; Signed32 high - unsigned Q. Clear carry for floor, then propagate the
; low-word borrow into the upper word. LD and EX preserve that borrow.
ld b,h
ld c,l
ld hl,(qtemp)
or a,a
sbc hl,bc
ex de,hl
ld hl,(qtemp+2)
ld bc,#0
sbc hl,bc
ret
q37_negative:
; a<0: keep |a| as unsigned16 (including 32768). Restore hi's own sign.
"""+negate16+prepare+"""bit 7,h
jr nz,q37_negative_high_negative
call _q14_unsigned
jp q37_negative_high_ready
q37_negative_high_negative:
"""+negate16+"""call _q14_unsigned
call neg32
q37_negative_high_ready:
"""+fraction+"""; Add ceil(P/16384): carry is one exactly when the discarded 14 bits
; are nonzero. ADC includes it in Q; propagate low-word overflow upward.
ld a,d
and a,#63
or a,e
add a,#255
ld de,(qtemp)
adc hl,de
ex de,hl
ld hl,(qtemp+2)
jr nc,q37_negative_return
inc hl
q37_negative_return:
ret

"""
