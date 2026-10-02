; Register-only cost probe for one term of the RC-aware modulator.
; NOT a complete PDM kernel and NOT integrated into the Spectrum player.
; Input: HL=e, DE=older, signed fixed point. e-older must fit signed 16 bits.
; Output: HL=e+floor((e-older)/2), DE=previous e, BC=previous e.
; This is damped feedback (b=0.5). RC update/quantizer/output are excluded.
; BC/DE are occupied in the real player; allocation/save costs are excluded.
; Baseline has no such extrapolation: 0 T -> 62 T for this direct sequence.
        ORG 0x8000
start:  LD B,H                  ; 4: retain e
        LD C,L                  ; 4
        OR A                    ; 4: clear borrow, regardless of A
        SBC HL,DE               ; 15: e-older
        SRA H                   ; 8: signed division by two
        RR L                    ; 8
        ADD HL,BC               ; 11: add original e
        LD D,B                  ; 4: retain original e for the next slot
        LD E,C                  ; 4
done:   NOP                     ; excluded from the 62-T measurement
