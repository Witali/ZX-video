; Full-input CPU probe: VQ7x512 (or predictive VQ7) -> PCM8 -> IMA nibbles.
; This is not a release player. Port01 is a test sink, not a sound output.
; IMA arithmetic is assembled from the separately maintained LPC prototype.
; It is identical to that baseline, allowing its cost to be measured directly.
; Alternate HL=vector, DE=input cursor, C=high index bits, B=predictor.
; IYH=samples left in vector, IYL=indices left in high-bit header.
        INCLUDE "vq-config.inc"
        ORG 0x8000
start:  DI
        LD SP,0x5FF0
        LD IX,first_segment_samples
        LD IY,0x0101
        LD A,19
        LD BC,0x7FFD
        OUT (C),A
        EXX
        LD DE,0xC000
        LD B,128
        EXX
sample_loop:
        CALL next_pcm
pcm_ready:
        CALL encode_ima
ima_ready:
        OUT (1),A
        DEC IX
        LD A,IXH
        OR IXL
        JP NZ,sample_loop
        LD A,(segments_left)
        DEC A
        LD (segments_left),A
        JP NZ,sample_loop    ; IX=0 deliberately counts another 65536 samples
        LD B,128
guard_loop:
        PUSH BC
        LD A,128
guard_pcm_ready:
        CALL encode_ima
guard_ima_ready:
        OUT (1),A
        POP BC
        DJNZ guard_loop
complete:
        JP complete

next_pcm:
        EXX
        DEC IYH
        JR NZ,have_vector
        LD IYH,7
        DEC IYL
        JR NZ,have_header
        CALL read_byte
        LD C,A
        LD IYL,8
have_header:
        CALL read_byte
        LD L,A
        LD H,0
        ADD HL,HL
        ADD HL,HL
        ADD HL,HL
        LD A,H
        OR 0x90
        LD H,A
        SRL C
        JR NC,low_half
        SET 3,H
low_half:
        IF predictive
        LD A,(last_pcm)
        SRL A
        ADD A,64
        LD B,A
        ENDIF
have_vector:
        LD A,(HL)
        INC L               ; seven values fit inside an aligned eight-byte row
        IF predictive
        ADD A,B             ; PC encoder rejects all overflowing vectors
        LD (last_pcm),A
        ENDIF
        EXX
        RET

read_byte:
        LD A,(DE)
        INC DE
        BIT 7,D
        RET NZ
        PUSH AF
        PUSH BC
        LD A,23
        LD BC,0x7FFD
        OUT (C),A
        LD DE,0xC000
        POP BC
        POP AF
        RET

        INCLUDE "ima-encoder.inc"
segments_left: DB segment_count
last_pcm: DB 128
ima_predictor: DW 32768
ima_index: DB 0
ima_code: DB 0
        ASSERT $ < 0x9000
        DS 0x9000-$
        MDAT "dictionary.bin"
        ASSERT $ == 0xA000
steps: MDAT "ima-steps.bin"
code_end:
