"""G.711 A-law / mu-law bytes with exact PCM16 lookup decoding.

The decoder equations implement the segment/mantissa reconstruction of
ITU-T G.711. Exhaustive external checks use FFmpeg's independent decoder.
Each optional future Z80 lookup table is 256 signed words (512 bytes);
there is no predictor, index, previous-sample dependence or PCM buffer.
This module does not implement a Spectrum player.
"""
from functools import lru_cache
import subprocess
import numpy as np


@lru_cache(maxsize=2)
def decode_table(law):
    if law not in ('mulaw','alaw'):raise ValueError('law must be mulaw or alaw')
    result=[]
    for code in range(256):
        value=code^(255 if law=='mulaw' else 0x55)
        exponent=(value>>4)&7;mantissa=value&15
        if law=='mulaw':
            magnitude=((mantissa*8+132)<<exponent)-132
            sample=-magnitude if value&128 else magnitude
        else:
            magnitude=(mantissa*16+8 if exponent==0 else (mantissa*16+264)<<(exponent-1))
            sample=magnitude if value&128 else -magnitude
        result.append(sample)
    table=np.asarray(result,dtype='<i2');table.flags.writeable=False
    return table


def decode(data,law):
    return decode_table(law)[np.frombuffer(data,'u1')]


def encode(pcm16,law,ffmpeg):
    """PC encoding only. Return raw one-byte-per-sample G.711 payload."""
    decode_table(law)
    samples=np.asarray(pcm16)
    if samples.ndim!=1 or not np.issubdtype(samples.dtype,np.integer) or np.any((samples<-32768)|(samples>32767)):
        raise ValueError('need mono signed PCM16 integer samples')
    result=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','s16le','-ar','8000','-ac','1','-i','-',
                           '-c:a','pcm_'+law,'-f',law,'-'],input=samples.astype('<i2').tobytes(),capture_output=True,check=True)
    if len(result.stdout)!=len(samples):raise AssertionError('G.711 sample count changed')
    return result.stdout


def verify_tables(ffmpeg):
    results=[]
    for law in ('mulaw','alaw'):
        result=subprocess.run([ffmpeg,'-v','error','-nostdin','-f',law,'-ar','8000','-ac','1','-i','-',
                               '-f','s16le','-c:a','pcm_s16le','-'],input=bytes(range(256)),capture_output=True,check=True)
        expected=np.frombuffer(result.stdout,'<i2')
        if not np.array_equal(expected,decode_table(law)):raise AssertionError(law+' decoder differs from FFmpeg')
        results.append(dict(law=law,every_code_matches_ffmpeg=True,checked_codes=256,table_bytes=512))
    return results
