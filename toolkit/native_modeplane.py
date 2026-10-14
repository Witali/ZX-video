"""CB48 exact native cells with a two-bit mode plane and native row pairs.

Header/book are CB47-compatible. A frame begins with144 mode bytes for all
576 cells, then72 attribute-mask bytes, selected data and changed attributes.
Modes0 skip,1 book,2 raw8,3 special:0 front,1..8 single row,10 four pair
indices,40h..77h two changed rows packed as(row0<<3)|row1. ROWS holds the
fixed256-pair dictionary in two planar pages. No pixel approximation.
"""
from collections import Counter
import struct
import numpy as np
from build_fap3_trd import sha
from build_zxv_trd import spectrum_bitmap_offset
from native_cell_codebook import validate,patterns,history,MAX_PACKET
from probe_cell_codebook import mask,indices


def pack_zeros(data):
    out=bytearray();at=0
    while at<len(data):
        if data[at]:out.append(data[at]);at+=1;continue
        stop=at+1
        while stop<len(data) and not data[stop] and stop-at<255:stop+=1
        out+=bytes([0,stop-at]);at=stop
    return bytes(out)


def unpack_zeros(data,size):
    out=bytearray();at=0
    while at<len(data):
        value=data[at];at+=1
        if value:out.append(value)
        else:
            if at>=len(data) or not data[at]:raise ValueError('invalid zero run')
            out+=bytes(data[at]);at+=1
        if len(out)>size:raise ValueError('zero run exceeds plane')
    if len(out)!=size:raise ValueError('zero plane extent differs')
    return bytes(out)


