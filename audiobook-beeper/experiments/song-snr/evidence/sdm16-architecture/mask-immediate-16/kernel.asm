; Standalone counted precision feasibility kernel, not a release player.
; Unclipped IMA predictor IX is copied to mainDE after each table decode.
; mainHL is a16-bit modulo accumulator, mainC16 is preserved by EXX.
; ADD carry becomes only EAR bit4; MIC and border stay0. AF is scratch.
; DEC/INC source paging, IRQ, UI and real disk delays are not implemented.
 ORG 0x8000
low_0:
EXX
 LD A,(DE)
 AND 15
 RLCA
 RLCA
 OR L
 LD L,A
 LD SP,HL
 POP BC
 POP HL
 ADD IX,BC
 EXX
 LD D,IXH
 LD E,IXL
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
low_complete_0:
EXX
 LD A,(DE)
 AND 240
 RRCA
 RRCA
 INC DE
 OR L
 LD L,A
 LD SP,HL
 POP BC
 POP HL
 ADD IX,BC
 EXX
 LD D,IXH
 LD E,IXL
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 ADD HL,DE
 SBC A,A
 AND 16
 OUT (254),A
 JP complete
complete:
 NOP
