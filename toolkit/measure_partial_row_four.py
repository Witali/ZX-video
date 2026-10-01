"""Recode the one selected cached partition after bounded exact CB46 proofs."""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from convert_cb41 import pack_blocks
from convert_video import write_json
from partial_row_cells import encode
from probe_adaptive_block_codecs import ExternalCodec


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('states','baseline','lzsa','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    with np.load(a.states,allow_pickle=False) as saved:frames=saved['states']
    source=json.loads((a.baseline/'report.json').read_bytes())
    assert source['complete'] and source['frames_sha256']==sha(frames.tobytes())
    volumes=json.loads((a.baseline/'volumes.json').read_bytes())
    codec=ExternalCodec('lzsa2',a.lzsa,a.lzsa,'pinned existing executable')
    cache=a.output/'lzsa';cache.mkdir(exist_ok=True);runs=[]
    for i,v in enumerate(volumes,1):
        stem=f'part{i:02}';base=json.loads((a.baseline/(stem+'.json')).read_bytes())
        base['raw']=gzip.decompress((a.baseline/(stem+'.raw.gz')).read_bytes())
        assert sha(base['raw'])==base['raw_sha256']
        result=encode(base,frames,v['start'],v['end'])
        assert result['proof']['screen_sha256']==base['proof']['screen_sha256']
        coded,blocks=pack_blocks(result['raw'],codec,cache)
        for suffix,blob in (('raw',result['raw']),('stream',coded)):
            (a.output/(stem+'.'+suffix+'.gz')).write_bytes(gzip.compress(blob,mtime=0))
        write_json(a.output/(stem+'.json'),dict(rows=result['rows'],proof=result['proof'],details=result['details'],
            blocks=blocks,raw_sha256=sha(result['raw']),stream_sha256=sha(coded)))
        runs.append(dict(start=v['start'],end=v['end'],before_video_bytes=v['video_bytes'],video_bytes=len(coded),
            delta_bytes=len(coded)-v['video_bytes'],video_sectors=(len(coded)+255)//256,raw_bytes=len(result['raw']),
            partial_cells=sum(d['partial_cells'] for d in result['details']),host_screens_exact=True,
            original_audio=v['original_audio']))
        write_json(a.output/'volumes.json',runs)
        write_json(a.output/'report.json',dict(complete=len(runs)==4,release=False,scope=__doc__,
            frames_sha256=sha(frames.tobytes()),baseline_report_sha256=sha((a.baseline/'report.json').read_bytes()),
            pixel_changes=0,ay_changed=False,whole_movie_timing_verified=False,volumes=runs,
            video_sectors=sum(r['video_sectors'] for r in runs),candidate_partitions_encoded=1,
            boundaries=source['boundaries'],source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n'))
                for n in ('partial_row_cells.py','dynamic_row_dictionary.py','measure_partial_row_four.py')}))
        print(json.dumps({k:runs[-1][k] for k in ('start','end','video_bytes','delta_bytes','video_sectors','partial_cells')}),flush=True)


if __name__=='__main__':main()
