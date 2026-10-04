"""Host-only pulse-area steering on a saved full Fuse timeline.

The search chooses six-bit control levels without the IMA restriction. This
greedy result is not an optimal bound, executable disk or timing proof.
"""
import argparse,gzip,json
from pathlib import Path
import numpy as np
from build_pdm import reconstruct,write_wav
from pdm_player import CPU_CLOCK
from probe_feedback_packets import integral_table
from probe_reconstruction_error import wav8,filtered
from verify_direct import sample_positions
from assess_snr import ratio


def context(path):
    meta=json.loads((path/'player.json').read_bytes());n=meta['pcm_samples'];count=meta['outputs_per_cycle']
    t=np.frombuffer(gzip.decompress((path/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:count+1]
    t-=t[0];holds=np.diff(t);at=(n-3)*16+15;pairs=meta['loop_idle_pairs']
    ordinary=np.r_[holds[:at],holds[at+pairs*2:]].reshape(n,16) if pairs else holds.reshape(n,16)
    unique,ids=np.unique(ordinary,axis=0,return_inverse=True)
    model=meta['model'];bins=model.get('pcm_bins',64)
    words,next_state,_=integral_table(bins,2,holds=model['holds'],beta=model['beta'],extent=model['extent'],q_clip=tuple(model.get('q_clip',(0,15))))
    bits=np.unpackbits(words.astype('>u2').view('u1'),axis=1).reshape(bins,32,16)
    means=(unique@bits.reshape(-1,16).T/unique.sum(axis=1)[:,None]).reshape(len(unique),bins,32)
    return meta,t,words,next_state,bits,means,ids


def render_levels(levels,meta,words,next_state):
    q=16;packets=[]
    for v in levels:
        packets.append(words[v,q]);q=int(next_state[v,q])
    bits=np.unpackbits(np.asarray(packets,dtype='>u2').view('u1'))
    at=(len(levels)-3)*16+15;pairs=meta['loop_idle_pairs']
    if pairs:bits=np.r_[bits[:at],np.tile([1,0],pairs),bits[at:]]
    return bits,q


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    meta,t,words,nxt,_,means,ids=context(a.input)
    source=wav8(a.input/'source-preview.wav');target=wav8(a.input/'compensated-pcm.wav')/256
    period=CPU_CLOCK/8000;segments=int(np.ceil(t[-1]/period));edges=np.r_[np.arange(segments)*period,t[-1]]
    levels=np.pad(source/256,(0,max(0,segments-len(source))),constant_values=.5)[:segments]
    original=filtered(reconstruct(levels,edges),a.ffmpeg);ref=original[4410:-4410];rows=[]
    for gamma in (0.,.5,1.):
        chosen=np.empty(len(source),dtype='u1');q=16;error=peak=0.
        for i,x in enumerate(target):
            desired=x+gamma*error
            costs=(means[ids[i],:,q]-desired)**2
            v=int(np.argmin(costs)) if i<len(source)-128 else 32
            error=desired-means[ids[i],v,q];peak=max(peak,abs(error))
            chosen[i]=v;q=int(nxt[v,q])
        bits,end=render_levels(chosen,meta,words,nxt)
        actual=filtered(reconstruct(bits,t),a.ffmpeg)
        row=dict(gamma=gamma,fixed_clock_snr_db=ratio(ref,actual[4410:-4410]-ref),peak_error=peak,
                 final_feedback_state=end,unique_measured_hold_vectors=len(means),samples=len(source),
                 ima_constraint_applied=False,new_timeline_verified=False)
        name=f'area-{gamma:g}';(a.output/(name+'.levels.gz')).write_bytes(gzip.compress(chosen.tobytes(),mtime=0))
        write_wav(a.output/(name+'-preview.wav'),actual);rows.append(row);print(json.dumps(row),flush=True)
    (a.output/'report.json').write_text(json.dumps(dict(scope=__doc__,input=str(a.input),rows=rows),indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
