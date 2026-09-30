"""Fixed five-level row tables in the existing compact renderer and boot image.

One dictionary covers the entire independently bootable volume. Index zero
must mean a black row. No runtime table switch or renderer opcode changes.
"""
from contextlib import contextmanager
from unittest.mock import patch

import numpy as np
import build_long_video_trd as video
import five_level_dither as five
from fast_zx0_player import Builder as FastBuilder
from build_fap3_trd import sha, padded, sectors


def encode_states(frames):
    words = np.stack([five.unpack_words(frame[:3840]) for frame in frames])
    counts = np.bincount(words.ravel(), minlength=625)
    book = [0]+sorted((i for i in range(1,625) if counts[i]), key=lambda i:(-int(counts[i]),i))
    if len(book) > 256:
        raise ValueError(f'whole-volume dictionary needs {len(book)} rows; maximum 256')
    lookup = np.zeros(625, dtype=np.uint8)
    lookup[book] = np.arange(len(book), dtype=np.uint8)
    states = np.stack([np.frombuffer(lookup[w].tobytes()+frame[3840:],dtype=np.uint8)
                       for w,frame in zip(words,frames)])
    tables = bytes(five.TOP[w] for w in book)+bytes(256-len(book))
    tables += bytes(five.BOTTOM[w] for w in book)+bytes(256-len(book))
    metadata = dict(words=book,entries=len(book),tables_hex=tables.hex(),sha256=sha(tables),
                    ram_bytes=512,table_address=0x9e00,renderer_opcode_delta_tstates=0,
                    lifetime='entire volume, including cold checkpoint and both alternating screens')
    with reference_tables(metadata):
        for frame,state in zip(frames,states):
            if video.expand_compact_screen(state.tobytes()) != five.expand(frame):
                raise AssertionError('dictionary changes native pixels or attributes')
    return states,metadata


@contextmanager
def reference_tables(metadata):
    """Scope the legacy host reference to the table bytes actually installed."""
    data = bytes.fromhex(metadata['tables_hex'])
    if len(data)!=512 or data[0] or data[256] or sha(data)!=metadata['sha256']:
        raise ValueError('invalid fixed dictionary')
    with patch.object(video,'PLAYER_DITHER_TOP',data[:256]), patch.object(video,'PLAYER_DITHER_BOTTOM',data[256:]):
        yield


def display_screen(state, metadata):
    from frame_output_pipeline import display_screen as legacy
    if 'row_dictionary' not in metadata:
        return legacy(state,black_borders=True)
    with reference_tables(metadata['row_dictionary']):
        return legacy(state,black_borders=True)


class Builder(FastBuilder):
    def __init__(self,*args,row_dictionary,**kwargs):
        if kwargs.get('startup_delta'): raise ValueError('use a directly compressed startup table section')
        self.row_dictionary=row_dictionary
        super().__init__(*args,**kwargs)

    def ram(self,*args):
        sections,m=super().ram(*args)
        tables=bytes.fromhex(self.row_dictionary['tables_hex'])
        self.expected_banks[2][0x1e00:0x2000]=tables
        result=[]
        for section in sections:
            at=section['address']&16383
            raw=bytes(self.expected_banks[section['bank']][at:at+section['decoded_bytes']])
            if sha(raw)==section['sha256']:
                result.append(section); continue
            if section.get('startup_delta'): raise ValueError('unexpected startup delta section')
            coded=self.compress(raw)
            result.append(dict(section,data=padded(coded),compressed_bytes=len(coded),sectors=sectors(coded),sha256=sha(raw)))
        m['row_dictionary']=self.row_dictionary
        return result,m
