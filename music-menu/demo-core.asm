; Cold boot keeps the first SCR visible throughout all startup reads. The
; stock ROM prints the menu into RAM5 while RAM7 is the displayed splash.
; A temporary fixed-RAM copy lets RAM7 subsequently retain the complete menu.
start:  DI
        LD SP,0xBD00
        LD IY,0x5C3A
        LD A,6
        OUT (0xFE),A
        CALL mute
        LD A,23
        CALL page_bank
        LD HL,0x4000
        LD DE,0xC000
        LD BC,6912
        LDIR
        LD A,31
        CALL page_bank
        CALL print_menu
        CALL highlight
        CALL show_status
        LD HL,0x5025
        LD DE,checkbox_x
        LD B,8
save_checkbox:
        LD A,(HL)
        LD (DE),A
        INC DE
        INC H
        DJNZ save_checkbox
        LD HL,0x4000
        LD DE,0xA000
        LD BC,6912
        LDIR
menu_snapshot_done:
        LD HL,0xC000
        LD DE,0x4000
        LD BC,6912
        LDIR
        LD A,23
        CALL page_bank
        LD HL,0xA000
        LD DE,0xC000
        LD BC,6912
        LDIR
        LD BC,0xFBDF
        IN A,(C)
        LD (mouse_raw_x),A
        LD BC,0xFFDF
        IN A,(C)
        LD (mouse_raw_y),A
        LD IX,cache_extents
        IM 1
load_extent:
        LD A,(IX+0)
        CP 255
        JR Z,loaded
        CALL page_bank
        LD E,(IX+1)
        LD D,(IX+2)
        LD (disk_position),DE
        LD B,(IX+3)
        LD HL,0xC000
        EI
        CALL read_n
        DI
        LD DE,4
        ADD IX,DE
        JR load_extent
loaded: CALL prepare_next
        CALL install_irq
        LD A,1
        LD (queued_command),A
ready:  EI
autoplay_wait:
menu_ready:
        HALT
field_start:
        CALL ui_tick
        CALL graphics_tick
menu_frame_done:
        JP menu_ready

; Music owns the ULA interrupt. Slow one-shot graphics decoding and screen
; copies are foreground work and may span fields, but never defer AY service.
; Save both AF sets (LZSA-compatible), the main pairs and the paged input bank.
; IX/IY and alternate BC/DE/HL are untouched by every called music routine.
irq:    PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL
        EX AF,AF'
        PUSH AF
        EX AF,AF'
        LD A,(actual_page)
        PUSH AF
        LD HL,(field_counter)
        INC HL
        LD (field_counter),HL
        LD HL,(hold_counter)
        LD A,H
        OR L
        JR Z,irq_command
        DEC HL
        LD (hold_counter),HL
irq_command:
        LD A,(queued_command)
        OR A
        JR Z,irq_audio
        LD B,A
        XOR A
        LD (queued_command),A
        LD (pause_remaining),A
        LD A,B
        CP 3
        JR Z,irq_stop
        DEC A
        LD (selected),A
        CALL choose
        JR audio_done
irq_stop:
        CALL stop_song
        JR audio_done
irq_audio:
        LD A,(pause_remaining)
        OR A
        JR Z,irq_active
        DEC A
        LD (pause_remaining),A
        JR NZ,audio_done
        CALL choose
        JR audio_done
irq_active:
        LD A,(playing)
        CP 255
        JR Z,audio_done
        CALL page_stream
        CALL music_tick
audio_done:
        POP AF
        CALL page_bank
        EX AF,AF'
        POP AF
        EX AF,AF'
        POP HL
        POP DE
        POP BC
        POP AF
        EI
        RETI

; Grammar byte provider. BC/DE survive; HL is scratch. Pending right children
; live at B700..B717, separate from the CPU stack and incoming artwork. Each
; leaf is the EXACT old row-stream byte; no note, voice or duration is removed.
; Children <256 are literals; 256..382 select four-byte dictionary entries.
read_byte:
        PUSH BC
        PUSH DE
        LD HL,(grammar_sp)
        LD A,L
        OR A
        JR Z,grammar_root
        DEC HL
        LD B,(HL)
        DEC HL
        LD C,(HL)
        LD (grammar_sp),HL
        JR grammar_expand
grammar_root:
        CALL read_packed_byte
        LD C,A
        LD B,0
        CP 128
        JR C,grammar_leaf
        CP 255
        JR Z,grammar_escape
        SUB 128
        LD C,A
        INC B
grammar_expand:
        LD A,B
        OR A
        JR Z,grammar_leaf
        LD L,C
        LD H,0
        ADD HL,HL
        ADD HL,HL
        LD DE,grammar_dictionary
        ADD HL,DE
        LD E,(HL)
        INC HL
        LD D,(HL)
        INC HL
        LD C,(HL)
        INC HL
        LD B,(HL)
        LD HL,(grammar_sp)
        LD (HL),C
        INC HL
        LD (HL),B
        INC HL
        LD (grammar_sp),HL
        LD B,D
        LD C,E
        JR grammar_expand
grammar_escape:
        CALL read_packed_byte
        LD C,A
grammar_leaf:
        LD A,C
        LD HL,(raw_position)
        INC HL
        LD (raw_position),HL
        POP DE
        POP BC
        RET

; All paging stores the intended latch before OUT. An IRQ between these two
; instructions restores that same intended bank before the interrupted OUT.
page_bank:
        OR 16
        LD (actual_page),A
        LD BC,0x7FFD
stream_page:
        OUT (C),A
        RET

queued_command: DEFB 0
actual_page: DEFB 16
pause_remaining: DEFB 0
grammar_sp: DEFW 0xB700
raw_position: DEFW 0
field_counter: DEFW 0
hold_counter: DEFW 300
