"""Bounded LZW with GIF-compatible codes, verified independently by Pillow.

8-bit alphabet, LSB-first codes, CLEAR=256, EOI=257; 9-bit initial width.
Reset one entry before the configured table fills (10..12 bits). No GIF
headers are counted as compressed video: the wrapper is a decoder oracle.
"""
import io,struct
from PIL import Image


def encode(raw,max_bits):
    if not 10<=max_bits<=12:raise ValueError('supported limits are 10..12')
    output=bytearray();reservoir=used=0;resets=0;peak=258
    def put(code,width):
        nonlocal reservoir,used
        reservoir|=code<<used;used+=width
        while used>=8:
            output.append(reservoir&255);reservoir>>=8;used-=8
    def fresh():return {bytes([i]):i for i in range(256)},258,9
    table,next_code,width=fresh();put(256,width);word=b''
    for value in raw:
        char=bytes([value]);longer=word+char
        if longer in table:word=longer;continue
        put(table[word],width)
        if next_code<(1<<max_bits)-1:
            table[longer]=next_code;next_code+=1;peak=max(peak,next_code)
            if next_code>1<<width and width<12:width+=1
        else:
            put(256,width);table,next_code,width=fresh();resets+=1
        word=char
    if word:
        put(table[word],width)
        if next_code==1<<width and width<12:width+=1
    put(257,width)
    if used:output.append(reservoir&255)
    return bytes(output),dict(resets=resets,peak_next_code=peak)


def decode_independent(packed,size):
    if not 1<=size<=65535:raise ValueError('GIF oracle width unsupported')
    shape=struct.pack('<HH',size,1)
    gif=b'GIF89a'+shape+b'\xf7\x00\x00'+b''.join(bytes([i,i,i]) for i in range(256))
    gif+=b'\x2c'+bytes(4)+shape+b'\x00\x08'
    gif+=b''.join(bytes([len(packed[i:i+255])])+packed[i:i+255] for i in range(0,len(packed),255))
    gif+=b'\x00\x3b'
    with Image.open(io.BytesIO(gif)) as image:
        image.load();return image.tobytes()
