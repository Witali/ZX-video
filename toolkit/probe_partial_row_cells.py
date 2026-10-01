"""Measure single-row cell patches on cached windows, not alternative disk sets."""
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
    for key in ('prepared','baseline','lzsa','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    prep=json.loads(a.prepared.read_bytes());frames=[]
    for chunk in prep['chunks']:
        path=a.prepared.parent/chunk['file'];assert sha(path.read_bytes())==chunk['sha256']
        with np.load(path,allow_pickle=False) as saved:frames.extend(saved['five_states'])
    frames=np.stack(frames);codec=ExternalCodec('lzsa2',a.lzsa,a.lzsa,'pinned existing executable')
    cache=a.output/'lzsa';cache.mkdir(exist_ok=True);runs=[]
    for lo,hi in ((0,256),(2560,2816),(4096,4352)):
        stem=f'{lo}-{hi}-refit';base=json.loads((a.baseline/(stem+'.json')).read_bytes())
        base['raw']=gzip.decompress((a.baseline/(stem+'.raw.gz')).read_bytes())
        old=gzip.decompress((a.baseline/(stem+'.stream.gz')).read_bytes())
        assert sha(base['raw'])==base['raw_sha256'] and sha(old)==base['stream_sha256']
        result=encode(base,frames,lo,hi);assert result['proof']['screen_sha256']==base['proof']['screen_sha256']
        coded,blocks=pack_blocks(result['raw'],codec,cache);out=f'{lo}-{hi}'
        for suffix,blob in (('raw',result['raw']),('stream',coded)):
            (a.output/(out+'.'+suffix+'.gz')).write_bytes(gzip.compress(blob,mtime=0))
        write_json(a.output/(out+'.json'),dict(rows=result['rows'],details=result['details'],proof=result['proof'],
            blocks=blocks,raw_sha256=sha(result['raw']),stream_sha256=sha(coded)))
        runs.append(dict(start=lo,end=hi,before_bytes=len(old),after_bytes=len(coded),delta_bytes=len(coded)-len(old),
            partial_cells=sum(d['partial_cells'] for d in result['details']),
            literal_counts=[sum(d['literal_cells_by_changed_rows'][i] for d in result['details']) for i in range(5)],
            raw_bytes_saved=len(base['raw'])-len(result['raw']),all_screens_exact=True))
        print(json.dumps(runs[-1]),flush=True)
        write_json(a.output/'report.json',dict(complete=len(runs)==3,release=False,native_implemented=False,
            native_timing_verified=False,scope=__doc__,runs=runs,pixel_changes=0,ay_changed=False,
            total_before=sum(r['before_bytes'] for r in runs),total_after=sum(r['after_bytes'] for r in runs),
            frames_sha256=sha(frames.tobytes()),source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n'))
                for n in ('partial_row_cells.py','probe_partial_row_cells.py','dynamic_row_dictionary.py')}))


if __name__=='__main__':main()
