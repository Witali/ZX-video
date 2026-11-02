"""Resident demo packing: complete AY grammars and independently decoded art.

Five paged banks hold immutable inputs. RAM7 retains the stock-ROM menu;
RAM2 holds code, the shared footer and one 5760-byte incoming illustration.
No disk read is needed after the first musical field.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'libraries/zx0/src'))
from zx0 import decompress
from music_codec import compress
from slides import picture_columns

NAMES = ('city','expedition','duel','portrait','guardian','underwater','gustave',
         'titan','monoco','esquie','renoir','lampmaster','visages','maelle',
         'paintress','sirene','gestral-village','gustave-sophie')
CACHE_BANKS = (0,4,6,1,3)
DISK_NAME = 'Expedition-33-Demo.trd'


def assets(raw_songs):
    encoded, dictionary, depth = compress(raw_songs)
    banks = [bytearray(b''.join(encoded))]
    assert len(banks[0]) <= 16384
    songs, offset = [], 0
    for data in encoded:
        songs.append(dict(offset=offset,start_bank_index=0,start_address=0xC000+offset,
                          compressed_bytes=len(data)))
        offset += len(data)
    manifest = {}
    for directory in (HERE/'artwork',HERE/'artwork/proposals'):
        manifest.update({i['name']:i for i in json.loads((directory/'compiled.json').read_text())['images']})
    pictures = []
    for name in NAMES:
        directory = HERE/'artwork' if (HERE/'artwork'/f'{name}.scr').exists() else HERE/'artwork/proposals'
        screen = (directory/f'{name}.scr').read_bytes()
        raw = b''.join(picture_columns(screen))
        packed = (HERE/'artwork/packed'/f'{name}.zx0').read_bytes()
        assert decompress(packed,limit=5760) == raw
        # Best fit retains each entire decoder input within one physical bank.
        choices = [(16384-len(b)-len(packed),i) for i,b in enumerate(banks) if len(b)+len(packed)<=16384]
        if choices:
            _, bank = min(choices)
        else:
            bank = len(banks)
            banks.append(bytearray())
        address = 0xC000+len(banks[bank])
        banks[bank].extend(packed)
        pictures.append(dict(name=name,bank=CACHE_BANKS[bank],address=address,
            compressed_bytes=len(packed),raw_bytes=len(raw),border=manifest[name]['border'],
            accent=screen[6144+22*32],scr_sha256=hashlib.sha256(screen).hexdigest()))
    assert len(banks)<=len(CACHE_BANKS)
    return songs,dictionary,depth,pictures,banks


def footer():
    screen = (HERE/'artwork/city.scr').read_bytes()
    return b''.join(screen[0x1080+i*256:0x1100+i*256] for i in range(8))
