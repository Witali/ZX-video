; LPS1 -> PCM8 -> ordinary low-nibble-first IMA, entirely on the Z80.
; This program runs before sound starts. No PDM deadline applies here.
; Fixed bank2: code/state below 9C00, final compressed tail at A000..B7FF.
; Bank5: visible screen/workspace below6000, temporary product tables6000..77FF.
; LPC input initially occupies banks3/7. Those bytes are consumed before reuse.
        INCLUDE "lpc-config.inc"
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
        LD A,3
        CALL page
        LD DE,lpc_disk
        LD (disk_position),DE
        LD HL,0xC000
        LD B,lpc_first_sectors
        CALL read_n
        IF lpc_second_sectors > 0
        LD A,7
        CALL page
        LD HL,0xC000
        LD B,lpc_second_sectors
        CALL read_n
        ENDIF
        DI
load_complete:
        LD A,32
        LD (load_progress),A
        LD HL,0x5940
        LD B,32
load_full:
        LD (HL),0x64
        INC HL
        DJNZ load_full
        LD HL,0xC020
        LD (input_cursor),HL
        LD HL,lpc_bytes-32
        LD (input_left),HL
        LD A,3
        LD (input_bank),A
        LD HL,section_data
        LD (section_cursor),HL
        CALL select_output
        LD HL,27853           ; de-emphasis coefficient round(.85*32768)
        EX DE,HL
        LD A,0x76
        CALL build_table
        LD HL,frame_count
        LD (frames_left),HL
frame_loop:
        CALL read_frame
        LD IX,frame_buffer
        LD B,10
        LD C,0x60
coefficient_loop:
        LD E,(IX+0)
        LD D,(IX+1)
        LD A,C
        PUSH BC
        CALL build_table
        POP BC
        INC IX
        INC IX
        INC C
        INC C
        DJNZ coefficient_loop
        LD DE,(frame_buffer+26)
        LD A,0x74
        CALL build_table       ; noise amplitude * signed8 /128
        LD HL,(frames_left)
        DEC HL
        LD (frames_left),HL
        LD A,H
        OR L
        LD A,160
        JR NZ,frame_length_ready
        LD A,last_frame_samples
frame_length_ready:
        LD (samples_left),A
sample_loop:
        CALL synth_sample
pcm_ready:
        CALL emit_pcm
        LD A,(samples_left)
        DEC A
        LD (samples_left),A
        JP NZ,sample_loop
        LD HL,(frames_left)
        LD A,H
        OR L
        JP NZ,frame_loop
        LD B,128              ; independent silent guard settles IMA to0/0
guard_loop:
        PUSH BC
        LD A,128
guard_pcm_ready:
        CALL emit_pcm
        POP BC
        DJNZ guard_loop
unpack_complete:
        LD HL,trampoline_data
        LD DE,0x6000
        LD BC,trampoline_size
        LDIR
        JP 0x6000             ; replace this program with the resident player

; BC and IY may be destroyed by TR-DOS; caller loop/cursor are preserved.
read_n: LD (disk_destination),HL
read_sector:
        PUSH BC
        LD HL,(disk_destination)
        LD DE,(disk_position)
        LD BC,0x0105
        EI
disk_call:
        CALL 0x3D13
        DI
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
        LD A,(sectors_read)
        INC A
        LD (sectors_read),A
        LD HL,load_thresholds
        LD E,A
        LD A,(load_progress)
        CP 32
        JR Z,load_no_update
        LD C,A
        LD B,0
        ADD HL,BC
        LD A,E
        CP (HL)
        JR C,load_no_update
        LD HL,0x5940
        ADD HL,BC
        LD (HL),0x64
        LD A,C
        INC A
        LD (load_progress),A
load_progress_event:
        NOP
        LD A,(sectors_read)
        LD E,A
        LD HL,load_thresholds
        LD A,(load_progress)
        CP 32
        JR Z,load_no_update
        LD C,A
        LD B,0
        ADD HL,BC
        LD A,E
        CP (HL)
        JR C,load_no_update
        LD HL,0x5940
        ADD HL,BC
        LD (HL),0x64
        LD A,C
        INC A
        LD (load_progress),A
        JR load_progress_event
load_no_update:
        POP BC
        DJNZ read_sector
        RET

page:   LD BC,0x7FFD
        OR 16                 ; ROM1, visible bank5, paging stays enabled
        OUT (C),A
        RET

read_frame:
        LD A,(input_fixed)
        OR A
        JR NZ,input_selected
        LD A,(input_bank)
        CALL page
input_selected:
        LD HL,(input_cursor)
        LD DE,frame_buffer
        LD B,28
read_frame_byte:
        LD A,(HL)
        LD (DE),A
        INC DE
        INC HL
        LD A,H
        OR L
        JR NZ,read_frame_continue
        PUSH BC
        LD A,7
        LD (input_bank),A
        CALL page
        POP BC
        LD HL,0xC000
read_frame_continue:
        DJNZ read_frame_byte
        LD (input_cursor),HL
        LD HL,(input_left)
        LD DE,28
        OR A
        SBC HL,DE
        LD (input_left),HL
        LD A,(output_bank)
        JP page

select_output:
        LD HL,(section_cursor)
        LD A,(HL)
        LD (output_bank),A
        INC HL
        LD E,(HL)
        INC HL
        LD D,(HL)
        INC HL
        LD (section_cursor),HL
        LD (output_cursor),DE
        CP 7
        JR NZ,output_selected
        CALL page
        LD HL,(input_cursor)
        LD DE,0xA000
        LD BC,(input_left)
        LD A,B
        OR C
        JR Z,tail_copied
        LDIR                  ; <=6144 bytes, before bank7 overwrites input
tail_copied:
        LD HL,0xA000
        LD (input_cursor),HL
        LD A,1
        LD (input_fixed),A
output_selected:
        LD A,(output_bank)
        JP page

; Build two 256-byte pages t[x] = floor(k * signed8(x) /128).
; DE=k, A=low-byte page. Incremental quotient/remainder is exact for negatives.
; Each table consumes512 temporary bytes, reused for every frame.
build_table:
        LD (table_page),A
        LD A,E
        AND 127
        LD (table_remainder_step),A
        PUSH DE
        EX DE,HL
        CALL sar7
        LD (table_step),HL
        POP DE
        LD HL,0
        OR A
        SBC HL,DE             ; quotient at signed input-128 equals-k
        EX DE,HL
        LD A,(table_page)
        LD H,A
        LD L,128
        LD A,(table_remainder_step)
        LD C,A
        LD B,0                ; 256 entries, signed index128..255,0..127
        XOR A
table_loop:
        LD (HL),E
        INC H
        LD (HL),D
        DEC H
        PUSH HL
        LD HL,(table_step)
        ADD HL,DE
        EX DE,HL
        POP HL
        ADD A,C
        JP P,table_no_carry
        AND 127
        INC DE
table_no_carry:
        INC L
        DJNZ table_loop
        RET

; HL signed input, A=table low page -> HL approximate Q15 product.
; Preserves BC; destroys DE/AF. Error from split-byte flooring is <2 units.
mul_table:
        PUSH BC
        LD B,A
        LD C,L
        LD L,H
        LD H,B
        LD E,(HL)
        INC H
        LD D,(HL)
        PUSH DE
        LD A,C
        SRL A
        LD L,A
        LD H,B
        LD E,(HL)
        INC H
        LD D,(HL)
        EX DE,HL
        CALL sar7
        POP DE
        ADD HL,DE
        POP BC
        RET
sar7:   SLA L
        RL H
        LD L,H
        SBC A,A
        LD H,A
        RET
clip_hl:
        LD A,H
        BIT 7,A
        JR NZ,clip_negative
        CP 0x40
        RET C
        LD HL,0x3FFF
        RET
clip_negative:
        CP 0xC0
        RET NC
        LD HL,0xC000
        RET

