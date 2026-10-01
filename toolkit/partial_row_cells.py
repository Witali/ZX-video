"""CB46 host prototype: mode 3 changes exactly one row-pair of a literal cell.

Mode payload is row-pair number 0..3 followed by its mutable row-table index.
The other three pairs remain in the physical back screen. Other CB44 modes,
row updates, attributes and the static book are unchanged.
"""
import struct
import numpy as np
from build_fap3_trd import sha
from dynamic_row_dictionary import patterns,decode_check
from probe_cell_codebook import indices


def encode(base,frames,start,end):
    raw=base['raw'];assert raw[:4]==b'CB44'
    output=bytearray(b'CB46'+raw[4:2056]);at=2056;details=[]
    for frame in range(start,end):
        while True:
            length=struct.unpack_from('<H',raw,at)[0];at+=2
            if not length&0x8000:break
            size=3*(length&0x7fff);output+=struct.pack('<H',length)+raw[at:at+size];at+=size
        packet=raw[at:at+length];at+=length
        cells=indices(packet[:72],576);width=(len(cells)+3)//4
        modes=bytearray(packet[144:144+width]);cursor=144+width;payload=bytearray()
        current=patterns(frames[frame]);previous=patterns(frames[frame-2]) if frame>=2 else np.zeros_like(current)
        changed=np.sum(current!=previous,axis=1);partial=0;literal_counts=[0]*5
        for i,cell in enumerate(cells):
            mode=(modes[i//4]>>((i%4)*2))&3
            assert mode in (0,1,2),'host neighbour mode is not CB46 input'
            size=(4,1,0)[mode];value=packet[cursor:cursor+size];cursor+=size
            if mode==0:
                count=int(changed[cell]);literal_counts[count]+=1
                if count==1:
                    row=int(np.flatnonzero(current[cell]!=previous[cell])[0])
                    value=bytes([row,value[row]]);modes[i//4]|=3<<((i%4)*2);partial+=1
            payload+=value
        body=packet[:144]+modes+payload+packet[cursor:]
        output+=struct.pack('<H',len(body))+body
        details.append(dict(frame=frame,literal_cells_by_changed_rows=literal_counts,
            partial_cells=partial,raw_bytes_saved=2*partial,packet_bytes_before=length,packet_bytes=len(body)))
    assert at==len(raw)
    data=bytes(output);proof=decode_check(data,frames,start,end,base['rows'])
    return dict(raw=data,rows=base['rows'],details=details,raw_sha256=sha(data),proof=proof)
