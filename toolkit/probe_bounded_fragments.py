"""Bounded row-pair simplification before the existing FAP3 encoder.

Search happens on the PC. Every bound is against the original Spectrum
frame, including errors already present in the input candidate. Attributes,
resolution and frame count stay exact. This is not a playback release.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from probe_bounded_dictionary import bitmap_cells, compact_states, contrast_squared
from probe_bounded_motion import CHANGES, MAX_DELTA, SQUARED
from probe_fine_motion import tile_bytes, raster_bytes
from probe_lossless_layouts import sha


def write_report(path,report,row_key='rows'):
    """Keep every frame, with one diffable JSON line per frame."""
    header=json.dumps({k:v for k,v in report.items() if k!=row_key},indent=2)
    body=',\n'.join('    '+json.dumps(row) for row in report[row_key])
    path.write_text(header[:-2]+f',\n  "{row_key}": [\n'+body+'\n  ]\n}\n',encoding='utf-8')


def cell_counts(values):
    """Tile bytes -> NW, NE, SW, SE sums, preserving each byte's four pixels."""
    return values.reshape(-1, 2, 4, 2).sum(axis=2).reshape(-1, 4)


def simple_kinds(tiles):
    rows=tiles.reshape(-1,8,2).astype(np.uint16)
    words=rows[:,:,0]*256+rows[:,:,1]
    distinct=1+np.count_nonzero(np.diff(np.sort(words,axis=1),axis=1),axis=1)
    kinds=np.where(distinct>2,85,np.where(distinct==2,87,86))
    kinds[np.all(tiles==tiles[:,:1],axis=1)]=88
    return kinds


def row_candidates(reference, current, attrs, *, maximum_changed=2, rmse=24):
    """Enumerate 36 row-medoid pairs; choose the shortest eligible tile.

    Row assignment minimizes logical changes, with ties retaining the input
    row when possible. This bounded search is not a global rate-distortion
    optimum, and it does not predict the final ZX0 size.
    """
    source=current.reshape(-1,8,2)
    target=reference.reshape(-1,8,2)
    count=len(source)
    best=current.copy(); scores=np.full(count,np.inf); found=np.zeros(count,bool)
    kinds=simple_kinds(current); allowed_kind=kinds==85
    contrasts=contrast_squared(attrs)
    for first in range(8):
        for second in range(first,8):
            a=source[:,first:first+1,:]; b=source[:,second:second+1,:]
            ca=CHANGES[target,a].sum(axis=2); cb=CHANGES[target,b].sum(axis=2)
            take_b=(cb<ca)|((cb==ca)&np.all(source==b,axis=2))
            proposed=np.where(take_b[:,:,None],b,a).reshape(count,16)
            changed=cell_counts(CHANGES[reference,proposed])
            squared=cell_counts(SQUARED[reference,proposed])
            valid=(allowed_kind & (changed<=maximum_changed).all(axis=1)
                   & (MAX_DELTA[reference,proposed]<=1).all(axis=1)
                   & (squared*contrasts<=rmse**2*256).all(axis=1))
            mode=simple_kinds(proposed)
            sizes=np.choose(mode-85,[16,2,5,1])
            # Prefer fewer payload bytes, then fewer changed logical pixels.
            score=sizes*1000+changed.sum(axis=1)*10+np.count_nonzero(proposed!=current,axis=1)/16
            use=valid&(score<scores)
            best[use]=proposed[use]; scores[use]=score[use]; found|=use
    return best,found


