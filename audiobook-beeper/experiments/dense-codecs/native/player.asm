; CPU-only PVQ3x1024 feasibility probe, not a beeper player.
; Test port 01 emits complete PCM8 bytes to the native verification harness.
; Main PDM registers are untouched while the alternate set does the work.
; Alternate HL: current residual vector; DE: compressed cursor;
; B: unsigned predictor base; C: packed high-index fields.
; IXH: last PCM8 value; IYL: samples remaining; IYH: codes in header group.
        ORG 0x8000
start:  LD IX,0x8000
        LD IY,0x0101
        EXX
        LD DE,0xC000
        LD HL,0x9000
        LD B,128
        LD C,0
        EXX
next_sample:
        EXX
        DEC IYL
        JR NZ,have_vector
        LD IYL,3
        DEC IYH
        JR NZ,have_header
        LD A,(DE)
        INC DE
        LD C,A
        LD IYH,4
have_header:
        LD A,(DE)
        INC DE
        LD L,A
        LD H,0x88
        LD A,(HL)              ; low byte of four-byte dictionary record
        INC H
        LD H,(HL)              ; base 90 + the low index byte's upper two bits
        LD L,A
        LD A,C
        AND 3
        RLCA
        RLCA
        OR H
        LD H,A
        SRL C
        SRL C
        LD A,IXH
        SRL A
        ADD A,64               ; floor((last - 128)/2) + 128
        LD B,A
have_vector:
        LD A,(HL)
        INC L                  ; three consecutive signed-byte residuals
        ADD A,B                ; encoder proves there is no PCM8 overflow
        LD IXH,A
        EXX
sample_ready:
        OUT (1),A              ; test-only output, 11 T
        JP next_sample         ; test-only driver, 10 T
        ASSERT $ < 0x8800
        DS 0x8800-$
        MDAT "pointer-low.bin"
        MDAT "pointer-high.bin"
        DS 0x9000-$
        MDAT "dictionary.bin"
        ASSERT $ == 0xA000
