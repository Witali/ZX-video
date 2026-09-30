; Raw LZMA1 block decoder: lc=0, lp=0, pb=2, dictionary <= 16 KiB.
; Original Z80 implementation from Igor Pavlov's LZMA format specification.
; See LZMA_Z80.md for ABI, limits, layout, provenance and timing evidence.
; Assemble with pyz80, -D FAST_MUL=1 (unrolled) or 0 (loop baseline).
; No indexed operands, self-modifying code, DI, paging or ROM calls.
;
; Entry: HL=input, DE=output, BC=exact output size (0..15872).
; Caller sets input_end to the exclusive input limit. EOS is mandatory.
; Success: A=0, carry clear. Error: A=1, carry set. SP restored on error.
; All primary/alternate BC/DE/HL and AF clobbered; IX/IY/AF' untouched.
; Buffers must not overlap code, model, state or stack. Not reentrant.

        org 0x8000
lzma_decode:
        ld (entry_sp),sp
        ld (input_ptr),hl
        ld (output_ptr),de
        ld (output_start),de
        ld h,b
        ld l,c
        add hl,de
        jp c,decode_error
        ld (output_end),hl
        ld hl,0x3e00
        or a
        sbc hl,bc
        jp c,decode_error
        ld hl,state_begin
        ld de,state_begin+1
        ld bc,state_end-state_begin-1
        ld (hl),0
        ldir
        ld hl,0xffff
        ld (range_value),hl
        ld (range_value+2),hl
        ld hl,probs
        ld de,probs+2
        ld bc,probs_end-probs-2
        ld (hl),0
        inc hl
        ld (hl),4
        dec hl
        ldir
        call read_byte
        or a
        jp nz,decode_error
        call read_byte
        ld (code_value+3),a
        call read_byte
        ld (code_value+2),a
        call read_byte
        ld (code_value+1),a
        call read_byte
        ld (code_value),a
        ld hl,(code_value)
        ld de,(code_value+2)
        ld a,h
        and l
        and d
        and e
        inc a
        jp z,decode_error
next_symbol:
        ld hl,(output_ptr)
        ld de,(output_start)
        or a
        sbc hl,de
        ld a,l
        and 3
        ld (pos_state),a
        ld c,a
        ld a,(lz_state)
        add a,a
        add a,a
        add a,c
        add a,a
        ld (state_pos_offset),a
        ld l,a
        ld h,0
        ld de,is_match
        add hl,de
        call decode_bit
        or a
        jp z,literal
        ld hl,is_rep
        call state_bit
        or a
        jp z,new_match
        ld hl,is_rep_g0
        call state_bit
        or a
        jr nz,other_rep
        ld a,(state_pos_offset)
        ld l,a
        ld h,0
        ld de,is_rep0_long
        add hl,de
        call decode_bit
        or a
        jr nz,long_rep
short_rep:
        ld a,(lz_state)
        cp 7
        ld a,9
        jr c,short_state
        ld a,11
short_state:
        ld (lz_state),a
        ld bc,1
        jp copy_match
other_rep:
        ld hl,is_rep_g1
        call state_bit
        or a
        jr nz,rep_two_three
rep_one:
        ld hl,(rep1)
        jr set_rep0
rep_two_three:
        ld hl,is_rep_g2
        call state_bit
        or a
        ld hl,(rep2)
        jr z,set_rep1
rep_three:
        ld hl,(rep3)
        ld de,(rep2)
        ld (rep3),de
set_rep1:
        ld de,(rep1)
        ld (rep2),de
set_rep0:
        ld de,(rep0)
        ld (rep1),de
        ld (rep0),hl
long_rep:
        ld hl,rep_len
        call decode_length
        inc hl
        inc hl
        ld b,h
        ld c,l
        ld a,(lz_state)
        cp 7
        ld a,8
        jr c,long_state
        ld a,11
long_state:
        ld (lz_state),a
        jp copy_match
new_match:
        ld hl,(rep2)
        ld (rep3),hl
        ld hl,(rep1)
        ld (rep2),hl
        ld hl,(rep0)
        ld (rep1),hl
        ld hl,match_len
        call decode_length
        ld (match_length),hl
        ld a,h
        or a
        ld a,3
        jr nz,length_state_ready
        ld a,l
        cp 4
        jr c,length_state_ready
        ld a,3
length_state_ready:
        ld l,a
        ld h,0
        ; Each position-slot tree has 64 two-byte probabilities.
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,pos_slots
        add hl,de
        ld b,6
        call decode_tree
        ld a,l
        ld (pos_slot),a
        cp 4
        jp c,distance_small
        srl a
        dec a
        ld (distance_bits),a
        ld b,a
        ld a,l
        and 1
        or 2
        ld l,a
        ld h,0
        ld de,0
distance_prefix_loop:
        add hl,hl
        rl e
        rl d
        djnz distance_prefix_loop
        ld (distance_value),hl
        ld (distance_value+2),de
        ld a,(pos_slot)
        cp 14
        jr nc,distance_direct
        ; The compact spec's PosDecoders includes an unused leading entry.
        ld e,a
        ld d,0
        or a
        sbc hl,de
        add hl,hl
        ld de,pos_decoders
        add hl,de
        ld a,(distance_bits)
        ld b,a
        call reverse_tree
        ld de,(distance_value)
        add hl,de
        jp distance_small
distance_direct:
        ld a,(distance_bits)
        sub 4
        ld (direct_count),a
        xor a
        ld hl,0
        ld (direct_value),hl
        ld (direct_value+2),hl
direct_loop:
        call normalize
        ; range >>= 1. Code comparison/subtraction uses 16-bit halves.
        ld hl,(range_value+2)
        srl h
        rr l
        ld (range_value+2),hl
        ld hl,(range_value)
        rr h
        rr l
        ld (range_value),hl
        ex de,hl
        ld hl,(code_value)
        or a
        sbc hl,de
        ld (code_low_temp),hl
        ld hl,(code_value+2)
        ld de,(range_value+2)
        sbc hl,de
        jr c,direct_zero
        ld (code_value+2),hl
        ld hl,(code_low_temp)
        ld (code_value),hl
        scf
        jr direct_append
direct_zero:
        or a
direct_append:
        ld hl,(direct_value)
        adc hl,hl
        ld (direct_value),hl
        ld hl,(direct_value+2)
        adc hl,hl
        ld (direct_value+2),hl
        ld a,(direct_count)
        dec a
        ld (direct_count),a
        jr nz,direct_loop
        ld hl,(direct_value)
        ld de,(direct_value+2)
        ld b,4
direct_shift:
        add hl,hl
        rl e
        rl d
        djnz direct_shift
        ld bc,(distance_value)
        add hl,bc
        ld (distance_value),hl
        ld hl,(distance_value+2)
        adc hl,de
        ld (distance_value+2),hl
        ld hl,align_probs
        ld b,4
        call reverse_tree
        ld de,(distance_value)
        add hl,de
        ld (distance_value),hl
        ld hl,(distance_value+2)
        ld de,0
        adc hl,de
        ld (distance_value+2),hl
        ld a,h
        or l
        jr z,distance_fits
        ; The only legal >16-bit distance is the all-ones EOS marker.
        ld a,h
        and l
        ld hl,(distance_value)
        and h
        and l
        inc a
        jp nz,decode_error
end_marker:
        call normalize
        ld hl,(code_value)
        ld de,(code_value+2)
        ld a,h
        or l
        or d
        or e
        jp nz,decode_error
        ld hl,(output_ptr)
        ld de,(output_end)
        or a
        sbc hl,de
        jp nz,decode_error
        ld hl,(input_ptr)
        ld de,(input_end)
        or a
        sbc hl,de
        jp nz,decode_error
decode_success:
        xor a
        ret
distance_fits:
        ld hl,(distance_value)
distance_small:
        ld (rep0),hl
        ld a,(lz_state)
        cp 7
        ld a,7
        jr c,match_state
        ld a,10
match_state:
        ld (lz_state),a
        ld bc,(match_length)
        inc bc
        inc bc
copy_match:
        ; Validate all bounds before LDIR (overlap is intentional).
        ld hl,(output_ptr)
        push hl
        add hl,bc
        jp c,decode_error
        ld de,(output_end)
        or a
        sbc hl,de
        jp c,copy_size_ok
        jp nz,decode_error
