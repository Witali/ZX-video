; Experimental 4-bit PWM: two 226-T periods per decoded IMA sample.
; Authoritative externally assembled source; no runtime PCM/PWM buffer.
; Requires the same host proof of unclipped PCM16 as the uniform PDM player.
; Main BC=10FEh, DE=input, HL=NOP ladder cursor; IX=biased predictor.
; Alternate HL=clean IMA row, BC=delta; SP=read-only table cursor.
; A=15-(PCM8>>4), IYL=next width. Main L protects q during decoding.
; IRQs disabled; RET C is never taken after AND has cleared carry.
;
; Each page has two complementary 15-NOP ladders. Falling edge is
; 68+4*(15-q) T after rising edge; ordinary period is exactly 226 T.
; Decoder work fits between edges. Two periods/sample =452 T vs PDM438 T.
; Page crossings remain 452 T. Bank tails add89 T, final bank adds121 T.
; ULA I/O/data contention and startup TR-DOS latency are measured separately.

        INCLUDE "config.inc"
        ORG 0x8000

LOAD_BANK: MACRO
        LD BC,0x7FFD
        LD A,\0+16
        OUT (C),A
        LD DE,\1
        LD (disk_position),DE
        LD HL,\2
        LD B,\3
        CALL read_n
        ENDM

SILENCE_AY: MACRO
        LD BC,0xFFFD
        LD A,\0
        OUT (C),A
        LD BC,0xBFFD
        XOR A
        OUT (C),A
        ENDM

start:  DI
        LD SP,0x6000
        LD IY,0x5C3A
        IM 1
        XOR A
        OUT (0xFE),A
        LD HL,screen_data
        LD DE,0x4000
        LD BC,6912
        LDIR
        EI
        LOAD_BANK 0,disk_0,address_0,sectors_0
        LOAD_BANK 4,disk_1,address_1,sectors_1
        LOAD_BANK 6,disk_2,address_2,sectors_2
        LOAD_BANK 1,disk_3,address_3,sectors_3
        LOAD_BANK 3,disk_4,address_4,sectors_4
        LOAD_BANK 7,disk_5,address_5,sectors_5
        LOAD_BANK 2,disk_6,address_6,sectors_6
        LOAD_BANK 5,disk_7,address_7,sectors_7
        DI
        SILENCE_AY 8
        SILENCE_AY 9
        SILENCE_AY 10
        LD BC,0x7FFD
        LD A,16
        OUT (C),A
        EI
        HALT
        DI
ready:  LD DE,address_0
        EXX
        LD HL,tables+64*initial_index
        EXX
        LD IX,initial_predictor+32768
        LD HL,bank_tail_0
        LD (bank_jump+1),HL
        LD A,(DE)
        AND 15
        RLCA
        RLCA
        EXX
        OR L
        LD L,A
        LD SP,HL
        POP BC
        POP HL
        ADD IX,BC
        EXX
        LD A,IXH
        CPL
        RRCA
        RRCA
        RRCA
        RRCA
        AND 15
        LD BC,0x10FE
        JP high_first

bank_dispatch:
bank_jump: JP bank_tail_0

; Startup-only real-stack disk reader. No disk access while PWM is running.
read_n: PUSH BC
        PUSH HL
        LD DE,(disk_position)
        LD BC,0x0105
disk_call:
        CALL 0x3D13
        POP HL
        POP BC
        INC H
        LD DE,(disk_position)
        INC E
        BIT 4,E
        JR Z,sector_ok
        LD E,0
        INC D
sector_ok:
        LD (disk_position),DE
        DJNZ read_n
        RET
disk_position: DW 0
; Macro arguments: page base, label prefix, nibble (0=low/1=high),
; and stage (0=table decode/1=quantize and publish).
CELL:   MACRO
        ASSERT $ <= \0
        DS \0-$
\1_ramp_high: ASSERT 1
        DS 15                   ; 0..15 NOPs: 0..60 T
\1_fall: DB 0xED,0x71         ; OUT (C),0: 12 T, NMOS Z80 (pyz80 lacks mnemonic)
        XOR 79                  ; 7: complementary low-ramp address, CY=0
        LD L,A                  ; 4
        JP (HL)                 ; 4
        DS \0+64-$
\1_ramp_low: ASSERT 1
        DS 15                   ; complementary NOP count; total always15
        IF \3 == 0
        EXX                     ; 4
        POP BC                  ; 10: signed modular delta
        POP HL                  ; 10: clean next state row
