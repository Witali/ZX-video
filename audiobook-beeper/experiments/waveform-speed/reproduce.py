"""Time exact search backends and optionally reproduce all three full streams."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import time

os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
import ima_waveform_encoder as encoder
from probe_reconstruction_error import wav8
from test_search import baseline

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def digest(data):return hashlib.sha256(data).hexdigest()


def save(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--full',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    old=baseline()
    started=time.perf_counter()
    meta,_,_,nxt,source,desired,features,ids=encoder.prepare(HERE/'pilot')
    preparation=time.perf_counter()-started
    prior=wav8(HERE/'pilot/compensated-pcm.wav')
    rows=[]
    common=dict(regularization=.03,allowed_codes=np.arange(0,16,2),level_bounds=meta['model']['level_bounds'])
    for backend in ('baseline','numpy','native'):
        n=2048
        values=np.r_[prior[:n],np.full(128,128,dtype='u1')]
        args=(values,desired[:n],features,ids[:n],nxt)
        timings=[]
        for repeat in range(3):
            started=time.perf_counter()
            function=old.encode_waveform if backend=='baseline' else encoder.encode_waveform
            packed=function(*args,width=1024,block_size=256,commit_size=64,**common,
                            **({} if backend=='baseline' else dict(backend=backend)))
            timings.append(time.perf_counter()-started)
            if backend=='baseline' and repeat==0:expected=packed
            assert packed==expected,(backend,repeat)
        row=dict(backend=backend,seconds=timings,median_seconds=float(np.median(timings)),
                 samples=n,packed_sha256=digest(packed),byte_exact=True)
        rows.append(row);save(a.output/'short.json',rows);print(json.dumps(row),flush=True)
    full=[]
    if a.full:
        for number,(width,horizon) in enumerate(((256,128),(512,128),(1024,256)),1):
            reference=HERE.parent/'entertainer-normalized/ima3/attempts'/f'encode-{number}'
            expected=gzip.decompress((reference/'soundtrack.ima.gz').read_bytes())
            started=time.perf_counter()
            packed=encoder.encode_waveform(prior,desired,features,ids,nxt,width=width,
                                            block_size=horizon,commit_size=64,backend='native',**common)
            elapsed=time.perf_counter()-started
            assert packed==expected,f'complete search {number} differs from the released stream'
            (a.output/f'encode-{number}.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
            row=dict(attempt=number,width=width,horizon=horizon,seconds=elapsed,
                     old_complete_cli_seconds=json.loads((reference/'report.json').read_bytes())['elapsed_seconds'],
                     samples=len(source),packed_sha256=digest(packed),byte_exact=True)
            full.append(row);save(a.output/'full.json',full);print(json.dumps(row),flush=True)
    producers={name:digest((ROOT/'audiobook-beeper'/name).read_bytes().replace(b'\r\n',b'\n'))
               for name in ('ima_waveform_encoder.py','waveform_kernel.py','convert_ima3_audio.py')}
    save(a.output/'report.json',dict(complete=True,source_sha256=digest(source.tobytes()),
         preparation_seconds=preparation,short=rows,full=full,producer_sha256_lf=producers,
         native_tstate_delta=0,changed_player=False,
         timing_scope='Short medians time the same encode function; old full times also include CLI preparation/scoring.'))


if __name__=='__main__':main()
