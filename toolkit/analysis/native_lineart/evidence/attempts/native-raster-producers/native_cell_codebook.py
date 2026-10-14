"""CB47: exact native8x8 bitmap cells, front reuse and single-row changes.

Header: CB47,u16 frame count,u16 book size256,256*8 row-order bytes.
Each u16-sized payload has72-byte bitmap/attribute masks, two-bit cell modes,
cell data then changed attributes. Modes:0 eight literal bytes;1 book index;
2 same-position front copy;3 row0..7 plus one literal byte. No row table,
radix-five pattern or runtime row-update controls are used.

Length bit15 selects a dense packet:144 raster rows of32 native bytes,
then576 active attributes (5184 bytes). Dense moving drawings compress
better in raster order and can be written with bounded32-byte LDIRs.
"""
from collections import Counter
import struct
import numpy as np
from build_fap3_trd import sha
from build_zxv_trd import spectrum_bitmap_offset
from probe_cell_codebook import mask, indices
from native_lineart import OFFSETS, unpack

MAX_PACKET = 5472
RASTER_BYTES = 5184
RASTER_THRESHOLD = 577


def validate(frames):
    if frames.ndim != 2 or frames.shape[1] != 6912 or not len(frames) or frames.dtype != np.uint8:
        raise ValueError('expected nonempty uint8 Nx6912 native screens')
    for i, frame in enumerate(frames):
        bits, attrs = unpack(frame)
        if bits[:24].any() or bits[168:].any() or (attrs & 128).any() or np.any(attrs[:96] != 1) or np.any(attrs[672:] != 1):
            raise ValueError(f'native frame {i}: invalid bands or FLASH attribute')


def patterns(frame):
    linear = np.asarray(frame, np.uint8)[:6144][OFFSETS][24:168]
    return np.ascontiguousarray(linear.reshape(18, 8, 32).transpose(0, 2, 1).reshape(576, 8))


def history(frames, index):
    if index >= 0:return frames[index].tobytes()
    if index not in (-2, -1):raise ValueError('invalid native history')
    return bytes(6144)+frames[0,6144:].tobytes()


