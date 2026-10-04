"""Exact direct cosine lookup for four-unit angles, polynomial fallback otherwise."""
from make_decoder import cos_int


def generate():
    return '''; Exact upstream integer cosine for HL=0..25736, returned signed16 in DE.
; Fold to 0..12868 using the original boundary convention. Four-unit-aligned
; angles use an exact word table; all other inputs use the original nested
; rounded polynomial. Never round an input angle to the table grid.
; Preserve IX/IY, all alternates and caller SP; clobber ordinary AF/BC/DE/HL,
; the old two-byte cosine scratch and the general multiplier's sign scratch.
; Save the folded sign on the real stack across either path. Nonreentrant.
.globl _cos36_x2, _cos36_aligned, _cos36_polynomial, _cos36_p13
_cos36_x2 = cos_sign
cosine:
ld de,#12868
or a,a
sbc hl,de
jr c,cos36_low
ld de,#12868
ex de,hl
or a,a
sbc hl,de
ld a,#1
jr cos36_folded
cos36_low:
add hl,de
xor a,a
cos36_folded:
push af
ld a,l
and a,#3
jr nz,_cos36_polynomial
_cos36_aligned::
; The table stores cos_int(4*i) as little-endian words. Since x is a multiple
; of four, its byte offset is x/2. The folded endpoint 12868 is included.
srl h
rr l
ld de,#cos_table
add hl,de
ld e,(hl)
inc hl
ld d,(hl)
jp cos36_sign
_cos36_polynomial::
; x2=P13(x*x), then 8192+P13(x2*(-4096+P13(x2*(340+P13(-10*x2))))).
; For folded x<=12868 all P13 results fit signed16. cos_sign/cos_offset are
; adjacent legacy bytes, now one signed16 x2 slot; no state is allocated.
ld d,h
ld e,l
call _cos36_p13
ld (_cos36_x2),hl
ld de,#-10
call _cos36_p13
ld de,#340
add hl,de
ld de,(_cos36_x2)
call _cos36_p13
ld de,#-4096
add hl,de
ld de,(_cos36_x2)
call _cos36_p13
ld de,#8192
add hl,de
ex de,hl
cos36_sign:
pop af
or a,a
ret z
xor a,a
sub a,e
ld e,a
sbc a,a
sub a,d
ld d,a
ret

; P13: signed16 HL*DE, add 4096, arithmetic shift by 13, return low16 in HL.
; The cosine caller's results fit signed16. The product and rounding fit
; signed32 for any signed16 operands. Clobber ordinary AF/BC/DE and the
; multiplier scratch; preserve IX/IY, alternates and the real stack.
_cos36_p13::
call _zx_mul_table
ex de,hl
ld bc,#4096
add hl,bc
jr nc,cos36_rounded
inc de
cos36_rounded:
; Capture product bits 13..15 from H, shift the upper word left three,
; and merge those bits. This exactly returns bits 13..28, including negatives.
ld a,h
rlca
rlca
rlca
and a,#7
ex de,hl
add hl,hl
add hl,hl
add hl,hl
or a,l
ld l,a
ret

'''


def table():
    values=[cos_int(x) for x in range(0,12869,4)]
    assert len(values)==3218
    data=[v for x in values for v in (x&255,(x>>8)&255)]
    return '; Exact cos_int(4*i), i=0..3217; 6436 bytes, no packed-delta table.\n'+''.join(
        '.db '+','.join(map(str,data[i:i+16]))+'\n' for i in range(0,len(data),16))
