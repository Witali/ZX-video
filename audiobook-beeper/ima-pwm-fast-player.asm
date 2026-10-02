; Fast PWM with first-order error feedback: 30-T /40-T high pulses.
; The 8-bit PCM target is represented by the mean width over successive
; periods, not by sixteen widths in each period. Both paths have equal cost.
; Main BC=10FEh, D=current PCM8, E=0, HL=input; A'=width error accumulator.
; Main AF=decoder scratch, IX=biased PCM16, IY=bank dispatch.
; Alternate HL=clean IMA table row, BC=delta. SP=read-only table cursor.
; Guard every predictor addition on the host; interrupts remain disabled.
;
; Each PWM kernel costs56 T: OUT12 +EX4 +ADD4 +JP10 +OUT12 +JP10 +EX4.
; Narrow path delays AFTER falling, wide path BEFORE falling. High30/40 T.
; Ordinary periods [84,84,84,87,84] total423 T/sample (old PDM438).
; Page adds84 T. Nonfinal bank periods total934 T; final bank931 T.
; All counts exclude ULA I/O/data waits and startup TR-DOS/disk latency.

        INCLUDE "config.inc"
        ORG 0x8000

PULSE:  MACRO
\0:    OUT (C),B               ; 12: rising edge, B=16
        EX AF,AF'               ; 4: preserve decoder flags/candidate
        ADD A,D                 ; 4: width error feedback, modulo256
        JP C,\0_wide           ; 10 for both outcomes
\0_narrow: OUT (C),E           ; 12: E=0, high pulse30 T
        JP \0_done             ; 10: balancing delay after falling
\0_wide: JP \0_wide_fall      ; 10: same delay before falling
\0_wide_fall: OUT (C),E        ; 12: high pulse40 T
\0_done: EX AF,AF'             ; 4: restore decoder, save width error
        ENDM

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
ready:  LD HL,address_0
        EXX
        LD HL,tables+64*initial_index
        EXX
        LD IX,initial_predictor+32768
        LD IY,bank_tail_0

; Prime first sample with the same guarded recurrence and clean row table.
        LD A,(HL)
        EXX
        AND 15
        RLCA
        RLCA
        OR L
        LD L,A
        LD SP,HL
        POP BC
        POP HL
        ADD IX,BC
        EXX
        LD A,IXH
        LD BC,0x10FE
        LD D,A
        LD E,0
        EX AF,AF'
        LD A,128
        EX AF,AF'
        JP high

HEAD:   MACRO
        PULSE \0_out0
        LD A,(HL)               ; 7
        IF \1 == 0
        AND 15                  ; 7
        RLCA                    ; 4
        RLCA                    ; 4
        ELSE
        AND 240                 ; 7
        RRCA                    ; 4
        RRCA                    ; 4
        ENDIF
        INC SP                  ; 6: old table cursor dead; work28
        PULSE \0_out1
        EXX                     ; 4
        OR L                    ; 4
        LD L,A                  ; 4
        LD SP,HL                ; 6
        LD SP,HL                ; 6: harmless duplicate for work28
        EXX                     ; 4
        PULSE \0_out2
        EXX                     ; 4
        POP BC                  ; 10
        POP HL                  ; 10
\0_state: EXX                  ; 4: work28; state visible before EXX
        PULSE \0_out3
        EXX                     ; 4
        ADD IX,BC               ; 15: guarded, no clipping branch
        EXX                     ; 4
        LD A,IXH                ; 8: work31, this period is87 T
\0_clipped: ASSERT 1
        PULSE \0_out4
        ENDM

low:    HEAD low,0
        LD D,A                  ; 4: publish only after all old-level pulses
        NOP                     ; 4
        JP low_next             ; 10
low_next:
        JP high                 ; 10: work28

high:   HEAD high,1
        INC L                   ; 4
        JP NZ,high_address_ok   ; 10
        INC H                   ; 4
        JP Z,bank_dispatch      ; 10: work28 before next PWM edge
page_finish:
        PULSE page_out5
        LD D,A                  ; 4
        NOP                     ; 4
        JP page_next            ; 10
page_next:
        JP low                  ; 10: extra full period at page crossing
high_address_ok:
        LD D,A                  ; 4
        JP low                  ; 10: normal high work4+10+4+10=28

bank_dispatch:
        PULSE bank_out5
        LD (bank_candidate),A   ; 13: preserve candidate through paging
        LD A,0                  ; 7: scratch
        JP (IY)                 ; 8: work28

BANK_TAIL: MACRO
bank_tail_\0: ASSERT 1
        PULSE bank_\0_out6
        EXX                     ; 4
        LD BC,0x7FFD            ; 10
        LD A,\1+16             ; 7
        EXX                     ; 4
        NOP                     ; 4: work29, period85
        PULSE bank_\0_out7
        EXX                     ; 4
page_\0: OUT (C),A             ; 12: real paging latch write
        EXX                     ; 4
        NOP                     ; 4
        NOP                     ; 4: work28
        PULSE bank_\0_out8
        LD H,\2 >> 8           ; 7: L already zero
        LD IY,bank_tail_\3      ; 14
        IF \0 == 7
        LD A,0                  ; 7: work28
        PULSE bank_\0_out9
        EXX                     ; 4
        LD HL,tables+64*initial_index ; 10
        EXX                     ; 4
        LD IX,initial_predictor+32768 ; 14: work32
        PULSE bank_\0_out10
        JP bank_finish          ; 10, shared remainder below
        ELSE
        JP bank_common          ; 10: work31, +3 T to share two PWM stages
        ENDIF
        ENDM
        BANK_TAIL 0,4,address_1,1
        BANK_TAIL 1,6,address_2,2
        BANK_TAIL 2,1,address_3,3
        BANK_TAIL 3,3,address_4,4
        BANK_TAIL 4,7,address_5,5
        BANK_TAIL 5,2,address_6,6
        BANK_TAIL 6,5,address_7,7
        BANK_TAIL 7,0,address_0,0
bank_common:
        PULSE bank_out9
        DS 8                    ; 32 T: match final predictor reset
        PULSE bank_out10
        JP bank_finish
bank_finish:
bank_candidate: EQU $+1
        LD D,0                  ; 7: saved candidate, direct publication
        JP low                  ; 10: work10+7+10=27, period83

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
code_end:
        ASSERT $ <= 0x8600
        DS 0x8600-$
tables: MDAT "decoder-table.bin"
        ASSERT $ == 0x9C40
        DS 0x9D00-$
screen_data: MDAT "screen.bin"
player_end:
        ASSERT $ == 0xB800