copy_size_ok:
        pop hl
        ld de,(rep0)
        inc de
        ld a,d
        or e
        jp z,decode_error
        push hl
        or a
        sbc hl,de
        jp c,decode_error
        ld de,(output_start)
        or a
        sbc hl,de
        jp c,decode_error
        add hl,de
        pop de
        ldir
        ld (output_ptr),de
        jp next_symbol

literal:
        ld hl,(output_ptr)
        ld de,(output_end)
        or a
        sbc hl,de
        jp nc,decode_error
        ld hl,1
        ld (literal_node),hl
        ld a,(lz_state)
        cp 7
        jr c,literal_plain
        ld hl,(output_ptr)
        ld de,(rep0)
        inc de
        or a
        sbc hl,de
        ld a,(hl)
        ld (match_byte),a
literal_matched:
        ld a,(match_byte)
        add a,a
        ld (match_byte),a
        ld a,1
        adc a,0
        ld d,a
        ld (match_bit_plus_one),a
        ld e,0
        ld hl,(literal_node)
        add hl,de
        add hl,hl
        ld de,literal_probs
        add hl,de
        call decode_bit
        ld c,a
        ld hl,(literal_node)
        add hl,hl
        or l
        ld l,a
        ld (literal_node),hl
        ld a,h
        or a
        jr nz,literal_done
        ld a,(match_bit_plus_one)
        dec a
        cp c
        jr z,literal_matched
literal_plain:
        ld hl,(literal_node)
        add hl,hl
        ld de,literal_probs
        add hl,de
        call decode_bit
        ld hl,(literal_node)
        add hl,hl
        or l
        ld l,a
        ld (literal_node),hl
        ld a,h
        or a
        jr z,literal_plain
literal_done:
        ld a,l
        ld hl,(output_ptr)
        ld (hl),a
        inc hl
        ld (output_ptr),hl
        ld a,(lz_state)
        cp 4
        jr c,literal_state_zero
        cp 10
        jr c,literal_state_sub3
        sub 3
literal_state_sub3:
        sub 3
        jr literal_state_save
literal_state_zero:
        xor a
literal_state_save:
        ld (lz_state),a
        jp next_symbol

; HL=model base, add the current state's two-byte offset.
state_bit:
        ld a,(lz_state)
        add a,a
        ld e,a
        ld d,0
        add hl,de
        jp decode_bit

; HL=length model; result HL=zero-based length (0..271).
decode_length:
        ld (length_base),hl
        call decode_bit
        or a
        jr z,length_low
        ld hl,(length_base)
        inc hl
        inc hl
        call decode_bit
        or a
        jr z,length_mid
        ld hl,(length_base)
        ld de,132
        add hl,de
        ld b,8
        call decode_tree
        ld de,16
        add hl,de
        ret
length_mid:
        ld de,68
        ld a,8
        jr length_pos
length_low:
        ld de,4
        xor a
length_pos:
        ld (length_bias),a
        ld hl,(length_base)
        add hl,de
        ld a,(pos_state)
        add a,a
        add a,a
        add a,a
        add a,a
        ld e,a
        ld d,0
        add hl,de
        ld b,3
        call decode_tree
        ld a,(length_bias)
        or l
        ld l,a
        ret

; HL=tree base, B=bit count (1..8); HL=result, all else clobbered.
decode_tree:
        ld (tree_base),hl
        ld a,b
        ld (tree_count),a
        ld hl,1
        ld (tree_node),hl
tree_loop:
        ld hl,(tree_node)
        add hl,hl
        ld de,(tree_base)
        add hl,de
        call decode_bit
        ld hl,(tree_node)
        add hl,hl
        or l
        ld l,a
        ld (tree_node),hl
        ld a,(tree_count)
        dec a
        ld (tree_count),a
        jr nz,tree_loop
        ; Strip the leading one, leaving at most eight result bits.
        ld a,h
        or a
        jr nz,tree_byte
        ld a,l
        ld b,0x80
tree_find_top:
        ld c,a
        and b
        ld a,c
        jr nz,tree_top_found
        srl b
        jr tree_find_top
