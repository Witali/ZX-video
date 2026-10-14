"""Compare an exact native prefix with the previously qualified coarse drawing."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'toolkit'))
import native_lineart as line
from row_dictionary_video import display_screen
import build_long_video_trd as video


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--outlined',type=Path)
    parser.add_argument('--experimental',action='store_true',help='allow a fully executed build whose timing gate failed')
    parser.add_argument('--ffmpeg',required=True)
    args=parser.parse_args()
    source=np.fromfile(args.build/'work/frames.rgb',np.uint8).reshape(-1,144,256,3)
    states=np.load(args.build/'work/native-states.npy')
    old_manifest=json.loads((args.baseline/'conversion.json').read_bytes())
    volume=old_manifest['volumes'][0]
    old_metadata=json.loads((args.baseline/volume['metadata']).read_bytes())
    old_states=np.load(args.baseline/volume['states'])['states'][:len(states)]
    outlined=np.load(args.outlined/'work/native-states.npy') if args.outlined else None
    if len(states)!=len(source) or len(old_states)!=len(states):raise ValueError('unmatched prefix')
    reference=json.loads((args.build/'conversion.json').read_bytes())
    if not reference['complete'] or (not reference['timing_verified'] and not args.experimental):raise ValueError('qualified build required, or explicit --experimental')
    output=args.build/'accuracy-comparison.mp4'
    command=[args.ffmpeg,'-v','error','-nostdin','-f','rawvideo','-pixel_format','rgb24',
        '-video_size','768x192','-framerate','10','-i','pipe:0','-i',str(args.build/'work/audio-preview.wav'),
        '-map','0:v:0','-map','1:a:0','-vf','scale=1536:384:flags=neighbor','-c:v','libx264',
        '-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',
        '-t',str(len(states)/10),'-movflags','+faststart',str(output)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    rows=[]
    selected=[59,119,179,237,269,299]
    selected=[min(i,len(states)-1) for i in selected]
    canvas=Image.new('RGB',(1536,len(selected)*316),'#181818');draw=ImageDraw.Draw(canvas)
    details=Image.new('RGB',(1536,len(selected)*316),'#181818');detail_draw=ImageDraw.Draw(details)
    padded=np.zeros((192,256,3),np.uint8)
    try:
        for i,(src,state,old_state) in enumerate(zip(source,states,old_states)):
            screen=display_screen(old_state.tobytes(),old_metadata)
            old=np.asarray(video.base.render_spectrum_screen(screen[:6144],screen[6144:]),np.uint8)
            current=line.pixels(state).astype(np.uint8)
            padded[24:168]=src
            errors={name:float(np.mean((image[24:168].astype(np.float32)-src)**2))
                for name,image in (('previous_coarse_mse',old),('native_thin_mse',current))}
            if outlined is not None:
                prior=line.pixels(outlined[i]).astype(np.uint8)
                errors.update(native_outlined_mse=float(np.mean((prior[24:168].astype(np.float32)-src)**2)),
                    thin_update_changed_pixels=int(np.any(current[24:168]!=prior[24:168],-1).sum()))
            rows.append(dict(frame=i,seconds=i/10,**errors))
            process.stdin.write(np.concatenate([padded,old,current],axis=1).tobytes())
            if i in selected:
                row=selected.index(i)
                for column,(title,image) in enumerate((('Source',src),('Previous coarse',old[24:168]),('Native; thin strokes kept',current[24:168]))):
                    draw.text((column*512+6,row*316+5),f'{i/10:.1f}s: {title}',fill='white')
                    canvas.paste(Image.fromarray(image).resize((512,288),Image.Resampling.NEAREST),(column*512,row*316+24))
                if outlined is not None:
                    for column,(title,image) in enumerate((('Source',src),('Rejected noisy native',prior[24:168]),('Corrected native',current[24:168]))):
                        detail_draw.text((column*512+6,row*316+5),f'{i/10:.1f}s: {title}',fill='white')
                        details.paste(Image.fromarray(image).resize((512,288),Image.Resampling.NEAREST),(column*512,row*316+24))
    finally:process.stdin.close()
    if process.wait()!=0:raise RuntimeError('comparison encoding failed')
    canvas.save(args.build/'comparison.png')
    if outlined is not None:details.save(args.build/'detail-comparison.png')
    means={key:float(np.mean([row[key] for row in rows])) for key in rows[0] if key.endswith('_mse')}
    report=dict(date='2026-10-14',frames=len(states),seconds=len(states)/10,
        columns=['Original source at native sampling','Qualified coarse drawing','CB47 native drawing; no extra thin-stroke outline'],
        player_timing_verified=reference['timing_verified'],experimental=args.experimental,
        preview_cadence='Host-rendered nominal 10 fps; not a recording of actual TRD publication times.',
        baseline=str(args.baseline.resolve()),metrics=means,frames_detail=rows,
        thin_update_changed_pixels=sum(row.get('thin_update_changed_pixels',0) for row in rows),
        source_extent='Same original frame times, contain fit, no crop. Native source is decoded directly at 256x144.',
        geometry_note='Previous drawing used 128x72 sampling expanded 2x2; rounding centres that source one native pixel differently. RGB error against the native source includes this resampling difference.',
        metric_scope='RGB error for a stylised drawing; no photographic or semantic accuracy claim.',command=command)
    (args.build/'accuracy-comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(output=str(output),metrics=means,frames=len(states))))


if __name__=='__main__':main()
