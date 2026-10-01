"""CB42: exact CB41 cells with a mutable 256-entry row cache.

The encoder knows future literal-row uses and evicts the farthest next use.
Screen history and the physical cell book never depend on cache indices.
Control words 8001h..8100h replace 1..256 rows before the next frame;
each replacement is (index, top byte, bottom byte). Ordinary frame packets
retain CB41's masks, mode bits, cell indices and four-row literal fallback.
"""
from collections import Counter, deque
import struct

import numpy as np

import five_level_dither as five
from build_fap3_trd import sha
from build_zxv_trd import spectrum_bitmap_offset
from probe_cell_codebook import mask, indices


def patterns(frame):
    words = five.unpack_words(frame[:3840].tobytes()).astype('<u2')
    return np.ascontiguousarray(words[12:84].reshape(18,4,32).transpose(0,2,1).reshape(576,4))


def screen(frames, index):
    if index >= 0:
        return b''.join(five.expand(frames[index].tobytes()))
    if index not in (-2,-1):
        raise ValueError('invalid initial screen history')
    return bytes(6144) + frames[0,3840:].tobytes()


def bitmap(key):
    words = np.frombuffer(key, '<u2')
    return bytes(value for word in words for value in (five.TOP[word],five.BOTTOM[word]))


def encode(frames, start, end, *, cell_window=None, book_front_reuse=False):
    if not 0 <= start < end <= len(frames) or end-start > 10922:
        raise ValueError('invalid volume extent')
    current = np.stack([patterns(frame) for frame in frames[start:end]])
    previous = np.concatenate((np.stack([patterns(frames[i]) if i>=0 else
        np.zeros((576,4),dtype='<u2') for i in (start-2,start-1)]),current[:-2]),axis=0)[:end-start]
    changed = np.any(current != previous,axis=2)
    counts = Counter(current[f,c].tobytes() for f,c in zip(*np.nonzero(changed)))
    book_counts=counts
    if book_front_reuse:
        if cell_window is not None:raise ValueError('front-reuse book fitting requires a static cell book')
        front=np.concatenate((previous[1:2] if end-start>1 else np.stack([
            patterns(frames[start-1]) if start else np.zeros((576,4),dtype='<u2')]),current[:-1]),axis=0)
        novel=changed & np.any(current!=front,axis=2)
        book_counts=Counter(current[f,c].tobytes() for f,c in zip(*np.nonzero(novel)))
    book = sorted(book_counts,key=lambda key:(-book_counts[key],key))[:256]
    book += [bytes(8)]*(256-len(book))
    lookup = {key:i for i,key in enumerate(book)}
    cell_updates=[[] for _ in range(end-start)]
    if cell_window is not None:
        from dynamic_cell_dictionary import plan
        book,symbols,cell_updates=plan(current,changed,cell_window)
        book=[key if key is not None else bytes(8) for key in book]
    else:
        symbols=np.full(changed.shape,-1,dtype=np.int16)
        for f,c in zip(*np.nonzero(changed)):
            symbols[f,c]=lookup.get(current[f,c].tobytes(),-1)
    required, coded, literal = [], [], []
    for f in range(end-start):
        cells = np.flatnonzero(changed[f]).tolist()
        modes = [j for j,c in enumerate(cells) if symbols[f,c]>=0]
        raw_cells = [c for c in cells if symbols[f,c]<0]
        used = set(map(int,current[f,raw_cells].ravel()))
        if len(used | {0}) > 256:
            raise ValueError('one frame needs more than 256 literal rows')
        required.append(used); coded.append(modes); literal.append(raw_cells)
    future = {word:deque() for word in range(625)}
    for f, words in enumerate(required):
        for word in words:
            future[word].append(f)
    # Index zero remains black for borders and legacy bootstrap compatibility.
    first_use = sorted((w for w in range(1,625) if future[w]),key=lambda w:(future[w][0],w))
    cache = [0]+first_use[:255]
    cache += [None]*(256-len(cache))
    initial = cache.copy()
    slots = {w:i for i,w in enumerate(cache) if w is not None}
    tables = bytes(five.TOP[w] if w is not None else 0 for w in cache)
    tables += bytes(five.BOTTOM[w] if w is not None else 0 for w in cache)
    row_meta = dict(words=[w if w is not None else 0 for w in cache],entries=256,
        tables_hex=tables.hex(),sha256=sha(tables),ram_bytes=512,table_address=0x9e00,
        lifetime='Mutable CB42 cache; index zero is permanently black')
    table = b''.join(map(bitmap,book))
    output = bytearray((b'CB42' if cell_window is None else b'CB43')+struct.pack('<HH',end-start,256)+table)
    details = []
    for f, needed in enumerate(required):
        if cell_updates[f]:
            output+=struct.pack('<H',0xc000|len(cell_updates[f]))
            for slot,key in cell_updates[f]:output+=bytes([slot])+bitmap(key)
        patches = []
        for word in sorted(needed - slots.keys()):
            available = [i for i,w in enumerate(cache) if i and w not in needed]
            def next_use(i):
                old = cache[i]
                return (end-start+1 if old is None or not future[old] else future[old][0],i)
            victim = max(available,key=next_use)
            old = cache[victim]
            if old is not None:
                del slots[old]
            cache[victim]=word; slots[word]=victim
            patches.append((victim,five.TOP[word],five.BOTTOM[word]))
        if patches:
            output += struct.pack('<H',0x8000|len(patches))
            output += bytes(value for patch in patches for value in patch)
        for word in needed:
            assert future[word].popleft() == f
        absolute = start+f
        cells = np.flatnonzero(changed[f]).tolist()
        attrs = frames[absolute,3936:4512]
        old_attrs = frames[absolute-2,3936:4512] if absolute>=2 else frames[0,3936:4512]
        attr_changed = np.flatnonzero(attrs!=old_attrs).tolist()
        payload = bytearray(mask(cells,576)+mask(attr_changed,576)+mask(coded[f],len(cells)))
        for cell in cells:
            symbol=int(symbols[f,cell])
            payload += bytes([symbol]) if symbol>=0 else bytes(slots[int(w)] for w in current[f,cell])
        payload += bytes(attrs[c] for c in attr_changed)
        assert 144 <= len(payload) <= 3096
        output += struct.pack('<H',len(payload))+payload
        details.append(dict(frame=absolute,changed_cells=len(cells),book_cells=len(coded[f]),
            literal_cells=len(literal[f]),attribute_cells=len(attr_changed),packet_bytes=len(payload),
            row_updates=len(patches),row_update_bytes=3*len(patches)+(2 if patches else 0)))
        if cell_window is not None:
            details[-1].update(cell_updates=len(cell_updates[f]),
                cell_update_bytes=9*len(cell_updates[f])+(2 if cell_updates[f] else 0))
    return dict(raw=bytes(output),rows=row_meta,details=details,
        row_updates=sum(d['row_updates'] for d in details),initial_cache=initial,
        unique_literal_rows=len({w for s in required for w in s}),
        unique_changed_patterns=len(counts),raw_sha256=sha(output),
        cell_updates=sum(map(len,cell_updates)))


