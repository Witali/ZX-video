"""Build actual three-volume layouts for combinations of measured accelerations.

Storage-only preflight, not playback or a release check. No new player
instructions; enables existing independently measured build options.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from build_fap3_trd import sha
from run_deferred_disk import ReadThroughBuilder


COMMON=dict(fast_disk=True,cached_seek=True,interleaved=True,cold_bitmaps=True,
    startup_delta=True,fast_noop_scan=True,irq_safe_paging=True)
VARIANTS=[('baseline',{}),('inline',dict(inline_matches=True)),
    ('deferred',dict(deferred_limit=248,keepalive_fields=64,frame_service=True)),
    ('combined',dict(inline_matches=True,deferred_limit=248,keepalive_fields=64,frame_service=True))]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('probe','partition','directory','states','zx0','output','report'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    args=p.parse_args();probe=json.loads(args.probe.read_bytes());partition=json.loads(args.partition.read_bytes())
    if not probe['complete'] or not partition['all_fit'] or partition['probe_raw_sha256']!=probe['raw_sha256']:
        raise ValueError('matching complete source and partition required')
    with np.load(args.states,allow_pickle=False) as saved:states=saved['states']
    if sha(states.tobytes())!=probe['states_sha256']:raise ValueError('states differ')
    ends=partition['selected']['ends'];args.output.mkdir(parents=True,exist_ok=True)
    sources=[]
    for i in range(1,4):
        v=next(v for v in probe['variants'] if v['name']==f'volume-{i}')
        raw=(args.directory/v['raw_file']).read_bytes()
        if sha(raw)!=v['raw_sha256']:raise ValueError('source differs')
        sources.append(raw)
    result=dict(complete=False,release=False,scope=__doc__,baseline_commit='3356730',
        states_sha256=sha(states.tobytes()),raw_sha256=list(map(sha,sources)),ends=ends,
        new_player_instructions=False,timing_verified=False,variants=[])
    args.report.parent.mkdir(parents=True,exist_ok=True)
    def save():args.report.write_text(json.dumps(result,indent=2)+'\n')
    save()
    for name,extra in VARIANTS:
        options=dict(COMMON,**extra);row=dict(name=name,options=options,volumes=[])
        result['variants'].append(row);save()
        for i,(start,end,raw) in enumerate(zip([0]+ends,ends,sources),1):
            b=ReadThroughBuilder(raw,states,args.zx0.resolve(),args.output/'zx0',**options)
            b.read_cache=[args.directory/'zx0']+args.read_cache;b.ends=ends
            image,m=b.volume(start,end,i)
            record={k:m[k] for k in ('part','frames','used_sectors','free_sectors','video_bytes','independently_bootable')}
            record['fits']=image is not None
            row['volumes'].append(record);save();print(json.dumps(dict(variant=name,**record)),flush=True)
        row['all_fit']=all(v['fits'] and v['independently_bootable'] for v in row['volumes']);save()
    result['complete']=True;save()


if __name__=='__main__':main()
