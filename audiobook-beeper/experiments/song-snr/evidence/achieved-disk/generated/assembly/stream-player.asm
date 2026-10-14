; Continuous IMA4/PDM player. Bank2 code/tables and bank5 lookup/workspace stay
; fixed. Audio begins in ordinary128K banks and continues directly through
; detected extended pages. Paging is the only live boundary work; no RAM copy.
; Main BC=00FE/10FE,D=16,E=feedback*6,HL dispatch,IX predictor,IY SECOND.
; Alternate HL=IMA row,BC delta,DE compressed cursor; AF' retains phase/code.
; SP is a lookup pointer during PDM and must never be used for live calls.
        INCLUDE "config.inc"
        ORG 0x8000
start:  JP stream_cold_start
ready:  LD IX,32768
        LD DE,(stream_first_address)
        LD A,(DE)
        AND 15
        RLCA
        RLCA
        LD HL,decoder_seed
        OR L
        LD L,A
        LD SP,HL
        POP BC
        POP HL
        ADD IX,BC
        EXX
        LD A,IXH
        LD L,A
        LD H,pcm_high >> 8
        LD H,(HL)
        LD L,initial_feedback_offset
        LD SP,HL
        POP HL
        POP IY
        POP DE
        LD BC,0x00FE
        SCF
        EX AF,AF'
        EXX
        LD A,(DE)
        AND 240
        RRCA
        RRCA
        INC DE
        EXX
        JP (HL)
; Enter with the alternate bank active, A already the extracted high nibble.
PAGE_TAIL: MACRO
page_tail_\0: ASSERT 1
        INC D
        JP Z,bank_handoff_\0
        EXX
        IF \0
        OUT (C),D
        ELSE
        DB 0xED,0x71
        ENDIF
        JP (HL)
bank_handoff_\0: ASSERT 1
        EX AF,AF'
        EXX
        LD B,\0*16              ; save last bit; 00FE/10FE are uncontended high bytes
        EXX
        JP bank_jump
        ENDM
        PAGE_TAIL 0
        PAGE_TAIL 1
bank_jump: JP stream_bank_tail
; The alternate bank is active here. AF' already holds the extracted code;
; alternate HL is still needed by the next decode, so save/restore it around
; the fixed-RAM descriptor walk. BC/DE are the usual paging/cursor scratches.
; A three-byte descriptor is paging byte,source high byte,Scorpion1FFD byte.
; Zero paging marks an exhausted RAM batch; only insufficient RAM reloads.
stream_bank_tail:
        LD (stream_tail_hl),HL
        LD HL,(stream_next_record)
        LD A,(HL)
        OR A
        JP Z,stream_exhausted
        LD (stream_paging),A
        INC HL
        LD D,(HL)
        LD E,0
        INC HL
        LD A,(HL)
        INC HL
        LD (stream_next_record),HL
        LD HL,(stream_tail_hl)
stream_high_switch:
        JP stream_high_done     ; Scorpion patches this to3 NOPs at cold boot
        LD BC,0x1FFD
        OUT (C),A
stream_high_done:
        LD BC,0x7FFD
        LD A,(stream_paging)
stream_page_event:
        OUT (C),A
        EXX
        SCF
        EX AF,AF'
        OUT (C),B               ; release the saved pulse after paging
        JP (HL)
startup_hot_end:
        IF compact_stream_loader
        ; Optional persistent loading helpers reuse fixed-bank2 startup
        ; padding. They remain callable at every insufficient-RAM refill.
        ; The bounce is mutable sector RAM, separately reserved after code;
        ; neither region overlaps the live startup/tail or FIRST dictionary.
stream_probe_start:
        INCLUDE "stream-probe.asm"
stream_probe_end:
stream_bounce: DEFS 256
        ENDIF
startup_end:
        ASSERT $ <= first_base
        DS first_base-$
PULSE: MACRO
        IF \0
        OUT (C),D
        ELSE
        DB 0xED,0x71
        ENDIF
        ENDM
IMMEDIATE: MACRO
        IF \0
        LD A,16
        ELSE
        LD A,0
        ENDIF
        OUT (0xFE),A
        ENDM
