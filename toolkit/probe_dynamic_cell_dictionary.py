"""Bounded lossless CB43 size comparison, including every cell replacement byte.

CB43 is host-only. No native decoder, update timing or full-film claim.
The cell renderer's ordinary frame body is unchanged; control records differ.
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
    for start,end in ((0,256),(2560,2816),(4096,4352)):
        variants={}
        for name,window in (('static',None),('dynamic32',32),('dynamic64',64)):
            result=representation(frames,start,end,cell_window=window)
            packed,blocks=pack_blocks(result['raw'],codec,cache)
            stem=f'{start}-{end}-{name}'
            for suffix,data in (('raw',result['raw']),('stream',packed)):
                (a.output/(stem+'.'+suffix+'.gz')).write_bytes(gzip.compress(data,mtime=0))
            write_json(a.output/(stem+'.json'),dict(rows=result['rows'],frames=result['details'],blocks=blocks,
                proof=result['dynamic_proof'],raw_sha256=sha(result['raw']),stream_sha256=sha(packed)))
            variants[name]=dict(bytes=len(packed),raw_bytes=len(result['raw']),row_updates=result['row_updates'],
                cell_updates=result['cell_updates'],changed_cells=sum(f['changed_cells'] for f in result['details']),
                book_cells=sum(f['book_cells'] for f in result['details']),screens_exact=True,
                replacement_bytes=sum(f['row_update_bytes']+f.get('cell_update_bytes',0) for f in result['details']))
            if window is None:reference=result['screen_sha256']
            else:assert result['screen_sha256']==reference
        runs.append(dict(start=start,end=end,variants=variants))
        print(json.dumps(runs[-1]),flush=True)
    report=dict(complete=True,release=False,native_implemented=False,native_timing_verified=False,
        scope=__doc__,prepared_sha256=sha(a.prepared.read_bytes()),frames_sha256=sha(frames.tobytes()),
        pixel_changes=0,ay_changed=False,window_frames=256,runs=runs,
        totals={name:sum(run['variants'][name]['bytes'] for run in runs) for name in variants},
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('dynamic_cell_dictionary.py','dynamic_row_dictionary.py','probe_dynamic_cell_dictionary.py')})
    write_json(a.output/'report.json',report);print(json.dumps(report['totals']))


if __name__=='__main__':main()
