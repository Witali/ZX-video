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


def register_preparation(d, f, additive=False):
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
        if additive:
            code+='''; Negate the step once, keeping HL/HL' and the saved positive
; 16*step unchanged. Then ADD/ADC can descend without clearing carry first.
; Both negation and recurrence are exact modulo32, including -32768 inputs.
'''
            code+=f'.globl _coef_neg_{part}_start, _coef_neg_{part}_end\n_coef_neg_{part}_start::\n'
            if part<2:
                code+='; LD A,0 preserves borrow. SBC A,A / SUB D would lose the outgoing borrow.\n'
                code+='xor a,a\nsub a,e\nld e,a\nld a,#0\nsbc a,d\nld d,a\n'
            else:
                code+='; Shift by 8/12 guarantees E=0; negate D directly and propagate its borrow.\n'
                code+='xor a,a\nsub a,d\nld d,a\n'
            code+='exx\nld a,#0\nsbc a,e\nld e,a\nld a,#0\nsbc a,d\nld d,a\nexx\n'
            code+=f'_coef_neg_{part}_end::\n'
        change='add hl,de\nexx\nadc hl,de\nexx\n' if additive else 'or a,a\nsbc hl,de\nexx\nsbc hl,de\nexx\n'
        code+=change
        for i in range(15,-1,-1):
            code+='exx\npush hl\nexx\npush hl\n'
            if part==3 and i==8:
                code+='; Convert -8*step to +8*step; next update yields row 7.\n' if additive else '; Convert -8*step to +8*step; next subtraction yields row 7.\n'
                code+='; Its low byte L is zero (coefficient shifted left 15 bits).\n'
                code+='xor a,a\nsub a,h\nld h,a\nexx\n'
                code+='ld a,#0\nsbc a,l\nld l,a\nld a,#0\nsbc a,h\nld h,a\nexx\n'
            if i:code+=change
        if part<3:code+='ld de,(coef_step)\nexx\nld de,(coef_step+2)\nexx\n'
    code+='''; Restore the caller's stack before returning or examining the next page.
ld sp,(coef_saved_sp)
ld hl,(coef_out)
inc h
ld (coef_out),hl
'''
    d=d[:begin]+code+d[end:]
    return d,f


def skip_zero_product_bytes(d, f):
    """The <<8 and <<12 partial products have a zero low byte, without exception."""
    split=d.index('_split_nibbles::')
    product=d.index('_coefficient_product::',split)
    head=d[split:product]
    head=replace_once(head,'or a,#128','or a,#129')
    head=replace_once(head,'or a,#192','or a,#193')
    d=d[:split]+head+d[product:]
    for part in (2,3):
        old=f'''product_offset_{part}:
ld l,#0
ld a,e
add a,(hl)
ld e,a
inc l
ld a,d
adc a,(hl)'''
        new=f'''; Shifted partial has low byte zero. Offset starts at byte 1;
; E remains unchanged and ADD starts a new carry chain at D.
product_offset_{part}:
ld l,#0
ld a,d
add a,(hl)'''
        d=replace_once(d,old,new)
    return d,f


