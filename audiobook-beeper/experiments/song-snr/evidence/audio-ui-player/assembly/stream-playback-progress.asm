; Optional Pentagon live progress. The entry comes from PAGE_TAIL with the
; alternate bank active and the prefetched nibble protected in AF'. SECOND
; has consumed all three packet words, so SP is dead until FIRST resets it.
; The ten-byte fixed-bank2 command is AF(validity/paging),DE(source/paging),
; BC(first attribute),BC(second attribute),AF(Scorpion selector, unused here).
; All clones retain the original audio allocation; only Pentagon dispatches
; here. Its RAM and I/O are uncontended. Legacy128/Scorpion live I/O remains
; unchanged to avoid adding address-dependent ULA waits.

PLAY_PROGRESS_TAIL: MACRO
stream_play_tail_\0: ASSERT 1
        LD SP,(stream_play_next_record) ; one shared cursor for both last bits
        POP AF                  ; A=paging; valid F.Z=0, sentinel A=0/F.Z=1
        JP Z,stream_play_exhausted_\0
        POP DE                  ; D=next source high byte,E=duplicate paging
        LD BC,0x7FFD
        LD A,31
        OUT (C),A               ; protected physicalbank7 screen atC000
        POP BC
        LD A,0x24
stream_play_attribute_first_\0: ASSERT 1
        LD (BC),A
        POP BC
stream_play_attribute_second_\0: ASSERT 1
        LD (BC),A
stream_play_after_attributes_\0: ASSERT 1
        POP AF                  ; consume unused high-selector word
        LD (stream_play_next_record),SP
        LD BC,0x7FFD
        LD A,E
stream_play_page_event_\0: ASSERT 1
        OUT (C),A               ; restore audio before any later prefetch
        LD E,0
        ; From previous bit1: page/bank detection32 + EXAF4/directJP10 +
        ; this command path207 + sixNOP24 =277T, unchanged34+243. The
        ; outgoing JP(HL)4 + nextFIRST OUT12 remains the original16T.
        NOP
        NOP
        NOP
        NOP
        NOP
        NOP
        EXX
        SCF
        EX AF,AF'
        IF \0
        OUT (C),D               ; mainD remains16 from SECOND POP DE
        ELSE
        DB 0xED,0x71            ; the existing literal-zero PULSE opcode
        ENDIF
        JP (HL)

        ENDM
        PLAY_PROGRESS_TAIL 0
        PLAY_PROGRESS_TAIL 1

; Only explicit refill/end paths reach this shared slow wrapper. BC is dead
; here; remember the literal handler and save ALT HL before the old exhausted
; routine uses it. Both release handlers still consume one shared cursor.
stream_play_exhausted_0:
        LD BC,stream_play_tail_0
        JP stream_play_exhausted_common
stream_play_exhausted_1:
        LD BC,stream_play_tail_1
stream_play_exhausted_common:
        LD (stream_tail_hl),HL
        LD (stream_reload_end+1),BC
        JP stream_exhausted

; Continuous streams do not use CACHE_START/COUNT for cached ROM reads.
; Their four reserved bytes are cleared by CACHE_DETECT and remain outside
; all packet entries. The loader tracks whole-source sectors, not batch size.
stream_play_fraction: EQU 0x5B74
stream_play_bar: EQU 0x5B76
stream_play_batch_bar: EQU 0x5B77

; Loading-only exact global fraction. Remainder<2392; adding32 cannot wrap
; 16 bits. Repeat subtraction also supports sources shorter than32 sectors.
; AF/BC/DE/HL scratch; no alternate register or audio lookup is modified.
stream_play_advance_global:
        LD HL,(stream_play_fraction)
        LD DE,32
        ADD HL,DE
        LD BC,stream_play_bar
stream_play_global_compare:
        LD DE,audio_sectors
        OR A
        SBC HL,DE
        JR C,stream_play_global_remainder
        LD A,(BC)
        INC A
        LD (BC),A
        JR stream_play_global_compare
stream_play_global_remainder:
        ADD HL,DE
        LD (stream_play_fraction),HL
        RET

stream_play_next_record: DEFW 0
; A zero-column command points here, never prematurely paints column0 or
; writes into bank7 audio atDB00. This byte is an explicitly mutable guard.
stream_play_dummy: DEFB 0
stream_play_records: DEFS record_slots*10
stream_play_records_end:
