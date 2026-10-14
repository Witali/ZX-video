; Loading/reload work stays in fixed bank2. TR-DOS always reads a fixed bounce
; buffer with normal RAM selected, then a sector is copied into its final
; physical page. There are no copies/ROM calls between live banks when RAM fits.
        INCLUDE "stream-probe.asm"

stream_cold_start:
        DI
        LD SP,0x6000
        LD IY,0x5C3A
        IM 1
        XOR A
        OUT (0xFE),A
        LD BC,0x1FFD
        OUT (C),A
        LD BC,0x7FFD
        LD A,31
        OUT (C),A
        LD DE,cover_disk
        LD HL,0xC000
        LD B,27
        CALL stream_read_n
cover_visible:
        LD DE,lower_disk
        LD HL,0x4000
        LD B,28
        CALL stream_read_n
        LD DE,upper_disk
        LD HL,0x6000
        LD B,32
        CALL stream_read_n
        CALL cache_detect       ; only after lookup sectors, so no state overlap
        LD A,(cache_pages)
        ADD A,6
        LD (stream_bank_limit),A
        LD A,(cache_mode)
        CP 1
        JR NZ,stream_patch_pentagon
        XOR A
        LD (stream_high_switch),A
        LD (stream_high_switch+1),A
        LD (stream_high_switch+2),A
stream_patch_pentagon:
        CALL stream_patch_first
        LD HL,audio_sector
        LD (stream_disk_sector),HL
        LD HL,audio_sectors
        LD (stream_remaining),HL
        CALL stream_load_chunk
        LD BC,0xFFFD
        LD A,8
stream_mute_ay:
        OUT (C),A
        PUSH AF
        LD BC,0xBFFD
        XOR A
        OUT (C),A
        LD BC,0xFFFD
        POP AF
        INC A
        CP 11
        JR C,stream_mute_ay
stream_loaded:
        EI
        HALT
        DI
        JP ready

; Preserve all live main/alternate registers and the lookup SP across a slow
; insufficient-RAM refill. Incoming DE is replaced by the new first descriptor
; on return, while prefetched predictor/code/row and PDM feedback remain exact.
stream_exhausted:
        LD HL,(stream_remaining)
        LD A,H
        OR L
        JP Z,stream_finish
stream_reload_begin:
        LD HL,(stream_tail_hl)
        LD (stream_lookup_sp),SP
        LD SP,0x6000
        PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL
        PUSH IX
        PUSH IY
        EXX
        PUSH BC
        PUSH DE
        PUSH HL
        EX AF,AF'
        PUSH AF
        EX AF,AF'
        EXX
        LD IY,0x5C3A
        XOR A
        OUT (0xFE),A
        CALL stream_load_chunk
        LD HL,stream_records
        LD (stream_next_record),HL
        EXX
        EX AF,AF'
        POP AF
        EX AF,AF'
        POP HL
        POP DE
        POP BC
        EXX
        POP IY
        POP IX
        POP HL
        POP DE
        POP BC
        POP AF
        LD SP,(stream_lookup_sp)
stream_reload_end:
        JP stream_bank_tail

; Allocate a complete physical-page batch in source order. Bank7 preserves
; its6912-byte shadow screen; bank2/5 remain code/table/workspace. Others offer
;64 sectors. Each source slice ends atFFFF so the existing page-tail detector
; needs no per-sample length comparison. Clear descriptors before refilling.
stream_load_chunk:
        DI
        LD A,24
        CALL cache_restore
        LD A,(cache_pages)
        LD B,A
        LD C,0
        SRL B
        RR C
        SRL B
        RR C
        LD HL,357
        ADD HL,BC
        LD DE,(stream_remaining)
        OR A
        SBC HL,DE
        JR C,stream_chunk_capacity
        LD B,D
        LD C,E
        JR stream_chunk_total
stream_chunk_capacity:
        ADD HL,DE
        LD B,H
        LD C,L
stream_chunk_total:
        LD (cache_total),BC
        LD HL,0
        LD (cache_fraction),HL
        XOR A
        LD (cache_bar),A
        LD (stream_bank_index),A
        INC A
        LD (cache_progress_enabled),A
        CALL cache_draw_bar
        LD HL,stream_records
        LD (stream_record_write),HL
stream_allocate:
        LD A,(stream_bank_index)
        CP 6
        JR NC,stream_extended_bank
        LD E,A
        LD D,0
        LD HL,stream_base_banks
        ADD HL,DE
        LD A,(HL)
        JR stream_bank_selected
stream_extended_bank:
        ADD A,2
stream_bank_selected:
        LD (stream_physical),A
        LD DE,64
        CP 7
        JR NZ,stream_capacity_known
        LD E,37
stream_capacity_known:
        LD HL,(stream_remaining)
        OR A
        SBC HL,DE
        JR NC,stream_full_page
        ADD HL,DE
        LD E,L
        LD HL,0
stream_full_page:
        LD (stream_remaining),HL
        LD A,E
        LD (stream_sector_count),A
        NEG                     ; high address=256-sector_count
        LD (stream_address_high),A
        LD H,A
        LD L,0
        LD (stream_destination),HL
        ; Build paging metadata separately from the live tail. Scorpion uses
        ; only low7FFD bits and1FFD bit4; Pentagon high bits are authorized by
        ; the detector. No512K record can assert the7FFD lock bit.
        LD HL,(stream_record_write)
        LD A,(stream_physical)
        LD E,A
        AND 7
        OR 24
        LD D,A
        LD A,(cache_mode)
        CP 1
        JR Z,stream_record_scorpion
        LD A,E
        AND 24
        RLCA
        RLCA
        RLCA
        OR D
        LD D,A
        LD A,E
        AND 32
        OR D
        LD D,A
stream_record_scorpion:
        LD (HL),D
        INC HL
        LD A,(stream_address_high)
        LD (HL),A
        INC HL
        LD A,E
        AND 8
        ADD A,A
        LD (HL),A
        INC HL
        LD (stream_record_write),HL
stream_sector_next:
        LD A,24
        CALL cache_restore
        LD HL,(stream_disk_sector)
        LD A,L
        AND 15
        LD E,A
        SRL H
        RR L
        SRL H
        RR L
        SRL H
        RR L
        SRL H
        RR L
        LD D,L
        LD HL,stream_bounce
        LD BC,0x0105
        EI
stream_disk_call:
        CALL 0x3D13
        DI
        LD A,(stream_physical)
        CALL cache_map
        LD HL,stream_bounce
        LD DE,(stream_destination)
        LD BC,256
        LDIR
        LD (stream_destination),DE
        LD HL,(stream_disk_sector)
        INC HL
        LD (stream_disk_sector),HL
        CALL cache_progress
        LD HL,stream_sector_count
        DEC (HL)
        JR NZ,stream_sector_next
        LD HL,stream_bank_index
        INC (HL)
        LD A,(HL)
        LD HL,stream_bank_limit
        CP (HL)
        JR NC,stream_chunk_loaded
        LD HL,(stream_remaining)
        LD A,H
        OR L
        JP NZ,stream_allocate
stream_chunk_loaded:
        LD HL,(stream_record_write)
        LD (HL),0
        LD A,(stream_records+1)
        LD H,A
        LD L,0
        LD (stream_first_address),HL
        LD HL,stream_records+3
        LD (stream_next_record),HL
        LD A,24
        CALL cache_restore
        DI
        RET

; Ordinary bank2/5/shadow loads at cold boot; ROM owns register scratches.
stream_read_n:
        LD (stream_rom_position),DE
stream_read_next:
        PUSH BC
        PUSH HL
        LD DE,(stream_rom_position)
        LD BC,0x0105
        EI
        CALL 0x3D13
        DI
        POP HL
        POP BC
        INC H
        LD DE,(stream_rom_position)
        INC E
        BIT 4,E
        JR Z,stream_rom_sector_ok
        LD E,0
        INC D
stream_rom_sector_ok:
        LD (stream_rom_position),DE
        DJNZ stream_read_next
        RET

; Pentagon-only register-preserving pacing: JP10 +4 NOPs16 +old JP(IY)8,
; ordinary delta26 T.128/Scorpion retain their original JP(IY), delta0.
hardware_delay:
        NOP
        NOP
        NOP
        NOP
        JP (IY)
stream_patch_first:
        LD A,(cache_mode)
        CP 2
        RET C
        LD DE,hardware_delay
        LD HL,first_base+first_size-3
        LD B,first_patterns
stream_patch_loop:
        LD (HL),0xC3
        INC HL
        LD (HL),E
        INC HL
        LD (HL),D
        LD A,L
        ADD A,first_size-2
        LD L,A
        JR NC,stream_patch_next
        INC H
stream_patch_next:
        DJNZ stream_patch_loop
        RET

stream_finish:
        DI
        LD SP,0x6000
        LD IY,0x5C3A
        XOR A
        OUT (0xFE),A
        LD A,31
        CALL cache_restore
        LD HL,stream_end_message
        LD DE,0xD080           ; footer bitmap at y160,keep the title visible
stream_print:
        LD A,(HL)
        OR A
        JR Z,stream_finished
        INC HL
        PUSH HL
        LD L,A
        LD H,0
        ADD HL,HL
        ADD HL,HL
        ADD HL,HL
        LD BC,0x3C00
        ADD HL,BC
        PUSH DE
        LD B,8
stream_glyph:
        LD A,(HL)
        LD (DE),A
        INC HL
        INC D
        DJNZ stream_glyph
        POP DE
        INC E
        POP HL
        JR stream_print
stream_finished:
        EI
        HALT
        JR stream_finished

        INCLUDE "stream-progress.asm"
cache_ref: DEFB 0
cache_candidate: DEFB 8
cache_limit: DEFB 0
cache_ref_byte: DEFB 0
cache_candidate_byte: DEFB 0
cache_distinct: DEFB 0
cache_destination_page: DEFB 24
stream_bank_limit: DEFB 6
stream_bank_index: DEFB 0
stream_physical: DEFB 0
stream_sector_count: DEFB 0
stream_address_high: DEFB 0
stream_paging: DEFB 24
stream_rom_position: DEFW 0
stream_disk_sector: DEFW 0
stream_remaining: DEFW 0
stream_record_write: DEFW 0
stream_destination: DEFW 0
stream_first_address: DEFW 0
stream_next_record: DEFW 0
stream_tail_hl: DEFW 0
stream_lookup_sp: DEFW 0
stream_base_banks: DEFB 0,4,6,1,3,7
stream_end_message: DEFM "END OF AUDIO",0
stream_records: DEFS record_slots*3+1
stream_bounce: DEFS 256
stream_worker_end:
