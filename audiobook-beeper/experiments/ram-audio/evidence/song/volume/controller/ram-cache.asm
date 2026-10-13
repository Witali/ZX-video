; Loading-only extended-RAM cache, included in both transient controller and
; fixed bank2. CACHE_STATE occupies16 unused packet-page bytes at5B70; callers
; independently prove <=18 feedback entries (108 bytes) in each half-page.
; All disk operations use a fixed-bank bounce buffer: TR-DOS is never asked
; to preserve an extended7FFD/1FFD mapping. No cache code runs during PDM.
CACHE_STATE: EQU 0x5B70
cache_mode: EQU CACHE_STATE+2       ; 0=128,1=Scorpion,2=Pentagon512,3=Pentagon1024
cache_pages: EQU CACHE_STATE+3      ; distinct extra16-KiB pages,0/8/24/56
cache_start: EQU CACHE_STATE+4      ; linear first disk sector in this window
cache_count: EQU CACHE_STATE+6      ; number of valid cached256-byte sectors
cache_bar: EQU CACHE_STATE+8
cache_progress_enabled: EQU CACHE_STATE+9
cache_fraction: EQU CACHE_STATE+10
cache_total: EQU CACHE_STATE+12
cache_volume: EQU CACHE_STATE+14

; A=physical RAM page,0..63. BC/DE/AF clobbered; HL preserved.
; Shadow screen and48K ROM stay selected. Bit5 is never used on a512K
; device: only the reversible EFF7 alias test may authorize the1024 mapping.
cache_map:
        LD E,A
        LD A,(cache_mode)
        CP 1
        JR NZ,cache_map_pentagon
        LD A,E
        AND 8
        ADD A,A
        LD BC,0x1FFD
        OUT (C),A
        LD A,E
        AND 7
        OR 24
        JR cache_map_output
cache_map_pentagon:
        LD A,E
        AND 24
        RLCA
        RLCA
        RLCA
        LD D,A
        LD A,E
        AND 32
        OR D
        LD D,A
        LD A,E
        AND 7
        OR 24
        OR D
cache_map_output:
        LD BC,0x7FFD
        OUT (C),A
        RET

; A=normal paging byte. Clear Scorpion's high RAM bit before returning to
; ordinary banks; preserve AF'/IY and use no ROM while high RAM is paged.
cache_restore:
        LD E,A
        LD A,(cache_mode)
        CP 1
        JR NZ,cache_restore_low
        XOR A
        LD BC,0x1FFD
        OUT (C),A
cache_restore_low:
        LD A,E
        LD BC,0x7FFD
        OUT (C),A
        RET

; Test two physical page selectors without destroying either original byte.
; Private ref/candidate fields are outside paged RAM. Z=alias,NZ=distinct.
; Even when both selectors alias, both saved originals are identical because
; they are captured before either test write. Interrupts must be disabled.
cache_alias:
        LD A,(cache_ref)
        CALL cache_map
        LD A,(0xC000)
        LD (cache_ref_byte),A
        LD A,(cache_candidate)
        CALL cache_map
        LD A,(0xC000)
        LD (cache_candidate_byte),A
        LD A,(cache_ref)
        CALL cache_map
        LD A,0x55
        LD (0xC000),A
        LD A,(cache_candidate)
        CALL cache_map
        LD A,0xAA
        LD (0xC000),A
        LD A,(cache_ref)
        CALL cache_map
        LD A,(0xC000)
        CP 0x55
        LD A,0
        JR NZ,cache_alias_saved
        INC A
cache_alias_saved:
        LD (cache_distinct),A
        LD A,(cache_candidate)
        CALL cache_map
        LD A,(cache_candidate_byte)
        LD (0xC000),A
        LD A,(cache_ref)
        CALL cache_map
        LD A,(cache_ref_byte)
        LD (0xC000),A
        LD A,(cache_distinct)
        OR A
        RET

; Cold initialization: probe Scorpion1FFD first, then safe Pentagon bits6/7.
; EFF7 bit2 temporarily removes Pentagon1024 high RAM bits without asserting
; 7FFD's lock bit. A512K machine ignores it and remains distinct. Verify every
; candidate against all earlier pages, so mirrored expansion cannot inflate
; the reported capacity. Every probe restores original RAM and normal paging.
cache_detect:
        DI
        XOR A
        LD HL,CACHE_STATE
        LD DE,CACHE_STATE+1
        LD BC,15
        LD (HL),A
        LDIR
        LD (cache_ref),A
        LD A,8
        LD (cache_candidate),A
        LD A,1
        LD (cache_mode),A
        CALL cache_alias
        JR NZ,cache_detect_scorpion
        LD A,24
        CALL cache_restore
        LD A,2
        LD (cache_mode),A
        CALL cache_alias
        JR Z,cache_detect_none
        LD BC,0xEFF7
        LD A,4
        OUT (C),A
        CALL cache_alias
        PUSH AF
        LD BC,0xEFF7
        XOR A
        OUT (C),A
        POP AF
        LD A,32
        JR NZ,cache_detect_limit
        LD A,3
        LD (cache_mode),A
        LD A,64
        JR cache_detect_limit
