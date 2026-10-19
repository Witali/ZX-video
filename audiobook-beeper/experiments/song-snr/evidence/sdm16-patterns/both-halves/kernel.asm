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
 JP first_suffix_0
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
 JP first_suffix_1
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
 JP first_suffix_2
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
 JP first_suffix_4
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
 JP first_suffix_8
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
 JP first_suffix_9
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
 JP first_suffix_10
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
 JP first_suffix_0
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
 JP first_suffix_1
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
 JP first_suffix_2
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
 JP first_suffix_4
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
 JP first_suffix_5
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
 JP first_suffix_0
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
 JP first_suffix_1
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
 JP first_suffix_2
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
 JP first_suffix_4
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
 JP first_suffix_5
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
 JP first_suffix_6
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
 JP first_suffix_8
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
 JP first_suffix_9
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
 JP first_suffix_10
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
 JP first_suffix_11
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
 JP first_suffix_12
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
 JP first_suffix_13
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
 JP first_suffix_2
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
 JP first_suffix_3
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
 JP first_suffix_4
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
 JP first_suffix_5
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
 JP first_suffix_6
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
 JP first_suffix_0
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
 JP first_suffix_1
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
 JP first_suffix_2
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
 JP first_suffix_4
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
 JP first_suffix_8
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
 JP first_suffix_9
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
 JP first_suffix_10
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
 JP first_suffix_12
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
 JP first_suffix_13
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
 JP first_suffix_0
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
 JP first_suffix_1
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
 JP first_suffix_2
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
 JP first_suffix_3
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
 JP first_suffix_4
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
 JP first_suffix_5
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
 JP first_suffix_6
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
 JP first_suffix_7
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
 JP first_suffix_9
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
 JP first_suffix_10
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
 JP first_suffix_11
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
 JP first_suffix_13
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
 JP first_suffix_14
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
 JP first_suffix_4
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
 JP first_suffix_5
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
 JP first_suffix_6
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
 JP first_suffix_9
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
 JP first_suffix_10
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
 JP first_suffix_11
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
 JP first_suffix_12
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
 JP first_suffix_13
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
 JP first_suffix_14
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
 JP first_suffix_15
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
 JP first_suffix_3
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
 JP first_suffix_5
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
 JP first_suffix_6
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
 JP first_suffix_7
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
 JP first_suffix_11
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
 JP first_suffix_13
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
 JP first_suffix_14
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
 JP first_suffix_15
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
 JP first_suffix_0
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
 JP first_suffix_1
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
 JP first_suffix_2
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
 JP first_suffix_4
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
 JP first_suffix_8
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
 JP first_suffix_9
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
 JP first_suffix_10
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
 JP first_suffix_12
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
 JP first_suffix_0
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
 JP first_suffix_1
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
 JP first_suffix_2
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
 JP first_suffix_3
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
 JP first_suffix_4
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
 JP first_suffix_5
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
 JP first_suffix_6
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
 JP first_suffix_9
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
 JP first_suffix_10
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
 JP first_suffix_11
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
 JP first_suffix_1
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
 JP first_suffix_2
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
 JP first_suffix_4
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
 JP first_suffix_5
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
 JP first_suffix_6
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
 JP first_suffix_8
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
 JP first_suffix_9
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
 JP first_suffix_10
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
 JP first_suffix_11
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
 JP first_suffix_12
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
 JP first_suffix_13
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
 JP first_suffix_14
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
 JP first_suffix_15
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
 JP first_suffix_2
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
 JP first_suffix_3
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
 JP first_suffix_5
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
 JP first_suffix_6
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
 JP first_suffix_7
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
 JP first_suffix_11
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
 JP first_suffix_13
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
 JP first_suffix_14
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
 JP first_suffix_15
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
 JP first_suffix_9
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
 JP first_suffix_10
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
 JP first_suffix_11
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
 JP first_suffix_12
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
 JP first_suffix_13
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
 JP first_suffix_2
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
 JP first_suffix_3
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
 JP first_suffix_4
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
 JP first_suffix_5
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
 JP first_suffix_6
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
 JP first_suffix_7
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
 JP first_suffix_9
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
 JP first_suffix_10
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
 JP first_suffix_11
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
 JP first_suffix_13
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
 JP first_suffix_14
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
 JP first_suffix_15
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
 JP first_suffix_10
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
 JP first_suffix_11
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
 JP first_suffix_13
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
 JP first_suffix_14
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
 JP first_suffix_15
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
 JP first_suffix_5
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
 JP first_suffix_6
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
 JP first_suffix_7
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
 JP first_suffix_11
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
 JP first_suffix_13
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
 JP first_suffix_14
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
 JP first_suffix_15
first_suffix_0:
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
first_suffix_1:
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
first_suffix_2:
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
first_suffix_3:
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
first_dispatch_3:
 JP (IY)
 DEFB 0
first_suffix_4:
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
first_suffix_5:
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
first_dispatch_5:
 JP (IY)
 DEFB 0
