; Exact area-error inner pulse for h=30; product supplied externally.
; A:HL is signed24-bit q. C:DE is signed24-bit h*(U-32768).
; q stayswithin +/-74*65536; trueintermediate fits25 signed bits. The ADC
; overflow flag disambiguates the sign when its24-bit representation wraps.
; BC high is scratch/restored q high; IX/IY/alternate state/SP are unchanged.
; All four sign/overflow paths cost78 T and emit only EAR0/16.
 ORG 0x8000
start:
 ADD HL,DE
 ADC A,C
 JP PE,overflow
 JP M,normal_negative
 SUB 15
 LD B,A
 LD A,16
 JP emit
normal_negative:
 ADD A,15
 LD B,A
 LD A,0
 JP emit
overflow:
 JP P,overflow_negative
 SUB 15
 LD B,A
 LD A,16
 JP emit
overflow_negative:
 ADD A,15
 LD B,A
 LD A,0
 JP emit
emit:
 OUT (254),A
 LD A,B
complete:
 NOP
