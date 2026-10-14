"""Bounded readability review of titles and faces on the same native source."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'toolkit'))
import native_lineart as line
from row_dictionary_video import display_screen
import build_long_video_trd as video


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path);p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    rgb=np.fromfile(args.build/'work/frames.rgb',np.uint8).reshape(-1,144,256,3)
    prior=np.load(args.build/'work/native-states.npy')
    old=json.loads((args.baseline/'conversion.json').read_bytes())['volumes'][0]
    old_meta=json.loads((args.baseline/old['metadata']).read_bytes())
    old_states=np.load(args.baseline/old['states'])['states']
    original=deepcopy(line.PARAMETERS);original_lines=line.source_lines
    profiles=[dict(name='Unfiltered native',filter=False,fine=12,coarse=20,thin=12),
        dict(name='Filtered, subtle',filter=True,fine=20,coarse=30,thin=24),
        dict(name='Filtered, clear',filter=True,fine=30,coarse=40,thin=32),
        dict(name='Filtered, strong',filter=True,fine=40,coarse=50,thin=40)]
    chosen=[59,119,179,299]
    canvas=Image.new('RGB',(512*(2+len(profiles)),312*len(chosen)),'#181818');draw=ImageDraw.Draw(canvas)
    results=[];native=np.zeros((192,256,3),np.uint8)
    for row,i in enumerate(chosen):
        native[24:168]=rgb[i]
        scr=display_screen(old_states[i].tobytes(),old_meta)
        baseline=np.asarray(video.base.render_spectrum_screen(scr[:6144],scr[6144:]),np.uint8)[24:168]
        views=[('Source',rgb[i]),('Previous coarse',baseline)]
        for profile in profiles:
            if not profile['filter']:
                views.append((profile['name'],line.pixels(prior[i])[24:168].astype(np.uint8)))
                continue
            line.PARAMETERS.update(fine_canny_low=profile['fine'],fine_canny_high=profile['fine']*2,
                coarse_canny_low=profile['coarse'],coarse_canny_high=profile['coarse']*2,
                thin_stroke_component_contrast=profile['thin'])
            line.source_lines=original_lines
            state=line.encode(native);output=line.pixels(state)[24:168].astype(np.uint8)
            views.append((profile['name'],output))
            results.append(dict(frame=i,profile=profile,black_pixels=int((output.max(-1)==0).sum())))
        for col,(name,view) in enumerate(views):
            draw.text((col*512+5,row*312+4),f'{i/10:.1f}s {name}',fill='white')
            canvas.paste(Image.fromarray(view).resize((512,288),Image.Resampling.NEAREST),(col*512,row*312+24))
    canvas.save(args.output/'comparison.png')
    for i in range(len(profiles)):
        strips=Image.new('RGB',(1536,312*len(chosen)))
        for row in range(len(chosen)):
            for col,source_col in enumerate((0,1,2+i)):
                strips.paste(canvas.crop((source_col*512,row*312,(source_col+1)*512,(row+1)*312)),(col*512,row*312))
        strips.save(args.output/(str(i)+'-profile.png'))
    (args.output/'review.json').write_text(json.dumps(dict(frames=chosen,profiles=profiles,results=results,baseline_parameters=original),indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
