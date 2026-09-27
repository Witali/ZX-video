"""Measure complete lossless AYH1 volumes, before any player or RAM changes."""
import json
from pathlib import Path

from ay_huffman_stream import encode,decode
from build_fap3_trd import sha

ROOT=Path(__file__).parent


def main():
    source=ROOT/'audio_lookahead_profile.json'
    profile=json.loads(source.read_bytes())
    if not profile['complete'] or profile['ticks']!=25326: raise ValueError('incomplete source')
    state=bytearray(11);volumes=[]
    for v in profile['volumes']:
        ticks=[bytes.fromhex(t['record_hex']) for t in v['records']]
        if sha(b''.join(ticks))!=v['audio_sha256']: raise ValueError('audio source changed')
        coded,detail=encode(ticks,bytes(state))
        initial,restored=decode(coded)
        if initial!=state or restored!=ticks: raise AssertionError('AY records changed')
        for tick in ticks:
            for reg,value in zip(tick[1::2],tick[2::2],strict=True): state[reg]=value
        row=dict(part=v['part'],raw_bytes=v['audio_bytes'],raw_sha256=v['audio_sha256'],
            **detail,coded_sha256=sha(coded),coded_hex=coded.hex(),initial_registers=initial.hex(),
            spare_in_16k_bank=16384-len(coded),exact_record_roundtrip=True)
        volumes.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ('coded_hex','contexts')}),flush=True)
    report=dict(complete=True,release=False,scope=__doc__,baseline_commit='8bc6a09',volumes=volumes,
        source_sha256={n:sha((ROOT/n).read_bytes()) for n in ('probe_resident_audio.py','ay_huffman_stream.py')},
        reference_sha256={source.name:sha(source.read_bytes())},
        packed_bytes=sum(v['total_bytes'] for v in volumes),raw_bytes=sum(v['raw_bytes'] for v in volumes),
        ticks=sum(v['ticks'] for v in volumes),runtime_decoder_implemented=False,
        runtime_ram_allocation_verified=False,combined_video_audio_storage_measured=False,
        new_disk_playback_verified=False,
        warning='Single-bank fit describes encoded data plus serialized tables only; executable decoder and expanded lookup RAM are not counted.')
    (ROOT/'resident_audio_probe.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
