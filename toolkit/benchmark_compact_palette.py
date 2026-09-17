"""Time old/new palette searches on real source frames and verify identical output."""
import argparse
import json
import os
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import numpy as np
import build_long_video_trd as video


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-video',type=Path,required=True)
    p.add_argument('--ffmpeg',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    os.environ['PATH']=str(args.ffmpeg.resolve().parent)+os.pathsep+os.environ['PATH']
    results=[];previous=None;prior=bytes(video.STATE_BYTES)
    for offset in (0,60,200,400,590):
        process,_=video.ffmpeg_frames(args.input_video,offset,.12,25/3,pad_end=True)
        raw=process.communicate()[0]
        if process.returncode or len(raw)!=256*144*3:raise ValueError('source frame decoding failed')
        image=video.apply_reframe(np.frombuffer(raw,dtype=np.uint8).reshape(144,256,3),video.ReframeWindow(.5,.5,1.25))
        call=(image,previous,prior,'ordered4',6,1.25)
        def reference(*a,**kw):return video.encode_compact_frame_reference(*a)
        # Suppress preparation in the reference path: the former loop had none.
        with patch.object(video,'encode_compact_frame',side_effect=reference),patch.object(video,'prepare_compact_palette',return_value=None),patch.object(video.base,'render_spectrum_screen',side_effect=video.base.render_spectrum_screen_reference):
            start=perf_counter();old=video.encode_feedback_frame(*call);old_seconds=perf_counter()-start
        start=perf_counter();new=video.encode_feedback_frame(*call);new_seconds=perf_counter()-start
        assert old[0]==new[0] and np.array_equal(old[1],new[1]) and old[2]==new[2]
        results.append(dict(source_seconds=offset,previous_seconds=old_seconds,current_seconds=new_seconds,
            speedup=old_seconds/new_seconds,distinct_colours=len(np.unique(image.reshape(-1,3),axis=0)),byte_identical=True))
        previous=new[1];prior=new[0]
    report=dict(scope='offline host conversion; player Z80 code unchanged, delta 0 T',
        note='Real frames before adaptive tone mapping; wall time depends on host load.',frames=results)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
