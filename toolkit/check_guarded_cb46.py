"""Check generic selection against an archived real window, without another TRD."""
import argparse
import json
from pathlib import Path

import numpy as np

from build_fap3_trd import sha
from convert_video import write_json
from guarded_cb46 import representation,select
from probe_adaptive_block_codecs import ExternalCodec


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('metadata','lzsa','output','expected'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    cache=a.output/'lzsa';cache.mkdir(exist_ok=True)
    m=json.loads(a.metadata.read_bytes());folder=a.metadata.parent/'work'/a.metadata.stem
    with np.load(folder/'states.npz',allow_pickle=False) as saved:frames=saved['states']
    raw=(folder/'codebook.raw').read_bytes();stream=(folder/'codebook.stream').read_bytes()
    rows=json.loads((folder/'rows.json').read_bytes())
    result=representation(frames,m['frame_start'],m['frame_end_exclusive'])
    assert result['raw']==raw and result['rows']==rows,'generic representation differs from the measured baseline'
    codec=ExternalCodec('lzsa2',a.lzsa,a.lzsa,'existing pinned executable')
    chosen=select(raw,stream,m['blocks'],rows,frames,m['frame_start'],m['frame_end_exclusive'],codec,cache)
    old=json.loads((a.expected/'report.json').read_bytes())
    assert chosen['raw']==(a.expected/'video.raw').read_bytes()
    assert chosen['stream']==(a.expected/'video.stream').read_bytes()
    assert chosen['report']['states_sha256']==old['states_sha256']
    for name in ('decoder_tstates_before','decoder_tstates_after'):
        assert chosen['report'][name]==old[name]
    (a.output/'video.raw').write_bytes(chosen['raw']);(a.output/'video.stream').write_bytes(chosen['stream'])
    write_json(a.output/'report.json',dict(chosen['report'],generic_representation_exact=True,
        archived_candidate_exact=True,metadata_sha256=sha(a.metadata.read_bytes()),codec=codec.identity))
    print(json.dumps({k:chosen['report'][k] for k in ('selected','bytes_before','bytes_after',
        'decoder_tstates_before','decoder_tstates_after','distinct_blocks_recompressed')}))


if __name__=='__main__':main()
