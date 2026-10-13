; Whole-block Fast ZX0 example. Code/operands and private stack are writable.
; The tiny payload at 6500 does not overlap prefix 7C00/core 8DF2.
; Caller stack below BFF0 and decoder stack below 7BE0 are separate.
; IRQ handlers must preserve the decoder's live AF/BC/DE/HL and AF'.
include "constants.inc"
org $6000
start:
    ld sp,$bff0
    ld hl,packed
    ld (zx0_input_pointer),hl
    ld hl,$c000+raw_length
    ld (zx0_block_end),hl
    ld (zx0_slice_target),hl
    call zx0_begin
    ; Output C000..C000+raw_length now contains the complete sample.
    halt
    jp $-1
org $6500
packed:
    incbin "sample.zx0"
include "decoder.asm"
