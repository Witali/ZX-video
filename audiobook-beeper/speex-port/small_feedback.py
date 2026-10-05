"""Generate exact low-byte feedback kernels with fused subtractive state updates."""


def transform(source):
    start=source.index('_feedback39_top_zero::\n')+len('_feedback39_top_zero::\n')
    end=source.index('jp _filter_emit\n',start)+len('jp _filter_emit\n')
    body=source[start:end]
    setup="""ld a,h
and a,#15
add a,a
add a,a
or a,#129
.db 0xfd,0x6f ; LD IYL,A: 8 T
"""
    assert body.count(setup)==1;body=body.replace(setup,'')
    partial="""; Shifted partial has low byte zero. Offset starts at byte 1;
; E remains unchanged and ADD starts a new carry chain at D.
.db 0xfd,0x7d ; LD A,IYL: 8 T
ld l,a
ld a,d
add a,(hl)
ld d,a
inc l
ld a,c
adc a,(hl)
ld c,a
inc l
ld a,b
adc a,(hl)
ld b,a
"""
    assert body.count(partial)==10;body=body.replace(partial,'')
    body=body.replace('; Split nonzero 12-bit feedback into IXL/IXH/IYL; IYH stays untouched.',
                      '; Split a positive 1..255 magnitude into IXL/IXH; IY stays untouched.')
    body=body.replace('; Every inline product leaves exact modulo32 BC:DE; its top partial is zero.',
                      '; BC:DE is signed coefficient times the positive byte; upper partials vanish.')
    negative=body
    for tap in range(9):
        old=f"""ld hl,(_zx_memory+{4*tap+4})
add hl,de
ld (_zx_memory+{4*tap}),hl
ld hl,(_zx_memory+{4*tap+6})
adc hl,bc
ld (_zx_memory+{4*tap+2}),hl
"""
        new=f"""; history - positive-magnitude product, modulo 2^32. OR clears the
; low-word borrow; LD preserves it for the upper SBC.
ld hl,(_zx_memory+{4*tap+4})
or a,a
sbc hl,de
ld (_zx_memory+{4*tap}),hl
ld hl,(_zx_memory+{4*tap+6})
sbc hl,bc
ld (_zx_memory+{4*tap+2}),hl
"""
        assert negative.count(old)==1;negative=negative.replace(old,new)
    last='ld (_zx_memory+36),de\nld (_zx_memory+38),bc\n'
    negate=""".globl _feedback40_negate_start, _feedback40_negate_end
_feedback40_negate_start::
; Final state is -product. Use LD A,0 / SBC for intermediate bytes to
; retain the borrow. Only the final byte may use SBC A,A / SUB, since its
; outgoing borrow is discarded. All arithmetic is modulo 2^32.
xor a,a
sub a,e
ld e,a
ld a,#0
sbc a,d
ld d,a
ld a,#0
sbc a,c
ld c,a
sbc a,a
sub a,b
ld b,a
_feedback40_negate_end::
"""
    assert negative.count(last)==1;negative=negative.replace(last,negate+last)
    general='; Split signed feedback once into IX/IY halves.'
    assert source.count(general)==1
    source=source.replace(general,"""; A nonzero high byte FF may be a small negative feedback word.
; Test before borrowing SP. Other general values pay this fixed 18-T check.
ld a,h
inc a
jp z,_feedback40_negative_entry
.globl _feedback40_general
_feedback40_general::
"""+general)
    source=source.replace('_feedback39_top_zero::\n',"""_feedback39_top_zero::
; Within the existing positive 12-bit class, a zero high byte removes the
; third partial as well. Both branches pay 18 T; the n=0 path is separate.
ld a,h
or a,a
jp z,_feedback40_positive
""")
    point=source.index('    .area _QTABLE (ABS)')
    code="""
; Exact low-byte synthesis. Preserve the real SP and every alternate
; register. Ordinary registers and IX halves are scratch; IY stays untouched.
; No CALL/PUSH/RET while SP reads coefficient tables; restore SP before OUT.
; The positive kernel handles n=1..255 using only two partials per tap.
.globl _feedback40_positive, _feedback40_negative_entry
_feedback40_positive::
"""+body+"""
_feedback40_negative_entry::
; H=FF. L=0 means -256, which needs the unchanged general kernel. For
; -255..-1, NEG L gives the exact positive byte magnitude; H is unused by
; the two-offset setup and is overwritten by the first coefficient page.
ld a,l
or a,a
jp z,_feedback40_general
neg
ld l,a
; Subtract each positive-magnitude product from the next history state.
; This replaces both upper partials without a correction table or setup work.
"""+negative+'\n'
    return source[:point]+code+source[point:]
