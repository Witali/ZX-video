; Native residentPCM8 component, sixteen PDM outputs every28 T.
; Pentagon nominal3.584MHz gives128k decisions/s and8k PCM samples/s.
; MainBC=10FE (B is the constant EAR-high value); DE=source byte cursor.
; HL=lookup scratch / next FIRST target, IY=current SECOND target,
; IXL=successor feedback offset. Alternate registers and IXH stay untouched.
; SP is a six-byte lookup cursor and later dead scratch: never CALL/PUSH.
; Record: FIRST word, SECOND word, flag byte0, successorOffset byte.
; Enter FIRST with SP=record+2, DE=current PCM address, HL=FIRST address.
; One input sample is prefetched; current/next PCM bytes must both be valid.
; This flat one-bank proof has no IMA decoding, bank handoff, EOF or IRQ.
; Timing ledger is between effective OUT writes: ED OUT12 leaves16 T;
; immediate OUT11 leaves17 T. The latter gaps use7+4+6, neverindexedPOP14.
; Copy H/L into IY through A: direct prefixed H/L copies change semantics.
 ORG 32768
first_0:
first_0_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_0_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_0_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_0_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_0_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_0_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_0_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_0_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_1:
first_1_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_1_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_1_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_1_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_1_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_1_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_1_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_1_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_2:
first_2_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_2_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_2_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_2_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_2_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_2_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_2_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_2_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_4:
first_4_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_4_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_4_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_4_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_4_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_4_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_4_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_4_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_8:
first_8_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_8_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_8_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_8_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_8_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_8_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_8_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_8_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_16:
first_16_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_16_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_16_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_16_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_16_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_16_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_16_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_16_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_17:
first_17_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_17_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_17_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_17_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_17_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_17_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_17_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_17_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_18:
first_18_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_18_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_18_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_18_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_18_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_18_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_18_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_18_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_20:
first_20_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_20_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_20_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_20_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_20_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_20_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_20_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_20_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_32:
first_32_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_32_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_32_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_32_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_32_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_32_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_32_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_32_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_33:
first_33_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_33_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_33_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_33_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_33_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_33_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_33_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_33_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_34:
first_34_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_34_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_34_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_34_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_34_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_34_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_34_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_34_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_36:
first_36_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_36_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_36_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_36_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_36_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_36_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_36_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_36_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_37:
first_37_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_37_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_37_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_37_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_37_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_37_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_37_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_37_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_40:
first_40_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_40_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_40_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_40_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_40_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_40_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_40_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_40_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_41:
first_41_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_41_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_41_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_41_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_41_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_41_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_41_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_41_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_42:
first_42_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_42_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_42_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_42_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_42_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_42_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_42_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_42_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_50:
first_50_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_50_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_50_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_50_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_50_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_50_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_50_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_50_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_51:
first_51_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_51_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_51_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_51_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_51_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_51_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_51_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_51_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_53:
first_53_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_53_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_53_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_53_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_53_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_53_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_53_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_53_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_64:
first_64_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_64_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_64_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_64_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_64_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_64_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_64_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_64_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_65:
first_65_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_65_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_65_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_65_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_65_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_65_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_65_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_65_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_66:
first_66_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_66_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_66_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_66_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_66_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_66_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_66_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_66_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_68:
first_68_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_68_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_68_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_68_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_68_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_68_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_68_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_68_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_72:
first_72_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_72_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_72_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_72_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_72_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_72_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_72_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_72_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_73:
first_73_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_73_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_73_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_73_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_73_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_73_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_73_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_73_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_74:
first_74_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_74_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_74_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_74_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_74_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_74_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_74_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_74_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_82:
first_82_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_82_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_82_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_82_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_82_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_82_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_82_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_82_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_84:
first_84_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_84_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_84_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_84_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_84_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_84_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_84_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_84_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_85:
first_85_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_85_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_85_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_85_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_85_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_85_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_85_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_85_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_86:
first_86_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_86_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_86_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_86_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_86_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_86_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_86_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_86_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_89:
first_89_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_89_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_89_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_89_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_89_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_89_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_89_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_89_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_90:
first_90_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_90_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_90_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_90_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_90_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_90_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_90_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_90_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_91:
first_91_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_91_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_91_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_91_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_91_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_91_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_91_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_91_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_93:
first_93_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_93_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_93_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_93_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_93_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_93_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_93_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_93_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_101:
first_101_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_101_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_101_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_101_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_101_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_101_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_101_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_101_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_102:
first_102_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_102_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_102_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_102_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_102_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_102_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_102_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_102_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_106:
first_106_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_106_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_106_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_106_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_106_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_106_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_106_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_106_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_107:
first_107_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_107_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_107_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_107_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_107_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_107_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_107_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_107_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_109:
first_109_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_109_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_109_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_109_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_109_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_109_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_109_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_109_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_110:
first_110_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_110_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_110_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_110_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_110_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_110_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_110_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_110_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_111:
first_111_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_111_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_111_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_111_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_111_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_111_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_111_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_111_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_118:
first_118_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_118_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_118_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_118_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_118_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_118_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_118_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_118_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_119:
first_119_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_119_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_119_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_119_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_119_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_119_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_119_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_119_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_123:
first_123_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_123_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_123_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_123_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_123_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_123_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_123_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_123_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_125:
first_125_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_125_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_125_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_125_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_125_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_125_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_125_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_125_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_126:
first_126_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_126_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_126_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_126_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_126_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_126_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_126_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_126_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_127:
first_127_pulse_0:
 DB 237,113
 POP HL
 INC DE
first_127_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_127_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_127_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_127_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_127_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_127_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_127_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_128:
first_128_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_128_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_128_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_128_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_128_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_128_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_128_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_128_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_129:
first_129_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_129_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_129_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_129_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_129_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_129_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_129_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_129_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_130:
first_130_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_130_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_130_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_130_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_130_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_130_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_130_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_130_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_132:
first_132_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_132_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_132_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_132_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_132_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_132_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_132_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_132_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_136:
first_136_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_136_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_136_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_136_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_136_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_136_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_136_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_136_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_137:
first_137_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_137_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_137_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_137_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_137_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_137_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_137_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_137_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_138:
first_138_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_138_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_138_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_138_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_138_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_138_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_138_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_138_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_144:
first_144_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_144_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_144_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_144_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_144_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_144_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_144_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_144_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_145:
first_145_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_145_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_145_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_145_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_145_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_145_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_145_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_145_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_146:
first_146_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_146_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_146_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_146_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_146_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_146_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_146_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_146_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_148:
first_148_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_148_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_148_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_148_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_148_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_148_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_148_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_148_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_149:
first_149_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_149_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_149_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_149_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_149_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_149_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_149_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_149_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_153:
first_153_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_153_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_153_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_153_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_153_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_153_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_153_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_153_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_154:
first_154_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_154_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_154_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_154_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_154_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_154_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_154_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_154_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_162:
first_162_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_162_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_162_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_162_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_162_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_162_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_162_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_162_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_164:
first_164_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_164_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_164_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_164_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_164_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_164_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_164_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_164_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_165:
first_165_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_165_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_165_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_165_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_165_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_165_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_165_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_165_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_166:
first_166_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_166_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_166_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_166_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_166_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_166_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_166_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_166_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_169:
first_169_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_169_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_169_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_169_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_169_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_169_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_169_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_169_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_170:
first_170_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_170_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_170_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_170_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_170_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_170_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_170_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_170_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_171:
first_171_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_171_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_171_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_171_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_171_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_171_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_171_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_171_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_173:
first_173_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_173_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_173_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_173_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_173_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_173_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_173_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_173_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_181:
first_181_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_181_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_181_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_181_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_181_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_181_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_181_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_181_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_182:
first_182_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_182_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_182_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_182_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_182_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_182_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_182_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_182_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_183:
first_183_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_183_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_183_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_183_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_183_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_183_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_183_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_183_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_187:
first_187_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_187_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_187_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_187_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_187_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_187_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_187_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_187_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_189:
first_189_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_189_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_189_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_189_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_189_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_189_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_189_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_189_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_190:
first_190_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_190_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_190_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_190_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_190_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_190_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_190_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_190_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_191:
first_191_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_191_pulse_1:
 DB 237,113
 LD A,H
 LD IYH,A
 NOP
first_191_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_191_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_191_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_191_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_191_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_191_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_202:
first_202_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_202_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_202_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_202_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_202_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_202_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_202_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_202_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_204:
first_204_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_204_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_204_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_204_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_204_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_204_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_204_pulse_6:
 DB 237,113
 LD L,(HL)
 XOR A
 LD SP,HL
first_204_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_205:
first_205_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_205_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_205_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_205_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_205_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_205_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_205_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_205_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_213:
first_213_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_213_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_213_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_213_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_213_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_213_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_213_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_213_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_214:
first_214_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_214_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_214_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_214_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_214_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_214_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_214_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_214_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_215:
first_215_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_215_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_215_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_215_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_215_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_215_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_215_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_215_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_218:
first_218_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_218_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_218_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_218_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_218_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_218_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_218_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_218_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_219:
first_219_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_219_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_219_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_219_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_219_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_219_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_219_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_219_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_221:
first_221_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_221_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_221_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_221_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_221_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_221_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_221_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_221_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_222:
first_222_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_222_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_222_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_222_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_222_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_222_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_222_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_222_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_223:
first_223_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_223_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_223_pulse_2:
 DB 237,113
 LD A,L
 LD IYL,A
 NOP
first_223_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_223_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_223_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_223_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_223_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_235:
first_235_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_235_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_235_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_235_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_235_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_235_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_235_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_235_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_237:
first_237_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_237_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_237_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_237_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_237_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_237_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_237_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_237_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_238:
first_238_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_238_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_238_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_238_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_238_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_238_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_238_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_238_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_239:
first_239_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_239_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_239_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_239_pulse_3:
 DB 237,113
 POP AF
 LD SP,HL
first_239_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_239_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_239_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_239_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_247:
first_247_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_247_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_247_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_247_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_247_pulse_4:
 DB 237,113
 LD IXL,A
 NOP
 NOP
first_247_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_247_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_247_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_251:
first_251_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_251_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_251_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_251_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_251_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_251_pulse_5:
 DB 237,113
 LD L,E
 LD H,D
 NOP
 NOP
first_251_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_251_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_253:
first_253_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_253_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_253_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_253_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_253_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_253_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_253_pulse_6:
 DB 237,113
 LD L,(HL)
 LD A,B
 LD SP,HL
first_253_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_254:
first_254_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_254_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_254_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_254_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_254_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_254_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_254_pulse_6:
 OUT (C),B
 LD L,(HL)
 XOR A
 LD SP,HL
first_254_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
first_255:
first_255_pulse_0:
 OUT (C),B
 POP HL
 INC DE
first_255_pulse_1:
 OUT (C),B
 LD A,H
 LD IYH,A
 NOP
first_255_pulse_2:
 OUT (C),B
 LD A,L
 LD IYL,A
 NOP
first_255_pulse_3:
 OUT (C),B
 POP AF
 LD SP,HL
first_255_pulse_4:
 OUT (C),B
 LD IXL,A
 NOP
 NOP
first_255_pulse_5:
 OUT (C),B
 LD L,E
 LD H,D
 NOP
 NOP
first_255_pulse_6:
 OUT (C),B
 LD L,(HL)
 LD A,B
 LD SP,HL
first_255_pulse_7:
 OUT (254),A
 NOP
 NOP
 JP (IY)
second_0:
second_0_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_0_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_0_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_0_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_0_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_0_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_0_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_0_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_2:
second_2_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_2_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_2_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_2_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_2_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_2_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_2_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_2_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_4:
second_4_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_4_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_4_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_4_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_4_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_4_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_4_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_4_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_8:
second_8_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_8_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_8_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_8_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_8_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_8_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_8_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_8_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_16:
second_16_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_16_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_16_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_16_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_16_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_16_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_16_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_16_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_17:
second_17_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_17_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_17_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_17_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_17_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_17_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_17_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_17_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_18:
second_18_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_18_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_18_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_18_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_18_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_18_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_18_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_18_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_32:
second_32_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_32_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_32_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_32_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_32_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_32_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_32_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_32_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_33:
second_33_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_33_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_33_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_33_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_33_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_33_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_33_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_33_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_34:
second_34_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_34_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_34_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_34_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_34_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_34_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_34_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_34_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_36:
second_36_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_36_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_36_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_36_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_36_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_36_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_36_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_36_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_37:
second_37_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_37_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_37_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_37_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_37_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_37_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_37_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_37_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_40:
second_40_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_40_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_40_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_40_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_40_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_40_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_40_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_40_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_41:
second_41_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_41_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_41_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_41_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_41_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_41_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_41_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_41_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_42:
second_42_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_42_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_42_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_42_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_42_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_42_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_42_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_42_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_50:
second_50_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_50_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_50_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_50_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_50_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_50_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_50_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_50_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_51:
second_51_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_51_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_51_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_51_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_51_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_51_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_51_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_51_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_53:
second_53_pulse_0:
 DB 237,113
 LD H,176
 XOR A
 LD SP,HL
second_53_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_53_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_53_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_53_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_53_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_53_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_53_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_64:
second_64_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_64_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_64_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_64_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_64_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_64_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_64_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_64_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_65:
second_65_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_65_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_65_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_65_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_65_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_65_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_65_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_65_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_66:
second_66_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_66_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_66_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_66_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_66_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_66_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_66_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_66_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_68:
second_68_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_68_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_68_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_68_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_68_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_68_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_68_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_68_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_72:
second_72_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_72_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_72_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_72_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_72_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_72_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_72_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_72_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_73:
second_73_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_73_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_73_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_73_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_73_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_73_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_73_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_73_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_74:
second_74_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_74_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_74_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_74_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_74_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_74_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_74_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_74_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_76:
second_76_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_76_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_76_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_76_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_76_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_76_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_76_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_76_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_82:
second_82_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_82_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_82_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_82_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_82_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_82_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_82_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_82_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_84:
second_84_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_84_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_84_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_84_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_84_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_84_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_84_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_84_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_85:
second_85_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_85_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_85_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_85_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_85_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_85_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_85_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_85_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_86:
second_86_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_86_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_86_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_86_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_86_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_86_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_86_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_86_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_89:
second_89_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_89_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_89_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_89_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_89_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_89_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_89_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_89_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_90:
second_90_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_90_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_90_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_90_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_90_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_90_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_90_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_90_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_91:
second_91_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_91_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_91_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_91_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_91_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_91_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_91_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_91_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_102:
second_102_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_102_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_102_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_102_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_102_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_102_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_102_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_102_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_106:
second_106_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_106_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_106_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_106_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_106_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_106_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_106_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_106_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_107:
second_107_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_107_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_107_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_107_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_107_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_107_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_107_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_107_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_109:
second_109_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_109_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_109_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_109_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_109_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_109_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_109_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_109_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_110:
second_110_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_110_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_110_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_110_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_110_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_110_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_110_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_110_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_118:
second_118_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_118_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_118_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_118_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_118_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_118_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_118_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_118_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_119:
second_119_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_119_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_119_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_119_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_119_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_119_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_119_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_119_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_123:
second_123_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_123_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_123_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_123_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_123_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_123_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_123_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_123_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_125:
second_125_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_125_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_125_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_125_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_125_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_125_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_125_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_125_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_126:
second_126_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_126_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_126_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_126_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_126_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_126_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_126_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_126_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_127:
second_127_pulse_0:
 DB 237,113
 LD H,176
 LD A,B
 LD SP,HL
second_127_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_127_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_127_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_127_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_127_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_127_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_127_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_128:
second_128_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_128_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_128_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_128_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_128_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_128_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_128_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_128_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_129:
second_129_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_129_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_129_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_129_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_129_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_129_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_129_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_129_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_130:
second_130_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_130_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_130_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_130_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_130_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_130_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_130_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_130_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_132:
second_132_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_132_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_132_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_132_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_132_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_132_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_132_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_132_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_136:
second_136_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_136_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_136_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_136_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_136_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_136_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_136_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_136_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_137:
second_137_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_137_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_137_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_137_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_137_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_137_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_137_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_137_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_145:
second_145_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_145_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_145_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_145_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_145_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_145_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_145_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_145_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_146:
second_146_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_146_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_146_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_146_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_146_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_146_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_146_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_146_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_148:
second_148_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_148_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_148_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_148_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_148_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_148_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_148_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_148_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_149:
second_149_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_149_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_149_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_149_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_149_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_149_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_149_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_149_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_153:
second_153_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_153_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_153_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_153_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_153_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_153_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_153_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_153_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_164:
second_164_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_164_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_164_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_164_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_164_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_164_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_164_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_164_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_165:
second_165_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_165_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_165_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_165_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_165_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_165_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_165_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_165_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_166:
second_166_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_166_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_166_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_166_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_166_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_166_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_166_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_166_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_169:
second_169_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_169_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_169_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_169_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_169_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_169_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_169_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_169_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_170:
second_170_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_170_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_170_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_170_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_170_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_170_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_170_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_170_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_171:
second_171_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_171_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_171_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_171_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_171_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_171_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_171_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_171_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_173:
second_173_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_173_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_173_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_173_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_173_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_173_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_173_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_173_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_179:
second_179_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_179_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_179_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_179_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_179_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_179_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_179_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_179_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_181:
second_181_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_181_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_181_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_181_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_181_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_181_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_181_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_181_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_182:
second_182_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_182_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_182_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_182_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_182_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_182_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_182_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_182_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_183:
second_183_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_183_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_183_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_183_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_183_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_183_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_183_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_183_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_187:
second_187_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_187_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_187_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_187_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_187_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_187_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_187_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_187_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_189:
second_189_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_189_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_189_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_189_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_189_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_189_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_189_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_189_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_190:
second_190_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_190_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_190_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_190_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_190_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_190_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_190_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_190_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_191:
second_191_pulse_0:
 OUT (C),B
 LD H,176
 XOR A
 LD SP,HL
second_191_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_191_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_191_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_191_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_191_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_191_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_191_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_202:
second_202_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_202_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_202_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_202_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_202_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_202_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_202_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_202_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_204:
second_204_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_204_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_204_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_204_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_204_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_204_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_204_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_204_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_205:
second_205_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_205_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_205_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_205_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_205_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_205_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_205_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_205_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_213:
second_213_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_213_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_213_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_213_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_213_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_213_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_213_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_213_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_214:
second_214_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_214_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_214_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_214_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_214_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_214_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_214_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_214_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_215:
second_215_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_215_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_215_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_215_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_215_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_215_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_215_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_215_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_218:
second_218_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_218_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_218_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_218_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_218_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_218_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_218_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_218_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_219:
second_219_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_219_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_219_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_219_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_219_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_219_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_219_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_219_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_221:
second_221_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_221_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_221_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_221_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_221_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_221_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_221_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_221_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_222:
second_222_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_222_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_222_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_222_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_222_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_222_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_222_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_222_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_223:
second_223_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_223_pulse_1:
 OUT (254),A
 LD H,(HL)
 XOR A
 LD SP,HL
second_223_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_223_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_223_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_223_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_223_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_223_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_237:
second_237_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_237_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_237_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_237_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_237_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_237_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_237_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_237_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_238:
second_238_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_238_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_238_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_238_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_238_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_238_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_238_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_238_pulse_7:
 DB 237,113
 NOP
 NOP
 NOP
 JP (HL)
second_239:
second_239_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_239_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_239_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_239_pulse_3:
 DB 237,113
 LD SP,HL
 POP HL
second_239_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_239_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_239_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_239_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_247:
second_247_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_247_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_247_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_247_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_247_pulse_4:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_247_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_247_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_247_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_251:
second_251_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_251_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_251_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_251_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_251_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_251_pulse_5:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_251_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_251_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_253:
second_253_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_253_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_253_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_253_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_253_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_253_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_253_pulse_6:
 DB 237,113
 NOP
 NOP
 NOP
 NOP
second_253_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
second_255:
second_255_pulse_0:
 OUT (C),B
 LD H,176
 LD A,B
 LD SP,HL
second_255_pulse_1:
 OUT (254),A
 LD H,(HL)
 LD A,B
 LD SP,HL
second_255_pulse_2:
 OUT (254),A
 LD A,IXL
 LD L,A
 NOP
second_255_pulse_3:
 OUT (C),B
 LD SP,HL
 POP HL
second_255_pulse_4:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_255_pulse_5:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_255_pulse_6:
 OUT (C),B
 NOP
 NOP
 NOP
 NOP
second_255_pulse_7:
 OUT (C),B
 NOP
 NOP
 NOP
 JP (HL)
kernel_end:
 NOP
