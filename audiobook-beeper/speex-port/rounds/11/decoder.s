; Approximate 160-sample periodic-wave kernel, NOT a Speex decoder.
; Host supplies phase/step, 32 PCM8 wave entries at 9000, eight transition
; samples at 9020, and a page of signed noise at A000..AFFF. B is the sample
; counter, C the mixed wave value; AF/BC/DE/HL are clobbered. IRQ must be off.
.module periodic
.globl _kernel, _phase, _step, _noise_page, _noise_index
.area _DATA
_phase: .ds 2
_step: .ds 2
_noise_page: .ds 1
_noise_index: .ds 1
.area _CODE
_kernel::
ld b,#160
wave_loop:
ld hl,(_phase)
ld de,(_step)
add hl,de
ld (_phase),hl
; The top five phase bits address a 32-byte period. Integer lookup only.
ld a,h
rrca
rrca
rrca
and a,#31
ld l,a
ld h,#0x90
ld c,(hl)
ld a,(_noise_index)
inc a
ld (_noise_index),a
ld l,a
ld a,(_noise_page)
ld h,a
ld a,(hl)
add a,c
ld c,a
; The first eight samples are precomputed transition values in the record.
ld a,b
cp #153
jr c,wave_regular
ld a,#160
sub a,b
add a,#32
ld l,a
ld h,#0x90
ld c,(hl)
wave_regular:
ld a,c
out (0xfb),a
djnz wave_loop
ret
