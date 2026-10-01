"""Host-only CB45: CB44 bitmap modes with XOR against the old back attributes."""
import struct

from build_fap3_trd import sha
from dynamic_row_dictionary import decode_check
from probe_cell_codebook import indices


def encode(source,frames,start,end):
    raw=bytearray(source['raw']);assert raw[:4]==b'CB44'
    raw[:4]=b'CB45';at=2056
    for f in range(start,end):
        while True:
            length=struct.unpack_from('<H',raw,at)[0];at+=2
            if not length&0x8000:break
            assert not length&0x4000
            at+=3*(length&0x7fff)
        changed=indices(raw[at+72:at+144],576);tail=at+length-len(changed)
        previous=frames[f-2,3936:4512] if f>=2 else frames[0,3936:4512]
        for i,cell in enumerate(changed):
            assert raw[tail+i]==frames[f,3936+cell]
            raw[tail+i]^=int(previous[cell])
        at+=length
    assert at==len(raw);result=bytes(raw)
    proof=decode_check(result,frames,start,end,source['rows'])
    return dict(source,raw=result,raw_sha256=sha(result),proof=proof,attribute_xor=True)
