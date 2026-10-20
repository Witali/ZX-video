; Isolated residentPCM8 component, bank0 -> bank1 once, no disk/EOF.
; Main BC=10FE, DE=one-ahead source cursor, HL=lookup/nextFIRST pointer.
; Main IY/IX and AF' remain free/preserved. SP is a lookup pointer, no calls.
; ALT HL=10FE constant: H is the alternate EAR-high byte, L restores port C.
; ALT BC starts7FFE and becomes7FFD at the one bank switch. ALT DE is scratch.
; Main A/F are scratch; bank detection clears C and keeps it through RET C.
; Each FIRST self-patches only its own final JP operand with the SECOND word.
; Each lookup record is FIRST pointer, specialized SECOND pointer (4 bytes).
; SECOND specializes the low8 output bits and next feedback offset.
; Source mapping changes one PCM sample early, after the final old byte has
; already been prefetched into lookup state. The next FIRST then increments
; BF:FF to C0:00 and reads the new bank; no old source byte is reread.
; All instruction counts assume uncontended Pentagon CPU/I/O. Physical ROM,
; cover, loader, general descriptor iteration and clone timing are unproved.
 ORG 0x8000
first_0:
first_0_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_0_pulse_1:
 DB 237,113
 LD (first_0_jump+1),HL
first_0_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_0_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_0_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_0_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_0_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_0_pulse_7:
 OUT (254),A
 INC SP
first_0_jump:
 JP 0
first_1:
first_1_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_1_pulse_1:
 DB 237,113
 LD (first_1_jump+1),HL
first_1_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_1_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_1_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_1_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_1_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_1_pulse_7:
 OUT (254),A
 INC SP
first_1_jump:
 JP 0
first_2:
first_2_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_2_pulse_1:
 DB 237,113
 LD (first_2_jump+1),HL
first_2_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_2_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_2_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_2_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_2_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_2_pulse_7:
 OUT (254),A
 INC SP
first_2_jump:
 JP 0
first_4:
first_4_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_4_pulse_1:
 DB 237,113
 LD (first_4_jump+1),HL
first_4_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_4_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_4_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_4_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_4_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_4_pulse_7:
 OUT (254),A
 INC SP
first_4_jump:
 JP 0
first_8:
first_8_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_8_pulse_1:
 DB 237,113
 LD (first_8_jump+1),HL
first_8_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_8_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_8_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_8_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_8_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_8_pulse_7:
 OUT (254),A
 INC SP
first_8_jump:
 JP 0
first_16:
first_16_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_16_pulse_1:
 DB 237,113
 LD (first_16_jump+1),HL
first_16_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_16_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_16_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_16_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_16_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_16_pulse_7:
 OUT (254),A
 INC SP
first_16_jump:
 JP 0
first_17:
first_17_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_17_pulse_1:
 DB 237,113
 LD (first_17_jump+1),HL
first_17_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_17_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_17_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_17_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_17_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_17_pulse_7:
 OUT (254),A
 INC SP
first_17_jump:
 JP 0
first_18:
first_18_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_18_pulse_1:
 DB 237,113
 LD (first_18_jump+1),HL
first_18_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_18_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_18_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_18_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_18_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_18_pulse_7:
 OUT (254),A
 INC SP
first_18_jump:
 JP 0
first_20:
first_20_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_20_pulse_1:
 DB 237,113
 LD (first_20_jump+1),HL
first_20_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_20_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_20_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_20_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_20_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_20_pulse_7:
 OUT (254),A
 INC SP
first_20_jump:
 JP 0
first_32:
first_32_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_32_pulse_1:
 DB 237,113
 LD (first_32_jump+1),HL
first_32_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_32_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_32_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_32_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_32_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_32_pulse_7:
 OUT (254),A
 INC SP
first_32_jump:
 JP 0
first_33:
first_33_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_33_pulse_1:
 DB 237,113
 LD (first_33_jump+1),HL
first_33_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_33_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_33_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_33_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_33_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_33_pulse_7:
 OUT (254),A
 INC SP
first_33_jump:
 JP 0
first_34:
first_34_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_34_pulse_1:
 DB 237,113
 LD (first_34_jump+1),HL
first_34_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_34_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_34_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_34_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_34_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_34_pulse_7:
 OUT (254),A
 INC SP
first_34_jump:
 JP 0
first_36:
first_36_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_36_pulse_1:
 DB 237,113
 LD (first_36_jump+1),HL
first_36_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_36_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_36_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_36_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_36_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_36_pulse_7:
 OUT (254),A
 INC SP
first_36_jump:
 JP 0
first_37:
first_37_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_37_pulse_1:
 DB 237,113
 LD (first_37_jump+1),HL
first_37_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_37_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_37_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_37_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_37_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_37_pulse_7:
 OUT (254),A
 INC SP
first_37_jump:
 JP 0
first_40:
first_40_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_40_pulse_1:
 DB 237,113
 LD (first_40_jump+1),HL
first_40_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_40_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_40_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_40_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_40_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_40_pulse_7:
 OUT (254),A
 INC SP
first_40_jump:
 JP 0
first_41:
first_41_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_41_pulse_1:
 DB 237,113
 LD (first_41_jump+1),HL
first_41_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_41_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_41_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_41_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_41_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_41_pulse_7:
 OUT (254),A
 INC SP
first_41_jump:
 JP 0
first_42:
first_42_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_42_pulse_1:
 DB 237,113
 LD (first_42_jump+1),HL
first_42_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_42_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_42_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_42_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_42_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_42_pulse_7:
 OUT (254),A
 INC SP
first_42_jump:
 JP 0
first_50:
first_50_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_50_pulse_1:
 DB 237,113
 LD (first_50_jump+1),HL
first_50_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_50_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_50_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_50_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_50_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_50_pulse_7:
 OUT (254),A
 INC SP
first_50_jump:
 JP 0
first_51:
first_51_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_51_pulse_1:
 DB 237,113
 LD (first_51_jump+1),HL
first_51_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_51_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_51_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_51_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_51_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_51_pulse_7:
 OUT (254),A
 INC SP
first_51_jump:
 JP 0
first_53:
first_53_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_53_pulse_1:
 DB 237,113
 LD (first_53_jump+1),HL
first_53_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_53_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_53_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_53_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_53_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_53_pulse_7:
 OUT (254),A
 INC SP
first_53_jump:
 JP 0
first_64:
first_64_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_64_pulse_1:
 OUT (C),B
 LD (first_64_jump+1),HL
first_64_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_64_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_64_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_64_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_64_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_64_pulse_7:
 OUT (254),A
 INC SP
