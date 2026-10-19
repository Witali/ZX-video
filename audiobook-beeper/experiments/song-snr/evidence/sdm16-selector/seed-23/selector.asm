; Full-input model-B selector component, standalone CPU evidence only.
; Enter after SECOND dispatch, where old IY is dead; main A/F/HL scratch.
; IX retains all16 predictor bits. BC remains the output port, D16/E state.
; E is newly encoded as0x40+2*raw_state, selecting two parallel root pages.
; Alternate decoder/source registers and AF' are untouched. No CALL/PUSH.
; The component is flat native RAM: real paging/ULA/boot are not implemented.
 ORG 0x8000
selector:
 LD A,IXH
 LD L,A
 LD H,E
 LD A,(HL)
 INC H
 LD H,(HL)
 LD L,A
 JP (HL)
selector_root_end:
 DS 0x8100-$
handlers:
group_0:
 LD A,IXL
group_0_search:
 CP 1
 JP C,group_0_search_left
group_0_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45374
 POP HL
 POP IY
 POP DE
 JP complete
group_0_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45368
 POP HL
 POP IY
 POP DE
 JP complete
group_1:
 LD A,IXL
group_1_search:
 CP 2
 JP C,group_1_search_left
group_1_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45878
 POP HL
 POP IY
 POP DE
 JP complete
group_1_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45872
 POP HL
 POP IY
 POP DE
 JP complete
group_2:
 LD A,IXL
group_2_search:
 CP 3
 JP C,group_2_search_left
group_2_search_right:
 CP 42
 JP C,group_2_search_right_left
group_2_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45830
 POP HL
 POP IY
 POP DE
 JP complete
group_2_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45824
 POP HL
 POP IY
 POP DE
 JP complete
group_2_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45818
 POP HL
 POP IY
 POP DE
 JP complete
group_3:
 LD A,IXL
group_3_search:
 CP 95
 JP C,group_3_search_left
group_3_search_right:
 CP 130
 JP C,group_3_search_right_left
group_3_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46556
 POP HL
 POP IY
 POP DE
 JP complete
group_3_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46550
 POP HL
 POP IY
 POP DE
 JP complete
group_3_search_left:
 CP 4
 JP C,group_3_search_left_left
group_3_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,46544
 POP HL
 POP IY
 POP DE
 JP complete
group_3_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,46538
 POP HL
 POP IY
 POP DE
 JP complete
group_4:
 LD A,IXL
group_4_search:
 CP 5
 JP C,group_4_search_left
group_4_search_right:
 CP 141
 JP C,group_4_search_right_left
group_4_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45998
 POP HL
 POP IY
 POP DE
 JP complete
group_4_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45992
 POP HL
 POP IY
 POP DE
 JP complete
group_4_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45986
 POP HL
 POP IY
 POP DE
 JP complete
group_5:
 LD A,IXL
group_5_search:
 CP 10
 JP C,group_5_search_left
group_5_search_right:
 CP 100
 JP C,group_5_search_right_left
group_5_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46076
 POP HL
 POP IY
 POP DE
 JP complete
group_5_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46070
 POP HL
 POP IY
 POP DE
 JP complete
group_5_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46064
 POP HL
 POP IY
 POP DE
 JP complete
group_6:
 LD A,IXL
group_6_search:
 CP 13
 JP C,group_6_search_left
group_6_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45986
 POP HL
 POP IY
 POP DE
 JP complete
group_6_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45980
 POP HL
 POP IY
 POP DE
 JP complete
group_7:
 LD A,IXL
group_7_search:
 CP 139
 JP C,group_7_search_left
group_7_search_right:
 CP 176
 JP C,group_7_search_right_left
group_7_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45896
 POP HL
 POP IY
 POP DE
 JP complete
group_7_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45890
 POP HL
 POP IY
 POP DE
 JP complete
group_7_search_left:
 CP 14
 JP C,group_7_search_left_left
group_7_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45884
 POP HL
 POP IY
 POP DE
 JP complete
group_7_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45878
 POP HL
 POP IY
 POP DE
 JP complete
group_8:
 LD A,IXL
group_8_search:
 CP 15
 JP C,group_8_search_left
group_8_search_right:
 CP 210
 JP C,group_8_search_right_left
group_8_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45356
 POP HL
 POP IY
 POP DE
 JP complete
group_8_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45350
 POP HL
 POP IY
 POP DE
 JP complete
group_8_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45344
 POP HL
 POP IY
 POP DE
 JP complete
group_9:
 LD A,IXL
group_9_search:
 CP 16
 JP C,group_9_search_left
group_9_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46376
 POP HL
 POP IY
 POP DE
 JP complete
group_9_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46370
 POP HL
 POP IY
 POP DE
 JP complete
group_10:
 LD A,IXL
group_10_search:
 CP 16
 JP C,group_10_search_left
group_10_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46670
 POP HL
 POP IY
 POP DE
 JP complete
group_10_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46664
 POP HL
 POP IY
 POP DE
 JP complete
group_11:
 LD A,IXL
group_11_search:
 CP 17
 JP C,group_11_search_left
group_11_search_right:
 CP 119
 JP C,group_11_search_right_left
group_11_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46232
 POP HL
 POP IY
 POP DE
 JP complete
group_11_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46226
 POP HL
 POP IY
 POP DE
 JP complete
group_11_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46220
 POP HL
 POP IY
 POP DE
 JP complete
group_12:
 LD A,IXL
group_12_search:
 CP 18
 JP C,group_12_search_left
group_12_search_right:
 CP 196
 JP C,group_12_search_right_left
group_12_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45176
 POP HL
 POP IY
 POP DE
 JP complete
group_12_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45170
 POP HL
 POP IY
 POP DE
 JP complete
group_12_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45164
 POP HL
 POP IY
 POP DE
 JP complete
group_13:
 LD A,IXL
group_13_search:
 CP 18
 JP C,group_13_search_left
group_13_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45242
 POP HL
 POP IY
 POP DE
 JP complete
group_13_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45236
 POP HL
 POP IY
 POP DE
 JP complete
group_14:
 LD A,IXL
group_14_search:
 CP 18
 JP C,group_14_search_left
group_14_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45248
 POP HL
 POP IY
 POP DE
 JP complete
group_14_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45242
 POP HL
 POP IY
 POP DE
 JP complete
group_15:
 LD A,IXL
group_15_search:
 CP 19
 JP C,group_15_search_left
group_15_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46682
 POP HL
 POP IY
 POP DE
 JP complete
group_15_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46676
 POP HL
 POP IY
 POP DE
 JP complete
group_16:
 LD A,IXL
group_16_search:
 CP 22
 JP C,group_16_search_left
group_16_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46430
 POP HL
 POP IY
 POP DE
 JP complete
group_16_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46424
 POP HL
 POP IY
 POP DE
 JP complete
group_17:
 LD A,IXL
group_17_search:
 CP 23
 JP C,group_17_search_left
group_17_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45116
 POP HL
 POP IY
 POP DE
 JP complete
group_17_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45110
 POP HL
 POP IY
 POP DE
 JP complete
group_18:
 LD A,IXL
group_18_search:
 CP 36
 JP C,group_18_search_left
group_18_search_right:
 CP 90
 JP C,group_18_search_right_left
group_18_search_right_right:
 CP 228
 JP C,group_18_search_right_right_left
group_18_search_right_right_right:
 LD SP,45140
 POP HL
 POP IY
 POP DE
 JP complete
group_18_search_right_right_left:
 LD SP,45134
 POP HL
 POP IY
 POP DE
 JP complete
group_18_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45128
 POP HL
 POP IY
 POP DE
 JP complete
group_18_search_left:
 CP 23
 JP C,group_18_search_left_left
group_18_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45122
 POP HL
 POP IY
 POP DE
 JP complete
group_18_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45116
 POP HL
 POP IY
 POP DE
 JP complete
group_19:
 LD A,IXL
group_19_search:
 CP 26
 JP C,group_19_search_left
group_19_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46100
 POP HL
 POP IY
 POP DE
 JP complete
group_19_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46094
 POP HL
 POP IY
 POP DE
 JP complete
group_20:
 LD A,IXL
group_20_search:
 CP 26
 JP C,group_20_search_left
group_20_search_right:
 CP 194
 JP C,group_20_search_right_left
group_20_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46112
 POP HL
 POP IY
 POP DE
 JP complete
group_20_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46106
 POP HL
 POP IY
 POP DE
 JP complete
group_20_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46100
 POP HL
 POP IY
 POP DE
 JP complete
group_21:
 LD A,IXL
group_21_search:
 CP 28
 JP C,group_21_search_left
group_21_search_right:
 CP 43
 JP C,group_21_search_right_left
group_21_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45260
 POP HL
 POP IY
 POP DE
 JP complete
group_21_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45254
 POP HL
 POP IY
 POP DE
 JP complete
group_21_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45248
 POP HL
 POP IY
 POP DE
 JP complete
group_22:
 LD A,IXL
