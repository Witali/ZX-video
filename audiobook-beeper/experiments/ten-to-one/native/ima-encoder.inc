QUANTIZE: MACRO
        OR A
        SBC HL,DE
        JR C,quant_skip_\0
        PUSH HL
        LD H,B
        LD L,C
        ADD HL,DE
        LD B,H
        LD C,L
        POP HL
        LD A,(ima_code)
        OR \0
        LD (ima_code),A
        JR quant_done_\0
quant_skip_\0: ASSERT 1
        ADD HL,DE
quant_done_\0: ASSERT 1
        ENDM
encode_ima:
        LD H,A
        LD L,0
        LD DE,(ima_predictor)
        OR A
        SBC HL,DE
        LD A,0
        JR NC,ima_magnitude
        EX DE,HL
        LD HL,0
        OR A
        SBC HL,DE
        LD A,8
ima_magnitude:
        LD (ima_code),A
        PUSH HL
        LD A,(ima_index)
        ADD A,A
        LD L,A
        LD H,steps >> 8
        LD E,(HL)
        INC L
        LD D,(HL)
        LD B,D
        LD C,E
        SRL B
        RR C
        SRL B
        RR C
        SRL B
        RR C
        POP HL
        QUANTIZE 4
        SRL D
        RR E
        QUANTIZE 2
        SRL D
        RR E
        QUANTIZE 1
        LD HL,(ima_predictor)
        LD A,(ima_code)
        BIT 3,A
        JR Z,ima_add
        OR A
        SBC HL,BC
        JR ima_updated
ima_add:
        ADD HL,BC
ima_updated:
        LD (ima_predictor),HL
        LD A,(ima_code)
        AND 7
        CP 4
        LD A,(ima_index)
        JR NC,ima_index_up
        OR A
        JR Z,ima_index_ready
        DEC A
        JR ima_index_ready
ima_index_up:
        LD C,A
        LD A,(ima_code)
        AND 7
        SUB 3
        ADD A,A
        ADD A,C
        CP 89
        JR C,ima_index_ready
        LD A,88
ima_index_ready:
        LD (ima_index),A
        LD A,(ima_code)
        RET
