; Foreground controls. Any key first reveals the menu without changing audio.
; Swallow that complete press/release, so Space cannot also stop the song.
; Menu commands are queued atomically for the next ULA ISR; ROM is never used.
ui_tick:
        LD BC,0x00FE
        IN A,(C)
        AND 31
        CP 31
        LD B,A
        LD A,(menu_visible)
        OR A
        JR NZ,ui_menu
        LD A,B
        CP 31
        RET Z
        LD A,1
        LD (input_blocked),A
        JP show_menu
ui_menu:
        LD A,(input_blocked)
        OR A
        JR Z,ui_keys
        LD A,B
        CP 31
        RET NZ
        XOR A
        LD (input_blocked),A
        LD (last_command),A
        RET
ui_keys:
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
        CP 2
        LD A,7
        JR Z,dispatch
        LD A,6
dispatch:
        CP 7
        JR Z,toggle_pictures
        CP 8
        JR Z,resume_requested
        CP 4
        JR Z,select_first
        CP 5
        JR Z,select_second
        CP 3
        JR Z,stop_from_menu
        CP 1
        JR Z,choose_first
        CP 2
        JR Z,choose_second
        LD A,(selected)
        INC A
        JR queue_start
choose_first:
        LD A,1
        JR queue_start
choose_second:
        LD A,2
queue_start:
        LD (queued_command),A
resume_requested:
        LD A,(pictures_enabled)
        OR A
        JR Z,finish_ui
        JP resume_picture
stop_from_menu:
        LD A,3
        LD (queued_command),A
        JR finish_ui
select_first:
        XOR A
        JR selection_changed
select_second:
        LD A,1
selection_changed:
        LD (selected),A
        LD A,1
        LD (dirty),A
        JR finish_ui
toggle_pictures:
        LD A,(pictures_enabled)
        XOR 1
        LD (pictures_enabled),A
        CALL draw_checkbox
finish_ui:
        LD A,(dirty)
        OR A
        JR Z,draw_cursor
        XOR A
        LD (dirty),A
        CALL highlight
        CALL show_status
draw_cursor:
        JP cursor

show_menu:
        LD A,1
        LD (menu_visible),A
        LD A,7
        CALL page_bank
        LD HL,0xC000
        LD DE,0x4000
        LD BC,6912
        LDIR
        XOR A
        OUT (0xFE),A
        CALL highlight
        CALL show_status
        CALL draw_checkbox
        JP cursor

; Redraw only the checkbox glyph, using the same stock-ROM X bitmap captured
; at startup. Enabling pictures does not hide the menu until Play or M.
draw_checkbox:
        LD HL,checkbox_x
        LD DE,0x5025
        LD B,8
checkbox_line:
        LD A,(pictures_enabled)
        OR A
        LD A,0
        JR Z,checkbox_store
        LD A,(HL)
checkbox_store:
        LD (DE),A
        INC HL
        INC D
        DJNZ checkbox_line
        RET

; Entire one-shot decodes may span several ULA fields. The ISR preserves the
; source bank and all live decoder registers, so music retains its 50Hz clock.
; Table record is bank,U16 address,border,footer accent. A is the image index.
prepare_next:
        LD A,(next_picture)
prepare_picture:
        LD L,A
        LD H,0
        ADD HL,HL
        ADD HL,HL
        LD E,A
        LD D,0
        ADD HL,DE
        LD DE,picture_table
        ADD HL,DE
        LD A,(HL)
        PUSH HL
        CALL page_bank
        POP HL
        INC HL
        LD E,(HL)
        INC HL
        LD D,(HL)
        INC HL
        LD A,(HL)
        LD (incoming_border),A
        INC HL
        LD A,(HL)
        LD (incoming_accent),A
        EX DE,HL
        LD DE,0xA000
decode_picture:
        CALL 0x8D00
decoded_picture:
        LD A,1
        LD (prepared),A
        RET

resume_picture:
        LD A,(current_picture)
        CALL prepare_picture
        LD HL,0
resume_tile:
        PUSH HL
        XOR A
        LD (tile_kind),A
        CALL draw_tile
        POP HL
        INC HL
        LD DE,640
        OR A
        SBC HL,DE
        JR Z,resume_complete
        ADD HL,DE
        JR resume_tile
resume_complete:
        CALL draw_footer
        CALL picture_colors
        XOR A
        LD (menu_visible),A
        LD (prepared),A
        LD (transition_step),A
        LD HL,300
        LD (hold_counter),HL
        RET

graphics_tick:
        LD A,(menu_visible)
        OR A
        RET NZ
        LD A,(prepared)
        OR A
        CALL Z,prepare_next
        LD HL,(hold_counter)
        LD A,H
        OR L
        RET NZ
        LD A,(transition_step)
        OR A
        JR NZ,transition_active
        LD HL,0
        LD (dissolve_cursor),HL
        LD (reveal_cursor),HL
