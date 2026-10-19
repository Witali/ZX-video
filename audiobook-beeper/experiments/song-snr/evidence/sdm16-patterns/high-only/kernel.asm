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
 JP C,high_suffix_0
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
 JP C,high_suffix_1
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
 JP C,high_suffix_2
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
 JP C,high_suffix_4
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
 JP C,high_suffix_5
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
 JP C,high_suffix_8
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
 JP C,high_suffix_9
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
 JP C,high_suffix_10
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
 JP C,high_suffix_12
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
 JP C,high_suffix_0
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
 JP C,high_suffix_1
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
 JP C,high_suffix_2
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
 JP C,high_suffix_4
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
 JP C,high_suffix_5
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
 JP C,high_suffix_6
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
 JP C,high_suffix_9
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
 JP C,high_suffix_0
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
 JP C,high_suffix_1
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
 JP C,high_suffix_2
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
 JP C,high_suffix_4
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
 JP C,high_suffix_5
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
 JP C,high_suffix_6
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
 JP C,high_suffix_9
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
 JP C,high_suffix_10
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
 JP C,high_suffix_12
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
 JP C,high_suffix_13
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
 JP C,high_suffix_2
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
 JP C,high_suffix_3
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
 JP C,high_suffix_5
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
 JP C,high_suffix_6
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
 JP C,high_suffix_9
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
 JP C,high_suffix_10
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
 JP C,high_suffix_11
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
 JP C,high_suffix_13
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
 JP C,high_suffix_0
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
 JP C,high_suffix_1
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
 JP C,high_suffix_2
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
 JP C,high_suffix_4
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
 JP C,high_suffix_5
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
 JP C,high_suffix_8
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
 JP C,high_suffix_9
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
 JP C,high_suffix_10
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
 JP C,high_suffix_13
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
 JP C,high_suffix_1
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
 JP C,high_suffix_5
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
 JP C,high_suffix_6
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
 JP C,high_suffix_7
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
 JP C,high_suffix_9
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
 JP C,high_suffix_10
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
 JP C,high_suffix_11
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
 JP C,high_suffix_13
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
 JP C,high_suffix_14
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
 JP C,high_suffix_11
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
 JP C,high_suffix_13
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
 JP C,high_suffix_14
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
 JP C,high_suffix_15
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
 JP C,high_suffix_6
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
 JP C,high_suffix_7
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
 JP C,high_suffix_11
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
 JP C,high_suffix_13
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
 JP C,high_suffix_14
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
 JP C,high_suffix_15
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
 JP C,high_suffix_0
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
 JP C,high_suffix_1
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
 JP C,high_suffix_2
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
 JP C,high_suffix_4
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
 JP C,high_suffix_8
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
 JP C,high_suffix_9
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
 JP C,high_suffix_0
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
 JP C,high_suffix_1
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
 JP C,high_suffix_2
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
 JP C,high_suffix_4
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
 JP C,high_suffix_1
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
 JP C,high_suffix_2
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
 JP C,high_suffix_4
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
 JP C,high_suffix_5
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
 JP C,high_suffix_6
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
 JP C,high_suffix_8
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
 JP C,high_suffix_9
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
 JP C,high_suffix_10
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
 JP C,high_suffix_14
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
 JP C,high_suffix_2
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
 JP C,high_suffix_5
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
 JP C,high_suffix_6
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
 JP C,high_suffix_7
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
 JP C,high_suffix_10
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
 JP C,high_suffix_11
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
 JP C,high_suffix_13
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
 JP C,high_suffix_14
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
 JP C,high_suffix_15
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
 JP C,high_suffix_2
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
 JP C,high_suffix_4
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
 JP C,high_suffix_5
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
 JP C,high_suffix_6
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
 JP C,high_suffix_9
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
 JP C,high_suffix_10
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
 JP C,high_suffix_12
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
 JP C,high_suffix_13
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
 JP C,high_suffix_2
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
 JP C,high_suffix_3
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
 JP C,high_suffix_5
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
 JP C,high_suffix_6
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
 JP C,high_suffix_9
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
 JP C,high_suffix_10
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
 JP C,high_suffix_11
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
 JP C,high_suffix_13
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
 JP C,high_suffix_14
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
 JP C,high_suffix_15
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
 JP C,high_suffix_6
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
 JP C,high_suffix_9
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
 JP C,high_suffix_10
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
 JP C,high_suffix_11
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
 JP C,high_suffix_13
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
 JP C,high_suffix_14
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
 JP C,high_suffix_15
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
 JP C,high_suffix_3
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
 JP C,high_suffix_5
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
 JP C,high_suffix_6
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
 JP C,high_suffix_7
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
 JP C,high_suffix_10
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
 JP C,high_suffix_11
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
 JP C,high_suffix_13
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
 JP C,high_suffix_14
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
 JP C,high_suffix_15
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
high_suffix_0:
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
high_suffix_1:
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
high_suffix_2:
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
high_suffix_3:
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
high_suffix_4:
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
high_suffix_5:
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
high_suffix_6:
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
high_suffix_7:
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
high_suffix_8:
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
high_suffix_9:
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
high_suffix_10:
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
high_suffix_11:
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
high_suffix_12:
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
high_suffix_13:
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
high_suffix_14:
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
high_suffix_15:
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
second_end:
complete: NOP
