; Fixed bank-2 helpers for stream-audio-ui.asm. Include at the independently
; proved AUDIO_UI_RESIDENT_ORIGIN; require AUDIO_UI_END below worker origin.
; These routines are loading/paused/end only and must never run during PDM.

audio_ui_resident_begin:

; Bank 7/48K ROM mapped, IRQ disabled. The complete 10-cell fixed-width block
; is rewritten so dot phases do not move the title or leave stale glyphs.
audio_ui_loading_label:
        LD HL,audio_ui_loading_one
        LD A,(audio_ui_dots)
        CP 2
        JR C,audio_ui_label_ready
        LD HL,audio_ui_loading_two
        JR Z,audio_ui_label_ready
        LD HL,audio_ui_loading_three
audio_ui_label_ready:
        LD DE,0xD08B
        CALL audio_ui_print
        LD A,0x07
        JP audio_ui_label_attributes

; A=attribute; bank 7 mapped. HL/BC clobbered, exactly row 20 columns 11..20.
audio_ui_label_attributes:
        LD HL,0xDA8B
        LD B,10
audio_ui_label_attribute_next:
        LD (HL),A
        INC HL
        DJNZ audio_ui_label_attribute_next
        RET

; Bank 7 mapped; D=filled attribute, C=empty, CACHE_BAR=0..32. AF/BC/DE/HL
; clobbered. No paging or interrupts inside the 32-cell attribute loop.
audio_ui_bar_mapped:
        LD HL,0xDAC0
        LD A,(cache_bar)
        LD E,A
        LD B,32
audio_ui_bar_next:
        LD A,E
        OR A
        LD A,C
        JR Z,audio_ui_bar_empty
        DEC E
        LD A,D
audio_ui_bar_empty:
        LD (HL),A
        INC HL
        DJNZ audio_ui_bar_next
        RET

; HL=NUL-terminated ASCII, DE=top pixel byte of a character row. Return with
; HL at the terminator and DE advanced by the character count. AF/BC scratch.
; Uses the same 3C00+8*ASCII font convention as STREAM_FINISH, but returns at
; NUL rather than entering its terminal HALT loop. For callers here length 10
; cannot cross a 32-cell row; incrementing D visits the eight Spectrum scans.
audio_ui_print:
        LD A,(HL)
        OR A
        RET Z
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
audio_ui_glyph:
        LD A,(HL)
        LD (DE),A
        INC HL
        INC D
        DJNZ audio_ui_glyph
        POP DE
        INC E
        POP HL
        JR audio_ui_print

audio_ui_loading_one:   DEFM "LOADING.  ",0
audio_ui_loading_two:   DEFM "LOADING.. ",0
audio_ui_loading_three: DEFM "LOADING...",0
audio_ui_playing:       DEFM "PLAYING   ",0

; Mutable loading-only state is explicitly bounded for native memory guards.
; Do not alias the frame snapshot with the persistent playback descriptors.
audio_ui_data_start:
audio_ui_loading: DEFB 0
audio_ui_dots: DEFB 0
audio_ui_frame: DEFW 0
audio_ui_data_end:

; Redraw an already calculated global playback fill count without resetting
; CACHE_BAR. Call only while paused/refilling or after the final mute. Return
; in normal bank 0 with DI; clobber AF/BC/DE/HL, preserve IX/IY/alternates.
audio_ui_redraw_playback_bar:
        CALL audio_ui_map_screen
        LD D,0x24
        LD C,0x04
        CALL audio_ui_bar_mapped
        JP audio_ui_leave_disabled

; Clear the centered PLAYING label before the existing end message at column
; 0. Leave the final progress fill intact, disable loading animation, and
; return in normal bank 0 with DI. No audio code may be active at this call.
audio_ui_clear_label:
        XOR A
        LD (audio_ui_loading),A
        CALL audio_ui_map_screen
        LD HL,audio_ui_blank
        LD DE,0xD08B
        CALL audio_ui_print
        LD A,0x04
        CALL audio_ui_label_attributes
        JP audio_ui_leave_disabled

audio_ui_blank: DEFM "          ",0

audio_ui_end:
