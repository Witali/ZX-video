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