def combined_signed8(d, f, leading, signed_word=False):
    """Reuse A for the unread multiplier bits and the accumulating high byte."""
    begin=d.index('s8_b_positive:\n')+len('s8_b_positive:\n')
    end=d.index('; Signed A * positive energy/4096',begin)
    code='''; Unsigned core: A starts with the 8 multiplier bits and ends
; as the product high byte; HL holds the low word. ADD HL,HL carries into
; RLA, whose outgoing carry selects this bit's addition. ADC A,0 merges
; the low-word carry. DE is treated as unsigned; no extra table or scratch.
ld a,b
'''
    if leading:
        code+='; Nonzero B is guaranteed by the entry check. Skip the zero prefix.\n'
        for i in range(8):code+=f'add a,a\njr c,s8_leading_{i}\n'
        for i in range(8):
            target=f's8_acc_{i+1}' if i<7 else 's8_acc_done'
            code+=f's8_leading_{i}:\nld h,d\nld l,e\njp {target}\n'
    else:code+='ld hl,#0\n'
    for i in range(1 if leading else 0,8):
        code+=f'''s8_acc_{i}:
add hl,hl
rla
jr nc,s8_acc_skip_{i}
add hl,de
adc a,#0
s8_acc_skip_{i}:
'''
    code+='''s8_acc_done:
ex de,hl
ld l,a
ld h,#0
ld a,(s8_sign)
or a,a
jp nz,neg32
ret

'''
    if signed_word:
        # DE remains the original unsigned bit pattern during the core.
        # Correct the top product byte by -magnitude when its sign bit is set.
        tail=code.index('s8_acc_done:\n')
        code=code[:tail]+'''s8_acc_done:
; For negative DE, unsigned(DE) differs by 65536. Subtract B from the
; high product byte before sign extending, then apply the original A sign.
bit 7,d
jr z,s8_word_positive
sub a,b
s8_word_positive:
ex de,hl
ld l,a
add a,a
sbc a,a
ld h,a
bit 7,c
jp nz,neg32
ret

'''
    d=d[:begin]+code+d[end:]
    if signed_word:
        start=d.index('s8_nonzero:\n');stop=d.index('s8_b_positive:\n',start)
        d=d[:start]+'''s8_nonzero:
; C preserves the original signed byte; B is its unsigned magnitude.
; The multiplicand DE stays signed, avoiding a word negation and sign RAM.
ld c,a
ld b,a
bit 7,b
jr z,s8_a_positive
neg
ld b,a
s8_a_positive:
'''+d[stop:]
    d=d.replace('; Signed A * DE -> HL:DE. Magnitudes use an unsigned 24-bit C:HL accumulator.',
                '; Signed A * DE -> HL:DE. Magnitudes use an unsigned 24-bit A:HL accumulator.')
    return d,f


def excitation_shift(d, f):
    old=('sra l\nrr d\nrr e\n'*7)+'ld a,l\nadd a,a\nsbc a,a\nld h,a\n'
    new='''; Signed24 L:D:E >> 7, producing sign-extended HL:DE for clipping.
; Save the sign, shift once left and take the upper two bytes. The seven
; discarded low bits never reach DE; this retains arithmetic floor rounding.
.globl _exc_shift_start, _exc_shift_end
_exc_shift_start::
ld a,l
add a,a
sbc a,a
sla e
rl d
rl l
ld e,d
ld d,l
ld l,a
ld h,a
_exc_shift_end::
'''
    d=replace_once(d,old,new)
    return d,f


def innovation_registers(d, f):
    start=d.index('ld a,#132\nld (table_count),a\ninnov_build_loop:')
    end=d.index('\nret\n',start)+len('\nret\n')
    code='''; Hold the 12-bit remainder and fraction scaled by sixteen in
; alternate HL/DE. ADD HL,DE now produces exactly the quotient carry,
; leaving the next remainder scaled in HL. Alternate BC is the output cursor.
; Ordinary HL/C hold the signed24 value, DE its integer step, B the count.
; Both register sets are clobbered; IX/IY and the real stack are preserved.
ld hl,(table_rem)
add hl,hl
add hl,hl
add hl,hl
add hl,hl
ld de,(table_frac)
ex de,hl
add hl,hl
add hl,hl
add hl,hl
add hl,hl
ex de,hl
ld bc,(table_out)
exx
ld hl,(table_value)
ld de,(table_step)
ld a,(table_value+2)
ld c,a
ld b,#132
.globl _innov_register_loop, _innov_register_done
_innov_register_loop::
'''
    for reg in ('l','h','c'):
        code+=f'ld a,{reg}\nexx\nld (bc),a\ninc bc\nexx\n'
    code+='''; EXX preserves flags: fractional carry feeds the integer ADC,
; whose carry then advances the signed24 high byte without changing rounding.
exx
add hl,de
exx
adc hl,de
ld a,c
adc a,#0
ld c,a
djnz _innov_register_loop
_innov_register_done::
ret
'''
    d=d[:start]+code+d[end:]
    d=d.replace('; Clobbers AF/BC/DE/HL. Tables hold signed24 floor(shape*energy/4096), shape -65..66.',
                '; Clobbers both ordinary/alternate AF/BC/DE/HL sets; preserves IX/IY.\n'
                '; Tables hold signed24 floor(shape*energy/4096), shape -65..66.')
    return d,f


