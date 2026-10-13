"""Make a listening preview from the exact native reference screens and AY."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

HERE=Path(__file__).resolve().parent;TOOLKIT=HERE.parents[1];sys.path.insert(0,str(TOOLKIT))
import build_long_video_trd as video
from row_dictionary_video import display_screen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path);parser.add_argument('--ffmpeg',required=True);args=parser.parse_args()
    manifest=json.loads((args.build/'conversion.json').read_bytes())
    if not manifest['complete'] or not manifest['timing_verified']:raise ValueError('complete verified conversion required')
    if len(manifest['volumes'])!=1:raise ValueError('one-disk prefix expected')
    volume=manifest['volumes'][0];stem=Path(volume['file']).stem
    metadata=json.loads((args.build/volume['metadata']).read_bytes())
    states=np.load(args.build/'work'/stem/'states.npz')['states']
    output=args.build/'native-preview.mp4'
    command=[args.ffmpeg,'-v','error','-nostdin','-f','rawvideo','-pixel_format','rgb24','-video_size','256x192',
        '-framerate','10','-i','pipe:0','-i',str(args.build/'work/audio-preview.wav'),
        '-map','0:v:0','-map','1:a:0','-vf','scale=512:384:flags=neighbor','-c:v','libx264','-preset','veryfast',
        '-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-t',str(manifest['duration_seconds']),
        '-movflags','+faststart',str(output)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for index in range(volume['frame_start'],volume['frame_end_exclusive']):
            screen=display_screen(states[index].tobytes(),metadata)
            rgb=video.base.render_spectrum_screen(screen[:6144],screen[6144:])
            process.stdin.write(np.asarray(rgb,np.uint8).tobytes())
    finally:process.stdin.close()
    if process.wait()!=0:raise RuntimeError('FFmpeg preview failed')
    (args.build/'preview.json').write_text(json.dumps(dict(complete=True,frames=volume['frames'],fps=10,
        duration_seconds=manifest['duration_seconds'],native_screens_exact_before_video_encoding=True,
        source='Host-rendered native references plus common AY simulation; actual TRD cadence and full screens independently verified in Fuse.',
        command=command),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,output=str(output),seconds=manifest['duration_seconds'])))


if __name__=='__main__':main()
