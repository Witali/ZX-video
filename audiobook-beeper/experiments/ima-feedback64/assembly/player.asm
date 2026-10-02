; Live guarded IMA + eight-bit block error-feedback PDM.
; Authoritative instruction source, assembled externally by pyz80.
; Main E = rotating output byte; B = twice the 6-bit feedback state;
; C = next output byte; D/HL/AF = scratch; IY = packed input cursor.
; Alternate HL = IMA row, BC = signed delta; IX = biased PCM16.
; SP is a read-only table cursor during playback. No CALL/PUSH/IRQ then.
; A table lookup computes eight new bits AND the next feedback state.
; This is live conversion, not a stored or unpacked PDM soundtrack.
;
; Four input bytes are unrolled. Low halves take 428 T; the first three
; high halves take 436 T, the fourth 446 T: mean 433.25 T/sample.
; Previous feedback kernel: 437 T; standard six-slot PDM: 438 T.
; Holds: 49,53,56,58,53,56,59, then 44 (low), 52/62 (high).
; Counts exclude ULA contention, ROM and physical disk latency.
        INCLUDE "config.inc"
        ORG 0x8000

PULSE: MACRO
        ASSERT \0 >= 0
        RLC E                   ; 8: MSB-first, byte returns after eight bits
        SBC A,A                 ; 4: carry to 00/FF
        AND 16                  ; 7: EAR only, MIC/border zero
\0:     OUT (0xFE),A            ; 11: total 30 T, AF is scratch
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
        LOAD_BANK 5,disk_6,address_6,sectors_6
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
ready:  LD IY,address_0
        EXX
        LD HL,tables+64*initial_index
        EXX
        LD IX,initial_predictor+32768
        LD HL,bank_tail_0
        LD (bank_jump+1),HL
; Prime PCM0, then create its first output byte and feedback successor.
        LD A,(IY+0)
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
        LD B,initial_feedback*2
        LD A,IXH
        LD L,A
        LD H,pointer_low >> 8
        LD D,(HL)
        INC H
        LD H,(HL)
        LD A,D
        OR B
        LD L,A
        LD SP,HL
        POP BC
        LD E,C
        JP high

HALF: MACRO
        PULSE \0_out0
        LD D,(IY+0)             ; 19: cached input survives pulse AF
        PULSE \0_out1
        LD A,D                  ; 4
        IF \1 == 0
        AND 15                  ; 7
        RLCA                    ; 4
        RLCA                    ; 4
        ELSE
        AND 240
        RRCA
        RRCA
        ENDIF
        LD D,A                  ; 4: total 23
        PULSE \0_out2
        LD A,D                  ; 4
        EXX                     ; 4
        OR L                    ; 4: clean 64-byte-aligned IMA row
        LD L,A                  ; 4
        LD SP,HL                ; 6
        EXX                     ; 4: total 26
        PULSE \0_out3
        EXX                     ; 4
        POP BC                  ; 10: signed IMA delta
        POP HL                  ; 10: next row
\0_state: EXX                   ; 4: total 28
        PULSE \0_out4
        EXX                     ; 4
        ADD IX,BC               ; 15: builder proves no saturation
        EXX                     ; 4: total 23
\0_sample: ASSERT 1
        PULSE \0_out5
        LD A,IXH                ; 8: exact high byte of biased PCM16
        LD L,A                  ; 4: DD-prefixed LD L,IXH is not encodable
        LD H,pointer_low >> 8    ; 7
        LD D,(HL)               ; 7: table base low byte, total 26
        PULSE \0_out6
        INC H                   ; 4: pointer-high page
        LD H,(HL)               ; 7
        LD A,D                  ; 4
        OR B                    ; 4: combine PCM row and feedback state
        LD L,A                  ; 4
        LD SP,HL                ; 6: total 29
        PULSE \0_out7
        POP BC                  ; 10: C=new word, B=twice next state
        LD E,C                  ; 4: publish after eight old-word pulses
        ENDM

low:    HALF low,0               ; fall through: saves 10 T per input byte
high:   HALF high,1
        INC IYL                 ; 8: group alignment proves no page edge
low1:   HALF low1,0
high1:  HALF high1,1
        INC IYL                 ; skip the repeated branch/low-byte test
low2:   HALF low2,0
high2:  HALF high2,1
        INC IYL
low3:   HALF low3,0
high3:  HALF high3,1
        INC IYL                 ; 8: flags consumed before next pulse
        JP NZ,low               ; 10: ordinary high tail total 32 T
        INC IYH                 ; 8
        JP NZ,low               ; 10: page crossing adds 18 T

; At a bank edge, repeat the last sample's byte once while paging.
; It is exactly eight additional bits, so E returns to the original word.
; The feedback state is NOT advanced by that short duplicate block.
        PULSE bank_out0          ; last ordinary hold is 80 T
bank_jump: JP bank_tail_0        ; the only playback write is this operand

BANK_TAIL: MACRO
bank_tail_\0: ASSERT \0 >= 0
        LD D,\1+16              ; 7: page value survives PULSE's AF use
        EXX                     ; 4
        LD BC,0x7FFD             ; 10: alternate delta is now dead
        EXX                     ; 4: plus dispatch JP =35 T
        PULSE bank_\0_out1
        LD A,D                  ; 4
        EXX                     ; 4
page_\0: OUT (C),A              ; 12
        EXX                     ; 4: total 24
        PULSE bank_\0_out2
        LD IY,\2                ; 14
        PULSE bank_\0_out3
        LD HL,bank_tail_\3       ; 10
        LD (bank_jump+1),HL      ; 16
        PULSE bank_\0_out4
        IF \0 == 6
        EXX                     ; reset only IMA at wrap, retain feedback
        LD HL,tables+64*initial_index
        EXX                     ; 18 T
        ELSE
        LD HL,0                 ; scratch + NOPs, also 18 T
        NOP
        NOP
        ENDIF
        PULSE bank_\0_out5
        IF \0 == 6
        LD IX,initial_predictor+32768 ; 14 T
        ELSE
        LD HL,0
        NOP                     ; 14 T
        ENDIF
        PULSE bank_\0_out6
        LD HL,0
        LD D,0
        NOP                     ; 21 T, scratch values are dead
        PULSE bank_\0_out7
        LD HL,0
        NOP
        JP low                  ; 24 T
        ENDM
        BANK_TAIL 0,4,address_1,1
        BANK_TAIL 1,6,address_2,2
        BANK_TAIL 2,1,address_3,3
        BANK_TAIL 3,3,address_4,4
        BANK_TAIL 4,7,address_5,5
        BANK_TAIL 5,5,address_6,6
        BANK_TAIL 6,0,address_0,0

; Startup only: real stack below 6000, no reads during playback.
read_n: PUSH BC
        PUSH HL
        LD DE,(disk_position)
        LD BC,0x0105
disk_call: CALL 0x3D13
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
        ASSERT $ <= 0x8700
        DS 0x8700-$
tables: MDAT "decoder-table.bin"
        ASSERT $ == 0x9D40
        DS 0x9E00-$
pointer_low: MDAT "pointer-low.bin"
pointer_high: MDAT "pointer-high.bin"
        ASSERT $ == 0xA000
feedback: MDAT "feedback.bin"
        ASSERT $ == 0xC000
screen_data: MDAT "screen.bin"
player_end:
        ASSERT $ == 0xDB00
