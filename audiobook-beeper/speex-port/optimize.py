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


def register_multiplier(f):
    start=f.index('_zx_mul_table::')
    stop=f.index('; Unsigned A*C',start)
    code='''; Exact register-based signed16x16 -> HL:DE, preserving IX/IY.
; BC:HL shifts as a 32-bit accumulator; incoming multiplier bits select adds.
_zx_mul_table::
ld a,h
or a,l
jr z,reg_zero
ld a,d
or a,e
jr nz,reg_nonzero
reg_zero:
ld hl,#0
ld de,#0
ret
reg_nonzero:
ld a,h
xor a,d
and a,#128
ld (mul_sign),a
bit 7,h
jr z,reg_a_positive
xor a,a
sub a,l
ld l,a
sbc a,a
sub a,h
ld h,a
reg_a_positive:
bit 7,d
jr z,reg_b_positive
xor a,a
sub a,e
ld e,a
sbc a,a
sub a,d
ld d,a
reg_b_positive:
ld a,h
or a,a
jr z,reg_byte
ld a,d
or a,a
jr nz,reg_word
ex de,hl
reg_byte:
ld b,l
ld c,#0
ld hl,#0
jp reg_last8
reg_word:
ld b,h
ld c,l
ld hl,#0
'''
    for i in range(16):
        if i==8:code+='reg_last8:\n'
        code+=f'''add hl,hl
rl c
rl b
jr nc,reg_bit_{i}
add hl,de
jr nc,reg_bit_{i}
inc bc
reg_bit_{i}:
'''
    code+='''ex de,hl
ld h,b
ld l,c
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

'''
    return f[:start]+code+f[stop:]


def coefficient_tables(d,f):
    d=d.replace('state_end:', '''coef_valid: .ds 1
coef_old: .ds 20
coef_ptr: .ds 2
coef_out: .ds 2
coef_step: .ds 4
coef_taps: .ds 1
coef_group: .ds 1
coef_count: .ds 1
coef_nibbles: .ds 4
state_end:''')
    code='''
.globl _coefficient_start, _coefficient_end, _prepare_coefficients
.globl _split_nibbles, _coefficient_product
_coefficient_start = 0x7200
_coefficient_end = 0x7c00
; Build ten coefficient pages if LPC changed. Each page holds four 16x32-bit
; partial-product tables, shifted 0/4/8/12 bits; the top nibble is signed.
; Clobbers both ordinary and alternate AF/BC/DE/HL sets; preserves IX/IY.
_prepare_coefficients::
ld a,(coef_valid)
or a,a
jr z,coef_rebuild
ld hl,#_zx_lpc
ld de,#coef_old
ld b,#20
coef_compare:
ld a,(de)
cp a,(hl)
jr nz,coef_rebuild
inc hl
inc de
djnz coef_compare
ret
coef_rebuild:
ld a,#1
ld (coef_valid),a
ld hl,#_zx_lpc
ld de,#coef_old
ld bc,#20
ldir
ld hl,#_zx_lpc
ld (coef_ptr),hl
ld hl,#0x7200
ld (coef_out),hl
ld a,#10
ld (coef_taps),a
coef_tap:
ld hl,(coef_ptr)
ld e,(hl)
inc hl
ld d,(hl)
inc hl
ld (coef_ptr),hl
ld (coef_step),de
ld a,d
add a,a
sbc a,a
ld h,a
ld l,a
ld (coef_step+2),hl
ld hl,(coef_out)
exx
xor a,a
ld (coef_group),a
coef_group_start:
ld hl,#0
ld de,#0
ld a,#16
ld (coef_count),a
coef_build_loop:
'''
    for reg in ('e','d','l','h'):
        code+=f'ld a,{reg}\nexx\nld (hl),a\ninc hl\nexx\n'
    code+='''ld bc,(coef_step)
ex de,hl
add hl,bc
ex de,hl
ld bc,(coef_step+2)
adc hl,bc
ld a,(coef_count)
dec a
ld (coef_count),a
jr z,coef_group_done
cp #8
jr nz,coef_build_loop
ld a,(coef_group)
cp #3
jr nz,coef_build_loop
; At nibble 8, current value is +8*step. Flip it for signed digits -8..-1.
call neg32
jr coef_build_loop
coef_group_done:
ld a,(coef_group)
inc a
ld (coef_group),a
cp #4
jr z,coef_tap_done
; Sixteen increments already formed the next group's step = previous*16.
ld (coef_step),de
ld (coef_step+2),hl
jp coef_group_start
coef_tap_done:
exx
ld (coef_out),hl
exx
ld a,(coef_taps)
dec a
ld (coef_taps),a
jp nz,coef_tap
ret

; HL signed sample multiplier. Split it once for all ten taps; clobbers AF only.
_split_nibbles::
'''
    for i,reg in enumerate(('l','l','h','h')):
        code+=f'ld a,{reg}\n'
        code+=('and a,#15\nadd a,a\nadd a,a\n' if i%2==0 else 'and a,#240\nrrca\nrrca\n')
        if i:code+=f'or a,#{64*i}\n'
        code+=f'ld (coef_nibbles+{i}),a\n'
    code+='''ret
; A=coefficient page; four cached offsets -> exact signed32 HL:DE.
; Byte additions propagate carry in order, preserving the reference wrap semantics.
_coefficient_product::
ld h,a
ld a,(coef_nibbles)
ld l,a
ld e,(hl)
inc l
ld d,(hl)
inc l
ld c,(hl)
inc l
ld b,(hl)
'''
    for i in range(1,4):
        code+=f'ld a,(coef_nibbles+{i})\nld l,a\n'
        for j,reg in enumerate(('e','d','c','b')):
            code+=f'ld a,{reg}\n'+('add' if j==0 else 'adc')+f' a,(hl)\nld {reg},a\n'
            if j!=3:code+='inc l\n'
    code+='ld h,b\nld l,c\nret\n'
    d=d.replace('.area _TABLES (ABS)',code+'\n.area _TABLES (ABS)')
    f=f.replace('.module speex_filter','.module speex_filter\n.globl _prepare_coefficients, _split_nibbles, _coefficient_product')
    f=replace_once(f,'    ld (asm_count),a','    ld (asm_count),a\n    call _prepare_coefficients')
    f=replace_once(f,'    ld (asm_n),hl','    ld (asm_n),hl\n    call _split_nibbles')
    for i in range(10):
        f=replace_once(f,f'    ld hl,(_zx_lpc+{2*i})\n    ld de,(asm_n)\n    call _zx_mul_table',f'    ld a,#{0x72+i}\n    call _coefficient_product')
    return d,f


