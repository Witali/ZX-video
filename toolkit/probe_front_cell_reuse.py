"""Measure front-screen reuse on bounded windows; native CB44 is not enabled."""
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
from attribute_delta_stream import encode as attribute_delta
from probe_adaptive_block_codecs import ExternalCodec


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','lzsa','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    prepared=json.loads(a.prepared.read_bytes());frames=[]
    for chunk in prepared['chunks']:
        path=a.prepared.parent/chunk['file'];assert sha(path.read_bytes())==chunk['sha256']
        with np.load(path,allow_pickle=False) as saved:frames.extend(saved['five_states'])
    frames=np.stack(frames);assert len(frames)==prepared['frames']
    codec=ExternalCodec('lzsa2',a.lzsa,a.lzsa,'existing repository executable')
    cache=a.output/'lzsa';cache.mkdir(exist_ok=True);runs=[]
    for lo,hi in ((0,256),(2560,2816),(4096,4352)):
        base=representation(frames,lo,hi);variants={}
        for name,neighbours in (('baseline',None),('same',False),('neighbour',True),('refit',False),('delta',False)):
            chosen=representation(frames,lo,hi,book_front_reuse=True) if name in ('refit','delta') else base
            value=base if neighbours is None else encode(chosen,frames,lo,hi,neighbours=neighbours)
            if name=='delta':value=attribute_delta(value,frames,lo,hi)
            packed,blocks=pack_blocks(value['raw'],codec,cache);stem=f'{lo}-{hi}-{name}'
            for suffix,data in (('raw',value['raw']),('stream',packed)):
                (a.output/(stem+'.'+suffix+'.gz')).write_bytes(gzip.compress(data,mtime=0))
            proof=value.get('proof',value.get('dynamic_proof'))
            assert proof['screen_sha256']==base['screen_sha256']
            write_json(a.output/(stem+'.json'),dict(rows=value['rows'],details=value['details'],blocks=blocks,proof=proof,
                raw_sha256=sha(value['raw']),stream_sha256=sha(packed)))
            variants[name]=dict(bytes=len(packed),raw_bytes=len(value['raw']),
                same_cells=sum(d.get('front_same_cells',0) for d in value['details']),
                moved_cells=sum(d.get('front_moved_cells',0) for d in value['details']))
        runs.append(dict(start=lo,end=hi,variants=variants));print(json.dumps(runs[-1]),flush=True)
    report=dict(complete=True,release=False,native_implemented=False,native_timing_verified=False,
        scope=__doc__,prepared_sha256=sha(a.prepared.read_bytes()),frames_sha256=sha(frames.tobytes()),
        pixel_changes=0,ay_changed=False,runs=runs,
        totals={name:sum(run['variants'][name]['bytes'] for run in runs) for name in variants},
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('dynamic_row_dictionary.py','front_cell_reuse.py','attribute_delta_stream.py','probe_front_cell_reuse.py')})
    write_json(a.output/'report.json',report);print(json.dumps(report['totals']))


if __name__=='__main__':main()
