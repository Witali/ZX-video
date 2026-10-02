; Standard accumulator PDM, six slots/sample, with uniform ordinary timing.
; Assemble externally with pyz80. This variant REQUIRES a host proof that
; no signed IMA predictor addition clips, including the initial state.
; No RC model, no change to the PCM8 values or PDM error recurrence.
;
; Main BC=10FEh, D=current PCM8, E=three-slot bit pipeline, HL=input.
; A'=PDM error; main AF=decoder scratch, IX=biased PCM16, IY=bank dispatch.
; Alternate HL=clean table row, BC=delta. SP is a READ-ONLY table cursor.
; IRQs disabled. Never CALL/PUSH/return during playback. RET C below is
; provably NOT TAKEN (5 T): comments identify the preceding carry clear.
; INC SP (6 T) is used only while the old cursor is dead, before LD SP,HL.
; LD A,R (9 T) is read-only padding after publication; its value is dead.
;
; Counted from Z80 instruction timings, excluding ULA/ROM/disk latency:
; Ordinary low/high: 438/438 T, both [73]*6, versus old 439/437 T.
; Page: [73,73,73,73,73,74,73] =512 T, +74 vs ordinary (old +76).
; Bank: [73,73,73,73,73,72,77,67,73,72,73] =799 T, +361 (old +362).
; Full loop: 438*N +74*(pages-banks)+361*banks =101175126 T,
; versus 101176020 T (-894). Max native hold 77 vs79 (-2).
; The short 67-T paging slot reserves headroom for two ULA-contended OUTs.

        INCLUDE "config.inc"
        ORG 0x8000

PULSE:  MACRO
        ASSERT \0 >= 0
        EX AF,AF'               ; 4
        ADD A,D                 ; 4: original first-order accumulator
        RR E                    ; 8: three-slot output pipeline
        RES 3,E                 ; 8: MIC and border remain zero
\0:     OUT (C),E               ; 12
        EX AF,AF'               ; 4: total 40 T, preserves decoder AF
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
        RLCA                    ; 4: carry CLEAR for masked low nibble
        ELSE
        AND 240                 ; 7
        RRCA                    ; 4
        RRCA                    ; 4: carry CLEAR for masked high nibble
        ENDIF
        INC SP                  ; 6: old cursor dead; next slot replaces it
        RET C                   ; 5: NEVER taken. Slot work =33 T
        PULSE \0_out1
        EXX                     ; 4
        OR L                    ; 4: clean row, also CLEAR carry
        LD L,A                  ; 4
        LD SP,HL                ; 6
        EXX                     ; 4
        LD A,0                  ; 7: scratch A no longer needed
        NOP                     ; 4: slot work =33 T
        PULSE \0_out2
        EXX                     ; 4
        POP BC                  ; 10
        POP HL                  ; 10: clean next row, no sign tag
\0_state: EXX                   ; 4: Fuse captures row before EXX
        RET C                   ; 5: NEVER taken; OR L cleared carry
        PULSE \0_out3
        EXX                     ; 4
        ADD IX,BC               ; 15: guarded against signed overflow
        EXX                     ; 4
        JP \0_add_done          ; 10: slot work =33 T
\0_add_done: ASSERT 1
        PULSE \0_out4
        LD A,IXH                ; 8: preserve candidate in decoder A
        OR A                    ; 4: CLEAR carry, candidate unchanged
        IF \1 == 0
        RET C                   ; 5: NEVER taken
        NOP                     ; 4
        NOP                     ; 4
        NOP                     ; 4
        NOP                     ; 4: low slot work =33 T
        ELSE
        INC L                   ; 4: Z records page edge, carry stays clear
        RET C                   ; 5: NEVER taken; preserves Z
        JR \0_address_done      ; 12: high slot work =33 T
\0_address_done: ASSERT 1
        ENDIF
\0_clipped: ASSERT 1             ; verifier candidate marker (no clipping)
        PULSE \0_out5
        ENDM

low:    HEAD low,0
        LD D,A                  ; 4: publish only after all six old-level slots
        LD A,R                  ; 9: scratch result/flags are dead
        JP low_next             ; 10
low_next:
        JP high                 ; 10: low slot work =33 T

high:   HEAD high,1
        JP NZ,high_address_ok   ; 10, both outcomes
        INC H                   ; 4
        JP Z,bank_dispatch      ; 10
        JP page_finish          ; 10: page path =34 T (74-T hold)
high_address_ok:
        LD D,A                  ; 4
        LD A,R                  ; 9
        JP low                  ; 10: ordinary high work =33 T

page_finish:
        PULSE page_out6
        LD D,A                  ; 4: A still contains the candidate
        LD A,R                  ; 9
        JP page_next            ; 10
page_next:
        JP low                  ; 10: 33-T work

bank_dispatch:
        JP (IY)                 ; bank path =10+4+10+8 =32 T

BANK_TAIL: MACRO
bank_tail_\0: ASSERT \0 >= 0
        PULSE bank_\0_out6
        LD (bank_candidate),A   ; 13: candidate already in A; old code reread IXH
        EXX                     ; 4
        LD BC,0x7FFD            ; 10
        EXX                     ; 4
        INC SP                  ; 6: cursor dead. Work37, hold77 vs old79
        PULSE bank_\0_out7
        EXX                     ; 4
        LD A,\1+16              ; 7
page_\0: OUT (C),A              ; 12
        EXX                     ; 4: hold67; leave contention headroom
        PULSE bank_\0_out8
        LD H,\2 >> 8            ; 7: input L is already zero
        LD IY,bank_tail_\3       ; 14
        JR bank_next_\0         ; 12: work33 /hold73
bank_next_\0: PULSE bank_\0_out9
        IF \0 == 7
        EXX                     ; 4
        LD HL,tables+64*initial_index ; 10
        EXX                     ; 4
        LD IX,initial_predictor+32768 ; 14: work32 /hold72
        ELSE
        NOP
        NOP
        NOP
        NOP
        NOP
        NOP
        NOP
        NOP                     ; 32 T
        ENDIF
        PULSE bank_\0_out10
        JP bank_finish          ; 10: shared remainder below
        ENDM
        BANK_TAIL 0,4,address_1,1
        BANK_TAIL 1,6,address_2,2
        BANK_TAIL 2,1,address_3,3
        BANK_TAIL 3,3,address_4,4
        BANK_TAIL 4,7,address_5,5
        BANK_TAIL 5,2,address_6,6
        BANK_TAIL 6,5,address_7,7
        BANK_TAIL 7,0,address_0,0
bank_finish:
bank_candidate: EQU $+1
        LD D,0                  ; 7: direct publication vs old LD A,n /LD D,A
        INC SP                  ; 6: cursor dead
        JP low                  ; 10: 10+7+6+10=33 T, hold73 vs old71

; Startup-only real-stack disk reader. No disk access while PDM is running.
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
