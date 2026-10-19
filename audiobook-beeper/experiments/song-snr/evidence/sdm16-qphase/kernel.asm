; Exact q-successor component for a previously selected valid model-B word.
; Entry IX=unsigned biased IMA predictor, HL=C(word) modulo65536.
; E=old qcode0..15,D16; BC,IX,IY,SP,alternate registers and AF' are live.
; Return A=new qcode. Only A/F change in CORE36. No stack or paging operation.
; The admitted-cell certificate bounds the true subtraction within signed16
; and proves qcode already0..15. This routine must not be used with an arbitrary
; unrelated word or an unvalidated model; otherwise clipping/sign rules differ.
 ORG 0x8000
core36:
 LD A,IXL
 SUB L
 LD A,IXH
 SBC A,H
 SRA A
 ADD A,E
core36_complete: NOP
; Original raw seed=2*qcode+recent can be consumed after word selection.
rawseed44:
 SRL E
 LD A,IXL
 SUB L
 LD A,IXH
 SBC A,H
 SRA A
 ADD A,E
rawseed44_complete: NOP
; Current selector prototype's root-page byte is40h+2*rawseed.
; Extract its qcode without changing BC,D,IX,alternates or AF'. E is consumed.
rootpage59:
 LD A,E
 RRCA
 RRCA
 AND 15
 LD E,A
 LD A,IXL
 SUB L
 LD A,IXH
 SBC A,H
 SRA A
 ADD A,E
rootpage59_complete: NOP
; Batch driver for exhaustive real-cell execution. Six-byte fixture records
; contain C16,u16,qseed8,D16. These POPs/OUT/loop instructions are harness work,
; not part of the36-T component or a claimed integrated player schedule.
batch:
 LD SP,0xC000
 LD IY,2048
batch_loop:
 POP HL
 POP IX
 POP DE
 LD A,IXL
 SUB L
 LD A,IXH
 SBC A,H
 SRA A
 ADD A,E
 OUT (0xFD),A
 DEC IY
 LD A,IYH
 OR IYL
 JP NZ,batch_loop
batch_complete: NOP
