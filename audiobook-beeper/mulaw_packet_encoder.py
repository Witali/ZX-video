"""PC-only waveform search for the compact sixteen-pulse mu-law player."""
import gzip
import time
import numpy as np
from g711_codec import decode_table
from ima_waveform_encoder import WaveformModel,_best_unique
from waveform_kernel import workspace
from mulaw_packet import tables
from mulaw_waveform_encoder import timed_pcm


def encode(pcm,meta,times,width=32,horizon=32,commit=8,regularization=.1,backend='auto',statistics=None):
    n=len(pcm);count=n-128
    words,nxt=tables(meta['model'])
    patterns,wordids=np.unique(words,return_inverse=True);wordids=wordids.reshape(256,32)
    signed=np.unpackbits(patterns.astype('>u2').view('u1')).reshape(-1,16)*2.-1
    # The phase-locked clock is data-independent apart from the documented
    # <=3-T cold transient. New streams still receive a complete fresh trace.
    t=times[:count*16+1]-times[0];holds=np.diff(t).reshape(count,16)
    unique,ids=np.unique(holds,axis=0,return_inverse=True)
    model=WaveformModel();features=[]
    for row in unique:
        a,b,l,r=model.packet(row)
        features.append((a,l,signed@r.T,signed@b.T,row/(3546900/8000)))
    desired=model.reference(pcm.astype(float)/256+128,((t[:-1]+t[1:])/2).reshape(count,16))
    # Reuse float64 Lanczos interpolation with actual sixteen-pulse edges.
    centers=times[:n*16+1:16].astype(float)
    positions=(centers[:-1]+centers[1:])/(2*(3546900/8000))-.5
    prior=np.empty(n);offsets=np.arange(-15,17)
    for start in range(0,n,8192):
        stop=min(start+8192,n);index=np.floor(positions[start:stop,None]).astype(np.int64)+offsets
        distance=positions[start:stop,None]-index;weights=np.sinc(distance)*np.sinc(distance/16)
        values=np.where((index>=0)&(index<n),pcm[np.clip(index,0,n-1)],0.)
        prior[start:stop]=(values*weights).sum(axis=1)/weights.sum(axis=1)
    levels=decode_table('mulaw').astype(float)/32768
    kernel=workspace(width,256,backend);chosen=np.full(n,255,dtype='u1')
    q=16;state=np.zeros(6);started=time.perf_counter()
    for start in range(0,count,commit):
        stop=min(count,start+horizon);qs=np.array([q]);states=state[None].copy();costs=np.zeros(1)
        parents=np.empty((stop-start,width),dtype=np.intp);codes=np.empty((stop-start,width),dtype='u1')
        for sample in range(start,stop):
            a,l,response,endpoint,weights=features[ids[sample]]
            word=wordids[:,qs].T.ravel().astype(np.int64)
            newq=nxt[:,qs].T.ravel().astype(np.int64);parent=np.repeat(np.arange(len(qs)),256)
            base=states@l.T
            terms=((base[parent]+response[word]-desired[sample])**2*weights if kernel is None else
                   kernel.errors(base,response,word,desired[sample],weights))
            score=costs[parent]+np.sum(terms,axis=1)
            score+=regularization*np.tile((levels-prior[sample]/32768)**2,len(qs))
            candidates=np.arange(len(score))
            # Equal next q alone does not imply equal filter history. Merge
            # only identical output words from the same parent and next q.
            key=(parent*len(patterns)+word)*32+newq
            best=(_best_unique(candidates,score,key,width) if kernel is None else kernel.select(candidates,score,key))
            states=(states@a.T)[parent[best]]+endpoint[word[best]]
            qs=newq[best];costs=score[best]
            parents[sample-start,:len(best)]=parent[best];codes[sample-start,:len(best)]=best%256
        path=np.empty(stop-start,dtype='u1');winner=0
        for j in range(stop-start-1,-1,-1):path[j]=codes[j,winner];winner=parents[j,winner]
        for sample,code in zip(range(start,min(start+commit,stop)),path):
            a,_,_,endpoint,_=features[ids[sample]]
            word=wordids[code,q];q=int(nxt[code,q]);state=a@state+endpoint[word];chosen[sample]=code
        if start and start%16384==0:print(dict(packet_encoded_samples=start,total_samples=count),flush=True)
    if statistics is not None:
        statistics.update(width=width,horizon=horizon,commit=commit,regularization=regularization,
            search_seconds=time.perf_counter()-started,backend='native' if kernel else 'numpy',
            clock_patterns=len(features),packet_patterns=len(patterns),z80_tstate_delta=0,
            merge_rule='equal parent, output word and successor; retain different filter histories')
    return chosen.tobytes()