first_64_jump:
 JP 0
first_65:
first_65_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_65_pulse_1:
 OUT (C),B
 LD (first_65_jump+1),HL
first_65_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_65_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_65_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_65_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_65_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_65_pulse_7:
 OUT (254),A
 INC SP
first_65_jump:
 JP 0
first_66:
first_66_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_66_pulse_1:
 OUT (C),B
 LD (first_66_jump+1),HL
first_66_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_66_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_66_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_66_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_66_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_66_pulse_7:
 OUT (254),A
 INC SP
first_66_jump:
 JP 0
first_68:
first_68_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_68_pulse_1:
 OUT (C),B
 LD (first_68_jump+1),HL
first_68_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_68_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_68_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_68_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_68_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_68_pulse_7:
 OUT (254),A
 INC SP
first_68_jump:
 JP 0
first_72:
first_72_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_72_pulse_1:
 OUT (C),B
 LD (first_72_jump+1),HL
first_72_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_72_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_72_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_72_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_72_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_72_pulse_7:
 OUT (254),A
 INC SP
first_72_jump:
 JP 0
first_73:
first_73_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_73_pulse_1:
 OUT (C),B
 LD (first_73_jump+1),HL
first_73_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_73_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_73_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_73_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_73_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_73_pulse_7:
 OUT (254),A
 INC SP
first_73_jump:
 JP 0
first_74:
first_74_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_74_pulse_1:
 OUT (C),B
 LD (first_74_jump+1),HL
first_74_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_74_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_74_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_74_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_74_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_74_pulse_7:
 OUT (254),A
 INC SP
first_74_jump:
 JP 0
first_82:
first_82_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_82_pulse_1:
 OUT (C),B
 LD (first_82_jump+1),HL
first_82_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_82_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_82_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_82_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_82_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_82_pulse_7:
 OUT (254),A
 INC SP
first_82_jump:
 JP 0
first_84:
first_84_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_84_pulse_1:
 OUT (C),B
 LD (first_84_jump+1),HL
first_84_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_84_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_84_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_84_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_84_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_84_pulse_7:
 OUT (254),A
 INC SP
first_84_jump:
 JP 0
first_85:
first_85_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_85_pulse_1:
 OUT (C),B
 LD (first_85_jump+1),HL
first_85_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_85_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_85_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_85_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_85_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_85_pulse_7:
 OUT (254),A
 INC SP
first_85_jump:
 JP 0
first_86:
first_86_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_86_pulse_1:
 OUT (C),B
 LD (first_86_jump+1),HL
first_86_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_86_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_86_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_86_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_86_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_86_pulse_7:
 OUT (254),A
 INC SP
first_86_jump:
 JP 0
first_89:
first_89_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_89_pulse_1:
 OUT (C),B
 LD (first_89_jump+1),HL
first_89_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_89_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_89_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_89_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_89_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_89_pulse_7:
 OUT (254),A
 INC SP
first_89_jump:
 JP 0
first_90:
first_90_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_90_pulse_1:
 OUT (C),B
 LD (first_90_jump+1),HL
first_90_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_90_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_90_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_90_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_90_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_90_pulse_7:
 OUT (254),A
 INC SP
first_90_jump:
 JP 0
first_91:
first_91_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_91_pulse_1:
 OUT (C),B
 LD (first_91_jump+1),HL
first_91_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_91_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_91_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_91_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_91_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_91_pulse_7:
 OUT (254),A
 INC SP
first_91_jump:
 JP 0
first_93:
first_93_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_93_pulse_1:
 OUT (C),B
 LD (first_93_jump+1),HL
first_93_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_93_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_93_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_93_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_93_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_93_pulse_7:
 OUT (254),A
 INC SP
first_93_jump:
 JP 0
first_101:
first_101_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_101_pulse_1:
 OUT (C),B
 LD (first_101_jump+1),HL
first_101_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_101_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_101_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_101_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_101_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_101_pulse_7:
 OUT (254),A
 INC SP
first_101_jump:
 JP 0
first_102:
first_102_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_102_pulse_1:
 OUT (C),B
 LD (first_102_jump+1),HL
first_102_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_102_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_102_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_102_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_102_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_102_pulse_7:
 OUT (254),A
 INC SP
first_102_jump:
 JP 0
first_106:
first_106_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_106_pulse_1:
 OUT (C),B
 LD (first_106_jump+1),HL
first_106_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_106_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_106_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_106_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_106_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_106_pulse_7:
 OUT (254),A
 INC SP
first_106_jump:
 JP 0
first_107:
first_107_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_107_pulse_1:
 OUT (C),B
 LD (first_107_jump+1),HL
first_107_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_107_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_107_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_107_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_107_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_107_pulse_7:
 OUT (254),A
 INC SP
first_107_jump:
 JP 0
first_109:
first_109_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_109_pulse_1:
 OUT (C),B
 LD (first_109_jump+1),HL
first_109_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_109_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_109_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_109_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_109_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_109_pulse_7:
 OUT (254),A
 INC SP
first_109_jump:
 JP 0
first_110:
first_110_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_110_pulse_1:
 OUT (C),B
 LD (first_110_jump+1),HL
first_110_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_110_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_110_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_110_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_110_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_110_pulse_7:
 OUT (254),A
 INC SP
first_110_jump:
 JP 0
first_111:
first_111_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_111_pulse_1:
 OUT (C),B
 LD (first_111_jump+1),HL
first_111_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_111_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_111_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_111_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_111_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_111_pulse_7:
 OUT (254),A
 INC SP
first_111_jump:
 JP 0
first_118:
first_118_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_118_pulse_1:
 OUT (C),B
 LD (first_118_jump+1),HL
first_118_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_118_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_118_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_118_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_118_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_118_pulse_7:
 OUT (254),A
 INC SP
first_118_jump:
 JP 0
first_119:
first_119_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_119_pulse_1:
 OUT (C),B
 LD (first_119_jump+1),HL
first_119_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_119_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_119_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_119_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_119_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_119_pulse_7:
 OUT (254),A
 INC SP
first_119_jump:
 JP 0
first_123:
first_123_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_123_pulse_1:
 OUT (C),B
 LD (first_123_jump+1),HL
first_123_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_123_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_123_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_123_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_123_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_123_pulse_7:
 OUT (254),A
 INC SP
first_123_jump:
 JP 0
first_125:
first_125_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_125_pulse_1:
 OUT (C),B
 LD (first_125_jump+1),HL
first_125_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_125_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_125_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_125_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_125_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_125_pulse_7:
 OUT (254),A
 INC SP
first_125_jump:
 JP 0
first_126:
first_126_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_126_pulse_1:
 OUT (C),B
 LD (first_126_jump+1),HL
first_126_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_126_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_126_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_126_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_126_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_126_pulse_7:
 OUT (254),A
 INC SP
first_126_jump:
 JP 0
first_127:
first_127_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_127_pulse_1:
 OUT (C),B
 LD (first_127_jump+1),HL
first_127_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_127_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_127_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_127_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_127_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_127_pulse_7:
 OUT (254),A
 INC SP
first_127_jump:
 JP 0
first_128:
first_128_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_128_pulse_1:
 DB 237,113
 LD (first_128_jump+1),HL
first_128_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_128_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_128_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_128_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_128_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_128_pulse_7:
 OUT (254),A
 INC SP
first_128_jump:
 JP 0
first_129:
first_129_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_129_pulse_1:
 DB 237,113
 LD (first_129_jump+1),HL
first_129_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_129_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_129_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_129_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_129_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_129_pulse_7:
 OUT (254),A
 INC SP
first_129_jump:
 JP 0
first_130:
first_130_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_130_pulse_1:
 DB 237,113
 LD (first_130_jump+1),HL
first_130_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_130_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_130_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_130_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_130_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_130_pulse_7:
 OUT (254),A
 INC SP
first_130_jump:
 JP 0
first_132:
first_132_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_132_pulse_1:
 DB 237,113
 LD (first_132_jump+1),HL
first_132_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_132_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_132_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_132_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_132_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_132_pulse_7:
 OUT (254),A
 INC SP
first_132_jump:
 JP 0
first_136:
first_136_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_136_pulse_1:
 DB 237,113
 LD (first_136_jump+1),HL
first_136_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_136_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_136_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_136_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_136_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_136_pulse_7:
 OUT (254),A
 INC SP
first_136_jump:
 JP 0
first_137:
first_137_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_137_pulse_1:
 DB 237,113
 LD (first_137_jump+1),HL
first_137_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_137_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_137_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_137_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_137_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_137_pulse_7:
 OUT (254),A
 INC SP
first_137_jump:
 JP 0
first_138:
first_138_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_138_pulse_1:
 DB 237,113
 LD (first_138_jump+1),HL
first_138_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_138_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_138_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_138_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_138_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_138_pulse_7:
 OUT (254),A
 INC SP
first_138_jump:
 JP 0
first_144:
first_144_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_144_pulse_1:
 DB 237,113
 LD (first_144_jump+1),HL
first_144_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_144_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_144_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_144_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_144_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_144_pulse_7:
 OUT (254),A
 INC SP
first_144_jump:
 JP 0
first_145:
first_145_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_145_pulse_1:
 DB 237,113
 LD (first_145_jump+1),HL
first_145_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_145_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_145_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_145_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_145_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_145_pulse_7:
 OUT (254),A
 INC SP
first_145_jump:
 JP 0
first_146:
first_146_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_146_pulse_1:
 DB 237,113
 LD (first_146_jump+1),HL
first_146_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_146_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_146_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_146_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_146_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_146_pulse_7:
 OUT (254),A
 INC SP
first_146_jump:
 JP 0
first_148:
first_148_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_148_pulse_1:
 DB 237,113
 LD (first_148_jump+1),HL
first_148_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_148_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_148_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_148_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_148_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_148_pulse_7:
 OUT (254),A
 INC SP
first_148_jump:
 JP 0
first_149:
first_149_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_149_pulse_1:
 DB 237,113
 LD (first_149_jump+1),HL
first_149_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_149_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_149_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_149_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_149_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_149_pulse_7:
 OUT (254),A
 INC SP
first_149_jump:
 JP 0
first_153:
first_153_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_153_pulse_1:
 DB 237,113
 LD (first_153_jump+1),HL
first_153_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_153_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_153_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_153_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_153_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_153_pulse_7:
 OUT (254),A
 INC SP
first_153_jump:
 JP 0
first_154:
first_154_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_154_pulse_1:
 DB 237,113
 LD (first_154_jump+1),HL
first_154_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_154_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_154_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_154_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_154_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_154_pulse_7:
 OUT (254),A
 INC SP
first_154_jump:
 JP 0
first_162:
first_162_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_162_pulse_1:
 DB 237,113
 LD (first_162_jump+1),HL
first_162_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_162_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_162_pulse_4:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_162_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_162_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_162_pulse_7:
 OUT (254),A
 INC SP
first_162_jump:
 JP 0
first_164:
first_164_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_164_pulse_1:
 DB 237,113
 LD (first_164_jump+1),HL
first_164_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_164_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_164_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_164_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_164_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_164_pulse_7:
 OUT (254),A
 INC SP
first_164_jump:
 JP 0
first_165:
first_165_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_165_pulse_1:
 DB 237,113
 LD (first_165_jump+1),HL
first_165_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_165_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_165_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_165_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_165_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_165_pulse_7:
 OUT (254),A
 INC SP
first_165_jump:
 JP 0
first_166:
first_166_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_166_pulse_1:
 DB 237,113
 LD (first_166_jump+1),HL
first_166_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_166_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_166_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_166_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_166_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_166_pulse_7:
 OUT (254),A
 INC SP
first_166_jump:
 JP 0
first_169:
first_169_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_169_pulse_1:
 DB 237,113
 LD (first_169_jump+1),HL
first_169_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_169_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_169_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_169_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_169_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_169_pulse_7:
 OUT (254),A
 INC SP
first_169_jump:
 JP 0
first_170:
first_170_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_170_pulse_1:
 DB 237,113
 LD (first_170_jump+1),HL
first_170_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_170_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_170_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_170_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_170_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_170_pulse_7:
 OUT (254),A
 INC SP
first_170_jump:
 JP 0
first_171:
first_171_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_171_pulse_1:
 DB 237,113
 LD (first_171_jump+1),HL
first_171_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_171_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_171_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_171_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_171_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_171_pulse_7:
 OUT (254),A
 INC SP
first_171_jump:
 JP 0
first_173:
first_173_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_173_pulse_1:
 DB 237,113
 LD (first_173_jump+1),HL
first_173_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_173_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_173_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_173_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_173_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_173_pulse_7:
 OUT (254),A
 INC SP
first_173_jump:
 JP 0
first_181:
first_181_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_181_pulse_1:
 DB 237,113
 LD (first_181_jump+1),HL
first_181_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_181_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_181_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_181_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_181_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_181_pulse_7:
 OUT (254),A
 INC SP
first_181_jump:
 JP 0
first_182:
first_182_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_182_pulse_1:
 DB 237,113
 LD (first_182_jump+1),HL
first_182_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_182_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_182_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_182_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_182_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_182_pulse_7:
 OUT (254),A
 INC SP
first_182_jump:
 JP 0
first_183:
first_183_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_183_pulse_1:
 DB 237,113
 LD (first_183_jump+1),HL
first_183_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_183_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_183_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_183_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_183_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_183_pulse_7:
 OUT (254),A
 INC SP
first_183_jump:
 JP 0
first_187:
first_187_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_187_pulse_1:
 DB 237,113
 LD (first_187_jump+1),HL
first_187_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_187_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_187_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_187_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_187_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_187_pulse_7:
 OUT (254),A
 INC SP
first_187_jump:
 JP 0
first_189:
first_189_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_189_pulse_1:
 DB 237,113
 LD (first_189_jump+1),HL
first_189_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_189_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_189_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_189_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_189_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_189_pulse_7:
 OUT (254),A
 INC SP
first_189_jump:
 JP 0
first_190:
first_190_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_190_pulse_1:
 DB 237,113
 LD (first_190_jump+1),HL
first_190_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_190_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_190_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_190_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_190_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_190_pulse_7:
 OUT (254),A
 INC SP
first_190_jump:
 JP 0
first_191:
first_191_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_191_pulse_1:
 DB 237,113
 LD (first_191_jump+1),HL
first_191_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_191_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_191_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_191_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_191_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_191_pulse_7:
 OUT (254),A
 INC SP
first_191_jump:
 JP 0
first_202:
first_202_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_202_pulse_1:
 OUT (C),B
 LD (first_202_jump+1),HL
first_202_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_202_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_202_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_202_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_202_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_202_pulse_7:
 OUT (254),A
 INC SP
first_202_jump:
 JP 0
first_204:
first_204_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_204_pulse_1:
 OUT (C),B
 LD (first_204_jump+1),HL
first_204_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_204_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_204_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_204_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_204_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_204_pulse_7:
 OUT (254),A
 INC SP
first_204_jump:
 JP 0
first_205:
first_205_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_205_pulse_1:
 OUT (C),B
 LD (first_205_jump+1),HL
first_205_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_205_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_205_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_205_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_205_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_205_pulse_7:
 OUT (254),A
 INC SP
first_205_jump:
 JP 0
first_213:
first_213_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_213_pulse_1:
 OUT (C),B
 LD (first_213_jump+1),HL
first_213_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_213_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_213_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_213_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_213_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_213_pulse_7:
 OUT (254),A
 INC SP
first_213_jump:
 JP 0
first_214:
first_214_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_214_pulse_1:
 OUT (C),B
 LD (first_214_jump+1),HL
first_214_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_214_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_214_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_214_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_214_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_214_pulse_7:
 OUT (254),A
 INC SP
first_214_jump:
 JP 0
first_215:
first_215_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_215_pulse_1:
 OUT (C),B
 LD (first_215_jump+1),HL
first_215_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_215_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_215_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_215_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_215_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_215_pulse_7:
 OUT (254),A
 INC SP
first_215_jump:
 JP 0
first_218:
first_218_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_218_pulse_1:
 OUT (C),B
 LD (first_218_jump+1),HL
first_218_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_218_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_218_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_218_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_218_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_218_pulse_7:
 OUT (254),A
 INC SP
first_218_jump:
 JP 0
first_219:
first_219_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_219_pulse_1:
 OUT (C),B
 LD (first_219_jump+1),HL
first_219_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_219_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_219_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_219_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_219_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_219_pulse_7:
 OUT (254),A
 INC SP
first_219_jump:
 JP 0
first_221:
first_221_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_221_pulse_1:
 OUT (C),B
 LD (first_221_jump+1),HL
first_221_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_221_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_221_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_221_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_221_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_221_pulse_7:
 OUT (254),A
 INC SP
first_221_jump:
 JP 0
first_222:
first_222_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_222_pulse_1:
 OUT (C),B
 LD (first_222_jump+1),HL
first_222_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_222_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_222_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_222_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_222_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_222_pulse_7:
 OUT (254),A
 INC SP
first_222_jump:
 JP 0
first_223:
first_223_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_223_pulse_1:
 OUT (C),B
 LD (first_223_jump+1),HL
first_223_pulse_2:
 DB 237,113
 EXX
 LD C,L
 EXX
 NOP
first_223_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_223_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_223_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_223_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_223_pulse_7:
 OUT (254),A
 INC SP
first_223_jump:
 JP 0
first_235:
first_235_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_235_pulse_1:
 OUT (C),B
 LD (first_235_jump+1),HL
first_235_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_235_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_235_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_235_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_235_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_235_pulse_7:
 OUT (254),A
 INC SP
first_235_jump:
 JP 0
first_237:
first_237_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_237_pulse_1:
 OUT (C),B
 LD (first_237_jump+1),HL
first_237_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_237_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_237_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_237_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_237_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_237_pulse_7:
 OUT (254),A
 INC SP
first_237_jump:
 JP 0
first_238:
first_238_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_238_pulse_1:
 OUT (C),B
 LD (first_238_jump+1),HL
first_238_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_238_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_238_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_238_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_238_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_238_pulse_7:
 OUT (254),A
 INC SP
first_238_jump:
 JP 0
first_239:
first_239_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_239_pulse_1:
 OUT (C),B
 LD (first_239_jump+1),HL
first_239_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_239_pulse_3:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_239_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_239_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_239_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_239_pulse_7:
 OUT (254),A
 INC SP
first_239_jump:
 JP 0
first_247:
first_247_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_247_pulse_1:
 OUT (C),B
 LD (first_247_jump+1),HL
first_247_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_247_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_247_pulse_4:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_247_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_247_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_247_pulse_7:
 OUT (254),A
 INC SP
first_247_jump:
 JP 0
first_251:
first_251_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_251_pulse_1:
 OUT (C),B
 LD (first_251_jump+1),HL
first_251_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_251_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_251_pulse_4:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_251_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_251_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_251_pulse_7:
 OUT (254),A
 INC SP
first_251_jump:
 JP 0
first_253:
first_253_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_253_pulse_1:
 OUT (C),B
 LD (first_253_jump+1),HL
first_253_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_253_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_253_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_253_pulse_5:
 OUT (254),A
 LD H,191
 XOR A
 LD SP,HL
first_253_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_253_pulse_7:
 OUT (254),A
 INC SP
