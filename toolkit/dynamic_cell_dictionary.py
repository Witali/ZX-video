"""Host-only scene-local cell-book replacements for the CB43 size experiment."""
from collections import Counter

import numpy as np


def plan(current,changed,window,*,minimum_gain=12):
    if window<1 or minimum_gain<0:raise ValueError('invalid cell lookahead')
    count=len(current);symbols=np.full(changed.shape,-1,dtype=np.int16)
    keys=[[current[f,c].tobytes() for c in np.flatnonzero(changed[f])] for f in range(count)]
    book=[];lookup={};updates=[[] for _ in range(count)]
    for lo in range(0,count,window):
        hi=min(count,lo+window);uses=Counter(key for frame in keys[lo:hi] for key in frame)
        ranked=sorted(uses,key=lambda key:(-uses[key],key))
        if not book:
            book=ranked[:256]+[None]*max(0,256-len(ranked))
            initial=book.copy();lookup={key:i for i,key in enumerate(book) if key is not None}
        else:
            for key in ranked:
                if key in lookup:continue
                victim=min(range(256),key=lambda i:(uses.get(book[i],0),i))
                old=book[victim]
                # One dictionary cell uses one byte, a row fallback four;
                # the replacement itself costs nine bytes before LZSA2.
                if 3*(uses[key]-uses.get(old,0))<9+minimum_gain:break
                if old is not None:del lookup[old]
                book[victim]=key;lookup[key]=victim;updates[lo].append((victim,key))
        for f in range(lo,hi):
            for cell,key in zip(np.flatnonzero(changed[f]),keys[f]):
                symbols[f,cell]=lookup.get(key,-1)
    return initial,symbols,updates
