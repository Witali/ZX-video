; Adaptive transient TR-DOS controller; no cache work during audio.
; Transient TR-DOS controller. Never resident during PDM playback.
; Bank5:4000..49FF controller,4A00 header,4C00 incoming header.
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
        DI
        LD SP,0x6000
        LD IY,0x5C3A
        IM 1
        XOR A
        LD (slot),A
        LD (cache_mode),A
        LD (cache_progress_enabled),A
        LD HL,0
        LD (cache_count),HL
        LD HL,initial_volume
        LD (expected_volume),HL
        EI
        CALL read_header
        ; Display the independently stored cover before probing/loading audio.
        LD A,31
        LD (load_bank),A
        LD BC,0x7FFD
        OUT (C),A
        LD DE,cover_disk
        LD HL,0xC000
        LD B,27
        CALL read_n
cover_visible:
        CALL cache_detect
        LD HL,(expected_volume)
        LD (cache_volume),HL
        JP choose_part

choose_part:
        LD A,(slot)
        LD HL,0x4a1c
        CP (HL)
        JR C,load_part
        LD HL,(expected_volume)
        LD DE,(0x4a1a)          ; number of disks in this series
        OR A
        SBC HL,DE
        JR Z,end_audio
        LD HL,(expected_volume)
        INC HL
        LD (expected_volume),HL
        LD HL,0x4a80           ; INSERT DISK NNNN
        CALL show
        LD HL,space_message
        LD DE,0xC060
        CALL print
swap_prompt:
        CALL wait_space
key_accepted:
        CALL read_header
        ; A new volume is independently pictured before its first audio load.
        LD A,31
        LD (load_bank),A
        LD BC,0x7FFD
        OUT (C),A
        LD DE,cover_disk
        LD HL,0xC000
        LD B,27
        CALL read_n
continuation_cover_visible:
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
        LD A,(slot)
        ADD A,A
        LD L,A
        LD H,0
        LD DE,0x4a20
        ADD HL,DE
        LD E,(HL)
        INC HL
        LD D,(HL)
        LD (record_disk),DE
        LD HL,(0x4B40)
        LD (cache_disk_end),HL
        LD A,(slot)
        ADD A,A
        LD L,A
        LD H,0
        LD DE,0x4ac0
        ADD HL,DE
        LD E,(HL)
        INC HL
        LD D,(HL)
        LD HL,(record_disk)
        PUSH DE
        LD D,H
        LD E,L
        CALL cache_linear
        POP DE
        LD A,24
        LD (cache_destination_page),A
        CALL cache_begin_progress
        LD DE,(record_disk)
        LD BC,0x7FFD
        LD A,24                ; bank 0 with the shadow screen still visible
        OUT (C),A
        LD (load_bank),A
        LD HL,0x8000
        LD B,97                ; code64 + screen27 + compressed controller6 sectors
        CALL read_n
player_loaded:
        DI
        JP 0x8000

; Only a complete same-volume cached record may bypass physical identity
; checks. Otherwise authenticate the inserted disk before any audio reads.
read_header:
        XOR A
        LD (cache_progress_enabled),A
        LD HL,(expected_volume)
        LD DE,initial_volume
        OR A
        SBC HL,DE
        JR NZ,read_header_rom
        LD HL,(cache_volume)
        OR A
        SBC HL,DE
        JR NZ,read_header_rom
        LD HL,header_seed
        LD DE,0x4a00
        LD BC,512
        LDIR
        LD A,(slot)
        LD HL,0x4a1c
        CP (HL)
        JP NC,header_accepted
        ADD A,A
        LD L,A
        LD H,0
        LD DE,0x4a20
        ADD HL,DE
        LD E,(HL)
        INC HL
        LD D,(HL)
        CALL cache_linear
        LD DE,(cache_start)
        OR A
        SBC HL,DE
        JR C,read_header_rom
        LD A,(slot)
        ADD A,A
        LD L,A
        LD H,0
        LD DE,0x4ac0
        ADD HL,DE
        LD E,(HL)
        INC HL
        LD D,(HL)
        LD HL,(cache_start)
        LD BC,(cache_count)
        ADD HL,BC
        OR A
        SBC HL,DE
        JP NC,header_accepted
read_header_rom:
        LD A,24
        LD (load_bank),A
        LD DE,header_disk
        LD HL,0x4c00
        LD B,2
        CALL read_n
        LD HL,0x4c00
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
        LD A,(0x4c1c)
        OR A
        JR Z,wrong_disk
        CP 33
        JR NC,wrong_disk
        LD HL,0x4c00
        LD DE,0x4a00
        LD BC,512
        LDIR
        LD HL,(expected_volume)
        LD DE,(cache_volume)
        OR A
        SBC HL,DE
        JR Z,header_accepted
        LD HL,0
        LD (cache_count),HL
        LD HL,(expected_volume)
        LD (cache_volume),HL
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
        JP read_header

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
        LD A,(load_bank)
        CALL cache_read_sector
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
        PUSH BC
        PUSH HL
        CALL cache_progress
        POP HL
        POP BC
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
load_bank: DEFB 24
record_disk: DEFW 0
        INCLUDE "ram-cache.asm"
header_seed: MDAT "header-seed.bin"
code_end:
        ASSERT $ <= 0x49FF
        DS 0x49FF-$
        DEFB 0