def compact_lpc(d):
    # Original LSP vectors are multiples of 16. Divide before weighting so
    # every intermediate fits signed16 and both reference roundings are exact.
    begin=d.index('jp nz,exc_subframe')+len('jp nz,exc_subframe')
    end=d.index('ld hl,#lsp\nld de,#old_lsp',begin)
    interpolation='\n; Exact quarter interpolation: original codebook LSPs are multiples of 16.\n'
    for sub in range(4):
        for i in range(10):
            if sub==3:
                interpolation+=f'ld hl,(lsp+{2*i})\nld (interp+{2*i}),hl\n'
                continue
            for name,weight in [('old_lsp',3-sub),('lsp',sub+1)]:
                interpolation+=f'ld hl,({name}+{2*i})\n'+('srl h\nrr l\n'*2)
                if weight==2:interpolation+='add hl,hl\n'
                if weight==3:interpolation+='ld d,h\nld e,l\nadd hl,hl\nadd hl,de\n'
                if name=='old_lsp':interpolation+='ld b,h\nld c,l\n'
            interpolation+=f'add hl,bc\nld (interp+{2*i}),hl\n'
        interpolation+=f'''call enforce_margin
call _zx_speex_lpc
ld hl,#excitation+{288+80*sub}
ld de,#_pcm+{80*sub}
call _zx_speex_filter
ld hl,#next_lpc
ld de,#_zx_lpc
ld bc,#20
ldir
'''
    d=d[:begin]+interpolation+d[end:]
    d=d.replace('polynomial_p: .ds 312','polynomial_p: .ds 24').replace('polynomial_q: .ds 312','polynomial_q: .ds 24')
    d=d.replace('old_p: .ds 4\nold_q: .ds 4\n','')
    start=d.index('_zx_speex_lpc::');end=d.index('.globl _mul_s8',start)
    code='''_zx_speex_lpc::
; Each polynomial is palindromic. Keep coefficients 0..degree/2 only;
; update descending so all previous-stage operands remain available.
; Each Q14 product keeps the original signed16 high-part truncation.
'''
    for i in range(10):code+=f'ld hl,(interp+{2*i})\ncall cosine\nex de,hl\nadd hl,hl\nadd hl,hl\nld (frequency+{2*i}),hl\n'
    def add(at):return f'ld bc,({at})\nex de,hl\nadd hl,bc\nex de,hl\nld bc,({at}+2)\nadc hl,bc\n'
    def save(at):return f'ld ({at}),de\nld ({at}+2),hl\n'
    for name,k in [('polynomial_p',0),('polynomial_q',1)]:
        code+=f'ld hl,#0\nld ({name}),hl\nld hl,#16\nld ({name}+2),hl\n'
        code+=f'ld de,(frequency+{2*k})\ncall negative_frequency64\n'+save(name+'+4')
    for stage in range(1,5):
        for j in range(stage+1,0,-1):
            for name,k in [('polynomial_p',0),('polynomial_q',1)]:
                if j==1:
                    code+=f'ld de,(frequency+{(2*stage+k)*2})\ncall negative_frequency64\n'
                else:
                    code+=f'ld hl,(frequency+{(2*stage+k)*2})\nld de,#{name}+{4*(j-1)}\ncall mulq14\ncall neg32\n'
                previous=j if j<=stage else 2*stage-j
                code+=add(f'{name}+{4*previous}')
                if j>=2:code+=add(f'{name}+{4*(j-2)}')
                code+=save(f'{name}+{4*j}')
    for j in range(1,11):
        previous=min(j-1,11-j);current=min(j,10-j)
        code+=f'ld de,(polynomial_q+{4*previous})\nld hl,(polynomial_q+{4*previous+2})\ncall neg32\n'
        code+=add(f'polynomial_p+{4*previous}')+add(f'polynomial_p+{4*current}')+add(f'polynomial_q+{4*current}')
        code+=f'''ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_{j}
inc hl
compact_round_{j}:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+{2*(j-1)}),de
'''
    code+='''ret
; DE signed frequency -> HL:DE = -frequency*64. The constant polynomial
; endpoint is 2^20, so its Q14 product is an exact shift, not a general multiply.
negative_frequency64:
ld a,d
add a,a
sbc a,a
ld h,a
ld l,a
'''+('sla e\nrl d\nrl l\n'*6)+'jp neg32\n\n'
    return d[:start]+code+d[end:]


def optimize(folder,variant):
    d=(folder/'decoder.s').read_text()
    d=stage1(d)
    if variant!='pure-r1':d=stage2(d)
    f=(folder/'filter.s').read_text()
    if variant in ('pure-r3-register','pure-r3','pure-r4'):f=register_multiplier(f)
    if variant in ('pure-r3','pure-r4'):d,f=coefficient_tables(d,f)
    if variant=='pure-r4':d=compact_lpc(d)
    d=d.replace('_entry::','; Entry: packet count at B000; resets state/stack, disables IRQ, clobbers all registers.\n_entry::')
    d=d.replace('_zx_speex_decode::','; Decode one validated 20-byte packet. Carry reports an unsupported mode.\n; Excitation precedes four delayed 40-sample synthesis blocks. All scratch is private.\n_zx_speex_decode::')
    d=d.replace('_zx_speex_lpc::','; Interpolated LSP angles -> next_lpc, preserving upstream fixed-point rounding.\n; P/Q polynomial arithmetic wraps at 32 bits; final coefficients saturate symmetrically.\n_zx_speex_lpc::')
    d=d.replace('enforce_margin:','; Enforce ordered LSP spacing exactly as upstream before the cosine conversion.\nenforce_margin:')
    (folder/'decoder.s').write_text(d,newline='\n')
    f=f.replace('_zx_speex_filter::','; HL excitation input, DE PCM16 output; 40 samples and direct PCM8 OUT.\n; Preserves IX/IY; AF/BC/DE/HL and private scratch are clobbered.\n_zx_speex_filter::')
    (folder/'filter.s').write_text(f,newline='\n')
