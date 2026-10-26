; Spectrum128/Beta Disk jukebox. All code, DDS tables and stacks are in RAM2.
; Disk data is loaded into up to six other banks BEFORE playback begins.
; Sixteen-byte RLE records never cross C000..FFFF bank boundaries.
; Music uses ULA frame interrupts as its clock; a delayed service cannot
; move the schedule origin. No ROM/disk calls occur during live audio.
        ORG 0x8000
start:  DI
        LD SP,0xBD00
        LD IY,0x5C3A
        XOR A
        OUT (0xFE),A
        LD (selected),A
        LD (mode),A
        CALL install_irq
        CALL mute
        LD BC,0xFBDF
        IN A,(C)
        LD (mouse_raw_x),A
        LD BC,0xFFDF
        IN A,(C)
        LD (mouse_raw_y),A
menu:   DI
        LD SP,0xBD00
        CALL mute
        LD HL,screen_data
        LD DE,0x4000
        LD BC,6912
        LDIR
        CALL highlight
        XOR A
        LD (status),A
        CALL show_status
        CALL cursor
        EI
menu_ready:
        HALT
        CALL cursor
        CALL mouse
        PUSH AF
        CALL highlight
        CALL cursor
        POP AF
        OR A
        JP NZ,choose
        CALL keys
        LD B,A
        LD A,(last_command)
        CP B
        LD A,B
        LD (last_command),A
        JR Z,menu_ready
        OR A
        JR Z,menu_ready
        CP 1
        JR Z,choose_first
        CP 2
        JR Z,choose_second
        CP 3
        JR Z,toggle_mode
        CP 4
        JR Z,select_first
        CP 5
        JR Z,select_second
        JP choose
choose_first:
        XOR A
        LD (selected),A
        JP choose
choose_second:
        LD A,1
        LD (selected),A
        JP choose
select_first:
        XOR A
        LD (selected),A
        JR menu_ready
select_second:
        LD A,1
        LD (selected),A
        JR menu_ready
toggle_mode:
        LD A,(mode)
        XOR 1
        LD (mode),A
        JR menu_ready

; Selection*2+mode addresses a list of (bank,sector,track,count) extents.
; IM1/IY/ROM48 are restored for TR-DOS. IX is a fixed-RAM extent cursor.
choose:
        CALL highlight
        LD A,1
        LD (status),A
        CALL show_status
        LD A,(selected)
        ADD A,A
        LD B,A
        LD A,(mode)
        ADD A,B
        ADD A,A
        LD E,A
        LD D,0
        LD HL,variant_table
        ADD HL,DE
        LD E,(HL)
        INC HL
        LD D,(HL)
        PUSH DE
        POP IX
        DI
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
loaded:
        CALL install_irq
        LD A,2
        LD (status),A
        CALL show_status
        LD A,16
        LD (current_bank),A
        LD BC,0x7FFD
        OUT (C),A
        LD HL,0xC000
        LD (record_pointer),HL
        LD HL,0
        LD (remaining),HL
        LD (pwm_step+1),HL
        LD A,0xAB
        LD (pwm_page+1),A
        XOR A
        LD (frame_due),A
ready:  EI
        HALT
        JP field_work

; The IM2 handler preserves main AF and all main register pairs; AF' is scratch.
; Leave interrupts
; enabled through BOTH pulse levels: masking even an 85-T high can miss the
; short ULA INT window. IRQ can extend either level by 65 CPU T; field service
; extends low intervals. Both effects are measured separately from 242 T.
irq:    EX AF,AF'
        LD A,1
        LD (frame_due),A
        EX AF,AF'
        EI
        RETI

; HL is the 16-bit DDS phase. Events patch step and wave-page atomically.
; B/C are a temporary wave-table pointer; DE is the phase increment.
; Duty q=0..15 patches complementary NOP ladders, q+(15-q)=15 NOPs.
; Ordinary period: 242 CPU T, rising-to-falling:25+4*q T (no ULA waits).
pwm_sample:
pwm_step:
        LD DE,0
        ADD HL,DE
        LD C,H
pwm_page:
        LD B,0xAB
        LD A,(BC)
        LD C,A
        LD A,15
        SUB C
        LD (high_jump+1),A
        LD A,C
        LD (low_jump+1),A
        NOP
        LD A,16
pwm_high:
        OUT (0xFE),A
high_jump:
        JP high_nops

