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
.globl _coef35_unused_step, _coef35_page_cursor
_coef35_unused_step = coef_step
_coef35_page_cursor = coef_out
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

; Exact MULT16_32_Q14: a*int16(b>>14) + floor(a*(b&16383)/16384).
; Input HL=signed16 a, DE=pointer to little-endian signed32 b; return HL:DE.
; Split once on a's sign. Both bodies prepare |a| once and restore only the
; sign of the high product. The negative body subtracts ceil(|a|*lo/16384),
; avoiding the old high-product negation followed by whole-result negation.
; Preserve IX/IY, alternate AF/BC/DE/HL and caller SP. Clobber ordinary
; AF/BC/DE/HL and qcoef/qarg/qtemp. Nonreentrant, as in the prior scratch path.
; _q14_sign aliases the old unused slot for checker compatibility; no access.
.globl _q14_unsigned, _q14_sign, _q14_scratch_start, _q14_scratch_end
_q14_sign = s8_sign
_q14_scratch_start = qcoef
_q14_scratch_end = qtemp+4
mulq14:
bit 7,h
jp nz,q33_negative
; a >= 0: high product has hi's sign; the fractional term is nonnegative.
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
bit 7,h
jr z,q33_positive_high_positive
xor a,a
sub a,l
ld l,a
sbc a,a
sub a,h
ld h,a
call _q14_unsigned
call neg32
jp q33_positive_high_ready
q33_positive_high_positive:
call _q14_unsigned
q33_positive_high_ready:
ld (qtemp),de
ld (qtemp+2),hl
ld hl,(qarg)
ld a,h
and a,#63
ld h,a
ld de,(qcoef)
call _q14_unsigned
; P=c*lo is below 2^29. Extract Q=floor(P/16384) into HL.
; DE retains the original low word, including all 14 remainder bits.
add hl,hl
add hl,hl
ld a,d
rlca
rlca
and a,#3
or a,l
ld l,a
; Add unsigned Q to the signed32 high product. Only low-word overflow can
; change the upper word. EX/LD preserve carry; INC HL is modulo16, as needed.
ld de,(qtemp)
add hl,de
ex de,hl
ld hl,(qtemp+2)
jr nc,q33_positive_return
inc hl
q33_positive_return:
ret
q33_negative:
; a < 0: |a|=32768 remains a valid unsigned magnitude. For hi < 0 the
; high product is already positive; negate it only when hi is nonnegative.
xor a,a
sub a,l
ld l,a
sbc a,a
sub a,h
ld h,a
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
bit 7,h
jr nz,q33_negative_high_negative
call _q14_unsigned
call neg32
jp q33_negative_high_ready
q33_negative_high_negative:
xor a,a
sub a,l
ld l,a
sbc a,a
sub a,h
ld h,a
call _q14_unsigned
q33_negative_high_ready:
ld (qtemp),de
ld (qtemp+2),hl
ld hl,(qarg)
ld a,h
and a,#63
ld h,a
ld de,(qcoef)
call _q14_unsigned
; P=c*lo is below 2^29. Extract Q=floor(P/16384) into HL.
; DE retains the original low word, including all 14 remainder bits.
add hl,hl
add hl,hl
ld a,d
rlca
rlca
and a,#3
or a,l
ld l,a
; Subtract ceil(P/16384) from signed32 a*hi. Keep Q in BC and form
; R=(D&63)|E from the untouched low product word. ADD A,255 sets carry
; exactly when R != 0, supplying the rounding borrow for the low SBC.
; The upper SBC propagates its borrow. All intervening LD/EX preserve it.
; This handles exact fractions and a=-32768 without special saturation.
ld b,h
ld c,l
ld hl,(qtemp)
ld a,d
and a,#63
or a,e
add a,#255
sbc hl,bc
ex de,hl
ld hl,(qtemp+2)
ld bc,#0
sbc hl,bc
ret

; Exact upstream integer cosine for HL=0..25736, returned signed16 in DE.
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
; Choose one complete 40-sample path per subframe. IX is scratch for
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
; Alternate HL/C hold the low16/high8 modulo24 pitch sum. Each
; constant product preserves all alternate registers. No sum RAM
; access is needed until all three active-or-skipped pitch taps are handled.
.globl _pitch_init_start, _pitch_init_end, _pitch_sum_state
_pitch_sum_state = accum
_pitch_init_start::
exx
ld hl,#0
ld c,#0
exx
_pitch_init_end::

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
ld hl,(gain_current+4)
call _pitch_indirect
; A:HL is the exact signed24 product. Transfer HL through the real stack.
; A survives PUSH/EXX/POP; EXX and POP
; preserve flags; ADD supplies carry for the high-byte ADC. Discard carry
; beyond bit 23 exactly as in the previous RAM accumulation.
.globl _pitch_add_0_start, _pitch_add_0_end
_pitch_add_0_start::
push hl
exx
pop de
add hl,de
adc a,c
ld c,a
exx
_pitch_add_0_end::
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
ld hl,(gain_current+2)
call _pitch_indirect
; A:HL is the exact signed24 product. Transfer HL through the real stack.
; A survives PUSH/EXX/POP; EXX and POP
; preserve flags; ADD supplies carry for the high-byte ADC. Discard carry
; beyond bit 23 exactly as in the previous RAM accumulation.
.globl _pitch_add_1_start, _pitch_add_1_end
_pitch_add_1_start::
push hl
exx
pop de
add hl,de
adc a,c
ld c,a
exx
_pitch_add_1_end::
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
ld hl,(gain_current+0)
call _pitch_indirect
; A:HL is the exact signed24 product. Transfer HL through the real stack.
; A survives PUSH/EXX/POP; EXX and POP
; preserve flags; ADD supplies carry for the high-byte ADC. Discard carry
; beyond bit 23 exactly as in the previous RAM accumulation.
.globl _pitch_add_2_start, _pitch_add_2_end
_pitch_add_2_start::
push hl
exx
pop de
add hl,de
adc a,c
ld c,a
exx
_pitch_add_2_end::
skip_pitch_2:
; Write exactly the three bytes consumed by the unchanged clamp and
; innovation logic. The fourth scratch byte is never read on this path.
.globl _pitch_flush_start, _pitch_flush_end
_pitch_flush_start::
exx
ld (accum),hl
ld a,c
ld (accum+2),a
exx
_pitch_flush_end::
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
jp pitch27_subframe_done
; For pitch >=41 and j=0..39, j-(pitch+1-k) is always negative.
; The three history words are adjacent; no wrap/skip test is needed. IX
; advances one word per sample and survives getbits, constant multiplication and clip.
; Duplicate the sample/shape loop to avoid a per-sample dispatch. Its clamp,
; innovation and output-history arithmetic remain identical to the general path.
exc_shape_fast:
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
.globl _pitch27_fast_sum_start, _pitch27_fast_sum_end
_pitch27_fast_sum_start::
exx
ld hl,#0
ld c,#0
exx
ld e,0(ix)
ld d,1(ix)
ld hl,(gain_current+4)
call _pitch_indirect
push hl
exx
pop de
add hl,de
adc a,c
ld c,a
exx
ld e,2(ix)
ld d,3(ix)
ld hl,(gain_current+2)
call _pitch_indirect
push hl
exx
pop de
add hl,de
adc a,c
ld c,a
exx
ld e,4(ix)
ld d,5(ix)
ld hl,(gain_current+0)
call _pitch_indirect
push hl
exx
pop de
add hl,de
adc a,c
ld c,a
exx
inc ix
inc ix
exx
ld (accum),hl
ld a,c
ld (accum+2),a
exx
_pitch27_fast_sum_end::
; S=sum(gain8*history16), bounded to +/-2048000 before innovation.
ld a,(accum+2)
bit 7,a
jr nz,pitch27_fast_exc_negative24
cp #31
jr c,pitch27_fast_excitation_clamped
jr nz,pitch27_fast_clamp_exc_positive
ld hl,(accum)
ld de,#0x4000
or a,a
sbc hl,de
jr c,pitch27_fast_excitation_clamped
pitch27_fast_clamp_exc_positive:
ld hl,#0x4000
ld (accum),hl
ld a,#31
ld (accum+2),a
jr pitch27_fast_excitation_clamped
pitch27_fast_exc_negative24:
cp #224
jr c,pitch27_fast_clamp_exc_negative
jr nz,pitch27_fast_excitation_clamped
ld hl,(accum)
ld de,#0xc000
or a,a
sbc hl,de
jr nc,pitch27_fast_excitation_clamped
pitch27_fast_clamp_exc_negative:
ld hl,#0xc000
ld (accum),hl
ld a,#224
ld (accum+2),a
pitch27_fast_excitation_clamped:
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
jr nc,pitch27_fast_exc_round_done
inc l
pitch27_fast_exc_round_done:
; Signed24 L:D:E >> 7, producing sign-extended HL:DE for clipping.
; Save the sign, shift once left and take the upper two bytes. The seven
; discarded low bits never reach DE; this retains arithmetic floor rounding.
.globl pitch27_fast__exc_shift_start, pitch27_fast__exc_shift_end
pitch27_fast__exc_shift_start::
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
pitch27_fast__exc_shift_end::
call _zx_clip
ld hl,(exc_ptr)
ld (hl),e
inc hl
ld (hl),d
inc hl
ld (exc_ptr),hl
ld hl,#sum_byte
dec (hl)
jp nz,_pitch27_fast_sum_start
ld hl,#shape_count
dec (hl)
jp nz,exc_shape_fast
pitch27_subframe_done:
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
call _q14_negated
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
; Preserves alternate AF/BC/DE/HL and IX/IY, including the neg32 tail.
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
; Clobbers both ordinary/alternate AF/BC/DE/HL sets; preserves IX/IY.
; Tables hold signed24 floor(shape*energy/4096), shape -65..66.
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
; Hold the 12-bit remainder and fraction scaled by sixteen in
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
ld a,l
exx
ld (bc),a
inc bc
exx
ld a,h
exx
ld (bc),a
inc bc
exx
ld a,c
exx
ld (bc),a
inc bc
exx
; EXX preserves flags: fractional carry feeds the integer ADC,
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
; Each recurrence ends in the upper register set, where the next PUSH reads
; its high word. Omit the old adjacent EXX/EXX identity before that PUSH.
; All 64 rows retain the same registers, flags, writes and final SP; save
; 64*8 = 512 nominal T per changed page. IRQ remains disabled as below.
; IRQ must remain disabled. Save the real return stack before using SP as
; a reverse table writer. No CALL/RET occurs until the real SP is restored.
; DE/DE' hold the low/high step; HL/HL' hold the accumulator.
; BC/BC' retain the next positive step; all are documented scratch registers.
ld (coef_saved_sp),sp
ld a,d
add a,a
sbc a,a
exx
ld d,a
ld e,a
exx
; Partial table 0: rows are stored from index 15 down to 0.
.globl _coef35_group_0_start, _coef35_group_0_end
_coef35_group_0_start::
; coef_out is page-aligned (7200..7B00). Select the group end directly;
; group 3 ends at the next page. Later ADD/XOR initializes flags before use.
ld hl,(coef_out)
ld l,#64
ld sp,hl
_coef35_group_0_end::
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
; BC/BC' are unused by the unrolled recurrence and PUSH writer.
; Retain the positive 16*step for the next group without RAM traffic.
ld b,h
ld c,l
exx
ld b,h
ld c,l
exx
; Negate the step once, keeping HL/HL' and the saved positive
; 16*step unchanged. Then ADD/ADC can descend without clearing carry first.
; Both negation and recurrence are exact modulo32, including -32768 inputs.
.globl _coef_neg_0_start, _coef_neg_0_end
_coef_neg_0_start::
; LD A,0 preserves borrow. SBC A,A / SUB D would lose the outgoing borrow.
xor a,a
sub a,e
ld e,a
ld a,#0
sbc a,d
ld d,a
exx
ld a,#0
sbc a,e
ld e,a
ld a,#0
sbc a,d
ld d,a
exx
_coef_neg_0_end::
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
ld d,b
ld e,c
exx
ld d,b
ld e,c
exx
; Partial table 1: rows are stored from index 15 down to 0.
.globl _coef35_group_1_start, _coef35_group_1_end
_coef35_group_1_start::
; coef_out is page-aligned (7200..7B00). Select the group end directly;
; group 3 ends at the next page. Later ADD/XOR initializes flags before use.
ld hl,(coef_out)
ld l,#128
ld sp,hl
_coef35_group_1_end::
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
; BC/BC' are unused by the unrolled recurrence and PUSH writer.
; Retain the positive 16*step for the next group without RAM traffic.
ld b,h
ld c,l
exx
ld b,h
ld c,l
exx
; Negate the step once, keeping HL/HL' and the saved positive
; 16*step unchanged. Then ADD/ADC can descend without clearing carry first.
; Both negation and recurrence are exact modulo32, including -32768 inputs.
.globl _coef_neg_1_start, _coef_neg_1_end
_coef_neg_1_start::
; LD A,0 preserves borrow. SBC A,A / SUB D would lose the outgoing borrow.
xor a,a
sub a,e
ld e,a
ld a,#0
sbc a,d
ld d,a
exx
ld a,#0
sbc a,e
ld e,a
ld a,#0
sbc a,d
ld d,a
exx
_coef_neg_1_end::
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
ld d,b
ld e,c
exx
ld d,b
ld e,c
exx
; Partial table 2: rows are stored from index 15 down to 0.
.globl _coef35_group_2_start, _coef35_group_2_end
_coef35_group_2_start::
; coef_out is page-aligned (7200..7B00). Select the group end directly;
; group 3 ends at the next page. Later ADD/XOR initializes flags before use.
ld hl,(coef_out)
ld l,#192
ld sp,hl
_coef35_group_2_end::
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
; BC/BC' are unused by the unrolled recurrence and PUSH writer.
; Retain the positive 16*step for the next group without RAM traffic.
ld b,h
ld c,l
exx
ld b,h
ld c,l
exx
; Negate the step once, keeping HL/HL' and the saved positive
; 16*step unchanged. Then ADD/ADC can descend without clearing carry first.
; Both negation and recurrence are exact modulo32, including -32768 inputs.
.globl _coef_neg_2_start, _coef_neg_2_end
_coef_neg_2_start::
; Shift by 8/12 guarantees E=0; negate D directly and propagate its borrow.
xor a,a
sub a,d
ld d,a
exx
ld a,#0
sbc a,e
ld e,a
ld a,#0
sbc a,d
ld d,a
exx
_coef_neg_2_end::
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
ld d,b
ld e,c
exx
ld d,b
ld e,c
exx
; Partial table 3: rows are stored from index 15 down to 0.
.globl _coef35_group_3_start, _coef35_group_3_end
_coef35_group_3_start::
; coef_out is page-aligned (7200..7B00). Select the group end directly;
; group 3 ends at the next page. Later ADD/XOR initializes flags before use.
ld hl,(coef_out)
inc h
ld sp,hl
_coef35_group_3_end::
; Signed high nibble: first row is -step, followed by -2..-8.
ld hl,#0
exx
ld hl,#0
exx
; Negate the step once, keeping HL/HL' and the saved positive
; 16*step unchanged. Then ADD/ADC can descend without clearing carry first.
; Both negation and recurrence are exact modulo32, including -32768 inputs.
.globl _coef_neg_3_start, _coef_neg_3_end
_coef_neg_3_start::
; Shift by 8/12 guarantees E=0; negate D directly and propagate its borrow.
xor a,a
sub a,d
ld d,a
exx
ld a,#0
sbc a,e
ld e,a
ld a,#0
sbc a,d
ld d,a
exx
_coef_neg_3_end::
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
; Convert -8*step to +8*step; next update yields row 7.
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
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
push hl
exx
push hl
add hl,de
exx
adc hl,de
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

; DE signed16 history, HL selected immutable routine address. CALL this
; trampoline so the routine's RET returns directly to the pitch accumulator.
; Every constant routine returns signed24 A:HL and preserves IX/IY, all
; alternate registers and the real stack. Ordinary flags/BC/DE may be clobbered.
.globl _pitch_indirect
_pitch_indirect::
jp (hl)
; A:HL is a modulo24 accumulator; DE stays the original word. B, when used,
; is its sign extension. ADD/ADC and SBC/SBC include low-word carry/borrow.
; Intermediate wrap is harmless: every final book gain*word fits signed24,
; so the final A:HL bits are the exact signed24 product consumed by the sum.
; Constant -50: chain sequence; no data-dependent branches.
.globl _pitch_const_m50
_pitch_const_m50::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -39: chain sequence; no data-dependent branches.
.globl _pitch_const_m39
_pitch_const_m39::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -34: chain sequence; no data-dependent branches.
.globl _pitch_const_m34
_pitch_const_m34::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -31: chain sequence; no data-dependent branches.
.globl _pitch_const_m31
_pitch_const_m31::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -26: chain sequence; no data-dependent branches.
.globl _pitch_const_m26
_pitch_const_m26::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -24: chain sequence; no data-dependent branches.
.globl _pitch_const_m24
_pitch_const_m24::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -23: chain sequence; no data-dependent branches.
.globl _pitch_const_m23
_pitch_const_m23::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -21: chain sequence; no data-dependent branches.
.globl _pitch_const_m21
_pitch_const_m21::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -19: chain sequence; no data-dependent branches.
.globl _pitch_const_m19
_pitch_const_m19::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -18: chain sequence; no data-dependent branches.
.globl _pitch_const_m18
_pitch_const_m18::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -16: chain sequence; no data-dependent branches.
.globl _pitch_const_m16
_pitch_const_m16::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -15: chain sequence; no data-dependent branches.
.globl _pitch_const_m15
_pitch_const_m15::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -14: chain sequence; no data-dependent branches.
.globl _pitch_const_m14
_pitch_const_m14::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -13: chain sequence; no data-dependent branches.
.globl _pitch_const_m13
_pitch_const_m13::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -12: chain sequence; no data-dependent branches.
.globl _pitch_const_m12
_pitch_const_m12::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -11: chain sequence; no data-dependent branches.
.globl _pitch_const_m11
_pitch_const_m11::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -10: chain sequence; no data-dependent branches.
.globl _pitch_const_m10
_pitch_const_m10::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -9: chain sequence; no data-dependent branches.
.globl _pitch_const_m9
_pitch_const_m9::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -8: chain sequence; no data-dependent branches.
.globl _pitch_const_m8
_pitch_const_m8::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -7: chain sequence; no data-dependent branches.
.globl _pitch_const_m7
_pitch_const_m7::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -6: chain sequence; no data-dependent branches.
.globl _pitch_const_m6
_pitch_const_m6::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -5: chain sequence; no data-dependent branches.
.globl _pitch_const_m5
_pitch_const_m5::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -2: chain sequence; no data-dependent branches.
.globl _pitch_const_m2
_pitch_const_m2::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant -1: chain sequence; no data-dependent branches.
.globl _pitch_const_m1
_pitch_const_m1::
ld a,d
add a,a
sbc a,a
ld b,a
; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 0: chain sequence; no data-dependent branches.
.globl _pitch_const_0
_pitch_const_0::
xor a,a
ld h,a
ld l,a
ret
; Constant 1: chain sequence; no data-dependent branches.
.globl _pitch_const_1
_pitch_const_1::
ld a,d
add a,a
sbc a,a
ex de,hl
ret
; Constant 3: chain sequence; no data-dependent branches.
.globl _pitch_const_3
_pitch_const_3::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 4: chain sequence; no data-dependent branches.
.globl _pitch_const_4
_pitch_const_4::
ld a,d
add a,a
sbc a,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 5: chain sequence; no data-dependent branches.
.globl _pitch_const_5
_pitch_const_5::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 8: chain sequence; no data-dependent branches.
.globl _pitch_const_8
_pitch_const_8::
ld a,d
add a,a
sbc a,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 9: chain sequence; no data-dependent branches.
.globl _pitch_const_9
_pitch_const_9::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 10: chain sequence; no data-dependent branches.
.globl _pitch_const_10
_pitch_const_10::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 11: chain sequence; no data-dependent branches.
.globl _pitch_const_11
_pitch_const_11::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 13: chain sequence; no data-dependent branches.
.globl _pitch_const_13
_pitch_const_13::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 15: chain sequence; no data-dependent branches.
.globl _pitch_const_15
_pitch_const_15::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 16: chain sequence; no data-dependent branches.
.globl _pitch_const_16
_pitch_const_16::
ld a,d
add a,a
sbc a,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 17: chain sequence; no data-dependent branches.
.globl _pitch_const_17
_pitch_const_17::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 18: chain sequence; no data-dependent branches.
.globl _pitch_const_18
_pitch_const_18::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 19: chain sequence; no data-dependent branches.
.globl _pitch_const_19
_pitch_const_19::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 20: chain sequence; no data-dependent branches.
.globl _pitch_const_20
_pitch_const_20::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 22: chain sequence; no data-dependent branches.
.globl _pitch_const_22
_pitch_const_22::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 23: chain sequence; no data-dependent branches.
.globl _pitch_const_23
_pitch_const_23::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 24: chain sequence; no data-dependent branches.
.globl _pitch_const_24
_pitch_const_24::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 27: chain sequence; no data-dependent branches.
.globl _pitch_const_27
_pitch_const_27::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 28: chain sequence; no data-dependent branches.
.globl _pitch_const_28
_pitch_const_28::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 31: chain sequence; no data-dependent branches.
.globl _pitch_const_31
_pitch_const_31::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 32: chain sequence; no data-dependent branches.
.globl _pitch_const_32
_pitch_const_32::
ld a,d
add a,a
sbc a,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 33: chain sequence; no data-dependent branches.
.globl _pitch_const_33
_pitch_const_33::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 34: chain sequence; no data-dependent branches.
.globl _pitch_const_34
_pitch_const_34::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 35: chain sequence; no data-dependent branches.
.globl _pitch_const_35
_pitch_const_35::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 36: chain sequence; no data-dependent branches.
.globl _pitch_const_36
_pitch_const_36::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 37: chain sequence; no data-dependent branches.
.globl _pitch_const_37
_pitch_const_37::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 38: chain sequence; no data-dependent branches.
.globl _pitch_const_38
_pitch_const_38::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 44: chain sequence; no data-dependent branches.
.globl _pitch_const_44
_pitch_const_44::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 45: chain sequence; no data-dependent branches.
.globl _pitch_const_45
_pitch_const_45::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 46: chain sequence; no data-dependent branches.
.globl _pitch_const_46
_pitch_const_46::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 47: chain sequence; no data-dependent branches.
.globl _pitch_const_47
_pitch_const_47::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 53: chain sequence; no data-dependent branches.
.globl _pitch_const_53
_pitch_const_53::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 57: chain sequence; no data-dependent branches.
.globl _pitch_const_57
_pitch_const_57::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 60: chain sequence; no data-dependent branches.
.globl _pitch_const_60
_pitch_const_60::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 61: chain sequence; no data-dependent branches.
.globl _pitch_const_61
_pitch_const_61::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
or a,a
sbc hl,de
sbc a,b
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 65: chain sequence; no data-dependent branches.
.globl _pitch_const_65
_pitch_const_65::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 70: chain sequence; no data-dependent branches.
.globl _pitch_const_70
_pitch_const_70::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 89: chain sequence; no data-dependent branches.
.globl _pitch_const_89
_pitch_const_89::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret
; Constant 97: chain sequence; no data-dependent branches.
.globl _pitch_const_97
_pitch_const_97::
ld a,d
add a,a
sbc a,a
ld b,a
ld h,d
ld l,e
add hl,hl
rla
add hl,de
adc a,b
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,hl
rla
add hl,de
adc a,b
; Leave A:HL directly for modulo24 accumulation; no signed32 conversion.
ret

; Private LPC entry: return -MULT16_32_Q14(a,b) modulo32 in HL:DE.
; Input HL=signed16 a, DE=pointer to signed32 b. Preserve the original
; hi=int16(b>>14) truncation and lo=b&16383, even when hi wraps.
; For a>=0 return -a*hi-floor(a*lo/16384). For a<0 return
; |a|*hi+ceil(|a|*lo/16384). Do not negate the signed16 coefficient:
; its -32768 magnitude and the floor/ceiling distinction must remain exact.
; Preserve IX/IY, all alternate registers and caller SP. Clobber ordinary
; AF/BC/DE/HL and the existing qcoef/qarg/qtemp scratch (10 bytes).
; Nonreentrant like mulq14; the ordinary public Q14 entry remains unchanged.
.globl _q14_negated
_q14_negated::
bit 7,h
jp nz,q37_negative
; a>=0: restore the opposite of hi's sign, then subtract the low floor.
ld (qcoef),hl
; Read the two little-endian words directly: only the low word must
; survive the first product. Keep the high word in HL for hi extraction.
; INC HL crosses page boundaries and wraps at FFFF exactly as LDIR did.
; The argument must not alias Q14 scratch/stack (the LPC caller uses its
; polynomial array). qarg+2/+3 are now unused and are never written here.
ex de,hl
ld e,(hl)
inc hl
ld d,(hl)
inc hl
ld (qarg),de
ld e,(hl)
inc hl
ld d,(hl)
ex de,hl
add hl,hl
add hl,hl
ld a,(qarg+1)
rlca
rlca
and a,#3
or a,l
ld l,a
ld de,(qcoef)
bit 7,h
jr z,q37_positive_high_positive
xor a,a
sub a,l
ld l,a
sbc a,a
sub a,h
ld h,a
call _q14_unsigned
jp q37_positive_high_ready
q37_positive_high_positive:
call _q14_unsigned
call neg32
q37_positive_high_ready:
ld (qtemp),de
ld (qtemp+2),hl
ld hl,(qarg)
ld a,h
and a,#63
ld h,a
ld de,(qcoef)
call _q14_unsigned
; Extract Q=floor(|a|*lo/16384) into HL. DE retains the original low word
; for the exact remainder test. P<2^29 and Q fits a nonnegative signed16.
add hl,hl
add hl,hl
ld a,d
rlca
rlca
and a,#3
or a,l
ld l,a
; Signed32 high - unsigned Q. Clear carry for floor, then propagate the
; low-word borrow into the upper word. LD and EX preserve that borrow.
ld b,h
ld c,l
ld hl,(qtemp)
or a,a
sbc hl,bc
ex de,hl
ld hl,(qtemp+2)
ld bc,#0
sbc hl,bc
ret
q37_negative:
; a<0: keep |a| as unsigned16 (including 32768). Restore hi's own sign.
xor a,a
sub a,l
ld l,a
sbc a,a
sub a,h
ld h,a
ld (qcoef),hl
; Read the two little-endian words directly: only the low word must
; survive the first product. Keep the high word in HL for hi extraction.
; INC HL crosses page boundaries and wraps at FFFF exactly as LDIR did.
; The argument must not alias Q14 scratch/stack (the LPC caller uses its
; polynomial array). qarg+2/+3 are now unused and are never written here.
ex de,hl
ld e,(hl)
inc hl
ld d,(hl)
inc hl
ld (qarg),de
ld e,(hl)
inc hl
ld d,(hl)
ex de,hl
add hl,hl
add hl,hl
ld a,(qarg+1)
rlca
rlca
and a,#3
or a,l
ld l,a
ld de,(qcoef)
bit 7,h
jr nz,q37_negative_high_negative
call _q14_unsigned
jp q37_negative_high_ready
q37_negative_high_negative:
xor a,a
sub a,l
ld l,a
sbc a,a
sub a,h
ld h,a
call _q14_unsigned
call neg32
q37_negative_high_ready:
ld (qtemp),de
ld (qtemp+2),hl
ld hl,(qarg)
ld a,h
and a,#63
ld h,a
ld de,(qcoef)
call _q14_unsigned
; Extract Q=floor(|a|*lo/16384) into HL. DE retains the original low word
; for the exact remainder test. P<2^29 and Q fits a nonnegative signed16.
add hl,hl
add hl,hl
ld a,d
rlca
rlca
and a,#3
or a,l
ld l,a
; Add ceil(P/16384): carry is one exactly when the discarded 14 bits
; are nonzero. ADC includes it in Q; propagate low-word overflow upward.
ld a,d
and a,#63
or a,e
add a,#255
ld de,(qtemp)
adc hl,de
ex de,hl
ld hl,(qtemp+2)
jr nc,q37_negative_return
inc hl
q37_negative_return:
ret


