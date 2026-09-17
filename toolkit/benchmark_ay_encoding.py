"""Compare lossless AY formats inside the actual 8192-byte video ZX0 blocks.

Sizes are for an unsplit 1000-screen stream. Player code size can change
when a format is implemented, so fit predictions are not release approval.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zlib

import ay_events
import ay_interrupt
import blocked_stream
import build_fast_sparse_trd as codec
import build_long_video_trd as video
import disk_layout
import packed_stream


def mask_ticks(frames):
    previous=None;records=[]
    for frame in frames:
        current=ay_interrupt.registers(frame)
        mask=sum(1<<i for i in range(11) if previous is None or current[i]!=previous[i])
        records.append(mask.to_bytes(2,'little')+bytes(v for i,v in enumerate(current) if mask&(1<<i)))
        previous=current
    return records


def tagged_ticks(frames):
    records=[]
    for pairs in ay_interrupt.encode_ticks(frames):
        result=bytearray([pairs[0]])
        for r,v in zip(pairs[1::2],pairs[2::2]):
            if r in (0,2,4):result+=bytes([r<<4,v])
            elif r==6:result.append(0x60+v)
            elif r==7:result.append(0xB0+(v==0x2A))
            else:result.append((r<<4)|v)
        records.append(bytes(result))
    return records


def clustered_blocks(packets,ticks):
    """Audio first inside each block, followed by length-prefixed video frames."""
    groups=[];audio=bytearray();screens=bytearray();count=0
    for i,packet in enumerate(packets):
        sound=b''.join(ticks[i*6:i*6+6])
        # Reuse the checked screen-command serialiser; discard its dummy audio.
        commands=packed_stream.frame_bytes(packet,natural_order=True,audio_payload=bytes(6))[8:]
        screen=struct.pack('<H',len(commands))+commands
        if 2+len(audio)+len(screens)+len(sound)+len(screen)>8192:
            if not screens:raise ValueError('clustered frame exceeds block')
            groups.append((bytes(struct.pack('<H',len(audio))+audio+screens),count))
            audio=bytearray();screens=bytearray();count=0
        audio+=sound;screens+=screen;count+=1
    if screens:groups.append((bytes(struct.pack('<H',len(audio))+audio+screens),count))
    return groups


def proxy_partition(packets,ticks,clustered,strategy):
    """Shortest path over frame boundaries; DEFLATE estimates the ZX0 cost."""
    audio=[b''.join(ticks[i*6:i*6+6]) for i in range(len(packets))]
    screens=[packed_stream.frame_bytes(packet,natural_order=True,audio_payload=bytes(6))[8:] for packet in packets]
    video=[struct.pack('<H',len(screen))+screen for screen in screens]
    inline=[struct.pack('<H',len(sound)+len(screen))+sound+screen for sound,screen in zip(audio,screens)]
    def payload(first,last):
        if not clustered:return b''.join(inline[first:last])
        sound=b''.join(audio[first:last])
        return struct.pack('<H',len(sound))+sound+b''.join(video[first:last])
    size=[0]
    for sound,screen in zip(audio,video):size.append(size[-1]+len(sound)+len(screen))
    best=[0]+[float('inf')]*len(packets);previous=[None]*len(best)
    for last in range(1,len(best)):
        for first in range(last-1,-1,-1):
            if size[last]-size[first]+(2 if clustered else 0)>8192:break
            data=payload(first,last)
            compressor=zlib.compressobj(9,zlib.DEFLATED,-15,strategy=zlib.Z_FIXED if strategy=='fixed' else zlib.Z_DEFAULT_STRATEGY)
            cost=4+len(compressor.compress(data)+compressor.flush())
            if best[first]+cost<best[last]:best[last]=best[first]+cost;previous[last]=first
    groups=[];last=len(packets)
    while last:
        first=previous[last]
        if first is None:raise ValueError('no valid partition')
        groups.append((payload(first,last),last-first));last=first
    return list(reversed(groups))


def verify_clustered(blocks,packets,ticks):
    first=0
    for block in blocks:
        last=first+block.frames;data=block.decoded
        audio_length=int.from_bytes(data[:2],'little');position=audio_length+2
        assert data[2:position]==b''.join(ticks[first*6:last*6])
        for packet in packets[first:last]:
            length=int.from_bytes(data[position:position+2],'little');position+=2
            expected=packed_stream.frame_bytes(packet,natural_order=True,audio_payload=bytes(6))[8:]
            assert data[position:position+length]==expected
            position+=length
        assert position==len(data)
        first=last
    assert first==len(packets)


def xor_packets(states,ay_states):
    """Offline-only predictor: changed values are XOR against their screen bank."""
    zero=bytes(len(states[0]));previous=[zero,zero];result=[]
    for index,(state,sound) in enumerate(zip(states,ay_states)):
        prior=previous[index&1]
        difference=bytes(a^b for a,b in zip(state,prior))
        records=codec.frame_records(difference,zero,allow_dense_rle=True)
        packet=codec.pack_packet(records,sound)
        decoded=codec.apply_packet_reference(packet,zero)
        assert bytes(a^b for a,b in zip(decoded,prior))==state
        result.append(packet)
        if not index:previous=[state,state]
        else:previous[index&1]=state
    return result


def xor_sparse_record(record,state):
    """Involutive sparse-value transform; absolute RLE/predictors stay unchanged."""
    result=bytearray(record);command=record[0]
    if command==1:
        mask=int.from_bytes(record[2:6],'big');pos=6;base=record[1]*32
        for column in range(32):
            if mask&(1<<(31-column)):result[pos]^=state[base+column];pos+=1
    elif command==3:
        base=record[1]*32
        for pos in range(3,len(record),2):result[pos+1]^=state[base+record[pos]]
    elif command==7:
        base=record[1]*32;column=0;pos=3
        for _ in range(record[2]):
            token=record[pos];pos+=1;column+=token>>4
            length=(token&15)+1
            for j in range(length):result[pos+j]^=state[base+column+j]
            pos+=length;column+=length
    elif command==4:
        pos=2;index=-1
        for _ in range(record[1]):
            gap=record[pos];pos+=1
            if gap==255:gap=int.from_bytes(record[pos:pos+2],'little');pos+=2
            index+=gap+1;result[pos]^=state[video.STATE_LEVEL_BYTES+index];pos+=1
    return bytes(result)


def sparse_xor_packets(states,packets):
    zero=bytes(len(states[0]));previous=[zero,zero];result=[]
    for i,(state,packet) in enumerate(zip(states,packets)):
        records=[r for j,sector in enumerate(packet.sectors) for r in packed_stream.sector_records(sector,j==0)]
        records.sort(key=lambda r:256 if r[0] in (2,4) else r[1])
        current=previous[i&1];visible=states[i-1] if i else None;groups=[];last_key=None
        for record in records:
            encoded=xor_sparse_record(record,current)
            assert xor_sparse_record(encoded,current)==record
            current=codec.apply_packet_reference(codec.pack_packet([record],packet.ay_state),current,visible)
            key=record[1] if record[0] not in (2,4) else None
            if key is not None and key==last_key:groups[-1]+=encoded
            else:groups.append(encoded)
            last_key=key
        assert current==state
        transformed=codec.pack_packet(groups,packet.ay_state)
        # Verify again after sector packing and the runtime's natural row order.
        restored=previous[i&1]
        encoded_records=[r for j,sector in enumerate(transformed.sectors) for r in packed_stream.sector_records(sector,j==0)]
        encoded_records.sort(key=lambda r:256 if r[0] in (2,4) else r[1])
        for record in encoded_records:
            original=xor_sparse_record(record,restored)
            restored=codec.apply_packet_reference(codec.pack_packet([original],packet.ay_state),restored,visible)
        assert restored==state
        result.append(transformed)
        if not i:previous=[state,state]
        else:previous[i&1]=state
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-build',type=Path,required=True)
    p.add_argument('--ay-50hz',type=Path,required=True)
    p.add_argument('--player-build',type=Path,required=True)
    p.add_argument('--zx0',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--formats',nargs='+',default=['pairs','mask','tagged','events'])
    p.add_argument('--dense-video',action='store_true',help='try RLE for every screen and select by packed bytes')
    p.add_argument('--partition',choices=['greedy','deflate','fixed'],default='greedy')
    p.add_argument('--xor-video',action='store_true',help='prototype only: XOR values against the previous contents of each screen bank')
    p.add_argument('--xor-sparse-video',action='store_true',help='prototype only: XOR sparse values and keep RLE/motion/visible predictors')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    states,old_ay,fps=codec.decode_compact_build(args.source_build/'VIDEO_full.C.bin')
    raw=args.ay_50hz.read_bytes()
    if len(raw)!=len(states)*6*9:raise ValueError('six audio ticks per screen required')
    frames=[video.AyFrame.deserialize(raw[i:i+9]) for i in range(0,len(raw),9)]
    if args.xor_video:packets=xor_packets(states,old_ay)
    else:_,packets=codec.make_volume_packets(states,old_ay,0,0x100000,packed=True,dense_packed=args.dense_video)
    if args.xor_sparse_video:
        if args.xor_video:p.error('choose one XOR experiment')
        packets=sparse_xor_packets(states,packets)
    metadata=json.loads((args.player_build/'build_metadata.json').read_text())
    first=metadata['video_sector'];player_sectors=(metadata['player_bytes']+255)//256
    capacity=codec.TRD_DATA_SECTORS-1-player_sectors
    encoders=dict(pairs=ay_interrupt.encode_ticks,mask=mask_ticks,tagged=tagged_ticks,events=ay_events.encode_ticks)
    report=dict(source_sha256=hashlib.sha256(raw).hexdigest(),frames=len(states),ticks=len(frames),
                player_bytes_assumed=metadata['player_bytes'],capacity_sectors=capacity,dense_video=args.dense_video,partition=args.partition,xor_video=args.xor_video,xor_sparse_video=args.xor_sparse_video,
                noise_histogram=dict(Counter(f.noise_period for f in frames)),formats=[])
    for name in args.formats:
        clustered=name.endswith('_cluster');kind=name.removesuffix('_cluster')
        ticks=encoders[kind](frames);audio=b''.join(ticks)
        if kind=='events':assert ay_events.decode_ticks(audio,len(frames))==frames
        (args.output/f'{name}.bin').write_bytes(audio)
        if args.partition!='greedy':
            groups=proxy_partition(packets,ticks,clustered,args.partition)
            blocks=blocked_stream.compress_groups(groups,args.zx0,args.output/'cache')
        elif clustered:
            groups=clustered_blocks(packets,ticks)
            blocks=blocked_stream.compress_groups(groups,args.zx0,args.output/'cache')
        else:
            encoded=[packed_stream.frame_bytes(packet,natural_order=True,audio_payload=b''.join(ticks[i*6:i*6+6]))
                     for i,packet in enumerate(packets)]
            blocks=blocked_stream.compress_frames(encoded,args.zx0,args.output/'cache')
        assert sum(block.frames for block in blocks)==len(packets)
        if clustered:verify_clustered(blocks,packets,ticks)
        total=256+sum(len(block.serialize()) for block in blocks)
        physical=disk_layout.required_sectors((total+255)//256,first)
        row=dict(format=name,audio_bytes=len(audio),decoded_bytes=sum(len(block.decoded) for block in blocks),blocks=len(blocks),
                 video_bytes_before_sector_padding=total,physical_video_sectors=physical,
                 excess_sectors=physical-capacity,block_frames=[block.frames for block in blocks])
        report['formats'].append(row)
        (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(row),flush=True)


if __name__=='__main__':main()
