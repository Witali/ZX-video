"""Assemble actual volume layouts for lossless fragment-selection candidates.

Uses the saved independent bootstrap and player options, before debugger
queue/compiled-mask installation. No images are published and no playback
claim is made. A rejected over-capacity volume still has exact layout data.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from run_deferred_disk import ReadThroughBuilder


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('probe','directory','source','metadata','states','zx0','output'):
        p.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args();probe=json.loads(args.probe.read_bytes());meta=json.loads(args.metadata.read_bytes())
    if not probe['complete']:raise ValueError('storage probe is incomplete')
    with np.load(args.states,allow_pickle=False) as f:states=f['states']
    if sha(states.tobytes())!=probe['states_sha256']:raise ValueError('wrong states')
    options={k:meta[k] for k in ('fast_disk','cached_seek','interleaved','cold_bitmaps','startup_delta',
        'inline_matches','fast_noop_scan','irq_safe_paging','static_cache_borders','carry_huffman','register_fragments',
        'deferred_limit','keepalive_fields','frame_service')}
    result=dict(complete=False,release=False,scope=__doc__,probe_sha256=sha(args.probe.read_bytes()),
        input_metadata_sha256=sha(args.metadata.read_bytes()),part=meta['part'],options=options,variants=[])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    memo={}
    entries=[('baseline',args.source,probe['source_sha256'])]+[
        (f"allowance-{v['allowance_bits']}",args.directory/v['raw_file'],v['sha256']) for v in probe['variants']]
    for name,path,digest in entries:
        raw=path.read_bytes()
        if sha(raw)!=digest:raise ValueError('wrong candidate')
        b=ReadThroughBuilder(raw,states,args.zx0.resolve(),args.directory/'zx0',**options)
        b.memo=memo;b.ends=[1624,2921,4221]
        if (meta['frame_start'],meta['frame_end_exclusive'])!=(b.ends[meta['part']-2] if meta['part']>1 else 0,b.ends[meta['part']-1]):
            raise ValueError('different baseline partition')
        image,m=b.volume(meta['frame_start'],meta['frame_end_exclusive'],meta['part'])
        row=dict(name=name,source_sha256=digest,fits=image is not None,
            **{k:m[k] for k in ('independently_bootable','used_sectors','free_sectors','video_bytes',
                               'video_sectors','video_start_sector','video_physical_sectors','layout_padding_sectors')})
        result['variants'].append(row);save();print(json.dumps(row),flush=True)
        if name=='baseline' and any(row[k]!=meta[k] for k in ('used_sectors','video_bytes','video_start_sector')):
            raise AssertionError('baseline assembly differs')
    result['complete']=True;save()


if __name__=='__main__':main()
