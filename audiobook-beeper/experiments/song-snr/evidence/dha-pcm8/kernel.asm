; Resident unsignedPCM8, first-order accumulator, eight uniform56-T holds.
; MainHL=continuous modulo65536 accumulator, DE=PCM8<<8 (E remains zero),
; C=16 EAR mask. MainB/IX/IY/SP/I and alternateBC/HL are preserved.
; AlternateDE points to the NEXT source byte; current byte is already in D.
; AF' holds the prefetched byte only from gap1 to gap8; mainA/F are scratch.
; OUT(FE),A emits EAR0/16, with MIC/border zero. No RAM writes/CALL/PUSH.
; IRQs must be disabled. This bounded kernel has no EOF or bank handoff.
; Enter packet after priming D. All eight output holds are exactly56 T;
; source changes only after output8, for an exact448-T PCM sample period.
 ORG 0x8000
packet:
pulse_0:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
gap_0:
; Gap1: prefetch next target in AF',26 T including7-T dead load.
 EXX
 LD A,(DE)
 EX AF,AF'
 EXX
 LD A,0
pulse_1:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
gap_1:
;26 T free scheduling space; R-dependent flags/data are dead.
 LD A,R
 LD A,R
 NOP
 NOP
pulse_2:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
gap_2:
;26 T free scheduling space; R-dependent flags/data are dead.
 LD A,R
 LD A,R
 NOP
 NOP
pulse_3:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
gap_3:
;26 T free scheduling space; R-dependent flags/data are dead.
 LD A,R
 LD A,R
 NOP
 NOP
pulse_4:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
gap_4:
;26 T free scheduling space; R-dependent flags/data are dead.
 LD A,R
 LD A,R
 NOP
 NOP
pulse_5:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
gap_5:
;26 T free scheduling space; R-dependent flags/data are dead.
 LD A,R
 LD A,R
 NOP
 NOP
pulse_6:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
gap_6:
; Gap7: source advance,14 useful T plus12 T padding.
 EXX
 INC DE
 EXX
 NOP
 NOP
 NOP
pulse_7:
 ADD HL,DE
 SBC A,A
 AND C
 OUT (254),A
gap_7:
; Gap8: latch prefetched next target only after current output8.
; The10-T loop jump is included in the26-T gap, not added to the448-T clock.
 EX AF,AF'
 LD D,A
 NOP
 NOP
 JP packet
kernel_end:
 NOP
