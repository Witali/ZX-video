"""Recompress video-only packets plus resident AYH1, preserving every byte.

Optimal ZX0 v2 in independent <=8192-byte blocks; four-byte block headers.
The old disk's fixed overhead is retained as a comparison, but new player,
bootstrap/table placement, sector alignment and timing are not implemented.
This is a complete storage probe, not new independently bootable TRDs.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

from ay_huffman_stream import decode
from build_fap3_trd import sha
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from zx0_codec import decompress

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zx0',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--jobs',type=int,choices=range(1,5),default=4)
    p.add_argument('--output',type=Path,default=ROOT/'resident_audio_storage.json')
    a=p.parse_args();a.cache.mkdir(parents=True,exist_ok=True)
    paths=[ROOT/n for n in ('resident_audio_probe.json','lookahead_player_build.json','streaming_zx0_input_evidence.json')]
    audio,build,manifest=[json.loads(f.read_bytes()) for f in paths]
    if not all(r['complete'] for r in (audio,build,manifest)): raise ValueError('incomplete input')
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='8bc6a09',volumes=[],
        reference_sha256={p.name:sha(p.read_bytes()) for p in paths},
        source_sha256={n:sha((ROOT/n).read_bytes()) for n in
                       ('probe_resident_audio_storage.py','ay_huffman_stream.py','zx0_codec.py')},
        encoder_sha256=sha(a.zx0.read_bytes()),encoder_mode='optimal ZX0 v2',
        actual_new_trds_built=False,runtime_decoder_implemented=False,playback_verified=False)
    def save():a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    def compress(chunk):
        digest=sha(chunk);path=a.cache/(digest+'.zx0')
        if path.exists():coded=path.read_bytes()
        else:
            with tempfile.TemporaryDirectory(dir=a.cache) as tmp:
                src,dst=Path(tmp)/'input.raw',Path(tmp)/'output.zx0'
                src.write_bytes(chunk)
                subprocess.run([str(a.zx0.resolve()),'-f',str(src.resolve()),str(dst.resolve())],
                    check=True,capture_output=True)
                coded=dst.read_bytes()
            # Identical blocks may finish in parallel; publish atomically.
            with tempfile.NamedTemporaryFile(dir=a.cache,delete=False) as f:
                f.write(coded);temporary=f.name
            os.replace(temporary,path)
        if decompress(coded,limit=len(chunk))!=chunk: raise AssertionError('ZX0 mismatch')
        return dict(decoded_bytes=len(chunk),zx0_bytes=len(coded),sha256=digest,coded_sha256=sha(coded),
                    code_hex=coded.hex())
    try:
        for sound,built,entry in zip(audio['volumes'],build['volumes'],manifest['evidence'],strict=True):
            packed=(ROOT/'streaming_zx0_input_evidence'/entry['file']).read_bytes()
            stream=gzip.decompress(packed)
            if sha(packed)!=entry['sha256'] or sha(stream)!=built['stream_sha256']:
                raise ValueError('wrong archived stream')
            raw=bytearray();pos=0
            while pos<len(stream):
                size,length=struct.unpack_from('<HH',stream,pos);pos+=4
                chunk=decompress(stream[pos:pos+length],limit=size);pos+=length
                if len(chunk)!=size: raise ValueError('short decoded block')
                raw.extend(chunk)
            if pos!=len(stream): raise ValueError('trailing bytes')
            coded_audio=bytes.fromhex(sound['coded_hex'])
            if sha(coded_audio)!=sound['coded_sha256']: raise ValueError('audio differs')
            _,ticks=decode(coded_audio)
            r=Reader(bytes(raw));video=bytearray();reconstructed=bytearray()
            for index in range(sound['ticks']//6):
                _,packet=read_packet(r,stored_guards=False)
                if packet['ticks']!=ticks[index*6:index*6+6]: raise ValueError('different audio records')
                ay=b''.join(packet['ticks']);body=packet['payload'][len(ay):]
                video+=struct.pack('<H',len(body))+body
                original=ay+body
                reconstructed+=struct.pack('<H',len(original))+original
            r.end()
            if reconstructed!=raw: raise AssertionError('mux roundtrip differs')
            row=dict(part=entry['part'],frames=sound['ticks']//6,old_stream_bytes=len(stream),
                old_used_sectors=built['used_sectors'],old_video_sectors=built['video_sectors'],
                raw_video_bytes=len(video),raw_video_sha256=sha(video),raw_mux_sha256=sha(raw),
                ay_bytes=len(coded_audio),ay_sha256=sha(coded_audio),exact_mux_roundtrip=True,blocks=[])
            report['volumes'].append(row);save()
            chunks=[bytes(video[i:i+8192]) for i in range(0,len(video),8192)]
            with ThreadPoolExecutor(max_workers=a.jobs) as pool:
                for index,block in enumerate(pool.map(compress,chunks)):
                    row['blocks'].append(block)
                    if index%20==0:
                        save();print(f'Part {entry["part"]}: {index+1}/{len(chunks)} exact optimal ZX0 blocks',flush=True)
            video_bytes=sum(b['zx0_bytes']+4 for b in row['blocks'])
            # Independently round video and audio sections before comparison.
            combined_sectors=(video_bytes+255)//256+(len(coded_audio)+255)//256
            old_overhead=built['used_sectors']-built['video_sectors']
            row.update(complete=True,video_zx0_with_headers_bytes=video_bytes,
                combined_bytes=video_bytes+len(coded_audio),delta_stream_bytes=video_bytes+len(coded_audio)-len(stream),
                rounded_data_sectors=combined_sectors,old_fixed_overhead_sectors=old_overhead,
                estimated_used_sectors_with_old_overhead=old_overhead+combined_sectors,
                estimated_free_sectors=2544-old_overhead-combined_sectors)
            save();print(json.dumps({k:v for k,v in row.items() if k!='blocks'}),flush=True)
        report.update(complete=True,frames=sum(v['frames'] for v in report['volumes']),
            combined_bytes=sum(v['combined_bytes'] for v in report['volumes']),
            delta_stream_bytes=sum(v['delta_stream_bytes'] for v in report['volumes']))
    except Exception as exc:
        report['failure']=repr(exc);save();raise
    save()


if __name__=='__main__':main()
