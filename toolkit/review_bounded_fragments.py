"""Frame-level quality against the original movie at the saved edit indices."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from probe_bounded_dictionary import quality
from probe_lossless_layouts import sha
from probe_bounded_fragments import write_report
from review_bounded_dictionary import render, ssim
from review_motion_quality import transition_counts


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','candidate','output','filmstrip'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    with np.load(args.reference,allow_pickle=False) as z: original=z['states']
    with np.load(args.candidate,allow_pickle=False) as z:
        candidate=z['states'];indices=z['source_frames']
    reference=original[indices]
    report=quality(reference,candidate);rows=[];previous_ref=previous_new=None
    for index,(old,new) in enumerate(zip(reference,candidate)):
        first,second=render(old)[24:168],render(new)[24:168]
        transitions=transition_counts(previous_ref,first,previous_new,second) if index else dict(source_changes=0,missing_changes=0,spurious_changes=0)
        rows.append(dict(index=index,source_frame=int(indices[index]),ssim=ssim(first,second),
            changed_rgb_pixels=int(np.count_nonzero(np.any(first!=second,axis=2))),**transitions))
        previous_ref,previous_new=first,second
        if index%500==0:print(f'Quality: {index}/{len(reference)}',flush=True)
    worst=list(dict.fromkeys([min(range(len(rows)),key=lambda i:rows[i]['ssim']),
        max(range(len(rows)),key=lambda i:rows[i]['missing_changes']),max(range(len(rows)),key=lambda i:rows[i]['spurious_changes'])]))
    sheet=Image.new('RGB',(1280,len(worst)*616),(24,24,24));draw=ImageDraw.Draw(sheet)
    for strip,event in enumerate(worst):
        length=min(5,len(rows));start=min(max(0,event-2),len(rows)-length)
        for column,index in enumerate(range(start,start+length)):
            old,new=render(reference[index]),render(candidate[index]);diff=np.zeros_like(old)
            diff[np.any(old!=new,axis=2)]=[255,70,70]
            x,y=256*column,strip*616
            draw.text((x+4,y+4),f'Frame {index} / original {indices[index]}',fill='white')
            draw.text((x+4,y+19),'Original / candidate / differences',fill='white')
            for row,pixels in enumerate((old,new,diff)):sheet.paste(Image.fromarray(pixels),(x,y+40+192*row))
    args.filmstrip.parent.mkdir(parents=True,exist_ok=True);sheet.save(args.filmstrip)
    report.update(complete=True,release=False,original_sha256=sha(original.tobytes()),reference_sha256=sha(reference.tobytes()),
        candidate_sha256=sha(candidate.tobytes()),mean_ssim=float(np.mean([r['ssim'] for r in rows])),
        minimum_ssim=min(r['ssim'] for r in rows),mean_missing_changes=float(np.mean([r['missing_changes'] for r in rows[1:]])) if len(rows)>1 else 0,
        mean_spurious_changes=float(np.mean([r['spurious_changes'] for r in rows[1:]])) if len(rows)>1 else 0,
        worst_events=worst,full_motion_viewing_complete=False,rows=rows)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    write_report(args.output,report)
    print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)


if __name__=='__main__':main()