def zero_feedback(d, f):
    """A zero synthesis output shifts state exactly, for arbitrary old history."""
    f=replace_once(f,'asm_n: .ds 2\n','')
    f=replace_once(f,'    ld (asm_n),hl\n', '''; A still equals H after the signed negation, so this test needs only OR L.
; Feedback n=-y in HL: a zero product shifts the following nine 32-bit states
; and clears the final state, even when earlier history is nonzero.
.globl _filter_feedback_start, _filter_emit
_filter_feedback_start::
    or a,l
    jp z,filter_zero_feedback
''')
    f=replace_once(f,'    ld a,(asm_y+1)\n','_filter_emit::\n    ld a,(asm_y+1)\n')
    # Keep the handler after the normal filter return, outside its fallthrough.
    begin=f.index('_filter_emit::')
    end=f.index('    ret\n',begin)+len('    ret\n')
    f=f[:end]+'''
; Zero-feedback update; preserves IX/IY and SP, clobbers AF/BC/DE/HL.
; Source is four bytes ahead of destination, so forward LDIR's overlap is safe.
; No coefficient products are used; their cached nibble operands can stay old.
filter_zero_feedback:
    ld hl,#_zx_memory+4
    ld de,#_zx_memory
    ld bc,#36
    ldir
    ld hl,#0
    ld (_zx_memory+36),hl
    ld (_zx_memory+38),hl
    jp _filter_emit
'''+f[end:]
    return d,f


