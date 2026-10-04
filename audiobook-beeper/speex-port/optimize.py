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


INNOVATION='''
.globl _innovation_start, _innovation_end, _build_innovation
_innovation_start = 0x7c00
_innovation_end = 0x8000
; Build both energy alternatives once per changed frame gain. Cache starts invalid.
; Clobbers AF/BC/DE/HL. Tables hold signed24 floor(shape*energy/4096), shape -65..66.
prepare_innovation:
ld a,(innov_valid)
or a,a
jr z,innov_rebuild
ld a,(innov_cached)
ld hl,#gain_index
cp a,(hl)
ret z
innov_rebuild:
ld a,#1
ld (innov_valid),a
ld a,(gain_index)
ld (innov_cached),a
ld l,a
ld h,#0
add hl,hl
add hl,hl
add hl,hl
ld de,#energy_table
add hl,de
ld (energy_pair),hl
ex de,hl
ld hl,#0x7c00
call _build_innovation
ld de,(energy_pair)
inc de
inc de
inc de
inc de
ld hl,#0x7e00
jp _build_innovation

; HL destination, DE positive energy32 pointer. Only the initial -65 value
; needs multiplication; advance integer quotient and 12-bit remainder exactly.
_build_innovation::
ld (table_out),hl
ld a,#-65
call mulq12
ld (table_value),de
ld a,l
ld (table_value+2),a
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
ld (table_step),hl
ld hl,(qarg)
ld a,h
and a,#15
ld h,a
ld (table_frac),hl
ld d,h
ld e,l
'''+('add hl,hl\n'*6)+'''add hl,de
ex de,hl
ld hl,#0
or a,a
sbc hl,de
ld a,h
and a,#15
ld h,a
ld (table_rem),hl
ld a,#132
ld (table_count),a
innov_build_loop:
ld hl,(table_out)
ld de,(table_value)
ld (hl),e
inc hl
ld (hl),d
inc hl
ld a,(table_value+2)
ld (hl),a
inc hl
ld (table_out),hl
ld hl,(table_rem)
ld de,(table_frac)
add hl,de
ld a,h
and a,#16
rrca
rrca
rrca
rrca
ld b,a
ld a,h
and a,#15
ld h,a
ld (table_rem),hl
ld a,b
rrca
ld hl,(table_value)
ld de,(table_step)
adc hl,de
ld a,(table_value+2)
adc a,#0
ld (table_value),hl
ld (table_value+2),a
ld hl,#table_count
dec (hl)
jp nz,innov_build_loop
ret
'''


def stage2(d):
    d=d.replace('state_end:', '''innov_valid: .ds 1
innov_cached: .ds 1
innov_selected: .ds 2
energy_pair: .ds 2
table_out: .ds 2
table_value: .ds 3
table_step: .ds 2
table_frac: .ds 2
table_rem: .ds 2
table_count: .ds 1
state_end:''')
    d=replace_once(d,'ld (gain_index),a','ld (gain_index),a\ncall prepare_innovation')
    start='ld c,a\nld a,(gain_index)'
    old=start+d.split(start)[1].split('ldir')[0]+'ldir'
    d=replace_once(d,old,'''add a,a
add a,#0x7c
ld h,a
ld l,#0
ld (innov_selected),hl''')
    d=replace_once(d,'ld de,#energy\ncall mulq12', '''; Three-byte lookup replaces per-sample multiplication and fractional shifts.
add a,#65
ld l,a
ld h,#0
ld d,h
ld e,l
add hl,hl
add hl,de
ld de,(innov_selected)
add hl,de
ld e,(hl)
inc hl
ld d,(hl)
inc hl
ld l,(hl)''')
    d=d.replace('.area _TABLES (ABS)',INNOVATION+'\n.area _TABLES (ABS)')
    return d


def optimize(folder,variant):
    d=(folder/'decoder.s').read_text()
    d=stage1(d)
    if variant!='pure-r1':d=stage2(d)
    d=d.replace('_entry::','; Entry: packet count at B000; resets state/stack, disables IRQ, clobbers all registers.\n_entry::')
    d=d.replace('_zx_speex_decode::','; Decode one validated 20-byte packet. Carry reports an unsupported mode.\n; Excitation precedes four delayed 40-sample synthesis blocks. All scratch is private.\n_zx_speex_decode::')
    d=d.replace('_zx_speex_lpc::','; Interpolated LSP angles -> next_lpc, preserving upstream fixed-point rounding.\n; P/Q polynomial arithmetic wraps at 32 bits; final coefficients saturate symmetrically.\n_zx_speex_lpc::')
    d=d.replace('enforce_margin:','; Enforce ordered LSP spacing exactly as upstream before the cosine conversion.\nenforce_margin:')
    (folder/'decoder.s').write_text(d,newline='\n')