; Field service owns AF/BC/DE but preserves the DDS phase on the fixed stack.
; Only new RLE rows write AY. Sustains keep sounding in hardware without I/O.
; Keyboard is polled every field; Space mutes both outputs before menu redraw.
field_work:
        DI
        PUSH HL
        XOR A
        LD (frame_due),A
        LD BC,0x7FFE
        IN A,(C)
        BIT 0,A
        JP Z,stop
        LD HL,(remaining)
        LD A,H
        OR L
        JR Z,next_record
        DEC HL
        LD (remaining),HL
        JP tick_done
next_record:
        LD HL,(record_pointer)
        LD A,H
        OR A
        JR NZ,record_in_bank
        ; The record cursor wraps only after a full 16 KiB bank.
        LD A,(current_bank)
        LD HL,bank_order
find_bank:
        CP (HL)
        INC HL
        JR NZ,find_bank
        LD A,(HL)
        LD (current_bank),A
        LD BC,0x7FFD
        OUT (C),A
        LD HL,0xC000
record_in_bank:
        LD E,(HL)
        INC HL
        LD D,(HL)
        INC HL
        LD A,D
        OR E
        JP Z,finished
        DEC DE
        LD (remaining),DE
        LD E,(HL)
        INC HL
        LD D,(HL)
        INC HL
        LD (pwm_step+1),DE
        LD A,(HL)
        INC HL
        LD (pwm_page+1),A
        LD D,0
        LD C,0xFD
ay_loop:
        LD E,(HL)
        INC HL
        LD B,0xFF
        OUT (C),D
        LD B,0xBF
ay_out:
        OUT (C),E
        INC D
        LD A,D
        CP 11
        JR NZ,ay_loop
        LD (record_pointer),HL
record_event:
        NOP
tick_done:
        POP HL
        LD A,(mode)
        OR A
        EI
        JP Z,pwm_sample
ay_wait:
        HALT
        JP field_work
finished:
stop:   POP HL
        JP menu

; ROM48 paging bit is always set. The same code is used for startup and
; each selection; previous RAM, chip state and stack contents are irrelevant.
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
        LD D,0
        LD E,0
        LD C,0xFD
mute_loop:
        LD B,0xFF
        OUT (C),D
        LD B,0xBF
mute_out:
        OUT (C),E
        INC D
        LD A,D
        CP 14
        JR NZ,mute_loop
        RET

; Single-sector ROM reads keep the logical track/sector cursor explicit.
; These calls execute only with music muted; ROM/floppy time is not CPU audio.
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

; Return a command number, zero for no key. Commands are edge-triggered in
; menu_ready; number keys start immediately, 6/7 select, Enter starts, M mode.
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
        BIT 2,A
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

; Selection/mode/status use attributes only; no ROM font or external screen
; assets are needed on the target. fill uses B bytes, A attribute, HL address.
highlight:
        LD HL,0x5900
        LD B,96
        LD A,0x46
        CALL fill
        LD HL,0x5980
        LD B,96
        LD A,0x46
        CALL fill
        LD A,(selected)
        OR A
        LD HL,0x5900
        JR Z,selected_attr
        LD HL,0x5980
selected_attr:
        LD A,0x4F
        LD B,96
        CALL fill
        LD HL,0x5A20
        LD B,64
        LD A,0x41
        CALL fill
        LD HL,0x5A22
        LD A,(mode)
        OR A
        JR Z,mode_attr
        LD HL,0x5A33
mode_attr:
        PUSH HL
        LD B,12
        LD A,0x47
        CALL fill
        POP HL
        LD DE,32
        ADD HL,DE
        LD B,12
        LD A,0x47
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
mode:   DEFB 0
status: DEFB 0
last_command: DEFB 0
mouse_x: DEFB 120
mouse_y: DEFB 76
mouse_raw_x: DEFB 0
mouse_raw_y: DEFB 0
mouse_button: DEFB 2
cursor_bits: DEFB 0x80,0xC0,0xE0,0xF0,0xF8,0xD0,0x88,0x08
frame_due: DEFB 0
remaining: DEFW 0
record_pointer: DEFW 0
current_bank: DEFB 16
disk_position: DEFW 0
bank_order: DEFB 16,20,22,17,19,23,16
        INCLUDE "variants.inc"
code_end:
        ASSERT $ <= 0x8C00
        DS 0x8C00-$
high_nops:
        DS 15
        XOR A
pwm_low:
        OUT (0xFE),A
        EI
low_jump:
        JP low_nops
        DS 0x8D00-$
low_nops:
        DS 15
        LD A,(frame_due)
        OR A
        JP NZ,field_work
        JP pwm_sample
        DS 0x9000-$
screen_data:
        MDAT "screen.bin"
        ASSERT $ == 0xAB00
wave_data:
        MDAT "waves.bin"
        ASSERT $ == 0xBB00
        DS 0xBFFF-$
        DEFB 0
