"""Independent state recurrence and full native/Fuse direct-player checks."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
from direct_player import HOLDS
from ima_codec import decode
from probe_feedback_packets import integral_table
from verify_packet import rational_tables,native_check,fuse_check
from verify_pcm import save


def reference(packed,cycles=2,model=None):
    pcm,indices=decode(packed);assert (pcm[-1],indices[-1])==(0,0)
    levels=((pcm.astype(np.int32)+32768)>>8).astype('u1')
    model=model or dict(holds=HOLDS,beta=.5,extent=1.)
    words,nxt=rational_tables(model['holds'],integral_table(64,2,holds=model['holds'],beta=model['beta'],extent=model['extent']),model['beta'],model['extent'])
    state=16;output=np.empty(len(pcm)*cycles+1,dtype='>u2')
    for i in range(len(output)):
        value=int(levels[i%len(pcm)])//4;output[i]=words[value,state];state=int(nxt[value,state])
    return pcm,indices,levels,np.unpackbits(output.view('u1'))[:len(pcm)*cycles*16+1]


def intervals(meta):
    holds=np.tile(HOLDS,meta['pcm_samples']).astype(np.int64);end=0
    for s in meta['sections']:
        for byte in range(256,s['bytes']+1,256):
            holds[(2*(end+byte)-3)*16+14]+=meta['bank_extra_tstates'] if byte==s['bytes'] else 14
        end+=s['bytes']
    return holds


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--fuse',type=Path)
    p.add_argument('--probe',action='store_true');a=p.parse_args();out=a.directory.resolve()
    meta=json.loads((out/'player.json').read_bytes());packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    from functools import partial
    ref=partial(reference,model=meta.get('model'))
    if a.fuse:
        report=fuse_check(a.fuse,out,meta,packed,a.probe,ref,intervals)
        save(out/('probe.json' if a.probe else 'fuse.json'),report)
    else:
        report=native_check((out/'audiobook-preview.trd').read_bytes(),meta,packed,ref,intervals)
        save(out/'native.json',report)
    print(json.dumps(report),flush=True)
