; Standalone full16-bit first-order modulator with seven uniform64-T holds.
; A sample lasts448 T; IMA stays compressed and is decoded one sample ahead.
; MainHL=modulo16 accumulator, DE=current full16-bit biased sample, C=16.
; IX=next predictor, alternateHL=IMA row, alternateDE=source cursor,
; alternateBC=delta. AF' holds a prepared nibble only between gaps1 and2.
; MainB/IY are free; OUT(FE),A emits only EAR0/16, with MIC/border0.
; SP is dead after gap3 POPs, and reset before every future POP. No CALL/PUSH.
; Enter high_packet after priming the first LOW nibble; source cursor then
; points at that same byte. Page/bank handling and EOF are not implemented.
; IRQs must remain disabled, including while SP is a dead scratch pointer.
 ORG 0x8000
low_packet:
low_pulse_0:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
low_gap_0:
; Gap1,34 T: fetch/prepare the next code, then preserve it in AF'.
 EXX
 LD A,(DE)
 AND 15
 RLCA
 RLCA
 EX AF,AF'
 EXX
low_pulse_1:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
low_gap_1:
; Gap2,26 useful+8 pad: restore code and select its four-byte IMA row.
 EXX
 EX AF,AF'
 OR L
 LD L,A
 LD SP,HL
 EXX
 NOP
 NOP
low_pulse_2:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
low_gap_2:
; Gap3,28 useful+6 pad: load delta/next row, then discard lookup SP.
 EXX
 POP BC
 POP HL
 EXX
 LD SP,HL
low_pulse_3:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
low_gap_3:
; Gap4,23 useful+11 pad: update next predictor, preserving current DE.
 EXX
 ADD IX,BC
 EXX
 LD A,0
 NOP
low_pulse_4:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
low_gap_4:
; Gap5,34 pad: source still points at its unconsumed high nibble.
 LD A,R
 LD A,R
 NOP
 NOP
 NOP
 NOP
low_pulse_5:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
low_gap_5:
; Gap6 is34 T available for future resident-descriptor/paging work.
 LD A,R
 LD A,R
 NOP
 NOP
 NOP
 NOP
low_pulse_6:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
low_gap_6:
; Gap7: current output is finished; latch next predictor into DE.
 LD D,IXH
 LD E,IXL
 LD A,R
 LD A,R
high_packet:
high_pulse_0:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
high_gap_0:
; Gap1,34 T: fetch/prepare the next code, then preserve it in AF'.
 EXX
 LD A,(DE)
 AND 240
 RRCA
 RRCA
 EX AF,AF'
 EXX
high_pulse_1:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
high_gap_1:
; Gap2,26 useful+8 pad: restore code and select its four-byte IMA row.
 EXX
 EX AF,AF'
 OR L
 LD L,A
 LD SP,HL
 EXX
 NOP
 NOP
high_pulse_2:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
high_gap_2:
; Gap3,28 useful+6 pad: load delta/next row, then discard lookup SP.
 EXX
 POP BC
 POP HL
 EXX
 LD SP,HL
high_pulse_3:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
high_gap_3:
; Gap4,23 useful+11 pad: update next predictor, preserving current DE.
 EXX
 ADD IX,BC
 EXX
 LD A,0
 NOP
high_pulse_4:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
high_gap_4:
; Gap5,14 useful+20 pad: both nibbles are consumed; advance source.
 EXX
 INC DE
 EXX
 NOP
 NOP
 NOP
 NOP
 NOP
high_pulse_5:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
high_gap_5:
; Gap6 is34 T available for future resident-descriptor/paging work.
 LD A,R
 LD A,R
 NOP
 NOP
 NOP
 NOP
high_pulse_6:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
high_gap_6:
; Gap7: current output is finished; latch next predictor into DE.
 LD D,IXH
 LD E,IXL
 NOP
 NOP
 JP low_packet
kernel_end:
 NOP
