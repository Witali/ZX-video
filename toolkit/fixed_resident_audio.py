"""One exact AYH1 forest in fixed RAM, coded payload in bank 4 and a bank-6 tail."""
import struct

import ay_huffman_stream as wire
import banked_resident_audio as banked
from build_fap3_trd import sha,padded,sectors
import resident_audio_z80 as resident
from pipelined_frame_z80 import PAGE,SHADOW

ORIGIN,ROOTS,TAIL,TAIL_END=0x8000,0x8200,0xb100,0xb700


def single_stream(data):
    if data[:4]==b'AYB1':
        initial,records=banked.decode(data);result,_=wire.encode(records,initial)
        assert wire.decode(result)==(initial,records)
        return result
    wire.decode(data)
    return data


def forest(trees,core_limit):
    """Place 4-byte nodes in two disjoint fixed ranges; pointers remain absolute."""
    spans=[(ROOTS+26,core_limit),(TAIL,TAIL_END)]
    nodes=[];index=0;cursor=spans[0][0]
    def node(value):
        nonlocal index,cursor
        if isinstance(value,int):return value
        if set(value)!={0,1}:raise ValueError('incomplete fixed Huffman tree')
        while cursor+4>spans[index][1]:
            index+=1
            if index>=len(spans):raise ValueError('shared AY trees exceed fixed allocation')
            cursor=spans[index][0]
        at=cursor;cursor+=4;entry=[at,b''];nodes.append(entry)
        left,right=node(value[0]),node(value[1]);entry[1]=struct.pack('<HH',left,right)
        return at
    roots=struct.pack('<13H',*(node(tree) for tree in trees))
    regions=[(ROOTS,roots)]
    for at,blob in nodes:
        if regions[-1][0]+len(regions[-1][1])==at:
            before,data=regions[-1];regions[-1]=(before,data+blob)
        else:regions.append((at,blob))
    return regions


def build(data,audio,*,core_limit,batch=31,first_bank_bytes=16384,single_bank=4):
    data=single_stream(data);initial,records,trees,payload=resident.tables(data)
    if not 1<=first_bank_bytes<=16384:raise ValueError('invalid first payload capacity')
    if len(payload)>first_bank_bytes+1536:raise ValueError('shared AY overflow exceeds reserved 1536-byte tail')
    regions=forest(trees,core_limit)
    first=min(first_bank_bytes,len(payload));overflow=payload[first:]
    if single_bank not in (4,6):raise ValueError('shared AY single bank must be 4 or 6')
    if overflow and single_bank!=4:raise ValueError('four video slots require one-bank AY')
    start=0x10000-first_bank_bytes
    segments=[dict(bank=single_bank,address=start,data_hex=payload[:first].hex(),bytes=first)]
    second=0x10000-len(overflow) if overflow else None
    if overflow:segments.append(dict(bank=6,address=second,data_hex=overflow.hex(),bytes=len(overflow)))
    code,labels,listing=resident.code(audio,len(records),initial,ROOTS,start,batch=batch,origin=ORIGIN,
        payload_overflow=second,page_entry=PAGE)
    if labels['end']>ROOTS:raise ValueError('fixed AY decoder overlaps roots')
    regions=[(ORIGIN,code),*regions]
    return dict(enabled=True,wire='AYH1',origin=ORIGIN,ticks=len(records),batch=batch,
        labels=labels,listing=listing,regions=[dict(address=at,data_hex=blob.hex()) for at,blob in regions],
        payload_segments=segments,banks=[s['bank'] for s in segments],
        payload_bank_address=labels.get('payload_bank'),payload_address=start,payload_bytes=len(payload),
        bank6_reserved_bytes=len(overflow),code_bytes=labels['code_end']-ORIGIN,
        fixed_bytes=sum(len(blob) for _,blob in regions),fixed_limit=core_limit,
        input_bits=struct.unpack_from('<I',data,8)[0],ayh1_sha256=sha(data),
        initial_registers=initial.hex(),records_sha256=sha(b''.join(records)),
        normal_refill_byte_delta_tstates=28 if overflow else 0,
        first_bank_switch_byte_delta_tstates=214 if overflow else 0,
        final_bank_wrap_byte_delta_tstates=55 if overflow else 0,
        init_delta_tstates=20 if overflow else 0,
        timing_scope='Against one AYH1 model; includes 92-T page body at wrap, excludes outer bridge/IRQ/ULA')


def install(banks,m,sections,data,compress,*,four_slots=False):
    """Replace resident segments after the cell player has retired old code."""
    old=m['resident_audio'];cell=m['cell_codebook']
    if cell['wire'] not in ('CB44','CB46') or not cell.get('obsolete_fixed_ranges'):
        raise ValueError('fixed AY integration requires the retired CB44 reconstruction')
    compiled=build(data,m['audio_labels'],core_limit=m['decoder_labels']['start'],batch=old['compiled']['batch'],
        single_bank=6 if four_slots else 4)
    def put(at,blob):
        if not 0x4000<=at<at+len(blob)<=0xc000:raise ValueError('fixed AY region must stay mapped')
        bank=5 if at<0x8000 else 2;lo=at&16383;banks[bank][lo:lo+len(blob)]=blob
    for region in compiled['regions']:
        at=region['address'];blob=bytes.fromhex(region['data_hex'])
        if any(banks[2][at-0x8000:at-0x8000+len(blob)]):raise ValueError('fixed AY allocation is not retired/zero')
        put(at,blob)
    replacements=[];new_rows=list(compiled['listing']);new_regions=[]
    for key,target,bank_address in (
            ('refill_bridge',compiled['labels']['fill'],compiled['payload_bank_address']),
            ('init_bridge',compiled['labels']['init'],None)):
        previous=old[key];origin=previous['origin'];before=bytes.fromhex(previous['code_hex'])
        actual=bytes(banks[5 if origin<0x8000 else 2][origin&16383:(origin&16383)+len(before)])
        if actual!=before:raise ValueError('unexpected old resident bridge bytes')
        current=resident.bridge(origin,target,page=PAGE,shadow=SHADOW,bank_address=bank_address,
            bank=compiled['payload_segments'][0]['bank'])
        blob=bytes.fromhex(current['code_hex'])
        if len(blob)>len(before):raise ValueError('fixed AY bridge exceeds old allocation')
        put(origin,blob+bytes(len(before)-len(blob)));replacements.append((origin,origin+len(before)))
        old[key]=current;new_rows+=current['listing'];new_regions.append(dict(address=origin,code_hex=blob.hex()))
    if 'segment_hooks' in old:
        hooks=old.pop('segment_hooks');origin=hooks['origin'];length=len(bytes.fromhex(hooks['code_hex']))
        put(origin,bytes(length));replacements.append((origin,origin+length))
    for bank in (4,6):banks[bank][:]=bytes(16384)
    payload_sections=[]
    for part in compiled['payload_segments']:
        at=part['address'];raw=bytes.fromhex(part['data_hex']);lo=at&16383
        banks[part['bank']][lo:lo+len(raw)]=raw
        offset=0
        while offset<len(raw):
            length=min(8192,len(raw)-offset)
            while True:
                piece=raw[offset:offset+length];coded=compress(piece)
                if len(padded(coded))<=6912:break
                length-=256
                if length<=0:raise ValueError('fixed audio payload cannot fit staging')
            payload_sections.append(dict(bank=part['bank'],address=at+offset,buffer=0x4000,
                decoded_bytes=length,compressed_bytes=len(coded),sectors=sectors(coded),sha256=sha(piece),data=padded(coded)))
            offset+=length
    # Guard only the gaps left after installing the new fixed decoder/forest.
    ranges=[(r['start'],r['end']) for r in cell['obsolete_fixed_ranges']]+[(TAIL,TAIL_END)]
    for region in compiled['regions']:
        start=region['address'];end=start+len(bytes.fromhex(region['data_hex']));remaining=[]
        for lo,hi in ranges:
            if hi<=start or lo>=end:remaining.append((lo,hi))
            else:
                if lo<start:remaining.append((lo,start))
                if end<hi:remaining.append((end,hi))
        ranges=remaining
    cell['obsolete_fixed_ranges']=[dict(start=lo,end=hi,reason='unused fixed AY allocation gap') for lo,hi in ranges]
    cell['memory']['audio']=compiled['banks']
    cell['memory']['fixed_audio']=[dict(start=r['address'],end=r['address']+len(bytes.fromhex(r['data_hex']))) for r in compiled['regions']]
    cell['memory']['bank6_audio_tail_bytes']=compiled['bank6_reserved_bytes']
    old['previous_bank_bytes']=[s['image_bytes'] for s in old['compiled'].get('segments',[old['compiled']])]
    old.update(compiled=compiled,format='video-only '+cell['wire']+' + fixed AYH1',banks=compiled['banks'],
        shared_fixed=True,startup_sections=len(payload_sections),audio_isr_changed=False,
        bank6_reserved_bytes=compiled['bank6_reserved_bytes'])
    old.pop('segment_boundary_ticks',None)
    kept=[]
    for region in old['code_regions']:
        at=region['address']
        if any(lo<=at<hi for lo,hi in replacements):continue
        bank=5 if at<0x8000 else 2 if at<0xc000 else 7;lo=at&16383
        length=len(bytes.fromhex(region['code_hex']))
        kept.append(dict(address=at,code_hex=bytes(banks[bank][lo:lo+length]).hex()))
    old['code_regions']=kept+new_regions
    m['slot_queue_instruction_listing']=[r for r in m['slot_queue_instruction_listing']
        if not any(lo<=r['address']<hi for lo,hi in replacements)]+new_rows
    if four_slots:
        from four_video_slots import install as install_slots
        install_slots(banks,m)
    retained=[s for s in sections if s['bank'] not in (4,6)]
    assert retained[-1]['bank']==5 and retained[-1]['address']==0x4000
    return retained[:-1]+payload_sections+retained[-1:]
