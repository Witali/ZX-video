; PVQ4x1024, four signed residuals per vector, PCM8 DAC port FB.
; Valid encoder output has no sum overflow. IRQ disabled; nominal 3.5-MHz
; schedule excludes ULA contention. Code/tables/stack live above 8000.
; DE input cursor, C four packed high fields, B predictor, HL dictionary
; address, IXH previous sample, IY remaining complete 16-sample groups.
.module pvq_port
.globl _entry, _complete, _bank_index, _after_page
.area _DATA
_bank_index: .ds 1
.area _CODE
_entry::
di
ld sp,#0xbffe
xor a,a
ld (_bank_index),a
ld a,#16
ld bc,#0x7ffd
out (c),a
ld ix,#0x8000
ld de,#0xc000
ld iy,#11680
group_start:
call ensure_bank
ld a,(de)
inc de
ld c,a
; Form the aligned four-byte row from the low byte and two high bits.
ld a,(de)
inc de
ld l,a
ld h,#0x88
ld a,(hl)
inc h
ld h,(hl)
ld l,a
ld a,c
and a,#3
rlca
rlca
or a,h
ld h,a
srl c
srl c
; floor(last_signed/2)+128, exactly matching the encoder's recurrence.
.db 0xdd,0x7c ; ld a,ixh, 8 T (index-half instruction)
srl a
add a,#64
ld b,a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 83 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
nop
nop
nop
nop
nop
.globl _group_out0
_group_out0::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 411 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
nop
nop
nop
.globl _group_out1
_group_out1::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 412 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
cp #0
cp #0
nop
nop
nop
nop
nop
.globl _group_out2
_group_out2::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
add a,b
.db 0xdd,0x67 ; ld ixh,a, 8 T (index-half instruction)
; Delay 407 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
nop
nop
.globl _group_out3
_group_out3::
out (0xfb),a
; Form the aligned four-byte row from the low byte and two high bits.
ld a,(de)
inc de
ld l,a
ld h,#0x88
ld a,(hl)
inc h
ld h,(hl)
ld l,a
ld a,c
and a,#3
rlca
rlca
or a,h
ld h,a
srl c
srl c
; floor(last_signed/2)+128, exactly matching the encoder's recurrence.
.db 0xdd,0x7c ; ld a,ixh, 8 T (index-half instruction)
srl a
add a,#64
ld b,a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 296 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
cp #0
nop
nop
nop
nop
.globl _group_out4
_group_out4::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 411 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
nop
nop
nop
.globl _group_out5
_group_out5::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 412 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
cp #0
cp #0
nop
nop
nop
nop
nop
.globl _group_out6
_group_out6::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
add a,b
.db 0xdd,0x67 ; ld ixh,a, 8 T (index-half instruction)
; Delay 407 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
nop
nop
.globl _group_out7
_group_out7::
out (0xfb),a
; Form the aligned four-byte row from the low byte and two high bits.
ld a,(de)
inc de
ld l,a
ld h,#0x88
ld a,(hl)
inc h
ld h,(hl)
ld l,a
ld a,c
and a,#3
rlca
rlca
or a,h
ld h,a
srl c
srl c
; floor(last_signed/2)+128, exactly matching the encoder's recurrence.
.db 0xdd,0x7c ; ld a,ixh, 8 T (index-half instruction)
srl a
add a,#64
ld b,a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 296 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
cp #0
nop
nop
nop
nop
.globl _group_out8
_group_out8::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 411 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
nop
nop
nop
.globl _group_out9
_group_out9::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 412 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
cp #0
cp #0
nop
nop
nop
nop
nop
.globl _group_out10
_group_out10::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
add a,b
.db 0xdd,0x67 ; ld ixh,a, 8 T (index-half instruction)
; Delay 407 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
nop
nop
.globl _group_out11
_group_out11::
out (0xfb),a
; Form the aligned four-byte row from the low byte and two high bits.
ld a,(de)
inc de
ld l,a
ld h,#0x88
ld a,(hl)
inc h
ld h,(hl)
ld l,a
ld a,c
and a,#3
rlca
rlca
or a,h
ld h,a
srl c
srl c
; floor(last_signed/2)+128, exactly matching the encoder's recurrence.
.db 0xdd,0x7c ; ld a,ixh, 8 T (index-half instruction)
srl a
add a,#64
ld b,a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 296 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
cp #0
nop
nop
nop
nop
.globl _group_out12
_group_out12::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 411 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
nop
nop
nop
.globl _group_out13
_group_out13::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
inc l
add a,b
; Delay 412 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
cp #0
cp #0
nop
nop
nop
nop
nop
.globl _group_out14
_group_out14::
out (0xfb),a
; Keep history only at vector end; no dead final pointer increment.
ld a,(hl)
add a,b
.db 0xdd,0x67 ; ld ixh,a, 8 T (index-half instruction)
; Delay 407 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
push af
pop af
nop
nop
.globl _group_out15
_group_out15::
out (0xfb),a
dec iy
.db 0xfd,0x7c ; ld a,iyh, 8 T (index-half instruction)
.db 0xfd,0xb5 ; or a,iyl, 8 T (index-half instruction)
jp nz,group_start
tail_start:
_complete::
halt
jp _complete
; Exactly 143 T including RET on every path. A bank holds 3276 groups;
; four unused bytes prevent a vector/header from straddling the boundary.
; Clobbers AF/BC/HL, replaces DE only when a bank switch is needed.
ensure_bank:
ld a,d
cp #255
jr nz,page_fast
ld a,e
cp #252
jr nz,page_slow
ld a,(_bank_index)
inc a
ld (_bank_index),a
ld l,a
ld h,#0x8a
ld a,(hl)
or a,#16
ld bc,#0x7ffd
out (c),a
ld de,#0xc000
jp _after_page
_after_page::
ret
page_fast:
; Delay 110 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
cp #0
cp #0
nop
nop
nop
ret
page_slow:
; Delay 92 T: PUSH/POP AF=21, CP n=7, NOP=4.
push af
pop af
push af
pop af
push af
pop af
push af
pop af
nop
nop
ret
.globl _code_end
_code_end::
.area _TABLES (ABS)
.org 0x8800
.db 0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60
.db 64,68,72,76,80,84,88,92,96,100,104,108,112,116,120,124
.db 128,132,136,140,144,148,152,156,160,164,168,172,176,180,184,188
.db 192,196,200,204,208,212,216,220,224,228,232,236,240,244,248,252
.db 0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60
.db 64,68,72,76,80,84,88,92,96,100,104,108,112,116,120,124
.db 128,132,136,140,144,148,152,156,160,164,168,172,176,180,184,188
.db 192,196,200,204,208,212,216,220,224,228,232,236,240,244,248,252
.db 0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60
.db 64,68,72,76,80,84,88,92,96,100,104,108,112,116,120,124
.db 128,132,136,140,144,148,152,156,160,164,168,172,176,180,184,188
.db 192,196,200,204,208,212,216,220,224,228,232,236,240,244,248,252
.db 0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60
.db 64,68,72,76,80,84,88,92,96,100,104,108,112,116,120,124
.db 128,132,136,140,144,148,152,156,160,164,168,172,176,180,184,188
.db 192,196,200,204,208,212,216,220,224,228,232,236,240,244,248,252
.org 0x8900
.db 144,144,144,144,144,144,144,144,144,144,144,144,144,144,144,144
.db 144,144,144,144,144,144,144,144,144,144,144,144,144,144,144,144
.db 144,144,144,144,144,144,144,144,144,144,144,144,144,144,144,144
.db 144,144,144,144,144,144,144,144,144,144,144,144,144,144,144,144
.db 145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145
.db 145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145
.db 145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145
.db 145,145,145,145,145,145,145,145,145,145,145,145,145,145,145,145
.db 146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146
.db 146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146
.db 146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146
.db 146,146,146,146,146,146,146,146,146,146,146,146,146,146,146,146
.db 147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147
.db 147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147
.db 147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147
.db 147,147,147,147,147,147,147,147,147,147,147,147,147,147,147,147
.org 0x8a00
.db 0,1,3,4,6,7
.org 0x9000
.db 13,255,243,234,6,7,11,22,16,30,41,52,244,212,184,165
.db 27,50,67,74,210,157,169,158,253,252,252,252,10,12,7,254
.db 169,152,202,248,251,5,16,24,243,4,25,53,29,32,31,31
.db 249,247,244,241,224,223,224,226,2,28,43,31,18,24,25,43
.db 5,18,28,33,3,23,21,9,3,248,254,2,224,201,205,212
.db 24,2,241,24,34,251,197,164,223,194,248,54,252,225,213,208
.db 233,1,22,37,10,231,238,23,2,224,207,227,221,228,239,251
.db 246,226,214,216,36,80,84,36,39,55,14,224,15,12,8,3
.db 22,9,239,214,8,33,29,214,0,0,0,0,38,60,246,238
.db 228,13,254,250,255,39,51,62,239,234,227,223,233,236,242,217
.db 8,11,255,3,245,239,242,0,1,245,233,222,30,12,253,250
.db 22,206,144,135,205,16,31,1,233,9,54,92,238,23,50,23
.db 65,57,226,10,195,217,17,114,245,195,207,210,5,6,6,5
.db 9,31,235,239,19,21,20,19,29,12,8,19,218,241,28,56
.db 196,166,170,200,2,250,239,226,0,255,253,252,223,212,225,4
.db 35,28,20,8,0,4,22,39,241,228,207,182,250,250,248,238
.db 192,192,201,211,21,226,196,213,25,49,60,41,246,246,13,32
.db 54,38,244,203,16,33,18,12,234,255,29,46,6,8,9,9
.db 0,4,3,250,252,8,14,247,35,97,82,10,216,230,233,217
.db 39,240,234,252,14,220,150,128,42,117,109,18,209,175,171,192
.db 230,240,254,15,229,10,82,123,7,23,48,85,37,41,53,19
.db 43,52,52,48,9,29,42,46,39,36,26,15,5,115,127,93
.db 218,191,179,183,226,248,5,12,251,22,51,72,215,213,220,239
.db 226,233,244,255,30,43,29,15,240,231,241,7,241,24,2,186
.db 18,15,236,198,6,4,0,253,24,26,222,197,188,178,248,17
.db 13,184,162,181,2,24,36,22,254,0,3,5,237,187,175,199
.db 222,214,210,211,9,19,25,28,14,26,5,245,6,12,17,21
.db 250,208,210,4,44,2,227,231,44,33,4,37,252,0,5,9
.db 242,8,221,199,18,38,42,37,11,12,12,14,254,253,253,255
.db 23,26,8,17,191,194,254,208,21,18,7,38,255,18,44,106
.db 23,29,242,225,250,236,238,215,15,25,30,28,228,237,16,62
.db 4,0,250,241,245,221,205,207,228,219,213,214,3,254,255,1
.db 2,176,133,130,50,37,0,231,45,45,28,14,199,195,224,6
.db 3,36,77,13,16,41,55,12,15,15,13,12,238,36,84,76
.db 235,243,253,8,241,30,78,92,222,214,250,10,16,49,96,17
.db 11,5,232,212,255,4,10,16,10,46,28,7,218,219,223,234
.db 221,206,203,165,0,31,55,28,252,10,36,57,7,208,216,1
.db 0,255,255,255,241,246,255,7,50,23,13,24,218,229,247,9
.db 18,31,39,43,249,13,251,250,233,231,231,233,1,8,255,246
.db 12,12,26,16,244,231,34,60,9,32,12,233,224,187,219,17
.db 238,221,210,200,242,231,228,229,15,49,0,196,236,8,20,1
.db 208,174,198,248,23,43,19,221,32,68,36,236,9,3,251,11
.db 21,36,49,59,254,241,235,239,17,22,50,79,10,16,21,24
.db 63,92,84,44,226,226,229,236,244,226,251,229,221,211,203,202
.db 238,246,234,172,32,33,16,247,232,246,2,240,251,187,187,216
.db 230,233,200,158,58,251,175,146,246,255,11,24,22,14,2,2
.db 244,207,190,183,255,255,0,0,27,31,33,37,247,244,216,194
.db 26,253,219,204,205,205,252,45,10,10,248,249,242,249,254,250
.db 19,47,19,248,0,254,251,248,219,212,214,220,5,11,14,214
.db 42,205,218,229,61,39,35,41,216,197,202,226,235,239,243,246
.db 242,221,231,1,232,40,64,66,46,48,240,248,242,218,217,234
.db 12,24,37,20,169,207,24,237,11,245,238,248,23,32,32,26
.db 14,214,199,218,16,222,216,236,4,58,116,127,232,233,4,42
.db 255,14,16,13,198,223,32,88,28,21,21,29,6,247,221,195
.db 55,125,119,66,243,12,34,19,21,220,164,178,235,227,229,239
.db 16,250,0,12,250,251,1,252,23,27,11,248,43,27,240,189
.db 227,188,202,224,1,8,17,24,25,16,23,17,5,216,168,146
.db 2,252,249,14,217,183,238,216,1,2,3,3,254,224,189,165
.db 209,145,141,182,221,6,52,77,3,227,0,15,7,245,226,218
.db 240,250,10,255,12,226,179,152,206,196,200,248,254,23,19,246
.db 11,23,35,45,10,5,255,247,51,70,62,30,247,27,47,52
.db 254,240,230,226,236,217,199,187,246,196,156,145,253,252,250,249
.db 250,22,28,14,239,235,9,5,1,13,20,24,42,36,44,83
.db 10,52,58,241,253,251,230,237,220,199,202,5,207,225,2,41
.db 7,33,57,74,14,15,22,243,12,24,17,0,70,28,210,165
.db 232,208,214,224,4,242,227,238,1,15,31,27,24,24,17,6
.db 45,36,200,170,227,212,242,254,9,249,233,223,254,254,4,16
.db 248,8,28,42,38,0,210,242,233,225,219,216,10,9,6,4
.db 12,15,15,15,253,232,233,238,21,79,109,86,24,226,224,11
.db 252,225,5,53,25,255,203,210,8,20,1,19,240,2,36,70
.db 236,188,169,182,6,6,4,2,31,71,80,0,24,2,249,15
.db 254,1,2,0,240,181,140,136,23,6,243,228,251,224,198,187
.db 5,9,12,15,19,32,34,35,217,245,235,173,217,216,222,225
.db 245,244,244,246,238,13,31,235,231,231,234,240,72,112,58,240
.db 14,247,11,236,42,58,52,16,40,51,37,25,33,37,9,230
.db 12,198,198,228,229,230,225,221,4,251,241,233,223,202,194,212
.db 239,9,241,17,30,47,55,58,232,228,241,0,205,196,196,206
.db 217,178,227,196,16,16,62,55,14,64,89,86,249,235,221,209
.db 17,65,88,60,240,219,210,218,2,8,14,19,17,15,2,244
.db 1,2,248,214,239,251,13,30,247,31,16,16,48,56,60,59
.db 217,223,218,212,25,24,242,210,32,43,44,40,223,184,161,165
.db 27,43,40,49,247,0,2,253,10,178,185,19,48,39,23,3
.db 13,14,30,55,29,46,40,19,251,253,1,5,2,246,240,243
.db 22,27,29,32,209,197,234,236,187,200,255,68,225,224,238,23
.db 208,203,192,188,249,245,13,17,15,0,236,220,226,221,225,233
.db 9,13,22,35,5,209,204,207,23,36,40,28,14,24,25,11
.db 247,241,237,235,241,236,234,236,50,220,182,208,198,207,220,225
.db 59,251,228,16,6,18,21,20,220,253,243,229,241,205,179,176
.db 52,18,255,50,10,4,4,8,218,229,6,226,197,152,170,239
.db 41,4,216,206,1,209,208,21,2,252,245,238,228,219,216,238
.db 246,249,254,3,213,236,7,17,236,248,202,187,202,194,185,146
.db 31,42,29,47,248,253,4,12,27,38,47,49,3,5,7,8
.db 233,232,238,250,9,0,246,239,244,236,11,243,37,248,198,185
.db 14,18,15,5,4,0,248,231,5,17,32,46,251,230,222,228
.db 46,63,253,186,208,22,118,118,255,240,225,216,50,35,10,16
.db 31,13,240,228,39,64,57,44,23,59,81,73,213,239,27,101
.db 210,202,253,73,6,13,47,76,7,251,7,30,208,236,33,83
.db 183,196,30,121,226,223,251,40,251,235,217,200,246,214,206,240
.db 5,53,98,104,227,231,252,18,0,250,232,216,1,250,208,170
.db 233,213,227,241,231,217,205,198,182,160,211,51,60,58,20,234
.db 32,41,22,35,233,58,126,122,252,15,54,7,23,232,189,188
.db 13,253,226,10,27,5,239,248,32,61,58,19,11,6,247,229
.db 3,40,73,73,12,46,62,60,28,31,27,19,184,169,208,234
.db 255,54,37,248,7,10,13,49,21,246,17,52,4,6,9,12
.db 41,42,60,2,248,248,248,250,203,194,230,36,45,25,16,41
.db 239,221,253,255,7,17,12,31,191,204,229,175,7,87,125,120
.db 22,12,1,13,3,3,1,255,23,20,249,252,14,19,21,21
.db 6,4,237,234,15,9,28,43,31,66,72,48,235,245,11,37
.db 42,82,34,210,48,64,58,82,29,36,255,7,234,164,165,200
.db 228,206,195,197,211,226,237,236,5,237,224,224,8,0,253,252
.db 10,37,50,47,10,5,251,237,10,229,237,255,11,24,37,239
.db 64,60,12,18,234,220,221,244,43,15,210,32,232,229,244,14
.db 9,3,248,30,181,175,5,242,44,32,221,240,33,23,3,232
.db 215,216,230,236,254,248,229,206,9,248,14,16,249,251,6,246
.db 254,16,33,39,4,18,247,5,231,208,202,219,227,226,248,240
.db 36,43,49,53,33,236,183,158,228,18,236,247,244,237,233,231
.db 237,205,194,206,29,242,182,128,9,240,210,188,201,219,17,50
.db 11,14,17,20,0,13,26,39,248,7,21,35,235,247,5,16
.db 208,209,243,30,11,216,247,245,32,65,91,93,73,31,223,199
.db 28,41,36,0,251,245,238,232,237,250,10,23,197,195,214,234
.db 25,48,33,34,3,6,2,9,17,42,34,25,28,7,185,160
.db 247,3,1,5,30,12,6,8,0,254,249,242,248,18,0,237
.db 40,51,215,199,5,253,247,250,54,21,217,185,21,244,203,183
.db 4,4,3,2,1,2,254,1,37,28,23,24,0,251,248,246
.db 3,27,51,60,5,4,245,243,255,3,8,11,40,23,0,244
.db 238,230,221,212,209,217,234,251,26,28,26,24,238,228,223,220
.db 28,236,204,200,8,217,191,181,252,250,248,246,209,216,239,9
.db 15,215,206,178,242,241,242,246,28,16,217,174,251,206,191,217
.db 28,110,110,53,224,242,28,71,1,6,6,1,219,159,239,11
.db 242,242,214,213,4,255,250,246,4,249,5,2,250,2,9,14
.db 0,243,245,0,0,0,10,47,21,19,13,2,240,240,253,17
.db 18,19,25,33,44,32,32,49,225,243,10,31,4,46,61,45
.db 14,249,229,213,247,253,254,246,244,205,170,154,229,225,217,206
.db 6,3,253,246,224,190,170,160,226,208,216,198,233,233,218,192
.db 8,35,42,11,17,21,18,11,60,41,3,248,211,254,59,106
.db 17,41,62,79,16,10,3,252,243,206,209,218,245,37,96,124
.db 234,6,36,54,251,7,7,252,20,9,227,243,5,28,4,196
.db 247,248,251,255,255,255,4,253,13,63,60,53,253,27,62,82
.db 253,252,29,17,250,239,255,0,251,245,241,238,254,248,247,250
.db 29,7,15,27,0,229,204,9,25,247,218,229,7,36,32,25
.db 3,22,35,39,234,167,148,179,232,210,191,186,7,20,37,59
.db 3,1,9,238,252,46,239,155,252,232,247,35,238,238,243,252
.db 68,51,17,43,58,54,40,27,241,199,229,26,50,25,250,4
.db 10,251,239,240,240,224,204,191,219,204,232,20,239,0,51,36
.db 252,242,247,10,240,28,59,50,246,194,199,235,1,244,235,231
.db 238,242,249,251,251,243,1,11,1,26,234,180,4,14,238,205
.db 3,20,9,2,3,1,253,250,188,166,184,211,255,1,10,23
.db 23,19,14,12,236,234,232,229,242,0,20,38,247,229,210,194
.db 238,224,215,209,20,232,25,250,2,241,237,15,250,244,241,246
.db 2,240,217,198,56,62,35,255,242,6,38,86,241,232,236,252
.db 230,166,136,143,182,213,2,23,13,195,140,164,34,12,226,195
.db 250,0,16,3,18,234,195,171,229,232,239,245,0,7,12,13
.db 47,45,10,210,254,88,127,92,247,248,243,233,20,59,67,32
.db 13,4,19,24,11,15,4,224,43,48,43,42,251,249,242,227
.db 2,233,210,214,209,244,28,35,11,17,249,238,226,220,217,221
.db 206,186,185,195,2,2,2,2,6,23,43,55,19,253,12,7
.db 214,218,216,179,176,240,42,4,251,251,253,255,242,16,71,57
.db 30,239,189,230,221,231,14,34,200,218,227,214,34,64,41,18
.db 226,1,18,24,42,41,34,22,0,229,207,192,241,6,24,30
.db 20,27,26,18,250,252,0,25,248,253,5,7,253,191,144,128
.db 9,255,241,226,6,253,246,244,252,2,7,5,48,86,246,242
.db 212,234,245,246,1,6,16,33,16,5,238,233,212,222,14,72
.db 238,4,4,44,19,16,11,7,225,226,235,244,4,16,3,246
.db 21,12,21,31,236,243,246,230,0,254,3,10,239,223,218,225
.db 11,30,49,57,39,15,8,5,26,0,213,185,0,254,6,64
.db 38,16,239,212,248,20,37,72,28,20,5,248,6,246,222,208
.db 238,230,13,21,11,2,0,3,0,7,250,234,241,7,20,19
.db 232,242,7,23,196,144,187,211,250,0,250,254,242,241,238,231
.db 1,6,27,51,10,7,3,254,250,247,246,245,252,254,255,1
.db 7,41,82,88,250,2,30,249,254,249,245,242,1,13,25,239
.db 20,19,48,62,255,254,254,4,225,254,10,244,243,21,68,102
.db 236,243,232,205,4,230,191,165,253,18,36,50,39,249,205,218
.db 11,235,210,203,246,243,241,240,15,250,221,188,2,7,25,69
.db 18,3,244,223,40,63,15,255,255,248,241,235,239,2,246,251
.db 7,23,70,55,194,177,210,220,13,16,11,253,238,238,248,4
.db 23,250,0,26,31,32,23,13,15,20,24,27,27,23,32,62
.db 22,241,248,50,7,15,17,11,245,22,24,255,208,210,211,197
.db 59,69,58,55,20,23,25,24,250,36,85,103,241,245,250,1
.db 254,8,255,0,19,36,55,69,14,14,3,26,232,249,28,61
.db 230,181,156,152,16,60,38,254,242,244,240,8,3,250,2,248
.db 6,10,12,11,232,10,48,63,20,20,38,4,15,19,5,1
.db 55,90,69,14,18,17,253,233,247,0,19,30,16,17,17,16
.db 47,31,210,207,17,33,32,14,17,8,253,7,23,42,54,53
.db 238,236,238,243,252,237,235,252,209,186,190,209,36,19,247,237
.db 246,243,233,220,12,32,47,68,232,245,27,20,253,1,255,251
.db 11,34,61,58,231,223,229,247,21,29,2,216,231,201,177,168
.db 5,9,8,4,25,46,48,67,254,234,211,201,46,72,83,67
.db 251,0,253,241,36,23,251,221,233,215,234,4,6,253,255,9
.db 246,238,237,242,86,86,32,238,204,164,150,177,49,90,89,73
.db 241,49,44,29,244,248,5,21,13,7,0,250,238,3,254,238
.db 254,254,255,254,253,246,7,253,23,12,249,234,11,11,4,242
.db 216,206,216,230,1,12,9,237,48,4,194,198,236,220,234,220
.db 224,220,238,227,251,241,223,225,34,226,160,141,245,236,229,225
.db 236,228,225,230,7,255,236,217,251,32,9,238,27,40,58,69
.db 0,10,27,12,16,8,253,243,250,15,25,31,215,251,18,10
.db 194,221,213,180,7,12,21,27,246,19,7,6,24,24,20,14
.db 73,74,47,19,20,10,11,18,247,252,254,228,239,240,0,30
.db 25,4,4,253,246,152,148,217,3,19,23,255,176,165,237,37
.db 250,163,207,224,34,26,26,41,6,251,248,4,250,3,13,19
.db 6,255,6,6,5,9,6,252,243,215,242,29,1,29,38,1
.db 244,235,248,13,27,255,230,211,38,43,42,33,231,225,223,225
.db 246,17,44,44,9,224,188,199,14,223,198,240,21,35,45,45
.db 214,207,206,210,31,23,9,243,17,20,6,236,8,0,8,253
.db 10,12,254,16,248,173,192,173,227,238,238,233,238,254,6,5
.db 249,252,31,55,242,249,3,14,19,26,35,46,230,252,250,218
.db 16,9,218,199,20,33,21,29,204,10,82,108,246,34,38,7
.db 48,53,67,75,35,39,22,255,253,6,11,29,249,219,199,197
.db 19,254,248,2,243,8,14,226,223,195,208,237,204,253,44,57
.db 13,12,10,8,223,164,174,182,223,236,3,25,10,249,23,36
.db 2,1,255,253,7,12,15,16,47,43,22,32,255,8,23,32
.db 43,51,37,11,198,2,242,196,7,27,26,19,3,14,23,30
.db 228,214,208,229,33,86,54,239,7,235,227,242,245,200,217,244
.db 247,8,18,10,11,26,34,35,242,240,239,238,0,1,0,255
.db 23,16,222,221,220,229,11,252,27,4,252,42,199,161,182,178
.db 12,21,28,35,8,13,12,5,25,34,24,7,223,203,196,186
.db 40,18,242,18,201,188,199,192,3,2,1,5,240,248,18,51
.db 37,55,57,68,18,251,250,246,39,44,40,60,244,254,9,18
.db 206,188,207,208,239,22,65,77,2,232,202,182,1,205,155,132
.db 10,10,9,10,20,25,34,38,249,6,239,220,17,27,10,28
.db 30,45,232,176,241,10,9,246,254,5,250,4,0,9,12,5
.db 20,16,7,251,235,249,255,0,45,59,44,32,35,38,37,31
.db 1,218,227,252,39,52,32,244,248,244,247,0,255,241,252,27
.db 6,27,0,221,35,59,65,55,238,212,199,197,207,196,209,225
.db 247,237,244,244,250,10,23,21,18,12,247,224,9,46,40,36
.db 5,44,225,203,34,26,16,19,245,231,229,244,0,2,5,7
.db 64,64,6,211,252,14,2,12,18,45,52,33,25,58,52,3
.db 207,194,8,14,235,4,16,26,245,16,45,59,248,1,244,240
.db 2,9,47,36,251,250,250,251,220,219,231,244,29,17,208,21
.db 14,252,228,201,20,28,23,255,191,214,50,123,238,236,228,0
.db 29,20,7,29,0,0,1,3,3,3,0,18,24,32,41,51
.db 229,241,6,3,255,0,238,254,52,8,212,168,25,28,19,49
.db 2,65,78,38,20,60,76,12,0,252,250,1,198,181,192,224
.db 235,18,5,220,235,228,235,194,249,239,228,218,244,244,247,251
.db 8,33,8,7,220,184,182,218,41,76,51,19,1,1,1,1
.db 240,253,16,13,30,52,52,31,32,30,35,47,28,15,237,10
.db 230,249,22,44,237,237,237,238,33,207,173,194,251,248,254,3
.db 214,238,225,197,255,209,181,192,197,180,201,9,4,206,9,80
.db 231,239,248,253,23,54,70,89,4,239,10,35,255,252,2,2
.db 192,219,245,222,23,251,232,236,22,37,72,94,65,37,245,233
.db 11,3,241,0,222,243,18,46,23,12,255,244,24,46,66,61
.db 50,99,110,73,241,245,249,243,43,77,51,250,14,17,40,31
.db 35,30,14,1,217,201,195,199,6,250,16,254,247,250,1,9
.db 11,2,250,244,248,6,2,246,1,203,244,223,35,55,76,58
.db 10,244,231,234,9,243,252,26,252,33,48,44,12,4,6,16
.db 43,31,8,243,18,244,240,15,36,7,23,66,28,36,40,39
.db 10,251,237,230,219,234,10,51,225,208,216,243,33,77,88,74
.db 250,255,249,9,208,206,220,241,18,3,247,237,243,229,214,203
.db 229,14,38,36,17,16,16,24,230,216,209,207,28,53,14,17
.db 252,7,2,195,29,18,0,239,231,199,180,193,244,234,224,216
.db 13,235,215,219,244,252,204,219,195,169,209,177,221,222,237,3
.db 211,214,219,217,32,32,37,11,3,4,4,5,247,221,194,177
.db 242,18,30,38,249,241,234,228,215,225,255,26,229,237,249,5
.db 245,222,231,242,14,6,11,32,29,8,16,44,206,188,179,172
.db 63,75,27,233,226,200,186,174,5,3,252,3,33,35,32,24
.db 204,244,32,5,1,237,220,208,52,58,24,10,17,240,218,247
.db 0,253,251,251,17,48,80,48,28,21,9,2,232,5,29,7
