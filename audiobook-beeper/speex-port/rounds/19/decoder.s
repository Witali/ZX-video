.module speex_decode
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
polynomial_p: .ds 24
polynomial_q: .ds 24
_pcm: .ds 0 ; compatibility symbol; no PCM buffer is allocated
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
s8_sign: .ds 1
innov_valid: .ds 1
innov_cached: .ds 1
innov_selected: .ds 2
energy_pair: .ds 2
table_out: .ds 2
table_value: .ds 3
table_step: .ds 2
table_frac: .ds 2
table_rem: .ds 2
table_count: .ds 1
coef_valid: .ds 1
coef_old: .ds 20
coef_ptr: .ds 2
coef_out: .ds 2
coef_step: .ds 4
coef_taps: .ds 1
coef_group: .ds 1
coef_count: .ds 1
coef_nibbles: .ds 4
coef_cache_ptr: .ds 2
coef_force: .ds 1
coef_saved_sp: .ds 2
state_end:
.area _CODE
; Entry: packet count at B000; resets state/stack, disables IRQ, clobbers all registers.
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

; Decode one validated 20-byte packet. Carry reports an unsupported mode.
; Excitation precedes four delayed 40-sample synthesis blocks. All scratch is private.
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
ld de,#lsp_low
add hl,de
ld ix,#lsp+0
ld b,#5
add_lsp_low:
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
djnz add_lsp_low
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
ld de,#lsp_high
add hl,de
ld ix,#lsp+10
ld b,#5
add_lsp_high:
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
djnz add_lsp_high
ld a,(first)
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
call prepare_innovation
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
add a,a
add a,#0x7c
ld h,a
ld l,#0
ld (innov_selected),hl
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

ld a,(pitch)
add a,#1
ld e,a
ld a,(sample_index)
sub a,e
jr c,past_0
ld hl,#pitch
sub a,(hl)
jr nc,skip_pitch_0
past_0:
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
ld a,(gain_current+4)
call _mul_s8
ld bc,(accum)
ex de,hl
add hl,bc
ex de,hl
ld a,(accum+2)
adc a,l
ld (accum),de
ld (accum+2),a
skip_pitch_0:
ld a,(pitch)
add a,#0
ld e,a
ld a,(sample_index)
sub a,e
jr c,past_1
ld hl,#pitch
sub a,(hl)
jr nc,skip_pitch_1
past_1:
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
ld a,(gain_current+2)
call _mul_s8
ld bc,(accum)
ex de,hl
add hl,bc
ex de,hl
ld a,(accum+2)
adc a,l
ld (accum),de
ld (accum+2),a
skip_pitch_1:
ld a,(pitch)
add a,#-1
ld e,a
ld a,(sample_index)
sub a,e
jr c,past_2
ld hl,#pitch
sub a,(hl)
jr nc,skip_pitch_2
past_2:
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
ld a,(gain_current+0)
call _mul_s8
ld bc,(accum)
ex de,hl
add hl,bc
ex de,hl
ld a,(accum+2)
adc a,l
ld (accum),de
ld (accum+2),a
skip_pitch_2:
; S=sum(gain8*history16), bounded to +/-2048000 before innovation.
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
ld hl,(shape_ptr)
ld a,(hl)
inc hl
ld (shape_ptr),hl
; Three-byte lookup replaces per-sample multiplication and fractional shifts.
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
ld l,(hl)
ld bc,(accum)
ex de,hl
add hl,bc
ex de,hl
ld a,(accum+2)
adc a,l
ld l,a
ld bc,(accum)
ex de,hl
add hl,bc
ex de,hl
ld a,(accum+2)
adc a,l
ld l,a
ld bc,#64
ex de,hl
add hl,bc
ex de,hl
jr nc,exc_round_done
inc l
exc_round_done:
; Signed24 L:D:E >> 7, producing sign-extended HL:DE for clipping.
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
call _zx_clip
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
; Exact quarter interpolation: original codebook LSPs are multiples of 16.
ld hl,(old_lsp+0)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
ld b,h
ld c,l
ld hl,(lsp+0)
srl h
rr l
srl h
rr l
add hl,bc
ld (interp+0),hl
ld hl,(old_lsp+2)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
ld b,h
ld c,l
ld hl,(lsp+2)
srl h
rr l
srl h
rr l
add hl,bc
ld (interp+2),hl
ld hl,(old_lsp+4)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
ld b,h
ld c,l
ld hl,(lsp+4)
srl h
rr l
srl h
rr l
add hl,bc
ld (interp+4),hl
ld hl,(old_lsp+6)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
ld b,h
ld c,l
ld hl,(lsp+6)
srl h
rr l
srl h
rr l
add hl,bc
ld (interp+6),hl
ld hl,(old_lsp+8)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
ld b,h
ld c,l
ld hl,(lsp+8)
srl h
rr l
srl h
rr l
add hl,bc
ld (interp+8),hl
ld hl,(old_lsp+10)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
ld b,h
ld c,l
ld hl,(lsp+10)
srl h
rr l
srl h
rr l
add hl,bc
ld (interp+10),hl
ld hl,(old_lsp+12)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
ld b,h
ld c,l
ld hl,(lsp+12)
srl h
rr l
srl h
rr l
add hl,bc
ld (interp+12),hl
ld hl,(old_lsp+14)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
ld b,h
ld c,l
ld hl,(lsp+14)
srl h
rr l
srl h
rr l
add hl,bc
ld (interp+14),hl
ld hl,(old_lsp+16)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
ld b,h
ld c,l
ld hl,(lsp+16)
srl h
rr l
srl h
rr l
add hl,bc
ld (interp+16),hl
ld hl,(old_lsp+18)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
ld b,h
ld c,l
ld hl,(lsp+18)
srl h
rr l
srl h
rr l
add hl,bc
ld (interp+18),hl
call enforce_margin
call _zx_speex_lpc
ld hl,#excitation+288
call _zx_speex_filter
ld hl,#next_lpc
ld de,#_zx_lpc
ld bc,#20
ldir
ld hl,(old_lsp+0)
srl h
rr l
srl h
rr l
add hl,hl
ld b,h
ld c,l
ld hl,(lsp+0)
srl h
rr l
srl h
rr l
add hl,hl
add hl,bc
ld (interp+0),hl
ld hl,(old_lsp+2)
srl h
rr l
srl h
rr l
add hl,hl
ld b,h
ld c,l
ld hl,(lsp+2)
srl h
rr l
srl h
rr l
add hl,hl
add hl,bc
ld (interp+2),hl
ld hl,(old_lsp+4)
srl h
rr l
srl h
rr l
add hl,hl
ld b,h
ld c,l
ld hl,(lsp+4)
srl h
rr l
srl h
rr l
add hl,hl
add hl,bc
ld (interp+4),hl
ld hl,(old_lsp+6)
srl h
rr l
srl h
rr l
add hl,hl
ld b,h
ld c,l
ld hl,(lsp+6)
srl h
rr l
srl h
rr l
add hl,hl
add hl,bc
ld (interp+6),hl
ld hl,(old_lsp+8)
srl h
rr l
srl h
rr l
add hl,hl
ld b,h
ld c,l
ld hl,(lsp+8)
srl h
rr l
srl h
rr l
add hl,hl
add hl,bc
ld (interp+8),hl
ld hl,(old_lsp+10)
srl h
rr l
srl h
rr l
add hl,hl
ld b,h
ld c,l
ld hl,(lsp+10)
srl h
rr l
srl h
rr l
add hl,hl
add hl,bc
ld (interp+10),hl
ld hl,(old_lsp+12)
srl h
rr l
srl h
rr l
add hl,hl
ld b,h
ld c,l
ld hl,(lsp+12)
srl h
rr l
srl h
rr l
add hl,hl
add hl,bc
ld (interp+12),hl
ld hl,(old_lsp+14)
srl h
rr l
srl h
rr l
add hl,hl
ld b,h
ld c,l
ld hl,(lsp+14)
srl h
rr l
srl h
rr l
add hl,hl
add hl,bc
ld (interp+14),hl
ld hl,(old_lsp+16)
srl h
rr l
srl h
rr l
add hl,hl
ld b,h
ld c,l
ld hl,(lsp+16)
srl h
rr l
srl h
rr l
add hl,hl
add hl,bc
ld (interp+16),hl
ld hl,(old_lsp+18)
srl h
rr l
srl h
rr l
add hl,hl
ld b,h
ld c,l
ld hl,(lsp+18)
srl h
rr l
srl h
rr l
add hl,hl
add hl,bc
ld (interp+18),hl
call enforce_margin
call _zx_speex_lpc
ld hl,#excitation+368
call _zx_speex_filter
ld hl,#next_lpc
ld de,#_zx_lpc
ld bc,#20
ldir
ld hl,(old_lsp+0)
srl h
rr l
srl h
rr l
ld b,h
ld c,l
ld hl,(lsp+0)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,bc
ld (interp+0),hl
ld hl,(old_lsp+2)
srl h
rr l
srl h
rr l
ld b,h
ld c,l
ld hl,(lsp+2)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,bc
ld (interp+2),hl
ld hl,(old_lsp+4)
srl h
rr l
srl h
rr l
ld b,h
ld c,l
ld hl,(lsp+4)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,bc
ld (interp+4),hl
ld hl,(old_lsp+6)
srl h
rr l
srl h
rr l
ld b,h
ld c,l
ld hl,(lsp+6)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,bc
ld (interp+6),hl
ld hl,(old_lsp+8)
srl h
rr l
srl h
rr l
ld b,h
ld c,l
ld hl,(lsp+8)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,bc
ld (interp+8),hl
ld hl,(old_lsp+10)
srl h
rr l
srl h
rr l
ld b,h
ld c,l
ld hl,(lsp+10)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,bc
ld (interp+10),hl
ld hl,(old_lsp+12)
srl h
rr l
srl h
rr l
ld b,h
ld c,l
ld hl,(lsp+12)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,bc
ld (interp+12),hl
ld hl,(old_lsp+14)
srl h
rr l
srl h
rr l
ld b,h
ld c,l
ld hl,(lsp+14)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,bc
ld (interp+14),hl
ld hl,(old_lsp+16)
srl h
rr l
srl h
rr l
ld b,h
ld c,l
ld hl,(lsp+16)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,bc
ld (interp+16),hl
ld hl,(old_lsp+18)
srl h
rr l
srl h
rr l
ld b,h
ld c,l
ld hl,(lsp+18)
srl h
rr l
srl h
rr l
ld d,h
ld e,l
add hl,hl
add hl,de
add hl,bc
ld (interp+18),hl
call enforce_margin
call _zx_speex_lpc
ld hl,#excitation+448
call _zx_speex_filter
ld hl,#next_lpc
ld de,#_zx_lpc
ld bc,#20
ldir
ld hl,(lsp+0)
ld (interp+0),hl
ld hl,(lsp+2)
ld (interp+2),hl
ld hl,(lsp+4)
ld (interp+4),hl
ld hl,(lsp+6)
ld (interp+6),hl
ld hl,(lsp+8)
ld (interp+8),hl
ld hl,(lsp+10)
ld (interp+10),hl
ld hl,(lsp+12)
ld (interp+12),hl
ld hl,(lsp+14)
ld (interp+14),hl
ld hl,(lsp+16)
ld (interp+16),hl
ld hl,(lsp+18)
ld (interp+18),hl
call enforce_margin
call _zx_speex_lpc
ld hl,#excitation+528
call _zx_speex_filter
ld hl,#next_lpc
ld de,#_zx_lpc
ld bc,#20
ldir
ld hl,#lsp
ld de,#old_lsp
ld bc,#20
ldir
or a,a
ret
; Enforce ordered LSP spacing exactly as upstream before the cosine conversion.
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

