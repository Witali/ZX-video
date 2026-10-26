; AY-only Spectrum128 jukebox. RAM2 contains code, text, stack and IM2.
; Both complete delta streams are loaded once into RAM banks 0/4/6/1/3/7.
; The visible menu stays active during playback; switching never calls TR-DOS.
        ORG 0x8000
start:  DI
        LD SP,0xBD00
        LD IY,0x5C3A
        XOR A
        OUT (0xFE),A
        LD (selected),A
        LD (last_command),A
        LD A,255
        LD (playing),A
        CALL mute
        CALL print_menu
        CALL highlight
        LD A,1
        LD (status),A
        CALL show_status
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
        OR 16
        LD BC,0x7FFD
        OUT (C),A
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
loaded: CALL install_irq
        XOR A
        LD (status),A
        CALL show_status
        CALL cursor
        EI
ready:  NOP
menu_ready:
        HALT
; Audio is serviced first, before any cursor/attribute work. The remaining
; UI work must finish inside this same ULA field; complete Fuse runs check it.
field_start:
        DI
        LD A,(playing)
        CP 255
        CALL NZ,music_tick
audio_done:
        EI
        CALL cursor
        CALL mouse
        LD (click_pending),A
        CALL keys
        LD B,A
        LD A,(last_command)
        CP B
        LD A,B
        LD (last_command),A
        JR NZ,key_changed
        XOR A
key_changed:
        OR A
        JR NZ,dispatch
        LD A,(click_pending)
        OR A
        JR Z,finish_ui
        LD A,6
dispatch:
        CP 1
        JR Z,choose_first
        CP 2
        JR Z,choose_second
        CP 3
        JR Z,stop_from_menu
        CP 4
        JR Z,select_first
        CP 5
        JR Z,select_second
start_from_menu:
        CALL choose
        JR finish_ui
choose_first:
        XOR A
        LD (selected),A
        JR start_from_menu
choose_second:
        LD A,1
        LD (selected),A
        JR start_from_menu
select_first:
        XOR A
        LD (selected),A
        JR selection_changed
select_second:
        LD A,1
        LD (selected),A
selection_changed:
        LD A,1
        LD (dirty),A
        JR finish_ui
stop_from_menu:
        CALL stop_song
        EI
finish_ui:
        LD A,(dirty)
        OR A
        JR Z,draw_cursor
        XOR A
        LD (dirty),A
        CALL highlight
        CALL show_status
draw_cursor:
        CALL cursor
menu_frame_done:
        JP menu_ready

; Main AF/registers are untouched. ULA entry 19 T, body EI 4 + RETI 14 = 18 T.
; The foreground is HALTed between fields; no continuous CPU audio carrier.
irq:    EI
        RETI

; Standard ROM output, used once before disk loading and never in live audio.
; BASIC/TR-DOS supplied valid system variables. Restore the stock CHARS base,
; permanent/temporary attributes and stream2, then print AT controls via RST10.
; All main registers are scratch; the text cursor HL is saved across each RST.
print_menu:
        LD HL,0x3C00
        LD (23606),HL
        XOR A
        LD (23624),A
        LD (23694),A
        LD (23696),A
        LD (23697),A
        LD A,0x47
        LD (23693),A
        LD (23695),A
        CALL 0x0DAF
        LD A,2
        CALL 0x1601
        LD HL,menu_text
print_next:
        LD A,(HL)
        INC HL
        CP 255
        RET Z
        PUSH HL
rom_character:
        RST 0x10
        POP HL
        JR print_next

; Start/restart the selected cached song. Called with a normal RAM2 stack.
; Reset the complete AY chip before applying tick zero in this same field.
; Clobbers AF/BC/DE/HL. Every selection has its own absolute field origin.
choose: DI
        CALL mute
        LD A,(selected)
        LD (playing),A
        LD E,A
        ADD A,A
        ADD A,E
        LD E,A
        LD D,0
        LD HL,song_table
        ADD HL,DE
        LD A,(HL)
        LD (current_bank_index),A
        INC HL
        LD E,(HL)
        INC HL
        LD D,(HL)
        LD (record_pointer),DE
        CALL page_stream
        XOR A
        LD (remaining),A
        LD A,2
        LD (status),A
        LD A,1
        LD (dirty),A
song_started:
        CALL music_tick
        EI
        RET

; One field of a delta-register stream. No implicit R13 write: bit 13 must
; explicitly request a restart. Sustains do no I/O; hardware keeps running.
; AF/BC/DE/HL are scratch. A zero duration is EOF; a nonzero duration counts
; this field plus duration-1 subsequent calls. All 14 mask bits are consumed.
music_tick:
        LD A,(remaining)
        OR A
        JR Z,next_record
        DEC A
        LD (remaining),A
        RET
