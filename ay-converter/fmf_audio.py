"""Parse Fuse's requested uncompressed PCM-mono FMF recording subset.

Preserved from audiobook-beeper/record_pcm.py, without the beeper recorder CLI.
"""
import numpy as np


def read_fmf(blob):
    """Decode the uncompressed standard-screen PCM-mono subset we request."""
    if blob[:8] != b'FMF_V1eU' or blob[9] != ord('$'):
        raise ValueError('expected little-endian uncompressed standard FMF')
    pos = 16
    frame = 0
    audio = bytearray()
    chunks = []
    timing_codes = set()
    ended = False

    def skip_rle(count):
        nonlocal pos
        written = 0
        while written < count:
            value = blob[pos]
            pos += 1
            written += 1
            if written < count and blob[pos] == value:
                written += 1 + blob[pos+1]
                pos += 2
        if written != count:
            raise ValueError('invalid FMF screen run')

    while pos < len(blob):
        tag = chr(blob[pos])
        if tag == '$':
            size = blob[pos+4]*int.from_bytes(blob[pos+5:pos+7], 'little')
            pos += 7
            skip_rle(size)
            skip_rle(size)
        elif tag == 'N':
            timing_codes.add(chr(blob[pos+3]))
            frame += blob[pos+1]
            pos += 4
        elif tag == 'S':
            rate = int.from_bytes(blob[pos+2:pos+4], 'little')
            if blob[pos+1] != ord('P') or blob[pos+4] != ord('M') or rate != 44100:
                raise ValueError('expected PCM16 mono 44100 Hz')
            count = int.from_bytes(blob[pos+5:pos+7], 'little') + 1
            pos += 7
            chunks.append((frame, len(audio)//2, count))
            audio.extend(blob[pos:pos+count*2])
            pos += count*2
        elif tag == 'X':
            pos += 1
            ended = True
        else:
            raise ValueError(f'unknown FMF block {tag!r} at {pos}')
    if pos != len(blob) or not ended or len(timing_codes) != 1:
        raise ValueError('incomplete or mixed-machine FMF')
    return np.frombuffer(audio, '<i2'), chunks, timing_codes.pop()
