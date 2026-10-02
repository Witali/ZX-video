; IMA ADPCM -> 16-bit predictor -> PCM8 -> live beeper PDM.
; Authoritative source: assemble this file with pyz80 1.3.0. Python supplies
; config.inc, decoder-table.bin and screen.bin, then packages player.bin.
; Example from the prepared assembly directory:
;   python -m pyz80.pyz80 --obj=player.bin --lstfile=player.lst -s .* ima-player.asm
;
; Playback register contract (interrupts DISABLED, no ROM calls):
;   IX    unsigned biased predictor: signed PCM16 + 32768, saturated 0..65535.
;   HL    next 64-byte IMA row; lookup sets bit 0 to the delta sign, then
;         the final slot clears that tag before the next nibble lookup.
;   DE    packed input pointer; low nibble first, increment after high nibble.
;   BC/AF decoder scratch and canonical 7FFD paging port.
;   IY    current bank's tail routine (JP (IY), not CALL).
;   A'    modulo-256 PDM error; D' current PCM8 level; E' bit pipeline.
;   BC'   10FEh: even ULA port, uncontended high address on Spectrum 128.
;   SP    READ-ONLY TABLE CURSOR! No PUSH/CALL/RET or interrupts in playback.
;         The loader alone uses the real stack at 6000h (5F00..5FFF reserved).
;
; Each table entry is [signed modular delta:word, next-row|negative:word].
; 89 rows * 16 nibbles * 4 bytes = 5696 bytes. The delta uses the IMA-WAV /
; FFmpeg WAV shift/add rounding: (step>>3) plus step, step>>1 and step>>2
; selected by the magnitude's three bits. Each shift truncates. Negative zero
; has a CLEAR sign tag so that unsigned carry clipping handles it correctly.
;
; Timing below is Z80 CPU T-states, excluding ULA contention and disk ROM.
; Low nibble: 439 T; ordinary high: 453 T (892 T per packed byte).
; 256-byte input-page crossing: +14 T. Bank crossing: another +304 T.
; All output holds <=81 T natively; cold Fuse measures real ULA delays.
; Baseline PCM8: 441 T/sample and 10 pulses; IMA averages 446 T and 6 pulses.
; Moving tag clearing to the tail replaces AND 252 (7 T) with RES 0,L (8 T):
; +1 T/sample, but the contended input-read slot shrinks from 81 to 74 T.
; LD A,IXH uses the standard undocumented DD 7C instruction (8 T).

        INCLUDE "config.inc"
        ORG 0x8000

; 48 T total = 32-T modulator + 16 T to preserve decoder registers/flags.
; Carry is inserted into E' bit 7, reaches EAR bit 4 three pulses later.
; Clearing bit 3 keeps MIC and border zero, independent of audio data.
PULSE: MACRO
        ASSERT \0 >= 0          ; also declares label parameter to pyz80
        EXX                     ; 4: select BC'/DE'/HL'
        EX AF,AF'               ; 4: select PDM accumulator
        ADD A,D                 ; 4: add PCM8, carry is the new PDM bit
        RR E                    ; 8: advance three-bit output pipeline
        RES 3,E                 ; 8: clear bits below EAR
\0:     OUT (C),E               ; 12: write EAR; label used by verification
        EX AF,AF'               ; 4: restore decoder flags exactly
        EXX                     ; 4: restore decoder registers
        ENDM

; Publish candidate A as the next PCM level; preserve PDM A'/E'. 12 T.
TAKE_SAMPLE: MACRO
        EXX
        LD D,A
        EXX
        ENDM

; Loader-only macro. Full 7FFD port avoids aliases affecting 1FFD on +3.
LOAD_BANK: MACRO
        LD BC,0x7FFD
        LD A,\0+16
        OUT (C),A
        LD DE,\1                ; D=track, E=sector within track (0..15)
        LD (disk_position),DE
        LD HL,\2
        LD B,\3
        CALL read_n
        ENDM

SILENCE_AY: MACRO
        LD BC,0xFFFD
        LD A,\0
        OUT (C),A
        LD BC,0xBFFD
        XOR A
        OUT (C),A
        ENDM

