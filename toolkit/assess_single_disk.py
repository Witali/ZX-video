"""Measure full-movie storage, without changing the released disks/player.

Lossless comparisons use verified decoded blocks from existing TRDs. Optional
low-resolution probes use the saved logical screens: they measure storage of
new, lossy video representations, not playable Z80 implementations or quality
equivalence. Every tested compression is round-trip checked.
"""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import struct
import subprocess
import zlib

import numpy as np
import cv2

import ay_events
import ay_interrupt
import build_long_video_trd as video
import disk_layout
import zx0_codec
from validate_streaming_player import extract_file, parse_dir


def sha(data):return hashlib.sha256(data).hexdigest()


def deflate(data):
    compressor=zlib.compressobj(9,zlib.DEFLATED,-15)
    result=compressor.compress(data)+compressor.flush()
    assert zlib.decompress(result,-15)==data
    return result


def sizes(data):
    xz=lzma.compress(data,preset=9)
    assert lzma.decompress(xz)==data
    return dict(raw=len(data),deflate=len(deflate(data)),xz_lzma2=len(xz))


def read_build(build):
    meta=json.loads((build/'build_metadata.json').read_text())
    blocks=[];sound=bytearray();pictures=bytearray();hashes=[];next_frame=0
    for volume in meta['volumes']:
        assert volume['frame_start']==next_frame
        image=(build/volume['trd_name']).read_bytes();hashes.append(sha(image))
        physical=b''.join(extract_file(image,entry) for entry in parse_dir(image) if entry[0].startswith('VIDEO'))
        assert physical[:4]==b'ZXFC' and physical[4]==11
        count=struct.unpack_from('<H',physical,16)[0]+1
        logical=b''.join(physical[p*256:(p+1)*256] for p in disk_layout.positions(count,meta['video_sector']))
        length=struct.unpack_from('<I',logical,22)[0];body=logical[256:256+length]
        position=0;frames=0
        for saved in volume['blocks']:
            flagged,decoded_length=struct.unpack_from('<HH',body,position);position+=4
            length=flagged&32767;payload=body[position:position+length];position+=length
            data=payload if flagged&32768 else zx0_codec.decompress(payload)
            assert len(data)==decoded_length==saved['decoded_bytes'] and sha(data)==saved['sha256']
            assert length==saved['compressed_bytes']
            offset=0;block_frames=0
            while offset<len(data):
                packet_length=struct.unpack_from('<H',data,offset)[0];offset+=2
                packet=data[offset:offset+packet_length];offset+=packet_length
                audio_end=0
                for _ in range(6):audio_end+=1+2*packet[audio_end]
                assert audio_end<len(packet) and packet[-1]==0
                sound+=packet[:audio_end]
                screen=packet[audio_end:];pictures+=struct.pack('<H',len(screen))+screen
                block_frames+=1
            assert offset==len(data) and block_frames==saved['frames']
            frames+=block_frames;blocks.append(data)
        assert position==len(body) and frames==volume['frames']
        next_frame=volume['frame_end']
    assert next_frame==meta['frames']
    all_blocks=[b for v in meta['volumes'] for b in v['blocks']]
    return meta,blocks,bytes(sound),bytes(pictures),dict(
        trd_sha256=hashes,volumes=len(meta['volumes']),
        images_bytes=sum((build/v['trd_name']).stat().st_size for v in meta['volumes']),
        physical_video_bytes=sum(v['physical_video_sectors']*256 for v in meta['volumes']),
        zx0_block_bytes=sum(b['compressed_bytes']+4 for b in all_blocks),
        deflate_same_blocks_bytes=sum(min(len(deflate(data)),len(data))+4 for data in blocks),
        decoded_block_bytes=sum(map(len,blocks)),
        inline_audio_bytes=len(sound),video_commands_with_lengths_bytes=len(pictures))


def zx0_size(chunks,executable,cache):
    cache.mkdir(parents=True,exist_ok=True);total=0
    for index,chunk in enumerate(chunks):
        raw=cache/(sha(chunk)+'.raw');packed=raw.with_suffix('.zx0')
        if not packed.exists():
            raw.write_bytes(chunk)
            subprocess.run([str(executable.resolve()),'-f',str(raw.resolve()),str(packed.resolve())],check=True,capture_output=True)
        data=packed.read_bytes();assert zx0_codec.decompress(data)==chunk
        total+=4+min(len(data),len(chunk))
    return total