synth_sample:
        LD HL,(noise_seed)
        SRL H
        RR L
        JR NC,noise_shifted
        LD A,H
        XOR 0xB4
        LD H,A
noise_shifted:
        LD (noise_seed),HL
        LD A,H
        XOR 128
        LD L,A
        LD H,0x74
        LD E,(HL)
        INC H
        LD D,(HL)
        LD (forward),DE
        LD HL,(pitch_phase)
        LD DE,256
        OR A
        SBC HL,DE
        JR NC,pitch_ready
        LD DE,(frame_buffer+20)
        ADD HL,DE
        XOR A
        LD (chirp_index),A
pitch_ready:
        LD (pitch_phase),HL
        LD A,(chirp_index)
        CP 15
        JR NC,excitation_ready
        LD L,A
        LD H,0
        LD DE,chirp_signs
        ADD HL,DE
        INC A
        LD (chirp_index),A
        LD A,(HL)
        OR A
        LD HL,(frame_buffer+22)
        JR Z,chirp_ready
        LD HL,(frame_buffer+24)
chirp_ready:
        LD DE,(forward)
        ADD HL,DE
        CALL clip_hl
        LD (forward),HL
excitation_ready:
        LD IX,history+18
        LD C,0x72
        LD B,10
lattice_loop:
        LD L,(IX+0)
        LD H,(IX+1)
        LD A,C
        CALL mul_table
        EX DE,HL
        LD HL,(forward)
        OR A
        SBC HL,DE
        CALL clip_hl
        LD (forward),HL
        LD A,C
        CALL mul_table
        LD E,(IX+0)
        LD D,(IX+1)
        ADD HL,DE
        CALL clip_hl
        LD (IX+2),L
        LD (IX+3),H
        DEC IX
        DEC IX
        DEC C
        DEC C
        DJNZ lattice_loop
        LD HL,(forward)
        LD (history),HL
        LD HL,(deemphasis)
        LD A,0x76
        CALL mul_table
        LD DE,(forward)
        ADD HL,DE
        CALL clip_hl
        LD (deemphasis),HL
        LD DE,(previous_output)
        LD (previous_output),HL
        OR A
        SBC HL,DE
        CALL clip_hl
        LD DE,(dc_state)
        ADD HL,DE
        CALL clip_hl
        LD E,D               ; signed previous DC state >>8
        LD A,D
        ADD A,A
        SBC A,A
        LD D,A
        OR A
        SBC HL,DE
        CALL clip_hl
        LD (dc_state),HL
        LD B,5
pcm_shift:
        SRA H
        RR L
        DJNZ pcm_shift
        LD A,H
        OR A
        JR Z,pcm_positive
        INC A
        JR NZ,pcm_low
        LD A,L
        CP 129
        JR C,pcm_low
        ADD A,128
        RET
pcm_positive:
        LD A,L
        CP 128
        JR NC,pcm_high
        ADD A,128
        RET
pcm_low: LD A,1
        RET
pcm_high: LD A,255
        RET

; A=PCM8. IMA state persists across LPC frames and RAM bank boundaries.
emit_pcm:
        CALL encode_ima
        LD C,A
        LD A,(half_byte)
        XOR 1
        LD (half_byte),A
        JR Z,emit_packed
        LD A,C
        LD (pending_nibble),A
        RET
emit_packed:
        LD A,C
        RLCA
        RLCA
        RLCA
        RLCA
        LD HL,pending_nibble
        OR (HL)
        LD HL,(output_cursor)
ima_byte_ready:
        LD (HL),A
        INC HL
        LD (output_cursor),HL
        PUSH HL
        LD HL,(produced)
        INC HL
        LD (produced),HL
        LD A,H
        OR L
        JR NZ,produced_ready
        LD A,(produced+2)
        INC A
        LD (produced+2),A
produced_ready:
        CALL update_unpack_progress
        POP HL
        LD A,H
        OR L
        RET NZ
        LD A,(unpack_progress)
        CP 32
        RET Z                 ; last bank ended; do not read another section
        JP select_output

