"""Select four CB42 cuts from short windows, then encode only that partition.

Reports actual video bytes and exact two-bank AY sizes. Startup sectors,
native playback and full physical disk timing still need the TRD builder.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from build_fap3_trd import sha
from build_long_video_trd import AyFrame
from convert_cb41 import plan_volumes,pack_blocks
from convert_video import write_json
from dynamic_row_dictionary import representation
from probe_adaptive_block_codecs import ExternalCodec


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','metadata','lzsa','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    prepared=json.loads(a.prepared.read_bytes());frames=[]
    for chunk in prepared['chunks']:
        path=a.prepared.parent/chunk['file'];assert sha(path.read_bytes())==chunk['sha256']
        with np.load(path,allow_pickle=False) as data:frames.extend(data['five_states'])
    frames=np.stack(frames);assert len(frames)==prepared['frames']
    data=(a.prepared.parent/'audio.bin').read_bytes();assert sha(data)==prepared['ay_sha256']
    audio=[AyFrame.deserialize(data[i:i+9]) for i in range(0,len(data),9)]
    labels=json.loads(a.metadata.read_bytes())['audio_labels']
    codec=ExternalCodec('lzsa2',a.lzsa,a.lzsa,'existing repository executable')
    cache=a.output/'lzsa';cache.mkdir(exist_ok=True)
    parts,plan=plan_volumes(frames,audio,labels,codec,cache,4096,frame_fields=5,
        target_volumes=4,dynamic_rows=True,audio_banks=2)
    write_json(a.output/'partition.json',plan)
    assert len(parts)==4,'audio memory would require more than four disks'
    print(json.dumps(dict(boundaries=plan['boundaries'],estimates=plan['balanced_target']['estimated_video_bytes'])),flush=True)
    records=[]
    for number,part in enumerate(parts,1):
        lo,hi=part['start'],part['end'];chosen=representation(frames,lo,hi)
        coded,blocks=pack_blocks(chosen['raw'],codec,cache)
        stem=f'part{number:02}'
        (a.output/(stem+'.raw')).write_bytes(chosen['raw'])
        (a.output/(stem+'.stream')).write_bytes(coded)
        (a.output/(stem+'.ayb1')).write_bytes(part['audio'])
        write_json(a.output/(stem+'-rows.json'),chosen['rows'])
        write_json(a.output/(stem+'-frames.json'),dict(details=chosen['details'],proof=chosen['dynamic_proof']))
        record=dict(start=lo,end=hi,raw_bytes=len(chosen['raw']),video_bytes=len(coded),
            video_sectors=(len(coded)+255)//256,raw_sha256=sha(chosen['raw']),stream_sha256=sha(coded),
            row_updates=chosen['row_updates'],unique_literal_rows=chosen['unique_literal_rows'],
            audio=part['audio_report'],blocks=blocks,host_screens_exact=True)
        records.append(record);write_json(a.output/'volumes.json',records)
        print(json.dumps({k:record[k] for k in ('start','end','video_bytes','video_sectors','row_updates')}),flush=True)
    report=dict(complete=True,release=False,scope=__doc__,candidate_partitions_encoded=1,
        windows=len(plan['windows']),whole_movie_timing_verified=False,
        final_disk_capacity_verified=False,prepared_sha256=sha(a.prepared.read_bytes()),
        frames_sha256=sha(frames.tobytes()),ay_sha256=sha(data),boundaries=plan['boundaries'],volumes=records,
        video_sectors=sum(v['video_sectors'] for v in records),available_sectors=4*2544,
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('dynamic_row_dictionary.py','convert_cb41.py','balance_cb41_cadence.py','probe_four_dynamic_disks.py')})
    write_json(a.output/'report.json',report)
    print(json.dumps(dict(complete=True,video_sectors=report['video_sectors'],available_sectors=report['available_sectors'])))


if __name__=='__main__':main()