group_22_search:
 CP 28
 JP C,group_22_search_left
group_22_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46484
 POP HL
 POP IY
 POP DE
 JP complete
group_22_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46478
 POP HL
 POP IY
 POP DE
 JP complete
group_23:
 LD A,IXL
group_23_search:
 CP 56
 JP C,group_23_search_left
group_23_search_right:
 CP 100
 JP C,group_23_search_right_left
group_23_search_right_right:
 CP 209
 JP C,group_23_search_right_right_left
group_23_search_right_right_right:
 LD SP,46508
 POP HL
 POP IY
 POP DE
 JP complete
group_23_search_right_right_left:
 LD SP,46502
 POP HL
 POP IY
 POP DE
 JP complete
group_23_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46496
 POP HL
 POP IY
 POP DE
 JP complete
group_23_search_left:
 CP 28
 JP C,group_23_search_left_left
group_23_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,46490
 POP HL
 POP IY
 POP DE
 JP complete
group_23_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,46484
 POP HL
 POP IY
 POP DE
 JP complete
group_24:
 LD A,IXL
group_24_search:
 CP 29
 JP C,group_24_search_left
group_24_search_right:
 CP 30
 JP C,group_24_search_right_left
group_24_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46532
 POP HL
 POP IY
 POP DE
 JP complete
group_24_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46526
 POP HL
 POP IY
 POP DE
 JP complete
group_24_search_left:
 CP 28
 JP C,group_24_search_left_left
group_24_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,46520
 POP HL
 POP IY
 POP DE
 JP complete
group_24_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,46514
 POP HL
 POP IY
 POP DE
 JP complete
group_25:
 LD A,IXL
group_25_search:
 CP 28
 JP C,group_25_search_left
group_25_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46712
 POP HL
 POP IY
 POP DE
 JP complete
group_25_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46706
 POP HL
 POP IY
 POP DE
 JP complete
group_26:
 LD A,IXL
group_26_search:
 CP 44
 JP C,group_26_search_left
group_26_search_right:
 CP 220
 JP C,group_26_search_right_left
group_26_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45596
 POP HL
 POP IY
 POP DE
 JP complete
group_26_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45590
 POP HL
 POP IY
 POP DE
 JP complete
group_26_search_left:
 CP 29
 JP C,group_26_search_left_left
group_26_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45584
 POP HL
 POP IY
 POP DE
 JP complete
group_26_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45578
 POP HL
 POP IY
 POP DE
 JP complete
group_27:
 LD A,IXL
group_27_search:
 CP 30
 JP C,group_27_search_left
group_27_search_right:
 CP 185
 JP C,group_27_search_right_left
group_27_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46358
 POP HL
 POP IY
 POP DE
 JP complete
group_27_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46352
 POP HL
 POP IY
 POP DE
 JP complete
group_27_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46346
 POP HL
 POP IY
 POP DE
 JP complete
group_28:
 LD A,IXL
group_28_search:
 CP 30
 JP C,group_28_search_left
group_28_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46538
 POP HL
 POP IY
 POP DE
 JP complete
group_28_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46532
 POP HL
 POP IY
 POP DE
 JP complete
group_29:
 LD A,IXL
group_29_search:
 CP 32
 JP C,group_29_search_left
group_29_search_right:
 CP 237
 JP C,group_29_search_right_left
group_29_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46160
 POP HL
 POP IY
 POP DE
 JP complete
group_29_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46154
 POP HL
 POP IY
 POP DE
 JP complete
group_29_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46148
 POP HL
 POP IY
 POP DE
 JP complete
group_30:
 LD A,IXL
group_30_search:
 CP 166
 JP C,group_30_search_left
group_30_search_right:
 CP 215
 JP C,group_30_search_right_left
group_30_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45482
 POP HL
 POP IY
 POP DE
 JP complete
group_30_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45476
 POP HL
 POP IY
 POP DE
 JP complete
group_30_search_left:
 CP 34
 JP C,group_30_search_left_left
group_30_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45470
 POP HL
 POP IY
 POP DE
 JP complete
group_30_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45464
 POP HL
 POP IY
 POP DE
 JP complete
group_31:
 LD A,IXL
group_31_search:
 CP 34
 JP C,group_31_search_left
group_31_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46400
 POP HL
 POP IY
 POP DE
 JP complete
group_31_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46394
 POP HL
 POP IY
 POP DE
 JP complete
group_32:
 LD A,IXL
group_32_search:
 CP 36
 JP C,group_32_search_left
group_32_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45728
 POP HL
 POP IY
 POP DE
 JP complete
group_32_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45722
 POP HL
 POP IY
 POP DE
 JP complete
group_33:
 LD A,IXL
group_33_search:
 CP 37
 JP C,group_33_search_left
group_33_search_right:
 CP 48
 JP C,group_33_search_right_left
group_33_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46250
 POP HL
 POP IY
 POP DE
 JP complete
group_33_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46244
 POP HL
 POP IY
 POP DE
 JP complete
group_33_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46238
 POP HL
 POP IY
 POP DE
 JP complete
group_34:
 LD A,IXL
group_34_search:
 CP 38
 JP C,group_34_search_left
group_34_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45458
 POP HL
 POP IY
 POP DE
 JP complete
group_34_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45452
 POP HL
 POP IY
 POP DE
 JP complete
group_35:
 LD A,IXL
group_35_search:
 CP 38
 JP C,group_35_search_left
group_35_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45902
 POP HL
 POP IY
 POP DE
 JP complete
group_35_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45896
 POP HL
 POP IY
 POP DE
 JP complete
group_36:
 LD A,IXL
group_36_search:
 CP 39
 JP C,group_36_search_left
group_36_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46382
 POP HL
 POP IY
 POP DE
 JP complete
group_36_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46376
 POP HL
 POP IY
 POP DE
 JP complete
group_37:
 LD A,IXL
group_37_search:
 CP 40
 JP C,group_37_search_left
group_37_search_right:
 CP 189
 JP C,group_37_search_right_left
group_37_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45914
 POP HL
 POP IY
 POP DE
 JP complete
group_37_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45908
 POP HL
 POP IY
 POP DE
 JP complete
group_37_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45902
 POP HL
 POP IY
 POP DE
 JP complete
group_38:
 LD A,IXL
group_38_search:
 CP 40
 JP C,group_38_search_left
group_38_search_right:
 CP 117
 JP C,group_38_search_right_left
group_38_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45926
 POP HL
 POP IY
 POP DE
 JP complete
group_38_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45920
 POP HL
 POP IY
 POP DE
 JP complete
group_38_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45914
 POP HL
 POP IY
 POP DE
 JP complete
group_39:
 LD A,IXL
group_39_search:
 CP 41
 JP C,group_39_search_left
group_39_search_right:
 CP 69
 JP C,group_39_search_right_left
group_39_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46262
 POP HL
 POP IY
 POP DE
 JP complete
group_39_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46256
 POP HL
 POP IY
 POP DE
 JP complete
group_39_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46250
 POP HL
 POP IY
 POP DE
 JP complete
group_40:
 LD A,IXL
group_40_search:
 CP 41
 JP C,group_40_search_left
group_40_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46646
 POP HL
 POP IY
 POP DE
 JP complete
group_40_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46640
 POP HL
 POP IY
 POP DE
 JP complete
group_41:
 LD A,IXL
group_41_search:
 CP 42
 JP C,group_41_search_left
group_41_search_right:
 CP 114
 JP C,group_41_search_right_left
group_41_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45842
 POP HL
 POP IY
 POP DE
 JP complete
group_41_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45836
 POP HL
 POP IY
 POP DE
 JP complete
group_41_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45830
 POP HL
 POP IY
 POP DE
 JP complete
group_42:
 LD A,IXL
group_42_search:
 CP 43
 JP C,group_42_search_left
group_42_search_right:
 CP 72
 JP C,group_42_search_right_left
group_42_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45188
 POP HL
 POP IY
 POP DE
 JP complete
group_42_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45182
 POP HL
 POP IY
 POP DE
 JP complete
group_42_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45176
 POP HL
 POP IY
 POP DE
 JP complete
group_43:
 LD A,IXL
group_43_search:
 CP 44
 JP C,group_43_search_left
group_43_search_right:
 CP 74
 JP C,group_43_search_right_left
group_43_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46442
 POP HL
 POP IY
 POP DE
 JP complete
group_43_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46436
 POP HL
 POP IY
 POP DE
 JP complete
group_43_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46430
 POP HL
 POP IY
 POP DE
 JP complete
group_44:
 LD A,IXL
group_44_search:
 CP 46
 JP C,group_44_search_left
group_44_search_right:
 CP 229
 JP C,group_44_search_right_left
group_44_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46328
 POP HL
 POP IY
 POP DE
 JP complete
group_44_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46322
 POP HL
 POP IY
 POP DE
 JP complete
group_44_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46316
 POP HL
 POP IY
 POP DE
 JP complete
group_45:
 LD A,IXL