cache_detect_scorpion:
        LD A,16
cache_detect_limit:
        LD (cache_limit),A
        LD A,8
        LD (cache_candidate),A
cache_detect_next:
        XOR A
        LD (cache_ref),A
cache_detect_reference:
        CALL cache_alias
        JR Z,cache_detect_done
        LD A,(cache_ref)
        INC A
        LD (cache_ref),A
        LD HL,cache_candidate
        CP (HL)
        JR C,cache_detect_reference
        LD A,(cache_pages)
        INC A
        LD (cache_pages),A
        LD A,(cache_candidate)
        INC A
        LD (cache_candidate),A
        LD HL,cache_limit
        CP (HL)
        JR C,cache_detect_next
        JR cache_detect_done
cache_detect_none:
        XOR A
        LD (cache_mode),A
cache_detect_done:
        LD A,24
        CALL cache_restore
        LD HL,0x4352            ; 'RC',little endian
        LD (CACHE_STATE),HL
        RET

; DE=TR-DOS track/sector. Return HL=linear sector; AF/DE clobbered.
cache_linear:
        LD H,0
        LD L,D
        ADD HL,HL
        ADD HL,HL
        ADD HL,HL
        ADD HL,HL
        LD D,0
        ADD HL,DE
        RET

; HL=zero-based cached sector, <3584. A=RAM page,HL=page-local source.
cache_location:
        LD A,H
        ADD A,A
        ADD A,A
        LD D,A
        LD A,L
        RLCA
        RLCA
        AND 3
        OR D
        ADD A,8
        LD E,A
        LD A,L
        AND 63
        OR 0xC0
        LD H,A
        LD L,0
        LD A,E
        RET

; A=normal destination paging,HL=destination,DE=track/sector.
; Read one sector, using the cache only for a proved complete hit. Cached
; transfers first copy to fixed bounce RAM, then restore destination paging.
; Preserve the persistent state even when the destination is its table page.
cache_read_sector:
        DI
        LD (cache_destination_page),A
        LD (cache_destination),HL
        LD (cache_disk_address),DE
        LD HL,CACHE_STATE
        LD DE,cache_saved_state
        LD BC,16
        LDIR
        LD DE,(cache_disk_address)
        CALL cache_linear
        LD DE,(cache_start)
        OR A
        SBC HL,DE
        JR C,cache_read_rom
        PUSH HL
        LD DE,(cache_count)
        OR A
        SBC HL,DE
        POP HL
        JR NC,cache_read_rom
        CALL cache_location
        CALL cache_map
        LD DE,cache_bounce
        LD BC,256
        LDIR
        LD A,(cache_destination_page)
        CALL cache_restore
        LD HL,cache_bounce
        LD DE,(cache_destination)
        LD BC,256
        LDIR
cache_hit_event:
        JR cache_read_restored
cache_read_rom:
        LD A,(cache_destination_page)
        CALL cache_restore
        LD HL,(cache_destination)
        LD DE,(cache_disk_address)
        LD BC,0x0105
        EI
cache_physical_read:
        CALL 0x3D13
cache_read_restored:
        LD HL,cache_saved_state
        LD DE,CACHE_STATE
        LD BC,16
        LDIR
        EI
        RET

; HL=linear first future sector,DE=one-past-last sector on this volume.
; Refill only after the previous window has been consumed. Read the complete
; available window before audio, stopping at EOF rather than reading padding.
; Each disk read targets fixed bounce RAM before its physical extra-page copy.
cache_prefetch:
        LD (cache_future),HL
        PUSH HL
        LD HL,(cache_start)
        LD BC,(cache_count)
        ADD HL,BC
        POP BC
        OR A
        SBC HL,BC
        JR Z,cache_prefetch_empty
        RET NC                  ; some future sectors are still cached
cache_prefetch_empty:
        LD HL,(cache_future)
        LD (cache_start),HL
        EX DE,HL
        OR A
        SBC HL,DE
        RET Z
        RET C
        LD A,(cache_pages)
        OR A
        RET Z
        LD B,A
        LD C,0
        SRL B
        RR C
        SRL B
        RR C                    ; BC=pages*64
        OR A
        SBC HL,BC
        JR NC,cache_prefetch_capacity
        ADD HL,BC
        LD B,H
        LD C,L
cache_prefetch_capacity:
        LD (cache_fill_limit),BC
        LD HL,0
        LD (cache_count),HL
        LD (cache_fill_index),HL
cache_fill_next:
        LD HL,(cache_start)
        LD DE,(cache_fill_index)
        ADD HL,DE
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
        PUSH DE
        LD A,24
        CALL cache_restore
        POP DE
        LD HL,cache_bounce
        LD BC,0x0105
        EI
cache_prefetch_physical_read:
        CALL 0x3D13
        DI
        LD HL,(cache_fill_index)
        CALL cache_location
        PUSH HL
        CALL cache_map
        POP DE
        LD HL,cache_bounce
        LD BC,256
        LDIR
        LD A,24
        CALL cache_restore
        LD HL,(cache_fill_index)
        INC HL
        LD (cache_fill_index),HL
        LD (cache_count),HL
        CALL cache_progress
cache_prefetch_sector_done:
        LD HL,(cache_fill_index)
        LD BC,(cache_fill_limit)
        OR A
        SBC HL,BC
        JR C,cache_fill_next
        EI
        RET

; Progress uses remainder arithmetic: add32 per completed sector and publish
; one cell when remainder>=total. No approximation or early100% completion.
; Caller supplies the actual logical loading+prefetch total before its reads.
cache_progress:
        LD A,(cache_progress_enabled)
        OR A
        RET Z
        LD HL,(cache_fraction)
        LD DE,32
        ADD HL,DE
        LD DE,(cache_total)
        OR A
        SBC HL,DE
        JR NC,cache_progress_publish
        ADD HL,DE
        LD (cache_fraction),HL
        RET
cache_progress_publish:
        LD (cache_fraction),HL
        LD A,(cache_bar)
        CP 32
        RET NC
        INC A
        LD (cache_bar),A
cache_progress_event:
        JP cache_draw_bar

; Loading-only UI: the shadow screen is bank7. Restore the caller's normal
; destination page afterward. HL/DE/BC/AF are scratch; AF'/IX/IY untouched.
cache_draw_bar:
        DI
        LD A,31
        CALL cache_restore
        LD HL,0xDAC0
        LD A,(cache_bar)
        LD E,A
        LD B,32
cache_draw_cell:
        LD A,E
        OR A
        LD A,4
        JR Z,cache_draw_empty
        DEC E
        LD A,0x24
cache_draw_empty:
        LD (HL),A
        INC HL
        DJNZ cache_draw_cell
        LD A,(cache_destination_page)
        CALL cache_restore
        EI
        RET

; HL=current record start,DE=record end. Include any newly needed prefetch
; in the exact progress denominator; an existing unconsumed window is free.
cache_begin_progress:
        LD (cache_record_start),HL
        LD (cache_future),DE
        EX DE,HL
        OR A
        SBC HL,DE
        LD (cache_total),HL
        LD HL,(cache_start)
        LD DE,(cache_count)
        ADD HL,DE
        LD DE,(cache_future)
        OR A
        SBC HL,DE
        JR C,cache_begin_fill
        JR NZ,cache_begin_ready
cache_begin_fill:
        LD HL,(cache_disk_end)
        OR A
        SBC HL,DE
        LD A,(cache_pages)
        LD B,A
        LD C,0
        SRL B
        RR C
        SRL B
        RR C
        OR A
        SBC HL,BC
        JR NC,cache_begin_capacity
        ADD HL,BC
        LD B,H
        LD C,L
cache_begin_capacity:
        LD HL,(cache_total)
        ADD HL,BC
        LD (cache_total),HL
cache_begin_ready:
        XOR A
        LD (cache_bar),A
        LD HL,0
        LD (cache_fraction),HL
        INC A
        LD (cache_progress_enabled),A
        JP cache_draw_bar

cache_ref: DEFB 0
cache_candidate: DEFB 8
cache_limit: DEFB 0
cache_ref_byte: DEFB 0
cache_candidate_byte: DEFB 0
cache_distinct: DEFB 0
cache_destination_page: DEFB 24
cache_destination: DEFW 0
cache_disk_address: DEFW 0
cache_future: DEFW 0
cache_fill_limit: DEFW 0
cache_fill_index: DEFW 0
cache_record_start: DEFW 0
cache_disk_end: DEFW 0
cache_saved_state: DEFS 16
cache_bounce: DEFS 256
cache_code_end:
