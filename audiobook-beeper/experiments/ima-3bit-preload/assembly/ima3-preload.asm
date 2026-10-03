; Read small three-bit IMA blocks, expand them directly into resident RAM.
; Fixed bank2: code8000..8FFF, four lookup pages9000..93FF, screen9400..AEFF.
; Bank5: screen4000..5AFF, ROM workspace/stack5B00..5FFF, input6000..77FF.
; Output is paged at C000. Bank2's final F800..FFFF aliases B800..BFFF,
; safely beyond this preloader. Nothing needs the complete input in RAM.
        INCLUDE "ima3-config.inc"
        ORG 0x8000
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
        LD DE,audio_disk
        LD (disk_position),DE
        LD HL,chunk_data
        LD (chunk_cursor),HL
chunk_loop:
        LD HL,(chunk_cursor)
        LD A,(HL)               ; output bank
        INC HL
        LD BC,0x7FFD
        OR 16                   ; ROM1, visible screen5, paging enabled
        OUT (C),A
        LD E,(HL)
        INC HL
        LD D,(HL)
        INC HL
        LD (output_address),DE
        LD B,(HL)               ; number of disk sectors for this block
        INC HL
        LD E,(HL)
        INC HL
        LD D,(HL)
        INC HL
        LD (group_count),DE     ; three input bytes -> four output bytes
        LD A,(HL)
        INC HL
        LD (unpack_target),A    ; completed output fraction, 0..32 cells
        LD (chunk_cursor),HL
        LD HL,0x6000
        CALL read_n
block_loaded:
        LD HL,0x6000
        LD DE,(output_address)
        LD IX,(group_count)
        CALL expand
block_expanded:
        CALL update_unpack
        LD A,(chunks_left)
        DEC A
        LD (chunks_left),A
        JP NZ,chunk_loop
unpack_complete:
        LD HL,trampoline_data
        LD DE,0x6000
        LD BC,trampoline_size
        LDIR
handoff:
        JP 0x6000               ; loader replaces8000..B7FF with the player

; The round-3 lookup core, unchanged at285 T per eight samples.
; CALL/RET and block setup/progress are outside that count.
expand:
group_loop:
        LD A,(HL)
        INC HL
        LD B,A
        LD A,(HL)
        INC HL
        LD C,A
        LD A,(HL)
        INC HL
        LD IYH,A
        PUSH HL
        LD L,B
        LD H,0x90
        LD A,(HL)
        LD (DE),A
        INC DE
        LD A,B
        AND 3
        RLCA
        RLCA
        LD B,A
        LD L,C
        INC H
        LD A,(HL)
        OR B
        LD (DE),A
        INC DE
        LD L,C
        INC H
        LD B,(HL)
        LD A,IYH
        RRCA
        AND 0x60
        OR B
        LD (DE),A
        INC DE
        LD A,IYH
        LD L,A
        INC H
        LD A,(HL)
        LD (DE),A
        INC DE
group_written:
        POP HL
        DEC IX
        LD A,IXH
        OR IXL
        JP NZ,group_loop
expand_end:
        RET

; Read through the real TR-DOS ROM. The preloader never holds IY scratch
; across this call: restore the ROM's system-variable pointer every time.
read_n: LD (disk_destination),HL
read_sector:
        PUSH BC
        LD IY,0x5C3A
        LD HL,(disk_destination)
        LD DE,(disk_position)
        LD BC,0x0105
        EI
disk_call:
        CALL 0x3D13
        DI
disk_return:
        LD HL,(disk_destination)
        INC H
        LD (disk_destination),HL
        LD DE,(disk_position)
        INC E
        BIT 4,E
        JR Z,sector_ok
        LD E,0
        INC D
sector_ok:
        LD (disk_position),DE
        LD HL,(sectors_read)    ; more than256 sectors: use a16-bit counter
        INC HL
        LD (sectors_read),HL
        EX DE,HL
        LD HL,(load_threshold_cursor)
        LD A,E
        CP (HL)
        JR NZ,load_no_update
        INC HL
        LD A,D
        CP (HL)
        JR NZ,load_no_update
        INC HL
        LD (load_threshold_cursor),HL
        LD A,(load_progress)
        LD C,A
        LD B,0
        LD HL,0x5940
        ADD HL,BC
        LD (HL),0x64
        INC A
        LD (load_progress),A
load_progress_event:
        NOP
load_no_update:
        POP BC
        DJNZ read_sector
        RET

; Update after each decoded block, outside the expansion hot loop.
update_unpack:
        LD A,(unpack_target)
        LD B,A
        LD A,(unpack_progress)
unpack_step:
        CP B
        RET Z
        LD L,A
        LD H,0x5A
        LD (HL),0x64
        INC A
        LD (unpack_progress),A
unpack_progress_event:
        JR unpack_step

disk_position: DW 0
disk_destination: DW 0
sectors_read: DW 0
load_progress: DB 0
load_threshold_cursor: DW load_thresholds
unpack_progress: DB 0
unpack_target: DB 0
chunk_cursor: DW 0
output_address: DW 0
group_count: DW 0
chunks_left: DB chunk_count
chunk_data: MDAT "chunks.bin"
load_thresholds: MDAT "load-thresholds.bin"
trampoline_data: MDAT "trampoline.bin"
code_end:
        ASSERT $ <= 0x9000
        DS 0x9000-$
lookup: MDAT "lookup.bin"
screen_data: MDAT "progress-screen.bin"
        ASSERT $ == 0xAF00
