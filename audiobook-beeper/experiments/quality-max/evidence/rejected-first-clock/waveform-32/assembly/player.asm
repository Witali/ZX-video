; G.711 mu-law bytes stay compressed in banked RAM. Inverse companding
; is pipelined one sample ahead through two 256-byte lookup planes.
; Main HL: 16-bit modulo error, DE: unsigned decoded level, BC: 10FE.
; Alternate BC: source cursor, HL: lookup cursor, DE: next level.
; SP transfers just one level (two bytes); no expanded PCM/PDM buffer.
; DI throughout playback. No calls and no input-dependent pulse branches.
        INCLUDE "config.inc"
        ORG 0x8000
LOAD_AUDIO: MACRO
        LD BC,0x7FFD
        LD A,\0+24
        OUT (C),A
        LD (load_bank),A
        LD DE,\1
        LD HL,\2
        LD B,\3
        CALL read_n
        ENDM
SILENCE: MACRO
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
        LD BC,0x7FFD
        LD A,31
        OUT (C),A
        LD HL,0x4000
        LD DE,0xC000
        LD BC,6912
        LDIR
        LD HL,0xD800
        LD B,96
show_loading:
        LD (HL),0x47
        INC L
        DJNZ show_loading
        LD HL,0xD8A0
        LD B,32
show_progress:
        LD (HL),0x08
        INC L
        DJNZ show_progress
loading_visible:
        EI
        INCLUDE "loads.inc"
        DI
        LD BC,0x7FFD
        LD A,31
        OUT (C),A
        LD HL,0xD800
        LD B,96
hide_loading:
        LD (HL),0
        INC L
        DJNZ hide_loading
        LD HL,0xD8A0
        LD B,32
hide_progress:
        LD (HL),0
        INC L
        DJNZ hide_progress
loading_hidden:
        SILENCE 8
        SILENCE 9
        SILENCE 10
        LD BC,0x7FFD
        LD A,24
        OUT (C),A
        EI
        HALT
        DI
ready:  LD SP,0x8800
        LD BC,first_address
        LD A,(BC)
        INC BC
        LD L,A
        LD H,levels >> 8
        LD E,(HL)
        INC H
        LD D,(HL)
        DEC H
        PUSH DE
        LD IX,bank_tail_0
        EXX
        POP DE
        LD HL,32768
        LD BC,0x10FE
; One exact 16-bit first-order decision takes 34 T: ADD 11, SBC 4,
; AND 7, OUT 12. Carry is consumed immediately. The table retains all
; decoded bits, including small G.711 levels near silence.
PULSE: MACRO
        ASSERT \0 >= 0
        ADD HL,DE
        SBC A,A
        AND 16
out_\0: OUT (C),A
        ENDM
sample:
        PULSE 0
        EXX
        LD A,(BC)
        LD L,A
        EXX                    ; 19 T prefetch: next compact code
        PULSE 1
        EXX
        LD E,(HL)
        INC H
        EXX                    ; 19 T: next low decoded byte
        PULSE 2
        EXX
        LD D,(HL)
        DEC H
        EXX                    ; 19 T: next high decoded byte
        PULSE 3
        EXX
        PUSH DE
        EXX                    ; 19 T: stage two bytes, not the audio
        PULSE 4
        EXX
        INC C
        JP Z,advance_page
resume_cursor:
        EXX                    ; ordinary cursor update: 22 T
        PULSE 5
        LD A,0
        LD A,0
        LD A,0                 ; 21 T padding; flags/data irrelevant
        PULSE 6
        LD A,0
        LD A,0
        LD A,0                 ; 21 T padding
        PULSE 7
        POP DE
        JP sample              ; 20 T; current level changes only here
; Page check happens after prefetch, one sample before a section ends.
; This also handles bank 5's C000..DBFF range without touching TR-DOS.
advance_page:
        INC B
        LD A,B
end_page_compare:
        CP first_end_high
        JP Z,bank_dispatch
        JP resume_cursor
bank_dispatch:
        JP (IX)
; Alternate registers are active here. Preserve lookup H/L; replace only
; the input cursor, paging latch, terminal high byte and next tail target.
BANK_TAIL: MACRO
bank_tail_\0: ASSERT 1
        LD BC,0x7FFD
        LD A,\1+24
page_\0: OUT (C),A
        LD BC,\2
        LD IX,bank_tail_\3
        LD A,\4
        LD (end_page_compare+1),A
        JP resume_cursor
        ENDM
        INCLUDE "tails.inc"
; All disk reads finish before modulation. 5C00..5FFF stays reserved for
; ROM variables and the load-time stack. The displayed screen is bank 7.
read_n: LD (disk_position),DE
read_next:
        PUSH BC
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
        CALL update_progress
        DJNZ read_next
        RET
disk_position: DW 0
update_progress:
        PUSH HL
        LD HL,progress_remaining
        DEC (HL)
        JR NZ,progress_return
        PUSH BC
        DI
        LD BC,0x7FFD
        LD A,31
        OUT (C),A
        LD A,(load_progress)
        ADD A,0xA0
        LD L,A
        LD H,0xD8
        LD (HL),0x20
        LD HL,load_progress
        INC (HL)
load_progress_event:
        LD A,(load_bank)
        OUT (C),A
        LD HL,(progress_cursor)
        LD A,(HL)
        LD (progress_remaining),A
        INC HL
        LD (progress_cursor),HL
        EI
        POP BC
progress_return:
        POP HL
        RET
load_bank: DB 31
load_progress: DB 0
progress_remaining: DB progress_first
progress_cursor: DW progress_steps
progress_steps: MDAT "progress-steps.bin"
        ASSERT $ <= 0x8500
        DS 0x8500-$
levels: MDAT "levels.bin"
resident_end:
        ASSERT $ == 0x8700
        DS 0x8800-$             ; playback stack; only 87FE..87FF written
screen_data: MDAT "screen.bin"
