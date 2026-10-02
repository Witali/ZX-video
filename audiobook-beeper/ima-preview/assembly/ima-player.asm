; IMA ADPCM -> 16-bit predictor -> PCM8 -> live beeper PDM.
; Authoritative source: assemble this file with pyz80 1.3.0. Python supplies
; config.inc, decoder-table.bin and screen.bin, then packages player.bin.
; Example from the prepared assembly directory:
;   python -m pyz80.pyz80 --obj=player.bin --lstfile=player.lst -s .* ima-player.asm
;
; Playback register contract (interrupts DISABLED, no ROM calls):
;   Main BC=10FEh, D=current PCM8 level, E=PDM bit pipeline, HL=input pointer.
;   Alternate HL=IMA table row, BC=signed delta. EXX is used only for lookup
;   work, not around every PDM pulse. A'=PDM error; main AF=decoder scratch.
;   IX=unsigned biased predictor (signed PCM16+32768); IY=bank tail address.
;   SP=READ-ONLY TABLE CURSOR! No PUSH/CALL/RET or IRQ during playback.
;   Only the startup loader uses a real stack at 6000h (5F00..5FFF reserved).
;
; Table entry: [signed modular delta:word, next row|negative sign tag:word].
; 89*16*4=5696 bytes. Exact IMA-WAV shift/add rounding, independently checked
; against FFmpeg. A zero delta has a clear sign tag even for a negative code.
; BIT tests the tag before RES clears it; neither RES nor EXX changes flags.
; ADD IX preserves BIT's Z and supplies carry for unsigned saturation.
;
; Z80 timing (ULA and TR-DOS latency measured separately in Fuse):
; Low sample 439 T, high 437 T, average 438 T vs first IMA's 446 (-8 T).
; PDM kernel 40 T vs 48 (-8 T/pulse); PCM8 baseline used 32 T and 441 T/sample.
; Native output holds are 72..74 T normally, vs 56..81 before balancing.
; A 256-byte page adds one pulse /76 T; a bank adds five pulses /362 T.
; Both avoid a long gap. Rare bank-tail holds range 67..79 T.
; LD A,IXH is standard undocumented DD 7C, 8 T including prefix.

        INCLUDE "config.inc"
        ORG 0x8000

; 40 T total = 32-T modulator + 8 T to preserve decoder AF.
; Main BC/DE are already the PDM registers; no EXX in this hot macro.
; Carry is inserted into E bit 7, reaches EAR bit 4 three pulses later.
; Clearing bit 3 keeps MIC and border zero, independent of audio data.
PULSE: MACRO
        ASSERT \0 >= 0          ; also declares label parameter to pyz80
        EX AF,AF'               ; 4: select PDM accumulator
        ADD A,D                 ; 4: add PCM8, carry is the new PDM bit
        RR E                    ; 8: advance three-bit output pipeline
        RES 3,E                 ; 8: clear bits below EAR
\0:     OUT (C),E               ; 12: write EAR; label used by verification
        EX AF,AF'               ; 4: restore decoder flags exactly
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
ready:  LD HL,address_0
        EXX
        LD HL,tables+64*initial_index
        EXX
        LD IX,initial_predictor+32768
        LD IY,bank_tail_0

; Prime sample zero before the first output, using the same IMA recurrence.
        LD A,(HL)
        EXX
        AND 15
        RLCA
        RLCA
        OR L
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
        RES 0,L
        EXX
        LD A,IXH
        LD BC,0x10FE
        LD D,A
        LD E,0
        EX AF,AF'
        LD A,128
        EX AF,AF'
        JP high

; First four slots shared in structure, but distinct labels permit exact
; instruction-boundary capture. Each PULSE preserves all decoder flags.
DECODE_HEAD: MACRO
        PULSE \0_out0
        LD A,(HL)               ; 7+15+4+4+4 = 34 T, including EXX pair
        IF \1 == 0
        AND 15
        RLCA
        RLCA
        ELSE
        RRCA
        RRCA
        AND 60
        ENDIF
        EXX
        OR L
        EXX
        PULSE \0_out1
        EXX                     ; 4+4+6+10+4+4 = 32 T
        LD L,A
        LD SP,HL
        POP BC                  ; first half of table entry
        EXX
        NOP
        PULSE \0_out2
        EXX                     ; 4+10+8+8+4 = 34 T
        POP HL                  ; next row and sign