\1_state: ADD IX,BC            ; 15: host-proven no saturation needed
        EXX                     ; 4
        XOR 79                  ; 7: restore old width q; total low work50
        ; JP adds10 T: low work60 T in both stages.
        JP \1_next
        ELSE
        JP \1_publish          ; 10: match the first-stage low work60 T
\1_publish: ASSERT 1
        LD A,IYL                ; 8: publish the new sample's width
        IF \2 == 1
        INC E                   ; 4: move input only after high nibble
        JP NZ,\1_address_ok    ; 10
        INC D                   ; 4
        JP Z,bank_dispatch      ; 10: bank handled while output is low
        NOP                     ; 4
        JP low_first            ; 10: page path low work50 T
\1_address_ok: ASSERT 1
        EXX                     ; 4: harmless padding, preserves main DE
        EXX                     ; 4
        JP \1_address_next     ; 10
\1_address_next: ASSERT 1
        JP low_first            ; 10: normal path low work50 T
        ELSE
        DS 8                    ; 32 T, AF and predictor unchanged
        JP high_first           ; 10: low-nibble path low work50 T
        ENDIF
        ENDIF
        ASSERT $ <= \0+128
        DS \0+128-$
\1: ASSERT 1
        LD H,\0 >> 8           ; 7: page-specific NOP ladder
        LD L,A                  ; 4: L saves q while decoder uses A
\1_rise: OUT (C),B             ; 12: B=16, EAR high, MIC/border low
        IF \3 == 0
        LD A,(DE)               ; 7
        IF \2 == 0
        AND 15                  ; 7
        RLCA                    ; 4
        RLCA                    ; 4
        ELSE
        AND 240                 ; 7
        RRCA                    ; 4
        RRCA                    ; 4
        ENDIF
        EXX                     ; 4
        OR L                    ; 4
        LD L,A                  ; 4
        LD SP,HL                ; 6
        EXX                     ; 4
        LD A,L                  ; 4: restore q from main L
        NOP                     ; 4: high work52 T
        ELSE
        LD A,IXH                ; 8: top eight bits of full IMA predictor
        CPL                     ; 4: invert for descending high-ramp length
        RRCA                    ; 4
        RRCA                    ; 4
        RRCA                    ; 4
        RRCA                    ; 4
        AND 15                  ; 7: quantize to16 pulse widths
        LD IYL,A                ; 8: candidate; current width still in main L
        LD A,L                  ; 4: restore q; AND15 cleared carry
        RET C                   ; 5: NEVER taken; high work52 T
        ENDIF
        JP (HL)                 ; 4
        ENDM

BANK_TAIL: MACRO
bank_tail_\0: ASSERT 1
        LD BC,0x7FFD            ; 10
        LD A,\1+16             ; 7
page_\0: OUT (C),A             ; 12
        LD DE,\2               ; 10
        LD HL,bank_tail_\3      ; 10
        LD (bank_jump+1),HL     ; 16
        IF \0 == 7
        EXX                     ; 4
        LD HL,tables+64*initial_index ; 10
        EXX                     ; 4
        LD IX,initial_predictor+32768 ; 14
        ENDIF
        LD BC,0x10FE            ; 10
        LD A,IYL                ; 8
        JP low_first            ; 10: 93 T, +32 on final bank
        ENDM

; Both stages: 52-T high work +60-T low work +114 T ramps/I/O =226 T.
; Each page fits two bank tails after its unreachable JP(HL).
high_first_next: EQU high_second
low_first_next: EQU low_second
        CELL 0x8200,high_first,1,0
        BANK_TAIL 0,4,address_1,1
        BANK_TAIL 1,6,address_2,2
        CELL 0x8300,high_second,1,1
        BANK_TAIL 2,1,address_3,3
        BANK_TAIL 3,3,address_4,4
        CELL 0x8400,low_first,0,0
        BANK_TAIL 4,7,address_5,5
        BANK_TAIL 5,2,address_6,6
        CELL 0x8500,low_second,0,1
        BANK_TAIL 6,5,address_7,7
        BANK_TAIL 7,0,address_0,0
code_end:
        ASSERT $ <= 0x8600
        DS 0x8600-$
tables: MDAT "decoder-table.bin"
        ASSERT $ == 0x9C40
        DS 0x9D00-$
screen_data: MDAT "screen.bin"
player_end:
        ASSERT $ == 0xB800
