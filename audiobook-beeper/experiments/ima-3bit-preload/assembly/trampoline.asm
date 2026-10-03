; Temporary bank5 trampoline: replace the preloader without overwriting
; any of the seven resident IMA sections, including bank2 B800..BFFF.
        INCLUDE "ima3-config.inc"
        ORG 0x6000
        DI
        LD SP,0x5FF0
        LD IY,0x5C3A
        LD DE,player_disk
        LD HL,0x8000
        LD B,56
loop:   PUSH BC
        PUSH DE
        PUSH HL
        LD BC,0x0105
        EI
disk_call:
        CALL 0x3D13
        DI
        POP HL
        POP DE
        POP BC
        INC H
        INC E
        BIT 4,E
        JR Z,sector_ok
        LD E,0
        INC D
sector_ok:
        DJNZ loop
        JP 0x8000
