"""Specialize exact synthesis for a nonzero feedback word below 4096."""


def transform(source):
    start=source.index('; Split signed feedback once into IX/IY halves.')
    end=source.index('_filter_emit::',start)
    body=source[start:end]
    setup="""ld a,h
and a,#240
rrca
rrca
or a,#193
.db 0xfd,0x67 ; LD IYH,A: 8 T
"""
    assert body.count(setup)==1
    body=body.replace(setup,'')
    partial="""; Shifted partial has low byte zero. Offset starts at byte 1;
; E remains unchanged and ADD starts a new carry chain at D.
.db 0xfd,0x7c ; LD A,IYH: 8 T
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
    assert body.count(partial)==10
    body=body.replace(partial,'')
    body=body.replace('; Split signed feedback once into IX/IY halves.',
                      '; Split nonzero 12-bit feedback into IXL/IXH/IYL; IYH stays untouched.')
    body=body.replace('; Every inline product leaves exact modulo32 BC:DE, including signed top nibble.',
                      '; Every inline product leaves exact modulo32 BC:DE; its top partial is zero.')
    dispatch="""; Choose once per nonzero sample: n=HL=(-y)&65535. If n<4096, its
; signed top nibble is zero for every coefficient. Preserve the separate
; n=0 state-copy path above; all other signed words use the general kernel.
; Dispatch costs 21 T on either branch; no table stack is borrowed yet.
ld a,h
and a,#240
jp z,_feedback39_top_zero
"""
    source=source[:start]+dispatch+source[start:]
    point=source.index('    .area _QTABLE (ABS)')
    extra="""
; Exact feedback update for 1<=n<=4095. Omit the fourth partial at all ten
; taps (650 T) and its offset setup (34 T). The final JP costs 10 T.
; Preserve real SP and all alternate registers, including the sample cursor.
; Ordinary AF/BC/DE/HL and IXL/IXH/IYL are scratch; IYH is untouched.
; IRQ remains disabled while SP reads tables. No CALL/PUSH/RET is allowed
; until the saved real SP is restored before returning to port emission.
.globl _feedback39_top_zero
_feedback39_top_zero::
"""+body+'jp _filter_emit\n\n'
    return source[:point]+extra+source[point:]