ld hl,(interp+0)
ld de,#16
add hl,de
ld de,(interp+2)
or a,a
sbc hl,de
jr c,margin_low_1
add hl,de
ld (interp+2),hl
margin_low_1:
ld hl,(interp+4)
ld de,#16
or a,a
sbc hl,de
ld de,(interp+2)
or a,a
sbc hl,de
jr nc,margin_high_1
add hl,de
sra h
rr l
sra d
rr e
add hl,de
ld (interp+2),hl
margin_high_1:
ld hl,(interp+2)
ld de,#16
add hl,de
ld de,(interp+4)
or a,a
sbc hl,de
jr c,margin_low_2
add hl,de
ld (interp+4),hl
margin_low_2:
ld hl,(interp+6)
ld de,#16
or a,a
sbc hl,de
ld de,(interp+4)
or a,a
sbc hl,de
jr nc,margin_high_2
add hl,de
sra h
rr l
sra d
rr e
add hl,de
ld (interp+4),hl
margin_high_2:
ld hl,(interp+4)
ld de,#16
add hl,de
ld de,(interp+6)
or a,a
sbc hl,de
jr c,margin_low_3
add hl,de
ld (interp+6),hl
margin_low_3:
ld hl,(interp+8)
ld de,#16
or a,a
sbc hl,de
ld de,(interp+6)
or a,a
sbc hl,de
jr nc,margin_high_3
add hl,de
sra h
rr l
sra d
rr e
add hl,de
ld (interp+6),hl
margin_high_3:
ld hl,(interp+6)
ld de,#16
add hl,de
ld de,(interp+8)
or a,a
sbc hl,de
jr c,margin_low_4
add hl,de
ld (interp+8),hl
margin_low_4:
ld hl,(interp+10)
ld de,#16
or a,a
sbc hl,de
ld de,(interp+8)
or a,a
sbc hl,de
jr nc,margin_high_4
add hl,de
sra h
rr l
sra d
rr e
add hl,de
ld (interp+8),hl
margin_high_4:
ld hl,(interp+8)
ld de,#16
add hl,de
ld de,(interp+10)
or a,a
sbc hl,de
jr c,margin_low_5
add hl,de
ld (interp+10),hl
margin_low_5:
ld hl,(interp+12)
ld de,#16
or a,a
sbc hl,de
ld de,(interp+10)
or a,a
sbc hl,de
jr nc,margin_high_5
add hl,de
sra h
rr l
sra d
rr e
add hl,de
ld (interp+10),hl
margin_high_5:
ld hl,(interp+10)
ld de,#16
add hl,de
ld de,(interp+12)
or a,a
sbc hl,de
jr c,margin_low_6
add hl,de
ld (interp+12),hl
margin_low_6:
ld hl,(interp+14)
ld de,#16
or a,a
sbc hl,de
ld de,(interp+12)
or a,a
sbc hl,de
jr nc,margin_high_6
add hl,de
sra h
rr l
sra d
rr e
add hl,de
ld (interp+12),hl
margin_high_6:
ld hl,(interp+12)
ld de,#16
add hl,de
ld de,(interp+14)
or a,a
sbc hl,de
jr c,margin_low_7
add hl,de
ld (interp+14),hl
margin_low_7:
ld hl,(interp+16)
ld de,#16
or a,a
sbc hl,de
ld de,(interp+14)
or a,a
sbc hl,de
jr nc,margin_high_7
add hl,de
sra h
rr l
sra d
rr e
add hl,de
ld (interp+14),hl
margin_high_7:
ld hl,(interp+14)
ld de,#16
add hl,de
ld de,(interp+16)
or a,a
sbc hl,de
jr c,margin_low_8
add hl,de
ld (interp+16),hl
margin_low_8:
ld hl,(interp+18)
ld de,#16
or a,a
sbc hl,de
ld de,(interp+16)
or a,a
sbc hl,de
jr nc,margin_high_8
add hl,de
sra h
rr l
sra d
rr e
add hl,de
ld (interp+16),hl
margin_high_8:
ret
; Interpolated LSP angles -> next_lpc, preserving upstream fixed-point rounding.
; P/Q polynomial arithmetic wraps at 32 bits; final coefficients saturate symmetrically.
_zx_speex_lpc::
; Each polynomial is palindromic. Keep coefficients 0..degree/2 only;
; update descending so all previous-stage operands remain available.
; Each Q14 product keeps the original signed16 high-part truncation.
ld hl,(interp+0)
call cosine
ex de,hl
add hl,hl
add hl,hl
ld (frequency+0),hl
ld hl,(interp+2)
call cosine
ex de,hl
add hl,hl
add hl,hl
ld (frequency+2),hl
ld hl,(interp+4)
call cosine
ex de,hl
add hl,hl
add hl,hl
ld (frequency+4),hl
ld hl,(interp+6)
call cosine
ex de,hl
add hl,hl
add hl,hl
ld (frequency+6),hl
ld hl,(interp+8)
call cosine
ex de,hl
add hl,hl
add hl,hl
ld (frequency+8),hl
ld hl,(interp+10)
call cosine
ex de,hl
add hl,hl
add hl,hl
ld (frequency+10),hl
ld hl,(interp+12)
call cosine
ex de,hl
add hl,hl
add hl,hl
ld (frequency+12),hl
ld hl,(interp+14)
call cosine
ex de,hl
add hl,hl
add hl,hl
ld (frequency+14),hl
ld hl,(interp+16)
call cosine
ex de,hl
add hl,hl
add hl,hl
ld (frequency+16),hl
ld hl,(interp+18)
call cosine
ex de,hl
add hl,hl
add hl,hl
ld (frequency+18),hl
ld hl,#0
ld (polynomial_p),hl
ld hl,#16
ld (polynomial_p+2),hl
ld de,(frequency+0)
call negative_frequency64
ld (polynomial_p+4),de
ld (polynomial_p+4+2),hl
ld hl,#0
ld (polynomial_q),hl
ld hl,#16
ld (polynomial_q+2),hl
ld de,(frequency+2)
call negative_frequency64
ld (polynomial_q+4),de
ld (polynomial_q+4+2),hl
ld hl,(frequency+4)
ld de,#polynomial_p+4
call mulq14
call neg32
ld bc,(polynomial_p+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+0+2)
adc hl,bc
ld bc,(polynomial_p+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+0+2)
adc hl,bc
ld (polynomial_p+8),de
ld (polynomial_p+8+2),hl
ld hl,(frequency+6)
ld de,#polynomial_q+4
call mulq14
call neg32
ld bc,(polynomial_q+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+0+2)
adc hl,bc
ld bc,(polynomial_q+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+0+2)
adc hl,bc
ld (polynomial_q+8),de
ld (polynomial_q+8+2),hl
ld de,(frequency+4)
call negative_frequency64
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld (polynomial_p+4),de
ld (polynomial_p+4+2),hl
ld de,(frequency+6)
call negative_frequency64
ld bc,(polynomial_q+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+4+2)
adc hl,bc
ld (polynomial_q+4),de
ld (polynomial_q+4+2),hl
ld hl,(frequency+8)
ld de,#polynomial_p+8
call mulq14
call neg32
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld (polynomial_p+12),de
ld (polynomial_p+12+2),hl
ld hl,(frequency+10)
ld de,#polynomial_q+8
call mulq14
call neg32
ld bc,(polynomial_q+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+4+2)
adc hl,bc
ld bc,(polynomial_q+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+4+2)
adc hl,bc
ld (polynomial_q+12),de
ld (polynomial_q+12+2),hl
ld hl,(frequency+8)
ld de,#polynomial_p+4
call mulq14
call neg32
ld bc,(polynomial_p+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+8+2)
adc hl,bc
ld bc,(polynomial_p+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+0+2)
adc hl,bc
ld (polynomial_p+8),de
ld (polynomial_p+8+2),hl
ld hl,(frequency+10)
ld de,#polynomial_q+4
call mulq14
call neg32
ld bc,(polynomial_q+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+8+2)
adc hl,bc
ld bc,(polynomial_q+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+0+2)
adc hl,bc
ld (polynomial_q+8),de
ld (polynomial_q+8+2),hl
ld de,(frequency+8)
call negative_frequency64
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld (polynomial_p+4),de
ld (polynomial_p+4+2),hl
ld de,(frequency+10)
call negative_frequency64
ld bc,(polynomial_q+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+4+2)
adc hl,bc
ld (polynomial_q+4),de
ld (polynomial_q+4+2),hl
ld hl,(frequency+12)
ld de,#polynomial_p+12
call mulq14
call neg32
ld bc,(polynomial_p+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+8+2)
adc hl,bc
ld bc,(polynomial_p+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+8+2)
adc hl,bc
ld (polynomial_p+16),de
ld (polynomial_p+16+2),hl
ld hl,(frequency+14)
ld de,#polynomial_q+12
call mulq14
call neg32
ld bc,(polynomial_q+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+8+2)
adc hl,bc
ld bc,(polynomial_q+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+8+2)
adc hl,bc
ld (polynomial_q+16),de
ld (polynomial_q+16+2),hl
ld hl,(frequency+12)
ld de,#polynomial_p+8
call mulq14
call neg32
ld bc,(polynomial_p+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+12+2)
adc hl,bc
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld (polynomial_p+12),de
ld (polynomial_p+12+2),hl
ld hl,(frequency+14)
ld de,#polynomial_q+8
call mulq14
call neg32
ld bc,(polynomial_q+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+12+2)
adc hl,bc
ld bc,(polynomial_q+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+4+2)
adc hl,bc
ld (polynomial_q+12),de
ld (polynomial_q+12+2),hl
ld hl,(frequency+12)
ld de,#polynomial_p+4
call mulq14
call neg32
ld bc,(polynomial_p+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+8+2)
adc hl,bc
ld bc,(polynomial_p+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+0+2)
adc hl,bc
ld (polynomial_p+8),de
ld (polynomial_p+8+2),hl
ld hl,(frequency+14)
ld de,#polynomial_q+4
call mulq14
call neg32
ld bc,(polynomial_q+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+8+2)
adc hl,bc
ld bc,(polynomial_q+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+0+2)
adc hl,bc
ld (polynomial_q+8),de
ld (polynomial_q+8+2),hl
ld de,(frequency+12)
call negative_frequency64
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld (polynomial_p+4),de
ld (polynomial_p+4+2),hl
ld de,(frequency+14)
call negative_frequency64
ld bc,(polynomial_q+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+4+2)
adc hl,bc
ld (polynomial_q+4),de
ld (polynomial_q+4+2),hl
ld hl,(frequency+16)
ld de,#polynomial_p+16
call mulq14
call neg32
ld bc,(polynomial_p+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+12+2)
adc hl,bc
ld bc,(polynomial_p+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+12+2)
adc hl,bc
ld (polynomial_p+20),de
ld (polynomial_p+20+2),hl
ld hl,(frequency+18)
ld de,#polynomial_q+16
call mulq14
call neg32
ld bc,(polynomial_q+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+12+2)
adc hl,bc
ld bc,(polynomial_q+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+12+2)
adc hl,bc
ld (polynomial_q+20),de
ld (polynomial_q+20+2),hl
ld hl,(frequency+16)
ld de,#polynomial_p+12
call mulq14
call neg32
ld bc,(polynomial_p+16)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+16+2)
adc hl,bc
ld bc,(polynomial_p+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+8+2)
adc hl,bc
ld (polynomial_p+16),de
ld (polynomial_p+16+2),hl
ld hl,(frequency+18)
ld de,#polynomial_q+12
call mulq14
call neg32
ld bc,(polynomial_q+16)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+16+2)
adc hl,bc
ld bc,(polynomial_q+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+8+2)
adc hl,bc
ld (polynomial_q+16),de
ld (polynomial_q+16+2),hl
ld hl,(frequency+16)
ld de,#polynomial_p+8
call mulq14
call neg32
ld bc,(polynomial_p+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+12+2)
adc hl,bc
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld (polynomial_p+12),de
ld (polynomial_p+12+2),hl
ld hl,(frequency+18)
ld de,#polynomial_q+8
call mulq14
call neg32
ld bc,(polynomial_q+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+12+2)
adc hl,bc
ld bc,(polynomial_q+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+4+2)
adc hl,bc
ld (polynomial_q+12),de
ld (polynomial_q+12+2),hl
ld hl,(frequency+16)
ld de,#polynomial_p+4
call mulq14
call neg32
ld bc,(polynomial_p+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+8+2)
adc hl,bc
ld bc,(polynomial_p+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+0+2)
adc hl,bc
ld (polynomial_p+8),de
ld (polynomial_p+8+2),hl
ld hl,(frequency+18)
ld de,#polynomial_q+4
call mulq14
call neg32
ld bc,(polynomial_q+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+8+2)
adc hl,bc
ld bc,(polynomial_q+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+0+2)
adc hl,bc
ld (polynomial_q+8),de
ld (polynomial_q+8+2),hl
ld de,(frequency+16)
call negative_frequency64
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld (polynomial_p+4),de
ld (polynomial_p+4+2),hl
ld de,(frequency+18)
call negative_frequency64
ld bc,(polynomial_q+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+4+2)
adc hl,bc
ld (polynomial_q+4),de
ld (polynomial_q+4+2),hl
ld de,(polynomial_q+0)
ld hl,(polynomial_q+2)
call neg32
ld bc,(polynomial_p+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+0+2)
adc hl,bc
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld bc,(polynomial_q+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+4+2)
adc hl,bc
ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_1
inc hl
compact_round_1:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+0),de
ld de,(polynomial_q+4)
ld hl,(polynomial_q+6)
call neg32
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld bc,(polynomial_p+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+8+2)
adc hl,bc
ld bc,(polynomial_q+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+8+2)
adc hl,bc
ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_2
inc hl
compact_round_2:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+2),de
ld de,(polynomial_q+8)
ld hl,(polynomial_q+10)
call neg32
ld bc,(polynomial_p+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+8+2)
adc hl,bc
ld bc,(polynomial_p+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+12+2)
adc hl,bc
ld bc,(polynomial_q+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+12+2)
adc hl,bc
ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_3
inc hl
compact_round_3:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+4),de
ld de,(polynomial_q+12)
ld hl,(polynomial_q+14)
call neg32
ld bc,(polynomial_p+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+12+2)
adc hl,bc
ld bc,(polynomial_p+16)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+16+2)
adc hl,bc
ld bc,(polynomial_q+16)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+16+2)
adc hl,bc
ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_4
inc hl
compact_round_4:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+6),de
ld de,(polynomial_q+16)
ld hl,(polynomial_q+18)
call neg32
ld bc,(polynomial_p+16)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+16+2)
adc hl,bc
ld bc,(polynomial_p+20)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+20+2)
adc hl,bc
ld bc,(polynomial_q+20)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+20+2)
adc hl,bc
ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_5
inc hl
compact_round_5:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+8),de
ld de,(polynomial_q+20)
ld hl,(polynomial_q+22)
call neg32
ld bc,(polynomial_p+20)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+20+2)
adc hl,bc
ld bc,(polynomial_p+16)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+16+2)
adc hl,bc
ld bc,(polynomial_q+16)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+16+2)
adc hl,bc
ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_6
inc hl
compact_round_6:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+10),de
ld de,(polynomial_q+16)
ld hl,(polynomial_q+18)
call neg32
ld bc,(polynomial_p+16)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+16+2)
adc hl,bc
ld bc,(polynomial_p+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+12+2)
adc hl,bc
ld bc,(polynomial_q+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+12+2)
adc hl,bc
ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_7
inc hl
compact_round_7:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+12),de
ld de,(polynomial_q+12)
ld hl,(polynomial_q+14)
call neg32
ld bc,(polynomial_p+12)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+12+2)
adc hl,bc
ld bc,(polynomial_p+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+8+2)
adc hl,bc
ld bc,(polynomial_q+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+8+2)
adc hl,bc
ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_8
inc hl
compact_round_8:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+14),de
ld de,(polynomial_q+8)
ld hl,(polynomial_q+10)
call neg32
ld bc,(polynomial_p+8)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+8+2)
adc hl,bc
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld bc,(polynomial_q+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+4+2)
adc hl,bc
ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_9
inc hl
compact_round_9:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+16),de
ld de,(polynomial_q+4)
ld hl,(polynomial_q+6)
call neg32
ld bc,(polynomial_p+4)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+4+2)
adc hl,bc
ld bc,(polynomial_p+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_p+0+2)
adc hl,bc
ld bc,(polynomial_q+0)
ex de,hl
add hl,bc
ex de,hl
ld bc,(polynomial_q+0+2)
adc hl,bc
ld bc,#128
ex de,hl
add hl,bc
ex de,hl
jr nc,compact_round_10
inc hl
compact_round_10:
ld e,d
ld d,l
ld l,h
ld a,h
add a,a
sbc a,a
ld h,a
call _zx_clip
ld (next_lpc+18),de
ret
; DE signed frequency -> HL:DE = -frequency*64. The constant polynomial
; endpoint is 2^20, so its Q14 product is an exact shift, not a general multiply.
negative_frequency64:
ld a,d
add a,a
sbc a,a
ld h,a
ld l,a
sla e
rl d
rl l
sla e
rl d
rl l
sla e
rl d
rl l
sla e
rl d
rl l
sla e
rl d
rl l
sla e
rl d
rl l
jp neg32

