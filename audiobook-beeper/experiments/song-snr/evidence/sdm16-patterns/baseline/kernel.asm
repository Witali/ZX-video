; Standalone literal-pattern compression proof. No decoder/table or source change.
; Main BC=00FE/10FE,D=16,E=feedback*6,HL dispatch,IX predictor,IY SECOND.
; Alternate HL=IMA row,BC delta,DE compressed cursor; AF' retains phase/code.
; SP is the live table pointer; no CALL/RET or ordinary stack use is permitted.
; All extra transfers below are fixed JP10, independent of pattern and phase.
 ORG 0x8000
pcm_high: EQU 0x5E00
page_tail_0:
 INC D
 JP Z,bank_handoff_0
 EXX
 DB 0xED,0x71
 JP (HL)
bank_handoff_0:
 EX AF,AF'
 EXX
 LD B,0
 EXX
 JP bank_jump
page_tail_1:
 INC D
 JP Z,bank_handoff_1
 EXX
 OUT (C),D
 JP (HL)
bank_handoff_1:
 EX AF,AF'
 EXX
 LD B,16
 EXX
 JP bank_jump
bank_jump: JP stream_bank_tail
stream_bank_tail:
 LD (stream_tail_hl),HL
 LD HL,(stream_next_record)
 LD A,(HL)
 OR A
 JP Z,exhausted
 LD (stream_paging),A
 INC HL
 LD D,(HL)
 LD E,0
 INC HL
 LD A,(HL)
 INC HL
 LD (stream_next_record),HL
 LD HL,(stream_tail_hl)
stream_high_switch: JP stream_high_done
 LD BC,0x1FFD
 OUT (C),A
stream_high_done:
 LD BC,0x7FFD
 LD A,(stream_paging)
stream_page_event: OUT (C),A
 EXX
 SCF
 EX AF,AF'
 OUT (C),B
 JP (HL)
exhausted: HALT
hardware_delay: NOP
 NOP
 NOP
 NOP
 JP (IY)
stream_tail_hl: DEFW 0
stream_next_record: DEFW descriptor
stream_paging: DEFB 0
descriptor: DEFB 25,192,0,0
 DS 0x8340-$
first_begin:
; FIRST prefixes decode the next IMA nibble. A shared suffix retains the
; exact same predictor lookup work; its extra JP preserves all registers/F.
first_0:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_0:
 JP (IY)
 DEFB 0
first_1:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_1:
 JP (IY)
 DEFB 0
first_2:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_2:
 JP (IY)
 DEFB 0
first_4:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_4:
 JP (IY)
 DEFB 0
first_8:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_8:
 JP (IY)
 DEFB 0
first_9:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_9:
 JP (IY)
 DEFB 0
first_10:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_10:
 JP (IY)
 DEFB 0
first_16:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_16:
 JP (IY)
 DEFB 0
first_17:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_17:
 JP (IY)
 DEFB 0
first_18:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_18:
 JP (IY)
 DEFB 0
first_20:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_20:
 JP (IY)
 DEFB 0
first_21:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_21:
 JP (IY)
 DEFB 0
first_32:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_32:
 JP (IY)
 DEFB 0
first_33:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_33:
 JP (IY)
 DEFB 0
first_34:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_34:
 JP (IY)
 DEFB 0
first_36:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_36:
 JP (IY)
 DEFB 0
first_37:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_37:
 JP (IY)
 DEFB 0
first_38:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_38:
 JP (IY)
 DEFB 0
first_40:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_40:
 JP (IY)
 DEFB 0
first_41:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_41:
 JP (IY)
 DEFB 0
first_42:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_42:
 JP (IY)
 DEFB 0
first_43:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_43:
 JP (IY)
 DEFB 0
first_44:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_44:
 JP (IY)
 DEFB 0
first_45:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_45:
 JP (IY)
 DEFB 0
first_50:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_50:
 JP (IY)
 DEFB 0