.area _TABLES (ABS)
.org 0x4000
cos_table:
; Exact cos_int(4*i), i=0..3217; 6436 bytes, no packed-delta table.
.db 0,32,0,32,0,32,0,32,0,32,0,32,0,32,0,32
.db 0,32,0,32,0,32,0,32,0,32,0,32,0,32,0,32
.db 0,32,0,32,0,32,0,32,0,32,0,32,0,32,0,32
.db 0,32,0,32,0,32,0,32,255,31,255,31,255,31,255,31
.db 255,31,255,31,255,31,255,31,255,31,255,31,255,31,255,31
.db 255,31,255,31,255,31,254,31,254,31,254,31,254,31,254,31
.db 254,31,254,31,254,31,254,31,254,31,254,31,253,31,253,31
.db 253,31,253,31,253,31,253,31,253,31,253,31,252,31,252,31
.db 252,31,252,31,252,31,252,31,252,31,252,31,251,31,251,31
.db 251,31,251,31,251,31,251,31,251,31,250,31,250,31,250,31
.db 250,31,250,31,250,31,250,31,249,31,249,31,249,31,249,31
.db 249,31,249,31,248,31,248,31,248,31,248,31,248,31,247,31
.db 247,31,247,31,247,31,247,31,246,31,246,31,246,31,246,31
.db 246,31,245,31,245,31,245,31,245,31,245,31,244,31,244,31
.db 244,31,244,31,244,31,243,31,243,31,243,31,243,31,242,31
.db 242,31,242,31,242,31,241,31,241,31,241,31,241,31,240,31
.db 240,31,240,31,240,31,239,31,239,31,239,31,239,31,238,31
.db 238,31,238,31,238,31,237,31,237,31,237,31,237,31,236,31
.db 236,31,236,31,235,31,235,31,235,31,235,31,234,31,234,31
.db 234,31,233,31,233,31,233,31,232,31,232,31,232,31,232,31
.db 231,31,231,31,231,31,230,31,230,31,230,31,229,31,229,31
.db 229,31,228,31,228,31,228,31,227,31,227,31,227,31,226,31
.db 226,31,226,31,225,31,225,31,225,31,224,31,224,31,224,31
.db 223,31,223,31,222,31,222,31,222,31,221,31,221,31,221,31
.db 220,31,220,31,219,31,219,31,219,31,218,31,218,31,218,31
.db 217,31,217,31,216,31,216,31,216,31,215,31,215,31,214,31
.db 214,31,214,31,213,31,213,31,212,31,212,31,212,31,211,31
.db 211,31,210,31,210,31,209,31,209,31,209,31,208,31,208,31
.db 207,31,207,31,206,31,206,31,205,31,205,31,205,31,204,31
.db 204,31,203,31,203,31,202,31,202,31,201,31,201,31,200,31
.db 200,31,200,31,199,31,199,31,198,31,198,31,197,31,197,31
.db 196,31,196,31,195,31,195,31,194,31,194,31,193,31,193,31
.db 192,31,192,31,191,31,191,31,190,31,190,31,189,31,189,31
.db 188,31,188,31,187,31,187,31,186,31,186,31,185,31,185,31
.db 184,31,183,31,183,31,182,31,182,31,181,31,181,31,180,31
.db 180,31,179,31,179,31,178,31,177,31,177,31,176,31,176,31
.db 175,31,175,31,174,31,174,31,173,31,172,31,172,31,171,31
.db 171,31,170,31,170,31,169,31,168,31,168,31,167,31,167,31
.db 166,31,165,31,165,31,164,31,164,31,163,31,162,31,162,31
.db 161,31,161,31,160,31,159,31,159,31,158,31,157,31,157,31
.db 156,31,156,31,155,31,154,31,154,31,153,31,152,31,152,31
.db 151,31,151,31,150,31,149,31,149,31,148,31,147,31,147,31
.db 146,31,145,31,145,31,144,31,143,31,143,31,142,31,141,31
.db 141,31,140,31,139,31,139,31,138,31,137,31,137,31,136,31
.db 135,31,135,31,134,31,133,31,132,31,132,31,131,31,130,31
.db 130,31,129,31,128,31,128,31,127,31,126,31,125,31,125,31
.db 124,31,123,31,123,31,122,31,121,31,120,31,120,31,119,31
.db 118,31,117,31,117,31,116,31,115,31,114,31,114,31,113,31
.db 112,31,111,31,111,31,110,31,109,31,108,31,108,31,107,31
.db 106,31,105,31,105,31,104,31,103,31,102,31,102,31,101,31
.db 100,31,99,31,99,31,98,31,97,31,97,31,96,31,95,31
.db 94,31,93,31,93,31,92,31,91,31,90,31,89,31,89,31
.db 88,31,87,31,86,31,85,31,84,31,84,31,83,31,82,31
.db 81,31,80,31,80,31,79,31,78,31,77,31,76,31,75,31
.db 74,31,74,31,73,31,72,31,71,31,70,31,69,31,69,31
.db 68,31,67,31,66,31,65,31,64,31,63,31,62,31,62,31
.db 61,31,60,31,59,31,58,31,57,31,56,31,55,31,55,31
.db 54,31,53,31,52,31,51,31,50,31,49,31,48,31,47,31
.db 46,31,46,31,45,31,44,31,43,31,42,31,41,31,40,31
.db 39,31,38,31,37,31,36,31,35,31,35,31,34,31,33,31
.db 32,31,31,31,30,31,29,31,28,31,28,31,27,31,26,31
.db 25,31,24,31,23,31,22,31,21,31,20,31,19,31,18,31
.db 17,31,16,31,15,31,14,31,13,31,12,31,11,31,10,31
.db 9,31,8,31,7,31,6,31,5,31,4,31,3,31,2,31
.db 1,31,0,31,255,30,254,30,253,30,252,30,251,30,250,30
.db 249,30,248,30,247,30,246,30,245,30,244,30,243,30,242,30
.db 241,30,240,30,239,30,238,30,237,30,236,30,235,30,234,30
.db 233,30,232,30,231,30,230,30,229,30,228,30,227,30,226,30
.db 225,30,224,30,223,30,222,30,220,30,219,30,218,30,217,30
.db 216,30,215,30,214,30,213,30,212,30,211,30,210,30,209,30
.db 207,30,206,30,205,30,204,30,203,30,202,30,201,30,200,30
.db 199,30,198,30,197,30,196,30,195,30,194,30,192,30,191,30
.db 190,30,189,30,188,30,187,30,186,30,185,30,183,30,182,30
.db 181,30,180,30,179,30,178,30,177,30,175,30,174,30,173,30
.db 172,30,171,30,170,30,169,30,167,30,166,30,165,30,164,30
.db 163,30,162,30,161,30,160,30,158,30,157,30,156,30,155,30
.db 154,30,153,30,151,30,150,30,149,30,148,30,147,30,145,30
.db 144,30,143,30,142,30,141,30,139,30,138,30,137,30,136,30
.db 134,30,133,30,132,30,131,30,130,30,129,30,128,30,126,30
.db 125,30,124,30,123,30,121,30,120,30,119,30,118,30,116,30
.db 115,30,114,30,113,30,111,30,110,30,109,30,108,30,106,30
.db 105,30,104,30,103,30,101,30,100,30,99,30,98,30,97,30
.db 95,30,94,30,93,30,92,30,90,30,89,30,88,30,86,30
.db 85,30,84,30,83,30,81,30,80,30,79,30,77,30,76,30
.db 75,30,73,30,73,30,71,30,70,30,69,30,67,30,66,30
.db 65,30,63,30,62,30,61,30,59,30,58,30,57,30,55,30
.db 54,30,53,30,51,30,50,30,49,30,47,30,46,30,45,30
.db 44,30,42,30,41,30,40,30,38,30,37,30,35,30,34,30
.db 33,30,31,30,30,30,29,30,27,30,26,30,24,30,23,30
.db 22,30,20,30,19,30,18,30,17,30,15,30,14,30,12,30
.db 11,30,10,30,8,30,7,30,5,30,4,30,3,30,1,30
.db 0,30,254,29,253,29,251,29,250,29,249,29,248,29,246,29
.db 245,29,243,29,242,29,240,29,239,29,238,29,236,29,235,29
.db 233,29,232,29,230,29,229,29,228,29,226,29,225,29,223,29
.db 222,29,221,29,219,29,218,29,216,29,215,29,213,29,212,29
.db 210,29,209,29,208,29,206,29,205,29,203,29,202,29,200,29
.db 199,29,197,29,196,29,194,29,193,29,191,29,190,29,189,29
.db 187,29,186,29,184,29,183,29,181,29,180,29,178,29,177,29
.db 175,29,173,29,172,29,170,29,169,29,167,29,166,29,165,29
.db 163,29,162,29,160,29,159,29,157,29,155,29,154,29,152,29
.db 151,29,149,29,148,29,146,29,145,29,143,29,142,29,140,29
.db 139,29,137,29,136,29,134,29,132,29,131,29,129,29,128,29
.db 126,29,125,29,123,29,122,29,120,29,119,29,117,29,115,29
.db 114,29,112,29,110,29,109,29,107,29,106,29,104,29,103,29
.db 101,29,100,29,98,29,96,29,95,29,93,29,92,29,90,29
.db 89,29,87,29,85,29,84,29,82,29,80,29,79,29,77,29
.db 75,29,74,29,72,29,71,29,69,29,68,29,66,29,64,29
.db 63,29,61,29,59,29,58,29,56,29,55,29,53,29,51,29
.db 50,29,48,29,46,29,45,29,43,29,41,29,40,29,38,29
.db 37,29,35,29,33,29,32,29,30,29,28,29,26,29,25,29
.db 23,29,22,29,20,29,18,29,17,29,15,29,13,29,11,29
.db 10,29,8,29,7,29,5,29,3,29,1,29,0,29,254,28
.db 252,28,250,28,249,28,247,28,246,28,244,28,242,28,240,28
.db 239,28,237,28,235,28,233,28,232,28,230,28,229,28,227,28
.db 225,28,223,28,221,28,220,28,218,28,217,28,215,28,213,28
.db 211,28,209,28,208,28,206,28,204,28,203,28,201,28,199,28
.db 197,28,195,28,194,28,192,28,190,28,189,28,187,28,185,28
.db 183,28,181,28,180,28,178,28,176,28,174,28,173,28,171,28
.db 169,28,167,28,165,28,163,28,162,28,160,28,158,28,157,28
.db 155,28,153,28,151,28,149,28,148,28,146,28,144,28,142,28
.db 140,28,138,28,137,28,135,28,133,28,131,28,129,28,128,28
.db 126,28,124,28,122,28,121,28,119,28,117,28,115,28,113,28
.db 111,28,110,28,108,28,106,28,104,28,102,28,100,28,98,28
.db 97,28,95,28,93,28,91,28,89,28,87,28,85,28,83,28
.db 82,28,80,28,78,28,76,28,74,28,72,28,70,28,69,28
.db 67,28,65,28,63,28,61,28,59,28,57,28,55,28,53,28
.db 51,28,50,28,48,28,46,28,44,28,42,28,40,28,38,28
.db 36,28,34,28,33,28,31,28,29,28,27,28,25,28,23,28
.db 21,28,19,28,17,28,15,28,13,28,11,28,9,28,8,28
.db 6,28,4,28,2,28,0,28,254,27,252,27,250,27,248,27
.db 246,27,244,27,242,27,240,27,238,27,236,27,234,27,232,27
.db 231,27,229,27,227,27,225,27,222,27,221,27,219,27,217,27
.db 215,27,213,27,211,27,209,27,207,27,205,27,203,27,201,27
.db 199,27,197,27,195,27,193,27,191,27,189,27,187,27,185,27
.db 183,27,181,27,179,27,177,27,175,27,173,27,171,27,169,27
.db 167,27,165,27,163,27,161,27,159,27,157,27,155,27,153,27
.db 151,27,149,27,146,27,145,27,143,27,141,27,138,27,136,27
.db 135,27,133,27,130,27,128,27,126,27,124,27,122,27,120,27
.db 118,27,116,27,114,27,112,27,110,27,108,27,106,27,104,27
.db 102,27,100,27,98,27,96,27,93,27,91,27,89,27,87,27
.db 85,27,83,27,81,27,79,27,77,27,75,27,73,27,70,27
.db 68,27,66,27,64,27,62,27,60,27,58,27,56,27,54,27
.db 52,27,50,27,48,27,45,27,43,27,41,27,39,27,37,27
.db 35,27,32,27,31,27,28,27,26,27,24,27,22,27,19,27
.db 18,27,15,27,13,27,11,27,9,27,7,27,5,27,3,27
.db 1,27,254,26,252,26,250,26,248,26,246,26,244,26,241,26
.db 239,26,237,26,235,26,233,26,231,26,229,26,226,26,224,26
.db 222,26,220,26,218,26,216,26,213,26,211,26,209,26,207,26
.db 205,26,202,26,200,26,198,26,196,26,194,26,191,26,190,26
.db 187,26,185,26,183,26,181,26,178,26,176,26,174,26,172,26
.db 169,26,167,26,165,26,163,26,161,26,159,26,156,26,154,26
.db 152,26,149,26,147,26,145,26,143,26,140,26,138,26,136,26
.db 134,26,132,26,129,26,127,26,125,26,122,26,120,26,118,26
.db 116,26,113,26,111,26,109,26,107,26,105,26,102,26,100,26
.db 98,26,96,26,93,26,91,26,88,26,86,26,84,26,82,26
.db 80,26,77,26,75,26,73,26,70,26,68,26,66,26,64,26
.db 61,26,59,26,57,26,54,26,52,26,50,26,48,26,45,26
.db 43,26,41,26,38,26,36,26,34,26,31,26,29,26,27,26
.db 24,26,22,26,20,26,18,26,15,26,13,26,11,26,8,26
.db 6,26,4,26,1,26,255,25,252,25,250,25,248,25,246,25
.db 243,25,241,25,239,25,236,25,234,25,231,25,229,25,227,25
.db 225,25,222,25,220,25,218,25,215,25,213,25,210,25,208,25
.db 206,25,203,25,201,25,198,25,196,25,194,25,191,25,189,25
.db 187,25,184,25,182,25,180,25,177,25,174,25,172,25,170,25
.db 168,25,165,25,163,25,161,25,158,25,155,25,153,25,151,25
.db 149,25,146,25,144,25,141,25,139,25,137,25,134,25,132,25
.db 129,25,127,25,124,25,122,25,120,25,117,25,115,25,112,25
.db 110,25,107,25,105,25,103,25,100,25,98,25,95,25,92,25
.db 90,25,88,25,85,25,83,25,81,25,78,25,75,25,73,25
.db 71,25,69,25,66,25,63,25,61,25,58,25,56,25,54,25
.db 51,25,48,25,46,25,44,25,41,25,39,25,36,25,34,25
.db 31,25,29,25,26,25,24,25,21,25,19,25,16,25,14,25
.db 11,25,9,25,6,25,4,25,1,25,255,24,253,24,250,24
.db 247,24,244,24,242,24,240,24,237,24,235,24,232,24,230,24
.db 227,24,225,24,222,24,219,24,217,24,215,24,212,24,209,24
.db 207,24,204,24,202,24,199,24,197,24,194,24,192,24,189,24
.db 187,24,184,24,182,24,179,24,177,24,174,24,172,24,169,24
.db 166,24,164,24,162,24,159,24,156,24,154,24,151,24,149,24
.db 146,24,143,24,141,24,139,24,136,24,133,24,130,24,128,24
.db 126,24,123,24,120,24,118,24,115,24,113,24,110,24,107,24
.db 105,24,102,24,100,24,97,24,95,24,92,24,89,24,87,24
.db 84,24,82,24,79,24,76,24,73,24,72,24,69,24,66,24
.db 63,24,61,24,58,24,55,24,53,24,50,24,48,24,45,24
.db 42,24,40,24,37,24,35,24,32,24,29,24,27,24,24,24
.db 21,24,18,24,16,24,14,24,11,24,8,24,5,24,3,24
.db 0,24,254,23,251,23,249,23,246,23,243,23,240,23,238,23
.db 235,23,233,23,230,23,227,23,224,23,222,23,219,23,217,23
.db 214,23,211,23,208,23,205,23,203,23,201,23,198,23,195,23
.db 193,23,190,23,187,23,184,23,182,23,179,23,176,23,174,23
.db 171,23,168,23,166,23,163,23,160,23,157,23,155,23,152,23
.db 149,23,146,23,144,23,141,23,138,23,136,23,133,23,130,23
.db 128,23,125,23,122,23,120,23,117,23,114,23,111,23,109,23
.db 106,23,103,23,100,23,98,23,95,23,92,23,89,23,87,23
.db 84,23,81,23,78,23,76,23,73,23,70,23,67,23,65,23
.db 62,23,59,23,56,23,54,23,51,23,48,23,45,23,43,23
.db 40,23,37,23,34,23,32,23,29,23,26,23,23,23,21,23
.db 18,23,15,23,12,23,10,23,7,23,4,23,1,23,255,22
.db 252,22,249,22,246,22,243,22,240,22,238,22,235,22,232,22
.db 229,22,226,22,223,22,221,22,218,22,215,22,212,22,210,22
.db 207,22,204,22,201,22,199,22,196,22,193,22,190,22,187,22
.db 185,22,182,22,178,22,176,22,173,22,170,22,167,22,165,22
.db 162,22,159,22,156,22,154,22,151,22,147,22,145,22,142,22
.db 139,22,136,22,133,22,131,22,128,22,125,22,122,22,119,22
.db 117,22,114,22,111,22,108,22,105,22,102,22,100,22,96,22
.db 94,22,91,22,88,22,85,22,82,22,79,22,77,22,74,22
.db 71,22,67,22,65,22,62,22,59,22,56,22,54,22,51,22
.db 47,22,45,22,42,22,39,22,36,22,33,22,30,22,27,22
.db 25,22,21,22,18,22,16,22,13,22,10,22,7,22,4,22
.db 1,22,254,21,251,21,248,21,246,21,242,21,239,21,237,21
.db 234,21,231,21,228,21,225,21,222,21,219,21,217,21,214,21
.db 210,21,207,21,205,21,202,21,199,21,196,21,193,21,190,21
.db 187,21,184,21,182,21,178,21,175,21,173,21,169,21,167,21
.db 163,21,161,21,158,21,155,21,151,21,149,21,146,21,143,21
.db 140,21,137,21,134,21,131,21,128,21,126,21,122,21,119,21
.db 116,21,114,21,110,21,108,21,105,21,101,21,98,21,96,21
.db 93,21,89,21,86,21,84,21,81,21,77,21,75,21,72,21
.db 69,21,65,21,63,21,60,21,57,21,53,21,51,21,48,21
.db 45,21,42,21,39,21,36,21,33,21,30,21,27,21,24,21
.db 20,21,18,21,15,21,12,21,9,21,6,21,3,21,0,21
.db 253,20,250,20,246,20,244,20,241,20,238,20,235,20,232,20
.db 229,20,225,20,222,20,220,20,216,20,213,20,211,20,208,20
.db 204,20,201,20,198,20,195,20,192,20,189,20,185,20,182,20
.db 180,20,177,20,173,20,170,20,168,20,164,20,161,20,158,20
.db 155,20,152,20,149,20,146,20,143,20,140,20,137,20,134,20
.db 130,20,127,20,125,20,121,20,118,20,116,20,112,20,109,20
.db 106,20,103,20,100,20,97,20,94,20,91,20,88,20,84,20
.db 81,20,78,20,75,20,72,20,69,20,66,20,62,20,60,20
.db 57,20,53,20,51,20,48,20,44,20,41,20,38,20,35,20
.db 32,20,29,20,26,20,23,20,20,20,16,20,13,20,10,20
.db 7,20,4,20,1,20,254,19,251,19,247,19,244,19,242,19
.db 238,19,235,19,232,19,229,19,226,19,222,19,219,19,216,19
.db 213,19,210,19,207,19,203,19,200,19,198,19,194,19,191,19
.db 188,19,185,19,181,19,179,19,176,19,172,19,169,19,166,19
.db 163,19,160,19,157,19,153,19,150,19,147,19,144,19,141,19
.db 137,19,135,19,131,19,128,19,125,19,122,19,119,19,115,19
.db 112,19,109,19,105,19,103,19,99,19,96,19,94,19,90,19
.db 87,19,83,19,80,19,76,19,74,19,70,19,67,19,63,19
.db 61,19,57,19,54,19,52,19,48,19,45,19,42,19,38,19
.db 35,19,31,19,29,19,25,19,22,19,19,19,16,19,12,19
.db 9,19,6,19,3,19,255,18,253,18,249,18,246,18,243,18
.db 240,18,236,18,234,18,230,18,227,18,223,18,221,18,217,18
.db 214,18,211,18,208,18,204,18,202,18,198,18,195,18,191,18
.db 188,18,185,18,181,18,179,18,175,18,172,18,169,18,165,18
.db 162,18,159,18,156,18,152,18,149,18,146,18,142,18,139,18
.db 136,18,133,18,129,18,127,18,123,18,120,18,117,18,114,18
.db 110,18,106,18,104,18,100,18,97,18,94,18,91,18,87,18
.db 84,18,81,18,77,18,74,18,71,18,67,18,65,18,61,18
.db 58,18,54,18,51,18,48,18,44,18,42,18,38,18,35,18
.db 32,18,28,18,24,18,22,18,18,18,15,18,12,18,9,18
.db 5,18,1,18,255,17,251,17,248,17,244,17,240,17,237,17
.db 234,17,231,17,227,17,224,17,221,17,217,17,215,17,211,17
.db 207,17,205,17,201,17,197,17,194,17,191,17,187,17,184,17
.db 181,17,177,17,174,17,171,17,167,17,164,17,161,17,158,17
.db 154,17,151,17,148,17,144,17,141,17,138,17,134,17,131,17
.db 127,17,124,17,121,17,118,17,114,17,110,17,108,17,104,17
.db 100,17,98,17,94,17,90,17,88,17,84,17,80,17,78,17
.db 74,17,70,17,68,17,64,17,60,17,58,17,54,17,50,17
.db 48,17,44,17,40,17,38,17,34,17,30,17,28,17,24,17
.db 20,17,17,17,13,17,10,17,6,17,3,17,0,17,252,16
.db 249,16,246,16,242,16,239,16,235,16,232,16,229,16,225,16
.db 222,16,219,16,215,16,212,16,209,16,205,16,201,16,199,16
.db 195,16,191,16,189,16,185,16,181,16,178,16,175,16,171,16
.db 168,16,164,16,161,16,157,16,153,16,150,16,147,16,143,16
.db 139,16,137,16,133,16,129,16,126,16,123,16,118,16,116,16
.db 112,16,109,16,106,16,102,16,98,16,96,16,91,16,88,16
.db 85,16,82,16,77,16,75,16,71,16,67,16,65,16,61,16
.db 57,16,54,16,51,16,47,16,44,16,40,16,37,16,34,16
.db 30,16,26,16,23,16,20,16,15,16,13,16,9,16,5,16
.db 3,16,255,15,251,15,248,15,244,15,241,15,238,15,234,15
.db 230,15,227,15,224,15,220,15,217,15,213,15,209,15,207,15
.db 203,15,199,15,196,15,192,15,189,15,186,15,182,15,178,15
.db 176,15,171,15,168,15,165,15,161,15,157,15,155,15,150,15
.db 147,15,144,15,140,15,136,15,134,15,130,15,126,15,123,15
.db 119,15,116,15,113,15,109,15,106,15,102,15,98,15,95,15
.db 91,15,88,15,85,15,81,15,77,15,72,15,69,15,65,15
.db 62,15,59,15,55,15,52,15,48,15,44,15,42,15,38,15
.db 34,15,31,15,27,15,23,15,20,15,17,15,13,15,10,15
.db 6,15,2,15,0,15,251,14,247,14,245,14,241,14,237,14
.db 234,14,230,14,226,14,223,14,220,14,217,14,213,14,209,14
.db 206,14,202,14,198,14,196,14,192,14,188,14,185,14,181,14
.db 177,14,174,14,170,14,166,14,164,14,159,14,157,14,153,14
.db 149,14,146,14,142,14,138,14,136,14,131,14,127,14,125,14
.db 120,14,117,14,114,14,110,14,106,14,103,14,99,14,95,14
.db 93,14,88,14,86,14,82,14,78,14,75,14,71,14,67,14
.db 64,14,60,14,56,14,53,14,49,14,46,14,43,14,39,14
.db 36,14,32,14,28,14,25,14,21,14,17,14,14,14,10,14
.db 6,14,4,14,254,13,250,13,248,13,243,13,239,13,237,13
.db 233,13,229,13,226,13,222,13,218,13,215,13,211,13,208,13
.db 204,13,200,13,197,13,193,13,189,13,186,13,182,13,178,13
.db 175,13,171,13,167,13,165,13,161,13,158,13,154,13,150,13
.db 146,13,142,13,138,13,136,13,132,13,128,13,125,13,121,13
.db 118,13,114,13,110,13,107,13,103,13,99,13,96,13,92,13
.db 88,13,85,13,81,13,78,13,74,13,70,13,67,13,63,13
.db 59,13,56,13,52,13,48,13,45,13,41,13,38,13,34,13
.db 30,13,27,13,23,13,19,13,17,13,12,13,8,13,5,13
.db 1,13,255,12,250,12,246,12,243,12,239,12,235,12,232,12
.db 228,12,226,12,221,12,217,12,214,12,210,12,206,12,203,12
.db 199,12,195,12,192,12,188,12,183,12,180,12,176,12,172,12
.db 168,12,164,12,160,12,158,12,153,12,151,12,147,12,142,12
.db 140,12,136,12,131,12,128,12,124,12,121,12,117,12,113,12
.db 110,12,106,12,102,12,99,12,95,12,92,12,88,12,84,12
.db 81,12,77,12,73,12,70,12,65,12,63,12,58,12,54,12
.db 51,12,47,12,43,12,40,12,36,12,33,12,29,12,25,12
.db 22,12,18,12,14,12,11,12,7,12,4,12,0,12,251,11
.db 249,11,244,11,240,11,237,11,233,11,230,11,226,11,222,11
.db 219,11,215,11,211,11,208,11,204,11,201,11,197,11,192,11
.db 189,11,185,11,182,11,178,11,174,11,171,11,167,11,163,11
.db 160,11,156,11,153,11,149,11,144,11,142,11,137,11,133,11
.db 130,11,126,11,123,11,117,11,113,11,109,11,106,11,102,11
.db 98,11,95,11,91,11,88,11,83,11,79,11,76,11,72,11
.db 69,11,65,11,61,11,58,11,54,11,49,11,46,11,42,11
.db 39,11,35,11,31,11,28,11,24,11,21,11,16,11,12,11
.db 9,11,5,11,2,11,254,10,250,10,247,10,242,10,238,10
.db 236,10,231,10,228,10,224,10,220,10,217,10,213,10,210,10
.db 205,10,201,10,198,10,194,10,191,10,187,10,183,10,180,10
.db 175,10,171,10,168,10,164,10,161,10,157,10,152,10,150,10
.db 145,10,142,10,138,10,134,10,131,10,127,10,124,10,119,10
.db 115,10,112,10,108,10,105,10,101,10,96,10,93,10,89,10
.db 86,10,82,10,78,10,75,10,71,10,66,10,60,10,57,10
.db 53,10,49,10,46,10,41,10,39,10,34,10,30,10,27,10
.db 23,10,20,10,15,10,11,10,8,10,4,10,1,10,253,9
.db 248,9,245,9,241,9,238,9,234,9,230,9,227,9,222,9
.db 219,9,215,9,210,9,208,9,203,9,200,9,196,9,192,9
.db 189,9,185,9,182,9,177,9,173,9,170,9,165,9,163,9
.db 158,9,154,9,151,9,147,9,144,9,139,9,135,9,132,9
.db 128,9,125,9,121,9,116,9,113,9,109,9,106,9,102,9
.db 97,9,94,9,90,9,87,9,83,9,78,9,75,9,71,9
.db 68,9,64,9,59,9,56,9,52,9,49,9,44,9,40,9
.db 37,9,33,9,30,9,25,9,23,9,18,9,14,9,8,9
.db 3,9,1,9,252,8,249,8,245,8,242,8,237,8,233,8
.db 230,8,226,8,223,8,218,8,214,8,211,8,207,8,204,8
.db 199,8,195,8,192,8,187,8,184,8,180,8,176,8,173,8
.db 168,8,166,8,161,8,157,8,153,8,149,8,146,8,142,8
.db 139,8,134,8,130,8,127,8,123,8,120,8,115,8,111,8
.db 108,8,103,8,101,8,96,8,92,8,89,8,84,8,81,8
.db 77,8,74,8,70,8,65,8,62,8,57,8,55,8,50,8
.db 46,8,43,8,38,8,35,8,31,8,28,8,24,8,19,8
.db 16,8,12,8,9,8,4,8,0,8,253,7,249,7,246,7
.db 241,7,237,7,234,7,229,7,226,7,222,7,216,7,211,7
.db 208,7,204,7,199,7,196,7,191,7,189,7,184,7,182,7
.db 177,7,172,7,170,7,165,7,162,7,158,7,153,7,150,7
.db 146,7,143,7,138,7,135,7,131,7,126,7,123,7,119,7
.db 116,7,111,7,109,7,104,7,99,7,97,7,92,7,89,7
.db 85,7,80,7,77,7,73,7,70,7,65,7,62,7,58,7
.db 53,7,50,7,45,7,43,7,38,7,35,7,31,7,26,7
.db 23,7,19,7,16,7,12,7,7,7,4,7,255,6,252,6
.db 248,6,245,6,240,6,236,6,233,6,228,6,226,6,221,6
.db 218,6,213,6,209,6,206,6,201,6,199,6,194,6,191,6
.db 187,6,182,6,175,6,171,6,168,6,163,6,161,6,156,6
.db 153,6,148,6,144,6,141,6,136,6,133,6,129,6,126,6
.db 121,6,117,6,114,6,109,6,106,6,102,6,99,6,94,6
.db 90,6,87,6,82,6,79,6,75,6,72,6,67,6,62,6
.db 60,6,55,6,52,6,47,6,45,6,40,6,35,6,33,6
.db 28,6,25,6,20,6,18,6,13,6,8,6,5,6,1,6
.db 254,5,249,5,246,5,241,5,239,5,234,5,229,5,227,5
.db 222,5,219,5,215,5,212,5,207,5,202,5,199,5,195,5
.db 192,5,187,5,185,5,180,5,177,5,172,5,167,5,165,5
.db 160,5,157,5,153,5,149,5,141,5,136,5,134,5,129,5
.db 126,5,121,5,118,5,114,5,111,5,106,5,101,5,99,5
.db 94,5,91,5,86,5,84,5,79,5,74,5,71,5,66,5
.db 64,5,59,5,56,5,51,5,49,5,44,5,39,5,36,5
.db 32,5,29,5,24,5,21,5,17,5,14,5,9,5,4,5
.db 1,5,253,4,250,4,245,4,242,4,238,4,235,4,230,4
.db 225,4,223,4,218,4,215,4,210,4,207,4,203,4,200,4
.db 195,4,190,4,187,4,183,4,180,4,175,4,173,4,167,4
.db 165,4,160,4,155,4,153,4,148,4,145,4,140,4,137,4
.db 132,4,130,4,125,4,120,4,118,4,108,4,106,4,101,4
.db 98,4,93,4,89,4,86,4,81,4,78,4,73,4,70,4
.db 66,4,63,4,58,4,55,4,51,4,46,4,43,4,38,4
.db 35,4,30,4,28,4,23,4,20,4,15,4,11,4,8,4
.db 3,4,0,4,251,3,249,3,244,3,241,3,236,3,233,3
.db 229,3,224,3,221,3,216,3,213,3,209,3,206,3,201,3
.db 198,3,193,3,189,3,186,3,181,3,178,3,173,3,171,3
.db 166,3,163,3,158,3,155,3,150,3,146,3,143,3,138,3
.db 135,3,130,3,128,3,123,3,120,3,115,3,112,3,108,3
.db 103,3,100,3,95,3,88,3,83,3,80,3,75,3,73,3
.db 68,3,63,3,60,3,55,3,53,3,48,3,45,3,40,3
.db 37,3,32,3,30,3,25,3,20,3,17,3,12,3,9,3
.db 4,3,2,3,253,2,250,2,245,2,243,2,238,2,235,2
.db 230,2,225,2,222,2,217,2,215,2,210,2,207,2,202,2
.db 200,2,195,2,192,2,187,2,184,2,180,2,175,2,172,2
.db 167,2,164,2,159,2,156,2,151,2,149,2,144,2,141,2
.db 136,2,134,2,129,2,124,2,121,2,116,2,113,2,108,2
.db 106,2,101,2,98,2,93,2,90,2,85,2,83,2,78,2
.db 75,2,66,2,61,2,58,2,53,2,50,2,45,2,43,2
.db 38,2,33,2,30,2,25,2,22,2,17,2,15,2,10,2
.db 7,2,2,2,255,1,250,1,248,1,243,1,240,1,235,1
.db 230,1,227,1,222,1,220,1,214,1,212,1,207,1,204,1
.db 199,1,197,1,192,1,189,1,184,1,181,1,176,1,171,1
.db 169,1,164,1,161,1,156,1,153,1,148,1,146,1,141,1
.db 138,1,133,1,130,1,125,1,123,1,118,1,115,1,110,1
.db 105,1,102,1,97,1,94,1,90,1,87,1,82,1,79,1
.db 74,1,72,1,66,1,64,1,54,1,49,1,46,1,41,1
.db 39,1,34,1,31,1,26,1,23,1,18,1,16,1,11,1
.db 8,1,3,1,254,0,251,0,246,0,244,0,239,0,236,0
.db 231,0,228,0,223,0,220,0,215,0,213,0,208,0,205,0
.db 200,0,197,0,192,0,190,0,184,0,182,0,177,0,172,0
.db 169,0,164,0,161,0,157,0,154,0,149,0,146,0,141,0
.db 138,0,133,0,131,0,126,0,123,0,118,0,115,0,110,0
.db 108,0,102,0,100,0,95,0,92,0,87,0,84,0,79,0
.db 74,0,71,0,67,0,64,0,59,0,56,0,46,0,41,0
.db 39,0,33,0,31,0,26,0,23,0,18,0,16,0,10,0
.db 8,0,3,0
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
; Same 32x3 word book layout, now immutable code pointers. The existing
; gain_current scratch holds a selected pointer triple instead of gain values.
.globl _pitch_gain_targets
_pitch_gain_targets = pitch_gains
pitch_gains:
.dw _pitch_const_0,_pitch_const_0,_pitch_const_0 ; Book 0
.dw _pitch_const_1,_pitch_const_m26,_pitch_const_16 ; Book 1
.dw _pitch_const_m9,_pitch_const_8,_pitch_const_m11 ; Book 2
.dw _pitch_const_m24,_pitch_const_10,_pitch_const_m23 ; Book 3
.dw _pitch_const_19,_pitch_const_65,_pitch_const_m9 ; Book 4
.dw _pitch_const_28,_pitch_const_m7,_pitch_const_23 ; Book 5
.dw _pitch_const_m9,_pitch_const_47,_pitch_const_20 ; Book 6
.dw _pitch_const_24,_pitch_const_17,_pitch_const_20 ; Book 7
.dw _pitch_const_33,_pitch_const_34,_pitch_const_m12 ; Book 8
.dw _pitch_const_10,_pitch_const_m34,_pitch_const_m10 ; Book 9
.dw _pitch_const_m6,_pitch_const_60,_pitch_const_9 ; Book 10
.dw _pitch_const_11,_pitch_const_46,_pitch_const_m5 ; Book 11
.dw _pitch_const_32,_pitch_const_53,_pitch_const_m18 ; Book 12
.dw _pitch_const_m21,_pitch_const_m39,_pitch_const_5 ; Book 13
.dw _pitch_const_m5,_pitch_const_31,_pitch_const_13 ; Book 14
.dw _pitch_const_13,_pitch_const_27,_pitch_const_4 ; Book 15
.dw _pitch_const_38,_pitch_const_97,_pitch_const_m12 ; Book 16
.dw _pitch_const_m1,_pitch_const_m16,_pitch_const_m1 ; Book 17
.dw _pitch_const_m8,_pitch_const_89,_pitch_const_18 ; Book 18
.dw _pitch_const_15,_pitch_const_36,_pitch_const_m13 ; Book 19
.dw _pitch_const_1,_pitch_const_70,_pitch_const_m1 ; Book 20
.dw _pitch_const_9,_pitch_const_60,_pitch_const_m8 ; Book 21
.dw _pitch_const_m11,_pitch_const_61,_pitch_const_20 ; Book 22
.dw _pitch_const_m2,_pitch_const_45,_pitch_const_9 ; Book 23
.dw _pitch_const_16,_pitch_const_47,_pitch_const_5 ; Book 24
.dw _pitch_const_18,_pitch_const_m50,_pitch_const_17 ; Book 25
.dw _pitch_const_1,_pitch_const_57,_pitch_const_0 ; Book 26
.dw _pitch_const_11,_pitch_const_37,_pitch_const_27 ; Book 27
.dw _pitch_const_m15,_pitch_const_m31,_pitch_const_m19 ; Book 28
.dw _pitch_const_m14,_pitch_const_44,_pitch_const_35 ; Book 29
.dw _pitch_const_4,_pitch_const_15,_pitch_const_3 ; Book 30
.dw _pitch_const_22,_pitch_const_46,_pitch_const_m8 ; Book 31
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