def inline_products(d, f, pop_tables=False):
    """Keep nibble offsets in index halves, leaving ordinary BC:DE for the sum."""
    f+='''
; Playback never calls the retained standalone self-modifying product helpers.
; Verification must forbid every code write for this entry-to-completion path.
.globl _immutable_playback_code
_immutable_playback_code = 1
'''
    f=replace_once(f,'    push ix\n    push hl\n    pop ix\n',
                   '    push ix\n    push iy\n    push hl\n')
    f=replace_once(f,'    call _prepare_coefficients\n', '''    call _prepare_coefficients
; Preparation clobbers both register sets. Recover the saved input cursor only
; afterwards; alternate HL remains its cursor throughout this 40-sample call.
    exx
    pop hl
    exx
'''+('    ld (_filter_saved_sp),sp\n' if pop_tables else ''))
    f=replace_once(f,'    ld c,0(ix)\n    ld b,1(ix)\n', '''; Fetch through the alternate cursor and transfer its word via the real stack.
; _zx_clip and the inline product/state update preserve alternate HL.
    exx
    ld c,(hl)
    inc hl
    ld b,(hl)
    inc hl
    push bc
    exx
    pop bc
''')
    f=replace_once(f,'    inc ix\n    inc ix\n','')
    f=replace_once(f,'    pop ix\n    ret\n','    pop iy\n    pop ix\n    ret\n')
    f=f.replace('; Preserves IX/IY; AF/BC/DE/HL and private scratch are clobbered.',
                '; Preserves IX/IY; ordinary and alternate AF/BC/DE/HL and scratch are clobbered.')
    # Build a sample's four offsets once, without writable product instructions.
    split=d[d.index('_split_nibbles::\n')+len('_split_nibbles::\n'):d.index('; A=coefficient page;')]
    assert split.endswith('ret\n')
    split=split[:-len('ret\n')]
    regs=('ixl','ixh','iyl','iyh')
    # SDAS rejects index-half mnemonics. Encode the real Z80 prefixed register
    # operations explicitly, keeping their mnemonic and timing in the output.
    for i,reg in enumerate(regs):
        prefix=0xdd if i<2 else 0xfd;store=0x6f if i%2==0 else 0x67
        split=replace_once(split,f'ld (_smc{i}),a',f'.db {prefix:#x},{store:#x} ; LD {reg.upper()},A: 8 T')
    product=d[d.index('_coefficient_product::\n')+len('_coefficient_product::\n'):d.index('\n.area _TABLES',d.index('_coefficient_product::'))]
    product=replace_once(product,'ld h,a\n','')
    product=replace_once(product,'ld h,b\nld l,c\nret\n','')
    product=product.rstrip()+'\n'
    for i,reg in enumerate(regs):
        prefix=0xdd if i<2 else 0xfd;load=0x7d if i%2==0 else 0x7c
        product=replace_once(product,f'product_offset_{i}:\nld l,#0',
                             f'.db {prefix:#x},{load:#x} ; LD A,{reg.upper()}: 8 T\nld l,a')
    if pop_tables:
        product=replace_once(product,'ld e,(hl)\ninc l\nld d,(hl)\ninc l\nld c,(hl)\ninc l\nld b,(hl)\n',
                             'ld sp,hl\npop de\npop bc\n')
        f=replace_once(f,'asm_y: .ds 2\n','asm_y: .ds 2\n.globl _filter_saved_sp\n_filter_saved_sp:: .ds 2\n')
    body='''; Split signed feedback once into IX/IY halves. Indexed LD A,r followed
; by ordinary LD L,A intentionally avoids DD/FD substitution of ordinary L.
; Every inline product leaves exact modulo32 BC:DE, including signed top nibble.
'''+split
    if pop_tables:
        body+='''; IRQ must remain disabled. Each tap borrows SP to read four table bytes
; with POP; no CALL/PUSH/RET occurs before the saved real SP is restored.
; Coefficient preparation has its own independent saved-SP slot.
'''
    for tap in range(10):
        body+=f'; Synthesis tap {tap}: coefficient page {0x72+tap:#04x}.\nld h,#{0x72+tap}\n'+product
        if tap<9:
            body+=f'''ld hl,(_zx_memory+{4*tap+4})
add hl,de
ld (_zx_memory+{4*tap}),hl
ld hl,(_zx_memory+{4*tap+6})
adc hl,bc
ld (_zx_memory+{4*tap+2}),hl
'''
        else:body+='ld (_zx_memory+36),de\nld (_zx_memory+38),bc\n'
    if pop_tables:body+='ld sp,(_filter_saved_sp)\n'
    start=f.index('    call _split_nibbles\n');end=f.index('_filter_emit::',start)
    f=f[:start]+body+f[end:]
    return d,f