group_45_search:
 CP 46
 JP C,group_45_search_left
group_45_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46754
 POP HL
 POP IY
 POP DE
 JP complete
group_45_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46748
 POP HL
 POP IY
 POP DE
 JP complete
group_46:
 LD A,IXL
group_46_search:
 CP 47
 JP C,group_46_search_left
group_46_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46304
 POP HL
 POP IY
 POP DE
 JP complete
group_46_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46298
 POP HL
 POP IY
 POP DE
 JP complete
group_47:
 LD A,IXL
group_47_search:
 CP 58
 JP C,group_47_search_left
group_47_search_right:
 CP 164
 JP C,group_47_search_right_left
group_47_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45974
 POP HL
 POP IY
 POP DE
 JP complete
group_47_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45968
 POP HL
 POP IY
 POP DE
 JP complete
group_47_search_left:
 CP 48
 JP C,group_47_search_left_left
group_47_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45962
 POP HL
 POP IY
 POP DE
 JP complete
group_47_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45956
 POP HL
 POP IY
 POP DE
 JP complete
group_48:
 LD A,IXL
group_48_search:
 CP 49
 JP C,group_48_search_left
group_48_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45788
 POP HL
 POP IY
 POP DE
 JP complete
group_48_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45782
 POP HL
 POP IY
 POP DE
 JP complete
group_49:
 LD A,IXL
group_49_search:
 CP 80
 JP C,group_49_search_left
group_49_search_right:
 CP 117
 JP C,group_49_search_right_left
group_49_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45296
 POP HL
 POP IY
 POP DE
 JP complete
group_49_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45290
 POP HL
 POP IY
 POP DE
 JP complete
group_49_search_left:
 CP 50
 JP C,group_49_search_left_left
group_49_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45284
 POP HL
 POP IY
 POP DE
 JP complete
group_49_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45278
 POP HL
 POP IY
 POP DE
 JP complete
group_50:
 LD A,IXL
group_50_search:
 CP 52
 JP C,group_50_search_left
group_50_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45212
 POP HL
 POP IY
 POP DE
 JP complete
group_50_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45206
 POP HL
 POP IY
 POP DE
 JP complete
group_51:
 LD A,IXL
group_51_search:
 CP 52
 JP C,group_51_search_left
group_51_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46316
 POP HL
 POP IY
 POP DE
 JP complete
group_51_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46310
 POP HL
 POP IY
 POP DE
 JP complete
group_52:
 LD A,IXL
group_52_search:
 CP 53
 JP C,group_52_search_left
group_52_search_right:
 CP 89
 JP C,group_52_search_right_left
group_52_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45710
 POP HL
 POP IY
 POP DE
 JP complete
group_52_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45704
 POP HL
 POP IY
 POP DE
 JP complete
group_52_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45698
 POP HL
 POP IY
 POP DE
 JP complete
group_53:
 LD A,IXL
group_53_search:
 CP 53
 JP C,group_53_search_left
group_53_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46190
 POP HL
 POP IY
 POP DE
 JP complete
group_53_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46184
 POP HL
 POP IY
 POP DE
 JP complete
group_54:
 LD A,IXL
group_54_search:
 CP 53
 JP C,group_54_search_left
group_54_search_right:
 CP 132
 JP C,group_54_search_right_left
group_54_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46580
 POP HL
 POP IY
 POP DE
 JP complete
group_54_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46574
 POP HL
 POP IY
 POP DE
 JP complete
group_54_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46568
 POP HL
 POP IY
 POP DE
 JP complete
group_55:
 LD A,IXL
group_55_search:
 CP 54
 JP C,group_55_search_left
group_55_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45512
 POP HL
 POP IY
 POP DE
 JP complete
group_55_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45506
 POP HL
 POP IY
 POP DE
 JP complete
group_56:
 LD A,IXL
group_56_search:
 CP 55
 JP C,group_56_search_left
group_56_search_right:
 CP 193
 JP C,group_56_search_right_left
group_56_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45338
 POP HL
 POP IY
 POP DE
 JP complete
group_56_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45332
 POP HL
 POP IY
 POP DE
 JP complete
group_56_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45326
 POP HL
 POP IY
 POP DE
 JP complete
group_57:
 LD A,IXL
group_57_search:
 CP 56
 JP C,group_57_search_left
group_57_search_right:
 CP 86
 JP C,group_57_search_right_left
group_57_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45674
 POP HL
 POP IY
 POP DE
 JP complete
group_57_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45668
 POP HL
 POP IY
 POP DE
 JP complete
group_57_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45662
 POP HL
 POP IY
 POP DE
 JP complete
group_58:
 LD A,IXL
group_58_search:
 CP 57
 JP C,group_58_search_left
group_58_search_right:
 CP 126
 JP C,group_58_search_right_left
group_58_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46694
 POP HL
 POP IY
 POP DE
 JP complete
group_58_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46688
 POP HL
 POP IY
 POP DE
 JP complete
group_58_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46682
 POP HL
 POP IY
 POP DE
 JP complete
group_59:
 LD A,IXL
group_59_search:
 CP 95
 JP C,group_59_search_left
group_59_search_right:
 CP 213
 JP C,group_59_search_right_left
group_59_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45560
 POP HL
 POP IY
 POP DE
 JP complete
group_59_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45554
 POP HL
 POP IY
 POP DE
 JP complete
group_59_search_left:
 CP 58
 JP C,group_59_search_left_left
group_59_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45548
 POP HL
 POP IY
 POP DE
 JP complete
group_59_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45542
 POP HL
 POP IY
 POP DE
 JP complete
group_60:
 LD A,IXL
group_60_search:
 CP 58
 JP C,group_60_search_left
group_60_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45656
 POP HL
 POP IY
 POP DE
 JP complete
group_60_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45650
 POP HL
 POP IY
 POP DE
 JP complete
group_61:
 LD A,IXL
group_61_search:
 CP 61
 JP C,group_61_search_left
group_61_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45566
 POP HL
 POP IY
 POP DE
 JP complete
group_61_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45560
 POP HL
 POP IY
 POP DE
 JP complete
group_62:
 LD A,IXL
group_62_search:
 CP 62
 JP C,group_62_search_left
group_62_search_right:
 CP 209
 JP C,group_62_search_right_left
group_62_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46634
 POP HL
 POP IY
 POP DE
 JP complete
group_62_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46628
 POP HL
 POP IY
 POP DE
 JP complete
group_62_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46622
 POP HL
 POP IY
 POP DE
 JP complete
group_63:
 LD A,IXL
group_63_search:
 CP 116
 JP C,group_63_search_left
group_63_search_right:
 CP 166
 JP C,group_63_search_right_left
group_63_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46292
 POP HL
 POP IY
 POP DE
 JP complete
group_63_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46286
 POP HL
 POP IY
 POP DE
 JP complete
group_63_search_left:
 CP 64
 JP C,group_63_search_left_left
group_63_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,46280
 POP HL
 POP IY
 POP DE
 JP complete
group_63_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,46274
 POP HL
 POP IY
 POP DE
 JP complete
group_64:
 LD A,IXL
group_64_search:
 CP 64
 JP C,group_64_search_left
group_64_search_right:
 CP 71
 JP C,group_64_search_right_left
group_64_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46418
 POP HL
 POP IY
 POP DE
 JP complete
group_64_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46412
 POP HL
 POP IY
 POP DE
 JP complete
group_64_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46406
 POP HL
 POP IY
 POP DE
 JP complete
group_65:
 LD A,IXL
group_65_search:
 CP 65
 JP C,group_65_search_left
group_65_search_right:
 CP 76
 JP C,group_65_search_right_left
group_65_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45608
 POP HL
 POP IY
 POP DE
 JP complete
group_65_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45602
 POP HL
 POP IY
 POP DE
 JP complete
group_65_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45596
 POP HL
 POP IY
 POP DE
 JP complete
group_66:
 LD A,IXL
group_66_search:
 CP 68
 JP C,group_66_search_left
group_66_search_right:
 CP 189
 JP C,group_66_search_right_left
group_66_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45368
 POP HL
 POP IY
 POP DE
 JP complete
group_66_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45362
 POP HL
 POP IY
 POP DE
 JP complete
group_66_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45356
 POP HL
 POP IY
 POP DE
 JP complete
group_67:
 LD A,IXL
group_67_search:
 CP 68
 JP C,group_67_search_left
group_67_search_right:
 CP 131
 JP C,group_67_search_right_left
group_67_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46088
 POP HL
 POP IY
 POP DE
 JP complete
group_67_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46082
 POP HL
 POP IY
 POP DE
 JP complete
group_67_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46076
 POP HL
 POP IY
 POP DE
 JP complete
group_68:
 LD A,IXL
group_68_search:
 CP 87
 JP C,group_68_search_left
group_68_search_right:
 CP 170
 JP C,group_68_search_right_left
group_68_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46184
 POP HL
 POP IY
 POP DE
 JP complete
group_68_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46178
 POP HL
 POP IY
 POP DE
 JP complete
group_68_search_left:
 CP 71
 JP C,group_68_search_left_left
group_68_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,46172
 POP HL
 POP IY
 POP DE
 JP complete
group_68_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,46166
 POP HL
 POP IY
 POP DE
 JP complete
group_69:
 LD A,IXL
group_69_search:
 CP 71
 JP C,group_69_search_left
group_69_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46406
 POP HL
 POP IY
 POP DE
 JP complete
group_69_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46400
 POP HL
 POP IY
 POP DE
 JP complete
group_70:
 LD A,IXL
group_70_search:
 CP 72
 JP C,group_70_search_left
group_70_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45398
 POP HL
 POP IY
 POP DE
 JP complete
group_70_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45392
 POP HL
 POP IY
 POP DE
 JP complete
group_71:
 LD A,IXL
group_71_search:
 CP 133
 JP C,group_71_search_left
group_71_search_right:
 CP 145
 JP C,group_71_search_right_left
group_71_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45416
 POP HL
 POP IY
 POP DE
 JP complete
group_71_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45410
 POP HL
 POP IY
 POP DE
 JP complete
group_71_search_left:
 CP 72
 JP C,group_71_search_left_left
group_71_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45404
 POP HL
 POP IY
 POP DE
 JP complete
group_71_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45398
 POP HL
 POP IY
 POP DE
 JP complete
group_72:
 LD A,IXL
group_72_search:
 CP 79
 JP C,group_72_search_left
group_72_search_right:
 CP 113
 JP C,group_72_search_right_left
group_72_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45650
 POP HL
 POP IY
 POP DE
 JP complete
group_72_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45644
 POP HL
 POP IY
 POP DE
 JP complete
group_72_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45638
 POP HL
 POP IY
 POP DE
 JP complete
group_73:
 LD A,IXL
group_73_search:
 CP 79
 JP C,group_73_search_left
group_73_search_right:
 CP 106
 JP C,group_73_search_right_left
group_73_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46610
 POP HL
 POP IY
 POP DE
 JP complete
group_73_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46604
 POP HL
 POP IY
 POP DE
 JP complete
group_73_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46598
 POP HL
 POP IY
 POP DE
 JP complete
group_74:
 LD A,IXL
group_74_search:
 CP 80
 JP C,group_74_search_left
group_74_search_right:
 CP 201
 JP C,group_74_search_right_left
group_74_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45392
 POP HL
 POP IY
 POP DE
 JP complete
group_74_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45386
 POP HL
 POP IY
 POP DE
 JP complete
group_74_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45380
 POP HL
 POP IY
 POP DE
 JP complete
group_75:
 LD A,IXL
group_75_search:
 CP 100
 JP C,group_75_search_left
group_75_search_right:
 CP 249
 JP C,group_75_search_right_left
group_75_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45542
 POP HL
 POP IY
 POP DE
 JP complete
group_75_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45536
 POP HL
 POP IY
 POP DE
 JP complete
group_75_search_left:
 CP 81
 JP C,group_75_search_left_left
group_75_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45530
 POP HL
 POP IY
 POP DE
 JP complete
group_75_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45524
 POP HL
 POP IY
 POP DE
 JP complete
group_76:
 LD A,IXL
group_76_search:
 CP 83
 JP C,group_76_search_left
group_76_search_right:
 CP 142
 JP C,group_76_search_right_left
group_76_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46460
 POP HL
 POP IY
 POP DE
 JP complete
group_76_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46454
 POP HL
 POP IY
 POP DE
 JP complete
group_76_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46448
 POP HL
 POP IY
 POP DE
 JP complete
group_77:
 LD A,IXL
group_77_search:
 CP 84
 JP C,group_77_search_left
group_77_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46238
 POP HL
 POP IY
 POP DE
 JP complete
group_77_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46232
 POP HL
 POP IY
 POP DE
 JP complete
group_78:
 LD A,IXL
group_78_search:
 CP 84
 JP C,group_78_search_left
group_78_search_right:
 CP 137
 JP C,group_78_search_right_left
group_78_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46274
 POP HL
 POP IY
 POP DE
 JP complete
group_78_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46268
 POP HL
 POP IY
 POP DE
 JP complete
group_78_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46262
 POP HL
 POP IY
 POP DE
 JP complete
group_79:
 LD A,IXL
group_79_search:
 CP 84
 JP C,group_79_search_left
group_79_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46808
 POP HL
 POP IY
 POP DE
 JP complete
group_79_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46802
 POP HL
 POP IY
 POP DE
 JP complete
group_80:
 LD A,IXL
group_80_search:
 CP 86
 JP C,group_80_search_left
group_80_search_right:
 CP 192
 JP C,group_80_search_right_left
group_80_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46706
 POP HL
 POP IY
 POP DE
 JP complete
group_80_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46700
 POP HL
 POP IY
 POP DE
 JP complete
group_80_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46694
 POP HL
 POP IY
 POP DE
 JP complete
group_81:
 LD A,IXL
group_81_search:
 CP 86
 JP C,group_81_search_left
group_81_search_right:
 CP 162
 JP C,group_81_search_right_left
group_81_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46724
 POP HL
 POP IY
 POP DE
 JP complete
group_81_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46718
 POP HL
 POP IY
 POP DE
 JP complete
group_81_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46712
 POP HL
 POP IY
 POP DE
 JP complete
group_82:
 LD A,IXL
group_82_search:
 CP 87
 JP C,group_82_search_left
group_82_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45680
 POP HL
 POP IY
 POP DE
 JP complete
group_82_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45674
 POP HL
 POP IY
 POP DE
 JP complete
group_83:
 LD A,IXL
group_83_search:
 CP 87
 JP C,group_83_search_left
group_83_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46136
 POP HL
 POP IY
 POP DE
 JP complete
group_83_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46130
 POP HL
 POP IY
 POP DE
 JP complete
group_84:
 LD A,IXL
group_84_search:
 CP 90
 JP C,group_84_search_left
group_84_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45266
 POP HL
 POP IY
 POP DE
 JP complete
group_84_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45260
 POP HL
 POP IY
 POP DE
 JP complete
group_85:
 LD A,IXL
group_85_search:
 CP 144
 JP C,group_85_search_left
group_85_search_right:
 CP 164
 JP C,group_85_search_right_left
group_85_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45158
 POP HL
 POP IY
 POP DE
 JP complete
group_85_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45152
 POP HL
 POP IY
 POP DE
 JP complete
group_85_search_left:
 CP 92
 JP C,group_85_search_left_left
group_85_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45146
 POP HL
 POP IY
 POP DE
 JP complete
group_85_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45140
 POP HL
 POP IY
 POP DE
 JP complete
group_86:
 LD A,IXL
group_86_search:
 CP 92
 JP C,group_86_search_left
group_86_search_right:
 CP 162
 JP C,group_86_search_right_left
group_86_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45224
 POP HL
 POP IY
 POP DE
 JP complete
group_86_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45218
 POP HL
 POP IY
 POP DE
 JP complete
group_86_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45212
 POP HL
 POP IY
 POP DE
 JP complete
group_87:
 LD A,IXL
group_87_search:
 CP 93
 JP C,group_87_search_left
group_87_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45794
 POP HL
 POP IY
 POP DE
 JP complete
group_87_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45788
 POP HL
 POP IY
 POP DE
 JP complete
group_88:
 LD A,IXL
group_88_search:
 CP 94
 JP C,group_88_search_left
group_88_search_right:
 CP 247
 JP C,group_88_search_right_left
group_88_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45098
 POP HL
 POP IY
 POP DE
 JP complete
group_88_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45092
 POP HL
 POP IY
 POP DE
 JP complete
group_88_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45086
 POP HL
 POP IY
 POP DE
 JP complete
group_89:
 LD A,IXL
group_89_search:
 CP 120
 JP C,group_89_search_left
group_89_search_right:
 CP 249
 JP C,group_89_search_right_left
group_89_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46016
 POP HL
 POP IY
 POP DE
 JP complete
group_89_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46010
 POP HL
 POP IY
 POP DE
 JP complete
group_89_search_left:
 CP 94
 JP C,group_89_search_left_left
group_89_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,46004
 POP HL
 POP IY
 POP DE
 JP complete
group_89_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45998
 POP HL
 POP IY
 POP DE
 JP complete
group_90:
 LD A,IXL
group_90_search:
 CP 95
 JP C,group_90_search_left
group_90_search_right:
 CP 250
 JP C,group_90_search_right_left
group_90_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46592
 POP HL
 POP IY
 POP DE
 JP complete
group_90_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46586
 POP HL
 POP IY
 POP DE
 JP complete
group_90_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46580
 POP HL
 POP IY
 POP DE
 JP complete
group_91:
 LD A,IXL
group_91_search:
 CP 95
 JP C,group_91_search_left
group_91_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46598
 POP HL
 POP IY
 POP DE
 JP complete
