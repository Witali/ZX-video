"""Choose volume cuts from window costs and optional row unions, no TRD sweeps."""
import numpy as np


def balanced_parts(costs, max_frames, volumes, *, sets=None, grid=16):
    """Minimize the largest local-window byte sum without encoding candidates.

    A missing row-set constraint means the caller uses a dynamic dictionary.
    Exact resident audio, final disk capacity and delivery remain later gates.
    """
    count=len(costs)
    if not 1<=volumes<=count or max_frames<1 or grid<1:
        raise ValueError('invalid volume planning bounds')
    if not np.all(np.isfinite(costs)) or np.any(np.asarray(costs)<0):
        raise ValueError('invalid local byte costs')
    edges=[0]+list(range(grid if count>2*grid else 1,count,grid if count>2*grid else 1))+[count]
    cumulative=np.r_[0,np.cumsum(costs)]
    prefix=None
    if sets is not None:
        if len(sets)!=count:raise ValueError('row-set extent differs')
        present=np.zeros((count,625),dtype=np.int32)
        for i,values in enumerate(sets):present[i,list(values|{0})]=1
        prefix=np.vstack([np.zeros(625,dtype=np.int32),present.cumsum(axis=0)])
    # Each state records minimax cost, sum of squares (tie-break) and cuts.
    previous={0:(0.,0.,[0])};tested=0
    for part in range(volumes):
        current={}
        for hi in edges[1:]:
            if hi==count and part!=volumes-1:continue
            best=None
            for lo,(peak,square,cuts) in previous.items():
                if not 0<hi-lo<=max_frames:continue
                tested+=1
                if prefix is not None and np.count_nonzero(prefix[hi]-prefix[max(0,lo-2)])>256:continue
                amount=float(cumulative[hi]-cumulative[lo])
                candidate=(max(peak,amount),square+amount*amount,cuts+[hi])
                if best is None or candidate<best:best=candidate
            if best is not None:current[hi]=best
        previous=current
    if count not in previous:raise ValueError('no valid volume cuts on the selected grid')
    peak,_,cuts=previous[count]
    return list(zip(cuts,cuts[1:])),dict(method='minimax dynamic programming over local-window costs',
        volumes=volumes,grid_frames=grid,transitions_tested=tested,boundaries=cuts,
        dynamic_row_dictionary=sets is None,estimated_peak_video_bytes=peak,
        estimated_video_bytes=[float(cumulative[hi]-cumulative[lo]) for lo,hi in zip(cuts,cuts[1:])],
        exact_final_capacity_required=True,whole_movie_candidates_compressed=0)


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