def probe_profiles(checkpoint,frames,rate,audio_raw,expected_sha,zx0=None,cache=None):
    """Threshold averaged displayed luminance; no new dithering or motion model."""
    with np.load(checkpoint) as saved:states=saved['states']
    assert len(states)==frames
    assert sha(states.tobytes())==expected_sha
    profiles=[(128,96,1,1),(64,48,1,1),(64,48,2,1),(64,48,2,2),(64,48,1,2),(48,36,1,1)]
    streams={p:[] for p in profiles};gray_lookup=np.array((0,.25,.5,1))
    palette=video.base.SCREEN_PALETTE.astype(np.float32)
    luminance=palette@np.array([.2126,.7152,.0722],dtype=np.float32)
    for index,state in enumerate(states):
        packed=state[:3072].reshape(96,32)
        levels=((packed[:,:,None]>>np.array([6,4,2,0]))&3).reshape(96,128)
        attr=np.repeat(np.repeat(state[3072:].reshape(24,32),4,0),4,1)
        bright=(attr>>6&1)*8
        ink=luminance[(attr&7)+bright];paper=luminance[(attr>>3&7)+bright]
        gray=paper+(ink-paper)*gray_lookup[levels]
        for p in profiles:
            width,height,bits,step=p
            if index%step:continue
            small=cv2.resize(gray,(width,height),interpolation=cv2.INTER_AREA)
            # Same four ink coverages as the existing player's dither patterns.
            thresholds=[127.5] if bits==1 else [31.875,95.625,191.25]
            values=np.searchsorted(thresholds,small).astype(np.uint8)
            group=values.ravel().reshape(-1,8//bits)
            packed=np.bitwise_or.reduce(group.astype(np.uint16)<<np.arange(8-bits,-1,-bits),axis=1).astype(np.uint8)
            streams[p].append(packed)
    result=[]
    # Reserve unchanged full-rate audio, including independent block headers.
    audio_blocks=[audio_raw[i:i+6138] for i in range(0,len(audio_raw),6138)]
    audio_bytes=sum(4+min(len(x),len(deflate(x))) for x in audio_blocks)
    audio_zx0=zx0_size(audio_blocks,zx0,cache) if zx0 else None
    for p,frames_data in streams.items():
        width,height,bits,step=p;matrix=np.array(frames_data,dtype=np.uint8)
        delta=matrix.copy();delta[1:]^=matrix[:-1]
        assert np.array_equal(np.bitwise_xor.accumulate(delta,axis=0),matrix)
        frame_bytes=matrix.shape[1];block_frames=6144//frame_bytes
        choices={}
        for name,array in [('absolute',matrix),('xor_previous',delta)]:
            chunks=[array[i:i+block_frames].tobytes() for i in range(0,len(array),block_frames)]
            choices[name]=sum(4+min(len(x),len(deflate(x))) for x in chunks)
        smallest=min(choices.values())
        result.append(dict(width=width,height=height,bits_per_pixel=bits,fps=rate/step,
            frames=len(matrix),last_frame_hold_seconds=(frames-(len(matrix)-1)*step)/rate,
            block_decoded_limit=6144,video_deflate_bytes=choices,
            audio_deflate_bytes=audio_bytes,total_stream_bytes=256+smallest+audio_bytes,
            note='New lossy representation; unchanged AY raw states at 50 Hz. Size only, no Z80 decoder or playback/quality validation.'))
        if zx0 and p==(64,48,1,1):
            method=min(choices,key=choices.get)
            array=delta if method=='xor_previous' else matrix
            chunks=[array[i:i+block_frames].tobytes() for i in range(0,len(array),block_frames)]
            actual=zx0_size(chunks,zx0,cache)
            result[-1]['zx0_probe']=dict(prediction=method,video_bytes=actual,
                audio_bytes=audio_zx0,total_stream_bytes=256+actual+audio_zx0)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True,help='dense complete ZX0 build')
    p.add_argument('--release-build',type=Path,required=True)
    p.add_argument('--audio',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path)
    p.add_argument('--zx0',type=Path,help='also measure the 64x48 monochrome candidate with the real ZX0 encoder')
    p.add_argument('--cache',type=Path,default=Path('.tmp/single_disk'))
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    meta,blocks,inline,pictures,dense=read_build(args.build)
    release_meta,_,_,_,released=read_build(args.release_build)
    assert meta['frames']==release_meta['frames']
    player=(args.build/'PLAYER.C.bin').read_bytes()
    assert player==(args.release_build/'PLAYER.C.bin').read_bytes()
    raw=args.audio.read_bytes();assert sha(raw)==meta['audio_source']['sha256']
    audio=[video.AyFrame.deserialize(raw[i:i+9]) for i in range(0,len(raw),9)]
    expected=b''.join(record for volume in meta['volumes'] for record in
        ay_interrupt.encode_ticks(audio[volume['frame_start']*6:volume['frame_end']*6]))
    assert inline==expected
    events=b''.join(ay_events.encode_ticks(audio))
    assert ay_events.decode_ticks(events,len(audio))==audio
    # 16 service sectors, actual loader allocation, actual player allocation.
    directory=parse_dir((args.build/meta['volumes'][0]['trd_name']).read_bytes())
    reserved=16+sum(e[2] for e in directory if e[0] in ('boot','PLAYER'))
    budget=(2560-reserved)*256
    report=dict(scope=__doc__,frames=meta['frames'],duration_seconds=meta['frames']/meta['frame_rate'],
        fps=meta['frame_rate'],source_sha256=meta['source_metadata']['source']['source_sha256'],
        capacity=dict(trd_bytes=655360,reserved_sectors=reserved,stream_bytes=budget,
            bytes_per_frame=budget/meta['frames'],bytes_per_second=budget/(meta['frames']/meta['frame_rate']),
            note='Generous storage budget before interleave holes and any new decoder growth.'),
        dense=dense,released=released,
        same_packets_whole_stream=sizes(b''.join(blocks)),
        video_without_any_audio=sizes(pictures),
        audio_raw=sizes(raw),audio_pairs=sizes(b''.join(ay_interrupt.encode_ticks(audio))),
        audio_events=sizes(events),player_sha256=sha(player),
        unchanged_player_instruction_delta_tstates=0,
        caveat='Whole-stream compressors are offline size comparisons, not Z80 implementations or a mathematical lower bound. Dense input retains seven volume keyframes.')
    if args.checkpoint:
        report['checkpoint_sha256']=sha(args.checkpoint.read_bytes())
        report['lossy_size_probes']=probe_profiles(args.checkpoint,meta['frames'],meta['frame_rate'],raw,
            meta['source_metadata']['logical_states_sha256'],args.zx0,args.cache)
        for probe in report['lossy_size_probes']:probe['spare_stream_bytes']=budget-probe['total_stream_bytes']
    report['dense']['additional_reduction_needed']=dense['zx0_block_bytes']/budget
    report['dense']['bytes_to_remove_percent']=100*(1-budget/dense['zx0_block_bytes'])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