group_91_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46592
 POP HL
 POP IY
 POP DE
 JP complete
group_92:
 LD A,IXL
group_92_search:
 CP 96
 JP C,group_92_search_left
group_92_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45614
 POP HL
 POP IY
 POP DE
 JP complete
group_92_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45608
 POP HL
 POP IY
 POP DE
 JP complete
group_93:
 LD A,IXL
group_93_search:
 CP 96
 JP C,group_93_search_left
group_93_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46514
 POP HL
 POP IY
 POP DE
 JP complete
group_93_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46508
 POP HL
 POP IY
 POP DE
 JP complete
group_94:
 LD A,IXL
group_94_search:
 CP 97
 JP C,group_94_search_left
group_94_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46562
 POP HL
 POP IY
 POP DE
 JP complete
group_94_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46556
 POP HL
 POP IY
 POP DE
 JP complete
group_95:
 LD A,IXL
group_95_search:
 CP 97
 JP C,group_95_search_left
group_95_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46568
 POP HL
 POP IY
 POP DE
 JP complete
group_95_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46562
 POP HL
 POP IY
 POP DE
 JP complete
group_96:
 LD A,IXL
group_96_search:
 CP 98
 JP C,group_96_search_left
group_96_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46130
 POP HL
 POP IY
 POP DE
 JP complete
group_96_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46124
 POP HL
 POP IY
 POP DE
 JP complete
group_97:
 LD A,IXL
group_97_search:
 CP 99
 JP C,group_97_search_left
group_97_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45872
 POP HL
 POP IY
 POP DE
 JP complete
group_97_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45866
 POP HL
 POP IY
 POP DE
 JP complete
group_98:
 LD A,IXL
group_98_search:
 CP 99
 JP C,group_98_search_left
group_98_search_right:
 CP 113
 JP C,group_98_search_right_left
group_98_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46124
 POP HL
 POP IY
 POP DE
 JP complete
group_98_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46118
 POP HL
 POP IY
 POP DE
 JP complete
group_98_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46112
 POP HL
 POP IY
 POP DE
 JP complete
group_99:
 LD A,IXL
group_99_search:
 CP 101
 JP C,group_99_search_left
group_99_search_right:
 CP 146
 JP C,group_99_search_right_left
group_99_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45452
 POP HL
 POP IY
 POP DE
 JP complete
group_99_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45446
 POP HL
 POP IY
 POP DE
 JP complete
group_99_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45440
 POP HL
 POP IY
 POP DE
 JP complete
group_100:
 LD A,IXL
group_100_search:
 CP 113
 JP C,group_100_search_left
group_100_search_right:
 CP 191
 JP C,group_100_search_right_left
group_100_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45752
 POP HL
 POP IY
 POP DE
 JP complete
group_100_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45746
 POP HL
 POP IY
 POP DE
 JP complete
group_100_search_left:
 CP 101
 JP C,group_100_search_left_left
group_100_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45740
 POP HL
 POP IY
 POP DE
 JP complete
group_100_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45734
 POP HL
 POP IY
 POP DE
 JP complete
group_101:
 LD A,IXL
group_101_search:
 CP 230
 JP C,group_101_search_left
group_101_search_right:
 CP 234
 JP C,group_101_search_right_left
group_101_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46784
 POP HL
 POP IY
 POP DE
 JP complete
group_101_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46778
 POP HL
 POP IY
 POP DE
 JP complete
group_101_search_left:
 CP 101
 JP C,group_101_search_left_left
group_101_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,46772
 POP HL
 POP IY
 POP DE
 JP complete
group_101_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,46766
 POP HL
 POP IY
 POP DE
 JP complete
group_102:
 LD A,IXL
group_102_search:
 CP 103
 JP C,group_102_search_left
group_102_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45950
 POP HL
 POP IY
 POP DE
 JP complete
group_102_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45944
 POP HL
 POP IY
 POP DE
 JP complete
group_103:
 LD A,IXL
group_103_search:
 CP 103
 JP C,group_103_search_left
group_103_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46472
 POP HL
 POP IY
 POP DE
 JP complete
group_103_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46466
 POP HL
 POP IY
 POP DE
 JP complete
group_104:
 LD A,IXL
group_104_search:
 CP 104
 JP C,group_104_search_left
group_104_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46094
 POP HL
 POP IY
 POP DE
 JP complete
group_104_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46088
 POP HL
 POP IY
 POP DE
 JP complete
group_105:
 LD A,IXL
group_105_search:
 CP 104
 JP C,group_105_search_left
group_105_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46760
 POP HL
 POP IY
 POP DE
 JP complete
group_105_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46754
 POP HL
 POP IY
 POP DE
 JP complete
group_106:
 LD A,IXL
group_106_search:
 CP 249
 JP C,group_106_search_left
group_106_search_right:
 CP 255
 JP C,group_106_search_right_left
group_106_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46040
 POP HL
 POP IY
 POP DE
 JP complete
group_106_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46034
 POP HL
 POP IY
 POP DE
 JP complete
group_106_search_left:
 CP 107
 JP C,group_106_search_left_left
group_106_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,46028
 POP HL
 POP IY
 POP DE
 JP complete
group_106_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,46022
 POP HL
 POP IY
 POP DE
 JP complete
group_107:
 LD A,IXL
group_107_search:
 CP 108
 JP C,group_107_search_left
group_107_search_right:
 CP 236
 JP C,group_107_search_right_left
group_107_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45200
 POP HL
 POP IY
 POP DE
 JP complete
group_107_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45194
 POP HL
 POP IY
 POP DE
 JP complete
group_107_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45188
 POP HL
 POP IY
 POP DE
 JP complete
group_108:
 LD A,IXL
group_108_search:
 CP 108
 JP C,group_108_search_left
group_108_search_right:
 CP 228
 JP C,group_108_search_right_left
group_108_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46394
 POP HL
 POP IY
 POP DE
 JP complete
group_108_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46388
 POP HL
 POP IY
 POP DE
 JP complete
group_108_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46382
 POP HL
 POP IY
 POP DE
 JP complete
group_109:
 LD A,IXL
group_109_search:
 CP 110
 JP C,group_109_search_left
group_109_search_right:
 CP 119
 JP C,group_109_search_right_left
group_109_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45308
 POP HL
 POP IY
 POP DE
 JP complete
group_109_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45302
 POP HL
 POP IY
 POP DE
 JP complete
group_109_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45296
 POP HL
 POP IY
 POP DE
 JP complete
group_110:
 LD A,IXL
group_110_search:
 CP 113
 JP C,group_110_search_left
group_110_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46334
 POP HL
 POP IY
 POP DE
 JP complete
group_110_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46328
 POP HL
 POP IY
 POP DE
 JP complete
group_111:
 LD A,IXL
group_111_search:
 CP 116
 JP C,group_111_search_left
group_111_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45800
 POP HL
 POP IY
 POP DE
 JP complete
group_111_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45794
 POP HL
 POP IY
 POP DE
 JP complete
group_112:
 LD A,IXL
group_112_search:
 CP 116
 JP C,group_112_search_left
group_112_search_right:
 CP 170
 JP C,group_112_search_right_left
group_112_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45812
 POP HL
 POP IY
 POP DE
 JP complete
group_112_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45806
 POP HL
 POP IY
 POP DE
 JP complete
group_112_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45800
 POP HL
 POP IY
 POP DE
 JP complete
group_113:
 LD A,IXL
group_113_search:
 CP 117
 JP C,group_113_search_left
group_113_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46730
 POP HL
 POP IY
 POP DE
 JP complete
group_113_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46724
 POP HL
 POP IY
 POP DE
 JP complete
group_114:
 LD A,IXL
group_114_search:
 CP 117
 JP C,group_114_search_left
group_114_search_right:
 CP 191
 JP C,group_114_search_right_left
group_114_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46742
 POP HL
 POP IY
 POP DE
 JP complete
group_114_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46736
 POP HL
 POP IY
 POP DE
 JP complete
group_114_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46730
 POP HL
 POP IY
 POP DE
 JP complete
group_115:
 LD A,IXL
group_115_search:
 CP 117
 JP C,group_115_search_left
group_115_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46766
 POP HL
 POP IY
 POP DE
 JP complete
group_115_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46760
 POP HL
 POP IY
 POP DE
 JP complete
group_116:
 LD A,IXL
group_116_search:
 CP 119
 JP C,group_116_search_left
group_116_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45314
 POP HL
 POP IY
 POP DE
 JP complete
group_116_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45308
 POP HL
 POP IY
 POP DE
 JP complete
group_117:
 LD A,IXL
group_117_search:
 CP 119
 JP C,group_117_search_left
group_117_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45344
 POP HL
 POP IY
 POP DE
 JP complete
group_117_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45338
 POP HL
 POP IY
 POP DE
 JP complete
group_118:
 LD A,IXL
group_118_search:
 CP 123
 JP C,group_118_search_left
group_118_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45110
 POP HL
 POP IY
 POP DE
 JP complete
group_118_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45104
 POP HL
 POP IY
 POP DE
 JP complete
group_119:
 LD A,IXL
group_119_search:
 CP 129
 JP C,group_119_search_left
group_119_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46640
 POP HL
 POP IY
 POP DE
 JP complete
group_119_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46634
 POP HL
 POP IY
 POP DE
 JP complete
group_120:
 LD A,IXL
group_120_search:
 CP 143
 JP C,group_120_search_left
group_120_search_right:
 CP 202
 JP C,group_120_search_right_left
group_120_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45638
 POP HL
 POP IY
 POP DE
 JP complete
group_120_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45632
 POP HL
 POP IY
 POP DE
 JP complete
group_120_search_left:
 CP 134
 JP C,group_120_search_left_left
group_120_search_left_right:
 LD A,R
 NOP
 NOP
 LD SP,45626
 POP HL
 POP IY
 POP DE
 JP complete
group_120_search_left_left:
 LD A,R
 NOP
 NOP
 LD SP,45620
 POP HL
 POP IY
 POP DE
 JP complete
group_121:
 LD A,IXL
group_121_search:
 CP 136
 JP C,group_121_search_left
group_121_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46622
 POP HL
 POP IY
 POP DE
 JP complete
group_121_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46616
 POP HL
 POP IY
 POP DE
 JP complete
group_122:
 LD A,IXL
group_122_search:
 CP 141
 JP C,group_122_search_left
group_122_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45272
 POP HL
 POP IY
 POP DE
 JP complete
group_122_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45266
 POP HL
 POP IY
 POP DE
 JP complete
group_123:
 LD A,IXL
group_123_search:
 CP 143
 JP C,group_123_search_left
group_123_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46424
 POP HL
 POP IY
 POP DE
 JP complete
group_123_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46418
 POP HL
 POP IY
 POP DE
 JP complete
group_124:
 LD A,IXL
group_124_search:
 CP 143
 JP C,group_124_search_left
group_124_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46748
 POP HL
 POP IY
 POP DE
 JP complete
group_124_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46742
 POP HL
 POP IY
 POP DE
 JP complete
group_125:
 LD A,IXL
group_125_search:
 CP 144
 JP C,group_125_search_left
group_125_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45428
 POP HL
 POP IY
 POP DE
 JP complete
group_125_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45422
 POP HL
 POP IY
 POP DE
 JP complete
group_126:
 LD A,IXL
group_126_search:
 CP 146
 JP C,group_126_search_left
group_126_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45440
 POP HL
 POP IY
 POP DE
 JP complete
group_126_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45434
 POP HL
 POP IY
 POP DE
 JP complete
group_127:
 LD A,IXL
group_127_search:
 CP 146
 JP C,group_127_search_left
group_127_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45464
 POP HL
 POP IY
 POP DE
 JP complete
group_127_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45458
 POP HL
 POP IY
 POP DE
 JP complete
group_128:
 LD A,IXL
group_128_search:
 CP 146
 JP C,group_128_search_left
group_128_search_right:
 CP 185
 JP C,group_128_search_right_left
group_128_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46370
 POP HL
 POP IY
 POP DE
 JP complete
group_128_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46364
 POP HL
 POP IY
 POP DE
 JP complete
group_128_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46358
 POP HL
 POP IY
 POP DE
 JP complete
group_129:
 LD A,IXL
group_129_search:
 CP 148
 JP C,group_129_search_left
group_129_search_right:
 CP 161
 JP C,group_129_search_right_left
group_129_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45938
 POP HL
 POP IY
 POP DE
 JP complete
group_129_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45932
 POP HL
 POP IY
 POP DE
 JP complete
group_129_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45926
 POP HL
 POP IY
 POP DE
 JP complete
group_130:
 LD A,IXL
group_130_search:
 CP 149
 JP C,group_130_search_left
group_130_search_right:
 CP 217
 JP C,group_130_search_right_left
group_130_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45782
 POP HL
 POP IY
 POP DE
 JP complete
group_130_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45776
 POP HL
 POP IY
 POP DE
 JP complete
group_130_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45770
 POP HL
 POP IY
 POP DE
 JP complete
group_131:
 LD A,IXL
group_131_search:
 CP 152
 JP C,group_131_search_left
group_131_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45206
 POP HL
 POP IY
 POP DE
 JP complete
group_131_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45200
 POP HL
 POP IY
 POP DE
 JP complete
group_132:
 LD A,IXL
group_132_search:
 CP 156
 JP C,group_132_search_left
group_132_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46298
 POP HL
 POP IY
 POP DE
 JP complete
group_132_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46292
 POP HL
 POP IY
 POP DE
 JP complete
group_133:
 LD A,IXL
group_133_search:
 CP 156
 JP C,group_133_search_left
group_133_search_right:
 CP 236
 JP C,group_133_search_right_left
group_133_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46802
 POP HL
 POP IY
 POP DE
 JP complete
group_133_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46796
 POP HL
 POP IY
 POP DE
 JP complete
group_133_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46790
 POP HL
 POP IY
 POP DE
 JP complete
group_134:
 LD A,IXL
group_134_search:
 CP 161
 JP C,group_134_search_left
group_134_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45722
 POP HL
 POP IY
 POP DE
 JP complete
group_134_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45716
 POP HL
 POP IY
 POP DE
 JP complete
group_135:
 LD A,IXL
group_135_search:
 CP 161
 JP C,group_135_search_left
group_135_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45734
 POP HL
 POP IY
 POP DE
 JP complete
group_135_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45728
 POP HL
 POP IY
 POP DE
 JP complete
group_136:
 LD A,IXL
group_136_search:
 CP 163
 JP C,group_136_search_left
group_136_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45278
 POP HL
 POP IY
 POP DE
 JP complete
group_136_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45272
 POP HL
 POP IY
 POP DE
 JP complete
group_137:
 LD A,IXL
group_137_search:
 CP 163
 JP C,group_137_search_left
group_137_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46208
 POP HL
 POP IY
 POP DE
 JP complete
group_137_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46202
 POP HL
 POP IY
 POP DE
 JP complete
group_138:
 LD A,IXL
group_138_search:
 CP 163
 JP C,group_138_search_left
group_138_search_right:
 CP 220
 JP C,group_138_search_right_left
group_138_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46220
 POP HL
 POP IY
 POP DE
 JP complete
group_138_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46214
 POP HL
 POP IY
 POP DE
 JP complete
group_138_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46208
 POP HL
 POP IY
 POP DE
 JP complete
group_139:
 LD A,IXL
group_139_search:
 CP 165
 JP C,group_139_search_left
group_139_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46142
 POP HL
 POP IY
 POP DE
 JP complete
group_139_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46136
 POP HL
 POP IY
 POP DE
 JP complete
group_140:
 LD A,IXL
group_140_search:
 CP 165
 JP C,group_140_search_left
group_140_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46820
 POP HL
 POP IY
 POP DE
 JP complete
group_140_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46814
 POP HL
 POP IY
 POP DE
 JP complete
group_141:
 LD A,IXL
group_141_search:
 CP 166
 JP C,group_141_search_left
group_141_search_right:
 CP 226
 JP C,group_141_search_right_left
group_141_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45854
 POP HL
 POP IY
 POP DE
 JP complete
group_141_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45848
 POP HL
 POP IY
 POP DE
 JP complete
group_141_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45842
 POP HL
 POP IY
 POP DE
 JP complete
group_142:
 LD A,IXL
group_142_search:
 CP 167
 JP C,group_142_search_left
group_142_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46616
 POP HL
 POP IY
 POP DE
 JP complete
group_142_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46610
 POP HL
 POP IY
 POP DE
 JP complete
group_143:
 LD A,IXL
group_143_search:
 CP 169
 JP C,group_143_search_left
group_143_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45662
 POP HL
 POP IY
 POP DE
 JP complete
group_143_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45656
 POP HL
 POP IY
 POP DE
 JP complete
group_144:
 LD A,IXL
group_144_search:
 CP 169
 JP C,group_144_search_left
group_144_search_right:
 CP 219
 JP C,group_144_search_right_left
group_144_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46346
 POP HL
 POP IY
 POP DE
 JP complete
group_144_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46340
 POP HL
 POP IY
 POP DE
 JP complete
group_144_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46334
 POP HL
 POP IY
 POP DE
 JP complete
group_145:
 LD A,IXL
group_145_search:
 CP 174
 JP C,group_145_search_left
group_145_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45500
 POP HL
 POP IY
 POP DE
 JP complete
group_145_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45494
 POP HL
 POP IY
 POP DE
 JP complete
group_146:
 LD A,IXL
group_146_search:
 CP 174
 JP C,group_146_search_left
group_146_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46790
 POP HL
 POP IY
 POP DE
 JP complete
group_146_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46784
 POP HL
 POP IY
 POP DE
 JP complete
group_147:
 LD A,IXL
group_147_search:
 CP 175
 JP C,group_147_search_left
