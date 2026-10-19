; Fractional q-input correction only; this is not an integrated modulator.
; IX unsigned16 predictor, fraction is a9-bit accumulator in two fixed bytes.
; Add low10 predictor bits to fraction; return A=carry0/1/2 in q*8 units.
; Preserve IX/IY/BC/DE, alternate registers and AF'. Main HL/A/F are scratch.
; Processing high partial first preserves the carry from the low-byte add.
 ORG 0x8000
fraction: EQU 0xAF00
start:
 LD HL,fraction+1
 LD A,IXH
 AND 3
 ADD A,(HL)
 LD (HL),A
 DEC HL
 LD A,IXL
 ADD A,(HL)
 LD (HL),A
 INC HL
 LD A,(HL)
 ADC A,0
 RRA
 LD (HL),0
 RL (HL)
fraction_complete:
 ; Three256-aligned maps translate old compact offset to an injected offset.
 ADD A,0xA0
 LD H,A
 LD L,E
 LD E,(HL)
complete:
 NOP
