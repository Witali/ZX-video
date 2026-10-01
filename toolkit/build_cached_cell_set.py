"""Assemble one coherent CB46 set from accepted cached video and AY streams.

No frame quantization, compression search or alternate partition is performed.
Each volume receives a fresh cold bootstrap and a common content-derived ID.
Native/Fuse playback verification is separate from this cold capacity build.
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
from dynamic_row_dictionary import decode_check
from guarded_cb46 import PLAYER_OPTIONS
from invisible_attribute_writes import verify_rgb
from rebuild_cell_player import verify_cached_blocks
from row_dictionary_video import reference_tables
import banked_resident_audio


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','probe','audio','output','zx0','lzsa'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--replacement-metadata',type=Path,action='append',default=[])
    a=p.parse_args();base=read(a.base);source=a.base.parent
    if a.output.exists() and any(a.output.iterdir()):p.error('output must be new or empty')
    raw=(source/'work/stream.raw').read_bytes();assert sha(raw)==base['raw_sha256']
    statefile=source/'work'/a.base.stem/'states.npz'
    with np.load(statefile,allow_pickle=False) as data:original=data['states']
    assert sha(original.tobytes())==base['states_sha256']
    probe=read(a.probe/'report.json');volumes=read(a.probe/'volumes.json')
    assert probe['complete'] and probe['frames_sha256']==base['states_sha256']
    boundaries=[0]+[v['end'] for v in volumes]
    assert boundaries[-1]==len(original) and all(v['start']==boundaries[i] for i,v in enumerate(volumes))
    overrides={}
    for path in a.replacement_metadata:
        m=read(path);assert m['part'] not in overrides
        assert 1<=m['part']<=len(volumes)
        overrides[m['part']]=(path,m)
    inputs=[]
    for part,v in enumerate(volumes,1):
        name=f'part{part:02}';c=read(a.probe/(name+'.json'))
        cell=gzip.decompress((a.probe/(name+'.raw.gz')).read_bytes())
        stream=gzip.decompress((a.probe/(name+'.stream.gz')).read_bytes())
        assert sha(cell)==c['raw_sha256'] and sha(stream)==c['stream_sha256']
        sound=(a.audio/(name+'.ayb1')).read_bytes();states=original
        input_statefile=statefile;replacement=None
        if part in overrides:
            path,m=overrides[part];cache=path.parent/'work'/path.stem
            assert (m['frame_start'],m['frame_end_exclusive'])==(v['start'],v['end'])
            assert m['frame_fields']==base['frame_fields']==5 and m['cell_codebook']['wire']=='CB46'
            cell=(cache/'codebook.raw').read_bytes();stream=(cache/'codebook.stream').read_bytes()
            assert sha(cell)==m['cell_codebook']['raw_sha256'] and len(stream)==m['video_bytes']
            assert sound==(cache/'audio.ayh1').read_bytes()
            input_statefile=cache/'states.npz'
            with np.load(input_statefile,allow_pickle=False) as data:states=data['states']
            assert sha(states.tobytes())==m['states_sha256']
            assert np.array_equal(states[:,:3840],original[:,:3840])
            rgb=verify_rgb(original,states,v['start'],v['end'])
            c=dict(blocks=m['blocks'],rows=read(cache/'rows.json'))
            replacement=dict(metadata=str(path),metadata_sha256=sha(path.read_bytes()),rgb_proof=rgb)
        lo,hi=v['start'],v['end'];_,ticks=banked_resident_audio.decode(sound)
        assert len(ticks)==(hi-lo)*base['frame_fields']
        blocks=verify_cached_blocks(stream,cell,c['blocks'])
        proof=decode_check(cell,states,lo,hi,c['rows'])
        inputs.append(dict(part=part,start=lo,end=hi,cell=cell,stream=stream,sound=sound,
            states=states,statefile=input_statefile,rows=c['rows'],blocks=c['blocks'],
            proof=proof,cache_check=blocks,replacement=replacement))
    identity_contract=dict(boundaries=boundaries,frame_fields=base['frame_fields'],
        player_options=PLAYER_OPTIONS,legacy_options=OPTIONS,raw_sha256=sha(raw),
        sources=[dict(video=sha(x['stream']),states=sha(x['states'].tobytes()),audio=sha(x['sound'])) for x in inputs])
    identity=b'CB46SET1'+bytes.fromhex(sha(json.dumps(identity_contract,sort_keys=True).encode()))[:6]
    work=a.output/'work';work.mkdir(parents=True)
    (work/'stream.raw').write_bytes(raw);shutil.copyfile(statefile,work/'original-states.npz')
    write_json(a.output/'partition.json',dict(boundaries=boundaries))
    write_json(a.output/'identity.json',dict(fingerprint=identity.hex(),contract=identity_contract))
    records=[];checks=[]
    for x in inputs:
        part,lo,hi=x['part'],x['start'],x['end'];stem=f'ZX-video-refined_part{part:02}'
        folder=work/stem;folder.mkdir()
        for name,key in (('codebook.raw','cell'),('codebook.stream','stream'),('audio.ayh1','sound')):(folder/name).write_bytes(x[key])
        shutil.copyfile(x['statefile'],folder/'states.npz');write_json(folder/'rows.json',x['rows'])
        write_json(folder/'cached-proof.json',dict(host=x['proof'],blocks=x['cache_check'],replacement=x['replacement']))
        scaffold=np.zeros((len(x['states']),3840),dtype=np.uint8);scaffold[:,3072:]=x['states'][:,3840:]
        with reference_tables(x['rows']):
            b=Builder(raw,scaffold,a.zx0.resolve(),work/'zx0',row_dictionary=x['rows'],lzsa=a.lzsa.resolve(),
                series_fingerprint=identity,cell_raw=x['cell'],cell_start=lo,frame_fields=base['frame_fields'],
                reference_frames=x['states'],**PLAYER_OPTIONS,**OPTIONS)
            b.ends=boundaries[1:];b.inplace_streams[lo,hi]=x['stream'],x['blocks'];b.resident_streams[lo,hi]=b'',x['sound']
            image,m=b.volume(lo,hi,part);write_json(a.output/(stem+'.json'),m)
            if image is None:raise ValueError(f'Volume {part} exceeds capacity: {m["used_sectors"]}')
            assert bytes.fromhex(m['disk_id_hex'])==identity+part.to_bytes(2,'little')
            assert m['independently_bootable'] and m['used_sectors']<=2544
            cold=check_cold(image,m,b.expected_banks)
        (a.output/(stem+'.trd')).write_bytes(image)
        records.append(dict(file=stem+'.trd',metadata=stem+'.json',states='work/'+stem+'/states.npz',
            frames=hi-lo,frame_start=lo,frame_end_exclusive=hi,used_sectors=m['used_sectors'],
            free_sectors=m['free_sectors'],sha256=sha(image)))
        checks.append(dict(part=part,cold=cold,cache_check=x['cache_check']))
        write_json(a.output/'volumes.json',records)
        write_json(a.output/'build.json',dict(complete=len(records)==len(inputs),release=False,scope=__doc__,
            fingerprint=identity.hex(),frames=len(original),frame_fields=base['frame_fields'],
            original_states_sha256=base['states_sha256'],boundaries=boundaries,checks=checks,
            source_metadata_sha256=sha(a.base.read_bytes()),probe_report_sha256=sha((a.probe/'report.json').read_bytes())))
        print(json.dumps(dict(part=part,frames=hi-lo,used_sectors=m['used_sectors'],video_bytes=len(x['stream']),cold_exact=True)),flush=True)


if __name__=='__main__':main()
