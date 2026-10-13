; Optional startup-only AY/YM register-readback probe. Never called by the
; existing player. Call with interrupts disabled and channels muted: R1 is
; temporarily changed. Its old readable value is restored before returning.
; Output A=0 unknown/absent, A=1 AY-style, A=2 YM-style; clobbers F/BC/DE/HL.
; Leaves the register latch at R1. Normal AY/YM ports: FFFD select/read,
; BFFD write. This classifies readback behavior, not guaranteed silicon ID.
; The physical test requires 1Fh, not FFh: genuine YM parts can mask FFh.
        ORG 0x8000
probe_psg:
        LD BC,0xFFFD
        LD A,1
        OUT (C),A
        IN D,(C)
        ; Test used bits first, so a floating or stuck bus is not classified.
        LD B,0xBF
        XOR A
        OUT (C),A
        LD B,0xFF
        IN E,(C)
        LD B,0xBF
        LD A,0x0F
        OUT (C),A
        LD B,0xFF
        IN H,(C)
        LD B,0xBF
        LD A,0x1F
        OUT (C),A
        LD B,0xFF
        IN L,(C)
        ; Restore R1 even if any of the tests failed.
        LD B,0xBF
        OUT (C),D
        LD A,E
        OR A
        JR NZ,probe_unknown
        LD A,H
        CP 0x0F
        JR NZ,probe_unknown
        LD A,L
        CP 0x0F
        JR Z,probe_ay
        CP 0x1F
        JR Z,probe_ym
probe_unknown:
        XOR A
        RET
probe_ay:
        LD A,1
        RET
probe_ym:
        LD A,2
        RET
