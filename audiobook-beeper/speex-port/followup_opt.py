"""Follow-up assembly transforms, always starting from the verified round-four code."""
import re
from optimize import replace_once


def immediate_offsets(d, f):
    """Four self-modified immediate operands replace forty memory loads/sample."""
    for i in range(4):
        d=replace_once(d,f'ld (coef_nibbles+{i}),a',f'ld (_smc{i}),a')
        source='coef_nibbles' + (f'+{i}' if i else '')
        d=replace_once(d,f'ld a,({source})\nld l,a',
                       f'product_offset_{i}:\nld l,#0')
    d += '\n; Only these immediate bytes are writable code. Not reentrant; IRQ is disabled.\n'
    for i in range(4):
        d += f'.globl _smc{i}\n_smc{i} = product_offset_{i}+1\n'
    d=d.replace('; HL signed sample multiplier. Split it once for all ten taps; clobbers AF only.',
                '; HL signed multiplier: patch four LD L,n operands once for all ten taps.\n'
                '; Code must reside in writable RAM. Clobbers AF; no opcode is modified.')
    return d,f


def faster_preparation(d, f):
    d += '\n.globl coef_cache_ptr\n'
    d=d.replace('state_end:', 'coef_cache_ptr: .ds 2\ncoef_force: .ds 1\nstate_end:')
    d=replace_once(d,'coef_rebuild:\nld a,#1',
        'coef_rebuild:\nld a,(coef_valid)\nld (coef_force),a\nld a,#1')
    d=replace_once(d,'ld hl,#_zx_lpc\nld de,#coef_old\nld bc,#20\nldir',
        'ld hl,#coef_old\nld (coef_cache_ptr),hl')
    d=replace_once(d,'ld (coef_ptr),hl\nld (coef_step),de', '''ld (coef_ptr),hl
; Compare each page independently. First use always builds, even for zero.
ld hl,(coef_cache_ptr)
ld a,(hl)
ld (hl),e
inc hl
xor a,e
ld c,a
ld a,(hl)
ld (hl),d
inc hl
xor a,d
or a,c
ld b,a
ld (coef_cache_ptr),hl
ld a,(coef_force)
or a,a
jr z,coef_changed
ld a,b
or a,a
jr nz,coef_changed
ld hl,(coef_out)
inc h
ld (coef_out),hl
jp coef_next
coef_changed:
ld (coef_step),de''')
    start=d.index('ld a,#16\nld (coef_count),a\ncoef_build_loop:')
    end=d.index('coef_group_done:',start)
    body=''.join('ld a,'+r+'\nexx\nld (hl),a\ninc hl\nexx\n' for r in ('e','d','l','h'))
    body+='ld bc,(coef_step)\nex de,hl\nadd hl,bc\nex de,hl\nld bc,(coef_step+2)\nadc hl,bc\n'
    unrolled='; Sixteen additions replace per-entry counters and branches.\n'
    for i in range(16):
        unrolled+=body
        if i==7:
            unrolled+='ld a,(coef_group)\ncp #3\njr nz,coef_unsigned_midpoint\ncall neg32\ncoef_unsigned_midpoint:\n'
    d=d[:start]+unrolled+d[end:]
    d=replace_once(d,'ld (coef_out),hl\nexx\nld a,(coef_taps)',
                   'ld (coef_out),hl\nexx\ncoef_next:\nld a,(coef_taps)')
    return d,f


def port_only(d, f):
    d=replace_once(d,'_pcm: .ds 320','_pcm: .ds 0 ; compatibility symbol; no PCM buffer is allocated')
    d=re.sub(r'ld de,#_pcm\+\d+\n','',d)
    f=replace_once(f,'    push de\n    pop iy\n','')
    for line in ('    push iy\n','    pop iy\n','    ld 0(iy),e\n','    ld 1(iy),d\n','    inc iy\n'):
        f=f.replace(line,'')
    f=f.replace('; HL excitation input, DE PCM16 output; 40 samples and direct PCM8 OUT.',
                '; HL excitation input; 40 samples to PCM8 OUT, no PCM16 output buffer.\n'
                '; Internal PCM16 feedback is retained; _last_pcm16 exposes it to verification.')
    f+='\n.globl _last_pcm16\n_last_pcm16 = asm_y\n'
    return d,f


def approximate_feedback(d, f):
    f=f.replace('exact Speex synthesis','APPROXIMATE Speex feedback synthesis')
    f=f.replace('Internal PCM16 feedback is retained; _last_pcm16 exposes it to verification.',
                'Feedback is quantized; _last_pcm16 exposes the output before PCM8 conversion.')
    d=d.replace('patch four LD L,n operands once for all ten taps.',
                'patch two LD L,n operands once for all ten taps.')
    d=d.replace('four cached offsets -> exact signed32 HL:DE.',
                'two upper-byte offsets -> quantized signed32 HL:DE.')
    start=d.index('_split_nibbles::')+len('_split_nibbles::\n')
    end=d.index('ld a,h\nand a,#15',start)
    d=d[:start]+'; Approximation: floor the signed feedback multiplier to a multiple of 256.\n'+d[end:]
    start=d.index('_coefficient_product::')+len('_coefficient_product::\n')
    end=d.index('product_offset_3:',start)
    d=d[:start]+'''ld h,a
; Only the upper byte contributes. The two lower partial products vanish.
product_offset_2:
ld l,#0
ld e,(hl)
inc l
ld d,(hl)
inc l
ld c,(hl)
inc l
ld b,(hl)
'''+d[end:]
    for i in range(2):d=d.replace(f'.globl _smc{i}\n_smc{i} = product_offset_{i}+1\n','')
    return d,f


def register_preparation(d, f):
    """Keep the 32-bit table step in DE/DE' and write reverse rows with PUSH."""
    d=d.replace('state_end:', 'coef_saved_sp: .ds 2\nstate_end:')
    begin=d.index('coef_changed:\n')
    end=d.index('coef_next:\n',begin)
    code='''coef_changed:
; IRQ must remain disabled. Save the real return stack before using SP as
; a reverse table writer. No CALL/RET occurs until the real SP is restored.
; DE/DE' hold the low/high step; HL/HL' hold the low/high accumulator.
ld (coef_saved_sp),sp
ld a,d
add a,a
sbc a,a
exx
ld d,a
ld e,a
exx
'''
    for part in range(4):
        code+=f'''; Partial table {part}: rows are stored from index 15 down to 0.
ld hl,(coef_out)
ld bc,#{64*(part+1)}
add hl,bc
ld sp,hl
'''
        if part<3:
            code+='ld h,d\nld l,e\nexx\nld h,d\nld l,e\nexx\n'
            code+=('add hl,hl\nexx\nadc hl,hl\nexx\n')*4
            code+='; Save 16*step for the next group before forming 15*step.\n'
            code+='ld (coef_step),hl\nexx\nld (coef_step+2),hl\nexx\n'
        else:
            code+='; Signed high nibble: first row is -step, followed by -2..-8.\n'
            code+='ld hl,#0\nexx\nld hl,#0\nexx\n'
        code+='or a,a\nsbc hl,de\nexx\nsbc hl,de\nexx\n'
        for i in range(15,-1,-1):
            code+='exx\npush hl\nexx\npush hl\n'
            if part==3 and i==8:
                code+='; Convert -8*step to +8*step; next subtraction yields row 7.\n'
                code+='; Its low byte L is zero (coefficient shifted left 15 bits).\n'
                code+='xor a,a\nsub a,h\nld h,a\nexx\n'
                code+='ld a,#0\nsbc a,l\nld l,a\nld a,#0\nsbc a,h\nld h,a\nexx\n'
            if i:code+='or a,a\nsbc hl,de\nexx\nsbc hl,de\nexx\n'
        if part<3:code+='ld de,(coef_step)\nexx\nld de,(coef_step+2)\nexx\n'
    code+='''; Restore the caller's stack before returning or examining the next page.
ld sp,(coef_saved_sp)
ld hl,(coef_out)
inc h
ld (coef_out),hl
'''
    d=d[:begin]+code+d[end:]
    return d,f


def apply(folder, variant):
    d=(folder/'decoder.s').read_text();f=(folder/'filter.s').read_text()
    d,f=immediate_offsets(d,f)
    if variant!='pure-r7':d,f=faster_preparation(d,f)
    if variant not in ('pure-r7','pure-r8'):d,f=port_only(d,f)
    if variant=='pure-r10-approx':d,f=approximate_feedback(d,f)
    if variant=='pure-r15':d,f=register_preparation(d,f)
    (folder/'decoder.s').write_text(d,newline='\n')
    (folder/'filter.s').write_text(f,newline='\n')