first_253_jump:
 JP 0
first_254:
first_254_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_254_pulse_1:
 OUT (C),B
 LD (first_254_jump+1),HL
first_254_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_254_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_254_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_254_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_254_pulse_6:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
first_254_pulse_7:
 OUT (254),A
 INC SP
first_254_jump:
 JP 0
first_255:
first_255_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_255_pulse_1:
 OUT (C),B
 LD (first_255_jump+1),HL
first_255_pulse_2:
 OUT (C),B
 EXX
 LD C,L
 EXX
 NOP
first_255_pulse_3:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_255_pulse_4:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_255_pulse_5:
 OUT (254),A
 LD H,191
 LD A,B
 LD SP,HL
first_255_pulse_6:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
first_255_pulse_7:
 OUT (254),A
 INC SP
first_255_jump:
 JP 0
second_0_0:
second_0_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_0_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_0_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_0_0_pulse_11:
 DB 237,113
 JP Z,bank_0_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_0_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_0_4:
second_0_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_0_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_0_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_0_4_pulse_11:
 DB 237,113
 JP Z,bank_0_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_0_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_0_8:
second_0_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_0_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_0_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_0_8_pulse_11:
 DB 237,113
 JP Z,bank_0_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_0_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_0_12:
second_0_12_pulse_8:
 DB 237,113
 LD L,12
 LD A,R
second_0_12_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_0_12_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_0_12_pulse_11:
 DB 237,113
 JP Z,bank_0_12
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_0_12:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_0_16:
second_0_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_0_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_0_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_0_16_pulse_11:
 DB 237,113
 JP Z,bank_0_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_0_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_2_0:
second_2_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_2_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_2_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_2_0_pulse_11:
 DB 237,113
 JP Z,bank_2_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_2_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_4_0:
second_4_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_4_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_4_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_4_0_pulse_11:
 DB 237,113
 JP Z,bank_4_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_4_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_4_4:
second_4_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_4_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_4_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_4_4_pulse_11:
 DB 237,113
 JP Z,bank_4_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_4_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_8_0:
second_8_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_8_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_8_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_8_0_pulse_11:
 DB 237,113
 JP Z,bank_8_0
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_8_0:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_8_4:
second_8_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_8_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_8_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_8_4_pulse_11:
 DB 237,113
 JP Z,bank_8_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_8_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_8_8:
second_8_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_8_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_8_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_8_8_pulse_11:
 DB 237,113
 JP Z,bank_8_8
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_8_8:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_8_16:
second_8_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_8_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_8_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_8_16_pulse_11:
 DB 237,113
 JP Z,bank_8_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_8_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_16_0:
second_16_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_16_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_16_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_16_0_pulse_11:
 OUT (C),H
 JP Z,bank_16_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_16_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_16_4:
second_16_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_16_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_16_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_16_4_pulse_11:
 OUT (C),H
 JP Z,bank_16_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_16_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_16_8:
second_16_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_16_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_16_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_16_8_pulse_11:
 OUT (C),H
 JP Z,bank_16_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_16_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_16_16:
second_16_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_16_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_16_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_16_16_pulse_11:
 OUT (C),H
 JP Z,bank_16_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_16_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_17_0:
second_17_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_17_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_17_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_17_0_pulse_11:
 OUT (C),H
 JP Z,bank_17_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_17_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_18_4:
second_18_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_18_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_18_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_18_4_pulse_11:
 OUT (C),H
 JP Z,bank_18_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_18_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_18_8:
second_18_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_18_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_18_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_18_8_pulse_11:
 OUT (C),H
 JP Z,bank_18_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_18_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_32_4:
second_32_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_32_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_32_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_32_4_pulse_11:
 DB 237,113
 JP Z,bank_32_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_32_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_32_8:
second_32_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_32_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_32_8_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_32_8_pulse_11:
 DB 237,113
 JP Z,bank_32_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_32_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_32_16:
second_32_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_32_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_32_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_32_16_pulse_11:
 DB 237,113
 JP Z,bank_32_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_32_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_33_0:
second_33_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_33_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_33_0_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_33_0_pulse_11:
 DB 237,113
 JP Z,bank_33_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_33_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_34_4:
second_34_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_34_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_34_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_34_4_pulse_11:
 DB 237,113
 JP Z,bank_34_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_34_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_34_8:
second_34_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_34_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_34_8_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_34_8_pulse_11:
 DB 237,113
 JP Z,bank_34_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_34_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_36_8:
second_36_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_36_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_36_8_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_36_8_pulse_11:
 DB 237,113
 JP Z,bank_36_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_36_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_36_16:
second_36_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_36_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_36_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_36_16_pulse_11:
 DB 237,113
 JP Z,bank_36_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_36_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_37_0:
second_37_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_37_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_37_0_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_37_0_pulse_11:
 DB 237,113
 JP Z,bank_37_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_37_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_40_20:
second_40_20_pulse_8:
 DB 237,113
 LD L,20
 LD A,R
second_40_20_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_40_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_40_20_pulse_11:
 DB 237,113
 JP Z,bank_40_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_40_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_41_4:
second_41_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_41_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_41_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_41_4_pulse_11:
 DB 237,113
 JP Z,bank_41_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_41_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_42_8:
second_42_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_42_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_42_8_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_42_8_pulse_11:
 DB 237,113
 JP Z,bank_42_8
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_42_8:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_50_16:
second_50_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_50_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_50_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_50_16_pulse_11:
 OUT (C),H
 JP Z,bank_50_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_50_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_51_0:
second_51_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_51_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_51_0_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_51_0_pulse_11:
 OUT (C),H
 JP Z,bank_51_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_51_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_53_4:
second_53_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_53_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_53_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_53_4_pulse_11:
 OUT (C),H
 JP Z,bank_53_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_53_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_64_0:
second_64_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_64_0_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_64_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_64_0_pulse_11:
 DB 237,113
 JP Z,bank_64_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_64_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_64_16:
second_64_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_64_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_64_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_64_16_pulse_11:
 DB 237,113
 JP Z,bank_64_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_64_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_65_0:
second_65_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_65_0_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_65_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_65_0_pulse_11:
 DB 237,113
 JP Z,bank_65_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_65_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_66_4:
second_66_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_66_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_66_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_66_4_pulse_11:
 DB 237,113
 JP Z,bank_66_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_66_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_68_8:
second_68_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_68_8_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_68_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_68_8_pulse_11:
 DB 237,113
 JP Z,bank_68_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_68_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_68_16:
second_68_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_68_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_68_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_68_16_pulse_11:
 DB 237,113
 JP Z,bank_68_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_68_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_72_16:
second_72_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_72_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_72_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_72_16_pulse_11:
 DB 237,113
 JP Z,bank_72_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_72_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_72_20:
second_72_20_pulse_8:
 DB 237,113
 LD L,20
 LD A,R
second_72_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_72_20_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_72_20_pulse_11:
 DB 237,113
 JP Z,bank_72_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_72_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_73_0:
second_73_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_73_0_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_73_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_73_0_pulse_11:
 DB 237,113
 JP Z,bank_73_0
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_73_0:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_73_4:
second_73_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_73_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_73_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_73_4_pulse_11:
 DB 237,113
 JP Z,bank_73_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_73_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_74_8:
second_74_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_74_8_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_74_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_74_8_pulse_11:
 DB 237,113
 JP Z,bank_74_8
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_74_8:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_74_16:
second_74_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_74_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_74_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_74_16_pulse_11:
 DB 237,113
 JP Z,bank_74_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_74_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_76_20:
second_76_20_pulse_8:
 DB 237,113
 LD L,20
 LD A,R
second_76_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_76_20_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_76_20_pulse_11:
 DB 237,113
 JP Z,bank_76_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_76_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_82_8:
second_82_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_82_8_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_82_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_82_8_pulse_11:
 OUT (C),H
 JP Z,bank_82_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_82_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_82_16:
second_82_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_82_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_82_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_82_16_pulse_11:
 OUT (C),H
 JP Z,bank_82_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_82_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_84_20:
second_84_20_pulse_8:
 DB 237,113
 LD L,20
 LD A,R
second_84_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_84_20_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_84_20_pulse_11:
 OUT (C),H
 JP Z,bank_84_20
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_84_20:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_85_4:
second_85_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_85_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_85_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_85_4_pulse_11:
 OUT (C),H
 JP Z,bank_85_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_85_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_85_12:
second_85_12_pulse_8:
 DB 237,113
 LD L,12
 LD A,R
second_85_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_85_12_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_85_12_pulse_11:
 OUT (C),H
 JP Z,bank_85_12
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_85_12:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_86_8:
second_86_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_86_8_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_86_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_86_8_pulse_11:
 OUT (C),H
 JP Z,bank_86_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_86_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_89_12:
second_89_12_pulse_8:
 DB 237,113
 LD L,12
 LD A,R
second_89_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_89_12_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_89_12_pulse_11:
 OUT (C),H
 JP Z,bank_89_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_89_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_90_16:
second_90_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_90_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_90_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_90_16_pulse_11:
 OUT (C),H
 JP Z,bank_90_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_90_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_90_20:
second_90_20_pulse_8:
 DB 237,113
 LD L,20
 LD A,R
second_90_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_90_20_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_90_20_pulse_11:
 OUT (C),H
 JP Z,bank_90_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_90_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_91_4:
second_91_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_91_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_91_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_91_4_pulse_11:
 OUT (C),H
 JP Z,bank_91_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_91_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_102_8:
second_102_8_pulse_8:
 DB 237,113
 LD L,8
 LD A,R
second_102_8_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_102_8_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_102_8_pulse_11:
 DB 237,113
 JP Z,bank_102_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_102_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_106_16:
second_106_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_106_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_106_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_106_16_pulse_11:
 DB 237,113
 JP Z,bank_106_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_106_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_106_20:
second_106_20_pulse_8:
 DB 237,113
 LD L,20
 LD A,R
second_106_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_106_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_106_20_pulse_11:
 DB 237,113
 JP Z,bank_106_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_106_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_107_0:
second_107_0_pulse_8:
 DB 237,113
 LD L,0
 LD A,R
second_107_0_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_107_0_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_107_0_pulse_11:
 DB 237,113
 JP Z,bank_107_0
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_107_0:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_107_4:
second_107_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_107_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_107_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_107_4_pulse_11:
 DB 237,113
 JP Z,bank_107_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_107_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_109_4:
second_109_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_109_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_109_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_109_4_pulse_11:
 DB 237,113
 JP Z,bank_109_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_109_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_109_12:
second_109_12_pulse_8:
 DB 237,113
 LD L,12
 LD A,R
second_109_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_109_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_109_12_pulse_11:
 DB 237,113
 JP Z,bank_109_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_109_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_110_16:
second_110_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_110_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_110_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_110_16_pulse_11:
 DB 237,113
 JP Z,bank_110_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_110_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_118_16:
second_118_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_118_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_118_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_118_16_pulse_11:
 OUT (C),H
 JP Z,bank_118_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_118_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_118_20:
second_118_20_pulse_8:
 DB 237,113
 LD L,20
 LD A,R
second_118_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_118_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_118_20_pulse_11:
 OUT (C),H
 JP Z,bank_118_20
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_118_20:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_119_4:
second_119_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_119_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_119_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_119_4_pulse_11:
 OUT (C),H
 JP Z,bank_119_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_119_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_123_12:
second_123_12_pulse_8:
 DB 237,113
 LD L,12
 LD A,R
second_123_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_123_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_123_12_pulse_11:
 OUT (C),H
 JP Z,bank_123_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_123_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_123_16:
second_123_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_123_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_123_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_123_16_pulse_11:
 OUT (C),H
 JP Z,bank_123_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_123_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_125_16:
second_125_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_125_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_125_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_125_16_pulse_11:
 OUT (C),H
 JP Z,bank_125_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_125_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_126_20:
second_126_20_pulse_8:
 DB 237,113
 LD L,20
 LD A,R
second_126_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_126_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_126_20_pulse_11:
 OUT (C),H
 JP Z,bank_126_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_126_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_127_4:
second_127_4_pulse_8:
 DB 237,113
 LD L,4
 LD A,R
second_127_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_127_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_127_4_pulse_11:
 OUT (C),H
 JP Z,bank_127_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_127_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_127_12:
second_127_12_pulse_8:
 DB 237,113
 LD L,12
 LD A,R
second_127_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_127_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_127_12_pulse_11:
 OUT (C),H
 JP Z,bank_127_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_127_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_127_16:
second_127_16_pulse_8:
 DB 237,113
 LD L,16
 LD A,R
second_127_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_127_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_127_16_pulse_11:
 OUT (C),H
 JP Z,bank_127_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_127_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_127_20:
second_127_20_pulse_8:
 DB 237,113
 LD L,20
 LD A,R
second_127_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_127_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_127_20_pulse_11:
 OUT (C),H
 JP Z,bank_127_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_127_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_128_0:
second_128_0_pulse_8:
 OUT (C),B
 LD L,0
 LD A,R
second_128_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_128_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_128_0_pulse_11:
 DB 237,113
 JP Z,bank_128_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_128_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_128_4:
second_128_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_128_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_128_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_128_4_pulse_11:
 DB 237,113
 JP Z,bank_128_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_128_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_128_8:
second_128_8_pulse_8:
 OUT (C),B
 LD L,8
 LD A,R
second_128_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_128_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_128_8_pulse_11:
 DB 237,113
 JP Z,bank_128_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_128_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_128_16:
second_128_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_128_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_128_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_128_16_pulse_11:
 DB 237,113
 JP Z,bank_128_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_128_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_129_0:
second_129_0_pulse_8:
 OUT (C),B
 LD L,0
 LD A,R
second_129_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_129_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_129_0_pulse_11:
 DB 237,113
 JP Z,bank_129_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_129_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_130_4:
second_130_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_130_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_130_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_130_4_pulse_11:
 DB 237,113
 JP Z,bank_130_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_130_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_132_4:
second_132_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_132_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_132_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_132_4_pulse_11:
 DB 237,113
 JP Z,bank_132_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_132_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_132_8:
second_132_8_pulse_8:
 OUT (C),B
 LD L,8
 LD A,R
second_132_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_132_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_132_8_pulse_11:
 DB 237,113
 JP Z,bank_132_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_132_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_136_16:
second_136_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_136_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_136_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_136_16_pulse_11:
 DB 237,113
 JP Z,bank_136_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_136_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_137_0:
second_137_0_pulse_8:
 OUT (C),B
 LD L,0
 LD A,R
second_137_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_137_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_137_0_pulse_11:
 DB 237,113
 JP Z,bank_137_0
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_137_0:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_137_4:
second_137_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_137_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_137_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_137_4_pulse_11:
 DB 237,113
 JP Z,bank_137_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_137_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_145_4:
second_145_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_145_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_145_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_145_4_pulse_11:
 OUT (C),H
 JP Z,bank_145_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_145_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_146_8:
second_146_8_pulse_8:
 OUT (C),B
 LD L,8
 LD A,R
second_146_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_146_8_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_146_8_pulse_11:
 OUT (C),H
 JP Z,bank_146_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_146_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_146_16:
second_146_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_146_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_146_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_146_16_pulse_11:
 OUT (C),H
 JP Z,bank_146_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_146_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_148_16:
second_148_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_148_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_148_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_148_16_pulse_11:
 OUT (C),H
 JP Z,bank_148_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_148_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_148_20:
second_148_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_148_20_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_148_20_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_148_20_pulse_11:
 OUT (C),H
 JP Z,bank_148_20
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_148_20:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_149_0:
second_149_0_pulse_8:
 OUT (C),B
 LD L,0
 LD A,R
second_149_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_149_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_149_0_pulse_11:
 OUT (C),H
 JP Z,bank_149_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_149_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_149_4:
second_149_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_149_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_149_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_149_4_pulse_11:
 OUT (C),H
 JP Z,bank_149_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_149_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_153_12:
second_153_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_153_12_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_153_12_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_153_12_pulse_11:
 OUT (C),H
 JP Z,bank_153_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_153_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_164_16:
second_164_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_164_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_164_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_164_16_pulse_11:
 DB 237,113
 JP Z,bank_164_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_164_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_165_0:
second_165_0_pulse_8:
 OUT (C),B
 LD L,0
 LD A,R
second_165_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_165_0_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_165_0_pulse_11:
 DB 237,113
 JP Z,bank_165_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_165_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_165_4:
second_165_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_165_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_165_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_165_4_pulse_11:
 DB 237,113
 JP Z,bank_165_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_165_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_166_8:
second_166_8_pulse_8:
 OUT (C),B
 LD L,8
 LD A,R
second_166_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_166_8_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_166_8_pulse_11:
 DB 237,113
 JP Z,bank_166_8
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_166_8:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_169_12:
second_169_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_169_12_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_169_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_169_12_pulse_11:
 DB 237,113
 JP Z,bank_169_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_169_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_170_8:
second_170_8_pulse_8:
 OUT (C),B
 LD L,8
 LD A,R
second_170_8_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_170_8_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_170_8_pulse_11:
 DB 237,113
 JP Z,bank_170_8
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_170_8:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_170_16:
second_170_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_170_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_170_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_170_16_pulse_11:
 DB 237,113
 JP Z,bank_170_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_170_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_171_0:
second_171_0_pulse_8:
 OUT (C),B
 LD L,0
 LD A,R
second_171_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_171_0_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_171_0_pulse_11:
 DB 237,113
 JP Z,bank_171_0
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_171_0:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_173_4:
second_173_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_173_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_173_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_173_4_pulse_11:
 DB 237,113
 JP Z,bank_173_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_173_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_173_12:
second_173_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_173_12_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_173_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_173_12_pulse_11:
 DB 237,113
 JP Z,bank_173_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_173_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_179_0:
second_179_0_pulse_8:
 OUT (C),B
 LD L,0
 LD A,R
second_179_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_179_0_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_179_0_pulse_11:
 OUT (C),H
 JP Z,bank_179_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_179_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_181_4:
second_181_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_181_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_181_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_181_4_pulse_11:
 OUT (C),H
 JP Z,bank_181_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_181_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_181_12:
second_181_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_181_12_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_181_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_181_12_pulse_11:
 OUT (C),H
 JP Z,bank_181_12
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_181_12:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_182_16:
second_182_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_182_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_182_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_182_16_pulse_11:
 OUT (C),H
 JP Z,bank_182_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_182_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_182_20:
second_182_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_182_20_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_182_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_182_20_pulse_11:
 OUT (C),H
 JP Z,bank_182_20
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_182_20:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_183_0:
second_183_0_pulse_8:
 OUT (C),B
 LD L,0
 LD A,R
second_183_0_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_183_0_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_183_0_pulse_11:
 OUT (C),H
 JP Z,bank_183_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_183_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_183_4:
second_183_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_183_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_183_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_183_4_pulse_11:
 OUT (C),H
 JP Z,bank_183_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_183_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_187_4:
second_187_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_187_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_187_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_187_4_pulse_11:
 OUT (C),H
 JP Z,bank_187_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_187_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_187_12:
second_187_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_187_12_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_187_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_187_12_pulse_11:
 OUT (C),H
 JP Z,bank_187_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_187_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_189_16:
second_189_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_189_16_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_189_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_189_16_pulse_11:
 OUT (C),H
 JP Z,bank_189_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_189_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_190_20:
second_190_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_190_20_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_190_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_190_20_pulse_11:
 OUT (C),H
 JP Z,bank_190_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_190_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_191_4:
second_191_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_191_4_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_191_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_191_4_pulse_11:
 OUT (C),H
 JP Z,bank_191_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_191_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_191_20:
second_191_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_191_20_pulse_9:
 DB 237,113
 LD SP,HL
 POP HL
second_191_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_191_20_pulse_11:
 OUT (C),H
 JP Z,bank_191_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_191_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_202_16:
second_202_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_202_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_202_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_202_16_pulse_11:
 DB 237,113
 JP Z,bank_202_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_202_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_204_20:
second_204_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_204_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_204_20_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_204_20_pulse_11:
 DB 237,113
 JP Z,bank_204_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_204_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_205_4:
second_205_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_205_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_205_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_205_4_pulse_11:
 DB 237,113
 JP Z,bank_205_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_205_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_213_12:
second_213_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_213_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_213_12_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_213_12_pulse_11:
 OUT (C),H
 JP Z,bank_213_12
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_213_12:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_214_16:
second_214_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_214_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_214_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_214_16_pulse_11:
 OUT (C),H
 JP Z,bank_214_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_214_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_215_0:
second_215_0_pulse_8:
 OUT (C),B
 LD L,0
 LD A,R
second_215_0_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_215_0_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_215_0_pulse_11:
 OUT (C),H
 JP Z,bank_215_0
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_215_0:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_218_20:
second_218_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_218_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_218_20_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_218_20_pulse_11:
 OUT (C),H
 JP Z,bank_218_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_218_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_219_4:
second_219_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_219_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_219_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_219_4_pulse_11:
 OUT (C),H
 JP Z,bank_219_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_219_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_219_12:
second_219_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_219_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_219_12_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_219_12_pulse_11:
 OUT (C),H
 JP Z,bank_219_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_219_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_221_12:
second_221_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_221_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_221_12_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_221_12_pulse_11:
 OUT (C),H
 JP Z,bank_221_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_221_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_221_16:
second_221_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_221_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_221_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_221_16_pulse_11:
 OUT (C),H
 JP Z,bank_221_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_221_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_222_20:
second_222_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_222_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_222_20_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_222_20_pulse_11:
 OUT (C),H
 JP Z,bank_222_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_222_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_223_4:
second_223_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_223_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_223_4_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_223_4_pulse_11:
 OUT (C),H
 JP Z,bank_223_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_223_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_223_12:
second_223_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_223_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_223_12_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_223_12_pulse_11:
 OUT (C),H
 JP Z,bank_223_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_223_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_223_16:
second_223_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_223_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_223_16_pulse_10:
 DB 237,113
 LD A,D
 AND E
 INC A
 EXX
second_223_16_pulse_11:
 OUT (C),H
 JP Z,bank_223_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_223_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_237_12:
second_237_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_237_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_237_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_237_12_pulse_11:
 DB 237,113
 JP Z,bank_237_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_237_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_237_16:
second_237_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_237_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_237_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_237_16_pulse_11:
 DB 237,113
 JP Z,bank_237_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_237_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_238_20:
second_238_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_238_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_238_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_238_20_pulse_11:
 DB 237,113
 JP Z,bank_238_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
bank_238_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 DB 237,113
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_239_4:
second_239_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_239_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_239_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_239_4_pulse_11:
 DB 237,113
 JP Z,bank_239_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_239_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_239_12:
second_239_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_239_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_239_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_239_12_pulse_11:
 DB 237,113
 JP Z,bank_239_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_239_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_239_16:
second_239_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_239_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_239_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_239_16_pulse_11:
 DB 237,113
 JP Z,bank_239_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_239_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_239_20:
second_239_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_239_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_239_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_239_20_pulse_11:
 DB 237,113
 JP Z,bank_239_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_239_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_247_4:
second_247_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_247_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_247_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_247_4_pulse_11:
 OUT (C),H
 JP Z,bank_247_4
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_247_4:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_247_12:
second_247_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_247_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_247_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_247_12_pulse_11:
 OUT (C),H
 JP Z,bank_247_12
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_247_12:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_247_16:
second_247_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_247_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_247_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_247_16_pulse_11:
 OUT (C),H
 JP Z,bank_247_16
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_247_16:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_247_20:
second_247_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_247_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_247_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_247_20_pulse_11:
 OUT (C),H
 JP Z,bank_247_20
 LD A,0
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_247_20:
 LD A,0
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_251_16:
second_251_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_251_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_251_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_251_16_pulse_11:
 OUT (C),H
 JP Z,bank_251_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_251_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_251_20:
second_251_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_251_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_251_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_251_20_pulse_11:
 OUT (C),H
 JP Z,bank_251_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_251_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,0
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_253_20:
second_253_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_253_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_253_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_253_20_pulse_11:
 OUT (C),H
 JP Z,bank_253_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 DB 237,113
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_253_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,0
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_255_4:
second_255_4_pulse_8:
 OUT (C),B
 LD L,4
 LD A,R
second_255_4_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_255_4_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_255_4_pulse_11:
 OUT (C),H
 JP Z,bank_255_4
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_255_4:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_255_12:
second_255_12_pulse_8:
 OUT (C),B
 LD L,12
 LD A,R
second_255_12_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_255_12_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_255_12_pulse_11:
 OUT (C),H
 JP Z,bank_255_12
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_255_12:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_255_16:
second_255_16_pulse_8:
 OUT (C),B
 LD L,16
 LD A,R
second_255_16_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_255_16_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_255_16_pulse_11:
 OUT (C),H
 JP Z,bank_255_16
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_255_16:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
second_255_20:
second_255_20_pulse_8:
 OUT (C),B
 LD L,20
 LD A,R
second_255_20_pulse_9:
 OUT (C),B
 LD SP,HL
 POP HL
second_255_20_pulse_10:
 OUT (C),B
 LD A,D
 AND E
 INC A
 EXX
second_255_20_pulse_11:
 OUT (C),H
 JP Z,bank_255_20
 LD A,16
 OUT (254),A
 EXX
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
bank_255_20:
 LD A,16
 OUT (254),A
 LD BC,0x7FFD
 LD A,16
 OUT (254),A
 LD DE,0x19C0
 LD A,16
 OUT (254),A
 OUT (C),D
 EXX
 OUT (C),B
 ; The following FIRST increment reaches C000 exactly.
 LD D,0xBF
 RET C
 JP (HL)
kernel_end:
 NOP
