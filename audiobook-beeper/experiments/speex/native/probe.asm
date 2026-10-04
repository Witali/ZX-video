; Optimistic exact signed 16 x 16 multiplication for Speex's LPC synthesis.
; One operand has seven prepared 256-byte table planes. Table creation,
; coefficient changes, 32-bit accumulation and argument setup are excluded.
; Input H=first table page, L=low input byte, A=high input byte.
; Output B:D:E:C is the signed 32-bit product, most significant byte first.
; INC H preserves carry between the three byte additions.
        ORG 0x8000
start:  CALL multiply          ; 17 T, counted separately
stop:   NOP
multiply:
        LD C,(HL)             ; 7: product of unsigned low byte, byte 0
        INC H                 ; 4
        LD E,(HL)             ; 7: byte 1
        INC H                 ; 4
        LD D,(HL)             ; 7: byte 2
        INC H                 ; 4
        LD B,(HL)             ; 7: sign extension, byte 3
        LD L,A                ; 4: signed high-byte table index
        INC H                 ; 4
        LD A,(HL)             ; 7: high-byte contribution, byte 1
        ADD A,E               ; 4
        LD E,A                ; 4
        INC H                 ; 4
        LD A,(HL)             ; 7: byte 2
        ADC A,D               ; 4
        LD D,A                ; 4
        INC H                 ; 4
        LD A,(HL)             ; 7: byte 3
        ADC A,B               ; 4
        LD B,A                ; 4
        RET                   ; 10
; 7 reads * 7 + 6 increments * 4 + LD L,A 4 + 3 adds * 4
; + 3 result moves * 4 + RET 10 = 111 T (128 T with CALL).
