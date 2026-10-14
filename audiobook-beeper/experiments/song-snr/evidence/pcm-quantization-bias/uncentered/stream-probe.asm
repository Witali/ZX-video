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