def representation(frames,start,end,*,zero_runs=False,repeat_rows=False):
    if zero_runs and repeat_rows:raise ValueError('repeat-row experiment uses the fixed mode planes')
    validate(frames)
    current=np.stack([patterns(f) for f in frames[start:end]])
    back=np.concatenate([np.stack([patterns(frames[i]) if i>=0 else np.zeros((576,8),np.uint8)
        for i in (start-2,start-1)]),current[:-2]])[:end-start]
    front=np.concatenate([np.stack([patterns(frames[start-1]) if start else np.zeros((576,8),np.uint8)]),current[:-1]])
    changed=np.any(current!=back,-1);novel=changed & np.any(current!=front,-1)
    counts=Counter(current[f,c].tobytes() for f,c in zip(*np.nonzero(novel)))
    book=sorted(counts,key=lambda key:(-counts[key],key))[:256];book += [bytes(8)]*(256-len(book));lookup={key:i for i,key in enumerate(book)}
    paircounts=Counter(current[f,c,i:i+2].tobytes() for f,c in zip(*np.nonzero(novel))
        if current[f,c].tobytes() not in lookup for i in range(0,8,2))
    pairs=[bytes(2)]+[key for key in sorted(paircounts,key=lambda key:(-paircounts[key],key)) if key!=bytes(2)][:255]
    pairs += [bytes(2)]*(256-len(pairs));pairlookup={key:i for i,key in enumerate(pairs)}
    raw=bytearray((b'CB50' if repeat_rows else b'CB49' if zero_runs else b'CB48')+struct.pack('<HH',end-start,256)+b''.join(book));details=[]
    for local,frame in enumerate(range(start,end)):
        oldattrs=frames[frame-2,6240:6816] if frame>=2 else frames[0,6240:6816]
        attrs=np.flatnonzero(frames[frame,6240:6816]!=oldattrs).tolist()
        modes=bytearray(144);data=bytearray();kinds=Counter()
        for cell in np.flatnonzero(changed[local]):
            key=current[local,cell].tobytes();rows=np.flatnonzero(current[local,cell]!=back[local,cell]).tolist()
            if np.array_equal(current[local,cell],front[local,cell]):mode=3;value=b'\0';kind='front'
            elif key in lookup:mode=1;value=bytes([lookup[key]]);kind='book'
            elif len(rows)==1:mode=3;value=bytes([1+rows[0],current[local,cell,rows[0]]]);kind='single'
            elif len(rows)==2:
                mode=3;value=bytes([0x40|(rows[0]<<3)|rows[1],*(current[local,cell,r] for r in rows)]);kind='two'
            else:
                differences=[r for r in range(1,8) if key[r]!=key[r-1]]
                pair_ok=all(key[i:i+2] in pairlookup for i in range(0,8,2))
                if repeat_rows and len(differences)+1 <= (3 if pair_ok else 5):
                    mode=3;value=bytes([0x80|sum(1<<(r-1) for r in differences),key[0],*(key[r] for r in differences)]);kind='repeat'
                elif pair_ok:mode=3;value=bytes([10]+[pairlookup[key[i:i+2]] for i in range(0,8,2)]);kind='pairs'
                else:mode=2;value=key;kind='literal'
            modes[cell//4] |= mode<<((cell%4)*2);data+=value;kinds[kind]+=1
        attrmask=mask(attrs,576)
        if zero_runs:
            mm,am=pack_zeros(modes),pack_zeros(attrmask)
            prefix=bytes([len(mm),len(am)])+mm+am
        else:prefix=modes+attrmask
        body=prefix+data+frames[frame,6240:6816][attrs].tobytes()
        assert (6 if zero_runs else 216)<=len(body)<=MAX_PACKET
        raw+=struct.pack('<H',len(body))+body;details.append(dict(frame=frame,bytes=len(body),changed_cells=int(changed[local].sum()),**kinds))
    tables=bytes(p[0] for p in pairs)+bytes(p[1] for p in pairs)
    rows=dict(words=[0]*256,entries=256,tables_hex=tables.hex(),sha256=sha(tables),ram_bytes=512,table_address=0x9e00,
        lifetime='Immutable native two-row dictionary for this independent volume')
    raw=bytes(raw);proof=decode_check(raw,frames,start,end,rows)
    return dict(raw=raw,raw_sha256=sha(raw),rows=rows,details=details,dynamic_proof=proof,row_updates=0,unique_literal_rows=0,native_pixels=True)


def decode_check(raw,frames,start,end,rows):
    if raw[:4] not in (b'CB48',b'CB49',b'CB50') or struct.unpack_from('<HH',raw,4)!=(end-start,256):raise ValueError('invalid native-mode header')
    zero_runs=raw[:4]==b'CB49'
    book=[raw[8+i*8:16+i*8] for i in range(256)];pairs=bytes.fromhex(rows['tables_hex'])
    screens=[bytearray(history(frames,start-2)),bytearray(history(frames,start-1))];at=2056
    for frame in range(start,end):
        n,=struct.unpack_from('<H',raw,at);at+=2;stop=at+n
        if not (6 if zero_runs else 216)<=n<=MAX_PACKET or stop>len(raw):raise ValueError('invalid mode-plane packet')
        if zero_runs:
            ml,al=raw[at:at+2];at+=2
            modes=unpack_zeros(raw[at:at+ml],144);at+=ml
            attrs=indices(unpack_zeros(raw[at:at+al],72),576);at+=al
        else:modes=raw[at:at+144];attrs=indices(raw[at+144:at+216],576);at+=216
        target=screens[(frame-start)%2];front=screens[1-(frame-start)%2]
        for cell in range(576):
            mode=(modes[cell//4]>>((cell%4)*2))&3
            if not mode:continue
            y,x=divmod(cell,32);offsets=[spectrum_bitmap_offset(x,(y+3)*8+r) for r in range(8)]
            if mode==1:values=book[raw[at]];at+=1
            elif mode==2:values=raw[at:at+8];at+=8
            else:
                selector=raw[at];at+=1
                if selector==0:values=bytes(front[o] for o in offsets)
                elif raw[:4]==b'CB50' and selector&128:
                    values=bytearray([raw[at]]);at+=1
                    for row in range(1,8):
                        if selector&(1<<(row-1)):values.append(raw[at]);at+=1
                        else:values.append(values[-1])
                elif 1<=selector<=8:target[offsets[selector-1]]=raw[at];at+=1;continue
                elif selector==10:
                    indexes=raw[at:at+4];at+=4;values=bytes(b for i in indexes for b in (pairs[i],pairs[256+i]))
                elif 0x40<=selector<0x78:
                    a,b=(selector>>3)&7,selector&7
                    if not a<b:raise ValueError('unordered native row pair')
                    target[offsets[a]],target[offsets[b]]=raw[at:at+2];at+=2;continue
                else:raise ValueError('invalid native special selector')
            if len(values)!=8:raise ValueError('truncated native cell')
            for o,value in zip(offsets,values):target[o]=value
        for cell in attrs:target[6240+cell]=raw[at];at+=1
        if at!=stop or bytes(target)!=frames[frame].tobytes():raise ValueError(f'native-mode frame {frame} differs')
    if at!=len(raw):raise ValueError('native-mode tail differs')
    return dict(complete=True,frames=end-start,full_native_screens_exact=True,compared_bytes=(end-start)*6912)
