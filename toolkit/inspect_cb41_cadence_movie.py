"""Check resampled movie coverage, unchanged AY prefix and selected pictures."""
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image, ImageDraw
import build_long_video_trd as video
from prepare_edited_movie import frame_map
from prepare_cell_codebook_movie import file_sha, sha
from verify_cell_codebook_movie import independent_screen


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('prepared','source','ffprobe','output','preview'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.prepared.read_bytes());contract=m['contract']
    assert file_sha(a.source)==contract['source_sha256']
    source_probe=json.loads(subprocess.check_output([str(a.ffprobe.resolve()),'-v','error',
        '-select_streams','v:0','-show_entries','stream=r_frame_rate,avg_frame_rate,time_base',
        '-of','json',str(a.source.resolve())]))
    fps=Fraction(contract['fps']);fields=contract['frame_fields'];t=contract['timeline']
    source_count=math.ceil(Fraction(t['source_frames']*3,25)*fps)
    cuts=[[math.ceil(Fraction(lo*3,25)*fps),math.ceil(Fraction(hi*3,25)*fps)] for lo,hi in t['remove_frames']]
    mapping=frame_map(source_count,cuts)
    assert len(mapping)==m['frames'] and mapping[-1]==source_count-1
    assert sha(mapping.astype('<i8').tobytes())==m['source_frame_map_sha256']
    audio=(a.prepared.parent/'audio.bin').read_bytes()
    assert len(audio)==len(mapping)*fields*9 and sha(audio)==m['ay_sha256']
    assert sha(audio[:m['original_audio_ticks']*9])==m['original_audio_sha256']
    assert audio[m['original_audio_ticks']*9:]==video.AyFrame((1,1,1),(0,0,0)).serialize()*m['silent_tail_ticks']
    samples=sorted({0,754,3428,4207,4338,4903,4904,len(mapping)-1,
        max(range(len(mapping)),key=lambda i:m['quality'][i]['five_mse'])})
    pictures={};count=0
    for chunk in m['chunks']:
        path=a.prepared.parent/chunk['file'];assert file_sha(path)==chunk['sha256']
        with np.load(path,allow_pickle=False) as f:
            assert np.array_equal(f['source_frames'],mapping[chunk['start']:chunk['end']])
            for i,frame in enumerate(f['five_states']):
                index=chunk['start']+i;screen=independent_screen(frame.tobytes())
                assert sha(screen)==m['quality'][index]['screen_sha256']
                assert m['quality'][index]['five_mse']<=m['quality'][index]['four_mse']+1e-9
                count+=1
                if index in samples: pictures[index]=(f['images'][i].copy(),screen)
    assert count==len(mapping)
    sheet=Image.new('RGB',(528,218*len(samples)),'#202020');draw=ImageDraw.Draw(sheet)
    for i,index in enumerate(samples):
        src,screen=pictures[index]
        draw.text((4,i*218+4),f'{index/float(fps):.1f}s / frame {index}: source and Spectrum',fill='white')
        sheet.paste(Image.fromarray(src).resize((256,192),Image.Resampling.NEAREST),(4,i*218+22))
        sheet.paste(Image.fromarray(video.base.render_spectrum_screen(screen[:6144],screen[6144:])),(268,i*218+22))
    sheet.save(a.preview)
    report=dict(complete=True,release=False,preparation_sha256=file_sha(a.prepared),
        source_probe=source_probe,video_fps=str(fps),frames=count,ay_ticks=len(audio)//9,
        original_audio_ticks=m['original_audio_ticks'],original_audio_sha256=m['original_audio_sha256'],
        original_audio_prefix_exact=True,silent_tail_ticks=m['silent_tail_ticks'],
        duration_seconds=count*fields/50,final_source_frame=int(mapping[-1]),
        cuts_at_new_rate=cuts,whole_story_and_post_credit_to_eof=True,
        full_host_screens_exact=True,compared_screen_bytes=count*6912,
        four_mse_mean=float(np.mean([q['four_mse'] for q in m['quality']])),
        five_mse_mean=float(np.mean([q['five_mse'] for q in m['quality']])),
        refinement_never_increased_rgb_error=True,preview_frames=samples,preview_sha256=file_sha(a.preview),
        motion_interpolation=False,actual_playback_measured=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__': main()
