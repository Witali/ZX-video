"""Choose three cuts from window costs and exact row unions, no TRD sweeps."""
import numpy as np


def three_parts(sets, costs, max_frames):
    count = len(sets)
    if count < 3: raise ValueError('three volumes need at least three frames')
    present = np.zeros((count,625),dtype=np.int32)
    for i,values in enumerate(sets): present[i,list(values)] = 1
    prefix = np.vstack([np.zeros(625,dtype=np.int32),present.cumsum(axis=0)])
    cumulative = np.r_[0,np.cumsum(costs)]
    # 16-frame cut grid plus the final endpoint. Exact row histories use n-2.
    edges = np.arange(16,count,16) if count > 32 else np.arange(1,count)
    candidates = []
    tested = 0
    for left in edges:
        if left > max_frames or np.count_nonzero(prefix[left]) > 256: continue
        rights = edges[(edges>left)&(edges-left<=max_frames)&(count-edges<=max_frames)]
        if not len(rights): continue
        mid = np.count_nonzero(prefix[rights]-prefix[max(0,left-2)],axis=1)
        tail = np.count_nonzero(prefix[count]-prefix[np.maximum(0,rights-2)],axis=1)
        valid = (mid<=256)&(tail<=256)
        tested += len(rights)
        for right in rights[valid]:
            amounts = [cumulative[left],cumulative[right]-cumulative[left],cumulative[count]-cumulative[right]]
            candidates.append((max(amounts),float(np.std(amounts)),int(left),int(right),amounts))
    if not candidates: raise ValueError('no three-volume row-valid cuts on the 16-frame grid')
    _,_,left,right,amounts = min(candidates)
    bounds = [0,left,right,count]
    return list(zip(bounds,bounds[1:])),dict(method='minimax local-window bytes on a 16-frame grid',
        candidates=tested,row_valid_candidates=len(candidates),boundaries=bounds,
        estimated_video_bytes=list(map(float,amounts)),
        exact_final_capacity_required=True,whole_movie_candidates_compressed=0)
