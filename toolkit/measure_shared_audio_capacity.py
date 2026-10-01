"""Measure complete startup capacity for one already encoded cell partition.

Reuse all video blocks and AY records. Optionally save selected diagnostic
images and their rebuild inputs. Independently cold-check every fitting volume;
neither a capacity result nor a saved image establishes playback timing.
"""
import argparse
import gzip
import json
from pathlib import Path
import shutil
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
    p.add_argument('--four-video-slots',action='store_true',help='move AY payload to bank 6 with fixed overflow')
    p.add_argument('--parts',type=int,nargs='+',help='one-based volumes to measure; default all')
    p.add_argument('--write-images',action='store_true',help='save diagnostic TRDs and cached rebuild inputs')
    a=p.parse_args();m=json.loads(a.base.read_bytes());source=a.base.parent
    if a.output.exists() and any(a.output.iterdir()):p.error('output must be new or empty')
    a.output.mkdir(parents=True)
    raw=(source/'work/stream.raw').read_bytes();assert sha(raw)==m['raw_sha256']
    with np.load(source/'work'/a.base.stem/'states.npz',allow_pickle=False) as saved:frames=saved['states']
    assert sha(frames.tobytes())==m['states_sha256']
    report=json.loads((a.probe/'report.json').read_bytes());volumes=json.loads((a.probe/'volumes.json').read_bytes())
    assert report['complete'] and report['frames_sha256']==sha(frames.tobytes())
    ends=[v['end'] for v in volumes];assert ends[-1]==len(frames)
    selected=set(a.parts or range(1,len(volumes)+1))
    if not selected or not selected<=set(range(1,len(volumes)+1)):p.error('invalid selected parts')
    if a.write_images:
        (a.output/'work').mkdir()
        shutil.copyfile(source/'work/stream.raw',a.output/'work/stream.raw')
        write_json(a.output/'partition.json',dict(boundaries=[0]+ends))
    states=np.zeros((len(frames),3840),dtype=np.uint8);states[:,3072:]=frames[:,3840:]
    identity=b'CB44FXA1'+bytes.fromhex(sha((a.probe/'report.json').read_bytes()))[:6]
    results=[];images=[]
    for part,v in enumerate(volumes,1):
        if part not in selected:continue
        stem=f'part{part:02}';cached=json.loads((a.probe/(stem+'.json')).read_bytes())
        cell=gzip.decompress((a.probe/(stem+'.raw.gz')).read_bytes())
        stream=gzip.decompress((a.probe/(stem+'.stream.gz')).read_bytes())
        assert sha(cell)==cached['raw_sha256'] and sha(stream)==cached['stream_sha256']
        check=verify_cached_blocks(stream,cell,cached['blocks'])
        sound=(a.audio/(stem+'.ayb1')).read_bytes();_,records=banked_resident_audio.decode(sound)
        lo,hi=v['start'],v['end'];assert len(records)==(hi-lo)*m['frame_fields']
        if a.write_images:
            from dynamic_row_dictionary import decode_check
            proof=decode_check(cell,frames,lo,hi,cached['rows'])
            assert proof['screen_sha256']==cached['proof']['screen_sha256']
            folder=a.output/'work'/stem;folder.mkdir()
            (folder/'codebook.raw').write_bytes(cell);(folder/'codebook.stream').write_bytes(stream)
            (folder/'audio.ayh1').write_bytes(sound)
            write_json(folder/'rows.json',cached['rows'])
            shutil.copyfile(source/'work'/a.base.stem/'states.npz',folder/'states.npz')
        with reference_tables(cached['rows']):
            b=Builder(raw,states,a.zx0.resolve(),a.output/'zx0',row_dictionary=cached['rows'],
                lzsa=a.lzsa.resolve(),series_fingerprint=identity,cell_raw=cell,cell_start=lo,
                frame_fields=m['frame_fields'],reference_frames=frames,shared_audio=True,
                four_slots=a.four_video_slots,**OPTIONS)
            b.ends=ends;b.inplace_streams[lo,hi]=stream,cached['blocks'];b.resident_streams[lo,hi]=b'',sound
            image,meta=b.volume(lo,hi,part);write_json(a.output/(stem+'.json'),meta)
            cold=check_cold(image,meta,b.expected_banks) if image is not None else None
        if a.write_images and image is not None:
            (a.output/(stem+'.trd')).write_bytes(image)
            images.append(dict(file=stem+'.trd',metadata=stem+'.json',states='work/'+stem+'/states.npz',
                frames=hi-lo,frame_start=lo,frame_end_exclusive=hi,used_sectors=meta['used_sectors'],
                free_sectors=meta['free_sectors'],sha256=sha(image),host_screens_exact=True,
                row_entries=cached['rows']['entries']))
            write_json(a.output/'volumes.json',images)
        results.append(dict(part=part,start=lo,end=hi,used_sectors=meta['used_sectors'],
            available_sectors=2544,video_sectors=meta['video_sectors'],video_bytes=len(stream),
            fits=image is not None,cold=cold,cache_check=check,
            source_audio_sha256=sha(sound),fixed_audio_bytes=meta['resident_audio']['compiled']['fixed_bytes'],
            bank6_tail=meta['resident_audio']['bank6_reserved_bytes'],
            fixed_payload_bytes=meta['resident_audio']['compiled'].get('fixed_payload_bytes',0)))
        write_json(a.output/'capacity.json',dict(complete=len(results)==len(selected),release=False,scope=__doc__,
            selected_parts=sorted(selected),whole_partition=len(selected)==len(volumes),
            all_volumes_fit=all(r['fits'] for r in results) and len(results)==len(volumes),
            total_used_sectors=sum(r['used_sectors'] for r in results),volumes=results))
        print(json.dumps({k:r for k,r in results[-1].items() if k not in ('cold','cache_check')}),flush=True)


if __name__=='__main__':main()
