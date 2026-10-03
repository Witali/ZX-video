"""Search existing pulse-code words for lower sensitivity to ULA hold variation.

Only table entries change in this host model. Word candidates use the original
first/second code-pattern pools and feedback states, preserving that layout's
upper memory bound. New content/timing still needs full native/Fuse checks.
"""
import argparse,gzip,json
from pathlib import Path
import numpy as np
from ima_codec import decode
from probe_companded_packets import make_table
from probe_packet_area import context,render_levels
from probe_reconstruction_error import wav8,filtered
from build_pdm import reconstruct,write_wav
from pdm_player import CPU_CLOCK
from assess_snr import ratio


def optimize(targets,model,ordinary,covariance_weight):
    baseline,base_next,mapping,layout=make_table(targets,model)
    reachable={16}
    while True:
        nxt=reachable|set(map(int,base_next[:,sorted(reachable)].ravel()))
        if nxt==reachable:break
        reachable=nxt
    states=sorted(reachable)
    hi=np.unique(baseline[:,states]>>8);lo=np.unique(baseline[:,states]&255)
    pool=((hi[:,None].astype(np.uint16)<<8)|lo[None,:]).ravel()
    bits=np.unpackbits(pool.astype('>u2').view('u1')).reshape(-1,16).astype(float)
    weights=np.asarray(model['holds'])/np.mean(model['holds'])
    normal=ordinary[:-128];normal=normal[normal.max(axis=1)<80]
    residual=normal/normal.mean(axis=1)[:,None]-weights
    covariance=residual.T@residual/len(residual)
    variance=np.sum((bits@covariance)*bits,axis=1)
    response=[];previous=np.zeros(len(pool));area=np.zeros(len(pool))
    for k,w in enumerate(weights):
        previous=area/w+model['beta']*previous+bits[:,k]
        response.append(previous.copy());area+=w*bits[:,k]
    response=np.asarray(response).T;norm=np.sum(response*response,axis=1)
    words=baseline.copy();next_state=base_next.copy();peak=0.;changed=0
    for v,x in enumerate(np.asarray(targets)/128):
        for state in states:
            q0=(state//2-8)/8;recent=(state%2-.5)*model['extent'];q=q0;values=[]
            for w in weights:
                recent=x+q/w+model['beta']*recent;values.append(recent);q+=w*x
            values=np.asarray(values)
            cost=norm-2*response@values+np.dot(values,values)+covariance_weight*variance
            qcode=np.floor((q-area)*8+8.5).astype(int)
            last=values[-1]-response[:,-1]
            successor=qcode*2+(last>=0)
            valid=np.isin(successor,states)&(qcode>=0)&(qcode<=15)
            assert valid.any()
            selected=int(np.argmin(np.where(valid,cost,np.inf)))
            words[v,state]=pool[selected];next_state[v,state]=successor[selected]
            peak=max(peak,float(np.max(abs(values-response[selected]))))
            changed+=int(pool[selected]!=baseline[v,state])
    return words,next_state,mapping,dict(**layout,word_pool=len(pool),changed_reachable_entries=changed,
                                       maximum_forced_recent_error=peak,covariance_weight=covariance_weight)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--palette',choices=('linear','medium'),default='linear')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    meta,t,_,_,_,_,_=context(a.input);n=meta['pcm_samples'];at=(n-3)*16+15;pairs=meta['loop_idle_pairs'];h=np.diff(t)
    ordinary=np.r_[h[:at],h[at+2*pairs:]].reshape(n,16)
    if a.palette=='linear':targets=np.arange(1,128,2)
    else:
        positive=np.r_[np.arange(1,17),np.arange(18,33,2),np.arange(36,61,4)]
        targets=np.r_[64-positive[::-1],64,64,64+positive]
    pcm,_=decode(gzip.decompress((a.input/'soundtrack.ima.gz').read_bytes()))
    pcm8=((pcm.astype(np.int32)+32768)>>8).astype('u1');source=wav8(a.input/'source-preview.wav')
    period=CPU_CLOCK/8000;segments=int(np.ceil(t[-1]/period));edges=np.r_[np.arange(segments)*period,t[-1]]
    levels=np.pad(source/256,(0,max(0,segments-len(source))),constant_values=.5)[:segments]
    ref=filtered(reconstruct(levels,edges),a.ffmpeg)[4410:-4410];rows=[]
    for weight in (0.,4.,16.,64.):
        words,nxt,mapping,info=optimize(targets,meta['model'],ordinary,weight)
        bits,last=render_levels(mapping[pcm8],meta,words,nxt);actual=filtered(reconstruct(bits,t),a.ffmpeg)
        row=dict(palette=a.palette,fixed_clock_snr_db=ratio(ref,actual[4410:-4410]-ref),final_state=last,
                 **info,new_timeline_verified=False,planned_native_tstate_delta=0)
        name=f'weight-{weight:g}';np.savez_compressed(a.output/(name+'.npz'),words=words,next_state=nxt,mapping=mapping,targets=targets)
        write_wav(a.output/(name+'-preview.wav'),actual);rows.append(row);print(json.dumps(row),flush=True)
    (a.output/'report.json').write_text(json.dumps(dict(scope=__doc__,input=str(a.input),rows=rows),indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
