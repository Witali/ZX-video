        ORG 0x8000
start:  DI
        LD SP,0x6000
        LD IY,0x5C3A
        LD A,19
        LD BC,0x7FFD
        OUT (C),A
        LD DE,258
        LD HL,0xC000
        LD BC,512
read_begin:
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
        LD A,H
        OR A
        JR NZ,destination_ready
        LD H,0xC0
destination_ready:
        INC E
        BIT 4,E
        JR Z,sector_ready
        LD E,0
        INC D
sector_ready:
        DEC BC
        LD A,B
        OR C
        JR NZ,loop
read_end:
        JP read_end
        ASSERT $ <= 0x8100
        DS 0x8100-$