\0_state: BIT 0,L
        RES 0,L                 ; clear tag now, preserving BIT's Z
        EXX
        PULSE \0_out3
        EXX                     ; 4+15+4+10 = 33 T
        ADD IX,BC
        EXX
        JP NZ,\0_negative
        ENDM

; Low nibble holds [74,72,74,73,72,74] = 439 T.
low:    DECODE_HEAD low,0
low_positive:
        PULSE low_positive_out4
        JP C,low_positive_clip  ; saturation/no saturation both 24 T
        NOP
        JP low_positive_clipped
low_positive_clip:
        LD IX,65535
low_positive_clipped:
        NOP                     ; 24+8 = 32 T
        NOP
        PULSE low_positive_out5
        LD A,IXH                ; 8+4+12+10 = 34 T
        LD D,A
        JR low_positive_next
low_positive_next:
        JP high
low_negative:
        PULSE low_negative_out4
        JP NC,low_negative_clip
        NOP
        JP low_negative_clipped
low_negative_clip:
        LD IX,0
low_negative_clipped:
        NOP
        NOP
        PULSE low_negative_out5
        LD A,IXH
        LD D,A
        JR low_negative_next
low_negative_next:
        JP high

; High holds [74,72,74,73,72,72] = 437 T. Advance only after high nibble.
high:   DECODE_HEAD high,1
high_positive:
        PULSE high_positive_out4
        JP C,high_positive_clip
        NOP
        JP high_positive_clipped
high_positive_clip:
        LD IX,65535
high_positive_clipped:
        INC L                   ; 24+4+4 = 32 T
        NOP
        PULSE high_positive_out5
        JP NZ,high_positive_address_ok
        INC H
        JP Z,bank_dispatch
        JP page_finish          ; page path: 10+4+10+10 = 34 T
high_positive_address_ok:
        LD A,IXH                ; ordinary path: 10+8+4+10 = 32 T
        LD D,A
        JP low
high_negative:
        PULSE high_negative_out4
        JP NC,high_negative_clip
        NOP
        JP high_negative_clipped
high_negative_clip:
        LD IX,0
high_negative_clipped:
        INC L
        NOP
        PULSE high_negative_out5
        JP NZ,high_negative_address_ok
        INC H
        JP Z,bank_dispatch
        JP page_finish
high_negative_address_ok:
        LD A,IXH
        LD D,A
        JP low

; One extra slot per non-bank page boundary, preserving the current sample.
page_finish:
        PULSE page_out6
        LD A,IXH
        LD D,A
        JR page_next
page_next:
        JP low                  ; 8+4+12+10 = 34 T

bank_dispatch:
        JP (IY)                 ; total high slot 5: 10+4+10+8 = 32 T

; Main HL wrapped to zero. Only H needs loading for the next aligned bank.
; Bank holds [74,72,74,73,72,72,79,67,73,72,71] = 799 T.
BANK_TAIL: MACRO
bank_tail_\0: ASSERT \0 >= 0
        PULSE bank_\0_out6
        LD A,IXH                ; 8+13+4+10+4 = 39 T
        LD (bank_candidate),A
        EXX
        LD BC,0x7FFD             ; keep canonical paging port in scratch bank
        EXX
        PULSE bank_\0_out7
        EXX                     ; 4+7+12+4 = 27 T, leaving room for I/O delays
        LD A,\1+16
page_\0: OUT (C),A
        EXX
        PULSE bank_\0_out8
        LD H,\2 >> 8            ; 7+14+12 = 33 T; L remains zero
        LD IY,bank_tail_\3
        JR bank_next_\0
bank_next_\0: PULSE bank_\0_out9
        IF \0 == 7
        EXX                     ; 4+10+4+14 = 32 T; reset decoder only
        LD HL,tables+64*initial_index
        EXX
        LD IX,initial_predictor+32768
        ELSE
        NOP
        NOP
        NOP
        NOP
        NOP
        NOP
        NOP
        NOP
        ENDIF
        PULSE bank_\0_out10
        JP bank_finish          ; 10 T, remaining work is shared
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
bank_candidate: EQU $+1
        LD A,0
        LD D,A
        JP low                  ; tail slot 10 =10+7+4+10 =31 T (71 T hold)

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