first_suffix_6:
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
first_dispatch_6:
 JP (IY)
 DEFB 0
first_suffix_7:
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
first_dispatch_7:
 JP (IY)
 DEFB 0
first_suffix_8:
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
first_suffix_9:
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
first_suffix_10:
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
first_suffix_11:
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
first_dispatch_11:
 JP (IY)
 DEFB 0
first_suffix_12:
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
first_dispatch_12:
 JP (IY)
 DEFB 0
first_suffix_13:
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
first_dispatch_13:
 JP (IY)
 DEFB 0
first_suffix_14:
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
first_dispatch_14:
 JP (IY)
 DEFB 0
first_suffix_15:
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
first_dispatch_15:
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
 JP C,high_transfer_0
 JP low_suffix_0
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
 JP C,high_transfer_1
 JP low_suffix_1
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_4
 JP low_suffix_4
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_8
 JP low_suffix_8
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_12
 JP low_suffix_12
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
 JP C,high_transfer_0
 JP low_suffix_0
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
 JP C,high_transfer_1
 JP low_suffix_1
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_4
 JP low_suffix_4
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_0
 JP low_suffix_0
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
 JP C,high_transfer_1
 JP low_suffix_1
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_4
 JP low_suffix_4
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_12
 JP low_suffix_12
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_3
 JP low_suffix_3
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_11
 JP low_suffix_11
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_0
 JP low_suffix_0
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
 JP C,high_transfer_1
 JP low_suffix_1
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_4
 JP low_suffix_4
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_8
 JP low_suffix_8
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_1
 JP low_suffix_1
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_7
 JP low_suffix_7
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_11
 JP low_suffix_11
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_14
 JP low_suffix_14
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
 JP C,high_transfer_11
 JP low_suffix_11
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_14
 JP low_suffix_14
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
 JP C,high_transfer_15
 JP low_suffix_15
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_7
 JP low_suffix_7
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
 JP C,high_transfer_11
 JP low_suffix_11
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_14
 JP low_suffix_14
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
 JP C,high_transfer_15
 JP low_suffix_15
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
 JP C,high_transfer_0
 JP low_suffix_0
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
 JP C,high_transfer_1
 JP low_suffix_1
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_4
 JP low_suffix_4
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
 JP C,high_transfer_8
 JP low_suffix_8
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_0
 JP low_suffix_0
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
 JP C,high_transfer_1
 JP low_suffix_1
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_4
 JP low_suffix_4
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
 JP C,high_transfer_1
 JP low_suffix_1
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_4
 JP low_suffix_4
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_8
 JP low_suffix_8
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_14
 JP low_suffix_14
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_7
 JP low_suffix_7
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_11
 JP low_suffix_11
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_14
 JP low_suffix_14
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
 JP C,high_transfer_15
 JP low_suffix_15
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_4
 JP low_suffix_4
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_12
 JP low_suffix_12
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_2
 JP low_suffix_2
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
 JP C,high_transfer_3
 JP low_suffix_3
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_11
 JP low_suffix_11
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_14
 JP low_suffix_14
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
 JP C,high_transfer_15
 JP low_suffix_15
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_9
 JP low_suffix_9
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_11
 JP low_suffix_11
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_14
 JP low_suffix_14
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
 JP C,high_transfer_15
 JP low_suffix_15
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
 JP C,high_transfer_3
 JP low_suffix_3
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
 JP C,high_transfer_5
 JP low_suffix_5
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
 JP C,high_transfer_6
 JP low_suffix_6
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
 JP C,high_transfer_7
 JP low_suffix_7
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
 JP C,high_transfer_10
 JP low_suffix_10
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
 JP C,high_transfer_11
 JP low_suffix_11
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
 JP C,high_transfer_13
 JP low_suffix_13
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
 JP C,high_transfer_14
 JP low_suffix_14
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
 JP C,high_transfer_15
 JP low_suffix_15
high_transfer_0: JP high_suffix_0
low_suffix_0:
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
high_transfer_1: JP high_suffix_1
low_suffix_1:
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
high_transfer_2: JP high_suffix_2
low_suffix_2:
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
high_transfer_3: JP high_suffix_3
low_suffix_3:
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
high_transfer_4: JP high_suffix_4
low_suffix_4:
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
high_transfer_5: JP high_suffix_5
low_suffix_5:
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
high_transfer_6: JP high_suffix_6
low_suffix_6:
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
high_transfer_7: JP high_suffix_7
low_suffix_7:
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
high_transfer_8: JP high_suffix_8
low_suffix_8:
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
high_transfer_9: JP high_suffix_9
low_suffix_9:
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
high_transfer_10: JP high_suffix_10
low_suffix_10:
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
high_transfer_11: JP high_suffix_11
low_suffix_11:
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
high_transfer_12: JP high_suffix_12
low_suffix_12:
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
high_transfer_13: JP high_suffix_13
low_suffix_13:
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
high_transfer_14: JP high_suffix_14
low_suffix_14:
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
high_transfer_15: JP high_suffix_15
low_suffix_15:
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
