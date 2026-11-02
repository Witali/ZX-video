; The TR-DOS command interpreter clears SCREEN$ when another BASIC LOAD is
; issued. This small first-stage loader displays its embedded first picture,
; then reads PLAYER through the sector API, which does not clear the screen.
; It lives in fixed RAM5; its 1KiB stack gap above the SCR is not overwritten
; by the destination 8000..BFFF. All AF/BC/DE/HL are scratch; IY is ROM SYSVARS.
        ORG 0x6000
loader: DI
        LD SP,0x8000
        LD IY,0x5C3A
        LD A,16
        LD BC,0x7FFD
        OUT (C),A
        LD A,6
        OUT (0xFE),A
        LD HL,0x6100
        LD DE,0x4000
        LD BC,6912
        LDIR
        INCLUDE "loader-position.inc"
        LD (loader_position),DE
        LD HL,0x8000
        LD B,64
        IM 1
loader_read:
        PUSH BC
        PUSH HL
        LD DE,(loader_position)
        LD BC,0x0105
        EI
        CALL 0x3D13
        DI
        POP HL
        POP BC
        INC H
        LD DE,(loader_position)
        INC E
        BIT 4,E
        JR Z,loader_sector_ok
        LD E,0
        INC D
loader_sector_ok:
        LD (loader_position),DE
        DJNZ loader_read
        JP 0x8000
loader_position: DEFW 0
        ASSERT $ <= 0x6100
        DS 0x60FF-$
        DEFB 0
