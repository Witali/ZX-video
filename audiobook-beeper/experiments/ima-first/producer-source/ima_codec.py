"""IMA ADPCM, reference shift/add rounding (IMA-WAV), low nibble first.

The disk stores headerless nibbles. Initial predictor/index are player
constants, reset at each loop. Decoding retains signed 16-bit precision;
only the PDM input is reduced to unsigned PCM8.
"""
import struct
import numpy as np

STEPS=(7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,
       88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,
       598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,
       2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,10442,
       11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767)
INDEX=(-1,-1,-1,-1,2,4,6,8)


def transition(predictor,index,code):
    step=STEPS[index]
    diff=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
    predictor=max(-32768,min(32767,predictor+(-diff if code&8 else diff)))
    index=max(0,min(88,index+INDEX[code&7]))
    return predictor,index


def decode(packed,predictor=0,index=0):
    pcm=np.empty(len(packed)*2,dtype=np.int16); indices=np.empty(len(pcm),dtype=np.uint8)
    for i,byte in enumerate(packed):
        for half,code in enumerate((byte&15,byte>>4)):
            predictor,index=transition(predictor,index,code)
            pcm[2*i+half]=predictor; indices[2*i+half]=index
    return pcm,indices


def encode(pcm8,predictor=0,index=0):
    if len(pcm8)%2: raise ValueError('need an even number of PCM8 samples')
    out=bytearray(len(pcm8)//2)
    for i,byte in enumerate(pcm8):
        target=(int(byte)-128)*256; error=target-predictor; sign=8 if error<0 else 0
        magnitude=abs(error); step=STEPS[index]
        # Nearest representable delta under the decoder's exact rounding.
        guess=min(7,(magnitude*4)//step)
        candidates=range(max(0,guess-1),min(7,guess+1)+1)
        code=sign|min(candidates,key=lambda d:abs(target-transition(predictor,index,sign|d)[0]))
        predictor,index=transition(predictor,index,code)
        out[i//2]|=code<<(4*(i%2))
    return bytes(out)


def decoder_table(base):
    """Four bytes/state+code: signed modular delta; next row plus sign tag.

    Row is 64-byte aligned. Pointer bit 0 records negative NONZERO delta,
    avoiding the unsigned-carry ambiguity for IMA index 0 /code 8 (delta 0).
    """
    assert base%256==0
    result=bytearray()
    for index,step in enumerate(STEPS):
        for code in range(16):
            diff=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
            negative=bool(code&8 and diff)
            next_index=max(0,min(88,index+INDEX[code&7]))
            result+=struct.pack('<HH',(-diff if negative else diff)&65535,
                                (base+64*next_index)|int(negative))
    return bytes(result)


def verification_wav(packed,predictor=0,index=0):
    """One WAV IMA block for an independent FFmpeg decode, not a disk format.

    WAV outputs its initial predictor as an extra first sample. The caller
    removes that sample when comparing the headerless native stream.
    """
    if len(packed)>32764: raise ValueError('verification block too large')
    block=struct.pack('<hBB',predictor,index,0)+packed
    samples=len(packed)*2+1
    fmt=struct.pack('<HHIIHHHH',0x11,1,8000,round(len(block)*8000/samples),len(block),4,2,samples)
    def chunk(tag,data): return tag+struct.pack('<I',len(data))+data+b'\0'*(len(data)%2)
    body=b'WAVE'+chunk(b'fmt ',fmt)+chunk(b'fact',struct.pack('<I',samples))+chunk(b'data',block)
    return b'RIFF'+struct.pack('<I',len(body))+body
