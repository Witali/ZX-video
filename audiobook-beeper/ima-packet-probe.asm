; CPU-only packet-codebook probe. No loader, paging or buffer refill yet.
; Main BC: B=second output pattern, C=FE; D=16; E=next state *4.
; Main HL: dispatch/table cursor. Alternate HL: exact IMA row, BC: delta.
; IX: biased PCM16 predictor. IY: compressed input cursor.
; AF': alternating low/high nibble carry. SP reads ROM-like lookup data.
; Zero outputs use ED71, the NMOS Z80 OUT (C),0 instruction. This is
; assembled here explicitly because pyz80 does not accept its mnemonic.
; All instruction bytes are assembled here, never emitted by Python.
        INCLUDE "config.inc"
        ORG 0x8000

PULSE: MACRO
        IF \0
        OUT (C),D               ; 12 T, value 16
        ELSE
        DB 0xED,0x71            ; 12 T, OUT (C),0 on NMOS Z80
        ENDIF
        ENDM

IMMEDIATE: MACRO
        IF \0
        LD A,16                 ; 7 T
        ELSE
        LD A,0                  ; 7 T
        ENDIF
        OUT (0xFE),A            ; 11 T; alternate BC can hold IMA delta
        ENDM

FIRST: MACRO
        ASSERT $ == first_base + (\0)*first_stride
        PULSE ((\0)>>7) & 1
        EXX                     ; 4
        OR L                    ; 4: A already has nibble *4
        LD L,A                  ; 4
        LD SP,HL                ; 6
        IMMEDIATE ((\0)>>6) & 1
        POP BC                  ; 10: exact signed IMA delta
        IMMEDIATE ((\0)>>5) & 1
        POP HL                  ; 10: successor IMA row
        IMMEDIATE ((\0)>>4) & 1
        ADD IX,BC               ; 15: input is guarded against saturation
        EXX                     ; 4
        PULSE ((\0)>>3) & 1
        LD A,B                  ; 4: second eight-bit pattern
        LD L,A                  ; 4
        LD H,second_high >> 8    ; 7
        PULSE ((\0)>>2) & 1
        LD A,(HL)               ; 7
        INC H                   ; 4
        PULSE ((\0)>>1) & 1
        LD L,(HL)               ; 7
        LD H,A                  ; 4
        PULSE (\0) & 1
        JP (HL)                 ; 4
        ASSERT $ <= first_base + ((\0)+1)*first_stride
        DS first_base + ((\0)+1)*first_stride-$
        ENDM

first_base: EQU 0x8000
first_stride: EQU 40
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
        ASSERT $ == second_base + (\0)*second_stride
        PULSE ((\0)>>7) & 1
        LD A,IXH                ; 8
        LD L,A                  ; 4
        LD H,pcm_low >> 8       ; 7
        PULSE ((\0)>>6) & 1
        LD A,(HL)               ; 7
        OR E                    ; 4: state is already scaled by four
        PULSE ((\0)>>5) & 1
        INC H                   ; 4
        LD H,(HL)               ; 7
        LD L,A                  ; 4
        PULSE ((\0)>>4) & 1
        LD SP,HL                ; 6
        POP HL                  ; 10: first-pattern code pointer
        PULSE ((\0)>>3) & 1
        POP BC                  ; 10: B=second pattern, C=successor state
        LD E,C                  ; 4
        LD C,0xFE               ; 7: restore port before every output
        PULSE ((\0)>>2) & 1
        EX AF,AF'               ; 4
        CCF                     ; 4
        JP C,$+16               ; 10: equal-cost tail selection
; Low-nibble tail: 13 bytes, then the high-nibble tail at the JP target.
        PULSE ((\0)>>1) & 1
        EX AF,AF'               ; 4
        LD A,(IY+0)             ; 19
        PULSE (\0) & 1
        AND 15                  ; 7
        RLCA                    ; 4
        RLCA                    ; 4
        JP (HL)                 ; 4
        PULSE ((\0)>>1) & 1
        EX AF,AF'
        LD A,(IY+0)
        PULSE (\0) & 1
        AND 240
        RRCA
        RRCA
        INC IY                  ; 10, only after consuming the high nibble
        JP (HL)
        ASSERT $ <= second_base + ((\0)+1)*second_stride
        DS second_base + ((\0)+1)*second_stride-$
        ENDM

second_base: EQU 0xA800
second_stride: EQU 64
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
