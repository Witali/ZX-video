"""Integer SD2 driven directly by compact eight-bit audio bytes, PC model.

There is no expanded PCM audio buffer: read one code, look up its level,
and hold that level for this sample's PDM decisions. The returned bit array
is an observation trace for offline measurement, not a proposed RAM buffer.
No Z80 cycle cost or memory layout is claimed by this host implementation.
"""
import numpy as np
from g711_codec import decode_table


def modulate(data,encoding,slots=16):
    if encoding not in ('pcm8','mulaw','alaw') or slots not in (8,16):
        raise ValueError('supported encodings: pcm8/mulaw/alaw; slots: 8/16')
    table=None if encoding=='pcm8' else decode_table(encoding)
    bits=np.empty(len(data)*slots,dtype='u1');q=recent=peak=0;offset=0
    scale=65536
    for code in data:
        # Inverse companding is performed HERE, at the modulator input,
        # once per source sample. Preserve all16 bits of the table value.
        x=code*256 if table is None else int(table[code])+32768
        for _ in range(slots):
            u=x+q+recent;bit=int(u>=scale//2)
            recent=u-scale*bit;q+=x-scale*bit
            peak=max(peak,abs(q),abs(recent))
            if peak>8*scale:raise ValueError('SD2 state bound exceeded; no clipping applied')
            bits[offset]=bit;offset+=1
    return bits,dict(input_bytes=len(data),bytes_per_sample=1,
                     expanded_pcm_audio_buffer_bytes=0,
                     code_to_pcm16_table_bytes=0 if table is None else 512,
                     feedback_coordinates=2,model_storage_bits_per_coordinate=32,
                     maximum_absolute_integer_state=peak,state_peak=peak/scale,
                     playback_pipeline='read code -> inverse-compand in modulator -> PDM decisions',
                     scope='PC streaming model; output array is measurement trace, not Spectrum RAM')
