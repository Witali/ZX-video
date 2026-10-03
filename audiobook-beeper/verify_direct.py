"""Independent state recurrence and full native/Fuse direct-player checks."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
from direct_player import HOLDS
from ima_codec import decode
from probe_feedback_packets import integral_table
from verify_packet import rational_tables,native_check,fuse_check
from verify_pcm import save


def reference(packed,cycles=2,model=None,idle_pairs=0):
    pcm,indices=decode(packed);assert (pcm[-1],indices[-1])==(0,0)
    levels=((pcm.astype(np.int32)+32768)>>8).astype('u1')
    model=model or dict(holds=HOLDS,beta=.5,extent=1.)
    words,nxt=rational_tables(model['holds'],integral_table(64,2,holds=model['holds'],beta=model['beta'],extent=model['extent']),model['beta'],model['extent'])
    state=16;output=np.empty(len(pcm)*cycles+1,dtype='>u2')
    for i in range(len(output)):
        value=int(levels[i%len(pcm)])//4;output[i]=words[value,state];state=int(nxt[value,state])
    bits=np.unpackbits(output.view('u1'))[:len(pcm)*cycles*16+1]
    if idle_pairs:
        position=(len(pcm)-3)*16+15;count=len(pcm)*16
        bits=np.concatenate([part for i in range(cycles) for part in
            (bits[i*count:i*count+position],np.tile(np.array([1,0],dtype='u1'),idle_pairs),bits[i*count+position:(i+1)*count])]+[bits[-1:]])
    return pcm,indices,levels,bits


def intervals(meta):
    holds=np.tile(HOLDS,meta['pcm_samples']).astype(np.int64);end=0
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