group_147_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45506
 POP HL
 POP IY
 POP DE
 JP complete
group_147_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45500
 POP HL
 POP IY
 POP DE
 JP complete
group_148:
 LD A,IXL
group_148_search:
 CP 175
 JP C,group_148_search_left
group_148_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45578
 POP HL
 POP IY
 POP DE
 JP complete
group_148_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45572
 POP HL
 POP IY
 POP DE
 JP complete
group_149:
 LD A,IXL
group_149_search:
 CP 177
 JP C,group_149_search_left
group_149_search_right:
 CP 201
 JP C,group_149_search_right_left
group_149_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45524
 POP HL
 POP IY
 POP DE
 JP complete
group_149_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45518
 POP HL
 POP IY
 POP DE
 JP complete
group_149_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45512
 POP HL
 POP IY
 POP DE
 JP complete
group_150:
 LD A,IXL
group_150_search:
 CP 181
 JP C,group_150_search_left
group_150_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45944
 POP HL
 POP IY
 POP DE
 JP complete
group_150_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45938
 POP HL
 POP IY
 POP DE
 JP complete
group_151:
 LD A,IXL
group_151_search:
 CP 181
 JP C,group_151_search_left
group_151_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45956
 POP HL
 POP IY
 POP DE
 JP complete
group_151_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45950
 POP HL
 POP IY
 POP DE
 JP complete
group_152:
 LD A,IXL
group_152_search:
 CP 181
 JP C,group_152_search_left
group_152_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46664
 POP HL
 POP IY
 POP DE
 JP complete
group_152_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46658
 POP HL
 POP IY
 POP DE
 JP complete
group_153:
 LD A,IXL
group_153_search:
 CP 182
 JP C,group_153_search_left
group_153_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45320
 POP HL
 POP IY
 POP DE
 JP complete
group_153_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45314
 POP HL
 POP IY
 POP DE
 JP complete
group_154:
 LD A,IXL
group_154_search:
 CP 188
 JP C,group_154_search_left
group_154_search_right:
 CP 227
 JP C,group_154_search_right_left
group_154_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45698
 POP HL
 POP IY
 POP DE
 JP complete
group_154_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45692
 POP HL
 POP IY
 POP DE
 JP complete
group_154_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45686
 POP HL
 POP IY
 POP DE
 JP complete
group_155:
 LD A,IXL
group_155_search:
 CP 188
 JP C,group_155_search_left
group_155_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46310
 POP HL
 POP IY
 POP DE
 JP complete
group_155_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46304
 POP HL
 POP IY
 POP DE
 JP complete
group_156:
 LD A,IXL
group_156_search:
 CP 189
 JP C,group_156_search_left
group_156_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46064
 POP HL
 POP IY
 POP DE
 JP complete
group_156_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46058
 POP HL
 POP IY
 POP DE
 JP complete
group_157:
 LD A,IXL
group_157_search:
 CP 191
 JP C,group_157_search_left
group_157_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45326
 POP HL
 POP IY
 POP DE
 JP complete
group_157_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45320
 POP HL
 POP IY
 POP DE
 JP complete
group_158:
 LD A,IXL
group_158_search:
 CP 191
 JP C,group_158_search_left
group_158_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45434
 POP HL
 POP IY
 POP DE
 JP complete
group_158_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45428
 POP HL
 POP IY
 POP DE
 JP complete
group_159:
 LD A,IXL
group_159_search:
 CP 194
 JP C,group_159_search_left
group_159_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46202
 POP HL
 POP IY
 POP DE
 JP complete
group_159_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46196
 POP HL
 POP IY
 POP DE
 JP complete
group_160:
 LD A,IXL
group_160_search:
 CP 195
 JP C,group_160_search_left
group_160_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46838
 POP HL
 POP IY
 POP DE
 JP complete
group_160_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46832
 POP HL
 POP IY
 POP DE
 JP complete
group_161:
 LD A,IXL
group_161_search:
 CP 196
 JP C,group_161_search_left
group_161_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45422
 POP HL
 POP IY
 POP DE
 JP complete
group_161_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45416
 POP HL
 POP IY
 POP DE
 JP complete
group_162:
 LD A,IXL
group_162_search:
 CP 197
 JP C,group_162_search_left
group_162_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46676
 POP HL
 POP IY
 POP DE
 JP complete
group_162_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46670
 POP HL
 POP IY
 POP DE
 JP complete
group_163:
 LD A,IXL
group_163_search:
 CP 199
 JP C,group_163_search_left
group_163_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45686
 POP HL
 POP IY
 POP DE
 JP complete
group_163_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45680
 POP HL
 POP IY
 POP DE
 JP complete
group_164:
 LD A,IXL
group_164_search:
 CP 201
 JP C,group_164_search_left
group_164_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46652
 POP HL
 POP IY
 POP DE
 JP complete
group_164_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46646
 POP HL
 POP IY
 POP DE
 JP complete
group_165:
 LD A,IXL
group_165_search:
 CP 202
 JP C,group_165_search_left
group_165_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45164
 POP HL
 POP IY
 POP DE
 JP complete
group_165_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45158
 POP HL
 POP IY
 POP DE
 JP complete
group_166:
 LD A,IXL
group_166_search:
 CP 205
 JP C,group_166_search_left
group_166_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45716
 POP HL
 POP IY
 POP DE
 JP complete
group_166_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45710
 POP HL
 POP IY
 POP DE
 JP complete
group_167:
 LD A,IXL
group_167_search:
 CP 212
 JP C,group_167_search_left
group_167_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46196
 POP HL
 POP IY
 POP DE
 JP complete
group_167_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46190
 POP HL
 POP IY
 POP DE
 JP complete
group_168:
 LD A,IXL
group_168_search:
 CP 213
 JP C,group_168_search_left
group_168_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45980
 POP HL
 POP IY
 POP DE
 JP complete
group_168_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45974
 POP HL
 POP IY
 POP DE
 JP complete
group_169:
 LD A,IXL
group_169_search:
 CP 213
 JP C,group_169_search_left
group_169_search_right:
 CP 222
 JP C,group_169_search_right_left
group_169_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,46052
 POP HL
 POP IY
 POP DE
 JP complete
group_169_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,46046
 POP HL
 POP IY
 POP DE
 JP complete
group_169_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46040
 POP HL
 POP IY
 POP DE
 JP complete
group_170:
 LD A,IXL
group_170_search:
 CP 215
 JP C,group_170_search_left
group_170_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46148
 POP HL
 POP IY
 POP DE
 JP complete
group_170_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46142
 POP HL
 POP IY
 POP DE
 JP complete
group_171:
 LD A,IXL
group_171_search:
 CP 218
 JP C,group_171_search_left
group_171_search_right:
 CP 233
 JP C,group_171_search_right_left
group_171_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45770
 POP HL
 POP IY
 POP DE
 JP complete
group_171_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45764
 POP HL
 POP IY
 POP DE
 JP complete
group_171_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45758
 POP HL
 POP IY
 POP DE
 JP complete
group_172:
 LD A,IXL
group_172_search:
 CP 219
 JP C,group_172_search_left
group_172_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46448
 POP HL
 POP IY
 POP DE
 JP complete
group_172_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46442
 POP HL
 POP IY
 POP DE
 JP complete
group_173:
 LD A,IXL
group_173_search:
 CP 221
 JP C,group_173_search_left
group_173_search_right:
 CP 255
 JP C,group_173_search_right_left
group_173_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45236
 POP HL
 POP IY
 POP DE
 JP complete
group_173_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45230
 POP HL
 POP IY
 POP DE
 JP complete
group_173_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45224
 POP HL
 POP IY
 POP DE
 JP complete
group_174:
 LD A,IXL
group_174_search:
 CP 225
 JP C,group_174_search_left
group_174_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46814
 POP HL
 POP IY
 POP DE
 JP complete
group_174_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46808
 POP HL
 POP IY
 POP DE
 JP complete
group_175:
 LD A,IXL
group_175_search:
 CP 226
 JP C,group_175_search_left
group_175_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45818
 POP HL
 POP IY
 POP DE
 JP complete
group_175_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45812
 POP HL
 POP IY
 POP DE
 JP complete
group_176:
 LD A,IXL
group_176_search:
 CP 226
 JP C,group_176_search_left
group_176_search_right:
 CP 237
 JP C,group_176_search_right_left
group_176_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45866
 POP HL
 POP IY
 POP DE
 JP complete
group_176_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45860
 POP HL
 POP IY
 POP DE
 JP complete
group_176_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45854
 POP HL
 POP IY
 POP DE
 JP complete
group_177:
 LD A,IXL
group_177_search:
 CP 226
 JP C,group_177_search_left
group_177_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46478
 POP HL
 POP IY
 POP DE
 JP complete
group_177_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46472
 POP HL
 POP IY
 POP DE
 JP complete
group_178:
 LD A,IXL
group_178_search:
 CP 228
 JP C,group_178_search_left
group_178_search_right:
 CP 251
 JP C,group_178_search_right_left
