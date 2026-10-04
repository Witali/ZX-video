"""Emit the complete mode-3 decoder in Z80 assembly; no target C runtime.

Uses exact pre-expanded Speex codebooks and a losslessly packed integer-cosine
table. All tables fit the fixed 16-KiB bank at 4000..7fff.
"""
from pathlib import Path
import re
from make_asm import generate

HERE=Path(__file__).resolve().parent

def array(name):
    t=(HERE/'tables.h').read_text()
    m=re.search(r'\b'+name+r'\[[^]]*\]\s*=\s*\{([^}]*)\}',t,re.S)
    return [int(x) for x in re.findall(r'-?\d+',m[1])]

def cos_int(x):
    def p(a,b):return (a*b+4096)>>13
    x2=p(x,x)
    return 8192+p(x2,-4096+p(x2,340+p(-10,x2)))

def emit(path,fast=False):
    code=[]
    def w(s):code.append(s)
    def add32(address):
        w(f'ld bc,({address})\nex de,hl\nadd hl,bc\nex de,hl\nld bc,({address}+2)\nadc hl,bc')
    def store32(address):w(f'ld ({address}),de\nld ({address}+2),hl')
    w('''.module speex_decode
.globl _entry, _complete, _packet_count, _status, _pcm
.globl _zx_lpc, _zx_memory, _zx_speex_lpc, _zx_speex_decode, _zx_clip
.globl _zx_speex_filter, _zx_mul_table
.globl excitation, interp, next_lpc, cosine, mulq14, enforce_margin, lsp
.area _DATA
_packet_count: .ds 2
_status: .ds 2
state_start:
excitation: .ds 688
old_lsp: .ds 20
lsp: .ds 20
interp: .ds 20
next_lpc: .ds 20
_zx_lpc: .ds 20
_zx_memory: .ds 40
frequency: .ds 20
polynomial_p: .ds 312
polynomial_q: .ds 312
_pcm: .ds 320
packet: .ds 21 ; includes a zero guard for the eager bit-reader refill
first: .ds 1
frames_left: .ds 2
input_ptr: .ds 2
bank_index: .ds 1
bitptr: .ds 2
bitbyte: .ds 1
bitcount: .ds 1
gain_index: .ds 1
gain_current: .ds 6
pitch: .ds 1
energy: .ds 4
exc_ptr: .ds 2
sample_index: .ds 1
shape_ptr: .ds 2
shape_count: .ds 1
sub_count: .ds 1
accum: .ds 4
qcoef: .ds 2
qarg: .ds 4
qtemp: .ds 4
cos_sign: .ds 1
cos_offset: .ds 1
sum_byte: .ds 1
old_p: .ds 4
old_q: .ds 4
state_end:
.area _CODE
_entry::
di
ld sp,#0xbffe
ld hl,(_packet_count)
push hl
ld hl,#state_start
ld de,#state_start+1
ld bc,#state_end-state_start-1
ld (hl),#0
ldir
pop hl
ld de,#4916
push hl
or a,a
sbc hl,de
pop hl
jr c,count_valid
ld hl,#2
ld (_status),hl
jp _complete
count_valid:
ld (frames_left),hl
ld hl,#0
ld (_status),hl
ld a,#1
ld (first),a
ld hl,#0xc000
ld (input_ptr),hl
xor a,a
ld (bank_index),a
call page
frame_loop:
ld hl,(frames_left)
ld a,h
or a,l
jp z,_complete
dec hl
ld (frames_left),hl
ld hl,(input_ptr)
ld de,#packet
ld b,#20
copy_packet:
ld a,(hl)
ld (de),a
inc hl
inc de
ld a,h
or a,l
jr nz,copy_ready
push bc
push de
ld a,(bank_index)
inc a
ld (bank_index),a
call page
pop de
pop bc
ld hl,#0xc000
copy_ready:
djnz copy_packet
ld (input_ptr),hl
call _zx_speex_decode
jp nc,frame_loop
ld hl,#1
ld (_status),hl
_complete::
halt
jr _complete
page:
ld e,a
ld d,#0
ld hl,#bank_order
add hl,de
ld a,(hl)
or a,#16
ld bc,#0x7ffd
out (c),a
ret
bank_order: .db 0,1,3,4,6,7

; B bits (1..7), result A; input is a validated 20-byte mode-3 packet.
getbits:
ld hl,(bitptr)
ld a,(bitbyte)
ld e,a
ld a,(bitcount)
ld c,a
ld d,#0
getbits_loop:
sla e
rl d
dec c
jr nz,getbits_have
ld e,(hl)
inc hl
ld c,#8
getbits_have:
djnz getbits_loop
ld (bitptr),hl
ld a,e
ld (bitbyte),a
ld a,c
ld (bitcount),a
ld a,d
ret

; Sign-symmetric saturation: long HL:DE -> signed DE in [-32767,32767].
_zx_clip::
ld a,h
or a,l
jr z,clip_positive
ld a,h
and a,l
inc a
jr nz,clip_wide
bit 7,d
jr z,clip_min
ld a,d
cp #0x80
ret nz
ld a,e
or a,a
ret nz
clip_min:
ld de,#0x8001
ret
clip_wide:
bit 7,h
jr nz,clip_min
clip_max:
ld de,#0x7fff
ret
clip_positive:
bit 7,d
ret z
jr clip_max

neg32:
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

; HL coefficient, DE pointer to signed32 argument; exact Speex MULT16_32_Q14.
mulq14:
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
call _zx_mul_table
ld (qtemp),de
ld (qtemp+2),hl
ld hl,(qarg)
ld a,h
and a,#63
ld h,a
ld de,(qcoef)
call _zx_mul_table
; Low partial product >>14 fits signed16 exactly.
add hl,hl
add hl,hl
ld a,d
rlca
rlca
and a,#3
or a,l
ld l,a
ex de,hl
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

; Exact integer cosine, normalized positive-half table, signed input 0..25736.
cosine:
ld de,#12868
or a,a
sbc hl,de
ld a,#0
jr c,cos_low
inc a
ld de,#12868
ex de,hl
or a,a
sbc hl,de
jr cos_folded
cos_low:
add hl,de
cos_folded:
ld (cos_sign),a
ld a,l
and a,#15
ld (cos_offset),a
srl h
rr l
srl h
rr l
srl h
rr l
srl h
rr l
; Ten bytes per block: anchor16 plus sixteen packed signed-nibble deltas.
ld d,h
ld e,l
add hl,hl
add hl,hl
add hl,de
add hl,hl
ld de,#cos_table
add hl,de
ld e,(hl)
inc hl
ld d,(hl)
inc hl
ld a,(cos_offset)
srl a
ld b,a
jr z,cos_odd
cos_pairs:
ld a,(hl)
inc hl
push hl
ld l,a
ld h,#0x60
ld a,(hl)
pop hl
push hl
ld l,a
add a,a
sbc a,a
ld h,a
add hl,de
ex de,hl
pop hl
djnz cos_pairs
cos_odd:
ld a,(cos_offset)
and a,#1
jr z,cos_sign_apply
ld a,(hl)
and a,#15
sub a,#8
push hl
ld l,a
add a,a
sbc a,a
ld h,a
add hl,de
ex de,hl
pop hl
cos_sign_apply:
ld a,(cos_sign)
or a,a
ret z
xor a,a
sub a,e
ld e,a
sbc a,a
sub a,d
ld d,a
ret

_zx_speex_decode::
ld hl,#packet
ld a,(hl)
inc hl
ld (bitptr),hl
ld (bitbyte),a
ld a,#8
ld (bitcount),a
ld b,#5
call getbits
cp #3
jr z,mode_ok
scf
ret
mode_ok:
ld hl,#excitation+320
ld de,#excitation
ld bc,#368
ldir
ld b,#6
call getbits
ld l,a
ld h,#0
ld d,h
ld e,l
add hl,hl
add hl,hl
add hl,de
add hl,hl
add hl,hl
ld de,#lsp_base
add hl,de
ld de,#lsp
ld bc,#20
ldir
''')
    for book,offset in [('lsp_low',0),('lsp_high',10)]:
        w(f'''ld b,#6
call getbits
ld l,a
ld h,#0
ld d,h
ld e,l
add hl,hl
add hl,hl
add hl,de
add hl,hl
ld de,#{book}
add hl,de
ld ix,#lsp+{offset}
ld b,#5
add_{book}:
ld e,(hl)
inc hl
ld d,(hl)
inc hl
push hl
ld l,0(ix)
ld h,1(ix)
add hl,de
ld 0(ix),l
ld 1(ix),h
inc ix
inc ix
pop hl
djnz add_{book}''')
    w('''ld a,(first)
or a,a
jr z,old_ready
ld hl,#lsp
ld de,#old_lsp
ld bc,#20
ldir
xor a,a
ld (first),a
old_ready:
ld b,#5
call getbits
ld (gain_index),a
ld hl,#excitation+368
ld (exc_ptr),hl
ld a,#4
ld (sub_count),a
exc_subframe:
ld b,#7
call getbits
add a,#17
ld (pitch),a
ld b,#5
call getbits
ld l,a
ld h,#0
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,hl
ld de,#pitch_gains
add hl,de
ld de,#gain_current
ld bc,#6
ldir
ld b,#1
call getbits
ld c,a
ld a,(gain_index)
add a,a
add a,c
ld l,a
ld h,#0
add hl,hl
add hl,hl
ld de,#energy_table
add hl,de
ld de,#energy
ld bc,#4
ldir
xor a,a
ld (sample_index),a
ld a,#4
ld (shape_count),a
exc_shape:
ld b,#5
call getbits
ld l,a
ld h,#0
ld d,h
ld e,l
add hl,hl
add hl,hl
add hl,de
add hl,hl
ld de,#innovation_book
add hl,de
ld (shape_ptr),hl
ld a,#10
ld (sum_byte),a
exc_sample:
ld hl,#0
ld (accum),hl
ld (accum+2),hl
''')
    for k in range(3):
        w(f'''ld a,(pitch)
add a,#{1-k}
ld e,a
ld a,(sample_index)
sub a,e
jr c,past_{k}
ld hl,#pitch
sub a,(hl)
jr nc,skip_pitch_{k}
past_{k}:
ld hl,#sample_index
sub a,(hl)
ld l,a
ld h,#255
add hl,hl
ld de,(exc_ptr)
add hl,de
ld e,(hl)
inc hl
ld d,(hl)
ld hl,(gain_current+{(2-k)*2})
call _zx_mul_table''')
        add32('accum');store32('accum');w(f'skip_pitch_{k}:')
    # Reference limits excitation before adding innovation. Compare signed upper16.
    w('''ld hl,(accum+2)
ld de,#4000
or a,a
sbc hl,de
jr z,check_positive_low
jp p,clamp_exc_positive
ld hl,(accum+2)
ld de,#-4000
or a,a
sbc hl,de
jp m,clamp_exc_negative
jr excitation_clamped
check_positive_low:
ld hl,(accum)
ld a,h
or a,l
jr z,excitation_clamped
clamp_exc_positive:
ld hl,#4000
ld (accum+2),hl
ld hl,#0
ld (accum),hl
jr excitation_clamped
clamp_exc_negative:
ld hl,#-4000
ld (accum+2),hl
ld hl,#0
ld (accum),hl
excitation_clamped:
ld hl,(shape_ptr)
ld a,(hl)
inc hl
ld (shape_ptr),hl
ld l,a
add a,a
sbc a,a
ld h,a
add hl,hl
add hl,hl
ld de,#energy
call mulq14
; innovation = q14(shape*4, energy) <<7, then add 2*adaptive and rounding.
''')
    w('sla e\nrl d\nrl l\nrl h\n'*7)
    add32('accum');add32('accum')
    w('''ld bc,#8192
ex de,hl
add hl,bc
ex de,hl
jr nc,exc_round_done
inc hl
exc_round_done:
; Signed 32-bit >>14, preserving overflow for saturation.
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
''')
    w('sra l\nrr d\nrr e\n'*6)
    w('''call _zx_clip
ld hl,(exc_ptr)
ld (hl),e
inc hl
ld (hl),d
inc hl
ld (exc_ptr),hl
ld hl,#sample_index
inc (hl)
ld hl,#sum_byte
dec (hl)
jp nz,exc_sample
ld hl,#shape_count
dec (hl)
jp nz,exc_shape
ld hl,#sub_count
dec (hl)
jp nz,exc_subframe
''')
    # Interpolation uses exact rounded sums, independent rounding of the two weights.
    for sub in range(4):
        for i in range(10):
            if sub==3:
                w(f'ld hl,(lsp+{i*2})\nld (interp+{i*2}),hl')
            else:
                # Weights are quarters. Use signed32 additions and >>2, matching P14.
                w('ld hl,#0\nld de,#0');store32('accum')
                for source,weight in [('old_lsp',3-sub),('lsp',sub+1)]:
                    w(f'ld de,({source}+{i*2})\nld a,d\nadd a,a\nsbc a,a\nld h,a\nld l,a')
                    if weight==2:w('sla e\nrl d\nrl l\nrl h')
                    if weight==3:
                        store32('qtemp');w('sla e\nrl d\nrl l\nrl h');add32('qtemp')
                    w('ld bc,#2\nex de,hl\nadd hl,bc\nex de,hl\njr nc,round_interp_'+str(sub)+'_'+str(i)+'_'+source+'\ninc hl\nround_interp_'+str(sub)+'_'+str(i)+'_'+source+':')
                    w('sra l\nrr d\nrr e\n'*2)
                    add32('accum');store32('accum')
                w(f'ld hl,(accum)\nld (interp+{i*2}),hl')
        w(f'''call enforce_margin
call _zx_speex_lpc
ld hl,#excitation+{288+80*sub}
ld de,#_pcm+{80*sub}
call _zx_speex_filter
ld hl,#next_lpc
ld de,#_zx_lpc
ld bc,#20
ldir''')
    w('''ld hl,#lsp
ld de,#old_lsp
ld bc,#20
ldir
or a,a
ret
enforce_margin:
ld hl,(interp)
ld de,#16
or a,a
sbc hl,de
jr nc,margin_first_ok
ld (interp),de
margin_first_ok:
ld hl,(interp+18)
ld de,#25720
or a,a
sbc hl,de
jr c,margin_last_ok
ld (interp+18),de
margin_last_ok:
''')
    for i in range(1,9):
        w(f'''ld hl,(interp+{2*i-2})
ld de,#16
add hl,de
ld de,(interp+{2*i})
or a,a
sbc hl,de
jr c,margin_low_{i}
add hl,de
ld (interp+{2*i}),hl
margin_low_{i}:
ld hl,(interp+{2*i+2})
ld de,#16
or a,a
sbc hl,de
ld de,(interp+{2*i})
or a,a
sbc hl,de
jr nc,margin_high_{i}
add hl,de
sra h
rr l
sra d
rr e
add hl,de
ld (interp+{2*i}),hl
margin_high_{i}:''')
    w('ret\n_zx_speex_lpc::')
    for i in range(10):w(f'ld hl,(interp+{2*i})\ncall cosine\nex de,hl\nadd hl,hl\nadd hl,hl\nld (frequency+{2*i}),hl')
    # Initialize every polynomial cell, including zero columns, on every call.
    w('ld hl,#polynomial_p\nld de,#polynomial_p+1\nld bc,#623\nld (hl),#0\nldir')
    for name in ('polynomial_p','polynomial_q'):
        for i in range(6):
            for j in sorted({2,2+2*i}):w(f'ld hl,#16\nld ({name}+{i*52+j*4+2}),hl')
    for name,k in [('polynomial_p',0),('polynomial_q',1)]:
        w(f'ld hl,(frequency+{2*k})\nld de,#{name}+8\ncall mulq14\ncall neg32');store32(f'{name}+64')
    for i in range(1,5):
        for j in range(1,2*(i+1)):
            for name,k in [('polynomial_p',0),('polynomial_q',1)]:
                w(f'ld hl,(frequency+{(2*i+k)*2})\nld de,#{name}+{i*52+(j+1)*4}\ncall mulq14\ncall neg32')
                if j<2*(i+1)-1:add32(f'{name}+{i*52+(j+2)*4}')
                add32(f'{name}+{i*52+j*4}');store32(f'{name}+{(i+1)*52+(j+2)*4}')
    w('ld hl,#0\nld (old_p),hl\nld (old_p+2),hl\nld (old_q),hl\nld (old_q+2),hl')
    for j in range(1,11):
        w('ld de,(old_q)\nld hl,(old_q+2)\ncall neg32');add32('old_p')
        add32(f'polynomial_p+{260+(j+2)*4}');add32(f'polynomial_q+{260+(j+2)*4}')
        w('ld bc,#128\nex de,hl\nadd hl,bc\nex de,hl\njr nc,lpc_round_'+str(j)+'\ninc hl\nlpc_round_'+str(j)+':')
        w('ld e,d\nld d,l\nld l,h\nld a,h\nadd a,a\nsbc a,a\nld h,a\ncall _zx_clip')
        w(f'ld (next_lpc+{2*j-2}),de')
        for name,dest in [('polynomial_p','old_p'),('polynomial_q','old_q')]:
            w(f'ld de,({name}+{260+(j+2)*4})\nld hl,({name}+{260+(j+2)*4+2})');store32(dest)

    w('ret\n.area _TABLES (ABS)\n.org 0x4000\ncos_table:')
    cos=[cos_int(i) for i in range(12869)];packed=[]
    for base in range(0,len(cos),16):
        packed.extend([cos[base]&255,(cos[base]>>8)&255])
        delta=[]
        for i in range(16):
            a=min(base+i,len(cos)-1);b=min(a+1,len(cos)-1)
            d=cos[b]-cos[a];assert -8<=d<=7,d
            delta.append(d+8)
        packed.extend(delta[i]|delta[i+1]<<4 for i in range(0,16,2))
    assert len(packed)==8050
    def db(data):
        for i in range(0,len(data),16):w('.db '+','.join(str(x&255) for x in data[i:i+16]))
    db(packed)
    w('.org 0x6000\ncos_sum:');db([(x&15)+(x>>4)-16 for x in range(256)])
    w('.org 0x6500\nlsp_base:')
    def words(data):db([v for x in data for v in (x&255,(x>>8)&255)])
    words([(i%10+1)*2048+32*x for i,x in enumerate(array('cdbk_nb'))])
    w('lsp_low:');words([16*x for x in array('cdbk_nb_low1')])
    w('lsp_high:');words([16*x for x in array('cdbk_nb_high1')])
    w('pitch_gains:');words([(array('gain_cdbk_lbr')[4*i+j]+32)*128 for i in range(32) for j in range(3)])
    w('energy_table:')
    def q(a,b,k):return a*(b>>k)+((a*(b&((1<<k)-1)))>>k)
    gains=[q(28406,x,15) for x in array('ol_gain_table')]
    energy=[q(a,g,14) for g in gains for a in (11546,17224)]
    db([v for x in energy for v in (x&255,(x>>8)&255,(x>>16)&255,(x>>24)&255)])
    w('innovation_book:');db(array('exc_10_32_table'))
    path.write_text('\n'.join(code)+'\n',encoding='utf-8',newline='\n')
    generate(path.with_name('filter.s'),table=True,fast=fast)
    f=path.with_name('filter.s').read_text().replace('#0x60','#0x61').replace('.org 0x6000','.org 0x6100')
    f=f.replace('.globl ___mulsint2slong, _zx_mul_table, _zx_mul8','.globl _zx_mul_table, _zx_mul8')
    f=f.replace('    pop iy\n    ld hl,#asm_count','    pop iy\n    ld a,(asm_y+1)\n    xor a,#128\n    out (0xfb),a\n    ld hl,#asm_count')
    path.with_name('filter.s').write_text(f,encoding='utf-8',newline='\n')