start:  DI
        LD SP,0x6000
        LD IY,0x5C3A            ; ROM system variables during disk loading
        IM 1
        XOR A
        OUT (0xFE),A
        LD HL,screen_data       ; screen staging is reused for bank-2 audio
        LD DE,0x4000
        LD BC,6912
        LDIR
        EI
        LOAD_BANK 0, disk_0, address_0, sectors_0
        LOAD_BANK 4, disk_1, address_1, sectors_1
        LOAD_BANK 6, disk_2, address_2, sectors_2
        LOAD_BANK 1, disk_3, address_3, sectors_3
        LOAD_BANK 3, disk_4, address_4, sectors_4
        LOAD_BANK 7, disk_5, address_5, sectors_5
        LOAD_BANK 2, disk_6, address_6, sectors_6
        LOAD_BANK 5, disk_7, address_7, sectors_7
        DI
        SILENCE_AY 8
        SILENCE_AY 9
        SILENCE_AY 10
        LD BC,0x7FFD
        LD A,16
        OUT (C),A
        EI
        HALT                    ; one startup IRQ, then no IRQ/disk activity
        DI
ready:  LD DE,address_0
        LD HL,tables+64*initial_index
        LD IX,initial_predictor+32768
        LD IY,bank_tail_0

; Prime the first sample, without producing a dummy PCM value on the port.
; ADD IX preserves BIT's Z flag and supplies carry for unsigned saturation.
        LD A,(DE)
        AND 15
        RLCA
        RLCA
        OR L
        AND 252
        LD L,A
        LD SP,HL
        POP BC
        POP HL
        BIT 0,L
        ADD IX,BC
        JP NZ,prime_negative
        JP NC,prime_done
        LD IX,65535
        JP prime_done
prime_negative:
        JP C,prime_done
        LD IX,0
prime_done:
        RES 0,L                 ; prime has no PDM deadline; prepare clean row
        LD A,IXH
        EXX
        LD BC,0x10FE
        LD D,A
        LD E,0
        EX AF,AF'
        LD A,128
        EX AF,AF'
        EXX
        JP high                 ; output sample 0 while decoding sample 1

; Low nibble: six output holds [74,78,81,72,56,78] = 439 T.
low:    PULSE low_out0
        LD A,(DE)               ; address formation: 7+7+4+4+4 = 26 T
        AND 15
        RLCA
        RLCA
        OR L                    ; row low bits occupy bits 6..7
        PULSE low_out1
        LD L,A                  ; lookup: 4+6+10+10 = 30 T
        LD SP,HL
        POP BC                  ; signed modular delta
        POP HL                  ; next row plus sign tag
        PULSE low_out2
        BIT 0,L                 ; 8: Z selects sign, not predictor sign
        ADD IX,BC               ; 15: biased addition with carry
        JP NZ,low_negative      ; 10: same time taken or not taken
low_positive:
        PULSE low_positive_out3
        JP C,low_positive_clip  ; carry = positive overflow
        NOP                     ; both saturation paths take 24 T
        JP low_positive_clipped
low_positive_clip:
        LD IX,65535
low_positive_clipped:
        PULSE low_positive_out4
        LD A,IXH                ; 8: reduce to PCM8 only at the output
        PULSE low_positive_out5
        TAKE_SAMPLE
        RES 0,L                 ; 8: clear sign away from contended input read
        JP high                 ; 12+8+10 = 30 T
low_negative:
        PULSE low_negative_out3
        JP NC,low_negative_clip ; no carry = unsigned underflow
        NOP
        JP low_negative_clipped
low_negative_clip:
        LD IX,0
low_negative_clipped:
        PULSE low_negative_out4
        LD A,IXH
        PULSE low_negative_out5
        TAKE_SAMPLE
        RES 0,L
        JP high

; High nibble: [74,78,81,76,66,78] = 453 T, or +14 T at page rollover.
high:   PULSE high_out0
        LD A,(DE)               ; address formation: 7+4+4+7+4 = 26 T
        RRCA
        RRCA
        AND 60
        OR L
        PULSE high_out1
        LD L,A
        LD SP,HL
        POP BC
        POP HL
        PULSE high_out2
        BIT 0,L
        ADD IX,BC
        JP NZ,high_negative
high_positive:
        PULSE high_positive_out3
        JP C,high_positive_clip
        NOP
        JP high_positive_clipped
high_positive_clip:
        LD IX,65535
