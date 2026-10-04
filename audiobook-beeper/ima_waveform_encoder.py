"""Encode IMA against the filtered, timed PDM waveform on a saved schedule.

All extra computation is offline. This host probe neither changes the Z80
decoder nor proves that a new byte stream retains the pilot's ULA timeline.
The scoring model is an analog approximation to the existing listening filter;
the final host score still uses the unchanged FFmpeg measurement pipeline.
"""
import argparse,gzip,hashlib,json,time
from pathlib import Path
import numpy as np
from ima_codec import STEPS,INDEX,decode,require_unclipped
from ima_beam import encode as encode_pcm,code_alphabet
from probe_packet_area import context
from probe_reconstruction_error import wav8,filtered
from verify_direct import reference
from build_pdm import reconstruct,write_wav
from pdm_player import CPU_CLOCK
from assess_snr import ratio
from waveform_kernel import workspace


class WaveformModel:
    """Two Butterworth low-pass pairs at4500 Hz, then high-pass at70 Hz.

    Each pair uses normalized states y and y'/omega. Piecewise-constant
    input propagation is analytic through a48-term matrix exponential.
    No integration step is fitted to the desired answer.
    """
    def __init__(self):
        low=2*np.pi*4500;high=2*np.pi*70;root=np.sqrt(2)
        a=np.zeros((6,6))
        for start,w in ((0,low),(2,low),(4,high)):
            a[start,start+1]=w;a[start+1,start]=-w;a[start+1,start+1]=-root*w
            if start:a[start+1,start-2]=w
        self.c=np.array([0.,0.,1.,0.,-1.,-root])
        self.steady=np.array([1.,0.,1.,0.,1.,0.])
        power=np.eye(6);self.coefficients=[power.copy()]
        for k in range(1,49):
            power=power@(a/8000)/k;self.coefficients.append(power.copy())
        self.cache={}

    def transition(self,tstates):
        key=float(tstates)
        if key not in self.cache:
            fraction=key*8000/CPU_CLOCK
            assert 0<=fraction<2,'the long silent phase filler is outside the search model'
            e=np.zeros((6,6))
            for coefficient in reversed(self.coefficients):e=e*fraction+coefficient
            self.cache[key]=(e,self.steady-e@self.steady)
        return self.cache[key]

    def packet(self,holds):
        start=np.r_[0,np.cumsum(holds[:-1])];end=start+holds;total=end[-1]
        a,_=self.transition(total);b=np.zeros((6,16));l=np.empty((16,6));r=np.zeros((16,16))
        for j in range(16):
            midpoint=start[j]+holds[j]/2
            l[j]=self.c@self.transition(midpoint)[0]
            r[j,j]=self.c@self.transition(holds[j]/2)[1]
            for k in range(j):r[j,k]=self.c@self.transition(midpoint-end[k])[0]@self.transition(holds[k])[1]
            b[:,j]=self.transition(total-end[j])[0]@self.transition(holds[j])[1]
        # Independent sequential propagation verifies the composed matrices.
        state=np.array([.1,-.2,.3,-.4,.5,-.6]);bits=np.where(np.arange(16)%3,1.,-1.)
        original=state.copy();observed=[]
        for hold,bit in zip(holds,bits):
            eh,uh=self.transition(hold/2);observed.append(self.c@(eh@state+uh*bit))
            e,u=self.transition(hold);state=e@state+u*bit
        assert np.allclose(observed,l@original+r@bits,atol=2e-11,rtol=0)
        assert np.allclose(state,a@original+b@bits,atol=2e-11,rtol=0)
        return a,b,l,r

    def reference(self,source,queries):
        units=np.rint(queries*80).astype(np.int64)
        assert np.max(abs(queries*80-units))<1e-6
        index=units//35469;fraction=units%35469
        values=np.pad((source.astype(float)-128)/128,(0,max(0,int(index.max())+1-len(source))))
        states=np.zeros((len(values)+1,6));e,u=self.transition(CPU_CLOCK/8000)
        for i,x in enumerate(values):states[i+1]=e@states[i]+u*x
        f=np.arange(35469)/35469
        row=np.zeros((35469,6))
        for coefficient in reversed(self.coefficients):row=row*f[:,None]+self.c@coefficient
        # C*steady=0 for the final high-pass section.
        return np.sum(row[fraction]*(states[index]-values[index,None]*self.steady),axis=-1)


def prepare(path):
    meta,t,words,nxt,bits,_,_=context(path);n=meta['pcm_samples'];at=(n-3)*16+15
    h=np.diff(t);ordinary=np.r_[h[:at],h[at+meta['loop_idle_pairs']*2:]].reshape(n,16)
    # The final128 silent samples use the existing settling encoder, not the
    # optimization model's bounded-duration packet propagator.
    count=n-128;holds=ordinary[:count]
    unique,ids=np.unique(holds,axis=0,return_inverse=True)
    model=WaveformModel();features=[]
    signed=bits.reshape(-1,16).astype(float)*2-1
    for row in unique:
        a,b,l,r=model.packet(row)
        features.append((a,l,signed@r.T,signed@b.T,row/(CPU_CLOCK/8000)))
    queries=((t[:count*16]+t[1:count*16+1])/2).reshape(count,16)
    source=wav8(path/'source-preview.wav');desired=model.reference(source,queries)
    return meta,t,words,nxt,source,desired,features,ids


def _best_unique(candidates,score,key,width):
    """Merge equal decoder states, preserving the old (cost, candidate) ties.

    Sorting only the integer key costs less than lexsorting all candidates
    by key, score and ID. Group reductions select exactly the same winner.
    Partition the winners before sorting the beam; include every boundary
    tie so that argpartition's arbitrary tie order cannot change the stream.
    """
    order=np.argsort(key,kind='stable')
    ordered=candidates[order];keys=key[order];scores=score[ordered]
    starts=np.r_[0,np.flatnonzero(keys[1:]!=keys[:-1])+1]
    minimum=np.minimum.reduceat(scores,starts)
    tied=scores==np.repeat(minimum,np.diff(np.r_[starts,len(ordered)]))
    winners=np.minimum.reduceat(np.where(tied,ordered,np.iinfo(np.intp).max),starts)
    if len(winners)>width:
        threshold=np.partition(minimum,width-1)[width-1]
        winners=winners[minimum<=threshold]
    return winners[np.lexsort((winners,score[winners]))[:width]]