def simplify(reference, baseline, *, budget=128, max_inexact=3, source_frames=None, eligible_tiles=None):
    if reference.shape!=baseline.shape or reference.ndim!=2 or reference.shape[1]!=3840:
        raise ValueError('expected corresponding compact frames')
    if reference.dtype!=np.uint8 or baseline.dtype!=np.uint8 or budget<0 or max_inexact<1:
        raise ValueError('invalid compact data or bounds')
    if not np.array_equal(reference[:,3072:],baseline[:,3072:]):
        raise ValueError('attributes differ from original')
    if eligible_tiles is not None and eligible_tiles.shape!=(len(reference),192):
        raise ValueError('invalid tile eligibility map')
    order=np.arange(768).reshape(24,32).reshape(12,2,16,2).transpose(0,2,1,3).reshape(192,4)
    ref_tiles=tile_bytes(reference[:,:3072],8)
    base_tiles=tile_bytes(baseline[:,:3072],8)
    ages=np.zeros(768,np.uint8); output=np.empty_like(baseline); rows=[]
    for index,(original,old) in enumerate(zip(ref_tiles,base_tiles)):
        if source_frames is not None and index and source_frames[index]!=source_frames[index-1]+1:
            ages[:]=0
        attrs=reference[index,3072:][order]
        proposed,eligible=row_candidates(original,old,attrs)
        if eligible_tiles is not None:eligible &= eligible_tiles[index]
        errors=cell_counts(CHANGES[original,proposed])
        eligible &= np.all((errors==0)|(ages[order]<max_inexact),axis=1)
        sizes=np.choose(simple_kinds(proposed)-85,[16,2,5,1])
        ranked=sorted(np.flatnonzero(eligible),key=lambda t:(-(16-int(sizes[t]))/max(1,int(errors[t].sum())),int(t)))
        result=original.copy(); selected=np.zeros(192,bool); used=0
        for tile in ranked:
            charge=int(errors[tile].sum())
            if used+charge<=budget:
                result[tile]=proposed[tile]; selected[tile]=True; used+=charge
        # Keep old candidate errors where the new choices left budget. Never
        # compound errors or extend an inexact cell beyond the original bound.
        chosen=bitmap_cells(raster_bytes(result[None],8))[0]
        ref=bitmap_cells(reference[index:index+1])[0]
        old_cells=bitmap_cells(baseline[index:index+1])[0]
        old_changes=CHANGES[ref,old_cells].sum(axis=1)
        excluded=np.zeros(768,bool); excluded[order[selected].ravel()]=True
        for cell in np.flatnonzero((old_changes>0)&~excluded&(ages<max_inexact)):
            delta=MAX_DELTA[ref[cell],old_cells[cell]]
            squared=int(SQUARED[ref[cell],old_cells[cell]].sum())
            contrast=float(contrast_squared(reference[index,3072+cell]))
            charge=int(old_changes[cell])
            if charge<=2 and delta.max()<=1 and squared*contrast<=24**2*256 and used+charge<=budget:
                chosen[cell]=old_cells[cell]; used+=charge
        output[index]=compact_states(chosen[None],reference[index:index+1,3072:])[0]
        changed=CHANGES[ref,chosen].sum(axis=1)
        inexact=changed>0; ages=np.where(inexact,ages+1,0).astype(np.uint8)
        assert changed.sum()==used and used<=budget and changed.max()<=2
        assert ages.max()<=max_inexact and MAX_DELTA[ref,chosen].max()<=1
        assert np.all(SQUARED[ref,chosen].sum(axis=1)*contrast_squared(reference[index,3072:])<=24**2*256)
        rows.append(dict(index=index,selected_tiles=int(selected.sum()),logical_changes=used,
            maximum_inexact_age=int(ages.max()),replaced_payload_bytes=int(np.sum(16-sizes[selected])),
            changed_bytes_from_baseline=int(np.count_nonzero(output[index]!=baseline[index]))))
        if index%250==0: print(f'Bounded row pairs: {index}/{len(reference)}',flush=True)
    return output,rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','baseline','output','report'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--budget',type=int,default=128);p.add_argument('--max-inexact',type=int,default=3)
    p.add_argument('--raw-fragments-of',type=Path,help='Restrict new simplifications to existing mode-85 fragments in this FAP3')
    args=p.parse_args()
    with np.load(args.reference,allow_pickle=False) as z: reference=z['states']
    with np.load(args.baseline,allow_pickle=False) as z:
        baseline=z['states']; indices=z['source_frames'] if 'source_frames' in z.files else np.arange(len(baseline))
    if len(reference)!=len(baseline): reference=reference[indices]
    eligibility=None;source_sha=None
    if args.raw_fragments_of:
        from bulk_frame_stream import read_packet
        from probe_motion_entropy import Reader
        from probe_spatial_contexts import read_header
        raw=args.raw_fragments_of.read_bytes();source_sha=sha(raw);r=Reader(raw)
        _,_,count,_,_=read_header(r,magic=b'FAP3')
        if count!=len(baseline):raise ValueError('source and baseline frame counts differ')
        eligibility=[]
        for _ in range(count):
            _,detail=read_packet(r,stored_guards=False);start=sum(map(len,detail['ticks']))+8
            eligibility.append(np.frombuffer(detail['payload'][start:start+192],np.uint8)==85)
        r.end();eligibility=np.asarray(eligibility)
    result,rows=simplify(reference,baseline,budget=args.budget,max_inexact=args.max_inexact,source_frames=indices,eligible_tiles=eligibility)
    report=dict(complete=True,release=False,baseline_commit='3e0db88',scope=__doc__,
        reference_sha256=sha(reference.tobytes()),baseline_sha256=sha(baseline.tobytes()),
        candidate_sha256=sha(result.tobytes()),frames=len(result),budget=args.budget,max_inexact=args.max_inexact,
        raw_fragments_only=eligibility is not None,source_fap3_sha256=source_sha,
        attributes_exact=True,maximum_cell_changes=2,maximum_quarter_coverage_difference=1,rmse_limit=24,
        selected_tiles=sum(r['selected_tiles'] for r in rows),
        potential_literal_savings=sum(r['replaced_payload_bytes'] for r in rows),
        savings_note='Sum of sixteen-byte to row-pair payload reductions; not a measured stream or ZX0 delta.',
        hot_path_changed=False,player_instruction_delta_tstates=0,playback_verified=False,rows=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.report.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(args.output,states=result,source_frames=indices)
    write_report(args.report,report)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)


if __name__=='__main__':main()
