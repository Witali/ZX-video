"""Render complete native references at nominal cadence, with explicit timing status."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'toolkit'))
import native_lineart as line


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--experimental',action='store_true')
    args=p.parse_args();m=json.loads((args.build/'conversion.json').read_bytes())
    if not m['complete'] or len(m['volumes'])!=1:raise ValueError('complete single-volume prefix required')
    if not m['timing_verified'] and not args.experimental:raise ValueError('unqualified timing requires --experimental')
    v=m['volumes'][0];folder=args.build/'work'/Path(v['file']).stem
    proof=json.loads((folder/'screens.json').read_bytes())
    if not proof['full_screens_exact']:raise ValueError('complete native Fuse screens required')
    states=np.load(folder/'states.npz')['states'];assert len(states)==v['frames']
    output=args.build/'native-preview.mp4'
    command=[args.ffmpeg,'-v','error','-nostdin','-f','rawvideo','-pixel_format','rgb24',
        '-video_size','256x192','-framerate','10','-i','pipe:0','-i',str(args.build/'work/audio-preview.wav'),
        '-map','0:v:0','-map','1:a:0','-vf','scale=512:384:flags=neighbor','-c:v','libx264',
        '-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',
        '-t',str(v['frames']/10),'-movflags','+faststart',str(output)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for state in states:process.stdin.write(line.pixels(state).astype(np.uint8).tobytes())
    finally:process.stdin.close()
    if process.wait()!=0:raise RuntimeError('native preview failed')
    report=dict(complete=True,frames=len(states),fps=10,duration_seconds=len(states)/10,
        native_screens_exact_before_video_encoding=True,actual_player_timing_verified=m['timing_verified'],
        experimental=args.experimental,source='Nominal 10-fps host references and unchanged AY model WAV.',
        cadence_note='Not an emulator recording. When timing is unqualified, the TRD runs slower than this preview.',command=command)
    (args.build/'preview.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(output=str(output),frames=len(states),player_timing_verified=m['timing_verified'])))


if __name__=='__main__':main()