tree_top_found:
        xor b
        ld l,a
tree_byte:
        ld h,0
        ret
reverse_tree:
        push bc
        call decode_tree
        pop bc
        ld d,0
reverse_loop:
        rr l
        rl d
        djnz reverse_loop
        ld l,d
        ld h,0
        ret

; HL=probability address; A=decoded bit. Full register clobber except IX/IY/AF'.
decode_bit:
        ld (prob_ptr),hl
        call normalize
        ld hl,(prob_ptr)
        ld c,(hl)
        inc hl
        ld b,(hl)
        ; DE'/DE = range >> 11 (21 bits), BC = probability (11 bits).
        ld hl,(range_value+1)
        ld a,(range_value+3)
        srl a
        rr h
        rr l
        srl a
        rr h
        rr l
        srl a
        rr h
        rr l
        ex de,hl
        exx
        ld e,a
        ld d,0
        exx
        call multiply_bound
        ld (bound_value),hl
        exx
        ld (bound_value+2),hl
        exx
        ld de,(bound_value)
        ld hl,(code_value)
        or a
        sbc hl,de
        ld (code_low_temp),hl
        ld hl,(code_value+2)
        ld de,(bound_value+2)
        sbc hl,de
        jr c,bit_zero
bit_one:
        ld (code_value+2),hl
        ld hl,(code_low_temp)
        ld (code_value),hl
        ld hl,(range_value)
        ld de,(bound_value)
        or a
        sbc hl,de
        ld (range_value),hl
        ld hl,(range_value+2)
        ld de,(bound_value+2)
        sbc hl,de
        ld (range_value+2),hl
        ld hl,(prob_ptr)
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld h,b
        ld l,c
        call shift_right_five
        ex de,hl
        ld h,b
        ld l,c
        or a
        sbc hl,de
        ld a,1
        jr bit_store
bit_zero:
        ld hl,(bound_value)
        ld (range_value),hl
        ld hl,(bound_value+2)
        ld (range_value+2),hl
        ld hl,(prob_ptr)
        ld c,(hl)
        inc hl
        ld b,(hl)
        ld hl,2048
        or a
        sbc hl,bc
        call shift_right_five
        add hl,bc
        xor a
bit_store:
        ld de,(prob_ptr)
        ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
        ret
; HL <= 2047 (adaptive probabilities never reach zero), result HL >> 5.
shift_right_five:
        ld a,l
        rlca
        rlca
        rlca
        and 7
        ld l,a
        ld a,h
        add a,a
        add a,a
        add a,a
        or l
        ld l,a
        ld h,0
        ret

; DE'/DE * BC -> HL'/HL. Does not change DE'/DE.
multiply_bound:
        ld hl,0
        exx
        ld hl,0
        exx
        if FAST_MUL
        ; Eleven bits, MSB first. No shift is needed before the first bit.
        bit 2,b
        jr z,mul_skip10
        add hl,de
        exx
        adc hl,de
        exx
mul_skip10:
        add hl,hl
        exx
        adc hl,hl
        exx
        bit 1,b
        jr z,mul_skip9
        add hl,de
        exx
        adc hl,de
        exx
mul_skip9:
        add hl,hl
        exx
        adc hl,hl
        exx
        bit 0,b
        jr z,mul_skip8
        add hl,de
        exx
        adc hl,de
        exx
mul_skip8:
        add hl,hl
        exx
        adc hl,hl
        exx
        bit 7,c
        jr z,mul_skip7
        add hl,de
        exx
        adc hl,de
        exx
mul_skip7:
        add hl,hl
        exx
        adc hl,hl
        exx
        bit 6,c
        jr z,mul_skip6
        add hl,de
        exx
        adc hl,de
        exx
mul_skip6:
        add hl,hl
        exx
        adc hl,hl
        exx
        bit 5,c
        jr z,mul_skip5
        add hl,de
        exx
        adc hl,de
        exx
mul_skip5:
        add hl,hl
        exx
        adc hl,hl
        exx
        bit 4,c
        jr z,mul_skip4
        add hl,de
        exx
        adc hl,de
        exx
mul_skip4:
        add hl,hl
        exx
        adc hl,hl
        exx
        bit 3,c
        jr z,mul_skip3
        add hl,de
        exx
        adc hl,de
        exx
mul_skip3:
        add hl,hl
        exx
        adc hl,hl
        exx
        bit 2,c
        jr z,mul_skip2
        add hl,de
        exx
        adc hl,de
        exx
mul_skip2:
        add hl,hl
        exx
        adc hl,hl
        exx
        bit 1,c
        jr z,mul_skip1
        add hl,de
        exx
        adc hl,de
        exx
mul_skip1:
        add hl,hl
        exx
        adc hl,hl
        exx
        bit 0,c
        jr z,mul_skip0
        add hl,de
        exx
        adc hl,de
        exx
mul_skip0:
        else
        ; Align 11 probability bits with bit 15, then shift them out.
        ld a,5
mul_align:
        sla c
        rl b
        dec a
        jr nz,mul_align
        ld a,11
mul_loop:
        add hl,hl
        exx
        adc hl,hl
        exx
        sla c
        rl b
        jr nc,mul_loop_skip
        add hl,de
        exx
        adc hl,de
        exx
mul_loop_skip:
        dec a
        jr nz,mul_loop
        endif
        ret
multiply_end:

normalize:
        ld a,(range_value+3)
        or a
        ret nz
        ld hl,(range_value)
        ld a,(range_value+2)
        ld (range_value+3),a
        ld (range_value+1),hl
        xor a
        ld (range_value),a
        ld hl,(code_value)
        ld a,(code_value+2)
        ld (code_value+3),a
        ld (code_value+1),hl
        call read_byte
        ld (code_value),a
        ret
read_byte:
        ld hl,(input_ptr)
        ld de,(input_end)
        or a
        sbc hl,de
        jp nc,decode_error
        add hl,de
        ld a,(hl)
        inc hl
        ld (input_ptr),hl
        ret
decode_error:
        ld sp,(entry_sp)
        ld a,1
        scf
        ret
code_end:
        assert code_end <= 0xa000

; pb=2 specialization removes unreachable position states, losslessly.
probs:          equ 0xa000
is_match:       equ probs
is_rep:         equ is_match+48*2
is_rep_g0:      equ is_rep+12*2
is_rep_g1:      equ is_rep_g0+12*2
is_rep_g2:      equ is_rep_g1+12*2
is_rep0_long:   equ is_rep_g2+12*2
pos_slots:      equ is_rep0_long+48*2
pos_decoders:   equ pos_slots+256*2
align_probs:    equ pos_decoders+115*2
match_len:      equ align_probs+16*2
rep_len:        equ match_len+322*2
literal_probs:  equ rep_len+322*2
probs_end:      equ literal_probs+768*2
        assert probs_end <= 0xb000

; Caller configuration / per-block state are not part of the object file.
entry_sp:       equ 0xb000
input_end:      equ entry_sp+2
input_ptr:      equ input_end+2
output_start:   equ input_ptr+2
output_ptr:     equ output_start+2
output_end:     equ output_ptr+2
state_begin:    equ output_end+2
range_value:    equ state_begin
code_value:     equ range_value+4
rep0:           equ code_value+4
rep1:           equ rep0+2
rep2:           equ rep1+2
rep3:           equ rep2+2
lz_state:       equ rep3+2
pos_state:      equ lz_state+1
state_pos_offset: equ pos_state+1
match_length:   equ state_pos_offset+1
pos_slot:       equ match_length+2
distance_bits:  equ pos_slot+1
distance_value: equ distance_bits+1
direct_count:   equ distance_value+4
direct_value:   equ direct_count+1
code_low_temp:  equ direct_value+4
literal_node:   equ code_low_temp+2
match_byte:     equ literal_node+2
match_bit_plus_one: equ match_byte+1
length_base:    equ match_bit_plus_one+1
length_bias:    equ length_base+2
tree_base:      equ length_bias+1
tree_count:     equ tree_base+2
tree_node:      equ tree_count+1
prob_ptr:       equ tree_node+2
bound_value:    equ prob_ptr+2
state_end:      equ bound_value+4
        assert state_end <= 0xb100