def encode_waveform(source,desired,features,ids,nxt,width=16,block_size=64,regularization=.1,history_bins=0,
                    allowed_codes=None,level_bounds=None,commit_size=None,backend='auto',statistics=None):
    """Search a horizon, then accept its prefix and reconsider the future.

    Committing a whole horizon can introduce periodic errors at its end:
    the filter responds after the search has stopped considering the cost.
    A shorter commit keeps future context across those decision boundaries.
    None preserves the historical full-block search for reproducible probes.
    """
    commit_size=block_size if commit_size is None else commit_size
    if not 1<=commit_size<=block_size:raise ValueError('commit size must be within the lookahead block')
    codes=code_alphabet(allowed_codes);branches=len(codes)
    if width<1:raise ValueError('beam width must be positive')
    kernel=workspace(width,branches,backend)
    if statistics is not None:statistics['backend']='native' if kernel is not None else 'numpy'
    branch_for_code={int(code):branch for branch,code in enumerate(codes)}
    steps=np.asarray(STEPS,dtype=np.int64)[:,None]
    delta=(steps>>3)+steps*((codes&4)!=0)+(steps>>1)*((codes&2)!=0)+(steps>>2)*((codes&1)!=0)
    delta*=np.where(codes&8,-1,1)
    successor=np.clip(np.arange(89)[:,None]+np.asarray(INDEX)[codes&7],0,88)
    chosen=np.empty(len(source),dtype='u1');pred=index=0;q=16;filter_state=np.zeros(6)
    for start in range(0,len(ids),commit_size):
        stop=min(len(ids),start+block_size);preds=np.array([pred]);indices=np.array([index]);qs=np.array([q])
        states=filter_state[None,:].copy();costs=np.zeros(1)
        # Store ancestry once. Copying every complete path at every sample
        # adds quadratic horizon traffic; only the winning path is needed.
        parents=np.empty((stop-start,width),dtype=np.intp)
        path_codes=np.empty((stop-start,width),dtype='u1')
        for sample in range(start,stop):
            a,l,response,endpoint,weights=features[ids[sample]]
            predicted=(preds[:,None]+delta[indices]).ravel();next_indices=successor[indices].ravel()
            valid=(predicted>=-32768)&(predicted<=32767);parent=np.repeat(np.arange(len(preds)),branches)
            level=np.clip((predicted+32768)//(65536//nxt.shape[0]),0,nxt.shape[0]-1)
            if level_bounds is not None:
                valid &= (level>=level_bounds[0]) & (level<=level_bounds[1])
            word_index=level*32+qs[parent]
            # Broadcast the shared parent response instead of materializing
            # it once per branch. Reuse the scratch array for each elementwise
            # operation, retaining the original float64 evaluation order.
            if kernel is None:
                error=((states@l.T)[:,None,:]+response[word_index.reshape(-1,branches)]).reshape(-1,16)
                error-=desired[sample]
                np.multiply(error,error,out=error)
                error*=weights
            else:
                error=kernel.errors(states@l.T,response,word_index,desired[sample],weights)
            score=costs[parent]+np.sum(error,axis=1)
            # Keep the control signal near the already timed source. Without
            # this term a short beam can chase the filter's delayed response
            # into large DC excursions and clipping-range control values.
            target=(source[sample]-128.)/128
            score+=regularization*(predicted/32768-target)**2
            new_q=nxt[level,qs[parent]]
            candidates=np.flatnonzero(valid)
            key=((predicted[candidates]+32768)*89+next_indices[candidates])*32+new_q[candidates]
            if history_bins:
                next_filters=(states@a.T)[parent]+endpoint[word_index]
                columns=np.column_stack((key,np.rint(next_filters[candidates]*history_bins).astype(np.int64)))
                order=np.lexsort((candidates,score[candidates],*columns.T[::-1]))
                ordered=candidates[order]
                ordered=ordered[np.r_[True,np.any(columns[order][1:]!=columns[order][:-1],axis=1)]]
                best=ordered[np.lexsort((ordered,score[ordered]))[:width]]
                next_states=next_filters[best]
            else:
                best=(_best_unique(candidates,score,key,width) if kernel is None else
                      kernel.select(candidates,score,key))
                # Discarded branches do not need propagated filter states.
                next_states=(states@a.T)[parent[best]]+endpoint[word_index[best]]
            parents[sample-start,:len(best)]=parent[best]
            path_codes[sample-start,:len(best)]=codes[best%branches]
            states=next_states
            preds,indices,qs,costs=predicted[best],next_indices[best],new_q[best],score[best]
        path=np.empty(stop-start,dtype='u1');winner=0
        for position in range(stop-start-1,-1,-1):
            path[position]=path_codes[position,winner];winner=parents[position,winner]
        committed=min(stop,start+commit_size)
        chosen[start:committed]=path[:committed-start]
        if committed==stop:
            pred,index,q=int(preds[0]),int(indices[0]),int(qs[0]);filter_state=states[0]
        else:
            # The best lookahead path is known, but its final state belongs
            # to uncommitted future samples. Replay only the accepted prefix
            # to carry the exact IMA, PDM and analog-filter state forward.
            for sample,code in enumerate(chosen[start:committed],start):
                branch=branch_for_code[int(code)];pred+=int(delta[index,branch]);index=int(successor[index,branch])
                level=(pred+32768)//(65536//nxt.shape[0]);word=level*32+q
                aa,_,_,endpoint,_=features[ids[sample]]
                filter_state=aa@filter_state+endpoint[word];q=int(nxt[level,q])
        if committed%16384==0:print(json.dumps(dict(encoded_samples=committed,total_samples=len(source))),flush=True)
    bounds=((-32768,32767) if level_bounds is None else
            (level_bounds[0]*(65536//nxt.shape[0])-32768,
             (level_bounds[1]+1)*(65536//nxt.shape[0])-32769))
    tail=encode_pcm(np.full(128,128,dtype='u1'),width=32,predictor=pred,index=index,allowed_codes=codes,predictor_bounds=bounds)
    tbytes=np.frombuffer(tail,'u1');chosen[-128::2]=tbytes&15;chosen[-127::2]=tbytes>>4
    packed=bytes((chosen[::2]|(chosen[1::2]<<4)).tolist())
    pcm,indices=decode(packed);assert (pcm[-1],indices[-1])==(0,0)
    require_unclipped(packed)
    return packed


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--width',type=int,default=16)
    p.add_argument('--block-size',type=int,choices=(64,128,256),default=64)
    p.add_argument('--commit-size',type=int,help='Commit only this prefix, retaining future samples as lookahead')
    p.add_argument('--regularization',type=float,default=.1)
    p.add_argument('--prior',choices=('compensated','uniform'),default='compensated')
    p.add_argument('--history-bins',type=int,default=0)
    p.add_argument('--backend',choices=('auto','numpy','native'),default='auto',
                   help='optional locally compiled exact kernels; auto retains a NumPy fallback')
    p.add_argument('--ima3',action='store_true',help='Restrict every nibble, including the guard, to the exact IMA3 subset')
    a=p.parse_args()
    if a.commit_size is not None and not 1<=a.commit_size<=a.block_size:
        p.error('--commit-size must be within --block-size')
    a.output.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();meta,t,words,nxt,source,desired,features,ids=prepare(a.input)
    baseline=gzip.decompress((a.input/'soundtrack.ima.gz').read_bytes());pcm,_=decode(baseline)
    state=np.zeros(6);q=16;noise=signal=0.
    for i in range(len(ids)):
        aa,ll,rr,bb,w=features[ids[i]];v=(int(pcm[i])+32768)//(65536//nxt.shape[0]);k=v*32+q
        observed=ll@state+rr[k]
        if 800<=i<len(source)-800:
            noise+=float(np.sum(w*(observed-desired[i])**2));signal+=float(np.sum(w*desired[i]**2))
        state=aa@state+bb[k];q=int(nxt[v,q])
    baseline_model_snr=10*np.log10(signal/noise)
    print(json.dumps(dict(model_prepared=True,unique_packet_shapes=len(features),baseline_model_snr_db=baseline_model_snr)),flush=True)
    prior=wav8(a.input/'compensated-pcm.wav') if a.prior=='compensated' else source
    codes=np.arange(0,16,2) if a.ima3 else None
    search_stats={};search_started=time.monotonic()
    packed=encode_waveform(prior,desired,features,ids,nxt,a.width,regularization=a.regularization,
                           block_size=a.block_size,
                           history_bins=a.history_bins,allowed_codes=codes,
                           level_bounds=meta['model'].get('level_bounds'),commit_size=a.commit_size,
                           backend=a.backend,statistics=search_stats)
    search_seconds=time.monotonic()-search_started
    if a.ima3:
        assert not np.any(np.frombuffer(packed,'u1')&0x11)
    (a.output/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
    _,_,_,outbits=reference(packed,cycles=1,model=meta['model'],idle_pairs=meta['loop_idle_pairs'])
    actual=filtered(reconstruct(outbits[:len(t)-1],t),a.ffmpeg)
    period=CPU_CLOCK/8000;segments=int(np.ceil(t[-1]/period));edges=np.r_[np.arange(segments)*period,t[-1]]
    values=np.pad(source/256,(0,max(0,segments-len(source))),constant_values=.5)[:segments]
    original=filtered(reconstruct(values,edges),a.ffmpeg);ref=original[4410:-4410]
    snr=ratio(ref,actual[4410:-4410]-ref)
    write_wav(a.output/'waveform-preview.wav',actual)
    report=dict(scope=__doc__,input=str(a.input),samples=len(source),beam_width=a.width,
                block_size=a.block_size,
                commit_size=a.commit_size or a.block_size,
                allowed_ima_nibbles=code_alphabet(codes).tolist(),ima3_subset=a.ima3,
                source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                packed_sha256=hashlib.sha256(packed).hexdigest(),
                merge_rule=('Retain discrete decoder state plus quantized filter history' if a.history_bins else
                            'Heuristic: retain lowest-cost filter history per discrete predictor/index/PDM state'),
                history_bins=a.history_bins,
                search_backend=search_stats['backend'],search_seconds=search_seconds,
                baseline_model_snr_db=float(baseline_model_snr),host_fixed_clock_snr_db=snr,
                control_prior=a.prior,control_regularization=a.regularization,
                elapsed_seconds=time.monotonic()-started,ordinary_native_tstate_delta=0,new_timeline_verified=False,
                saturation_guard=require_unclipped(packed),model='Analog six-state filter, analytic pulse propagation, midpoint quadrature')
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
