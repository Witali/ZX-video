"""Cumulative exact assembly optimizations; baseline generators stay reproducible."""
import re


MUL_S8='''
.globl _mul_s8, mulq12
; Signed A * DE -> HL:DE. Magnitudes use an unsigned 24-bit C:HL accumulator.
_mul_s8::
or a,a
jr nz,s8_nonzero
ld hl,#0
ld de,#0
ret
s8_nonzero:
ld b,a
xor a,d
and a,#128
ld (s8_sign),a
bit 7,b
jr z,s8_a_positive
ld a,b
neg
ld b,a
s8_a_positive:
bit 7,d
jr z,s8_b_positive
xor a,a
sub a,e
ld e,a
sbc a,a
sub a,d
ld d,a
s8_b_positive:
ld hl,#0
ld c,h
'''+''.join(f'''add hl,hl
rl c
sla b
jr nc,s8_bit_{i}
add hl,de
jr nc,s8_bit_{i}
inc c
s8_bit_{i}:
''' for i in range(8))+'''
ex de,hl
ld l,c
ld h,#0
ld a,(s8_sign)
or a,a
jp nz,neg32
ret

; Signed A * positive energy/4096, rounded toward minus infinity.
mulq12:
ld (qcoef),a
ex de,hl
ld de,#qarg
ld bc,#4
ldir
ld hl,(qarg+2)
add hl,hl
add hl,hl
add hl,hl
add hl,hl
ld a,(qarg+1)
rrca
rrca
rrca
rrca
and a,#15
or a,l
ld l,a
ex de,hl
ld a,(qcoef)
call _mul_s8
ld (qtemp),de
ld (qtemp+2),hl
ld de,(qarg)
ld a,d
and a,#15
ld d,a
ld a,(qcoef)
call _mul_s8
ld e,d
ld d,l
'''+('sra d\nrr e\n'*4)+'''
ld a,d
add a,a
sbc a,a
ld h,a
ld l,a
ld bc,(qtemp)
ex de,hl
add hl,bc
ex de,hl
ld bc,(qtemp+2)
adc hl,bc
ret
'''

CLAMP24='''; S=sum(gain8*history16), bounded to +/-2048000 before innovation.
ld a,(accum+2)
bit 7,a
jr nz,exc_negative24
cp #31
jr c,excitation_clamped
jr nz,clamp_exc_positive
ld hl,(accum)
ld de,#0x4000
or a,a
sbc hl,de
jr c,excitation_clamped
clamp_exc_positive:
ld hl,#0x4000
ld (accum),hl
ld a,#31
ld (accum+2),a
jr excitation_clamped
exc_negative24:
cp #224
jr c,clamp_exc_negative
jr nz,excitation_clamped
ld hl,(accum)
ld de,#0xc000
or a,a
sbc hl,de
jr nc,excitation_clamped
clamp_exc_negative:
ld hl,#0xc000
ld (accum),hl
ld a,#224
ld (accum+2),a
excitation_clamped:
'''


def replace_once(text,old,new):
    assert text.count(old)==1,old[:100]
    return text.replace(old,new)


def stage1(d):
    from make_decoder import array
    d=d.replace('state_end:', 's8_sign: .ds 1\nstate_end:')
    old=d.split('pitch_gains:\n')[1].split('energy_table:')[0]
    gains=[array('gain_cdbk_lbr')[4*i+j]+32 for i in range(32) for j in range(3)]
    raw=[v for x in gains for v in (x&255,(x>>8)&255)]
    d=d.replace(old,'\n'.join('.db '+','.join(map(str,raw[i:i+16])) for i in range(0,len(raw),16))+'\n')
    for k in range(3):
        start=f'ld hl,(gain_current+{(2-k)*2})\ncall _zx_mul_table'
        end=f'skip_pitch_{k}:'
        old=d.split(start)[1].split(end)[0]
        new='''
ld bc,(accum)
ex de,hl
add hl,bc
ex de,hl
ld a,(accum+2)
adc a,l
ld (accum),de
ld (accum+2),a
'''
        d=replace_once(d,start+old,f'ld a,(gain_current+{(2-k)*2})\ncall _mul_s8'+new)
    start='ld hl,(accum+2)\nld de,#4000'
    old=start+d.split(start)[1].split('excitation_clamped:\n')[0]+'excitation_clamped:\n'
    d=replace_once(d,old,CLAMP24)
    start='ld l,a\nadd a,a\nsbc a,a\nld h,a\nadd hl,hl\nadd hl,hl\nld de,#energy\ncall mulq14'
    old=start+d.split(start)[1].split('call _zx_clip')[0]
    add='''ld bc,(accum)
ex de,hl
add hl,bc
ex de,hl
ld a,(accum+2)
adc a,l
ld l,a
'''
    new='ld de,#energy\ncall mulq12\n'+add+add+'''ld bc,#64
ex de,hl
add hl,bc
ex de,hl
jr nc,exc_round_done
inc l
exc_round_done:
'''+('sra l\nrr d\nrr e\n'*7)+'''ld a,l
add a,a
sbc a,a
ld h,a
'''
    d=replace_once(d,old,new)
    d=d.replace('.area _TABLES (ABS)',MUL_S8+'\n.area _TABLES (ABS)')
    return d


def optimize(folder,variant):
    d=(folder/'decoder.s').read_text()
    d=stage1(d)
    d=d.replace('_entry::','; Entry: packet count at B000; resets state/stack, disables IRQ, clobbers all registers.\n_entry::')
    d=d.replace('_zx_speex_decode::','; Decode one validated 20-byte packet. Carry reports an unsupported mode.\n; Excitation precedes four delayed 40-sample synthesis blocks. All scratch is private.\n_zx_speex_decode::')
    d=d.replace('_zx_speex_lpc::','; Interpolated LSP angles -> next_lpc, preserving upstream fixed-point rounding.\n; P/Q polynomial arithmetic wraps at 32 bits; final coefficients saturate symmetrically.\n_zx_speex_lpc::')
    d=d.replace('enforce_margin:','; Enforce ordered LSP spacing exactly as upstream before the cosine conversion.\nenforce_margin:')
    (folder/'decoder.s').write_text(d,newline='\n')
