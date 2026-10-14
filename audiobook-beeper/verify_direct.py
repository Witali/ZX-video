"""Independent state recurrence and full native/Fuse direct-player checks."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
from direct_player import HOLDS
from ima_codec import decode
from probe_feedback_packets import integral_table
from verify_packet import rational_tables,native_check,fuse_check
from verify_pcm import save


def independent_neutral_packet(model):
    """Validate the literal using counted holds, independently of its helper."""
    present='neutral_packet_word' in model
    if not present:
        if 'neutral_packet_successor' in model:
            raise ValueError('neutral packet successor requires a literal word')
        return None
    word=model['neutral_packet_word'];successor=model.get('neutral_packet_successor')
    if type(word) is not int or not 0<=word<=65535:
        raise ValueError('neutral packet word must be a literal integer within0..65535')
    if type(successor) is not int or successor!=16:
        raise ValueError('neutral packet successor must be integer16')
    holds=HOLDS.copy();holds[7]+=26
    try:specified_holds=list(model.get('holds',()));clip=tuple(model.get('q_clip',(0,15)))
    except TypeError:raise ValueError('neutral packet timing and q_clip must be sequences') from None
    bins=model.get('pcm_bins',64)
    if (specified_holds!=holds or model.get('pcm_quantization_bias')!=512 or
            type(bins) is not int or bins!=64 or model.get('family','integral')!='integral' or
            clip!=(0,15) or any(type(value) is not int for value in clip)):
        raise ValueError('neutral packet requires the centered64-bin Pentagon duration_zero integral model')
    for key,default,wanted in (('beta',.5,.5),('extent',1.,1),('pcm_origin',.5,0)):
        value=model.get(key,default)
        if type(value) not in (int,float) or value!=wanted:
            raise ValueError('neutral packet requires zero origin, full extent and beta0.5')
    on=sum(hold for slot,hold in enumerate(holds) if word&(1<<(15-slot)))
    if on not in (224,225):
        raise ValueError('neutral packet must have224 or225 on-T within the449-T ordinary packet')
    return word,successor


def reference(packed,cycles=2,model=None,idle_pairs=0):
    model=model or dict(holds=HOLDS,beta=.5,extent=1.)
    bins=model.get('pcm_bins',64)
    bias=model.get('pcm_quantization_bias',0)
    if type(bias) is not int or bias not in (0,512):
        raise ValueError('pcm_quantization_bias must be integer0 or512 (PCM16 units)')
    if bias and (bins!=64 or model.get('family') not in (None,'integral')):
        raise ValueError('PCM quantization bias requires the64-bin integral PDM model')
    neutral=independent_neutral_packet(model)
    pcm,indices=decode(packed);assert (pcm[-1],indices[-1])==(0,0)
    # Keep the returned PCM8 levels unchanged for existing callers. Derive the
    # optional centered packet index independently from full signed PCM16.
    levels=((pcm.astype(np.int32)+32768)>>8).astype('u1')
    if model.get('family')=='sigma_delta2':
        from sigma_delta2 import independent_tables
        words,nxt=independent_tables(model)
    else:
        clip=tuple(model.get('q_clip',(0,15)))
        origin=model.get('pcm_origin',.5)
        words,nxt=rational_tables(model['holds'],integral_table(bins,2,holds=model['holds'],beta=model['beta'],extent=model['extent'],q_clip=clip,pcm_origin=origin),model['beta'],model['extent'],clip,pcm_origin=origin)
    if neutral is not None:
        # Do not call the primary table helper: override the independently
        # generated row for every feedback state using only the two literals.
        words=words.copy();nxt=nxt.copy();words[32,:]=neutral[0];nxt[32,:]=neutral[1]
    state=16;output=np.empty(len(pcm)*cycles+1,dtype='>u2')
    for i in range(len(output)):
        if model.get('reset_feedback_in_guard') and i%len(pcm)==len(pcm)-1:
            state=16
        value=(min(63,(int(pcm[i%len(pcm)])+32768+bias)//1024) if bias
               else int(levels[i%len(pcm)])*bins//256)
        output[i]=words[value,state];state=int(nxt[value,state])
    bits=np.unpackbits(output.view('u1'))[:len(pcm)*cycles*16+1]
    if idle_pairs:
        position=(len(pcm)-3)*16+15;count=len(pcm)*16
        bits=np.concatenate([part for i in range(cycles) for part in
            (bits[i*count:i*count+position],np.tile(np.array([1,0],dtype='u1'),idle_pairs),bits[i*count+position:(i+1)*count])]+[bits[-1:]])
    return pcm,indices,levels,bits


def intervals(meta):
    if meta.get('packed_ima3_direct'):
        from ima3_direct_player import intervals as packed_intervals
        return packed_intervals(meta)
    holds=np.tile(HOLDS,meta['pcm_samples']).astype(np.int64);end=0
    if meta.get('extended_ram'):
        from ram_cache import timing_extra
        holds[7::16]+=timing_extra(meta,meta.get('ram_profile','128'))
    for s in meta['sections']:
        for byte in range(256,s['bytes']+1,256):
            holds[(2*(end+byte)-3)*16+14]+=meta['bank_extra_tstates'] if byte==s['bytes'] else meta['page_extra_tstates']
        end+=s['bytes']
    pairs=meta.get('loop_idle_pairs',0)
    if pairs:
        k=(meta['pcm_samples']-3)*16+14
        idle=[]
        for j in range(pairs):
            idle.extend([26,33 if (j+1)%255==0 and j+1<pairs else 26])
        idle[-1]=34+meta['loop_idle_pad_tstates']
        holds=np.r_[holds[:k],holds[k]-1,idle,holds[k+1:]]
    return holds


def expand_samples(meta,source):
    values=np.repeat(source,16)
    pairs=meta.get('loop_idle_pairs',0)
    if pairs:
        at=(len(source)-3)*16+15
        values=np.r_[values[:at],np.full(pairs*2,128),values[at:]]
    return values


def sample_positions(meta):
    positions=np.arange(meta['pcm_samples']+1,dtype=np.int64)*16
    pairs=meta.get('loop_idle_pairs',0)
    if pairs:positions[-3:]+=pairs*2
    return positions


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--fuse',type=Path)
    p.add_argument('--probe',action='store_true');a=p.parse_args();out=a.directory.resolve()
    meta=json.loads((out/'player.json').read_bytes());packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    from functools import partial
    ref=partial(reference,model=meta.get('model'),idle_pairs=meta.get('loop_idle_pairs',0))
    if a.fuse:
        report=fuse_check(a.fuse,out,meta,packed,a.probe,ref,intervals)
        save(out/('probe.json' if a.probe else 'fuse.json'),report)
    else:
        report=native_check((out/'audiobook-preview.trd').read_bytes(),meta,packed,ref,intervals)
        save(out/'native.json',report)
    print(json.dumps(report),flush=True)
