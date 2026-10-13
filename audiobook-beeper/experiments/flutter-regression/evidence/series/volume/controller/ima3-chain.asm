; Transient TR-DOS controller. Never resident during PDM playback.
; Bank 5: 4000..47FF code, 4800 header, 4A00 incoming header.
; It loads a complete independently runnable PLAYER into bank 2/bank 0,
; then that player's normal loader fills the audio banks and replaces us.
        INCLUDE "chain-config.inc"
        ORG 0x4000
        JP cold_start
        DEFM "IMA3CHN1"
resume_entry:
        ASSERT $ == 0x400B
        DI
        LD SP,0x6000
        LD IY,0x5C3A
        IM 1
        LD (slot),A
        LD (expected_volume),HL
        EI
        CALL read_header
        JP choose_part
cold_start:
        LD HL,initial_volume
        XOR A
        JP resume_entry

choose_part:
        LD A,(slot)
        LD HL,0x481C
        CP (HL)
        JR C,load_part
        LD HL,(expected_volume)
        LD DE,(0x481A)          ; number of disks in this series
        OR A
        SBC HL,DE
        JR Z,end_audio
        LD HL,(expected_volume)
        INC HL
        LD (expected_volume),HL
        LD HL,0x4880           ; INSERT DISK NNNN
        CALL show
        LD HL,space_message
        LD DE,0xC060
        CALL print
swap_prompt:
        CALL wait_space
key_accepted:
        CALL read_header
        XOR A
        LD (slot),A
        JR choose_part
end_audio:
        LD HL,end_message
        CALL show
finished:
        HALT
        JR finished

load_part:
        LD HL,loading_message
        CALL show
        LD A,(slot)
        ADD A,A
        LD L,A
        LD H,0
        LD DE,0x4820
        ADD HL,DE
        LD E,(HL)
        INC HL
        LD D,(HL)
        LD BC,0x7FFD
        LD A,24                ; bank 0 with the shadow screen still visible
        OUT (C),A
        LD HL,0x8000
        LD B,91                ; 16 KiB player + 6912-byte screen
        CALL read_n
player_loaded:
        DI
        JP 0x8000

read_header:
        LD DE,header_disk
        LD HL,0x4A00
        LD B,2
        CALL read_n
        LD HL,0x4A00
        LD DE,identity
        LD B,24                ; magic and 128-bit series identity
check_identity:
        LD A,(DE)
        CP (HL)
        JR NZ,wrong_disk
        INC HL
        INC DE
        DJNZ check_identity
        LD DE,(expected_volume)
        LD A,(HL)
        CP E
        JR NZ,wrong_disk
        INC HL
        LD A,(HL)
        CP D
        JR NZ,wrong_disk
        LD A,(0x4A1C)
        OR A
        JR Z,wrong_disk
        CP 33
        JR NC,wrong_disk
        LD HL,0x4A00
        LD DE,0x4800
        LD BC,512
        LDIR
header_accepted:
        RET
wrong_disk:
        LD HL,wrong_message
        CALL show
        LD HL,space_message
        LD DE,0xC060
        CALL print
wrong_disk_prompt:
        CALL wait_space
        JR read_header

wait_space:
        LD BC,0x7FFE
key_release:
        IN A,(C)
        AND 1
        JR Z,key_release
key_press:
        HALT
        IN A,(C)
        AND 1
        JR NZ,key_press
        RET

show:
        PUSH HL
        LD BC,0x7FFD
        LD A,31
        OUT (C),A
        LD HL,0xC000
        LD DE,0xC001
        LD BC,6143
        LD (HL),0
        LDIR
        LD HL,0xD800
        LD DE,0xD801
        LD BC,767
        LD (HL),0x47
        LDIR
        POP HL
        LD DE,0xC040
print:
        LD A,(HL)
        OR A
        RET Z
        INC HL
        PUSH HL
        LD L,A
        LD H,0
        ADD HL,HL
        ADD HL,HL
        ADD HL,HL
        LD BC,0x3C00           ; 48K ROM font, selected by paging value 31
        ADD HL,BC
        PUSH DE
        LD B,8
glyph:
        LD A,(HL)
        LD (DE),A
        INC HL
        INC D
        DJNZ glyph
        POP DE
        INC E
        POP HL
        JR print

; Same sector progression as the proven player loader. ROM/disk latency
; belongs to the between-part pause, not the PDM CPU timing budget.
read_n:
        LD (disk_position),DE
read_next:
        PUSH BC
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
        DJNZ read_next
        RET
slot: DEFB 0
expected_volume: DEFW 0
disk_position: DEFW 0
identity: MDAT "identity.bin"
loading_message: DEFM "LOADING AUDIO DATA",0
space_message: DEFM "THEN PRESS SPACE",0
wrong_message: DEFM "WRONG DISK - TRY AGAIN",0
end_message: DEFM "END OF AUDIO",0
code_end:
        ASSERT $ <= 0x47FF
        DS 0x47FF-$
        DEFB 0