transition_active:
        CP 40
        JR NC,transition_reveal
        LD A,1
        LD (tile_kind),A
        LD HL,(dissolve_cursor)
        CALL tile_batch
        LD (dissolve_cursor),HL
transition_reveal:
        LD A,(transition_step)
        CP 12
        JR C,transition_advance
        XOR A
        LD (tile_kind),A
        LD HL,(reveal_cursor)
        CALL tile_batch
        LD (reveal_cursor),HL
transition_advance:
        LD A,(transition_step)
        INC A
        LD (transition_step),A
        CP 52
        RET NZ
        LD A,(next_picture)
        LD (current_picture),A
        INC A
        CP PICTURE_COUNT
        JR C,next_index
        XOR A
next_index:
        LD (next_picture),A
        CALL picture_colors
        XOR A
        LD (prepared),A
        LD (transition_step),A
        LD HL,300
        LD (hold_counter),HL
picture_complete:
        RET

; 73 is coprime with 640: a bounded affine permutation visits every 8x8 tile
; exactly once. A 12-field reveal delay turns each old tile into a small petal
; before its successor appears. Sixteen cells/field bounds foreground writes.
; HL cursor enters/exits; all main registers and IX are scratch.
tile_batch:
        LD IX,16
tile_batch_loop:
        PUSH HL
        CALL draw_tile
        POP HL
        LD DE,73
        ADD HL,DE
        LD DE,640
        OR A
        SBC HL,DE
        JR NC,tile_wrapped
        ADD HL,DE
tile_wrapped:
        DEC IX
        LD A,IXL
        OR A
        JR NZ,tile_batch_loop
        RET

; HL is row-major cell index 0..639. Incoming data is column-major: 160
; bitmap bytes then 20 attributes per column. Spectrum destination addressing
; explicitly interleaves the three 64-line thirds and eight scanline planes.
draw_tile:
        PUSH HL
        LD DE,0x5800
        ADD HL,DE
        LD (tile_attribute),HL
        POP HL
        LD A,L
        AND 31
        LD C,A
        LD A,H
        RLCA
        RLCA
        RLCA
        LD B,A
        LD A,L
        RRCA
        RRCA
        RRCA
        RRCA
        RRCA
        AND 7
        OR B
        LD B,A
        LD (tile_row),A
        AND 24
        OR 0x40
        LD D,A
        LD A,B
        AND 7
        RRCA
        RRCA
        RRCA
        OR C
        LD E,A
        LD (tile_destination),DE
        LD A,C
        ADD A,A
        LD L,A
        LD H,0
        LD DE,column_table
        ADD HL,DE
        LD E,(HL)
        INC HL
        LD D,(HL)
        LD (tile_source),DE
        LD A,(tile_kind)
        OR A
        LD HL,petal_bits
        JR NZ,tile_pixels
        LD L,B
        LD H,0
        ADD HL,HL
        ADD HL,HL
        ADD HL,HL
        ADD HL,DE
tile_pixels:
        LD DE,(tile_destination)
        LD B,8
tile_line:
        LD A,(HL)
        LD (DE),A
        INC HL
        INC D
        DJNZ tile_line
        LD A,(tile_kind)
        OR A
        LD A,0x43
        JR NZ,tile_attr_store
        LD HL,(tile_source)
        LD A,(tile_row)
        ADD A,160
        LD E,A
        LD D,0
        ADD HL,DE
        LD A,(HL)
tile_attr_store:
        LD DE,(tile_attribute)
        LD (DE),A
        RET

draw_footer:
        LD HL,shared_footer
        LD DE,0x5080
        LD B,8
footer_plane:
        PUSH BC
        LD BC,128
        LDIR
        POP BC
        LD E,128
        DJNZ footer_plane
        RET
picture_colors:
        LD A,(incoming_border)
        OUT (0xFE),A
        LD HL,0x5A80
        LD B,64
        LD A,0x47
        CALL fill
        LD A,(incoming_accent)
        LD B,64
        JP fill

menu_visible: DEFB 0
pictures_enabled: DEFB 1
input_blocked: DEFB 0
current_picture: DEFB 0
next_picture: DEFB 1
prepared: DEFB 0
incoming_border: DEFB 6
incoming_accent: DEFB 70
transition_step: DEFB 0
dissolve_cursor: DEFW 0
reveal_cursor: DEFW 0
tile_kind: DEFB 0
tile_row: DEFB 0
tile_attribute: DEFW 0
tile_destination: DEFW 0
tile_source: DEFW 0
petal_bits: DEFB 0,0,8,28,56,16,0,0
checkbox_x: DEFB 0,0,0,0,0,0,0,0