update_unpack_progress:
        LD HL,(unpack_threshold_cursor)
        LD DE,(produced)
        LD A,E
        CP (HL)
        RET NZ
        INC HL
        LD A,D
        CP (HL)
        RET NZ
        INC HL
        LD A,(produced+2)
        CP (HL)
        RET NZ
        INC HL
        LD (unpack_threshold_cursor),HL
        LD A,(unpack_progress)
        LD L,A
        LD H,0x5A
        LD (HL),0x64
        INC A
        LD (unpack_progress),A
unpack_progress_event:
        RET

QUANTIZE: MACRO
        OR A
        SBC HL,DE
        JR C,quant_skip_\0
        PUSH HL
        LD H,B
        LD L,C
        ADD HL,DE
        LD B,H
        LD C,L
        POP HL
        LD A,(ima_code)
        OR \0
        LD (ima_code),A
        JR quant_done_\0
quant_skip_\0: ASSERT 1
        ADD HL,DE
quant_done_\0: ASSERT 1
        ENDM
encode_ima:
        LD H,A
        LD L,0
        LD DE,(ima_predictor)
        OR A
        SBC HL,DE
        LD A,0
        JR NC,ima_magnitude
        EX DE,HL
        LD HL,0
        OR A
        SBC HL,DE
        LD A,8
ima_magnitude:
        LD (ima_code),A
        PUSH HL
        LD A,(ima_index)
        ADD A,A
        LD L,A
        LD H,steps >> 8
        LD E,(HL)
        INC L
        LD D,(HL)
        LD B,D
        LD C,E
        SRL B
        RR C
        SRL B
        RR C
        SRL B
        RR C
        POP HL
        QUANTIZE 4
        SRL D
        RR E
        QUANTIZE 2
        SRL D
        RR E
        QUANTIZE 1
        LD HL,(ima_predictor)
        LD A,(ima_code)
        BIT 3,A
        JR Z,ima_add
        OR A
        SBC HL,BC
        JR ima_updated
ima_add:
        ADD HL,BC
ima_updated:
        LD (ima_predictor),HL
        LD A,(ima_code)
        AND 7
        CP 4
        LD A,(ima_index)
        JR NC,ima_index_up
        OR A
        JR Z,ima_index_ready
        DEC A
        JR ima_index_ready
ima_index_up:
        LD C,A
        LD A,(ima_code)
        AND 7
        SUB 3
        ADD A,A
        ADD A,C
        CP 89
        JR C,ima_index_ready
        LD A,88
ima_index_ready:
        LD (ima_index),A
        LD A,(ima_code)
        RET

disk_position: DW 0
disk_destination: DW 0
sectors_read: DB 0
load_progress: DB 0
unpack_progress: DB 0
input_cursor: DW 0
input_left: DW 0
input_bank: DB 0
input_fixed: DB 0
output_bank: DB 0
output_cursor: DW 0
section_cursor: DW 0
frames_left: DW 0
samples_left: DB 0
table_page: DB 0
table_remainder_step: DB 0
table_step: DW 0
noise_seed: DW 0xACE1
pitch_phase: DW 0
chirp_index: DB 15
forward: DW 0
deemphasis: DW 0
dc_state: DW 0
previous_output: DW 0
history: DS 22
frame_buffer: DS 28
ima_predictor: DW 32768
ima_index: DB 0
ima_code: DB 0
pending_nibble: DB 0
half_byte: DB 0
produced: DS 3
unpack_threshold_cursor: DW unpack_thresholds
chirp_signs: DB 0,0,0,0,1,1,1,0,1,1,0,0,1,0,1
section_data: MDAT "sections.bin"
load_thresholds: MDAT "load-thresholds.bin"
unpack_thresholds: MDAT "unpack-thresholds.bin"
trampoline_data: MDAT "trampoline.bin"
        DS (256-($ & 255)) & 255
steps:  MDAT "ima-steps.bin"
code_end:
        ASSERT $ <= 0x9C00
        DS 0x9C00-$
screen_data: MDAT "progress-screen.bin"
        ASSERT $ <= 0xB800
