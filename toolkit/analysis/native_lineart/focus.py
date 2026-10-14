"""Show exact title/face references without rerendering immutable video evidence."""
import argparse
from pathlib import Path
import sys
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'toolkit'))
import native_lineart as line


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',type=Path);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    source=np.fromfile(args.evidence/'work/frames.rgb',np.uint8).reshape(-1,144,256,3)
    after=np.load(args.evidence/'work/native-states.npy')
    before=np.load(args.evidence/'attempts/native-test-300-thin/states.npz')['states']
    selected=[59,119,179];canvas=Image.new('RGB',(1536,948),'#181818');draw=ImageDraw.Draw(canvas)
    for row,i in enumerate(selected):
        views=[('Source',source[i]),('Rejected noisy native',line.pixels(before[i])[24:168].astype(np.uint8)),
            ('Corrected native',line.pixels(after[i])[24:168].astype(np.uint8))]
        for column,(name,picture) in enumerate(views):
            draw.text((column*512+6,row*316+5),f'{i/10:.1f}s: {name}',fill='white')
            canvas.paste(Image.fromarray(picture).resize((512,288),Image.Resampling.NEAREST),(column*512,row*316+24))
    canvas.save(args.output)
    print(str(args.output))


if __name__=='__main__':main()