group_178_search_right_right:
 LD A,R
 NOP
 NOP
 LD SP,45494
 POP HL
 POP IY
 POP DE
 JP complete
group_178_search_right_left:
 LD A,R
 NOP
 NOP
 LD SP,45488
 POP HL
 POP IY
 POP DE
 JP complete
group_178_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45482
 POP HL
 POP IY
 POP DE
 JP complete
group_179:
 LD A,IXL
group_179_search:
 CP 233
 JP C,group_179_search_left
group_179_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45758
 POP HL
 POP IY
 POP DE
 JP complete
group_179_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45752
 POP HL
 POP IY
 POP DE
 JP complete
group_180:
 LD A,IXL
group_180_search:
 CP 237
 JP C,group_180_search_left
group_180_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46166
 POP HL
 POP IY
 POP DE
 JP complete
group_180_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46160
 POP HL
 POP IY
 POP DE
 JP complete
group_181:
 LD A,IXL
group_181_search:
 CP 238
 JP C,group_181_search_left
group_181_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45620
 POP HL
 POP IY
 POP DE
 JP complete
group_181_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45614
 POP HL
 POP IY
 POP DE
 JP complete
group_182:
 LD A,IXL
group_182_search:
 CP 241
 JP C,group_182_search_left
group_182_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46466
 POP HL
 POP IY
 POP DE
 JP complete
group_182_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46460
 POP HL
 POP IY
 POP DE
 JP complete
group_183:
 LD A,IXL
group_183_search:
 CP 245
 JP C,group_183_search_left
group_183_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45572
 POP HL
 POP IY
 POP DE
 JP complete
group_183_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45566
 POP HL
 POP IY
 POP DE
 JP complete
group_184:
 LD A,IXL
group_184_search:
 CP 246
 JP C,group_184_search_left
group_184_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46058
 POP HL
 POP IY
 POP DE
 JP complete
group_184_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46052
 POP HL
 POP IY
 POP DE
 JP complete
group_185:
 LD A,IXL
group_185_search:
 CP 247
 JP C,group_185_search_left
group_185_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45062
 POP HL
 POP IY
 POP DE
 JP complete
group_185_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45056
 POP HL
 POP IY
 POP DE
 JP complete
group_186:
 LD A,IXL
group_186_search:
 CP 247
 JP C,group_186_search_left
group_186_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45068
 POP HL
 POP IY
 POP DE
 JP complete
group_186_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45062
 POP HL
 POP IY
 POP DE
 JP complete
group_187:
 LD A,IXL
group_187_search:
 CP 247
 JP C,group_187_search_left
group_187_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45074
 POP HL
 POP IY
 POP DE
 JP complete
group_187_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45068
 POP HL
 POP IY
 POP DE
 JP complete
group_188:
 LD A,IXL
group_188_search:
 CP 247
 JP C,group_188_search_left
group_188_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45080
 POP HL
 POP IY
 POP DE
 JP complete
group_188_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45074
 POP HL
 POP IY
 POP DE
 JP complete
group_189:
 LD A,IXL
group_189_search:
 CP 247
 JP C,group_189_search_left
group_189_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45086
 POP HL
 POP IY
 POP DE
 JP complete
group_189_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45080
 POP HL
 POP IY
 POP DE
 JP complete
group_190:
 LD A,IXL
group_190_search:
 CP 247
 JP C,group_190_search_left
group_190_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45104
 POP HL
 POP IY
 POP DE
 JP complete
group_190_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45098
 POP HL
 POP IY
 POP DE
 JP complete
group_191:
 LD A,IXL
group_191_search:
 CP 249
 JP C,group_191_search_left
group_191_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46022
 POP HL
 POP IY
 POP DE
 JP complete
group_191_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46016
 POP HL
 POP IY
 POP DE
 JP complete
group_192:
 LD A,IXL
group_192_search:
 CP 250
 JP C,group_192_search_left
group_192_search_right:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46658
 POP HL
 POP IY
 POP DE
 JP complete
group_192_search_left:
 LD A,0
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46652
 POP HL
 POP IY
 POP DE
 JP complete
group_193:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45062
 POP HL
 POP IY
 POP DE
 JP complete
group_194:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45068
 POP HL
 POP IY
 POP DE
 JP complete
group_195:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45074
 POP HL
 POP IY
 POP DE
 JP complete
group_196:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45080
 POP HL
 POP IY
 POP DE
 JP complete
group_197:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45086
 POP HL
 POP IY
 POP DE
 JP complete
group_198:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45098
 POP HL
 POP IY
 POP DE
 JP complete
group_199:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45116
 POP HL
 POP IY
 POP DE
 JP complete
group_200:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45140
 POP HL
 POP IY
 POP DE
 JP complete
group_201:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45200
 POP HL
 POP IY
 POP DE
 JP complete
group_202:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45242
 POP HL
 POP IY
 POP DE
 JP complete
group_203:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45296
 POP HL
 POP IY
 POP DE
 JP complete
group_204:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45308
 POP HL
 POP IY
 POP DE
 JP complete
group_205:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45326
 POP HL
 POP IY
 POP DE
 JP complete
group_206:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45338
 POP HL
 POP IY
 POP DE
 JP complete
group_207:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45368
 POP HL
 POP IY
 POP DE
 JP complete
group_208:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45380
 POP HL
 POP IY
 POP DE
 JP complete
group_209:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45398
 POP HL
 POP IY
 POP DE
 JP complete
group_210:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45440
 POP HL
 POP IY
 POP DE
 JP complete
group_211:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45464
 POP HL
 POP IY
 POP DE
 JP complete
group_212:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45524
 POP HL
 POP IY
 POP DE
 JP complete
group_213:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45560
 POP HL
 POP IY
 POP DE
 JP complete
group_214:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45620
 POP HL
 POP IY
 POP DE
 JP complete
group_215:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45638
 POP HL
 POP IY
 POP DE
 JP complete
group_216:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45650
 POP HL
 POP IY
 POP DE
 JP complete
group_217:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45698
 POP HL
 POP IY
 POP DE
 JP complete
group_218:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45758
 POP HL
 POP IY
 POP DE
 JP complete
group_219:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45782
 POP HL
 POP IY
 POP DE
 JP complete
group_220:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45800
 POP HL
 POP IY
 POP DE
 JP complete
group_221:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45830
 POP HL
 POP IY
 POP DE
 JP complete
group_222:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45854
 POP HL
 POP IY
 POP DE
 JP complete
group_223:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45896
 POP HL
 POP IY
 POP DE
 JP complete
group_224:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,45956
 POP HL
 POP IY
 POP DE
 JP complete
group_225:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46016
 POP HL
 POP IY
 POP DE
 JP complete
group_226:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46022
 POP HL
 POP IY
 POP DE
 JP complete
group_227:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46094
 POP HL
 POP IY
 POP DE
 JP complete
group_228:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46100
 POP HL
 POP IY
 POP DE
 JP complete
group_229:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46160
 POP HL
 POP IY
 POP DE
 JP complete
group_230:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46166
 POP HL
 POP IY
 POP DE
 JP complete
group_231:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46208
 POP HL
 POP IY
 POP DE
 JP complete
group_232:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46220
 POP HL
 POP IY
 POP DE
 JP complete
group_233:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46232
 POP HL
 POP IY
 POP DE
 JP complete
group_234:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46250
 POP HL
 POP IY
 POP DE
 JP complete
group_235:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46298
 POP HL
 POP IY
 POP DE
 JP complete
group_236:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46328
 POP HL
 POP IY
 POP DE
 JP complete
group_237:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46358
 POP HL
 POP IY
 POP DE
 JP complete
group_238:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46406
 POP HL
 POP IY
 POP DE
 JP complete
group_239:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46448
 POP HL
 POP IY
 POP DE
 JP complete
group_240:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46466
 POP HL
 POP IY
 POP DE
 JP complete
group_241:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46484
 POP HL
 POP IY
 POP DE
 JP complete
group_242:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46532
 POP HL
 POP IY
 POP DE
 JP complete
group_243:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46562
 POP HL
 POP IY
 POP DE
 JP complete
group_244:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46592
 POP HL
 POP IY
 POP DE
 JP complete
group_245:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46616
 POP HL
 POP IY
 POP DE
 JP complete
group_246:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46634
 POP HL
 POP IY
 POP DE
 JP complete
group_247:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46730
 POP HL
 POP IY
 POP DE
 JP complete
group_248:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46826
 POP HL
 POP IY
 POP DE
 JP complete
group_249:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46838
 POP HL
 POP IY
 POP DE
 JP complete
group_250:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46844
 POP HL
 POP IY
 POP DE
 JP complete
group_251:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46850
 POP HL
 POP IY
 POP DE
 JP complete
group_252:
 LD A,0
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 NOP
 LD SP,46856
 POP HL
 POP IY
 POP DE
 JP complete
handlers_end:
complete:
 NOP
 ASSERT $ < 0xB000
