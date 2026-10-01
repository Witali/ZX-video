"""Encode one selected CB44 four-volume partition after bounded reuse probes.

Keeps exact frames, original AY and cuts. Size only: no native CB44 player,
final boot/startup sector accounting or complete playback verification.
"""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np

from build_fap3_trd import sha
from convert_cb41 import pack_blocks
from convert_video import write_json
from dynamic_row_dictionary import representation
from front_cell_reuse import encode
from probe_adaptive_block_codecs import ExternalCodec


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','baseline','lzsa','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    prepared=json.loads(a.prepared.read_bytes());baseline=json.loads(a.baseline.read_bytes());frames=[]
    assert sha(a.prepared.read_bytes())==baseline['prepared_sha256']
    for chunk in prepared['chunks']:
        path=a.prepared.parent/chunk['file'];assert sha(path.read_bytes())==chunk['sha256']
        with np.load(path,allow_pickle=False) as saved:frames.extend(saved['five_states'])
    frames=np.stack(frames);assert sha(frames.tobytes())==baseline['frames_sha256']
    codec=ExternalCodec('lzsa2',a.lzsa,a.lzsa,'existing repository executable')
    cache=a.output/'lzsa';cache.mkdir(exist_ok=True);volumes=[]
    for i,old in enumerate(baseline['volumes'],1):
        lo,hi=old['start'],old['end'];base=representation(frames,lo,hi,book_front_reuse=True)
        chosen=encode(base,frames,lo,hi);coded,blocks=pack_blocks(chosen['raw'],codec,cache)
        stem=f'part{i:02}'
        for suffix,data in (('raw',chosen['raw']),('stream',coded)):
            (a.output/(stem+'.'+suffix+'.gz')).write_bytes(gzip.compress(data,mtime=0))
        write_json(a.output/(stem+'.json'),dict(rows=chosen['rows'],proof=chosen['proof'],details=chosen['details'],blocks=blocks,
            raw_sha256=sha(chosen['raw']),stream_sha256=sha(coded)))
        item=dict(start=lo,end=hi,raw_bytes=len(chosen['raw']),video_bytes=len(coded),
            video_sectors=(len(coded)+255)//256,baseline_video_bytes=old['video_bytes'],
            delta_bytes=len(coded)-old['video_bytes'],front_same_cells=sum(d['front_same_cells'] for d in chosen['details']),
            original_audio=old['audio'],host_screens_exact=True)
        volumes.append(item);write_json(a.output/'volumes.json',volumes);print(json.dumps(item),flush=True)
    report=dict(complete=True,release=False,scope=__doc__,native_implemented=False,whole_movie_timing_verified=False,
        final_disk_capacity_verified=False,candidate_partitions_encoded=1,pixel_changes=0,ay_changed=False,
        prepared_sha256=sha(a.prepared.read_bytes()),frames_sha256=sha(frames.tobytes()),ay_sha256=baseline['ay_sha256'],
        baseline_report_sha256=sha(a.baseline.read_bytes()),boundaries=baseline['boundaries'],volumes=volumes,
        video_sectors=sum(v['video_sectors'] for v in volumes),available_sectors=10176,
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('dynamic_row_dictionary.py','front_cell_reuse.py','measure_front_four.py')})
    write_json(a.output/'report.json',report)
    print(json.dumps(dict(video_sectors=report['video_sectors'],spare_sectors_before_boot_audio=10176-report['video_sectors'])))


if __name__=='__main__':main()