high_positive_clipped:
        INC E                   ; 4 T; PULSE preserves the rollover Z flag
        PULSE high_positive_out4
        JP NZ,high_positive_address_ok
        INC D                   ; page rollover: +4+10 = 14 T
        JP Z,bank_dispatch      ; C000..FFFF exhausted when DE wraps to zero
high_positive_address_ok:
        LD A,IXH
        PULSE high_positive_out5
        TAKE_SAMPLE
        RES 0,L
        JP low
high_negative:
        PULSE high_negative_out3
        JP NC,high_negative_clip
        NOP
        JP high_negative_clipped
high_negative_clip:
        LD IX,0
high_negative_clipped:
        INC E
        PULSE high_negative_out4
        JP NZ,high_negative_address_ok
        INC D
        JP Z,bank_dispatch
high_negative_address_ok:
        LD A,IXH
        PULSE high_negative_out5
        TAKE_SAMPLE
        RES 0,L
        JP low

bank_dispatch:
        JP (IY)                 ; 8 T, no stack use; preceding work totals 32 T

; Bank tail keeps the preceding PCM level for four extra PDM pulses.
; Holds: [74,78,81,76,80,79,74,80,72,77] = 771 T per boundary high nibble.
; 771 - 453 = 14 page overhead + 304 bank overhead. No long mute interval.
BANK_TAIL: MACRO
bank_tail_\0: ASSERT \0 >= 0
        PULSE bank_\0_out5
        LD A,IXH                ; 8+13+10 = 31 T
        LD (bank_candidate),A   ; retain last decoded sample across decoder reset
        LD BC,0x7FFD
        PULSE bank_\0_out6
        LD A,\1+16              ; 7+12+7 = 26 T; both OUTs may be contended
page_\0: OUT (C),A
        LD D,\2 >> 8            ; E is already zero after input pointer wrap
                                ; 7 T vs LD DE,nn 10 T: -3 T/bank transition
        PULSE bank_\0_out7
        LD IY,bank_tail_\3      ; 14+10+8 = 32 T, including tag clear below
        IF \0 == 7
        LD HL,tables+64*initial_index
        ELSE
        LD BC,0                 ; timing padding, scratch register
        ENDIF
        RES 0,L                 ; bank_finish has no room for this 8-T operation
        PULSE bank_\0_out8
        IF \0 == 7
        LD IX,initial_predictor+32768 ; reset IMA only; PDM error stays continuous
        ELSE
        LD A,0                  ; 7+7 = 14 T, preserve next IY target
        LD A,0
        ENDIF
        JP bank_finish          ; 14+10 = 24 T
        ENDM

        BANK_TAIL 0,4,address_1,1
        BANK_TAIL 1,6,address_2,2
        BANK_TAIL 2,1,address_3,3
        BANK_TAIL 3,3,address_4,4
        BANK_TAIL 4,7,address_5,5
        BANK_TAIL 5,2,address_6,6
        BANK_TAIL 6,5,address_7,7
        BANK_TAIL 7,0,address_0,0
bank_finish:
        PULSE bank_out9
bank_candidate: EQU $+1         ; only self-modified playback byte: LD immediate
        LD A,0
        TAKE_SAMPLE
        JP low                  ; 7+12+10 = 29 T

; Startup-only TR-DOS sector reader; this uses the real stack, before SP is
; repurposed. ROM/disk latency is excluded from the playback CPU counts.
read_n: PUSH BC
        PUSH HL
        LD DE,(disk_position)
        LD BC,0x0105            ; one sector, TR-DOS read function
disk_call:
        CALL 0x3D13
        POP HL
        POP BC
        INC H                   ; next 256-byte destination sector
        LD DE,(disk_position)
        INC E
        BIT 4,E
        JR Z,sector_ok
        LD E,0
        INC D
sector_ok:
        LD (disk_position),DE
        DJNZ read_n
        RET
disk_position:
        DW 0
code_end:
        ASSERT $ <= 0x8600      ; fail rather than overlap the read-only table
        DS 0x8600-$
tables: MDAT "decoder-table.bin"
        ASSERT $ == 0x9C40
        DS 0x9D00-$
screen_data:
        MDAT "screen.bin"
player_end:
        ASSERT $ == 0xB800      ; bank-2 audio starts at 9D00 (DD00 when paged)
