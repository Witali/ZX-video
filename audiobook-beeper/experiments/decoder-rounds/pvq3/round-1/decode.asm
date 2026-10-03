; PVQ3x512 half-last predictor: independent decoder CPU/buffer probe.
; Eight nine-bit indices = high-bit header (LSB first), then8 low bytes.
; Dictionary rows:3 signed residual bytes +1 guard; address9000+4*index.
; The PC rejects overflowing reconstructed samples, so ADD A,B is sufficient.
; R0: sample iterator + memory history. R1: IXH history. R2: address tables.
; R3: one dispatch per vector; store three PCM bytes and update history once.
; Test caller: mainDE output, mainBC sample/vector count; alternateDE input.
        INCLUDE "pvq-config.inc"
        ORG 0x8000
loop:   IF optimization < 3
        CALL next_sample
        LD (DE),A
        INC DE
        ELSE
        CALL next_vector
        ENDIF
        DEC BC
        LD A,B
        OR C
        JP NZ,loop
complete:
        JP complete

        IF optimization < 3
next_sample:
        EXX
        DEC IYH
        JR NZ,have_vector
        LD IYH,3
        ELSE
next_vector:
        EXX
        ENDIF
        DEC IYL
        JR NZ,have_header
        LD A,(DE)
        INC DE
        LD C,A
        LD IYL,8
have_header:
        LD A,(DE)
        INC DE
        LD L,A
        IF optimization < 2
        LD H,0
        ADD HL,HL
        ADD HL,HL
        LD A,H
        OR 0x90
        LD H,A
        ELSE
        LD H,0x88
        LD A,(HL)
        INC H
        LD H,(HL)
        LD L,A
        ENDIF
        SRL C
        JR NC,low_half
        SET 2,H
low_half:
        IF optimization == 0
        LD A,(last_pcm)
        ELSE
        LD A,IXH
        ENDIF
        SRL A
        ADD A,64
        LD B,A
have_vector:
        IF optimization < 3
        LD A,(HL)
        INC L
        ADD A,B
        IF optimization == 0
        LD (last_pcm),A
        ELSE
        LD IXH,A
        ENDIF
        EXX
        RET
        ELSE
        LD A,(HL)
        INC L
        ADD A,B
        EXX
        LD (DE),A
        INC DE
        EXX
        LD A,(HL)
        INC L
        ADD A,B
        EXX
        LD (DE),A
        INC DE
        EXX
        LD A,(HL)
        ADD A,B
        LD IXH,A
        EXX
        LD (DE),A
        INC DE
        RET
        ENDIF
last_pcm: DB 128
code_end:
        IF optimization >= 2
        DS 0x8800-$
        MDAT "pointer-low.bin"
        MDAT "pointer-high.bin"
        ENDIF
        DS 0x9000-$
        MDAT "dictionary.bin"