FIRST: MACRO
        IF first_address_\0 >= 0
        ASSERT $ == first_address_\0
        PULSE ((\0)>>7) & 1
        EXX
        OR L
        LD L,A
        LD SP,HL
        IMMEDIATE ((\0)>>6) & 1
        POP BC
        IMMEDIATE ((\0)>>5) & 1
        POP HL
        IMMEDIATE ((\0)>>4) & 1
        ADD IX,BC
        EXX
        PULSE ((\0)>>3) & 1
        LD A,IXH
        LD L,A
        PULSE ((\0)>>2) & 1
        LD H,pcm_high >> 8
        LD H,(HL)
        PULSE ((\0)>>1) & 1
        LD L,E
        LD SP,HL
        PULSE (\0) & 1
        JP (IY)
        IF extended_ram
        DEFB 0                  ; unreachable byte for a three-byte clone pacing JP
        ENDIF
        ASSERT $ == first_address_\0+first_size
        ENDIF
        ENDM
        FIRST 0
        FIRST 1
        FIRST 2
        FIRST 3
        FIRST 4
        FIRST 5
        FIRST 6
        FIRST 7
        FIRST 8
        FIRST 9
        FIRST 10
        FIRST 11
        FIRST 12
        FIRST 13
        FIRST 14
        FIRST 15
        FIRST 16
        FIRST 17
        FIRST 18
        FIRST 19
        FIRST 20
        FIRST 21
        FIRST 22
        FIRST 23
        FIRST 24
        FIRST 25
        FIRST 26
        FIRST 27
        FIRST 28
        FIRST 29
        FIRST 30
        FIRST 31
        FIRST 32
        FIRST 33
        FIRST 34
        FIRST 35
        FIRST 36
        FIRST 37
        FIRST 38
        FIRST 39
        FIRST 40
        FIRST 41
        FIRST 42
        FIRST 43
        FIRST 44
        FIRST 45
        FIRST 46
        FIRST 47
        FIRST 48
        FIRST 49
        FIRST 50
        FIRST 51
        FIRST 52
        FIRST 53
        FIRST 54
        FIRST 55
        FIRST 56
        FIRST 57
        FIRST 58
        FIRST 59
        FIRST 60
        FIRST 61
        FIRST 62
        FIRST 63
        FIRST 64
        FIRST 65
        FIRST 66
        FIRST 67
        FIRST 68
        FIRST 69
        FIRST 70
        FIRST 71
        FIRST 72
        FIRST 73
        FIRST 74
        FIRST 75
        FIRST 76
        FIRST 77
        FIRST 78
        FIRST 79
        FIRST 80
        FIRST 81
        FIRST 82
        FIRST 83
        FIRST 84
        FIRST 85
        FIRST 86
        FIRST 87
        FIRST 88
        FIRST 89
        FIRST 90
        FIRST 91
        FIRST 92
        FIRST 93
        FIRST 94
        FIRST 95
        FIRST 96
        FIRST 97
        FIRST 98
        FIRST 99
        FIRST 100
        FIRST 101
        FIRST 102
        FIRST 103
        FIRST 104
        FIRST 105
        FIRST 106
        FIRST 107
        FIRST 108
        FIRST 109
        FIRST 110
        FIRST 111
        FIRST 112
        FIRST 113
        FIRST 114
        FIRST 115
        FIRST 116
        FIRST 117
        FIRST 118
        FIRST 119
        FIRST 120
        FIRST 121
        FIRST 122
        FIRST 123
        FIRST 124
        FIRST 125
        FIRST 126
        FIRST 127
        FIRST 128
        FIRST 129
        FIRST 130
        FIRST 131
        FIRST 132
        FIRST 133
        FIRST 134
        FIRST 135
        FIRST 136
        FIRST 137
        FIRST 138
        FIRST 139
        FIRST 140
        FIRST 141
        FIRST 142
        FIRST 143
        FIRST 144
        FIRST 145
        FIRST 146
        FIRST 147
        FIRST 148
        FIRST 149
        FIRST 150
        FIRST 151
        FIRST 152
        FIRST 153
        FIRST 154
        FIRST 155
        FIRST 156
        FIRST 157
        FIRST 158
        FIRST 159
        FIRST 160
        FIRST 161
        FIRST 162
        FIRST 163
        FIRST 164
        FIRST 165
        FIRST 166
        FIRST 167
        FIRST 168
        FIRST 169
        FIRST 170
        FIRST 171
        FIRST 172
        FIRST 173
        FIRST 174
        FIRST 175
        FIRST 176
        FIRST 177
        FIRST 178
        FIRST 179
        FIRST 180
        FIRST 181
        FIRST 182
        FIRST 183
        FIRST 184
        FIRST 185
        FIRST 186
        FIRST 187
        FIRST 188
        FIRST 189
        FIRST 190
        FIRST 191
        FIRST 192
        FIRST 193
        FIRST 194
        FIRST 195
        FIRST 196
        FIRST 197
        FIRST 198
        FIRST 199
        FIRST 200
        FIRST 201
        FIRST 202
        FIRST 203
        FIRST 204
        FIRST 205
        FIRST 206
        FIRST 207
        FIRST 208
        FIRST 209
        FIRST 210
        FIRST 211
        FIRST 212
        FIRST 213
        FIRST 214
        FIRST 215
        FIRST 216
        FIRST 217
        FIRST 218
        FIRST 219
        FIRST 220
        FIRST 221
        FIRST 222
        FIRST 223
        FIRST 224
        FIRST 225
        FIRST 226
        FIRST 227
        FIRST 228
        FIRST 229
        FIRST 230
        FIRST 231
        FIRST 232
        FIRST 233
        FIRST 234
        FIRST 235
        FIRST 236
        FIRST 237
        FIRST 238
        FIRST 239
        FIRST 240
        FIRST 241
        FIRST 242
        FIRST 243
        FIRST 244
        FIRST 245
        FIRST 246
        FIRST 247
        FIRST 248
        FIRST 249
        FIRST 250
        FIRST 251
        FIRST 252
        FIRST 253
        FIRST 254
        FIRST 255

