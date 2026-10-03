; Runs in temporary bank5 workspace after the final IMA byte is produced.
; It may overwrite the old decoder in bank2, then enters the normal player.
        INCLUDE "lpc-config.inc"
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
