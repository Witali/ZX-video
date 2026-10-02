; CPU-only feasibility probe, NOT a bootable player or replacement TRD.
; Assemble externally with pyz80; config.inc selects 8/9/10 slots and padding.
; Input blocks must stay inside a 256-byte page. No bank/page/loop tails here.
; Caller MUST prove that every predictor addition fits signed PCM16. The
; general player still needs saturation; this probe deliberately omits it.
;
; Main A=PDM error (unlike ima-player.asm), AF'=scratch, BC=10FEh,
; D=previous PCM8, E=three-slot PDM pipeline, HL=packed input.
; Alternate HL=untagged next table row, BC=delta; IX=biased predictor.
; SP is a read-only table cursor, interrupts disabled, no stack operations.
; LD D,IXH is undocumented DD 54, measured as 8 T by the native Z80 core.
;
; Unpadded low/high: 393/407 T at 8 slots (mean 400 vs baseline 438).
; Each additional slot adds 32 T. Balanced 8-slot low/high: both 437 T.
; Counts exclude ULA, page/bank transitions and startup/disk activity.
        INCLUDE "config.inc"
        ORG 0x8000

FAST:   MACRO
        ASSERT \0 >= 0
        ADD A,D                 ; 4: error/carry update
        RR E                    ; 8: carry reaches EAR three slots later
        RES 3,E                 ; 8: keep MIC/border zero
\0:     OUT (C),E               ; 12: total 32 T
        ENDM

SAVED:  MACRO
        ASSERT \0 >= 0
        EX AF,AF'               ; 4: one slot still needs saved decoder A
        FAST \0
        EX AF,AF'               ; 4: total 40 T
        ENDM

HALF:   MACRO
        FAST \0_out0
        EX AF,AF'
        LD A,(HL)
        IF \1 == 0
        AND 15
        RLCA
        ELSE
        AND 240
        RRCA
        ENDIF
        SAVED \0_out1
        IF \1 == 0
        RLCA
        ELSE
        RRCA
        ENDIF
        EXX
        OR L
        LD L,A
        EXX
        EX AF,AF'               ; PDM error stays in main A from here
        FAST \0_out2
        EXX
        LD SP,HL
        POP BC
        EXX
        FAST \0_out3
        EXX
        POP HL                  ; clean row pointer, no sign tag
        EXX
        FAST \0_out4
        EXX
        ADD IX,BC               ; flags disposable under no-overflow guard
        EXX
        FAST \0_out5
        IF balanced == 1
        NOP
        NOP
        NOP
        NOP
        NOP
        ENDIF
        FAST \0_out6
        IF \1 == 1
        INC L
        JP Z,page_trap          ; ordinary path only; flags consumed now
        ENDIF
        IF balanced == 1
        IF \1 == 0
        NOP
        NOP
        NOP
        NOP
        NOP
        NOP
        ELSE
        JP \0_pad_end
\0_pad_end: ASSERT 1
        ENDIF
        ENDIF
        IF slots >= 9
        FAST \0_extra8
        ENDIF
        IF slots >= 10
        FAST \0_extra9
        ENDIF
        FAST \0_out7
        LD D,IXH                ; 8 vs LD A,IXH / LD D,A = 12; preserves A
        ENDM

low:    HALF low,0
        JP high
high:   HALF high,1
        JP low
page_trap:
        HALT                    ; deliberately excluded from probe scope
        JP page_trap
code_end:
