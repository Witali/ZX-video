"""Check whether a tiny silent suffix can close the PDM feedback state."""
import gzip
import json
from pathlib import Path
import numpy as np
from ima_codec import decode, transition
from probe_feedback_packets import integral_table
from probe import CASES

HERE=Path(__file__).resolve().parent


def close(packed, nxt, count=16):
    pcm, indices=decode(packed); bins=len(nxt); q=16
    for value in pcm[:-count]:q=int(nxt[(int(value)+32768)//(65536//bins),q])
    seed=(int(pcm[-count-1]),int(indices[-count-1]),q)
    assert seed[1]==0 and abs(seed[0])<32, seed
    paths={seed:(0,())}
    for _ in range(count):
        following={}
        for (p,index,state),(cost,path) in paths.items():
            for code in (0,2,8,10):
                value,new_index=transition(p,index,code)
                if abs(value)>32:continue
                new_q=int(nxt[(value+32768)//(65536//bins),state])
                key=(value,new_index,new_q); candidate=(cost+value*value,path+(code,))
                if key not in following or candidate<following[key]:following[key]=candidate
        paths=following
    target=paths.get((0,0,16))
    if target:
        codes=np.asarray(target[1],dtype='u1')
        result=packed[:-count//2]+bytes((codes[::2]|(codes[1::2]<<4)).tolist())
        return result,dict(seed=seed,cost=target[0],codes=target[1])
    return None,dict(seed=seed,reachable_states=sorted({s for p,i,s in paths if p==i==0}))


def main():
    rows={}
    for name,(folder,_) in CASES.items():
        root=HERE.parent/folder; meta=json.loads((root/'player.json').read_bytes()); model=meta['model']
        _,nxt,_=integral_table(model.get('pcm_bins',64),2,holds=model['holds'],beta=model['beta'],
                              extent=model['extent'],q_clip=tuple(model.get('q_clip',(0,15))))
        packed=gzip.decompress((root/'soundtrack.ima.gz').read_bytes())
        pcm,_=decode(packed); state=16
        for value in pcm:state=int(nxt[(int(value)+32768)//(65536//len(nxt)),state])
        closed, report=close(packed,nxt)
        rows[name]=dict(original_final_state=state,closure_possible=closed is not None,**report)
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