def pitch_accumulator(d, f):
    """Keep the modulo24 pitch sum in alternate HL/C across the three products."""
    start=d.index('exc_sample:\n');end=d.index('; S=sum(gain8*history16)',start)
    body=d[start:end]
    body=replace_once(body,'ld hl,#0\nld (accum),hl\nld (accum+2),hl\n','''; Alternate HL/C hold the low16/high8 modulo24 pitch sum. The signed8
; product and its neg32 tail preserve all alternate registers. No sum RAM
; access is needed until all three active-or-skipped pitch taps are handled.
.globl _pitch_init_start, _pitch_init_end, _pitch_sum_state
_pitch_sum_state = accum
_pitch_init_start::
exx
ld hl,#0
ld c,#0
exx
_pitch_init_end::
''')
    old='ld bc,(accum)\nex de,hl\nadd hl,bc\nex de,hl\nld a,(accum+2)\nadc a,l\nld (accum),de\nld (accum+2),a\n'
    assert body.count(old)==3
    for tap in range(3):
        new=f'''; Transfer the low product word through the real stack. EXX and POP
; preserve flags; ADD supplies carry for the high-byte ADC. Discard carry
; beyond bit 23 exactly as in the previous RAM accumulation.
.globl _pitch_add_{tap}_start, _pitch_add_{tap}_end
_pitch_add_{tap}_start::
push de
ld a,l
exx
pop de
add hl,de
adc a,c
ld c,a
exx
_pitch_add_{tap}_end::
'''
        body=body.replace(old,new,1)
    body+='''; Write exactly the three bytes consumed by the unchanged clamp and
; innovation logic. The fourth scratch byte is never read on this path.
.globl _pitch_flush_start, _pitch_flush_end
_pitch_flush_start::
exx
ld (accum),hl
ld a,c
ld (accum+2),a
exx
_pitch_flush_end::
'''
    d=d[:start]+body+d[end:]
    d=replace_once(d,'_mul_s8::\n','; Preserves alternate AF/BC/DE/HL and IX/IY, including the neg32 tail.\n_mul_s8::\n')
    return d,f


def shared_pitch_history(d, f):
    """Dispatch once per subframe; long periods use adjacent history via IX."""
    shape_start=d.index('exc_shape:\n');sample_start=d.index('exc_sample:\n',shape_start)
    tail_start=d.index('; S=sum(gain8*history16)',sample_start)
    subframe_end=d.index('ld hl,#sub_count\ndec (hl)\njp nz,exc_subframe',tail_start)
    shape=d[shape_start+len('exc_shape:\n'):sample_start]
    tail=d[tail_start:subframe_end]
    init=d[d.index('_pitch_init_start::\n')+len('_pitch_init_start::\n'):d.index('_pitch_init_end::')]
    flush=d[d.index('_pitch_flush_start::\n')+len('_pitch_flush_start::\n'):d.index('_pitch_flush_end::')]
    additions=[d[d.index(f'_pitch_add_{tap}_start::\n')+len(f'_pitch_add_{tap}_start::\n'):
                 d.index(f'_pitch_add_{tap}_end::')] for tap in range(3)]
    # The common innovation/clamp arithmetic is copied exactly. Rename all its
    # internal labels and loop targets, keeping external routines/data shared.
    labels=re.findall(r'^(\w+)::?',tail,re.M)
    mapping={label:'pitch27_fast_'+label for label in labels}
    mapping.update(exc_sample='_pitch27_fast_sum_start',exc_shape='exc_shape_fast')
    tail=re.sub(r'\b('+'|'.join(map(re.escape,mapping))+r')\b',lambda m:mapping[m[0]],tail)
    tail=replace_once(tail,'ld hl,#sample_index\ninc (hl)\n','')
    fast='''; For pitch >=41 and j=0..39, j-(pitch+1-k) is always negative.
; The three history words are adjacent; no wrap/skip test is needed. IX
; advances one word per sample and survives getbits, signed8 multiply and clip.
; Duplicate the sample/shape loop to avoid a per-sample dispatch. Its clamp,
; innovation and output-history arithmetic remain identical to the general path.
exc_shape_fast:
'''+shape+'''.globl _pitch27_fast_sum_start, _pitch27_fast_sum_end
_pitch27_fast_sum_start::
'''+init
    for tap in range(3):
        fast+=f'ld e,{2*tap}(ix)\nld d,{2*tap+1}(ix)\nld a,(gain_current+{4-2*tap})\ncall _mul_s8\n'+additions[tap]
    fast+='inc ix\ninc ix\n'+flush+'_pitch27_fast_sum_end::\n'+tail
    # General subframes jump over the fast loop once; fast subframes fall through.
    d=d[:subframe_end]+'jp pitch27_subframe_done\n'+fast+'pitch27_subframe_done:\n'+d[subframe_end:]
    dispatch='''; Choose one complete 40-sample path per subframe. IX is scratch for
; packet decoding, as it already is during LSP reconstruction. No new RAM state.
.globl _pitch27_setup, _pitch27_general_ready, _pitch27_fast_ready
.globl _pitch27_period, _pitch27_exc_ptr, _pitch27_sample_index, _pitch27_gains
_pitch27_period = pitch
_pitch27_exc_ptr = exc_ptr
_pitch27_sample_index = sample_index
_pitch27_gains = gain_current
_pitch27_general_ready = exc_shape
_pitch27_fast_ready = exc_shape_fast
_pitch27_setup::
ld a,(pitch)
cp #41
jp c,exc_shape
; IX=e-2*(pitch+1). ADD HL,HL cannot carry for pitch<=144; subsequent
; EX/LD preserve that clear carry for SBC, so no extra carry-clear is needed.
ld l,a
ld h,#0
inc hl
add hl,hl
ex de,hl
ld hl,(exc_ptr)
sbc hl,de
push hl
pop ix
jp exc_shape_fast
'''
    d=d[:shape_start]+dispatch+d[shape_start:]
    return d,f


