; Whole-block raw LZSA2 coroutine. Prefix 7C00/core 8DE0 and state are writable.
; Source 6500, output C000, caller BFF0 and private 7BE0 stacks are disjoint.
; IRQ handlers preserve live AF/BC/DE/HL and the AF' nibble reservoir.
include "constants.inc"
org $6000
start:
    ld sp,$bff0
    ld hl,packed
    ld (lzsa2_input_pointer),hl
    ld hl,$c000+raw_length
    ld (lzsa2_block_end),hl
    ld (lzsa2_slice_target),hl
    call lzsa2_begin
    ; The byte-exact EOD path returns with the complete sample at C000.
    halt
    jp $-1
org $6500
packed:
    incbin "sample.lzsa"
include "decoder.asm"
