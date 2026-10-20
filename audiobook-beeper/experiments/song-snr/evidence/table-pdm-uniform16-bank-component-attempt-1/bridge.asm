; Bounded uncontended Z80 component, not a complete audio player.
; Main BC ends in FE, D=16, E and HL/IX/IY/SP retain their caller values.
; ALT HL is the live IMA row and must survive. ALT BC delta and ALT DE source
; are dead: both nibbles of the last source byte were already consumed/cached.
; AF' remains live and is untouched. Main A/F are scratch.
;
; The source-high/page immediate word is a host-patched static descriptor.
; ALT DE first holds D=page byte/E=next source high, then returns to the next
; source address (high<<8). No lookup SP, stack, RAM workspace or calls are used.
;
; Normal OUT(C),r takes12T, immediate OUT(FE),A takes11T. Count from one real
; speaker-write callback to the next; the NEXT output instruction belongs to
; each interval. The switch gap therefore has17T body plus11T immediate OUT.
; The page gap is pageOUT12 + EXX4 + normalOUT12 =28T, with no ULA port alias.
 ORG 0x8000
bridge_0:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_0:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_1:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_1:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_2:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_2:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_3:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_3:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_4:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_4:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_5:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_5:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_6:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_6:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_7:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_7:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_8:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_8:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_9:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_9:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_10:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_10:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_11:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_11:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_12:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_12:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_13:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_13:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_14:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_14:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_15:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_15:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_16:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_16:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_17:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_17:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_18:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_18:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_19:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_19:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_20:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_20:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_21:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_21:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_22:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_22:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_23:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_23:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_24:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_24:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_25:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_25:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_26:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_26:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_27:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_27:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_28:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_28:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_29:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_29:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_30:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_30:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_31:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_31:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_32:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_32:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_33:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_33:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_34:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_34:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_35:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_35:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_36:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_36:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_37:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_37:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_38:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_38:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_39:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_39:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_40:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_40:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_41:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_41:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_42:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_42:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_43:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_43:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_44:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_44:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_45:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_45:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_46:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_46:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_47:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_47:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_48:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_48:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_49:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_49:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_50:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_50:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_51:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_51:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_52:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_52:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_53:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_53:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_54:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_54:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_55:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_55:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_56:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_56:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_57:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_57:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_58:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_58:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_59:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_59:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_60:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_60:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_61:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_61:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_62:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_62:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_63:
 DB 0xED,0x71
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_63:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_64:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_64:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_65:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_65:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_66:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_66:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_67:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_67:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_68:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_68:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_69:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_69:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_70:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_70:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_71:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_71:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_72:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_72:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_73:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_73:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_74:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_74:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_75:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_75:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_76:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_76:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_77:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_77:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_78:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_78:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_79:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_79:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_80:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_80:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_81:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_81:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_82:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_82:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_83:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_83:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_84:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_84:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_85:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_85:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_86:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_86:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_87:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_87:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_88:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_88:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_89:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_89:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_90:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_90:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_91:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_91:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_92:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_92:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_93:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_93:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_94:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_94:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_95:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,0
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_95:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_96:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_96:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_97:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_97:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_98:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_98:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_99:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_99:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_100:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_100:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_101:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_101:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_102:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_102:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_103:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_103:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_104:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_104:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_105:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_105:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_106:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_106:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_107:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_107:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_108:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_108:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_109:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_109:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_110:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_110:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_111:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,0
 OUT (0xFE),A
descriptor_111:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_112:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_112:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_113:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_113:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_114:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_114:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_115:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_115:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_116:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_116:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_117:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_117:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_118:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_118:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_119:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_119:
 LD DE,0x18C0
 LD A,0
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_120:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_120:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_121:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_121:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_122:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_122:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_123:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_123:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 DB 0xED,0x71
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_124:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_124:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_125:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_125:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 DB 0xED,0x71
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
bridge_126:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_126:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 DB 0xED,0x71
 JP complete
bridge_127:
 OUT (C),D
 ; Switch to dead decoder scratches; INC BC is harmless padding.
 EXX
 LD A,16
 INC BC
 OUT (0xFE),A
 ; The two ten-T loads pair with the next constant-bit seven-T load.
 LD BC,0x7FFD
 LD A,16
 OUT (0xFE),A
descriptor_127:
 LD DE,0x18C0
 LD A,16
 OUT (0xFE),A
 ; This page OUT is not a speaker write; resume the main output registers.
 OUT (C),D
 EXX
 OUT (C),D
 ; Restore the source cursor while preserving ALT HL and all main pairs.
 EXX
 LD D,E
 EXX
 NOP
 OUT (C),D
 EXX
 XOR A
 LD E,A
 EXX
 OUT (C),D
 JP complete
complete:
 NOP
