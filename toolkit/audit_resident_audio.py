"""Recheck complete resident-audio storage from saved streams, without ZX0.exe.

Every new video block and AY record is independently decoded and recombined
into the exact previous FAP3 packets. This audit does not run new Z80 code.
"""
import gzip
import json
from pathlib import Path
import struct

from ay_huffman_stream import encode,decode
from build_fap3_trd import sha
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from zx0_codec import decompress

ROOT=Path(__file__).parent


def main():
    names=('audio_lookahead_profile.json','resident_audio_probe.json','resident_audio_storage.json',
           'lookahead_player_build.json','streaming_zx0_input_evidence.json')
    profile,audio,storage,build,manifest=[json.loads((ROOT/n).read_bytes()) for n in names]
    for report in (profile,audio,storage):
        if not report['complete'] or report['release']: raise ValueError('incomplete or unexpected release')
        for mapping in ('source_sha256','reference_sha256'):
            for name,digest in report[mapping].items():
                if sha((ROOT/name).read_bytes())!=digest: raise ValueError(('source/reference differs',name))
    for entry in profile['evidence']:
        blob=(ROOT/entry['directory']/entry['file']).read_bytes()
        if sha(blob)!=entry['sha256'] or sha(gzip.decompress(blob))!=entry['uncompressed_sha256']:
            raise ValueError('trace evidence differs')
    initial=bytes(11);volumes=[]
    for old,sound,new,built,entry in zip(profile['volumes'],audio['volumes'],storage['volumes'],build['volumes'],manifest['evidence'],strict=True):
        if len({r['part'] for r in (old,sound,new,built,entry)})!=1: raise ValueError('volume order differs')
        packed=(ROOT/'streaming_zx0_input_evidence'/entry['file']).read_bytes()
        stream=gzip.decompress(packed)
        if sha(packed)!=entry['sha256'] or sha(stream)!=old['stream_sha256'] or sha(stream)!=built['stream_sha256']:
            raise ValueError('old stream differs')
        raw=bytearray();pos=0
        while pos<len(stream):
            size,length=struct.unpack_from('<HH',stream,pos);pos+=4
            data=decompress(stream[pos:pos+length],limit=size);pos+=length
            if len(data)!=size: raise ValueError('old decoded size differs')
            raw.extend(data)
        if pos!=len(stream) or sha(raw)!=new['raw_mux_sha256']: raise ValueError('old raw differs')
        audio_blob=bytes.fromhex(sound['coded_hex']);start,ticks=decode(audio_blob)
        if (sha(audio_blob)!=sound['coded_sha256'] or start!=initial or start.hex()!=sound['initial_registers']
                or sha(b''.join(ticks))!=sound['raw_sha256'] or len(ticks)!=6*new['frames']
                or sum(map(len,ticks))!=sound['raw_bytes']): raise ValueError('audio differs')
        repeated,detail=encode(ticks,initial)
        if repeated!=audio_blob or any(sound[k]!=v for k,v in detail.items()): raise ValueError('codec arithmetic differs')
        if sound['spare_in_16k_bank']!=16384-len(audio_blob): raise ValueError('bank budget differs')
        video=bytearray();video_bytes=0
        for b in new['blocks']:
            code=bytes.fromhex(b['code_hex'])
            if sha(code)!=b['coded_sha256'] or len(code)!=b['zx0_bytes']: raise ValueError('new compressed block differs')
            data=decompress(code,limit=b['decoded_bytes'])
            if len(data)!=b['decoded_bytes'] or len(data)>8192 or sha(data)!=b['sha256']:
                raise ValueError('new decoded block differs')
            video.extend(data);video_bytes+=len(code)+4
        if len(video)!=new['raw_video_bytes'] or sha(video)!=new['raw_video_sha256']: raise ValueError('new video differs')
        original,changed=Reader(raw),Reader(video)
        state=bytearray(initial)
        for index in range(new['frames']):
            _,packet=read_packet(original,stored_guards=False)
            expected=ticks[index*6:index*6+6]
            size=changed.u16();body=changed.take(size)
            if packet['ticks']!=expected or b''.join(expected)+body!=packet['payload']:
                raise ValueError('roundtrip changed packet bytes')
            for tick in expected:
                for reg,value in zip(tick[1::2],tick[2::2],strict=True):state[reg]=value
        original.end();changed.end();initial=bytes(state)
        data_sectors=(video_bytes+255)//256+(len(audio_blob)+255)//256
        old_overhead=built['used_sectors']-built['video_sectors']
        values=dict(video_zx0_with_headers_bytes=video_bytes,combined_bytes=video_bytes+len(audio_blob),
            delta_stream_bytes=video_bytes+len(audio_blob)-len(stream),rounded_data_sectors=data_sectors,
            old_fixed_overhead_sectors=old_overhead,estimated_used_sectors_with_old_overhead=old_overhead+data_sectors,
            estimated_free_sectors=2544-old_overhead-data_sectors)
        if any(new[k]!=v for k,v in values.items()): raise ValueError('storage arithmetic differs')
        volumes.append(dict(part=new['part'],frames=new['frames'],ticks=len(ticks),
            audio_bytes=len(audio_blob),audio_header_bytes=sound['header_bytes'],
            audio_spare_in_16k_bank=sound['spare_in_16k_bank'],video_blocks=len(new['blocks']),
            **values,exact_all_packet_bytes=True,independent_audio_initial_state=True))
    for key in ('combined_bytes','delta_stream_bytes','frames'):
        if sum(v[key] for v in volumes)!=storage[key]:raise ValueError('total differs')
    total_ticks=sum(v['ticks'] for v in volumes)
    if total_ticks!=audio['ticks'] or total_ticks!=profile['ticks']:raise ValueError('tick total differs')
    if (sum(v['raw_bytes'] for v in audio['volumes'])!=audio['raw_bytes'] or
            sum(v['total_bytes'] for v in audio['volumes'])!=audio['packed_bytes']):
        raise ValueError('audio size total differs')
    sources=('audit_resident_audio.py','test_ay_huffman_stream.py','test_audio_lookahead_profile.py')
    report=dict(complete=True,release=False,scope=__doc__,baseline_commit='8bc6a09',volumes=volumes,
        frames=sum(v['frames'] for v in volumes),ticks=total_ticks,
        compressed_bytes=sum(v['combined_bytes'] for v in volumes),
        delta_compressed_bytes=sum(v['delta_stream_bytes'] for v in volumes),
        old_audio_bytes=audio['raw_bytes'],resident_audio_bytes=audio['packed_bytes'],
        reference_sha256={n:sha((ROOT/n).read_bytes()) for n in names},
        source_sha256={n:sha((ROOT/n).read_bytes()) for n in sources},
        current_player_changed=False,new_cpu_tstates_measured=False,new_disk_images_built=False,
        actual_bootstrap_capacity_verified=False,new_playback_timing_verified=False,
        next_gate='Implement a bank-resident AY decoder and measure actual Z80 CPU/RAM before integrating a three-slot video producer.')
    (ROOT/'resident_audio_summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('reference_sha256','source_sha256')}),flush=True)


if __name__=='__main__':main()
