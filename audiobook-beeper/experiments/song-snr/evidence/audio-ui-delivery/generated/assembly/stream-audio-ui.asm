; Optional loading UI for the continuous audio disk. Include at any proved
; fixed bank-2 address: this module contains no ORG or live-player hook.
; Include the public entries below FIRST; place stream-audio-ui-helper.asm
; separately in proved fixed bank-2 padding before the worker. Public entries
; use absolute helper addresses and the two chunks have no ordering dependency.
; CACHE_BAR and CACHE_RESTORE use the established cache ABI. All public
; routines clobber AF/BC/DE/HL, preserve IX/IY and every alternate register,
; and use the caller's ordinary loading stack. Never call during live PDM.
;
; Display bank 7 is protected through DAFF; audio in that bank starts at DB00.
; Row 20's centered 10-cell label uses D08B..D794 and DA8B..DA94. Row 22's
; 32-cell progress attributes are DAC0..DADF. Direct 48K-ROM font copying
; avoids ROM text routines that would write the decoder's normal screen RAM.

audio_ui_begin_loading:
        DI
        LD HL,(0x5C78)          ; low 16 ROM FRAMES; modular elapsed arithmetic
        LD (audio_ui_frame),HL
        LD A,1
        LD (audio_ui_dots),A
        LD (audio_ui_loading),A
        XOR A
        LD (cache_bar),A
        CALL audio_ui_map_screen
        CALL audio_ui_loading_label
        LD D,0x3F               ; paper7/ink7: solid light gray, no BRIGHT
        LD C,0x07               ; black paper, light-gray ink for empty cells
        CALL audio_ui_bar_mapped
        JP audio_ui_leave_enabled

; Call only after a completed physical read/copy, including optional header
; sectors after the cover is visible. Suppressed updates change neither bank
; selection nor IFF. ROM FRAMES, rather than source/sector count, sets the
; approximate 0.5-s period; long blocked reads can delay observation. A 16-bit
; difference also handles FRAMES wrapping. Large delays advance one phase,
; avoiding a burst of several labels when reads resume.
audio_ui_sector_tick:
        LD A,(audio_ui_loading)
        OR A
        RET Z
        LD HL,(0x5C78)
        LD DE,(audio_ui_frame)
        OR A
        SBC HL,DE
        LD DE,25
        OR A
        SBC HL,DE
        RET C
        LD HL,(0x5C78)
        LD (audio_ui_frame),HL
        LD A,(audio_ui_dots)
        INC A
        CP 4
        JR C,audio_ui_phase_ready
        LD A,1
audio_ui_phase_ready:
        LD (audio_ui_dots),A
        CALL audio_ui_map_screen
        CALL audio_ui_loading_label
        JP audio_ui_leave_enabled

; Replacement for the existing loading-only CACHE_DRAW_BAR call. CACHE_BAR
; is 0..32, calculated by the original exact-sector fractional accumulator.
; Rendering restores normal bank 0 before EI; the loader maps its destination
; again before the next physical sector copy.
audio_ui_draw_loading_bar:
        CALL audio_ui_map_screen
        LD D,0x3F
        LD C,0x07
        CALL audio_ui_bar_mapped
        JP audio_ui_leave_enabled

; Call once per loaded batch before entering/resuming live audio. This only
; paints PLAYING and resets the green progress display; a separate proved
; clock path owns playback advancement. It returns in normal bank 0 with DI.
audio_ui_begin_playback:
        DI
        XOR A
        LD (audio_ui_loading),A
        LD (cache_bar),A
        CALL audio_ui_map_screen
        LD HL,audio_ui_playing
        LD DE,0xD08B
        CALL audio_ui_print
        LD A,0x04
        CALL audio_ui_label_attributes
        LD D,0x24               ; green paper/ink for filled playback cells
        LD C,0x04               ; green ink on black paper for empty cells
        CALL audio_ui_bar_mapped
        JP audio_ui_leave_disabled

; Map protected shadow screen/48K ROM. CACHE_RESTORE independently clears
; Scorpion's high-RAM selector. Calling code must remain in fixed bank 2.
audio_ui_map_screen:
        DI
        LD A,31
        JP cache_restore

audio_ui_leave_enabled:
        LD A,24
        CALL cache_restore
        EI
        RET

; Common paused/end return: ordinary bank 0 with interrupts disabled.
audio_ui_leave_disabled:
        LD A,24
        CALL cache_restore
        DI
        RET

audio_ui_startup_end:
