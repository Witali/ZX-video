; Compact mu-law remains in RAM. A byte selects a deduplicated packet row;
; the row was calculated with the full standard16-bit G.711 decoded level.
; Main BC=00FE, D=16, E=feedback ordinal*4, HL=current FIRST /table cursor,
; IY=current SECOND. Alternate DE is the compressed-byte cursor. IX holds
; the next bank tail. SP reads four-byte records, never writes a PCM buffer.
; FIRST pointers are64-byte aligned: low six bits carry the successor state.
; The two eight-pulse routines overlap lookup of the following sample.
        INCLUDE "config.inc"
        ORG 0x8000
        INCLUDE "startup.inc"
ready:  LD IX,bank_tail_0
        LD DE,first_address
        LD A,(DE)
        INC DE
        EXX
        LD E,initial_feedback_offset
        LD L,A
        LD H,packet_map >> 8
        LD A,(HL)
        INC H
        LD H,(HL)
        OR E
        LD L,A
        LD SP,HL
        POP IY
        POP HL
        LD A,L
        AND 63
        LD E,A
        LD A,L
        AND 192
        LD L,A
        LD D,16
        LD BC,0x00FE
        JP (HL)

; Only a page boundary takes this detour. Main HL still holds the aligned
; current FIRST address. OR9 constructs its return without a stack write.
; AF' protects the prefetched byte while the paging/continuation code uses A.
advance_page:
        INC D
        JP Z,bank_handoff
        EX AF,AF'
        EXX
resume_first:
        LD A,L
        OR first_resume_offset
        LD L,A
        EX AF,AF'
        JP (HL)
bank_handoff:
        JP (IX)

; Balanced silent filler aligns complete loops to the same ULA field phase.
; It runs only before the final silent packet, not in the audible source.
IDLE_BLOCK: MACRO
        IF \0 > 0
        LD A,\0
idle_block_\1: ASSERT 1
        OUT (C),D
        JP $+3
        NOP
        DB 0xED,0x71
        DEC A
        JP NZ,idle_block_\1
        ENDIF
        ENDM
BANK_TAIL: MACRO
bank_tail_\0: ASSERT 1
        EX AF,AF'
        LD BC,0x7FFD
        LD A,\1+24
page_\0: OUT (C),A
        LD DE,\2
        LD IX,bank_tail_\3
        EXX
        IF \4
        IF loop_idle_pairs > 0
        IDLE_BLOCK idle_count_0,0
        IDLE_BLOCK idle_count_1,1
        IDLE_BLOCK idle_count_2,2
        IDLE_BLOCK idle_count_3,3
        IDLE_BLOCK idle_count_4,4
        IDLE_BLOCK idle_count_5,5
        IF idle_pad_loads > 0
        LD A,0
        ENDIF
        IF idle_pad_loads > 1
        LD A,0
        ENDIF
        IF idle_pad_loads > 2
        LD A,0
        ENDIF
        DS idle_pad_nops
        ENDIF
        ; The last code is zero. Its predecessor state maps exactly to the
        ; initial feedback, closing the repeat without changing source bytes.
        LD E,guard_feedback_offset
        ENDIF
        JP resume_first
        ENDM
        INCLUDE "tails.inc"
        INCLUDE "loader.inc"
        ASSERT $ <= 0x8400
        DS 0x8400-$

PULSE: MACRO
        IF \0
        OUT (C),D
        ELSE
        DB 0xED,0x71
        ENDIF
        ENDM
FIRST: MACRO
        ASSERT $ == first_address_\0
        PULSE ((\0)>>7) & 1
        EXX
        LD A,(DE)
        INC E
        JP Z,advance_page
        EXX
        ASSERT $ == first_address_\0+first_resume_offset
        PULSE ((\0)>>6) & 1
        LD L,A
        LD H,packet_map >> 8
        PULSE ((\0)>>5) & 1
        LD A,(HL)
        INC H
        PULSE ((\0)>>4) & 1
        LD H,(HL)
        OR E
        PULSE ((\0)>>3) & 1
        LD L,A
        LD SP,HL
        PULSE ((\0)>>2) & 1
        LD A,0
        LD A,0
        PULSE ((\0)>>1) & 1
        LD A,0
        LD A,0
        PULSE (\0) & 1
        LD BC,0x00FE
        JP (IY)
        ASSERT $ <= first_address_\0+64
        DS first_address_\0+64-$
        ENDM
        INCLUDE "first.inc"

SECOND: MACRO
        ASSERT $ == second_address_\0
        PULSE ((\0)>>7) & 1
        POP IY
        PULSE ((\0)>>6) & 1
        POP HL
        NOP
        PULSE ((\0)>>5) & 1
        LD A,L
        AND 63
        LD E,A
        PULSE ((\0)>>4) & 1
        LD A,L
        AND 192
        LD L,A
        PULSE ((\0)>>3) & 1
        NOP
        NOP
        NOP
        PULSE ((\0)>>2) & 1
        LD A,0
        LD A,0
        PULSE ((\0)>>1) & 1
        LD A,0
        NOP
        NOP
        PULSE (\0) & 1
        LD BC,0x00FE
        JP (HL)
        ASSERT $ <= second_address_\0+44
        DS second_address_\0+44-$
        ENDM
        INCLUDE "second.inc"
        ASSERT $ <= packet_map
        DS packet_map-$
        MDAT "map.bin"
resident_end:
        ASSERT $ == 0x8000+resident_reserve
        DS 0xC000-$
screen_data: MDAT "screen.bin"