first_51:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_51:
 JP (IY)
 DEFB 0
first_52:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_52:
 JP (IY)
 DEFB 0
first_53:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_53:
 JP (IY)
 DEFB 0
first_54:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_54:
 JP (IY)
 DEFB 0
first_64:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_64:
 JP (IY)
 DEFB 0
first_65:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_65:
 JP (IY)
 DEFB 0
first_66:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_66:
 JP (IY)
 DEFB 0
first_68:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_68:
 JP (IY)
 DEFB 0
first_72:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_72:
 JP (IY)
 DEFB 0
first_73:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_73:
 JP (IY)
 DEFB 0
first_74:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_74:
 JP (IY)
 DEFB 0
first_76:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_76:
 JP (IY)
 DEFB 0
first_77:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_77:
 JP (IY)
 DEFB 0
first_80:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_80:
 JP (IY)
 DEFB 0
first_81:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_81:
 JP (IY)
 DEFB 0
first_82:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_82:
 JP (IY)
 DEFB 0
first_83:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_83:
 JP (IY)
 DEFB 0
first_84:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_84:
 JP (IY)
 DEFB 0
first_85:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_85:
 JP (IY)
 DEFB 0
first_86:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_86:
 JP (IY)
 DEFB 0
first_87:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_87:
 JP (IY)
 DEFB 0
first_89:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_89:
 JP (IY)
 DEFB 0
first_90:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_90:
 JP (IY)
 DEFB 0
first_91:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_91:
 JP (IY)
 DEFB 0
first_93:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_93:
 JP (IY)
 DEFB 0
first_94:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_94:
 JP (IY)
 DEFB 0
first_100:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_100:
 JP (IY)
 DEFB 0
first_101:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_101:
 JP (IY)
 DEFB 0
first_102:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_102:
 JP (IY)
 DEFB 0
first_105:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_105:
 JP (IY)
 DEFB 0
first_106:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_106:
 JP (IY)
 DEFB 0
first_107:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_107:
 JP (IY)
 DEFB 0
first_108:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_108:
 JP (IY)
 DEFB 0
first_109:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_109:
 JP (IY)
 DEFB 0
first_110:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_110:
 JP (IY)
 DEFB 0
first_111:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_111:
 JP (IY)
 DEFB 0
first_115:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_115:
 JP (IY)
 DEFB 0
first_117:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_117:
 JP (IY)
 DEFB 0
first_118:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_118:
 JP (IY)
 DEFB 0
first_119:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_119:
 JP (IY)
 DEFB 0
first_123:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_123:
 JP (IY)
 DEFB 0
first_125:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_125:
 JP (IY)
 DEFB 0
first_126:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_126:
 JP (IY)
 DEFB 0
first_127:
 DB 0xED,0x71
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_127:
 JP (IY)
 DEFB 0
first_128:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_128:
 JP (IY)
 DEFB 0
first_129:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_129:
 JP (IY)
 DEFB 0
first_130:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_130:
 JP (IY)
 DEFB 0
first_132:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_132:
 JP (IY)
 DEFB 0
first_136:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_136:
 JP (IY)
 DEFB 0
first_137:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_137:
 JP (IY)
 DEFB 0
first_138:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_138:
 JP (IY)
 DEFB 0
first_140:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_140:
 JP (IY)
 DEFB 0
first_144:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_144:
 JP (IY)
 DEFB 0
first_145:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_145:
 JP (IY)
 DEFB 0
first_146:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_146:
 JP (IY)
 DEFB 0
first_147:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_147:
 JP (IY)
 DEFB 0
first_148:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_148:
 JP (IY)
 DEFB 0
first_149:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_149:
 JP (IY)
 DEFB 0
first_150:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_150:
 JP (IY)
 DEFB 0
first_153:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_153:
 JP (IY)
 DEFB 0
first_154:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_154:
 JP (IY)
 DEFB 0
