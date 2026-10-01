"""Measure complete startup capacity for one already encoded CB44 partition.

Reuse all video blocks and AY records. Do not write a disk set or claim
playback timing. Independently cold-check any volume that actually fits.
"""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np

from build_fap3_trd import sha
from build_integrated_bootstrap import check_cold
from cell_codebook_player import Builder
from convert_cb41 import OPTIONS
from convert_video import write_json
from rebuild_cell_player import verify_cached_blocks
from row_dictionary_video import reference_tables
import banked_resident_audio


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('base','probe','audio','output','zx0','lzsa'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.base.read_bytes());source=a.base.parent
    if a.output.exists() and any(a.output.iterdir()):p.error('output must be new or empty')
    a.output.mkdir(parents=True)
    raw=(source/'work/stream.raw').read_bytes();assert sha(raw)==m['raw_sha256']
    with np.load(source/'work'/a.base.stem/'states.npz',allow_pickle=False) as saved:frames=saved['states']
    assert sha(frames.tobytes())==m['states_sha256']
    report=json.loads((a.probe/'report.json').read_bytes());volumes=json.loads((a.probe/'volumes.json').read_bytes())
    assert report['complete'] and report['frames_sha256']==sha(frames.tobytes())
    ends=[v['end'] for v in volumes];assert ends[-1]==len(frames)
    states=np.zeros((len(frames),3840),dtype=np.uint8);states[:,3072:]=frames[:,3840:]
    identity=b'CB44FXA1'+bytes.fromhex(sha((a.probe/'report.json').read_bytes()))[:6]
    results=[]
    for part,v in enumerate(volumes,1):
        stem=f'part{part:02}';cached=json.loads((a.probe/(stem+'.json')).read_bytes())
        cell=gzip.decompress((a.probe/(stem+'.raw.gz')).read_bytes())
        stream=gzip.decompress((a.probe/(stem+'.stream.gz')).read_bytes())
        assert sha(cell)==cached['raw_sha256'] and sha(stream)==cached['stream_sha256']
        check=verify_cached_blocks(stream,cell,cached['blocks'])
        sound=(a.audio/(stem+'.ayb1')).read_bytes();_,records=banked_resident_audio.decode(sound)
        lo,hi=v['start'],v['end'];assert len(records)==(hi-lo)*m['frame_fields']
        with reference_tables(cached['rows']):
            b=Builder(raw,states,a.zx0.resolve(),a.output/'zx0',row_dictionary=cached['rows'],
                lzsa=a.lzsa.resolve(),series_fingerprint=identity,cell_raw=cell,cell_start=lo,
                frame_fields=m['frame_fields'],reference_frames=frames,shared_audio=True,**OPTIONS)
            b.ends=ends;b.inplace_streams[lo,hi]=stream,cached['blocks'];b.resident_streams[lo,hi]=b'',sound
            image,meta=b.volume(lo,hi,part);write_json(a.output/(stem+'.json'),meta)
            cold=check_cold(image,meta,b.expected_banks) if image is not None else None
        results.append(dict(part=part,start=lo,end=hi,used_sectors=meta['used_sectors'],
            available_sectors=2544,video_sectors=meta['video_sectors'],video_bytes=len(stream),
            fits=image is not None,cold=cold,cache_check=check,
            source_audio_sha256=sha(sound),fixed_audio_bytes=meta['resident_audio']['compiled']['fixed_bytes'],
            bank6_tail=meta['resident_audio']['bank6_reserved_bytes']))
        write_json(a.output/'capacity.json',dict(complete=len(results)==len(volumes),release=False,scope=__doc__,
            all_volumes_fit=all(r['fits'] for r in results) and len(results)==len(volumes),
            total_used_sectors=sum(r['used_sectors'] for r in results),volumes=results))
        print(json.dumps({k:r for k,r in results[-1].items() if k not in ('cold','cache_check')}),flush=True)


if __name__=='__main__':main()