SECOND: MACRO
        IF second_address_\0 >= 0
        ASSERT $ == second_address_\0
        PULSE ((\0)>>7) & 1
        POP HL
        PULSE ((\0)>>6) & 1
        POP IY
        PULSE ((\0)>>5) & 1
        POP DE
        PULSE ((\0)>>4) & 1
        EX AF,AF'
        CCF
        JP C,$+26               ; skip the 23-byte low tail
        PULSE ((\0)>>3) & 1
        EX AF,AF'
        EXX
        LD A,(DE)
        EXX
        PULSE ((\0)>>2) & 1
        AND 15
        RLCA
        RLCA
        PULSE ((\0)>>1) & 1
        JP $+3
        NOP
        NOP
        NOP
        PULSE (\0) & 1
        JP (HL)
        PULSE ((\0)>>3) & 1
        EX AF,AF'
        EXX
        LD A,(DE)
        EXX
        PULSE ((\0)>>2) & 1
        AND 240
        RRCA
        RRCA
        PULSE ((\0)>>1) & 1
        EXX
        INC E
        IF (\0) & 1
        JP Z,page_tail_1
        ELSE
        JP Z,page_tail_0
        ENDIF
        EXX
        PULSE (\0) & 1
        JP (HL)
        ASSERT $ <= second_address_\0+64
        DS second_address_\0+64-$
        ENDIF
        ENDM
        SECOND 0
        SECOND 1
        SECOND 2
        SECOND 3
        SECOND 4
        SECOND 5
        SECOND 6
        SECOND 7
        SECOND 8
        SECOND 9
        SECOND 10
        SECOND 11
        SECOND 12
        SECOND 13
        SECOND 14
        SECOND 15
        SECOND 16
        SECOND 17
        SECOND 18
        SECOND 19
        SECOND 20
        SECOND 21
        SECOND 22
        SECOND 23
        SECOND 24
        SECOND 25
        SECOND 26
        SECOND 27
        SECOND 28
        SECOND 29
        SECOND 30
        SECOND 31
        SECOND 32
        SECOND 33
        SECOND 34
        SECOND 35
        SECOND 36
        SECOND 37
        SECOND 38
        SECOND 39
        SECOND 40
        SECOND 41
        SECOND 42
        SECOND 43
        SECOND 44
        SECOND 45
        SECOND 46
        SECOND 47
        SECOND 48
        SECOND 49
        SECOND 50
        SECOND 51
        SECOND 52
        SECOND 53
        SECOND 54
        SECOND 55
        SECOND 56
        SECOND 57
        SECOND 58
        SECOND 59
        SECOND 60
        SECOND 61
        SECOND 62
        SECOND 63
        SECOND 64
        SECOND 65
        SECOND 66
        SECOND 67
        SECOND 68
        SECOND 69
        SECOND 70
        SECOND 71
        SECOND 72
        SECOND 73
        SECOND 74
        SECOND 75
        SECOND 76
        SECOND 77
        SECOND 78
        SECOND 79
        SECOND 80
        SECOND 81
        SECOND 82
        SECOND 83
        SECOND 84
        SECOND 85
        SECOND 86
        SECOND 87
        SECOND 88
        SECOND 89
        SECOND 90
        SECOND 91
        SECOND 92
        SECOND 93
        SECOND 94
        SECOND 95
        SECOND 96
        SECOND 97
        SECOND 98
        SECOND 99
        SECOND 100
        SECOND 101
        SECOND 102
        SECOND 103
        SECOND 104
        SECOND 105
        SECOND 106
        SECOND 107
        SECOND 108
        SECOND 109
        SECOND 110
        SECOND 111
        SECOND 112
        SECOND 113
        SECOND 114
        SECOND 115
        SECOND 116
        SECOND 117
        SECOND 118
        SECOND 119
        SECOND 120
        SECOND 121
        SECOND 122
        SECOND 123
        SECOND 124
        SECOND 125
        SECOND 126
        SECOND 127
        SECOND 128
        SECOND 129
        SECOND 130
        SECOND 131
        SECOND 132
        SECOND 133
        SECOND 134
        SECOND 135
        SECOND 136
        SECOND 137
        SECOND 138
        SECOND 139
        SECOND 140
        SECOND 141
        SECOND 142
        SECOND 143
        SECOND 144
        SECOND 145
        SECOND 146
        SECOND 147
        SECOND 148
        SECOND 149
        SECOND 150
        SECOND 151
        SECOND 152
        SECOND 153
        SECOND 154
        SECOND 155
        SECOND 156
        SECOND 157
        SECOND 158
        SECOND 159
        SECOND 160
        SECOND 161
        SECOND 162
        SECOND 163
        SECOND 164
        SECOND 165
        SECOND 166
        SECOND 167
        SECOND 168
        SECOND 169
        SECOND 170
        SECOND 171
        SECOND 172
        SECOND 173
        SECOND 174
        SECOND 175
        SECOND 176
        SECOND 177
        SECOND 178
        SECOND 179
        SECOND 180
        SECOND 181
        SECOND 182
        SECOND 183
        SECOND 184
        SECOND 185
        SECOND 186
        SECOND 187
        SECOND 188
        SECOND 189
        SECOND 190
        SECOND 191
        SECOND 192
        SECOND 193
        SECOND 194
        SECOND 195
        SECOND 196
        SECOND 197
        SECOND 198
        SECOND 199
        SECOND 200
        SECOND 201
        SECOND 202
        SECOND 203
        SECOND 204
        SECOND 205
        SECOND 206
        SECOND 207
        SECOND 208
        SECOND 209
        SECOND 210
        SECOND 211
        SECOND 212
        SECOND 213
        SECOND 214
        SECOND 215
        SECOND 216
        SECOND 217
        SECOND 218
        SECOND 219
        SECOND 220
        SECOND 221
        SECOND 222
        SECOND 223
        SECOND 224
        SECOND 225
        SECOND 226
        SECOND 227
        SECOND 228
        SECOND 229
        SECOND 230
        SECOND 231
        SECOND 232
        SECOND 233
        SECOND 234
        SECOND 235
        SECOND 236
        SECOND 237
        SECOND 238
        SECOND 239
        SECOND 240
        SECOND 241
        SECOND 242
        SECOND 243
        SECOND 244
        SECOND 245
        SECOND 246
        SECOND 247
        SECOND 248
        SECOND 249
        SECOND 250
        SECOND 251
        SECOND 252
        SECOND 253
        SECOND 254
        SECOND 255

code_end:
        ASSERT $ <= pcm_high
        DS pcm_high-$
        MDAT "pcm-high.bin"
        MDAT "fixed-pages.bin"
        MDAT "decoder-extra.bin"
resident_end:
        ; Loading-only worker follows the complete universal dictionary.
        ; Its origin changes no live instruction, paging tail or SP lookup.
        ASSERT $ <= worker_origin
        IF compact_stream_loader
        ASSERT $ == worker_origin
        ENDIF
        DS worker_origin-$
        INCLUDE "stream-worker.asm"
player_end:
        ASSERT $ < 0xBFFF
        DS 0xBFFF-$
        DEFB 0
