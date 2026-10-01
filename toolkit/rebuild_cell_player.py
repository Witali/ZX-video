"""Rebuild one cached CB42/44 volume without preparing or encoding video again.

Retain exact raw video, compressed blocks, AY, global frame histories and
volume boundaries. A failed capacity build is valid input for another capacity
probe. This is not a shortcut around full timing/content release gates.
"""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import struct

import numpy as np

from build_fap3_trd import sha
from build_cell_codebook_trd import verify
from build_integrated_bootstrap import check_cold
from cell_codebook_player import Builder
from convert_cb41 import OPTIONS
from convert_video import write_json
from row_dictionary_video import reference_tables
import lzsa2_stream


def verify_cached_blocks(coded,cell,blocks):
    at=decoded=0
    for block in blocks:
        count,size=struct.unpack_from('<HH',coded,at);at+=4
        assert (count,size)==(block['decoded_bytes'],block['compressed_bytes'])
        payload=coded[at:at+size];at+=size
        exact,_=lzsa2_stream.trace(payload,limit=count,input_start=block['inplace_layout']['input_start'])
        assert exact==cell[decoded:decoded+count] and sha(exact)==block['sha256']
        decoded+=count
    assert at==len(coded) and decoded==len(cell)
    return dict(complete=True,blocks=len(blocks),coded_bytes=at,raw_bytes=decoded,coded_sha256=sha(coded))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('metadata','output','zx0','lzsa'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--verify',choices=('cpu','cold','none'),default='cpu')
    p.add_argument('--shared-audio',action='store_true',help='experimental fixed AY decoder/trees and shared payload')
    p.add_argument('--four-video-slots',action='store_true',help='requires shared AY in bank 6/fixed RAM; use bank 4 as a fourth video slot')
    p.add_argument('--cell-probe',type=Path,help='validated replacement window JSON with sibling .raw.gz/.stream.gz')
    p.add_argument('--dictionary-probe',type=Path,help='validated numbering variant folder from probe_dictionary_numbering.py')
    p.add_argument('--inline-cells',action='store_true',help='experimental CB46 unrolled cell renderer, same video bytes')
    p.add_argument('--sector-cache',action='store_true',help='prefetch compressed sectors in spare bank-7 RAM')
    p.add_argument('--streaming-lzsa2',action='store_true',help='guarded input-prefix decoding; retain exact LZSA2 bytes')
    a=p.parse_args();m=json.loads(a.metadata.read_bytes());source=a.metadata.parent;stem=a.metadata.stem
    if a.cell_probe and a.dictionary_probe:p.error('choose one replacement probe')
    if a.output.exists() and any(a.output.iterdir()):p.error('output must be new or empty')
    if m['cell_codebook']['wire'] not in ('CB42','CB44','CB46'):p.error('cached rebuild needs dynamic rows')
    work=a.output/'work';folder=work/stem;folder.mkdir(parents=True)
    previous=source/'work'/stem
    raw=(source/'work/stream.raw').read_bytes();assert sha(raw)==m['raw_sha256']
    cell=(previous/'codebook.raw').read_bytes();assert sha(cell)==m['cell_codebook']['raw_sha256']
    coded=(previous/'codebook.stream').read_bytes();assert len(coded)==m['video_bytes']
    cache_check=verify_cached_blocks(coded,cell,m['blocks'])
    audio=(previous/'audio.ayh1').read_bytes();assert sha(audio)==m['resident_audio']['coded_audio_sha256']
    with np.load(previous/'states.npz',allow_pickle=False) as saved:frames=saved['states']
    assert sha(frames.tobytes())==m['states_sha256']
    rows=json.loads((previous/'rows.json').read_bytes())
    partition=json.loads((source/'partition.json').read_bytes());ends=partition['boundaries'][1:]
    start,end=m['frame_start'],m['frame_end_exclusive'];part=m['part']
    assert ends[part-1]==end and partition['boundaries'][part-1]==start
    identity=bytes.fromhex(m['disk_id_hex'])[:14]
    if 'trd_sha256' not in m:identity=b'CB44TST1'+bytes.fromhex(sha(cell))[:6]
    for name in ('codebook.raw','codebook.stream','audio.ayh1','states.npz','rows.json','dynamic-rows.json'):
        if (previous/name).exists():shutil.copyfile(previous/name,folder/name)
    if a.cell_probe:
        probe=json.loads(a.cell_probe.read_bytes())
        assert probe['rows']==rows and probe['details'][0]['frame']==start and len(probe['details'])==end-start
        cell=gzip.decompress(a.cell_probe.with_suffix('.raw.gz').read_bytes())
        coded=gzip.decompress(a.cell_probe.with_suffix('.stream.gz').read_bytes())
        assert sha(cell)==probe['raw_sha256'] and sha(coded)==probe['stream_sha256']
        from dynamic_row_dictionary import decode_check
        assert decode_check(cell,frames,start,end,rows)['screen_sha256']==probe['proof']['screen_sha256']
        cache_check=verify_cached_blocks(coded,cell,probe['blocks'])
        (folder/'codebook.raw').write_bytes(cell);(folder/'codebook.stream').write_bytes(coded)
        write_json(folder/'cell-probe.json',probe)
    blocks=probe['blocks'] if a.cell_probe else m['blocks']
    if a.dictionary_probe:
        folder_probe=a.dictionary_probe
        numbering=json.loads((folder_probe.parent/'report.json').read_bytes())
        candidate=numbering['variants'][folder_probe.name]
        assert numbering['complete'] and candidate['host_candidate_eligible']
        assert numbering['metadata_sha256']==sha(a.metadata.read_bytes())
        assert numbering['stream_sha256']==sha(coded) and numbering['raw_sha256']==sha(cell)
        cell=(folder_probe/'video.raw').read_bytes();coded=(folder_probe/'video.stream').read_bytes()
        rows=json.loads((folder_probe/'rows.json').read_bytes())
        assert sha(cell)==candidate['raw_sha256'] and sha(coded)==candidate['stream_sha256']
        from dynamic_row_dictionary import decode_check
        assert decode_check(cell,frames,start,end,rows)==candidate['proof']
        keys=('raw_start','raw_end','decoded_bytes','codec','compressed_bytes','sha256','inplace_proof','inplace_layout')
        blocks=[{key:b[key] for key in keys} for b in candidate['blocks']]
        cache_check=verify_cached_blocks(coded,cell,blocks)
        (folder/'codebook.raw').write_bytes(cell);(folder/'codebook.stream').write_bytes(coded)
        write_json(folder/'rows.json',rows);write_json(folder/'dictionary-probe.json',candidate)
    shutil.copyfile(source/'work/stream.raw',work/'stream.raw')
    write_json(a.output/'partition.json',partition)
    write_json(a.output/'cache-checks.json',cache_check)
    build_states=np.zeros((len(frames),3840),dtype=np.uint8);build_states[:,3072:]=frames[:,3840:]
    manifest=dict(complete=False,release=False,rebuild_of_sha256=sha(a.metadata.read_bytes()),
        cached_video_sha256=sha(coded),cached_audio_sha256=sha(audio),prepared_range=[start,end],whole_movie=False)
    write_json(a.output/'conversion.json',manifest)
    with reference_tables(rows):
        b=Builder(raw,build_states,a.zx0.resolve(),work/'zx0',row_dictionary=rows,lzsa=a.lzsa.resolve(),
            series_fingerprint=identity,cell_raw=cell,cell_start=start,frame_fields=m['frame_fields'],
            reference_frames=frames,shared_audio=a.shared_audio,four_slots=a.four_video_slots,inline_cells=a.inline_cells,sector_cache=a.sector_cache,streaming_lzsa2=a.streaming_lzsa2,**OPTIONS)
        b.ends=ends;b.inplace_streams[start,end]=coded,blocks;b.resident_streams[start,end]=b'',audio
        image,meta=b.volume(start,end,part);write_json(a.output/(stem+'.json'),meta)
        if image is None:
            manifest['failure']=f'Capacity: {meta["used_sectors"]} sectors / 2544'
            write_json(a.output/'conversion.json',manifest)
            print(json.dumps(manifest));return
        (a.output/(stem+'.trd')).write_bytes(image)
        record=dict(file=stem+'.trd',metadata=stem+'.json',states='work/'+stem+'/states.npz',
            frames=end-start,frame_start=start,frame_end_exclusive=end,used_sectors=meta['used_sectors'],
            free_sectors=meta['free_sectors'],sha256=sha(image),host_screens_exact=True,row_entries=rows['entries'])
        write_json(a.output/'volumes.json',[record])
        checked=dict(file=record['file'],frames=end-start)
        if a.verify!='none':checked['cold']=check_cold(image,meta,b.expected_banks)
        if a.verify=='cpu':
            cpu=verify(image,meta,frames);write_json(folder/'cpu.json',cpu)
            checked['cpu_complete']=cpu['complete'];checked['cpu_all_native_screens_exact']=cpu['all_native_screens_exact']
        write_json(a.output/'timing.json',dict(complete=a.verify!='none',release=False,
            all_nominal_deadlines_met=False,disks=[checked]))
    manifest['complete']=True;write_json(a.output/'conversion.json',manifest)
    print(json.dumps(dict(frames=end-start,used_sectors=meta['used_sectors'],video_bytes=len(coded),verified=a.verify)))


if __name__=='__main__':main()
