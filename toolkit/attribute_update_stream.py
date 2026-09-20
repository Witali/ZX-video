"""FAC1/FAC2: bitmap-only FAP3 plus explicit final attribute changes.

The old attribute Huffman tail or 768-byte literal tail is removed. Bitmap
vectors, corrections, fragments, native masks and all AY bytes are retained.
Attribute payload after bitmap literals: u16 byte length, u8 group count,
then (group index 0..71, MSB-first mask, selected final byte values).
Indices cover active attributes 96..671. Initial native attributes are 1.
FAC1 predicts from n-2 and can replace compact attribute RAM with commands.
FAC2 predicts from n-1; the first two records are full. A proposed consumer
maintains final attributes and both preceding group-index lists for n-2.
Each command payload is at most 723 bytes including length.
This PC codec alone does not verify player speed, IRQ or disk delivery.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np
from bulk_frame_stream import read_packet,WINDOW
from probe_lossless_layouts import sha,measure
from probe_motion_entropy import Reader,codes_for
from probe_motion_metadata import restore,transform
from probe_spatial_contexts import read_header
from probe_fast_fragments import SIZES


def encode_attributes(previous,current,*,force_full=False):
    if len(previous)!=768 or len(current)!=768:
        raise ValueError('768 attributes required')
    if current[:96]!=b'\1'*96 or current[672:]!=b'\1'*96:
        raise ValueError('constant borders required')
    out=bytearray([0])
    for group in range(72):
        start=96+group*8
        selected=[i for i in range(8) if force_full or previous[start+i]!=current[start+i]]
        if selected:
            out[0]+=1; out+=bytes([group,sum(128>>i for i in selected)])
            out+=bytes(current[start+i] for i in selected)
    return struct.pack('<H',len(out))+out


def apply_attributes(previous,record):
    p=Reader(record); n=p.u16(); data=p.take(n); p.end(); p=Reader(data)
    count=p.take(1)[0]
    if count>72: raise ValueError('too many attribute groups')
    out=bytearray(previous); last=-1
    for _ in range(count):
        group,mask=p.take(2)
        if not last<group<72 or not mask: raise ValueError('unordered or empty attribute group')
        last=group
        for bit in range(8):
            if mask & (128>>bit): out[96+group*8+bit]=p.take(1)[0]
    p.end()
    return bytes(out)


def strip_attributes(detail,previous,current,table):
    """Verify and remove only the old attribute tail, returning bitmap fields."""
    flags=detail['flags']; body=detail['payload']; ay=b''.join(detail['ticks'])
    start=len(ay)+5; ml=detail['mask_bytes']
    cache=body[start:start+3]; vectors=body[start+3:start+195]
    metadata=body[start+195:start+195+ml]
    masks=restore(metadata,1,480,4)
    native=body[detail['coded_offset']-80:detail['coded_offset']]
    coded=body[detail['coded_offset']:detail['literal_offset']]
    literal=body[detail['literal_offset']:]
    bits=8*len(coded)-((8-(flags&7))&7)
    if flags&64:
        if any(masks[384:]) or literal[-768:]!=current:
            raise AssertionError('old raw attribute tail differs')
        literal=literal[:-768]
    else:
        delta=bytes(a^b for a,b in zip(previous,current))
        if np.packbits(np.frombuffer(delta,dtype=np.uint8)!=0).tobytes()!=masks[384:]:
            raise AssertionError('old attribute mask differs')
        codes=codes_for(255,table); tail=tail_bits=0
        for value in delta:
            if value:
                code,size=codes[value]
                if not size: raise AssertionError('missing attribute code')
                tail=(tail<<size)|code; tail_bits+=size
        value=int.from_bytes(coded,'big') >> ((-bits)&7)
        if tail_bits>bits or value & ((1<<tail_bits)-1)!=tail:
            raise AssertionError('old attribute Huffman tail differs')
        bits-=tail_bits; value>>=tail_bits
        coded=(value<<((-bits)&7)).to_bytes((bits+7)//8,'big')
    if len(literal)!=sum(SIZES.get(v,0) for v in vectors):
        raise AssertionError('bitmap fragment length differs')
    metadata=transform(masks[:384]+bytes(96),480,4)
    return dict(ay=ay,flags=(flags&128)|(bits&7),cache=cache,vectors=vectors,
        metadata=metadata,native=native,coded=coded,literal=literal,bitmap_bits=bits)


def packet(fields,attributes):
    f=fields
    payload=f['ay']+struct.pack('<BHH',f['flags'],len(f['metadata']),len(f['coded']))
    payload+=f['cache']+f['vectors']+f['metadata']+f['native']+f['coded']+f['literal']+attributes
    if len(payload)>=WINDOW: raise ValueError('FAC1 packet exceeds input window')
    return struct.pack('<H',len(payload))+payload


def convert(raw,states,*,prediction='screen'):
    r=Reader(raw); _,_,count,_,tables=read_header(r,magic=b'FAP3')
    if states.shape!=(count,3840): raise ValueError('different states')
    if prediction not in ('screen','previous'): raise ValueError('unknown attribute prediction')
    out=bytearray((b'FAC1' if prediction=='screen' else b'FAC2')+raw[4:r.pos]); previous=bytes(768)
    screens=[b'\1'*768,b'\1'*768]; attribute_history=b'\1'*768; index_lists=[[],[]]; rows=[]
    for i,state in enumerate(states):
        _,detail=read_packet(r,stored_guards=False); attrs=state[3072:].tobytes()
        fields=strip_attributes(detail,previous,attrs,tables[-1])
        base=screens[i%2] if prediction=='screen' else attribute_history
        commands=encode_attributes(base,attrs,force_full=prediction=='previous' and i<2)
        restored=apply_attributes(base,commands)
        if restored!=attrs: raise AssertionError(('attributes differ',i))
        if prediction=='previous':
            # The CPU will keep only the current 576 final values plus two
            # lists of modified eight-byte groups, each at most 73 bytes.
            q=Reader(commands[3:]); indices=[]
            for _ in range(commands[2]):
                group,mask=q.take(2); indices.append(group); q.take(mask.bit_count())
            q.end(); index_lists[i%2]=indices
            target=bytearray(screens[i%2])
            for group in index_lists[0]+index_lists[1]:
                start=96+8*group; target[start:start+8]=restored[start:start+8]
            if bytes(target)!=attrs: raise AssertionError(('union of n-1 group lists differs',i))
            attribute_history=restored
        encoded=packet(fields,commands)
        # Parse through the unchanged bulk reader and compare every retained
        # field, including all six AY records and Huffman bitmap padding.
        q=Reader(encoded); _,d=read_packet(q,stored_guards=False); q.end()
        if d['ticks']!=detail['ticks'] or d['cache']!=detail['cache']:
            raise AssertionError('AY/cache changed')
        if d['payload'][d['coded_offset']:d['literal_offset']]!=fields['coded']:
            raise AssertionError('bitmap code changed')
        if d['payload'][d['literal_offset']:]!=fields['literal']+commands:
            raise AssertionError('bitmap fragments/attribute record changed')
        changed=sum(a!=b for a,b in zip(screens[i%2],attrs))
        rows.append(dict(index=i,old_payload_bytes=len(detail['payload']),payload_bytes=len(encoded)-2,
            old_coded_bytes=detail['coded_bytes'],coded_bytes=len(fields['coded']),bitmap_bits=fields['bitmap_bits'],
            old_raw_attributes=bool(detail['flags']&64),attribute_bytes=len(commands),
            changed_attributes=changed,attribute_groups=commands[2]))
        out+=encoded; previous=attrs; screens[i%2]=attrs
        if i%500==0: print(f'Attribute packets verified {i+1}/{count}',flush=True)
    r.end(); return bytes(out),rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','output','report'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--prediction',choices=('screen','previous'),default='screen')
    args=p.parse_args(); raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    data,rows=convert(raw,states,prediction=args.prediction); args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_bytes(data)
    result=dict(scope=__doc__,complete=True,release=False,cpu_measured=False,frames=len(rows),
        source_raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),output_sha256=sha(data),prediction=args.prediction,
        raw_bytes=len(data),delta_raw_bytes=len(data)-len(raw),deflate_8192_bytes=measure(data,8192),
        max_payload_bytes=max(v['payload_bytes'] for v in rows),max_attribute_bytes=max(v['attribute_bytes'] for v in rows),
        total_attribute_bytes=sum(v['attribute_bytes'] for v in rows),total_changed_native_n2_attributes=sum(v['changed_attributes'] for v in rows),
        old_raw_attribute_frames=sum(v['old_raw_attributes'] for v in rows),
        exact_ay_bytes=True,exact_bitmap_fields=True,exact_both_native_attribute_replay=True,
        disk_delivery_verified=False,frame_rate_verified=False)
    prefix=json.dumps(result,indent=2)
    args.report.write_text(prefix[:-2]+',\n  "frames": [\n'+',\n'.join('    '+json.dumps(v) for v in rows)+'\n  ]\n}\n',encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__': main()
