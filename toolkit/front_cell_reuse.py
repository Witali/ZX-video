"""Host-only CB44: reuse exact cells from the immutable previous front screen.

Two-bit modes: 0 four row indices; 1 cell-book index; 2 same front position;
3 signed one-byte front-cell displacement. Attributes remain unchanged.
No Spectrum player accepts CB44 yet.
"""
import struct

import numpy as np

from build_fap3_trd import sha
from dynamic_row_dictionary import patterns,decode_check
from probe_cell_codebook import indices


def representation(frames,start,end):
    from dynamic_row_dictionary import representation as rows
    base=rows(frames,start,end,book_front_reuse=True)
    result=encode(base,frames,start,end)
    return dict(base,**{k:v for k,v in result.items() if k not in ('details','proof')},
        details=[dict(old,**new) for old,new in zip(base['details'],result['details'])],
        dynamic_proof=result['proof'],front_reuse=True)


def encode(base,frames,start,end,*,neighbours=False):
    raw=base['raw'];assert raw[:4]==b'CB42'
    output=bytearray(b'CB44'+raw[4:2056]);at=2056;details=[]
    for f in range(start,end):
        while True:
            length=struct.unpack_from('<H',raw,at)[0];at+=2
            if not length&0x8000:break
            count=length&0x7fff
            output+=struct.pack('<H',length)+raw[at:at+count*3];at+=count*3
        packet=raw[at:at+length];at+=length
        cells=indices(packet[:72],576);width=(len(cells)+7)//8
        old_modes=packet[144:144+width];cursor=144+width
        modes=bytearray((2*len(cells)+7)//8);payload=bytearray();same=moved=0
        current=patterns(frames[f]);front=patterns(frames[f-1]) if f else np.zeros_like(current)
        for i,cell in enumerate(cells):
            old_mode=(old_modes[i//8]>>(i%8))&1;size=1 if old_mode else 4
            value=packet[cursor:cursor+size];cursor+=size;mode=old_mode
            if np.array_equal(current[cell],front[cell]):
                mode=2;value=b'';same+=1
            elif neighbours and not old_mode:
                y,x=divmod(cell,32)
                for dy,dx in ((0,-1),(0,1),(-1,0),(1,0),(-1,-1),(-1,1),(1,-1),(1,1)):
                    if 0<=y+dy<18 and 0<=x+dx<32:
                        offset=dy*32+dx
                        if np.array_equal(current[cell],front[cell+offset]):
                            mode=3;value=bytes([offset&255]);moved+=1;break
            modes[i//4]|=mode<<((i%4)*2);payload+=value
        body=packet[:144]+modes+payload+packet[cursor:]
        output+=struct.pack('<H',len(body))+body
        details.append(dict(frame=f,changed_cells=len(cells),front_same_cells=same,
            front_moved_cells=moved,packet_bytes_before=length,packet_bytes=len(body)))
    assert at==len(raw)
    data=bytes(output);proof=decode_check(data,frames,start,end,base['rows'])
    return dict(raw=data,raw_sha256=sha(data),rows=base['rows'],details=details,proof=proof)