.globl _mul_s8, mulq12
; Signed A * DE -> HL:DE. Magnitudes use an unsigned 24-bit A:HL accumulator.
_mul_s8::
or a,a
jr nz,s8_nonzero
ld hl,#0
ld de,#0
ret
s8_nonzero:
; C preserves the original signed byte; B is its unsigned magnitude.
; The multiplicand DE stays signed, avoiding a word negation and sign RAM.
ld c,a
ld b,a
bit 7,b
jr z,s8_a_positive
neg
ld b,a
s8_a_positive:
s8_b_positive:
; Unsigned core: A starts with the 8 multiplier bits and ends
; as the product high byte; HL holds the low word. ADD HL,HL carries into
; RLA, whose outgoing carry selects this bit's addition. ADC A,0 merges
; the low-word carry. DE is treated as unsigned; no extra table or scratch.
ld a,b
; Nonzero B is guaranteed by the entry check. Skip the zero prefix.
add a,a
jr c,s8_leading_0
add a,a
jr c,s8_leading_1
add a,a
jr c,s8_leading_2
add a,a
jr c,s8_leading_3
add a,a
jr c,s8_leading_4
add a,a
jr c,s8_leading_5
add a,a
jr c,s8_leading_6
add a,a
jr c,s8_leading_7
s8_leading_0:
ld h,d
ld l,e
jp s8_acc_1
s8_leading_1:
ld h,d
ld l,e
jp s8_acc_2
s8_leading_2:
ld h,d
ld l,e
jp s8_acc_3
s8_leading_3:
ld h,d
ld l,e
jp s8_acc_4
s8_leading_4:
ld h,d
ld l,e
jp s8_acc_5
s8_leading_5:
ld h,d
ld l,e
jp s8_acc_6
s8_leading_6:
ld h,d
ld l,e
jp s8_acc_7
s8_leading_7:
ld h,d
ld l,e
jp s8_acc_done
s8_acc_1:
add hl,hl
rla
jr nc,s8_acc_skip_1
add hl,de
adc a,#0
s8_acc_skip_1:
s8_acc_2:
add hl,hl
rla
jr nc,s8_acc_skip_2
add hl,de
adc a,#0
s8_acc_skip_2:
s8_acc_3:
add hl,hl
rla
jr nc,s8_acc_skip_3
add hl,de
adc a,#0
s8_acc_skip_3:
s8_acc_4:
add hl,hl
rla
jr nc,s8_acc_skip_4
add hl,de
adc a,#0
s8_acc_skip_4:
s8_acc_5:
add hl,hl
rla
jr nc,s8_acc_skip_5
add hl,de
adc a,#0
s8_acc_skip_5:
s8_acc_6:
add hl,hl
rla
jr nc,s8_acc_skip_6
add hl,de
adc a,#0
s8_acc_skip_6:
s8_acc_7:
add hl,hl
rla
jr nc,s8_acc_skip_7
add hl,de
adc a,#0
s8_acc_skip_7:
s8_acc_done:
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
sra d
rr e
sra d
rr e
sra d
rr e
sra d
rr e

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
add hl,hl
add hl,hl
add hl,hl
add hl,hl
add hl,hl
add hl,hl
add hl,de
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
ld a,(coef_valid)
ld (coef_force),a
ld a,#1
ld (coef_valid),a
ld hl,#coef_old
ld (coef_cache_ptr),hl
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
; Partial table 0: rows are stored from index 15 down to 0.
ld hl,(coef_out)
ld bc,#64
add hl,bc
ld sp,hl
ld h,d
ld l,e
exx
ld h,d
ld l,e
exx
add hl,hl
exx
adc hl,hl
exx
add hl,hl
exx
adc hl,hl
exx
add hl,hl
exx
adc hl,hl
exx
add hl,hl
exx
adc hl,hl
exx
; Save 16*step for the next group before forming 15*step.
ld (coef_step),hl
exx
ld (coef_step+2),hl
exx
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
ld de,(coef_step)
exx
ld de,(coef_step+2)
exx
; Partial table 1: rows are stored from index 15 down to 0.
ld hl,(coef_out)
ld bc,#128
add hl,bc
ld sp,hl
ld h,d
ld l,e
exx
ld h,d
ld l,e
exx
add hl,hl
exx
adc hl,hl
exx
add hl,hl
exx
adc hl,hl
exx
add hl,hl
exx
adc hl,hl
exx
add hl,hl
exx
adc hl,hl
exx
; Save 16*step for the next group before forming 15*step.
ld (coef_step),hl
exx
ld (coef_step+2),hl
exx
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
ld de,(coef_step)
exx
ld de,(coef_step+2)
exx
; Partial table 2: rows are stored from index 15 down to 0.
ld hl,(coef_out)
ld bc,#192
add hl,bc
ld sp,hl
ld h,d
ld l,e
exx
ld h,d
ld l,e
exx
add hl,hl
exx
adc hl,hl
exx
add hl,hl
exx
adc hl,hl
exx
add hl,hl
exx
adc hl,hl
exx
add hl,hl
exx
adc hl,hl
exx
; Save 16*step for the next group before forming 15*step.
ld (coef_step),hl
exx
ld (coef_step+2),hl
exx
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
ld de,(coef_step)
exx
ld de,(coef_step+2)
exx
; Partial table 3: rows are stored from index 15 down to 0.
ld hl,(coef_out)
ld bc,#256
add hl,bc
ld sp,hl
; Signed high nibble: first row is -step, followed by -2..-8.
ld hl,#0
exx
ld hl,#0
exx
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
; Convert -8*step to +8*step; next subtraction yields row 7.
; Its low byte L is zero (coefficient shifted left 15 bits).
xor a,a
sub a,h
ld h,a
exx
ld a,#0
sbc a,l
ld l,a
ld a,#0
sbc a,h
ld h,a
exx
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
or a,a
sbc hl,de
exx
sbc hl,de
exx
exx
push hl
exx
push hl
; Restore the caller's stack before returning or examining the next page.
ld sp,(coef_saved_sp)
ld hl,(coef_out)
inc h
ld (coef_out),hl
coef_next:
ld a,(coef_taps)
dec a
ld (coef_taps),a
jp nz,coef_tap
ret

; HL signed multiplier: patch four LD L,n operands once for all ten taps.
; Code must reside in writable RAM. Clobbers AF; no opcode is modified.
_split_nibbles::
ld a,l
and a,#15
add a,a
add a,a
ld (_smc0),a
ld a,l
and a,#240
rrca
rrca
or a,#64
ld (_smc1),a
ld a,h
and a,#15
add a,a
add a,a
or a,#129
ld (_smc2),a
ld a,h
and a,#240
rrca
rrca
or a,#193
ld (_smc3),a
ret
; A=coefficient page; four cached offsets -> exact signed32 HL:DE.
; Byte additions propagate carry in order, preserving the reference wrap semantics.
_coefficient_product::
ld h,a
product_offset_0:
ld l,#0
ld e,(hl)
inc l
ld d,(hl)
inc l
ld c,(hl)
inc l
ld b,(hl)
product_offset_1:
ld l,#0
ld a,e
add a,(hl)
ld e,a
inc l
ld a,d
adc a,(hl)
ld d,a
inc l
ld a,c
adc a,(hl)
ld c,a
inc l
ld a,b
adc a,(hl)
ld b,a
; Shifted partial has low byte zero. Offset starts at byte 1;
; E remains unchanged and ADD starts a new carry chain at D.
product_offset_2:
ld l,#0
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
; Shifted partial has low byte zero. Offset starts at byte 1;
; E remains unchanged and ADD starts a new carry chain at D.
product_offset_3:
ld l,#0
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
ld h,b
ld l,c
ret

