"""Render selected verified Fuse screens beside their saved source images."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from build_fap3_trd import sha
from build_long_video_trd import base


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('captures','prepared','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--frames',nargs='+',type=int,default=[31,95,159,191])
    a=p.parse_args();captured=json.loads(a.captures.read_bytes())
    assert captured['complete'] and captured['full_screens_exact']
    with np.load(a.prepared,allow_pickle=False) as f:
        states=f['states'];images=f['images']
    assert sha(states.tobytes())==captured['states_sha256']
    records={r['frame']:r for r in captured['screens']}
    sheet=Image.new('RGB',(1024,416*len(a.frames)),(24,24,24));draw=ImageDraw.Draw(sheet)
    for row,index in enumerate(a.frames):
        record=records[index];screen=bytes.fromhex(record['screen_hex'])
        assert record['exact'] and sha(screen)==record['screen_sha256']
        source=Image.fromarray(images[record['source_state']]).resize((256,192),Image.Resampling.NEAREST)
        native=Image.fromarray(base.render_spectrum_screen(screen[:6144],screen[6144:]))
        for col,(label,panel) in enumerate((('Prepared source',source),('Five-level CB41: actual Fuse screen',native))):
            sheet.paste(panel.resize((512,384),Image.Resampling.NEAREST),(col*512,row*416+24))
            draw.text((col*512+8,row*416+6),f'Frame {index}: {label}',fill='white')
    a.output.parent.mkdir(parents=True,exist_ok=True);sheet.save(a.output)
    print(json.dumps(dict(frames=a.frames,preview_sha256=sha(a.output.read_bytes()))))


if __name__=='__main__':main()
