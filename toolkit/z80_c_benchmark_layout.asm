; Standalone component map; the host harness calls _entry directly.
; No CRT or platform state is assumed. This is not a Spectrum RAM layout.
SECTION code_compiler
ORG $0200
SECTION code_clib
SECTION code_l_sccz80
SECTION code_l_sdcc
SECTION code_math
SECTION rodata_compiler
SECTION bss_compiler
ORG $9000