.area _TABLES (ABS)
.org 0x4000
cos_table:
.db 0,32,136,136,136,136,136,136,136,136,0,32,136,136,136,136
.db 136,136,136,136,0,32,136,136,136,136,136,136,136,136,0,32
.db 136,136,136,136,136,136,136,136,0,32,136,136,136,136,136,136
.db 136,136,0,32,136,136,136,136,136,136,136,136,0,32,136,136
.db 136,136,136,136,136,135,255,31,136,136,136,136,136,136,136,136
.db 255,31,136,136,136,136,136,136,136,136,255,31,136,136,136,136
.db 136,136,136,136,255,31,136,136,136,136,120,136,136,136,254,31
.db 136,136,136,136,136,136,136,136,254,31,136,136,136,136,136,136
.db 136,136,254,31,136,136,135,136,136,136,136,136,253,31,136,136
.db 136,136,136,136,136,136,253,31,136,136,136,120,136,136,136,136
.db 252,31,136,136,136,136,136,136,136,136,252,31,136,136,136,135
.db 136,136,136,136,251,31,136,136,136,136,136,136,136,136,251,31
.db 136,135,136,136,136,136,136,136,250,31,136,136,136,136,136,136
.db 135,136,249,31,136,136,136,136,136,136,136,136,249,31,136,136
.db 135,136,136,136,136,136,248,31,136,136,136,136,136,135,136,136
.db 247,31,136,136,136,136,136,136,136,120,246,31,136,136,136,136
.db 136,136,136,136,246,31,136,120,136,136,136,136,136,136,245,31
.db 136,136,136,135,136,136,136,136,244,31,136,136,136,136,120,136
.db 136,136,243,31,136,136,136,136,136,135,136,136,242,31,136,136
.db 136,136,136,120,136,136,241,31,136,136,136,136,136,120,136,136
.db 240,31,136,136,136,136,136,120,136,136,239,31,136,136,136,136
.db 136,120,136,136,238,31,136,136,136,136,136,135,136,136,237,31
.db 136,136,136,136,135,136,136,136,236,31,136,136,136,120,136,136
.db 136,136,235,31,136,136,135,136,136,136,136,136,234,31,136,135
.db 136,136,136,136,136,120,232,31,136,136,136,136,136,136,135,136
.db 231,31,136,136,136,136,120,136,136,136,230,31,136,136,136,135
.db 136,136,136,136,229,31,136,135,136,136,136,136,136,135,227,31
.db 136,136,136,136,136,135,136,136,226,31,136,136,120,136,136,136
.db 136,136,225,31,120,136,136,136,136,136,135,136,223,31,136,136
.db 136,120,136,136,136,136,222,31,136,135,136,136,136,136,120,136
.db 220,31,136,136,136,120,136,136,136,136,219,31,136,135,136,136
.db 136,136,135,136,217,31,136,136,136,120,136,136,136,136,216,31
.db 120,136,136,136,136,120,136,136,214,31,136,136,135,136,136,136
.db 136,135,212,31,136,136,136,136,135,136,136,136,211,31,120,136
.db 136,136,136,120,136,136,209,31,136,136,135,136,136,136,120,136
.db 207,31,136,136,136,135,136,136,136,120,205,31,136,136,136,136
.db 135,136,136,136,204,31,120,136,136,136,136,135,136,136,202,31
.db 136,120,136,136,136,120,136,136,200,31,136,136,135,136,136,136
.db 135,136,198,31,136,136,120,136,136,136,120,136,196,31,136,136
.db 120,136,136,136,120,136,194,31,136,136,120,136,136,136,120,136
.db 192,31,136,136,120,136,136,136,120,136,190,31,136,136,120,136
.db 136,136,120,136,188,31,136,136,120,136,136,136,120,136,186,31
.db 136,136,135,136,136,136,135,136,184,31,136,120,136,136,136,120
.db 136,136,182,31,136,135,136,136,136,135,136,136,180,31,120,136
.db 136,136,135,136,136,120,177,31,136,136,136,120,136,136,136,135
.db 175,31,136,136,120,136,136,136,135,136,173,31,136,120,136,136
.db 136,135,136,136,171,31,120,136,136,136,135,136,136,120,168,31
.db 136,136,120,136,136,136,135,136,166,31,136,120,136,136,136,135
.db 136,136,164,31,135,136,136,120,136,136,120,136,161,31,136,136
.db 135,136,136,120,136,136,159,31,120,136,136,120,136,136,136,135
.db 156,31,136,136,135,136,136,120,136,136,154,31,120,136,136,120
.db 136,136,136,135,151,31,136,136,135,136,136,135,136,136,149,31
.db 135,136,136,135,136,136,135,136,146,31,136,120,136,136,120,136
.db 136,120,143,31,136,136,120,136,136,120,136,136,141,31,120,136
.db 136,120,136,136,135,136,138,31,136,135,136,136,135,136,136,135
.db 135,31,136,136,135,136,136,135,136,120,132,31,136,136,120,136
.db 136,120,136,136,130,31,120,136,136,135,136,136,135,136,127,31
.db 136,135,136,120,136,136,120,136,124,31,136,135,136,136,135,136
.db 120,136,121,31,136,120,136,136,135,136,136,135,118,31,136,120
.db 136,136,120,136,136,135,115,31,136,120,136,136,120,136,136,135
.db 112,31,136,120,136,136,120,136,136,135,109,31,136,120,136,136
.db 120,136,136,135,106,31,136,120,136,136,135,136,120,136,103,31
.db 136,120,136,136,135,136,120,136,100,31,136,135,136,136,136,135
.db 136,120,97,31,136,136,135,136,120,136,136,135,94,31,136,120
.db 136,136,135,136,120,136,91,31,136,135,136,120,136,136,135,136
.db 88,31,120,136,136,135,136,120,136,120,84,31,136,136,135,136
.db 120,136,136,135,81,31,136,120,136,136,135,136,135,136,78,31
.db 120,136,136,135,136,120,136,120,74,31,136,136,135,136,120,136
.db 136,135,71,31,136,135,136,120,136,136,135,136,68,31,135,136
.db 120,136,136,135,136,135,64,31,136,120,136,120,136,136,135,136
.db 61,31,120,136,120,136,136,135,136,135,57,31,136,120,136,120
.db 136,136,135,136,54,31,135,136,120,136,120,136,136,135,50,31
.db 136,135,136,120,136,120,136,120,46,31,136,136,135,136,135,136
.db 120,136,43,31,120,136,120,136,136,135,136,135,39,31,136,135
.db 136,120,136,120,136,120,35,31,136,136,135,136,135,136,136,135
.db 32,31,136,120,136,120,136,120,136,120,28,31,136,136,135,136
.db 135,136,135,136,25,31,135,136,135,136,120,136,120,136,21,31
.db 120,136,120,136,120,136,120,136,17,31,136,135,136,135,136,135
.db 136,135,13,31,136,135,136,135,136,135,136,135,9,31,136,135
.db 136,135,136,135,136,135,5,31,136,135,136,135,136,135,136,135
.db 1,31,136,135,136,135,136,135,136,135,253,30,136,135,136,135
.db 136,135,136,135,249,30,136,135,136,135,136,135,136,135,245,30
.db 136,135,136,135,136,135,136,120,241,30,136,120,136,120,136,120
.db 136,120,237,30,136,120,136,120,136,135,136,135,233,30,136,135
.db 136,135,136,135,136,135,229,30,120,136,120,136,120,136,120,136
.db 225,30,135,136,135,136,135,136,135,120,220,30,136,120,136,120
.db 136,120,136,135,216,30,136,135,136,135,120,136,120,136,212,30
.db 120,136,120,136,135,136,135,120,207,30,136,120,136,120,136,135
.db 136,135,203,30,136,135,120,136,120,136,120,136,199,30,136,135
.db 136,135,120,136,120,136,195,30,135,136,135,120,136,120,136,120
.db 190,30,136,135,136,135,120,136,120,136,186,30,135,136,135,120
.db 136,120,136,135,181,30,136,135,120,136,120,136,135,136,177,30
.db 135,120,136,120,136,135,136,135,172,30,120,136,120,136,135,136
.db 135,120,167,30,136,135,136,135,120,136,120,136,163,30,135,136
.db 135,136,120,136,135,120,158,30,136,120,136,135,136,135,120,136
.db 154,30,135,136,135,120,136,135,136,135,149,30,120,136,135,136
.db 135,120,136,135,144,30,136,135,120,136,135,136,135,120,139,30
.db 136,135,136,135,120,136,135,120,134,30,136,120,136,135,120,136
.db 136,135,130,30,120,136,120,136,135,120,136,135,125,30,136,135
.db 120,136,135,120,136,120,120,30,136,135,120,136,135,120,136,120
.db 115,30,136,135,120,136,135,120,136,120,110,30,136,135,120,136
.db 135,120,136,120,105,30,136,135,120,136,135,120,136,135,100,30
.db 120,136,136,135,120,136,135,120,95,30,136,120,136,135,120,136
.db 135,120,90,30,136,135,120,136,135,120,136,120,85,30,136,135
.db 120,136,135,120,136,135,80,30,120,136,135,120,136,135,120,136
.db 75,30,135,120,136,136,135,120,136,135,70,30,120,136,135,120
.db 136,135,120,136,65,30,135,120,136,135,120,136,135,120,59,30
.db 136,135,120,136,135,120,136,135,54,30,120,136,135,120,136,135
.db 120,136,49,30,135,120,136,135,120,136,135,136,44,30,135,120
.db 136,135,120,136,135,120,38,30,136,135,120,120,136,135,120,136
.db 33,30,135,120,136,135,120,136,135,120,27,30,136,135,120,120
.db 136,135,120,136,22,30,135,120,136,135,120,136,135,136,17,30
.db 135,120,136,135,135,120,136,135,11,30,120,136,135,120,120,136
.db 135,120,5,30,136,135,120,136,135,135,120,136,0,30,135,120
.db 136,135,135,120,136,135,250,29,136,135,120,136,135,120,120,136
.db 245,29,135,120,136,135,120,120,136,135,239,29,120,136,135,135
.db 120,136,135,120,233,29,120,136,135,120,136,135,135,136,228,29
.db 135,120,136,135,120,120,136,135,222,29,120,136,135,135,120,136
.db 135,135,216,29,120,136,135,120,120,136,135,120,210,29,120,136
.db 135,136,135,120,120,136,205,29,135,120,120,136,135,120,120,136
.db 199,29,135,120,120,136,135,120,120,136,193,29,135,120,120,136
.db 135,136,135,120,187,29,120,136,135,120,120,136,135,135,181,29
.db 120,136,135,135,120,136,135,135,175,29,120,120,136,135,120,120
.db 136,135,169,29,135,120,136,135,135,136,135,120,163,29,120,136
.db 135,135,120,136,135,135,157,29,120,120,136,135,135,120,136,135
.db 151,29,135,120,120,136,135,135,136,135,145,29,120,120,136,135
.db 135,120,120,136,139,29,135,120,120,136,135,135,120,120,132,29
.db 136,135,135,120,120,136,120,120,126,29,136,135,120,120,136,135
.db 135,120,120,29,120,136,135,135,120,120,120,136,114,29,135,135
.db 120,120,136,135,135,120,107,29,136,120,120,120,136,135,135,120
.db 101,29,120,136,135,135,120,120,136,135,95,29,135,120,136,135
.db 120,120,136,135,89,29,135,135,120,120,136,135,135,120,82,29
.db 120,120,136,135,135,120,120,120,75,29,136,135,135,120,136,135
.db 120,120,69,29,136,135,135,135,120,120,136,135,63,29,135,135
.db 120,120,136,135,135,120,56,29,136,135,135,120,120,120,136,135
.db 50,29,135,135,120,120,136,135,135,135,43,29,120,120,120,136
.db 120,120,136,135,37,29,135,135,120,120,120,136,135,135,30,29
.db 135,120,120,120,136,135,135,135,23,29,120,136,135,135,120,120
.db 120,136,17,29,135,135,135,120,120,120,136,135,10,29,120,120
.db 136,135,135,135,120,120,3,29,120,120,136,135,135,135,120,120
.db 252,28,120,120,136,135,120,120,136,135,246,28,135,135,120,120
.db 120,120,136,135,239,28,135,135,135,120,120,120,120,136,232,28
.db 135,120,120,136,135,135,135,135,225,28,120,120,120,120,136,135
.db 120,120,218,28,120,136,135,135,135,135,120,120,211,28,120,120
.db 120,136,135,120,120,120,204,28,136,135,135,135,135,120,120,120
.db 197,28,120,120,136,135,135,135,135,135,190,28,136,135,135,135
.db 135,135,120,120,183,28,120,120,120,136,135,135,135,135,176,28
.db 135,135,136,135,135,135,135,135,169,28,120,120,120,120,120,120
.db 136,135,162,28,135,120,120,120,120,136,135,135,155,28,135,135
.db 135,135,135,120,136,135,148,28,135,135,135,135,120,120,120,120
.db 140,28,120,120,136,135,120,120,120,120,133,28,120,120,120,120
.db 136,135,135,135,126,28,135,120,120,120,120,136,135,135,119,28
.db 135,135,135,135,135,135,135,135,111,28,136,135,135,135,135,135
.db 135,135,104,28,135,135,135,120,120,120,120,136,97,28,135,135
.db 135,135,135,135,135,135,89,28,120,120,120,120,120,120,136,135
.db 82,28,135,135,135,135,135,135,135,135,74,28,135,120,120,120
.db 136,135,135,135,67,28,135,135,135,135,135,135,135,135,59,28
.db 135,135,120,120,120,120,120,120,51,28,136,135,135,135,135,135
.db 135,120,44,28,120,120,120,120,120,120,120,120,36,28,120,120
.db 120,136,135,135,135,135,29,28,135,135,135,135,135,135,135,135
.db 21,28,120,120,120,120,120,120,120,120,13,28,120,120,120,120
.db 136,135,135,135,6,28,135,135,135,135,135,135,135,135,254,27
.db 120,120,120,120,120,120,120,120,246,27,135,135,135,120,120,120
.db 120,120,238,27,120,120,120,120,120,120,136,135,231,27,135,135
.db 135,135,135,135,135,119,222,27,136,135,135,135,135,135,135,135
.db 215,27,135,135,135,120,120,120,120,120,207,27,135,135,135,135
.db 135,120,120,120,199,27,120,120,120,120,120,135,135,120,191,27
.db 120,120,120,120,120,120,120,120,183,27,135,135,120,120,120,120
.db 120,120,175,27,120,120,135,135,135,120,120,120,167,27,120,120
.db 120,135,135,135,135,135,159,27,135,120,120,120,135,135,135,135
.db 151,27,135,135,135,119,136,135,135,135,143,27,135,135,135,119
.db 120,120,120,136,135,27,135,135,119,120,120,120,120,120,126,27
.db 136,119,120,120,120,120,120,120,118,27,135,120,120,120,120,120
.db 135,135,110,27,135,120,120,120,135,135,135,135,102,27,135,135
.db 135,135,135,135,135,119,93,27,120,120,120,120,120,120,120,120
.db 85,27,120,120,120,135,135,135,135,135,77,27,135,135,135,135
.db 119,120,120,120,68,27,120,120,120,120,120,120,120,135,60,27
.db 135,120,120,135,135,135,135,135,52,27,135,135,135,135,119,120
.db 120,120,43,27,120,120,120,120,120,135,135,135,35,27,135,119
.db 120,136,135,119,120,120,26,27,120,120,135,135,135,119,136,135
.db 18,27,135,119,120,120,120,120,120,120,9,27,120,120,135,120
.db 120,120,135,135,1,27,135,119,120,120,136,119,120,120,248,26
.db 120,135,135,135,119,120,136,119,239,26,120,120,120,120,135,135
.db 135,135,231,26,135,135,119,120,136,119,120,120,222,26,120,135
.db 135,135,120,135,135,119,213,26,120,120,120,135,135,135,135,135
.db 205,26,135,119,120,120,120,135,135,120,196,26,135,135,135,119
.db 136,135,119,120,187,26,120,135,135,135,135,135,135,119,178,26
.db 120,120,135,135,135,135,135,119,169,26,120,120,120,135,135,120
.db 135,135,161,26,119,136,135,119,120,120,135,135,152,26,135,119
.db 136,119,120,120,120,135,143,26,135,119,120,120,135,120,120,135
.db 134,26,135,135,135,119,120,120,120,135,125,26,135,119,136,119
.db 120,120,135,135,116,26,119,120,120,120,120,120,135,135,107,26
.db 120,135,135,119,120,120,135,120,98,26,135,135,119,120,120,135
.db 135,119,88,26,120,120,120,120,135,135,120,135,80,26,119,120
.db 120,120,120,120,135,119,70,26,120,120,135,135,119,136,119,120
.db 61,26,120,135,120,135,135,119,120,120,52,26,120,120,135,135
.db 119,120,120,135,43,26,119,136,135,119,120,135,120,135,34,26
.db 135,119,120,120,120,120,135,119,24,26,120,120,135,135,135,135
.db 119,120,15,26,135,120,120,135,119,120,120,120,6,26,120,135
.db 119,120,120,135,119,120,252,25,120,120,120,135,120,135,119,120
.db 243,25,120,135,135,135,119,120,120,135,234,25,119,120,120,120
.db 120,120,120,135,225,25,119,120,120,135,119,136,119,120,215,25
.db 135,135,119,120,120,120,135,135,206,25,135,119,120,120,135,119
.db 120,135,196,25,135,135,135,119,136,119,120,135,187,25,119,120
.db 120,120,135,135,119,120,177,25,135,119,136,119,136,119,120,135
.db 168,25,119,120,120,135,119,136,119,120,158,25,135,119,136,119
.db 120,135,119,136,149,25,119,120,135,135,119,120,135,135,139,25
.db 135,135,119,120,120,135,119,120,129,25,135,135,135,119,120,135
.db 135,135,120,25,119,120,135,135,135,119,120,135,110,25,119,120
.db 135,120,135,120,135,119,100,25,120,135,119,120,135,119,136,119
.db 90,25,120,120,135,119,120,120,135,135,81,25,119,120,135,119
.db 120,120,120,135,71,25,135,135,119,120,135,119,120,135,61,25
.db 119,120,136,119,120,135,119,120,51,25,135,119,120,120,120,135
.db 135,119,41,25,120,135,119,120,120,120,135,119,31,25,120,135
.db 135,119,120,120,135,119,21,25,120,135,119,120,135,120,135,119
.db 11,25,120,135,135,119,120,135,119,120,1,25,120,135,119,136
.db 119,120,135,119,247,24,120,119,136,119,120,120,135,119,237,24
.db 120,135,119,120,135,135,120,119,227,24,120,135,119,120,135,119
.db 120,120,217,24,120,120,135,119,135,119,120,135,207,24,120,119
.db 136,119,120,119,120,135,197,24,135,119,120,135,135,119,120,135
.db 187,24,119,120,120,135,119,120,120,135,177,24,119,120,120,135
.db 119,120,135,119,166,24,120,120,135,135,119,120,119,120,156,24
.db 135,135,119,120,120,135,119,120,146,24,135,119,120,120,135,135
.db 119,120,136,24,119,120,135,119,120,120,120,135,126,24,119,120
.db 119,120,135,135,120,119,115,24,120,135,119,120,119,120,135,120
.db 105,24,120,119,120,135,119,120,119,136,95,24,135,119,135,119
.db 120,135,119,135,84,24,120,120,119,120,135,119,135,119,73,24
.db 136,135,119,135,119,120,119,120,63,24,135,120,135,119,120,119
.db 120,135,53,24,119,135,120,120,119,120,135,119,42,24,135,135
.db 135,119,120,135,119,135,32,24,119,120,120,120,135,119,135,119
.db 21,24,120,119,120,120,120,135,119,135,11,24,119,120,120,119
.db 136,119,135,119,0,24,135,135,119,120,135,135,119,135,246,23
.db 119,120,135,119,120,120,119,120,235,23,135,135,119,135,119,120
.db 120,119,224,23,120,120,119,120,135,135,119,135,214,23,135,119
.db 120,119,120,119,136,119,203,23,120,135,119,135,119,135,120,135
.db 193,23,119,120,119,120,119,120,120,120,182,23,135,119,135,119
.db 135,135,119,120,171,23,135,119,135,135,119,120,119,120,160,23
.db 120,119,120,120,119,120,119,120,149,23,135,119,120,135,135,119
.db 135,119,138,23,135,135,119,135,135,119,135,135,128,23,119,135
.db 119,135,135,135,119,135,117,23,119,135,119,135,135,135,119,135
.db 106,23,119,135,119,120,135,135,119,135,95,23,119,135,135,119
.db 135,135,119,135,84,23,135,119,135,119,135,135,135,119,73,23
.db 135,119,135,119,135,120,135,119,62,23,119,120,119,120,120,135
.db 119,120,51,23,119,120,120,119,120,135,119,120,40,23,135,119
.db 135,119,135,135,135,119,29,23,119,120,119,120,120,135,119,120
.db 18,23,119,120,135,119,135,135,119,120,7,23,119,120,119,120
.db 119,136,119,135,252,22,119,135,119,120,119,120,120,119,240,22
.db 120,120,119,135,119,135,120,119,229,22,120,119,120,119,120,120
.db 135,119,218,22,135,119,120,119,120,135,119,120,207,22,135,119
.db 135,119,119,121,119,120,196,22,119,135,135,119,119,120,120,135
.db 185,22,119,135,119,119,136,119,120,119,173,22,135,119,135,119
.db 120,120,119,135,162,22,135,119,119,120,135,120,119,135,151,22
.db 119,119,120,120,135,119,135,119,139,22,120,119,120,119,136,119
.db 119,120,128,22,119,135,135,119,120,119,120,135,117,22,119,135
.db 119,135,120,119,135,119,105,22,119,120,120,135,119,119,120,120
.db 94,22,119,135,135,119,120,119,135,119,82,22,135,119,135,135
.db 119,120,119,135,71,22,119,119,136,119,135,119,119,120,59,22
.db 120,119,120,135,119,120,119,119,47,22,120,135,135,119,119,120
.db 135,119,36,22,119,120,119,120,135,119,120,135,25,22,119,119
.db 120,119,135,135,119,120,13,22,119,120,119,120,119,120,120,119
.db 1,22,135,119,135,119,135,119,120,120,246,21,119,119,120,119
.db 136,119,119,120,234,21,135,119,119,135,120,119,120,119,222,21
.db 119,120,120,135,119,120,119,119,210,21,120,119,135,120,119,135
.db 135,119,199,21,119,135,135,119,135,119,119,120,187,21,135,119
.db 120,135,119,119,135,119,175,21,135,135,119,119,120,135,119,119
.db 163,21,135,120,119,135,119,120,119,119,151,21,121,119,135,119
.db 119,135,119,120,140,21,135,119,120,119,119,120,135,119,128,21
.db 120,135,119,119,135,119,135,119,116,21,120,135,119,119,135,135
.db 119,135,105,21,119,119,120,119,120,120,119,120,93,21,119,119
.db 120,119,120,120,119,120,81,21,119,119,120,135,119,135,119,120
.db 69,21,119,119,120,120,119,135,119,120,57,21,119,119,136,119
.db 119,135,119,120,45,21,119,135,135,119,119,135,119,135,33,21
.db 135,119,135,119,119,120,119,119,20,21,121,119,119,120,119,120
.db 119,120,9,21,120,119,119,135,119,135,119,120,253,20,119,120
.db 119,119,120,135,135,119,241,20,119,135,119,135,119,120,119,120
.db 229,20,119,119,135,119,120,135,119,119,216,20,120,119,120,135
.db 119,120,119,119,204,20,119,120,120,119,120,119,135,119,192,20
.db 135,119,120,118,120,119,120,135,180,20,119,135,119,119,135,119
.db 120,135,168,20,119,119,119,120,135,119,120,119,155,20,119,120
.db 119,120,135,119,119,120,143,20,119,135,119,120,119,120,119,119
.db 130,20,120,119,120,120,119,119,135,119,118,20,119,121,119,119
.db 119,120,119,120,106,20,120,119,119,120,119,120,119,120,94,20
.db 119,135,119,135,119,119,120,119,81,20,120,119,120,119,119,120
.db 120,119,69,20,135,119,119,119,136,119,119,120,57,20,119,119
.db 135,135,119,135,119,119,44,20,135,119,120,119,135,119,119,120
.db 32,20,135,119,119,120,119,135,119,135,20,20,119,119,120,119
.db 135,119,135,119,7,20,119,120,119,135,119,135,119,120,251,19
.db 119,119,119,120,135,135,119,119,238,19,119,120,119,135,135,119
.db 119,120,226,19,119,119,120,119,120,119,119,120,213,19,119,120
.db 135,119,119,119,135,119,200,19,120,120,119,119,135,119,135,119
.db 188,19,119,120,119,119,120,135,119,135,176,19,119,119,119,135
.db 135,119,135,119,163,19,119,135,119,120,119,119,135,119,150,19
.db 119,135,120,119,119,120,119,119,137,19,135,135,119,119,119,135
.db 119,120,125,19,135,119,119,135,119,119,120,119,112,19,120,119
.db 119,119,120,120,119,119,99,19,120,119,119,136,119,119,135,119
.db 87,19,118,120,135,119,119,119,135,135,74,19,119,119,119,120
.db 119,119,151,119,61,19,119,119,120,119,119,136,119,119,48,19
.db 119,135,119,135,119,119,120,119,35,19,119,119,120,120,119,119
.db 119,120,22,19,119,120,135,119,119,119,135,119,9,19,120,119
.db 120,119,119,119,136,119,253,18,119,119,120,119,119,120,120,119
.db 240,18,119,119,120,135,119,119,135,119,227,18,119,119,120,120
.db 119,119,135,119,214,18,135,119,119,120,119,119,119,136,202,18
.db 119,119,119,135,119,119,120,119,188,18,120,119,119,119,151,119
.db 119,119,175,18,119,120,119,120,119,119,120,119,162,18,119,135
.db 119,120,119,119,119,135,149,18,120,119,119,119,120,119,135,119
.db 136,18,120,119,119,119,120,120,119,119,123,18,120,119,119,135
.db 119,135,119,119,110,18,119,119,120,135,119,119,119,120,97,18
.db 135,119,119,135,119,119,135,119,84,18,120,119,119,119,119,120
.db 135,119,71,18,119,119,120,135,119,119,135,119,58,18,119,119
.db 120,119,135,119,119,119,44,18,135,135,119,119,119,120,119,120
.db 32,18,119,119,119,119,120,135,119,119,18,18,120,119,119,135
.db 135,119,119,119,5,18,119,119,136,119,119,119,120,119,248,17
.db 119,119,119,119,135,119,135,119,234,17,135,119,119,119,119,120
.db 119,135,221,17,119,119,119,121,119,119,119,119,207,17,119,151
.db 119,119,119,119,119,135,194,17,120,119,119,119,120,119,120,119
.db 181,17,119,119,135,119,135,119,119,119,167,17,135,119,135,119
.db 135,119,119,119,154,17,119,120,119,120,119,119,119,120,141,17
.db 119,135,119,119,119,135,119,119,127,17,120,119,119,135,120,119
.db 119,119,114,17,119,119,121,119,119,119,119,119,100,17,121,119
.db 119,119,119,119,151,119,88,17,119,119,119,119,151,119,119,119
.db 74,17,119,119,119,121,119,119,119,119,60,17,119,121,119,119
.db 119,119,119,136,48,17,119,119,119,119,119,151,119,119,34,17
.db 119,119,119,151,119,119,119,119,20,17,119,135,119,119,120,119
.db 119,119,6,17,120,119,120,119,119,119,120,119,249,16,120,119
.db 119,119,135,119,120,118,235,16,135,119,120,119,119,119,135,119
.db 222,16,135,119,119,119,135,119,135,119,209,16,119,119,119,119
.db 151,119,119,119,195,16,119,119,135,120,103,120,119,119,181,16
.db 135,119,119,120,119,119,119,120,168,16,119,119,119,120,119,119
.db 119,119,153,16,119,120,118,136,119,119,119,119,139,16,119,151
.db 119,134,119,119,119,135,126,16,119,120,119,103,120,135,119,119
.db 112,16,119,135,119,135,119,119,119,119,98,16,119,151,119,118
.db 120,119,119,135,85,16,119,120,103,119,120,135,119,119,71,16
.db 119,119,119,151,119,119,119,119,57,16,119,135,119,135,119,119
.db 119,135,44,16,119,119,119,120,118,151,119,119,30,16,119,119
.db 119,135,119,120,119,103,15,16,120,135,119,119,119,119,119,151
.db 3,16,119,119,119,119,119,135,135,103,244,15,119,120,119,135
.db 119,119,119,119,230,15,119,120,119,120,119,119,119,120,217,15
.db 119,119,135,118,119,121,119,119,203,15,119,119,119,120,104,119
.db 135,119,189,15,135,119,119,119,119,119,135,135,176,15,119,103
.db 135,119,135,119,119,119,161,15,119,119,135,135,119,103,120,119
.db 147,15,135,119,119,119,119,119,120,120,134,15,119,119,119,119
.db 120,119,119,119,119,15,119,135,135,119,119,119,119,135,106,15
.db 119,119,119,119,119,135,120,103,91,15,135,119,119,135,119,119
.db 119,119,77,15,118,119,120,119,135,103,135,119,62,15,120,119
.db 119,119,119,135,119,119,48,15,119,119,120,150,119,119,119,119
.db 34,15,119,135,119,119,119,119,119,105,20,15,135,119,119,119
.db 119,120,119,119,6,15,119,119,135,135,118,119,120,118,247,14
.db 151,119,119,119,119,119,120,119,234,14,119,119,119,119,136,103
.db 119,120,220,14,103,136,119,119,119,119,119,120,206,14,119,119
.db 119,119,119,121,103,135,192,14,119,134,135,119,119,119,119,119
.db 177,14,135,119,119,119,119,119,105,135,164,14,119,118,120,135
.db 119,119,119,119,149,14,119,135,119,119,119,119,119,136,136,14
.db 103,119,120,118,135,120,119,103,120,14,120,119,135,119,119,119
.db 119,119,106,14,120,119,119,119,119,119,105,135,93,14,103,119
.db 120,150,119,119,119,119,78,14,119,120,119,119,119,119,135,119
.db 64,14,119,119,119,119,151,103,119,104,49,14,119,120,135,119
.db 134,119,103,136,36,14,119,119,119,119,119,120,119,119,21,14
.db 119,119,119,120,119,119,119,119,6,14,135,120,118,88,119,119
.db 119,151,248,13,118,119,104,119,104,121,103,135,233,13,103,135
.db 135,119,103,120,103,120,218,13,120,119,119,119,119,135,119,119
.db 204,13,119,119,119,135,119,119,119,119,189,13,119,120,119,119
.db 119,119,135,119,175,13,104,119,119,119,105,135,103,135,161,13
.db 118,151,134,119,118,120,118,105,146,13,120,103,120,103,136,119
.db 119,119,132,13,119,134,120,119,119,119,119,135,118,13,119,119
.db 119,119,119,120,119,119,103,13,119,119,135,119,119,119,119,119
.db 88,13,120,119,119,119,119,135,119,119,74,13,119,119,119,120
.db 119,119,119,119,59,13,135,119,119,119,119,119,120,104,45,13
.db 119,119,119,135,104,119,119,119,30,13,119,105,119,119,119,119
.db 135,135,17,13,118,119,119,119,136,118,119,119,1,13,119,151
.db 118,119,119,119,119,120,243,12,104,119,119,119,120,104,119,119
.db 228,12,119,151,118,119,119,119,119,120,214,12,119,119,119,119
.db 135,119,119,119,199,12,119,119,120,119,119,119,119,118,183,12
.db 118,121,119,134,103,135,150,103,168,12,120,103,120,118,121,119
.db 134,103,153,12,135,120,103,120,118,104,151,134,140,12,103,135
.db 118,119,121,118,119,119,124,12,119,135,119,119,119,119,119,120
.db 110,12,119,119,119,119,120,119,119,119,95,12,119,135,119,119
.db 119,119,119,120,81,12,119,119,119,134,120,119,119,103,65,12
.db 120,150,119,103,120,118,136,103,51,12,135,118,119,119,136,103
.db 119,119,36,12,119,135,119,119,119,119,119,120,22,12,119,119
.db 119,119,120,119,119,119,7,12,119,135,119,119,103,104,151,119
.db 249,11,103,104,119,119,105,104,119,119,233,11,119,105,119,119
.db 119,119,135,119,219,11,119,119,119,119,120,119,119,119,204,11
.db 134,120,119,119,134,118,151,103,189,11,135,118,119,135,135,118
.db 119,119,174,11,135,119,119,119,119,119,120,119,160,11,119,119
.db 103,121,119,134,103,119,144,11,151,134,118,104,119,119,120,119
.db 130,11,119,119,119,120,116,135,104,119,113,11,119,119,135,119
.db 119,119,119,119,98,11,120,119,103,120,118,121,134,103,83,11
.db 119,119,136,118,119,119,119,135,69,11,119,119,119,119,135,119
.db 119,119,54,11,118,119,121,103,119,119,119,120,39,11,119,119
.db 119,119,120,119,119,119,24,11,103,136,119,103,135,118,151,118
.db 9,11,104,119,119,135,119,119,119,119,250,10,119,120,119,103
.db 120,118,121,134,236,10,118,119,119,105,119,119,119,119,220,10
.db 120,119,119,119,103,151,103,104,205,10,119,119,151,118,119,119
.db 119,135,191,10,119,119,103,120,118,121,134,118,175,10,119,119
.db 105,119,119,119,119,120,161,10,119,119,119,118,121,134,118,119
.db 145,10,119,135,119,119,119,119,135,119,131,10,119,119,134,150
.db 119,118,119,119,115,10,135,119,119,119,119,135,119,119,101,10
.db 103,104,151,103,119,119,119,135,86,10,119,119,119,119,134,120
.db 119,134,71,10,118,119,136,115,119,120,119,119,53,10,119,119
.db 120,119,134,118,119,136,39,10,118,119,119,119,120,119,119,119
.db 23,10,118,121,134,118,119,119,120,119,8,10,119,119,119,120
.db 119,119,118,119,248,9,121,118,119,119,119,120,119,119,234,9
.db 119,134,120,119,134,118,119,135,219,9,119,119,119,103,136,119
.db 103,104,203,9,119,135,104,119,119,119,120,119,189,9,119,134
.db 118,151,134,118,119,119,173,9,135,119,119,103,104,151,119,103
.db 158,9,119,119,135,119,119,119,119,150,144,9,103,104,119,119
.db 135,119,119,119,128,9,134,120,119,119,118,119,135,119,113,9
.db 119,119,119,120,119,119,134,118,97,9,105,119,119,119,119,120
.db 119,119,83,9,134,118,105,119,119,119,119,120,68,9,119,119
.db 134,118,105,104,119,119,52,9,119,120,119,103,104,119,121,103
.db 37,9,119,119,119,120,119,103,104,151,23,9,134,118,119,119
.db 135,116,103,119,3,9,121,134,118,119,119,120,119,119,245,8
.db 134,150,103,104,119,119,135,119,230,8,119,119,103,151,119,118
.db 119,119,214,8,135,119,119,119,118,151,103,119,199,8,119,119
.db 135,119,119,118,119,105,184,8,104,119,119,119,120,119,103,104
.db 168,8,119,136,118,119,119,134,120,103,153,8,104,119,119,120
.db 119,119,119,150,139,8,119,103,119,119,135,119,119,119,123,8
.db 103,151,119,118,119,119,120,119,108,8,119,103,119,121,118,119
.db 119,119,92,8,120,119,103,119,119,105,119,119,77,8,119,150
.db 119,119,118,119,135,104,62,8,119,103,104,151,119,118,119,119
.db 46,8,120,119,119,103,119,105,104,119,31,8,119,135,119,119
.db 134,118,151,103,16,8,119,119,119,150,119,103,119,119,0,8
.db 120,119,119,119,118,121,134,118,241,7,119,119,120,119,119,118
.db 151,103,226,7,119,119,87,119,118,119,119,105,208,7,119,119
.db 103,119,105,104,119,103,191,7,136,119,119,118,119,151,118,119
.db 177,7,119,118,151,134,118,119,119,120,162,7,119,134,118,119
.db 121,118,119,119,146,7,150,119,119,118,119,135,119,119,131,7
.db 119,118,121,103,119,119,119,120,116,7,119,118,119,151,118,119
.db 119,118,99,7,151,119,118,119,119,120,119,119,85,7,118,119
.db 136,118,119,119,150,119,70,7,134,118,119,135,119,119,103,119
.db 53,7,121,118,119,103,104,121,103,104,38,7,119,135,104,119
.db 103,119,151,103,23,7,119,119,134,120,119,134,118,119,7,7
.db 120,119,119,103,151,103,104,119,248,6,119,120,119,103,119,119
.db 120,119,233,6,119,118,151,119,118,119,103,136,218,6,119,103
.db 119,119,120,119,119,118,201,6,151,119,118,119,103,136,119,119
.db 187,6,118,119,136,99,119,119,105,119,168,6,119,118,151,134
.db 118,119,103,151,153,6,103,104,119,119,120,119,119,118,136,6
.db 151,103,119,119,103,151,119,118,121,6,119,119,120,119,103,119
.db 151,118,106,6,119,119,118,151,103,104,119,119,90,6,120,119
.db 118,119,135,104,119,119,75,6,118,151,118,119,119,103,121,119
.db 60,6,118,119,135,119,119,103,119,151,45,6,118,119,103,104
.db 121,119,118,119,28,6,135,119,119,103,119,121,118,119,13,6
.db 103,119,121,118,119,119,135,119,254,5,103,119,119,120,119,103
.db 104,151,239,5,134,118,119,103,121,119,118,119,222,5,135,104
.db 119,134,118,151,103,119,207,5,119,118,121,103,119,119,150,119
.db 192,5,103,104,119,121,118,119,103,151,177,5,119,118,119,103
.db 121,119,118,119,160,5,103,106,119,134,118,135,104,55,141,5
.db 119,103,121,119,118,119,135,119,126,5,119,118,119,105,119,119
.db 118,151,111,5,119,118,119,103,121,119,118,119,94,5,135,119
.db 119,118,119,121,118,119,79,5,103,119,121,118,119,103,121,119
.db 64,5,103,119,119,120,119,103,119,151,49,5,118,119,119,118
.db 121,103,119,119,32,5,150,119,119,118,119,105,119,119,17,5
.db 118,151,119,118,103,104,121,103,1,5,119,119,166,118,103,119
.db 119,105,242,4,119,119,118,151,103,119,119,103,225,4,121,119
.db 118,119,134,120,103,119,210,4,119,105,119,119,118,151,119,118
.db 195,4,119,118,121,103,119,119,135,119,180,4,119,118,119,151
.db 118,103,119,151,165,4,103,119,119,118,121,134,118,119,148,4
.db 166,118,103,119,119,105,119,103,132,4,119,151,118,119,119,118
.db 121,119,118,4,54,103,119,121,103,119,119,150,98,4,119,118
.db 119,119,120,119,103,119,81,4,105,119,119,103,151,103,104,119
.db 66,4,103,121,119,118,119,150,119,119,51,4,118,119,121,118
.db 119,118,151,103,35,4,119,103,119,121,103,119,103,136,20,4
.db 119,103,119,119,105,119,103,119,3,4,151,103,119,118,119,121
.db 118,119,244,3,118,151,119,118,119,150,119,119,229,3,118,119
.db 120,119,119,118,151,118,213,3,119,119,118,121,118,119,119,150
.db 198,3,119,118,119,119,120,119,118,119,181,3,151,118,119,118
.db 151,119,118,119,166,3,118,121,103,119,119,150,119,103,150,3
.db 119,119,105,119,103,119,121,118,135,3,119,103,151,119,118,119
.db 118,121,120,3,119,118,119,150,119,119,118,119,103,3,105,119
.db 103,119,121,39,119,118,83,3,119,105,119,103,119,151,103,119
.db 68,3,103,119,121,118,119,103,151,119,53,3,118,119,150,119
.db 119,118,119,105,37,3,119,103,119,151,118,119,119,118,20,3
.db 121,118,119,118,121,103,119,103,4,3,152,118,119,118,119,105
.db 119,103,245,2,119,121,118,119,103,151,119,118,230,2,119,118
.db 121,103,119,103,151,119,215,2,119,118,151,103,119,103,119,121
.db 200,2,118,119,118,151,103,119,103,151,184,2,119,119,118,119
.db 105,119,103,119,167,2,151,118,119,118,151,103,119,103,151,2
.db 119,121,118,119,118,121,103,119,136,2,119,151,118,119,118,119
.db 105,119,121,2,119,118,151,103,119,103,151,119,106,2,118,119
.db 118,121,119,118,119,105,90,2,119,103,119,151,118,119,118,151
.db 75,2,112,121,118,119,118,121,103,119,53,2,103,151,119,103
.db 119,151,118,119,38,2,118,119,105,119,119,118,151,103,22,2
.db 119,103,151,119,103,119,103,121,7,2,103,119,103,121,119,118
.db 119,166,248,1,118,119,118,151,103,119,119,118,230,1,121,103
.db 119,103,151,119,103,103,214,1,151,119,103,119,103,121,119,103
.db 199,1,119,121,118,119,103,151,119,118,184,1,103,151,119,118
.db 119,103,121,119,169,1,118,119,121,118,103,119,151,118,153,1
.db 119,118,151,119,118,119,118,121,138,1,118,119,103,121,119,118
.db 119,151,123,1,118,119,118,151,103,119,103,119,105,1,121,103
.db 119,118,121,103,119,119,90,1,150,119,103,119,150,119,119,118
.db 74,1,151,119,118,103,119,121,118,114,54,1,119,118,151,118
.db 119,103,119,121,39,1,103,119,103,121,103,119,119,150,23,1
.db 119,118,119,166,118,119,118,151,8,1,118,119,103,119,121,103
.db 119,118,246,0,121,119,118,119,120,119,118,119,231,0,151,103
.db 103,119,151,103,119,103,215,0,119,121,118,119,103,121,103,119
.db 200,0,119,150,119,118,119,151,118,103,184,0,119,151,103,119
.db 103,119,121,118,169,0,119,103,121,103,119,119,150,119,154,0
.db 118,119,151,118,103,119,151,103,138,0,119,103,151,119,103,119
.db 118,121,123,0,103,119,103,106,119,118,119,121,108,0,118,103
.db 119,151,103,119,118,151,92,0,119,103,103,151,119,103,119,103
.db 74,0,106,103,119,119,121,118,103,119,59,0,121,103,119,98
.db 119,103,121,119,39,0,118,103,106,119,119,118,166,118,23,0
.db 103,119,151,119,118,103,151,119,8,0,118,119,136,136,136,136
.db 136,136
.org 0x6000
cos_sum:
.db 240,241,242,243,244,245,246,247,248,249,250,251,252,253,254,255
.db 241,242,243,244,245,246,247,248,249,250,251,252,253,254,255,0
.db 242,243,244,245,246,247,248,249,250,251,252,253,254,255,0,1
.db 243,244,245,246,247,248,249,250,251,252,253,254,255,0,1,2
.db 244,245,246,247,248,249,250,251,252,253,254,255,0,1,2,3
.db 245,246,247,248,249,250,251,252,253,254,255,0,1,2,3,4
.db 246,247,248,249,250,251,252,253,254,255,0,1,2,3,4,5
.db 247,248,249,250,251,252,253,254,255,0,1,2,3,4,5,6
.db 248,249,250,251,252,253,254,255,0,1,2,3,4,5,6,7
.db 249,250,251,252,253,254,255,0,1,2,3,4,5,6,7,8
.db 250,251,252,253,254,255,0,1,2,3,4,5,6,7,8,9
.db 251,252,253,254,255,0,1,2,3,4,5,6,7,8,9,10
.db 252,253,254,255,0,1,2,3,4,5,6,7,8,9,10,11
.db 253,254,255,0,1,2,3,4,5,6,7,8,9,10,11,12
.db 254,255,0,1,2,3,4,5,6,7,8,9,10,11,12,13
.db 255,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14
.org 0x6500
lsp_base:
.db 192,11,96,18,192,28,64,36,0,45,0,52,192,61,96,69
.db 64,79,96,85,160,8,192,13,224,20,0,27,224,35,32,41
.db 128,49,128,66,64,76,128,83,128,5,32,8,224,11,128,20
.db 160,47,160,54,224,61,32,70,160,78,96,89,64,6,96,9
.db 96,14,32,22,0,40,160,47,96,55,96,66,192,74,64,83
.db 224,6,96,9,32,17,64,40,64,51,0,57,160,66,128,72
.db 64,81,128,86,128,7,224,10,192,16,32,28,192,37,32,44
.db 96,59,0,68,192,75,64,82,0,11,96,16,0,25,160,32
.db 128,38,160,47,64,59,128,67,64,81,224,87,192,7,32,11
.db 160,15,96,22,192,26,192,38,96,63,96,71,32,81,32,88
.db 128,13,0,21,224,32,0,41,64,50,96,58,64,68,0,75
.db 32,83,128,87,64,7,32,12,32,18,0,26,96,38,32,43
.db 224,54,224,64,64,72,224,89,224,7,32,11,128,16,224,29
.db 224,50,32,58,32,64,64,70,160,77,96,82,96,5,160,7
.db 160,12,32,21,224,34,192,41,224,56,64,66,224,76,64,89
.db 64,9,32,12,128,20,224,36,0,43,160,49,224,58,160,64
.db 0,79,160,85,160,11,64,17,96,23,96,30,160,38,160,43
.db 192,53,0,63,192,70,0,79,224,4,32,7,96,14,96,29
.db 64,40,0,50,64,62,224,71,224,82,224,90,160,8,0,12
.db 0,19,160,25,128,31,0,48,128,57,192,64,192,78,64,84
.db 160,8,128,14,0,28,128,38,128,48,0,56,160,64,96,71
.db 32,80,160,85,192,9,0,14,32,20,0,27,224,31,160,39
.db 32,61,32,70,224,77,160,84,160,6,128,9,160,14,128,21
.db 128,39,32,55,0,62,64,69,64,77,32,84,160,6,160,9
.db 128,15,64,31,160,41,0,48,0,57,0,63,64,75,0,84
.db 32,5,96,9,0,24,128,36,0,47,128,57,32,68,32,77
.db 224,85,32,92,224,7,128,12,32,19,0,27,160,34,64,41
.db 128,50,0,59,192,69,96,84,0,10,128,13,160,21,128,28
.db 192,34,160,51,224,61,192,68,64,81,160,85,96,8,96,12
.db 0,18,64,24,0,30,0,35,224,51,0,71,96,79,96,87
.db 64,9,32,18,192,29,0,41,128,50,160,60,160,70,96,79
.db 96,87,64,93,32,7,224,11,224,17,160,25,64,31,160,39
.db 160,52,32,60,192,80,96,88,0,6,64,8,96,13,128,29
.db 64,50,224,56,192,66,0,74,160,82,64,89,160,5,192,8
.db 160,14,96,26,96,36,224,43,192,53,224,60,160,77,32,87
.db 128,6,192,10,96,23,128,33,128,43,128,52,128,62,0,72
.db 32,82,64,90,160,9,224,14,160,20,128,28,192,42,96,48
.db 64,56,192,66,64,75,192,80,64,7,128,10,160,17,64,32
.db 224,41,64,49,0,62,96,69,32,78,64,84,160,5,64,8
.db 128,13,224,20,64,27,0,45,0,57,32,66,160,79,128,88
.db 224,12,0,19,224,26,96,34,0,42,96,47,128,57,224,65
.db 96,75,224,81,0,7,128,10,224,17,128,24,192,37,0,44
.db 128,52,128,70,192,78,192,87,0,7,0,10,96,14,64,23
.db 64,48,160,60,96,66,224,71,160,79,160,84,128,6,192,9
.db 160,14,0,24,32,44,32,50,160,57,32,67,224,73,160,89
.db 32,8,192,10,96,20,0,41,0,48,192,53,32,62,224,67
.db 160,79,128,85,0,7,32,10,64,17,64,26,64,36,96,50
.db 128,58,224,63,0,70,0,80,0,10,128,14,192,21,224,30
.db 192,36,160,44,192,54,64,61,160,78,160,85,192,6,32,10
.db 160,14,192,21,224,26,96,34,0,57,32,67,32,78,160,89
.db 64,14,32,24,64,38,160,46,128,55,192,62,96,70,0,76
.db 64,83,160,87,224,6,96,10,32,16,128,24,160,30,224,40
.db 0,57,96,65,128,74,160,83,0,8,160,11,224,17,160,26
.db 0,45,224,53,96,60,0,69,224,78,192,84,0,5,128,6
.db 32,11,0,18,160,36,96,48,224,58,64,68,128,78,96,89
.db 0,9,96,12,160,18,128,33,224,47,192,52,96,60,160,67
.db 0,75,0,81,32,11,96,17,32,24,32,30,192,37,160,42
.db 32,55,160,68,0,77,160,82,128,5,0,9,160,21,160,29
.db 128,39,192,47,96,57,160,67,96,78,224,87,192,7,128,10
.db 64,16,160,22,224,28,192,51,32,63,96,70,64,81,96,86
.db 64,14,192,21,128,32,0,40,32,48,128,54,224,63,224,70
.db 32,80,96,85,64,10,224,14,192,20,160,27,32,33,96,39
.db 96,56,192,64,0,73,32,82,32,6,96,8,64,13,224,19
.db 32,40,192,58,160,67,64,73,192,81,96,88,224,7,64,11
.db 192,15,0,26,0,46,224,52,160,59,32,67,32,74,224,79
.db 160,9,160,17,160,27,224,36,64,46,96,54,160,64,64,74
.db 32,84,64,92,192,7,128,11,64,18,160,28,0,38,64,44
.db 96,54,128,63,32,71,128,79,32,11,96,15,160,22,64,31
.db 224,36,96,45,32,60,128,65,224,75,160,83,0,7,64,11
.db 128,17,32,24,128,31,224,36,224,51,224,63,64,73,64,89
.db 192,7,32,14,96,31,96,43,32,53,32,61,160,68,224,74
.db 128,82,192,87,32,7,224,11,192,17,160,27,64,33,32,42
.db 32,59,32,66,64,82,32,90,96,6,0,9,160,13,160,34
.db 64,47,224,51,64,61,32,67,0,81,32,88,0,5,192,7
.db 160,12,0,25,32,41,192,47,160,58,64,65,160,80,96,89
.db 64,8,0,13,96,25,192,34,32,43,128,51,192,60,64,68
.db 0,78,32,84,224,8,96,12,192,20,32,34,224,41,224,47
.db 192,57,0,64,192,71,0,80,64,7,224,10,160,15,192,32
.db 192,39,224,46,96,58,64,64,160,82,64,89,64,5,160,7
.db 128,13,32,23,192,33,96,48,96,57,224,62,64,72,192,87
lsp_low:
.db 224,253,192,252,16,255,208,2,32,0,112,1,80,1,64,3
.db 128,1,240,253,112,255,240,255,144,0,64,253,112,253,48,255
.db 240,254,192,2,96,1,240,254,160,255,192,255,240,255,96,1
.db 96,2,160,1,0,1,32,0,32,3,176,1,208,253,224,253
.db 112,255,112,253,96,0,0,0,0,255,224,253,48,3,128,0
.db 32,255,16,254,240,252,240,0,240,253,208,2,16,3,16,2
.db 80,255,176,253,32,252,160,252,208,2,176,0,176,255,128,251
.db 176,0,240,255,64,255,80,255,128,1,176,1,80,255,80,253
.db 224,2,176,2,16,2,64,255,112,255,240,255,16,0,192,255
.db 144,254,112,252,144,251,176,0,128,0,0,1,16,1,128,255
.db 192,254,16,254,112,253,80,3,0,3,0,255,48,0,16,4
.db 128,254,128,255,144,254,0,254,176,253,0,254,240,252,96,255
.db 240,254,96,0,96,2,80,0,112,255,240,254,32,253,128,0
.db 64,3,48,0,96,0,208,2,128,2,112,2,144,255,160,255
.db 224,253,96,251,240,1,128,0,16,0,0,255,176,2,64,4
.db 80,255,208,254,16,254,64,0,96,0,0,0,160,255,240,254
.db 0,255,160,253,0,255,32,254,32,0,144,0,144,253,0,255
.db 240,255,176,2,96,255,0,3,48,0,48,0,0,255,16,254
.db 208,255,224,3,64,4,176,2,208,0,48,0,96,255,128,0
.db 64,1,128,252,192,0,192,0,224,255,224,254,96,1,16,255
.db 128,253,192,253,16,0,112,0,144,2,0,0,16,0,224,2
.db 160,255,32,252,192,255,64,255,224,255,80,255,208,250,48,255
.db 224,255,176,5,16,2,96,255,0,0,64,0,80,255,0,255
.db 240,4,0,2,80,2,224,0,144,0,48,3,176,254,64,254
.db 128,252,224,253,0,0,80,1,144,0,96,254,176,0,192,1
.db 96,253,160,252,144,254,224,255,16,255,240,1,224,1,128,0
.db 144,253,224,251,144,253,192,253,240,1,64,254,128,253,32,253
.db 48,2,128,2,96,1,128,1,16,2,0,3,112,1,224,253
.db 224,0,128,2,0,2,16,1,176,1,208,255,144,1,160,1
.db 48,255,48,252,240,254,176,0,64,0,240,1,192,3,160,255
.db 96,254,112,253,0,252,208,0,0,1,96,254,96,3,240,1
.db 80,255,144,254,112,255,80,255,224,253,144,251,176,254,224,253
.db 208,253,112,3,32,3,208,1,160,254,80,254,224,252,160,253
.db 144,3,16,2,160,2,144,3,0,3,160,1,176,0,0,0
.db 240,252,16,254,160,1,192,255,32,255,80,0,224,4,80,2
.db 16,1,0,0,240,252,64,255,144,254,160,1,224,0,32,0
.db 32,0,80,253,240,254,64,255,160,0,128,255,192,255,128,0
.db 32,1,192,0,160,255,64,1,64,255,160,255,48,255,112,254
.db 32,2,240,0,128,2,16,3,112,0,128,0,208,0,64,1
.db 64,1,208,254,160,254,224,255,128,255,32,0,48,3,208,252
lsp_high:
.db 96,254,128,255,208,1,80,1,64,0,48,1,144,253,16,2
.db 144,255,192,253,128,3,96,3,0,3,128,2,208,1,192,255
.db 128,254,96,253,224,251,80,253,64,252,48,1,224,255,80,2
.db 144,2,96,255,176,253,64,252,0,252,32,1,160,254,208,4
.db 144,4,128,2,144,1,64,0,48,1,208,254,224,251,224,255
.db 176,0,80,0,80,1,224,0,160,1,112,254,160,250,192,255
.db 32,1,16,0,160,1,176,253,160,0,80,2,240,255,128,1
.db 64,255,80,252,80,255,64,1,160,255,32,2,0,255,0,255
.db 160,2,48,1,64,254,208,252,80,3,0,2,64,0,160,0
.db 224,3,80,1,64,255,224,253,176,1,64,0,0,253,0,253
.db 224,252,240,252,240,1,144,255,176,254,96,253,112,254,192,255
.db 80,253,160,254,176,3,32,0,176,1,192,0,112,255,160,255
.db 0,255,128,255,0,254,96,252,0,255,48,254,176,255,144,2
.db 112,1,32,254,240,253,32,253,48,255,96,255,160,253,64,3
.db 64,3,16,0,240,254,112,255,160,0,160,1,112,254,160,255
.db 16,2,192,254,80,3,112,3,144,1,0,254,176,255,96,253
.db 112,1,80,1,32,4,80,0,64,254,64,1,144,0,176,4
.db 208,1,144,255,96,253,144,253,240,0,48,0,144,254,80,1
.db 96,0,176,0,16,0,48,254,224,0,240,3,160,0,96,3
.db 160,1,128,254,208,252,240,252,112,0,144,254,208,252,240,0
.db 224,251,16,0,192,3,144,1,160,0,0,0,32,254,192,255
.db 16,255,16,1,48,1,176,3,128,2,64,0,176,255,16,2
.db 96,0,160,254,96,252,160,251,176,255,112,1,160,255,192,3
.db 192,2,48,254,0,255,16,253,48,254,64,3,208,254,32,3
.db 192,1,0,1,48,2,240,1,64,2,0,0,176,254,96,0
.db 80,1,176,1,96,1,160,2,112,0,224,251,128,253,128,255
.db 112,0,48,1,224,2,0,0,192,255,192,3,64,2,208,2
.db 144,255,48,254,160,255,0,254,144,253,32,0,96,0,112,255
.db 16,2,64,1,208,252,224,253,32,1,160,255,48,1,96,0
.db 176,0,80,0,208,254,48,254,224,255,160,2,80,255,48,253
.db 176,254,144,252,144,3,80,2,32,0,32,255,208,251,0,255
.db 80,254,160,253,80,4,0,3,48,1,32,0,240,254,64,1
.db 192,254,0,255,224,253,240,254,112,254,48,252,160,0,144,4
.db 208,2,0,1,128,253,0,252,240,254,48,254,160,254,128,3
.db 16,1,144,253,128,0,80,255,128,0,112,254,224,254,48,255
.db 208,254,128,0,96,3,144,3,64,2,240,254,96,254,192,255
.db 96,0,176,254,128,2,160,2,192,255,64,1,240,1,80,3
.db 160,0,224,253,176,252,240,1,240,254,48,2,0,0,240,0
.db 160,255,192,254,16,252,112,251,96,1,144,1,208,1,16,1
.db 128,0,48,254,144,253,176,251,32,1,240,0,16,255,176,255
pitch_gains:
.db 0,0,0,0,0,0,1,0,230,255,16,0,247,255,8,0
.db 245,255,232,255,10,0,233,255,19,0,65,0,247,255,28,0
.db 249,255,23,0,247,255,47,0,20,0,24,0,17,0,20,0
.db 33,0,34,0,244,255,10,0,222,255,246,255,250,255,60,0
.db 9,0,11,0,46,0,251,255,32,0,53,0,238,255,235,255
.db 217,255,5,0,251,255,31,0,13,0,13,0,27,0,4,0
.db 38,0,97,0,244,255,255,255,240,255,255,255,248,255,89,0
.db 18,0,15,0,36,0,243,255,1,0,70,0,255,255,9,0
.db 60,0,248,255,245,255,61,0,20,0,254,255,45,0,9,0
.db 16,0,47,0,5,0,18,0,206,255,17,0,1,0,57,0
.db 0,0,11,0,37,0,27,0,241,255,225,255,237,255,242,255
.db 44,0,35,0,4,0,15,0,3,0,22,0,46,0,248,255
energy_table:
.db 26,45,0,0,72,67,0,0,4,60,0,0,135,89,0,0
.db 221,79,0,0,35,119,0,0,70,106,0,0,138,158,0,0
.db 108,141,0,0,248,210,0,0,50,188,0,0,191,24,1,0
.db 111,250,0,0,151,117,1,0,65,77,1,0,36,241,1,0
.db 120,187,1,0,142,149,2,0,34,78,2,0,88,112,3,0
.db 75,17,3,0,123,147,4,0,2,21,4,0,233,22,6,0
.db 154,110,5,0,118,26,8,0,126,58,7,0,131,200,10,0
.db 121,158,9,0,115,89,14,0,215,204,12,0,76,24,19,0
.db 137,8,17,0,237,104,25,0,157,170,22,0,46,208,33,0
.db 157,41,30,0,228,254,44,0,63,35,40,0,83,224,59,0
.db 102,105,53,0,153,173,79,0,92,19,71,0,84,7,106,0
.db 202,148,94,0,246,23,141,0,65,220,125,0,70,193,187,0
.db 227,123,167,0,12,217,249,0,118,223,222,0,189,121,76,1
.db 102,148,40,1,230,109,186,1,134,169,138,1,253,190,76,2
.db 139,46,13,2,153,115,15,3,168,221,186,2,109,140,18,4
.db 68,253,161,3,3,85,107,5,83,140,213,4,196,35,54,7
innovation_book:
.db 7,17,17,27,25,22,12,4,253,0,28,220,39,232,241,3
.db 247,15,251,10,31,228,11,31,235,9,245,245,254,249,231,14
.db 234,31,4,242,19,244,14,251,4,249,4,251,9,0,254,42
.db 209,240,1,8,0,9,23,199,0,28,245,6,225,55,211,3
.db 251,4,2,254,4,249,253,6,254,7,253,12,5,8,54,246
.db 8,249,248,232,231,229,242,251,8,5,44,23,5,247,245,245
.db 243,247,244,248,227,248,234,6,241,3,244,255,251,253,34,255
.db 29,240,17,252,12,2,1,4,254,252,2,255,11,253,204,28
.db 30,247,224,25,44,236,232,4,6,255,0,0,0,0,0,0
.db 0,0,0,0,0,0,231,246,22,29,13,243,234,243,252,0
.db 252,240,10,15,220,232,28,25,255,253,66,223,245,241,6,0
.db 3,4,254,5,24,236,209,29,19,254,252,255,0,255,254,3
.db 1,8,245,5,5,199,28,28,0,240,4,252,12,250,255,2
.db 236,61,247,24,234,214,29,6,17,8,4,2,191,15,8,10
.db 5,6,5,3,2,254,253,5,247,4,251,23,13,23,253,193
.db 3,251,252,250,0,253,23,220,210,9,5,5,8,4,9,251
.db 1,253,10,1,250,10,245,24,209,31,22,244,14,246,6,11
.db 249,249,7,225,51,244,250,7,6,239,9,245,236,52,237,3
.db 250,250,248,251,23,215,37,1,235,10,242,8,7,5,241,241
.db 23,39,230,223,7,2,224,226,235,248,4,12,17,15,14,11

; Only these immediate bytes are writable code. Not reentrant; IRQ is disabled.
.globl _smc0
_smc0 = product_offset_0+1
.globl _smc1
_smc1 = product_offset_1+1
.globl _smc2
_smc2 = product_offset_2+1
.globl _smc3
_smc3 = product_offset_3+1

.globl coef_cache_ptr
