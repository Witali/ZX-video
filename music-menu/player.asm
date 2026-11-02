; Expedition 33 Demo. Music is serviced on every real ULA IRQ; graphics and
; immutable compressed sources are fully resident before playback begins.
        ORG 0x8000
        INCLUDE "demo-core.asm"
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

; Start/restart the selected cached song, called only by the IM2 audio owner.
; Reset the complete AY chip before applying tick zero in this same field.
; Clobbers AF/BC/DE/HL. Every selection has its own absolute field origin.
choose: NOP
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
        LD (raw_position),A
        LD (raw_position+1),A
        LD HL,0xB700
        LD (grammar_sp),HL
        LD A,2
        LD (status),A
        LD A,1
        LD (dirty),A
song_started:
        CALL music_tick
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
        LD A,(playing)
        LD E,A
        LD D,0
        XOR 1
        LD (selected),A
        LD HL,song_pauses
        ADD HL,DE
        LD A,(HL)
        LD (pause_remaining),A
        CALL stop_song
        LD A,(pause_remaining)
        OR A
        JP Z,choose
        RET

; Silence the active stream. The ISR owns interrupt enable/restore; foreground
; controls only queue commands. EOF selects the next track after its pause.
stop_song:
        NOP
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
; Ordinary packed-byte path 75 T. Music fits entirely in cache bank0; the
; retained general bank-cross path includes the shared paging helper.
read_packed_byte:
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
        JP page_bank

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
mute:   NOP
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
        LD B,0xDF
        IN A,(C)
        BIT 2,A
        LD A,7
        RET Z
        LD B,0x7F
        IN A,(C)
        BIT 2,A
        LD A,8
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
        JR C,mouse_second
        CP 136
        JR C,no_click
        CP 152
        JR NC,no_click
        LD A,2
        RET
mouse_second:
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

code_end:
        ASSERT $ <= 0x8C00
        DS 0x8C00-$
; Mask slots prepare all generators first, then apply volumes/ENV enables.
; The aligned lookup keeps the streaming hot path independent of code layout.
register_order: DEFB 0,1,2,3,4,5,6,7,11,12,13,8,9,10
        DS 0x8D00-$
; The project's 74-byte ZX0 SMC decoder. Complete forward v2 block ABI:
; HL=input, DE=output; main AF/BC/DE/HL scratch, alternate registers preserved.
        INCLUDE "zx0.inc"
        DS 0x8E00-$
        INCLUDE "variants.inc"
        ASSERT $ <= 0x9400
        DS 0x9400-$
        INCLUDE "demo-graphics.asm"
        ASSERT $ <= 0x9C00
        DS 0x9C00-$
shared_footer:
        INCLUDE "footer.inc"
        ASSERT $ == 0xA000
        DS 0xBFFF-$
        DEFB 0