def constant_pitch_products(d, f, folder, strategy, return_ahl=False):
    """Replace the gain book with same-size target triples and constant routines."""
    import json
    from constant_pitch import gains,label,generate
    code,plan=generate(strategy,return_ahl)
    begin=d.index('pitch_gains:\n');end=d.index('energy_table:',begin)
    book=gains()
    table='''; Same 32x3 word book layout, now immutable code pointers. The existing
; gain_current scratch holds a selected pointer triple instead of gain values.
.globl _pitch_gain_targets
_pitch_gain_targets = pitch_gains
pitch_gains:
'''
    for row in range(32):table+='.dw '+','.join(label(g) for g in book[3*row:3*row+3])+f' ; Book {row}\n'
    d=d[:begin]+table+d[end:]
    for offset in (0,2,4):
        old=f'ld a,(gain_current+{offset})\ncall _mul_s8'
        assert d.count(old)==2
        d=d.replace(old,f'ld hl,(gain_current+{offset})\ncall _pitch_indirect')
    if return_ahl:
        # Both the general and copied long-period loops receive A:HL directly.
        # PUSH/EXX/POP preserve A; ADD supplies the carry consumed by ADC A,C.
        old='push de\nld a,l\nexx\npop de\nadd hl,de\nadc a,c\nld c,a\nexx\n'
        assert d.count(old)==6
        d=d.replace(old,'push hl\nexx\npop de\nadd hl,de\nadc a,c\nld c,a\nexx\n')
        d=d.replace('; Transfer the low product word through the real stack. EXX and POP',
                    '; A:HL is the exact signed24 product. Transfer HL through the real stack.\n; A survives PUSH/EXX/POP; EXX and POP')
        d=d.replace('; product and its neg32 tail preserve all alternate registers. No sum RAM',
                    '; constant product preserves all alternate registers. No sum RAM')
        d=d.replace('; Alternate HL/C hold the low16/high8 modulo24 pitch sum. The signed8',
                    '; Alternate HL/C hold the low16/high8 modulo24 pitch sum. Each')
        d=d.replace('survives getbits, signed8 multiply and clip.',
                    'survives getbits, constant multiplication and clip.')
    point=d.index('\n.area _TABLES (ABS)')
    d=d[:point]+'\n'+code+d[point:]
    (folder/'constant-pitch-plan.json').write_text(json.dumps(plan,indent=2)+'\n',newline='\n')
    return d,f


def synthesis_shift(d, f):
    """Replace signed24 >>5 with sign extension, three left shifts and byte selection."""
    f=replace_once(f,'filter_sample:\n','filter_sample:\n.globl _synthesis_round_start\n_synthesis_round_start::\n')
    f=replace_once(f,'    ; Signed 32-bit >>13: discard eight bits, then shift the remaining 24 five times.',
                   '    ; Signed 32-bit >>13: discard eight bits, then compute signed24 >>5.')
    old='    sra e\n    rr h\n    rr l\n'*5
    new='''; E:HL holds the signed24 upper bytes of the rounded 32-bit state.
; Sign-extend into A:E:HL, shift left three, and discard the low byte:
; (sign_extend(x)<<3)>>8 equals arithmetic x>>5 exactly, including negatives.
; ADD HL,HL / RL E / RLA carries across all four bytes. No 32-bit overflow
; is possible for signed24 x. Output E:HL; clobber AF, preserve D/BC,
; IX/IY, all alternates and SP. Later excitation sign extension overwrites
; flags before their next use, so the old shift's final carry is not needed.
.globl _synthesis_shift_start, _synthesis_shift_end
_synthesis_shift_start::
ld a,e
add a,a
sbc a,a
'''+('add hl,hl\nrl e\nrla\n'*3)+'''ld l,h
ld h,e
ld e,a
_synthesis_shift_end::
'''
    f=replace_once(f,old,new)
    return d,f


def split_word_product(d, f):
    """Replace the serial 32-bit accumulator with two byte/word partials."""
    from word_product import generate
    start=f.index('; Exact register-based signed16x16')
    stop=f.index('; Unsigned A*C',start)
    return d,f[:start]+generate()+f[stop:]


def shared_q14_coefficient(d, f, split_sign=False):
    """Prepare one coefficient magnitude for both exact Q14 partial products."""
    from q14_product import q14,q14_signed_tails,unsigned_product
    assert d.count('s8_sign')==1 and 's8_sign: .ds 1' in d
    start=d.index('; HL coefficient, DE pointer to signed32 argument;')
    end=d.index('; Exact integer cosine',start)
    d=d[:start]+(q14_signed_tails() if split_sign else q14())+d[end:]
    f=replace_once(f,'; Unsigned A*C',unsigned_product()+'; Unsigned A*C')
    return d,f


def cancel_preparation_exchanges(d, f):
    """Remove adjacent identity EXX pairs only within the changed-page builder."""
    start=d.index('coef_changed:\n');end=d.index('coef_next:\n',start)
    body=d[start:end];assert body.count('exx\nexx\n')==64
    body=body.replace('exx\nexx\n','')
    body=body.replace('coef_changed:\n','''coef_changed:
; Each recurrence ends in the upper register set, where the next PUSH reads
; its high word. Omit the old adjacent EXX/EXX identity before that PUSH.
; All 64 rows retain the same registers, flags, writes and final SP; save
; 64*8 = 512 nominal T per changed page. IRQ remains disabled as below.
''',1)
    return d[:start]+body+d[end:],f


def register_next_table_step(d, f):
    """Keep 16*step in spare BC/BC' and exploit page-aligned table groups."""
    start=d.index('coef_changed:\n');end=d.index('coef_next:\n',start)
    body=d[start:end]
    old='ld (coef_step),hl\nexx\nld (coef_step+2),hl\nexx\n'
    assert body.count(old)==3
    body=body.replace(old,''' ; BC/BC' are unused by the unrolled recurrence and PUSH writer.
; Retain the positive 16*step for the next group without RAM traffic.
ld b,h
ld c,l
exx
ld b,h
ld c,l
exx
'''.lstrip())
    old='ld de,(coef_step)\nexx\nld de,(coef_step+2)\nexx\n'
    assert body.count(old)==3
    body=body.replace(old,'ld d,b\nld e,c\nexx\nld d,b\nld e,c\nexx\n')
    for part in range(4):
        old=f'ld hl,(coef_out)\nld bc,#{64*(part+1)}\nadd hl,bc\nld sp,hl\n'
        new='''; coef_out is page-aligned (7200..7B00). Select the group end directly;
; group 3 ends at the next page. Later ADD/XOR initializes flags before use.
ld hl,(coef_out)
'''+(f'ld l,#{64*(part+1)}\n' if part<3 else 'inc h\n')+'ld sp,hl\n'
        new=f'.globl _coef35_group_{part}_start, _coef35_group_{part}_end\n_coef35_group_{part}_start::\n'+new+f'_coef35_group_{part}_end::\n'
        body=replace_once(body,old,new)
    body=body.replace("; DE/DE' hold the low/high step; HL/HL' hold the low/high accumulator.",
                      "; DE/DE' hold the low/high step; HL/HL' hold the accumulator.\n; BC/BC' retain the next positive step; all are documented scratch registers.")
    d=d[:start]+body+d[end:]
    assert d.count('coef_step')==1  # Only its retained, now-unused allocation.
    d=replace_once(d,'coef_step: .ds 4\n','''coef_step: .ds 4
.globl _coef35_unused_step, _coef35_page_cursor
_coef35_unused_step = coef_step
_coef35_page_cursor = coef_out
''')
    return d,f


def apply(folder, variant):
    d=(folder/'decoder.s').read_text();f=(folder/'filter.s').read_text()
    d,f=immediate_offsets(d,f)
    if variant!='pure-r7':d,f=faster_preparation(d,f)
    if variant not in ('pure-r7','pure-r8'):d,f=port_only(d,f)
    if variant=='pure-r10-approx':d,f=approximate_feedback(d,f)
    if variant in ('pure-r15','pure-r16','pure-r18-fixed','pure-r18','pure-r18-signed','pure-r19','pure-r20','pure-r22','pure-r23','pure-r23-pop','pure-r24','pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=register_preparation(d,f,variant in ('pure-r24','pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'))
    if variant in ('pure-r16','pure-r18-fixed','pure-r18','pure-r18-signed','pure-r19','pure-r20','pure-r22','pure-r23','pure-r23-pop','pure-r24','pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=skip_zero_product_bytes(d,f)
    if variant in ('pure-r18-fixed','pure-r18','pure-r18-signed','pure-r19','pure-r20','pure-r22','pure-r23','pure-r23-pop','pure-r24','pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):
        d,f=combined_signed8(d,f,variant!='pure-r18-fixed',variant in ('pure-r18-signed','pure-r19','pure-r20','pure-r22','pure-r23','pure-r23-pop','pure-r24','pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'))
    if variant in ('pure-r19','pure-r20','pure-r22','pure-r23','pure-r23-pop','pure-r24','pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=excitation_shift(d,f)
    if variant in ('pure-r20','pure-r22','pure-r23','pure-r23-pop','pure-r24','pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=innovation_registers(d,f)
    if variant in ('pure-r22','pure-r23','pure-r23-pop','pure-r24','pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=zero_feedback(d,f)
    if variant in ('pure-r23','pure-r23-pop','pure-r24','pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=inline_products(d,f,variant in ('pure-r23-pop','pure-r24','pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'))
    if variant in ('pure-r26','pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=pitch_accumulator(d,f)
    if variant in ('pure-r27','pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=shared_pitch_history(d,f)
    if variant in ('pure-r28-binary','pure-r28','pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=constant_pitch_products(d,f,folder,'binary' if variant=='pure-r28-binary' else 'chain',variant in ('pure-r29','pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'))
    if variant in ('pure-r30','pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=synthesis_shift(d,f)
    if variant in ('pure-r31','pure-r32','pure-r33','pure-r34','pure-r35'):d,f=split_word_product(d,f)
    if variant in ('pure-r32','pure-r33','pure-r34','pure-r35'):d,f=shared_q14_coefficient(d,f,variant in ('pure-r33','pure-r34','pure-r35'))
    if variant in ('pure-r34','pure-r35'):d,f=cancel_preparation_exchanges(d,f)
    if variant=='pure-r35':d,f=register_next_table_step(d,f)
    (folder/'decoder.s').write_text(d,newline='\n')
    (folder/'filter.s').write_text(f,newline='\n')
