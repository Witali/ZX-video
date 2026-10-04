; Standalone AY50 player: all R0..R10 records are loaded before playback.
; Python supplies constants, screen pixels and register data, never opcodes.
; Bank 5: display/BASIC/TR-DOS. Bank 2: code, screen image, stack and IM2.
; Six other banks: whole 11-byte records. Interrupts preserve all registers.
        INCLUDE "config.inc"
        ORG 0x8000
LOAD_BANK: MACRO
        IF \2 > 0
        LD A,16+\0
        LD BC,0x7FFD
        OUT (C),A
        LD DE,\1
        LD (disk_position),DE
        LD HL,0xC000
        LD B,\2
        CALL read_n
        ENDIF
        ENDM
start:  DI
        LD SP,0xB800
        LD IY,0x5C3A
        IM 1
        XOR A
        OUT (0xFE),A
        LD HL,screen_data
        LD DE,0x4000
        LD BC,6912
        LDIR
        EI
        LOAD_BANK 0,disk_0,sectors_0
        LOAD_BANK 4,disk_1,sectors_1
        LOAD_BANK 6,disk_2,sectors_2
        LOAD_BANK 1,disk_3,sectors_3
        LOAD_BANK 3,disk_4,sectors_4
        LOAD_BANK 7,disk_5,sectors_5
        DI
        ; Erase the first three character rows containing the loading message.
        ; Spectrum bitmap scanlines are interleaved in eight 256-byte planes.
        ; This runs once after loading and costs nothing during playback.
        LD HL,0x4000
        LD B,8
clear_loading:
        PUSH BC
        PUSH HL
        LD D,H
        LD E,L
        INC DE
        LD BC,95
        LD (HL),0
        LDIR
        POP HL
        INC H
        POP BC
        DJNZ clear_loading
        ; Clear the chip, including its envelope, after loading from disk.
        LD D,0
        LD E,0
        LD C,0xFD
clear_ay:
        LD B,0xFF
        OUT (C),D
        LD B,0xBF
        OUT (C),E
        INC D
        LD A,D
        CP 14
        JR NZ,clear_ay
        LD HL,0xBE00
        LD DE,0xBE01
        LD BC,256
        LD (HL),0xBD
        LDIR
        LD A,0xC3
        LD (0xBDBD),A
        LD HL,irq
        LD (0xBDBE),HL
        LD A,0xBE
        LD I,A
        IM 2
        LD A,16
        LD BC,0x7FFD
        OUT (C),A
        LD HL,0xC000
ready:  EI
wait_field:
        HALT
field_start:
        ; 38 T. Each tick remains tied to its original interrupt field.
        LD DE,(remaining)
        LD A,D
        OR E
        JP Z,finished
tick_start:
        LD D,0
        LD C,0xFD
write_register:
        ; 78 T continuing, 73 T final; setup + eleven writes = 867 T.
        LD E,(HL)
        INC HL
        LD B,0xFF
        OUT (C),D
        LD B,0xBF
ay_out: OUT (C),E
        INC D
        LD A,D
        CP 11
        JR NZ,write_register
tick_end:
        LD DE,(remaining)
        DEC DE
        LD (remaining),DE
        LD A,H
        CP 0xFF
        JR NZ,wait_field
        LD A,L
        CP 0xFB
        JR NZ,wait_field
        ; Never read past the bank table on an exact-boundary EOF.
        LD A,D
        OR E
        JR Z,wait_field
        LD HL,(bank_pointer)
        INC HL
        LD (bank_pointer),HL
        LD A,(HL)
        LD BC,0x7FFD
        OUT (C),A
        LD HL,0xC000
        JR wait_field
finished:
        IF loop_playback
        ; 105 T beyond the normal field check, once per repeat.
        ; Reset then publish tick zero in THIS field: no empty extra field.
        LD DE,total_ticks
        LD (remaining),DE
        LD HL,bank_table
        LD (bank_pointer),HL
        LD A,16
        LD BC,0x7FFD
        OUT (C),A
        LD HL,0xC000
        JP tick_start
        ELSE
        LD E,0
        LD C,0xFD
        LD D,8
        LD B,0xFF
        OUT (C),D
        LD B,0xBF
        OUT (C),E
        LD D,9
        LD B,0xFF
        OUT (C),D
        LD B,0xBF
        OUT (C),E
        LD D,10
        LD B,0xFF
        OUT (C),D
        LD B,0xBF
        OUT (C),E
        ENDIF
finished_wait:
        HALT
        JR finished_wait
irq:    EI
        RETI
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
remaining: DEFW total_ticks
disk_position: DEFW 0
bank_pointer: DEFW bank_table
bank_table: DEFB 16,20,22,17,19,23
code_end:
        ASSERT $ <= 0x9000
        DS 0x9000-$
screen_data:
        MDAT "screen.bin"
        ASSERT $ == 0xAB00
