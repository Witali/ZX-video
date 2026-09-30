"""Exact 4x4 logical-cell dictionary feasibility on one retained video window.

Experimental inner format only: two-screen deltas, optional 256-entry bitmap
codebook and four row-index fallback. Brightness precedes fixed dithering.
No native cell renderer, disk image, IRQ schedule or playback claim.
"""
import argparse,json,struct
from collections import Counter
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from build_five_level_test_trd import save
from build_zxv_trd import spectrum_bitmap_offset
from frame_output_pipeline import display_screen
from row_dictionary_video import reference_tables
from lzsa2_oracle_host import Author
from inplace_zx0 import layout
import lzsa2_stream

ROOT=Path(__file__).resolve().parent
CELLS=576
PATTERNS=((0,0),(2,0),(2,1),(3,1),(3,3))


def mask(indices,size):
    bits=bytearray((size+7)//8)
    for i in indices:bits[i//8]|=1<<(i%8)
    return bytes(bits)


def indices(data,size):
    return [i for i in range(size) if data[i//8]&(1<<(i%8))]


def cell_rows(state):
    rows=np.frombuffer(bytes(state[:3072]),dtype=np.uint8).reshape(96,32)
    return [bytes(rows[y*4:y*4+4,x]) for y in range(3,21) for x in range(32)]


def bitmap(pattern,words):
    """Scalar brightness reconstruction followed by the agreed final dither."""
    result=bytearray()
    for symbol in pattern:
        w=words[symbol];levels=[w//125,(w//25)%5,(w//5)%5,w%5]
        for line in range(2):
            value=0
            for level in levels:value=(value<<2)|PATTERNS[level][line]
            result.append(value)
    return bytes(result)


def changes(states,start,count):
    rows=[]
    for i in range(start,start+count):
        current=cell_rows(states[i]);previous=cell_rows(states[i-2])
        changed=[j for j in range(CELLS) if current[j]!=previous[j]]
        attrs=bytes(states[i,3072:]);old_attrs=bytes(states[i-2,3072:])
        # Black fields are not part of the proposed frame update.
        assert attrs[:96]==old_attrs[:96] and attrs[672:]==old_attrs[672:]
        ca=[j for j in range(CELLS) if attrs[96+j]!=old_attrs[96+j]]
        rows.append(dict(frame=i,patterns=current,changed=changed,attrs=attrs[96:672],attr_changed=ca))
    return rows


def encode(rows,book,words):
    lookup={key:i for i,key in enumerate(book)}
    table=b''.join(bitmap(key,words) for key in book)
    result=bytearray(b'CB41'+struct.pack('<HH',len(rows),len(book))+table);details=[]
    for row in rows:
        changed=row['changed'];coded=[j for j,k in enumerate(changed) if row['patterns'][k] in lookup]
        payload=bytearray(mask(changed,CELLS)+mask(row['attr_changed'],CELLS))
        if book:payload+=mask(coded,len(changed))
        for i in changed:
            key=row['patterns'][i]
            payload+=bytes([lookup[key]]) if key in lookup else key
        payload+=bytes(row['attrs'][i] for i in row['attr_changed'])
        result+=struct.pack('<H',len(payload))+payload
        details.append(dict(frame=row['frame'],changed_cells=len(changed),book_cells=len(coded),
            literal_cells=len(changed)-len(coded),attribute_cells=len(row['attr_changed']),packet_bytes=len(payload)))
    return bytes(result),table,details


def decode_check(data,states,start,count,words,book_meta):
    assert data[:4]==b'CB41'
    frames,entries=struct.unpack_from('<HH',data,4);assert frames==count and entries in (0,256)
    at=8;table=[data[at+i*8:at+(i+1)*8] for i in range(entries)];at+=entries*8
    checked=[]
    with reference_tables(book_meta):
        screens=[bytearray(display_screen(states[start-2+p].tobytes(),black_borders=True)) for p in (0,1)]
        initial=bytes(screens[0]+screens[1])
        for i in range(count):
            n=struct.unpack_from('<H',data,at)[0];at+=2;end=at+n
            changed=indices(data[at:at+72],CELLS);at+=72
            attrs=indices(data[at:at+72],CELLS);at+=72
            modes=data[at:at+(len(changed)+7)//8] if entries else b''
            if entries:at+=len(modes)
            screen=screens[i%2]
            for j,cell in enumerate(changed):
                if entries and modes[j//8]&(1<<(j%8)):
                    value=table[data[at]];at+=1
                else:
                    value=bitmap(data[at:at+4],words);at+=4
                y,x=divmod(cell,32);y+=3
                for line,v in enumerate(value):screen[spectrum_bitmap_offset(x,y*8+line)]=v
            for cell in attrs:screen[6144+96+cell]=data[at];at+=1
            assert at==end,'packet extent differs'
            expected=display_screen(states[start+i].tobytes(),black_borders=True)
            assert bytes(screen)==expected,('native screen differs',i)
            # The undisplayed bank remains the exact previous publication.
            other=start+i-1
            assert bytes(screens[1-i%2])==display_screen(states[other].tobytes(),black_borders=True)
            checked.append(sha(screen))
    assert at==len(data)
    return initial,checked


def compress(raw,author):
    stream=bytearray();blocks=[]
    for lo in range(0,len(raw),15872):
        data=raw[lo:lo+15872];payload=author.compress(data)
        assert author.decompress(payload,len(data))==data
        restored,proof=lzsa2_stream.trace(payload,limit=len(data));assert restored==data
        space=layout(len(payload),len(data),proof['minimum_input_start'],len(stream))
        assert space['sector_aligned_fits'],'unsafe block overlap'
        lzsa2_stream.trace(payload,limit=len(data),input_start=space['input_start'])
        blocks.append(dict(raw_start=lo,raw_end=lo+len(data),decoded_bytes=len(data),
            compressed_bytes=len(payload),proof=proof,layout=space))
        stream+=struct.pack('<HH',len(data),len(payload))+payload
    return bytes(stream),blocks


def packet_window(video,start,count):
    at=0;parts=[]
    for i in range(start+count):
        n=struct.unpack_from('<H',video,at)[0]
        if i>=start:parts.append(video[at:at+n+2])
        at+=n+2
    return b''.join(parts)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('states','metadata','video','author','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--start',type=int,default=128);p.add_argument('--count',type=int,default=64)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    with np.load(a.states,allow_pickle=False) as f:states=f['states']
    assert 2<=a.start and 32<=a.count<=64 and a.start+a.count<=len(states)
    m=json.loads(a.metadata.read_bytes());meta=m['row_dictionary'];words=meta['words']
    assert sha(states.tobytes())==m['states_sha256']
    source=a.video.read_bytes();retained=json.loads((ROOT/'borrowed_literals_profile.json').read_bytes())
    assert sha(source)==retained['video_sha256']
    # Independently generated final bitmaps must agree with the existing row tables.
    tables=bytes.fromhex(meta['tables_hex'])
    for i in range(len(words)):
        assert bitmap(bytes([i])*4,words)==bytes([tables[i],tables[256+i]])*4
    rows=changes(states,a.start,a.count)
    counts=Counter(row['patterns'][i] for row in rows for i in row['changed'])
    book=sorted(counts,key=lambda key:(-counts[key],key))[:256]
    # This experiment intentionally tests a fixed 256-entry table.
    assert len(book)==256
    raw,table,details=encode(rows,book,words);control,_,_=encode(rows,[],words)
    initial,checks=decode_check(raw,states,a.start,a.count,words,meta)
    initial2,checks2=decode_check(control,states,a.start,a.count,words,meta)
    assert initial==initial2 and checks==checks2
    variants={'current':packet_window(source,a.start,a.count),'direct_rows':control,'codebook':raw}
    author=Author(a.author);results={}
    for name,data in variants.items():
        packed,blocks=compress(data,author)
        (a.output/(name+'.raw')).write_bytes(data);(a.output/(name+'.stream')).write_bytes(packed)
        results[name]=dict(raw_bytes=len(data),compressed_bytes=len(packed),sectors=(len(packed)+255)//256,
            raw_sha256=sha(data),stream_sha256=sha(packed),blocks=blocks)
    (a.output/'initial-screens.bin').write_bytes(initial)
    report=dict(complete=True,release=False,scope=__doc__,baseline_commit='63947dd',start=a.start,count=a.count,
        states_sha256=sha(states.tobytes()),source_video_sha256=sha(source),initial_screens_sha256=sha(initial),
        dictionary_entries=len(book),dictionary_bitmap_bytes=len(table),dictionary_row_keys=[list(k) for k in book],
        dictionary_selection='Most frequent exact changed-cell patterns in this same bounded window; not a generalization or full-volume claim.',
        changed_cells=sum(r['changed_cells'] for r in details),book_cells=sum(r['book_cells'] for r in details),
        unique_changed_patterns=len(counts),variants=results,frames=details,screen_sha256=checks,
        full_native_screens_host_exact=True,brightness_before_dither=True,lossy_pixel_changes=0,
        audio_change=False,native_render_cycles_measured=False,actual_playback_measured=False,
        comparison_scope='Fresh LZSA2 resets for all three payload windows. New header and complete 2048-byte table are included in codebook bytes. Existing 512-byte row table, AY, player code and supplied prior screen/predictor history are common/excluded. This is not a cold-boot disk capacity estimate.',
        author_dll_sha256=sha(a.author.read_bytes()),
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in (
            'probe_cell_codebook.py','row_dictionary_video.py','five_level_dither.py','lzsa2_oracle_host.py','lzsa2_stream.py','inplace_zx0.py')})
    save(a.output/'probe.json',report)
    print(json.dumps(dict(changed_cells=report['changed_cells'],book_cells=report['book_cells'],
        unique_changed_patterns=len(counts),variants={k:{q:v[q] for q in ('raw_bytes','compressed_bytes','sectors')} for k,v in results.items()})))


if __name__=='__main__':main()
