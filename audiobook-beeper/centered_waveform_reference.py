"""Independent opt-in centered waveform-search reference.

The search below is an explicit Python copy of the unchanged original;
only the64-bin quantizer in candidate evaluation and accepted-prefix replay
changes for bias512. Bias0 delegates directly to the original encoder.
Original ima_waveform_encoder.py and ima_beam.py remain untouched.
"""
import json
import numpy as np
from ima_codec import STEPS,INDEX,decode,require_unclipped
from ima_beam import encode as encode_pcm,code_alphabet
from waveform_kernel import workspace
from ima_waveform_encoder import encode_waveform as _original_encode


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


def encode_waveform_reference(source,desired,features,ids,nxt,width=16,block_size=64,regularization=.1,history_bins=0,
                    allowed_codes=None,level_bounds=None,commit_size=None,backend='auto',statistics=None,pcm_quantization_bias=512):
    """Search a horizon, then accept its prefix and reconsider the future.

    Committing a whole horizon can introduce periodic errors at its end:
    the filter responds after the search has stopped considering the cost.
    A shorter commit keeps future context across those decision boundaries.
    None preserves the historical full-block search for reproducible probes.
    """
    if type(pcm_quantization_bias) is not int or pcm_quantization_bias not in (0,512):
        raise ValueError('pcm_quantization_bias must be builtin integer0 or512')
    if pcm_quantization_bias==0:
        return _original_encode(source,desired,features,ids,nxt,width=width,block_size=block_size,
            regularization=regularization,history_bins=history_bins,allowed_codes=allowed_codes,
            level_bounds=level_bounds,commit_size=commit_size,backend=backend,statistics=statistics)
    if nxt.shape != (64,32) or level_bounds is not None:
        raise ValueError('Centered reference requires64 bins/32 states and no level bounds')
    if statistics is not None:statistics['pcm_quantization_bias']=pcm_quantization_bias
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
            level=np.clip((predicted+32768+pcm_quantization_bias)//1024,0,63)
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
                level=min(63,(pred+32768+pcm_quantization_bias)//1024);word=level*32+q
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
