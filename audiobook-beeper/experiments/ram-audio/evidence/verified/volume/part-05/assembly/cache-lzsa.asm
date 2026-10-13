; Syntax-adapted forward LZSA2 decoder; original default instructions.
;
;  Speed-optimized LZSA2 decompressor by spke & uniabis (210 bytes)
;
;  ver.00 by spke for LZSA 1.0.0 (02-07/06/2019, 218 bytes);
;  ver.01 by spke for LZSA 1.0.5 (24/07/2019, added support for backward decompression);
;  ver.02 by spke for LZSA 1.0.6 (27/07/2019, fixed a bug in the backward decompressor);
;  ver.03 by uniabis (30/07/2019, 213(-5) bytes, +3.8% speed and support for Hitachi HD64180);
;  ver.04 by spke for LZSA 1.0.7 (01/08/2019, 214(+1) bytes, +0.2% speed and small re-organization of macros);
;  ver.05 by spke (27/08/2019, 216(+2) bytes, +1.1% speed);
;  ver.06 by spke for LZSA 1.1.0 (26/09/2019, added full revision history);
;  ver.07 by spke for LZSA 1.1.1 (10/10/2019, +0.2% speed and an option for unrolled copying of long matches);
;  ver.08 by spke (07-08/04/2022, 210(-6) bytes, +1.7% speed, using self-modifying code by default)
;
;  The data must be compressed using the command line compressor by Emmanuel Marty
;  The compression is done as follows:
;
;  lzsa.exe -f2 -r <sourcefile> <outfile>
;
;  where option -r asks for the generation of raw (frame-less) data.
;
;  The decompression is done in the standard way:
;
;  ld hl,FirstByteOfCompressedData
;  ld de,FirstByteOfMemoryForDecompressedData
;  call DecompressLZSA2
;
;  Backward compression is also supported; you can compress files backward using:
;
;  lzsa.exe -f2 -r -b <sourcefile> <outfile>
;
;  and decompress the resulting files using:
;
;  ld hl,LastByteOfCompressedData
;  ld de,LastByteOfMemoryForDecompressedData
;  call DecompressLZSA2
;
;  (do not forget to uncomment the BACKWARD_DECOMPRESS option in the decompressor).
;
;  Of course, LZSA2 compression algorithms are (c) 2019 Emmanuel Marty,
;  see https://github.com/emmanuel-marty/lzsa for more information
;
;  Drop me an email if you have any comments/ideas/suggestions: zxintrospec@gmail.com
;
;  This software is provided 'as-is', without any express or implied
;  warranty.  In no event will the authors be held liable for any damages
;  arising from the use of this software.
;
;  Permission is granted to anyone to use this software for any purpose,
;  including commercial applications, and to alter it and redistribute it
;  freely, subject to the following restrictions:
;
;  1. The origin of this software must not be misrepresented; you must not
;     claim that you wrote the original software. If you use this software
;     in a product, an acknowledgment in the product documentation would be
;     appreciated but is not required.
;  2. Altered source versions must be plainly marked as such, and must not be
;     misrepresented as being the original software.
;  3. This notice may not be removed or altered from any source distribution.
;	DEFINE	UNROLL_LONG_MATCHES						; uncomment for faster decompression of very compressible data (+38 bytes)
;	DEFINE	BACKWARD_DECOMPRESS						; uncomment for data compressed with option -b (+5 bytes, -3.2% speed)
		; HL = DE - HL
DecompressLZSA2:
        ld b,0
        scf
        EX AF,AF'
        jr ReadToken
ManyLiterals:
        ld a,18
        ADD A,(HL)
        INC HL
        jr nc,CopyMoreLiterals
        ld c,(hl)
        INC HL
        ld a,b
        ld b,(hl)
        jr ReadToken_NEXTHLuseBC
MoreLiterals:
        ld b,(hl)
        INC HL
        scf
        EX AF,AF'
        jr nc,MoreLiterals_noUpdate
        ld a,(hl)
        or a
        EX AF,AF'
        ld a,(hl)
        INC HL
        rrca
        rrca
        rrca
        rrca
MoreLiterals_noUpdate:
        or 0xF0
        inc a
        jr z,ManyLiterals
        sub 0xF0-3+1
CopyMoreLiterals:
        ld c,a
        ld a,b
        ld b,0
        LDI
        LDI
        LDIR
        or a
        jp p,CASE0xx
        cp 0b11000000
        jr c,CASE10x
CASE11x:
        cp 0b11100000
        jr nc,MatchLen
CASE110:
        ld b,(hl)
        INC HL
        jr ReadOffsetC
Literals0011:
        jr nz,MoreLiterals
NoLiterals:
        or (hl)
        INC HL
        jp m,CASE1xx
CASE0xx:
        cp 0b01000000
        jr c,CASE00x
CASE01x:
        dec b
        cp 0b01100000
        rl b
ReadOffsetC:
        ld c,(hl)
        INC HL
SaveOffset:
        ld (CopyMatch_PrevOffset),bc
        ld b,0
MatchLen:
        inc a
        and 0b00000111
        jr z,LongerMatch
        inc a
CopyMatch:
        ld c,a
CopyMatch_useC:
        push hl
CopyMatch_PrevOffset: EQU $+1
        ld hl,0
        ADD HL,DE
        LDI
        LDIR
CopyMatch_popSrc:
        pop hl
ReadToken:
        ld a,(hl)
        and 0b00011000
        jp pe,Literals0011
        rrca
        rrca
        rrca
        ld c,a
        ld a,(hl)
ReadToken_NEXTHLuseBC:
        INC HL
        LDIR
        or a
        jp p,CASE0xx
CASE1xx:
        cp 0b11000000
        jr nc,CASE11x
CASE10x:
        ld c,a
        EX AF,AF'
        jr nc,CASE10x_noUpdate
        ld a,(hl)
        or a
        EX AF,AF'
        ld a,(hl)
        INC HL
        rrca
        rrca
        rrca
        rrca
CASE10x_noUpdate:
        or 0xF0
        ld b,a
        ld a,c
        cp 0b10100000
        dec b
        rl b
        jr ReadOffsetC
CASE00x:
        ld b,a
        EX AF,AF'
        jr nc,CASE00x_noUpdate
        ld a,(hl)
        or a
        EX AF,AF'
        ld a,(hl)
        INC HL
        rrca
        rrca
        rrca
        rrca
CASE00x_noUpdate:
        or 0xF0
        ld c,a
        ld a,b
        cp 0b00100000
        rl c
        ld b,0xFF
        jr SaveOffset
LongerMatch:
        scf
        EX AF,AF'
        jr nc,LongerMatch_noUpdate
        ld a,(hl)
        or a
        EX AF,AF'
        ld a,(hl)
        INC HL
        rrca
        rrca
        rrca
        rrca
LongerMatch_noUpdate:
        or 0xF0
        sub 0xF0-9
        cp 15+9
        jr c,CopyMatch
LongMatch:
        ADD A,(HL)
        INC HL
        jr nc,CopyMatch
        ld c,(hl)
        INC HL
        ld b,(hl)
        INC HL
        jr nz,CopyMatch_useC
        ret
