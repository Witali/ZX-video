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