next_record:
        CALL read_byte
        OR A
        JR Z,finished
        DEC A
        LD (remaining),A
        CALL read_byte
        LD E,A
        CALL read_byte
        LD D,A
        XOR A
        LD (register_index),A
        LD C,0xFD
mask_loop:
        SRL D
        RR E
        JR NC,no_write
        CALL read_byte
        LD B,A
        LD A,(register_index)
        LD L,A
        LD H,0x8C
        LD A,(HL)
        LD H,B
        LD B,0xFF
        OUT (C),A
        LD B,0xBF
ay_out:
        OUT (C),H
no_write:
        LD A,(register_index)
        INC A
        LD (register_index),A
        CP 14
        JR NZ,mask_loop
record_event:
        NOP
music_tick_done:
        RET
finished:
        CALL stop_song
        RET

; Silence and stop the active stream. DI is retained for the caller to
; restore: audio_done or stop_from_menu enables IRQ before the next HALT.
stop_song:
        DI
        CALL mute
        LD A,255
        LD (playing),A
        XOR A
        LD (status),A
        LD A,1
        LD (dirty),A
stopped:
        RET

; Return the next cached byte in A, preserving BC/DE. HL is scratch.
; Cursor0000 means the previous read consumed FFFF: page the next physical
; bank before reading C000. Even masks/value lists may cross the boundary.
; Ordinary path 75 T; boundary work is measured separately.
read_byte:
        LD HL,(record_pointer)
        LD A,H
        OR L
        JR NZ,byte_in_bank
        PUSH BC
        PUSH DE
        LD A,(current_bank_index)
        INC A
        LD (current_bank_index),A
        CALL page_stream
        POP DE
        POP BC
        LD HL,0xC000
byte_in_bank:
        LD A,(HL)
        INC HL
        LD (record_pointer),HL
        RET
page_stream:
        LD A,(current_bank_index)
        LD E,A
        LD D,0
        LD HL,bank_order
        ADD HL,DE
        LD A,(HL)
        OR 16
        LD BC,0x7FFD
stream_page:
        OUT (C),A
        RET

; Install the fixed RAM2 IM2 vector table and jump. AF/BC/DE/HL are scratch.
install_irq:
        LD HL,0xBE00
        LD DE,0xBE01
        LD BC,256
        LD (HL),0xBD
        LDIR
        LD A,0xC3
        LD (0xBDBD),A
        LD HL,irq
        LD (0xBDBE),HL
        LD A,0xBE
        LD I,A
        IM 2
        RET
mute:   XOR A
        OUT (0xFE),A
        LD D,14
        LD C,0xFD
        LD HL,mute_values
mute_loop:
        LD A,(HL)
        INC HL
        LD B,0xFF
        OUT (C),A
        LD E,(HL)
        INC HL
        LD B,0xBF
mute_out:
        OUT (C),E
        DEC D
        JR NZ,mute_loop
        RET

; Startup-only TR-DOS reads: B sectors, HL page-aligned destination;
; disk_position is track:D/sector:E. IX is preserved; AF/BC/DE/HL are scratch.
; ROM execution and floppy latency are separate from player CPU timings.
read_n: PUSH BC
        PUSH HL
        PUSH IX
        LD DE,(disk_position)
        LD BC,0x0105
disk_call:
        CALL 0x3D13
        POP IX
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
        DJNZ read_n
        RET


; Commands 1/2 start immediately, 3 is Space stop, 4/5 are 7/6 navigation,
; 6 is Enter. Edge detection is shared by idle and active playback.
keys:   LD BC,0xF7FE
        IN A,(C)
        BIT 0,A
        LD A,1
        RET Z
        IN A,(C)
        BIT 1,A
        LD A,2
        RET Z
        LD B,0x7F
        IN A,(C)
        BIT 0,A
        LD A,3
        RET Z
        LD B,0xEF
        IN A,(C)
        BIT 3,A
        LD A,4
        RET Z
        IN A,(C)
        BIT 4,A
        LD A,5
        RET Z
        LD B,0xBF
        IN A,(C)
        BIT 0,A
        LD A,6
        RET Z
        XOR A
        RET