first_155:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_155:
 JP (IY)
 DEFB 0
first_161:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_161:
 JP (IY)
 DEFB 0
first_162:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_162:
 JP (IY)
 DEFB 0
first_164:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_164:
 JP (IY)
 DEFB 0
first_165:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_165:
 JP (IY)
 DEFB 0
first_166:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_166:
 JP (IY)
 DEFB 0
first_168:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_168:
 JP (IY)
 DEFB 0
first_169:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_169:
 JP (IY)
 DEFB 0
first_170:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_170:
 JP (IY)
 DEFB 0
first_171:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_171:
 JP (IY)
 DEFB 0
first_172:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_172:
 JP (IY)
 DEFB 0
first_173:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_173:
 JP (IY)
 DEFB 0
first_174:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_174:
 JP (IY)
 DEFB 0
first_175:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_175:
 JP (IY)
 DEFB 0
first_178:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_178:
 JP (IY)
 DEFB 0
first_179:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_179:
 JP (IY)
 DEFB 0
first_181:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_181:
 JP (IY)
 DEFB 0
first_182:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_182:
 JP (IY)
 DEFB 0
first_183:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_183:
 JP (IY)
 DEFB 0
first_187:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_187:
 JP (IY)
 DEFB 0
first_189:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_189:
 JP (IY)
 DEFB 0
first_190:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_190:
 JP (IY)
 DEFB 0
first_191:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,0
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_191:
 JP (IY)
 DEFB 0
first_201:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_201:
 JP (IY)
 DEFB 0
first_202:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_202:
 JP (IY)
 DEFB 0
first_203:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_203:
 JP (IY)
 DEFB 0
first_204:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_204:
 JP (IY)
 DEFB 0
first_205:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_205:
 JP (IY)
 DEFB 0
first_210:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_210:
 JP (IY)
 DEFB 0
first_211:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_211:
 JP (IY)
 DEFB 0
first_212:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_212:
 JP (IY)
 DEFB 0
first_213:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_213:
 JP (IY)
 DEFB 0
first_214:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_214:
 JP (IY)
 DEFB 0
first_215:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_215:
 JP (IY)
 DEFB 0
first_217:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_217:
 JP (IY)
 DEFB 0
first_218:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_218:
 JP (IY)
 DEFB 0
first_219:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_219:
 JP (IY)
 DEFB 0
first_221:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_221:
 JP (IY)
 DEFB 0
first_222:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_222:
 JP (IY)
 DEFB 0
first_223:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,0
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_223:
 JP (IY)
 DEFB 0
first_234:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_234:
 JP (IY)
 DEFB 0
first_235:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_235:
 JP (IY)
 DEFB 0
first_237:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_237:
 JP (IY)
 DEFB 0
first_238:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_238:
 JP (IY)
 DEFB 0
first_239:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,0
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_239:
 JP (IY)
 DEFB 0
first_245:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_245:
 JP (IY)
 DEFB 0
first_246:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_246:
 JP (IY)
 DEFB 0
first_247:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 DB 0xED,0x71
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_247:
 JP (IY)
 DEFB 0
first_251:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 DB 0xED,0x71
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_251:
 JP (IY)
 DEFB 0
first_253:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 DB 0xED,0x71
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_253:
 JP (IY)
 DEFB 0
first_254:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 DB 0xED,0x71
first_dispatch_254:
 JP (IY)
 DEFB 0
first_255:
 OUT (C),D
 EXX
 OR L
 LD L,A
 LD SP,HL
 LD A,16
 OUT (0xFE),A
 POP BC
 LD A,16
 OUT (0xFE),A
 POP HL
 LD A,16
 OUT (0xFE),A
 ADD IX,BC
 EXX
 OUT (C),D
 LD A,IXH
 LD L,A
 OUT (C),D
 LD H,pcm_high >> 8
 LD H,(HL)
 OUT (C),D
 LD L,E
 LD SP,HL
 OUT (C),D
first_dispatch_255:
 JP (IY)
 DEFB 0
first_end:
second_begin:
; SECOND's existing constant-time phase JP can directly reach one of sixteen
; shared high suffixes. This redirection costs no additional instruction.
second_0:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_0
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_0:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_0+64-$
second_1:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_1
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_1:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_1+64-$
second_2:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_2
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_2:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_2+64-$
second_4:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_4
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_4:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_4+64-$
second_5:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_5
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_5:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_5+64-$
second_8:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_8
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_8:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_8+64-$
second_9:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_9
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_9:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_9+64-$
second_10:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_10
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_10:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_10+64-$
second_12:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_12
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_12:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_12+64-$
second_16:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_16
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_16:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_16+64-$
second_17:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_17
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_17:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_17+64-$
second_18:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_18
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_18:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_18+64-$
second_20:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_20
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_20:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_20+64-$
second_21:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_21
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_21:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_21+64-$
second_22:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_22
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_22:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_22+64-$
second_25:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_25
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_25:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_25+64-$
second_32:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_32
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_32:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_32+64-$
second_33:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_33
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_33:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_33+64-$
second_34:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_34
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_34:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_34+64-$
second_36:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_36
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_36:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_36+64-$
second_37:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_37
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_37:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_37+64-$
second_38:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_38
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_38:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_38+64-$
second_41:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_41
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_41:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_41+64-$
second_42:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_42
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_42:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_42+64-$
second_44:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_44
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_44:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_44+64-$
second_45:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_45
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_45:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_45+64-$
second_50:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_50
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_50:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_50+64-$
second_51:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_51
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_51:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_51+64-$
second_53:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_53
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_53:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_53+64-$
second_54:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_54
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_54:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_54+64-$
second_57:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_57
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_57:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_57+64-$
second_58:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_58
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_58:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_58+64-$
second_59:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_59
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_59:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_59+64-$
second_61:
 DB 0xED,0x71
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_61
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_61:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_61+64-$
second_64:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_64
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_64:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_64+64-$
second_65:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_65
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_65:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_65+64-$
second_66:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_66
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_66:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_66+64-$
second_68:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_68
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_68:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_68+64-$
second_69:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_69
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_69:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_69+64-$
second_72:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_72
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_72:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_72+64-$
second_73:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_73
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_73:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_73+64-$
second_74:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_74
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_74:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_74+64-$
second_77:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_77
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_77:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_77+64-$
second_81:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_81
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_81:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_81+64-$
second_85:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_85
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_85:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_85+64-$
second_86:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_86
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_86:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_86+64-$
second_87:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_87
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_87:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_87+64-$
second_89:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_89
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_89:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_89+64-$
second_90:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_90
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_90:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_90+64-$
second_91:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_91
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_91:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_91+64-$
second_93:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_93
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_93:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_93+64-$
second_94:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_94
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_94:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_94+64-$
second_107:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_107
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_107:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_107+64-$
second_109:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_109
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_109:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_109+64-$
second_110:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_110
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_110:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_110+64-$
second_111:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_111
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_111:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_111+64-$
second_118:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_118
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_118:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_118+64-$
second_119:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_119
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_119:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_119+64-$
second_123:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_123
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_123:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_123+64-$
second_125:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_125
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_125:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_125+64-$
second_126:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_126
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_126:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_126+64-$
second_127:
 DB 0xED,0x71
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_127
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_127:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_127+64-$
second_128:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_128
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_128:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_128+64-$
second_129:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_129
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_129:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_129+64-$
second_130:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_130
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_130:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_130+64-$
second_132:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_132
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_132:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_132+64-$
second_136:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_136
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_136:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_136+64-$
second_137:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_137
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_137:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_137+64-$
second_144:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_144
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_144:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_144+64-$
second_145:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_145
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_145:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_145+64-$
second_146:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_146
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_146:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_146+64-$
second_148:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_148
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_148:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_148+64-$
second_161:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_161
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_161:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_161+64-$
second_162:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_162
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_162:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_162+64-$
second_164:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_164
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_164:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_164+64-$
second_165:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_165
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_165:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_165+64-$
second_166:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_166
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_166:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_166+64-$
second_168:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_168
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_168:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_168+64-$
second_169:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_169
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_169:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_169+64-$
second_170:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_170
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_170:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_170+64-$
second_174:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_174
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_174:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_174+64-$
second_178:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_178
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_178:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_178+64-$
second_181:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_181
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_181:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_181+64-$
second_182:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_182
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_182:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_182+64-$
second_183:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_183
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_183:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_183+64-$
second_186:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_186
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_186:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_186+64-$
second_187:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_187
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_187:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_187+64-$
second_189:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_189
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_189:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_189+64-$
second_190:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_190
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_190:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_190+64-$
second_191:
 OUT (C),D
 POP HL
 DB 0xED,0x71
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_191
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_191:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_191+64-$
second_194:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_194
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_194:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_194+64-$
second_196:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_196
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_196:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_196+64-$
second_197:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_197
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_197:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_197+64-$
second_198:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_198
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_198:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_198+64-$
second_201:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_201
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_201:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_201+64-$
second_202:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_202
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_202:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_202+64-$
second_204:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_204
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_204:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_204+64-$
second_205:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_205
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_205:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_205+64-$
second_210:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_210
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_210:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_210+64-$
second_211:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_211
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_211:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_211+64-$
second_213:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_213
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_213:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_213+64-$
second_214:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_214
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_214:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_214+64-$
second_217:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_217
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_217:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_217+64-$
second_218:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_218
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_218:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_218+64-$
second_219:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_219
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_219:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_219+64-$
second_221:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_221
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_221:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_221+64-$
second_222:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_222
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_222:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_222+64-$
second_223:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 DB 0xED,0x71
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_223
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_223:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_223+64-$
second_230:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_230
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_230:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_230+64-$
second_233:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_233
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_233:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_233+64-$
second_234:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_234
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_234:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_234+64-$
second_235:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_235
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_235:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_235+64-$
second_237:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_237
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_237:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_237+64-$
second_238:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_238
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_238:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_238+64-$
second_239:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 DB 0xED,0x71
 EX AF,AF'
 CCF
 JP C,high_239
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_239:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_239+64-$
second_243:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_243
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_243:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_243+64-$
second_245:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_245
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_245:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_245+64-$
second_246:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_246
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_246:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_246+64-$
second_247:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_247
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_247:
 DB 0xED,0x71
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_247+64-$
second_250:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_250
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_250:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_250+64-$
second_251:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_251
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_251:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 DB 0xED,0x71
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_251+64-$
second_253:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_253
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 DB 0xED,0x71
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_253:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 DB 0xED,0x71
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_253+64-$
second_254:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_254
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 DB 0xED,0x71
 JP (HL)
high_254:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_0
 EXX
 DB 0xED,0x71
 JP (HL)
 DS second_254+64-$
second_255:
 OUT (C),D
 POP HL
 OUT (C),D
 POP IY
 OUT (C),D
 POP DE
 OUT (C),D
 EX AF,AF'
 CCF
 JP C,high_255
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 15
 RLCA
 RLCA
 OUT (C),D
 JP $+3
 NOP
 NOP
 NOP
 OUT (C),D
 JP (HL)
high_255:
 OUT (C),D
 EX AF,AF'
 EXX
 LD A,(DE)
 EXX
 OUT (C),D
 AND 240
 RRCA
 RRCA
 OUT (C),D
 EXX
 INC E
 JP Z,page_tail_1
 EXX
 OUT (C),D
 JP (HL)
 DS second_255+64-$
second_end:
complete: NOP
