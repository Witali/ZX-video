; Loading-only exact sector progress. A short batch can publish several
; cells per sector, so subtract repeatedly instead of assuming total>=32.
; HL/DE/BC/AF scratch. No code here runs during live audio.
cache_progress:
        LD A,(cache_progress_enabled)
        OR A
        RET Z
        LD HL,(cache_fraction)
        LD DE,32
        ADD HL,DE
cache_progress_compare:
        LD DE,(cache_total)
        OR A
        SBC HL,DE
        JR C,cache_progress_remainder
        LD (cache_fraction),HL
        LD A,(cache_bar)
        CP 32
        RET NC
        INC A
        LD (cache_bar),A
cache_progress_event:
        CALL cache_draw_bar
        LD HL,(cache_fraction)
        JR cache_progress_compare
cache_progress_remainder:
        ADD HL,DE
        LD (cache_fraction),HL
        RET

; Shadow screen is always bank7. Restore normal bank0 before enabling IRQs;
; loader explicitly maps the next destination before each physical copy.
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
        LD A,24
        CALL cache_restore
        EI
        RET