; Kempston counters are relative modulo256; Y grows upwards. Signed deltas
; update a bounded screen cursor. Missing hardware (FF on reads) is stationary
; and never clicks. Left button is active-low bit1, with a separate edge latch.
mouse:  LD BC,0xFBDF
        IN A,(C)
        LD D,A
        LD A,(mouse_raw_x)
        LD E,A
        LD A,D
        LD (mouse_raw_x),A
        SUB E
        LD E,A
        LD A,(mouse_x)
        CALL clamp_x
        LD (mouse_x),A
        LD BC,0xFFDF
        IN A,(C)
        LD D,A
        LD A,(mouse_raw_y)
        SUB D
        LD E,A
        LD A,D
        LD (mouse_raw_y),A
        LD A,(mouse_y)
        CALL clamp_y
        LD (mouse_y),A
        LD BC,0xFADF
        IN A,(C)
        AND 2
        LD B,A
        LD A,(mouse_button)
        LD C,A
        LD A,B
        LD (mouse_button),A
        OR A
        JR NZ,no_click
        LD A,C
        OR A
        JR Z,no_click
        LD A,(mouse_x)
        CP 16
        JR C,no_click
        CP 240
        JR NC,no_click
        LD A,(mouse_y)
        CP 62
        JR C,no_click
        CP 91
        JR C,mouse_first
        CP 94
        JR C,no_click
        CP 123
        JR NC,no_click
        LD A,1
        LD (selected),A
        RET
mouse_first:
        XOR A
        LD (selected),A
        INC A
        RET
no_click:
        XOR A
        RET
clamp_x:
        LD B,247
        JR clamp
clamp_y:
        LD B,183
clamp:  LD D,0
        BIT 7,E
        JR Z,delta_positive
        DEC D
delta_positive:
        LD L,A
        LD H,0
        ADD HL,DE
        BIT 7,H
        JR NZ,clamp_min
        LD A,H
        OR A
        JR NZ,clamp_max
        LD A,L
        CP 8
        JR C,clamp_min
        CP B
        RET C
clamp_max:
        LD A,B
        RET
clamp_min:
        LD A,8
        RET

; XOR an eight-pixel-wide arrow on an eight-pixel X grid. The screen address
; is recomputed per scanline, including Spectrum's interleaved character rows.
; Calling twice restores the original bitmap. Clobbers AF/BC/DE/HL/IX.
cursor: LD IX,cursor_bits
        LD A,(mouse_y)
        LD D,A
        LD B,8
cursor_line:
        LD A,D
        AND 7
        OR 0x40
        LD H,A
        LD A,D
        RRCA
        RRCA
        RRCA
        AND 0x18
        OR H
        LD H,A
        LD A,D
        AND 0x38
        RLCA
        RLCA
        LD L,A
        LD A,(mouse_x)
        RRCA
        RRCA
        RRCA
        AND 31
        OR L
        LD L,A
        LD A,(IX+0)
        XOR (HL)
        LD (HL),A
        INC IX
        INC D
        DJNZ cursor_line
        RET


; Attributes distinguish the current song (green) from the selection (blue).
; Updates occur only after an input/state change. Fill: HL address,B count,A.
highlight:
        LD HL,0x5900
        LD B,96
        LD A,0x46
        CALL fill
        LD HL,0x5980
        LD B,96
        LD A,0x46
        CALL fill
        LD A,(playing)
        CP 255
        JR Z,selection_attr
        OR A
        LD HL,0x5900
        JR Z,playing_attr
        LD HL,0x5980
playing_attr:
        LD A,0x67
        LD B,96
        CALL fill
selection_attr:
        LD A,(selected)
        OR A
        LD HL,0x5900
        JR Z,selected_attr
        LD HL,0x5980
selected_attr:
        LD A,0x4F
        LD B,96
        JP fill
show_status:
        LD HL,0x5A60
        LD B,64
        LD A,0x41
        CALL fill
        LD A,(status)
        LD HL,0x5A62
        OR A
        JR Z,status_attr
        LD HL,0x5A6A
        DEC A
        JR Z,status_attr
        LD HL,0x5A74
status_attr:
        PUSH HL
        LD B,8
        LD A,0x46
        CALL fill
        POP HL
        LD DE,32
        ADD HL,DE
        LD B,8
        LD A,0x46
fill:   LD (HL),A
        INC HL
        DJNZ fill
        RET

selected: DEFB 0
playing: DEFB 255
status: DEFB 0
dirty: DEFB 0
last_command: DEFB 0
click_pending: DEFB 0
mouse_x: DEFB 120
mouse_y: DEFB 76
mouse_raw_x: DEFB 0
mouse_raw_y: DEFB 0
mouse_button: DEFB 2
cursor_bits: DEFB 0x80,0xC0,0xE0,0xF0,0xF8,0xD0,0x88,0x08
remaining: DEFB 0
register_index: DEFB 0
record_pointer: DEFW 0
current_bank_index: DEFB 0
disk_position: DEFW 0
bank_order: DEFB 0,4,6,1,3,7
        INCLUDE "variants.inc"
code_end:
        ASSERT $ <= 0x8C00
        DS 0x8C00-$
; Mask slots prepare all generators first, then apply volumes/ENV enables.
; The aligned lookup keeps the streaming hot path independent of code layout.
register_order: DEFB 0,1,2,3,4,5,6,7,11,12,13,8,9,10
        DS 0x9000-$
        DS 0xBFFF-$
        DEFB 0
