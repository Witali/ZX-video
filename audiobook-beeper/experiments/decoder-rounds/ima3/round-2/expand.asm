; Expand MSB-first three-bit codes to the even IMA nibbles (code <<1).
; Eight source codes occupy3 bytes and become4 low-nibble-first IMA bytes.
; This special transport is bit-exact for the project's step6 ADPCM3.
; It is not the generic ADPCM-XQ / WAV three-bit format.
; Independent CPU benchmark: HL=inputC000, DE=output4000, IX=group count.
; Version0: bit loop; version1: unrolled extraction; version2: byte algebra;
; version3: four fixed256-byte lookup tables. All produce identical bytes.
        INCLUDE "expand-config.inc"
        ORG 0x8000
start:  DI
        LD SP,0xBFF0
        LD HL,0xC000
        LD DE,0x4000
        LD IX,groups
        LD B,1
group_loop:
        IF optimization < 2
        LD IYL,4
pair_loop:
        CALL code
        LD IYH,A
        CALL code
        RLCA
        RLCA
        RLCA
        RLCA
        OR IYH
        LD (DE),A
        INC DE
        DEC IYL
        JR NZ,pair_loop
        ELSE
        LD A,(HL)
        INC HL
        LD B,A
        LD A,(HL)
        INC HL
        LD C,A
        LD A,(HL)
        INC HL
        LD IYH,A
        IF optimization == 2
        LD A,B
        RRCA
        RRCA
        RRCA
        RRCA
        AND 0x0E
        LD IYL,A
        LD A,B
        RLCA
        RLCA
        RLCA
        AND 0xE0
        OR IYL
        LD (DE),A
        INC DE
        LD A,B
        AND 3
        RLCA
        RLCA
        LD B,A
        LD A,C
        RLCA
        AND 0xE0
        OR B
        LD B,A
        LD A,C
        RLCA
        RLCA
        AND 2
        OR B
        LD (DE),A
        INC DE
        LD A,C
        AND 14
        LD B,A
        LD A,C
        RRCA
        AND 128
        OR B
        LD B,A
        LD A,IYH
        RRCA
        AND 0x60
        OR B
        LD (DE),A
        INC DE
        LD A,IYH
        RRCA
        RRCA
        AND 14
        LD B,A
        LD A,IYH
        RRCA
        RRCA
        RRCA
        AND 0xE0
        OR B
        LD (DE),A
        INC DE
        ELSE
        PUSH HL
        LD L,B
        LD H,0x90
        LD A,(HL)
        LD (DE),A
        INC DE
        LD A,B
        AND 3
        RLCA
        RLCA
        LD B,A
        LD L,C
        INC H
        LD A,(HL)
        OR B
        LD (DE),A
        INC DE
        LD L,C
        INC H
        LD B,(HL)
        LD A,IYH
        RRCA
        AND 0x60
        OR B
        LD (DE),A
        INC DE
        LD A,IYH
        LD L,A
        INC H
        LD A,(HL)
        LD (DE),A
        INC DE
        POP HL
        ENDIF
        ENDIF
        DEC IX
        LD A,IXH
        OR IXL
        JP NZ,group_loop
complete:
        JP complete

        IF optimization < 2
code:   XOR A
        IF optimization == 0
        PUSH DE
        LD E,3
code_bit:
        CALL read_bit
        RLA
        DEC E
        JR NZ,code_bit
        POP DE
        ELSE
        CALL read_bit
        RLA
        CALL read_bit
        RLA
        CALL read_bit
        RLA
        ENDIF
        ADD A,A
        RET
read_bit:
        DEC B
        JR NZ,bit_ready
        LD C,(HL)
        INC HL
        LD B,8
bit_ready:
        SLA C
        RET
        ENDIF
code_end:
        IF optimization == 3
        DS 0x9000-$
        MDAT "lookup.bin"
        ENDIF
