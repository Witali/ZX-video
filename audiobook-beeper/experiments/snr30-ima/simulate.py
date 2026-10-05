"""Bounded PC-only search: filtered-error IMA and high-precision feedback.

Keep the IMA decoder, number of codes, source duration, 128-kHz decision
rate and listening filter. No Z80 assembly, TRD, or feasibility claim.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from assess import feedback, CPU
from assess_snr import FILTER,ratio
from build_pdm import reconstruct,write_wav
from ima_beam import encode as tail_encode,code_alphabet
from ima_codec import STEPS,INDEX,decode,require_unclipped
from ima_waveform_encoder import WaveformModel,_best_unique
from probe_reconstruction_error import wav8,filtered
from verify_pcm import save

HERE=Path(__file__).resolve().parent


def matrices():
    """Exact linear propagation; 16 midpoint samples integrate each cost.

    The filter acts on (decoded-original). Its state therefore represents
    only reconstruction error. A quadratic form scores all IMA choices
    without running a separate filter for every branch.
    """
    model=WaveformModel();period=CPU/8000
    e,u=model.transition(period)
    pairs=[model.transition(period*(j+.5)/16) for j in range(16)]
    l=np.asarray([model.c@a for a,_ in pairs]);r=np.asarray([model.c@b for _,b in pairs])
    return e,u,l.T@l/16,l.T@r/16,float(r@r/16),l,r


def encode_filtered(source,codes,width=128,horizon=128,commit=64):
    """Overlapping bounded beam; exact IMA predictor/index, no saturation.

    Merging equal predictor/index states is a heuristic because error-filter
    histories can differ. This is a measured candidate, never an optimum.
    """
    codes=code_alphabet(codes);branches=len(codes)
    steps=np.asarray(STEPS)[:,None]
    delta=(steps>>3)+steps*((codes&4)!=0)+(steps>>1)*((codes&2)!=0)+(steps>>2)*((codes&1)!=0)
    delta*=np.where(codes&8,-1,1)
    successors=np.clip(np.arange(89)[:,None]+np.asarray(INDEX)[codes&7],0,88)
    e,u,q,v,w,_,_=matrices();target=(source.astype(float)-128)/128
    chosen=np.empty(len(source),dtype='u1');predictor=index=0;state=np.zeros(6)
    lut={int(c):b for b,c in enumerate(codes)}
    for start in range(0,len(source)-128,commit):
        stop=min(len(source)-128,start+horizon)
        preds=np.array([predictor]);indices=np.array([index]);states=state[None,:];costs=np.zeros(1)
        parents=np.empty((stop-start,width),dtype=np.intp);paths=np.empty((stop-start,width),dtype='u1')
        for j in range(start,stop):
            predicted=(preds[:,None]+delta[indices]).ravel()
            next_indices=successors[indices].ravel();parent=np.repeat(np.arange(len(preds)),branches)
            error=predicted/32768-target[j]
            constant=np.sum((states@q)*states,axis=1);cross=states@v
            score=costs[parent]+constant[parent]+2*cross[parent]*error+w*error**2
            candidates=np.flatnonzero((predicted>=-30720)&(predicted<=30719))
            key=(predicted[candidates]+32768)*89+next_indices[candidates]
            best=_best_unique(candidates,score,key,width)
            parents[j-start,:len(best)]=parent[best];paths[j-start,:len(best)]=codes[best%branches]
            states=(states@e.T)[parent[best]]+error[best,None]*u
            preds,indices,costs=predicted[best],next_indices[best],score[best]
        path=np.empty(stop-start,dtype='u1');winner=0
        for j in range(stop-start-1,-1,-1):
            path[j]=paths[j,winner];winner=parents[j,winner]
        accepted=min(stop,start+commit);chosen[start:accepted]=path[:accepted-start]
        for j in range(start,accepted):
            branch=lut[int(chosen[j])];predictor+=int(delta[index,branch]);index=int(successors[index,branch])
            state=e@state+u*(predictor/32768-target[j])
    tail=tail_encode(np.full(128,128,dtype='u1'),width=32,predictor=predictor,index=index,
                     allowed_codes=codes,predictor_bounds=(-30720,30719))
    values=np.frombuffer(tail,'u1');chosen[-128::2]=values&15;chosen[-127::2]=values>>4
    packed=(chosen[::2]|(chosen[1::2]<<4)).tobytes()
    pcm,indices=decode(packed);assert (pcm[-1],indices[-1])==(0,0)
    require_unclipped(packed)
    return packed


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assessment',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('output must be empty')
    source=wav8(HERE.parent/'ima-3bit-overlap/qualified/source-preview.wav')
    n=len(source);times=np.arange(n*16+1)*CPU/128000
    source_signal=reconstruct(source/256,np.arange(n+1)*CPU/8000)
    source_filtered=filtered(source_signal,a.ffmpeg)
    cut=slice(4410,-4410);rows=[];failures=[]
    report=dict(date='2026-10-05',scope=__doc__,source_pcm_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                samples=n,filter=FILTER,edge_exclusions_seconds=.1,rate_hz=128000,
                assessment_sha256=hashlib.sha256((a.assessment/'report.json').read_bytes()).hexdigest(),
                rows=rows,failures=failures,decoder_unchanged=True,z80_ported=False)
    def score(name,output,gain,**extra):
        ref=source_filtered*gain;actual=filtered(output,a.ffmpeg)
        row=dict(name=name,snr_db=ratio(ref[cut],actual[cut]-ref[cut]),declared_gain=gain,**extra)
        rows.append(row);save(out/'report.json',report);print(json.dumps(row),flush=True)
        return actual
    candidates={}
    for codec,codes in [('ima3',range(0,16,2)),('ima4',None)]:
        old=gzip.decompress((a.assessment/(codec+'-pcm-search.ima.gz')).read_bytes())
        candidates[codec+'-pcm64']=(decode(old)[0].astype(float)+32768)/65536
        begin=time.monotonic();packed=encode_filtered(source,codes)
        (out/(codec+'-filtered128.ima.gz')).write_bytes(gzip.compress(packed,mtime=0))
        pcm,_=decode(packed);levels=(pcm.astype(float)+32768)/65536
        candidates[codec+'-filtered128']=levels
        score(codec+'-filtered128-pcm',reconstruct(levels,np.arange(n+1)*CPU/8000),1.,
              scope='Filtered-error IMA, ideal multilevel DAC; no PDM',encode_seconds=time.monotonic()-begin,
              beam_width=128,horizon=128,commit=64,disk_audio_bytes=n*(3 if codec=='ima3' else 4)//8)
    # Predeclared bounded gain/feedback sweep, keeping exactly 128000 Hz.
    # Reject overload instead of silently clipping the integrators.
    for name,levels in candidates.items():
        held=np.repeat(levels,16)
        for beta,gain in ((.5,1.),(.75,1.),(1.,.5),(1.,.625),(1.,.75),(1.,1.)):
            label=f'{name}-beta{beta:g}-gain{gain:g}'
            try:bits,peak=feedback(held,beta,gain)
            except ValueError as ex:
                failures.append(dict(name=label,reason=str(ex)));save(out/'report.json',report);continue
            actual=score(label,reconstruct(bits,times),gain,
                         scope='Uniform 128-kHz floating-state PC simulation; no Z80/timing claim',
                         beta=beta,state_peak=peak)
            if beta==1:
                write_wav(out/(label+'.wav'),actual)
    pdm=[r for r in rows if 'beta' in r]
    report['best_by_codec']={codec:max((r for r in pdm if r['name'].startswith(codec)),key=lambda r:r['snr_db']) for codec in ('ima3','ima4')}
    report['target_met']=all(r['snr_db']>=30 for r in report['best_by_codec'].values())
    save(out/'report.json',report)


if __name__=='__main__':main()