def representation(frames, start, end):
    validate(frames)
    if not 0 <= start < end <= len(frames) or end-start > 10922:raise ValueError('invalid native extent')
    current = np.stack([patterns(frame) for frame in frames[start:end]])
    back = np.concatenate([np.stack([patterns(frames[i]) if i >= 0 else np.zeros((576,8),np.uint8)
        for i in (start-2,start-1)]), current[:-2]])[:end-start]
    front = np.concatenate([np.stack([patterns(frames[start-1]) if start else np.zeros((576,8),np.uint8)]),current[:-1]])
    changed = np.any(current != back, -1);novel = changed & np.any(current != front, -1)
    counts = Counter(current[f,c].tobytes() for f,c in zip(*np.nonzero(novel)))
    book = sorted(counts, key=lambda key:(-counts[key],key))[:256]
    book += [bytes(8)]*(256-len(book));lookup = {key:i for i,key in enumerate(book)}
    output = bytearray(b'CB47'+struct.pack('<HH',end-start,256)+b''.join(book));details = []
    for local, frame in enumerate(range(start,end)):
        selected = np.flatnonzero(changed[local]).tolist()
        old_attrs = frames[frame-2,-672:-96] if frame >= 2 else frames[0,-672:-96]
        changed_attrs = np.flatnonzero(frames[frame,-672:-96] != old_attrs).tolist()
        modes = bytearray((len(selected)+3)//4);payload = bytearray();counts_mode = [0]*4
        for j, cell in enumerate(selected):
            key = current[local,cell].tobytes()
            if np.array_equal(current[local,cell],front[local,cell]):mode=2;value=b''
            elif key in lookup:mode=1;value=bytes([lookup[key]])
            else:
                rows = np.flatnonzero(current[local,cell] != back[local,cell])
                if len(rows) == 1:mode=3;value=bytes([int(rows[0]),int(current[local,cell,rows[0]])])
                else:mode=0;value=key
            modes[j//4] |= mode << ((j%4)*2);payload += value;counts_mode[mode] += 1
        body = mask(selected,576)+mask(changed_attrs,576)+modes+payload+frames[frame,-672:-96][changed_attrs].tobytes()
        assert 144 <= len(body) <= MAX_PACKET
        raster=sum(counts_mode[i] for i in (0,1,3))>=RASTER_THRESHOLD
        if raster:
            body=frames[frame,:6144][OFFSETS][24:168].tobytes()+frames[frame,6240:6816].tobytes()
        output += struct.pack('<H',len(body)|(0x8000 if raster else 0))+body
        actual_modes=[0]*4 if raster else counts_mode
        details.append(dict(frame=frame,changed_cells=len(selected),attribute_cells=len(changed_attrs),
            literal_cells=actual_modes[0],book_cells=actual_modes[1],front_cells=actual_modes[2],
            single_row_cells=actual_modes[3],packet_bytes=len(body),raster_packet=raster,
            candidate_literal_cells=counts_mode[0],native_bitmap_bytes_written=4608 if raster else len(selected)*8,
            native_attributes_written=576 if raster else len(changed_attrs)))
    raw = bytes(output);proof = decode_check(raw,frames,start,end)
    tables = bytes(512)
    return dict(raw=raw,raw_sha256=sha(raw),details=details,dynamic_proof=proof,
        rows=dict(words=[0]*256,entries=256,tables_hex=tables.hex(),sha256=sha(tables),ram_bytes=512,
            table_address=0x9e00,lifetime='Unused reserved CB46 row-table space; CB47 literals contain actual native bytes'),
        row_updates=0,unique_literal_rows=0,unique_changed_patterns=len(counts),native_pixels=True)


def decode_check(raw, frames, start, end):
    if raw[:4] != b'CB47' or struct.unpack_from('<HH',raw,4) != (end-start,256):raise ValueError('invalid CB47 header')
    book = [raw[8+i*8:16+i*8] for i in range(256)]
    screens = [bytearray(history(frames,start-2)),bytearray(history(frames,start-1))]
    at = 2056;hashes = []
    for frame in range(start,end):
        if at+2 > len(raw):raise ValueError('truncated native length')
        encoded_length, = struct.unpack_from('<H',raw,at);at += 2
        raster=bool(encoded_length&0x8000);length=encoded_length&0x7fff;stop=at+length
        if not 144 <= length <= MAX_PACKET or stop > len(raw):raise ValueError('invalid native packet length')
        if raster:
            if length!=RASTER_BYTES:raise ValueError('invalid raster packet length')
            target=screens[(frame-start)%2]
            target_array=np.frombuffer(target,np.uint8)
            target_array[OFFSETS[24:168]]=np.frombuffer(raw[at:at+4608],np.uint8).reshape(144,32)
            target[6240:6816]=raw[at+4608:stop];at=stop
            if bytes(target)!=frames[frame].tobytes():raise AssertionError(f'native raster frame {frame} differs')
            hashes.append(sha(target));continue
        bitmap_cells = indices(raw[at:at+72],576);attrs = indices(raw[at+72:at+144],576);at += 144
        size = (len(bitmap_cells)+3)//4;modes = raw[at:at+size];at += size
        target = screens[(frame-start)%2];front = screens[1-(frame-start)%2]
        for j,cell in enumerate(bitmap_cells):
            mode = (modes[j//4] >> ((j%4)*2)) & 3;y,x = divmod(cell,32);y = (y+3)*8
            if mode == 3:
                if at+2 > stop:raise ValueError('truncated native row')
                row,value = raw[at:at+2];at += 2
                if row >= 8:raise ValueError('invalid native row')
                target[spectrum_bitmap_offset(x,y+row)] = value;continue
            if mode == 0:
                values = raw[at:at+8];at += 8
                if len(values) != 8:raise ValueError('truncated literal cell')
            elif mode == 1:
                if at >= stop:raise ValueError('truncated book symbol')
                values = book[raw[at]];at += 1
            else:values = bytes(front[spectrum_bitmap_offset(x,y+row)] for row in range(8))
            for row,value in enumerate(values):target[spectrum_bitmap_offset(x,y+row)] = value
        for cell in attrs:
            if at >= stop:raise ValueError('truncated native attribute')
            target[6144+96+cell] = raw[at];at += 1
        if at != stop:raise ValueError('native payload extent differs')
        if bytes(target) != frames[frame].tobytes():raise AssertionError(f'native frame {frame} differs')
        hashes.append(sha(target))
    if at != len(raw):raise ValueError('extra native bytes')
    return dict(complete=True,frames=end-start,full_native_screens_exact=True,
        compared_bytes=(end-start)*6912,screen_sha256=sha(''.join(hashes).encode()))