def decode_check(data, frames, start, end, row_meta):
    """Independent byte parser checks both physical screens after every frame."""
    if data[:4] not in (b'CB42',b'CB43',b'CB44',b'CB45') or struct.unpack_from('<HH',data,4)!=(end-start,256):
        raise ValueError('invalid dynamic dictionary header')
    cache = bytearray.fromhex(row_meta['tables_hex'])
    if len(cache)!=512 or cache[0] or cache[256]:
        raise ValueError('invalid initial row cache')
    book = [data[8+i*8:16+i*8] for i in range(256)]
    screens = [bytearray(screen(frames,start-2)),bytearray(screen(frames,start-1))]
    at, updates, book_updates, hashes = 2056, 0, 0, []
    for frame in range(start,end):
        while True:
            length, = struct.unpack_from('<H',data,at); at+=2
            if not length & 0x8000:
                break
            is_book=bool(length&0x4000)
            if is_book and data[:4]!=b'CB43':raise ValueError('invalid row update count (cell replacement requires CB43)')
            count=length & 0x3fff
            if not 1<=count<=256:
                raise ValueError('invalid row update count')
            seen = set()
            for _ in range(count):
                if is_book:
                    index=data[at];at+=1
                    if index in seen:raise ValueError('duplicate cell replacement')
                    seen.add(index);book[index]=data[at:at+8];at+=8
                    continue
                index, top, bottom = data[at:at+3]; at+=3
                if index in seen or index==0 and (top or bottom):
                    raise ValueError('invalid row replacement')
                seen.add(index); cache[index]=top; cache[256+index]=bottom
            if is_book:book_updates+=count
            else:updates+=count
        front_modes=data[:4] in (b'CB44',b'CB45')
        if not 144<=length<=(3168 if front_modes else 3096):
            raise ValueError('invalid frame packet length')
        stop=at+length
        cells=indices(data[at:at+72],576); attrs=indices(data[at+72:at+144],576); at+=144
        mode_bits=2 if front_modes else 1
        modes=data[at:at+(mode_bits*len(cells)+7)//8]; at+=len(modes)
        target=screens[(frame-start)%2]
        for j,cell in enumerate(cells):
            mode=(modes[j//4]>>((j%4)*2))&3 if front_modes else (modes[j//8]>>(j%8))&1
            if mode>=2:
                source=cell
                if mode==3:
                    offset=data[at];at+=1;source+=offset if offset<128 else offset-256
                if not 0<=source<576:raise ValueError('front source outside active picture')
                sy,sx=divmod(source,32);front=screens[1-(frame-start)%2]
                raster=bytes(front[spectrum_bitmap_offset(sx,(sy+3)*8+line)] for line in range(8))
            elif mode==1:
                raster=book[data[at]]; at+=1
            else:
                raster=bytes(b for index in data[at:at+4] for b in (cache[index],cache[256+index])); at+=4
            y,x=divmod(cell,32)
            for line,value in enumerate(raster):
                target[spectrum_bitmap_offset(x,(y+3)*8+line)]=value
        for cell in attrs:
            target[6240+cell]=data[at]^(target[6240+cell] if data[:4]==b'CB45' else 0); at+=1
        assert at==stop and bytes(target)==screen(frames,frame),frame
        assert bytes(screens[1-(frame-start)%2])==screen(frames,frame-1),('other screen',frame)
        hashes.append(sha(target))
    assert at==len(data)
    return dict(complete=True,frames=end-start,row_updates=updates,cell_updates=book_updates,screen_sha256=hashes,
                both_screens_exact=True,pixel_changes=0)


def representation(frames,start,end,*,cell_window=None,book_front_reuse=False):
    result=encode(frames,start,end,cell_window=cell_window,book_front_reuse=book_front_reuse)
    proof=decode_check(result['raw'],frames,start,end,result['rows'])
    return dict(result,first=max(0,start-2),start=start,end=end,
        screen_sha256=proof['screen_sha256'],full_host_screens_exact=True,
        dynamic_proof=proof)
