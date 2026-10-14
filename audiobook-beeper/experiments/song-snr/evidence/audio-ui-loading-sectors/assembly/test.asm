ORG 32906
cache_bar: EQU 0x5B78
cache_mode: EQU 0x5B72
INCLUDE "stream-audio-ui.asm"
ASSERT audio_ui_startup_end < 0x8340
DS 47424 - $
INCLUDE "stream-audio-ui-helper.asm"
ASSERT audio_ui_end < 0xBA00
DS 0xBB00 - $
cache_restore:
        LD E,A
        LD A,(cache_mode)
        CP 1
        JR NZ,cache_restore_low
        XOR A
        LD BC,0x1FFD
        OUT (C),A
cache_restore_low:
        LD A,E
        LD BC,0x7FFD
        OUT (C),A
        RET

