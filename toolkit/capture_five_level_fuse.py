"""Capture complete real Fuse screens in separate runs after selected OUTs.

Timing verification is a separate uninterrupted run. At each selected screen
publication this tool stops the player, pages its physical screen bank, and
dumps RAM using an existing DI instruction. It never patches screen bytes.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw
import build_long_video_trd as video
import five_level_dither as five
from build_fap3_trd import sha
from disk_progress_z80 import reference_screen
from smoke_test_fuse import hidden_startupinfo


def capture(fuse,trd,m,index,work):
    lab=m['player_labels']; nonce=secrets.randbits(30)
    start=0xc000 if index%2==0 else 0x4000; end=start+6912
    count=lab['published']
    lines=['base 10','set $r 0',f'set $dump {end+1}',
        f'breakpoint {lab["start"]}','commands 1','set $r 1','continue','end',
        f'breakpoint {lab["publish_out"]+2}','commands 2','print 100',f'print {nonce}',
        'print spectrum:frames*70908+ula:tstates','print ula:mem7ffd',f'print [{count}]+256*[{count+1}]',
        'print [39520]','set $r 0',f'set $dump {start}','out 32765 23','set z80:pc 39520','continue','end',
        f'condition 2 $r==1 && [{count}]+256*[{count+1}]=={index}',
        'breakpoint 39521','commands 3','print 300',
        'print [$dump]+256*[$dump+1]+65536*[$dump+2]+16777216*[$dump+3]',
        'set $dump $dump+4','set z80:pc 39520','continue','end',f'condition 3 $dump<{end}',
        'breakpoint 39521','commands 4','print 301','exit 77','end',f'condition 4 $dump=={end}']
    script='\n'.join(lines)
    command=[str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions',
        '--speed','10000','--machine','128','--beta128','--debugger-command',script,str(trd.resolve())]
    epoch=time.time()
    result=subprocess.run(command,cwd=fuse.parent,env=dict(os.environ,SDL_VIDEODRIVER='dummy'),
                          capture_output=True,timeout=120,startupinfo=hidden_startupinfo())
    output=result.stdout.decode(errors='replace'); fallback=fuse.parent/'stdout.txt'
    if not re.search(r'^\s*\d+\s*$',output,re.M) and fallback.exists() and fallback.stat().st_mtime>=epoch-2:
        output=fallback.read_text(errors='replace')
    (work/f'frame-{index}.trace.txt').write_text(output)
    (work/f'frame-{index}.debugger.txt').write_text(script)
    nums=[int(s.strip(),0) for s in output.splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip())]
    if nums[:2]!=[100,nonce] or nums[4]!=index or nums[5]!=0xf3 or nums[-1]!=301:
        raise AssertionError(('capture marker mismatch',index,nums[:6],nums[-6:]))
    pairs=nums[6:-1]
    if len(pairs)!=3456 or pairs[::2]!=[300]*1728:
        raise AssertionError('incomplete screen dump')
    screen=b''.join((v&0xffffffff).to_bytes(4,'little') for v in pairs[1::2])
    if bool(nums[3]&8)!=(index%2==0): raise AssertionError('published screen bank differs')
    return screen,dict(frame=index,publication_tstate=nums[2],page=nums[3],nonce_exact=True,
        screen_sha256=sha(screen),trace_sha256=sha((work/f'frame-{index}.trace.txt').read_bytes()),
        debugger_sha256=sha((work/f'frame-{index}.debugger.txt').read_bytes()),
        exit_code=result.returncode)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('fuse','trd','metadata','prepared','build-report','work','output','preview'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--frames',type=int,nargs='+',default=[31,64,95,128,159,191])
    a=p.parse_args(); m=json.loads(a.metadata.read_text()); build=json.loads(a.build_report.read_text())
    a.work.mkdir(parents=True,exist_ok=True)
    if sha(a.trd.read_bytes())!=build['trd_sha256']: raise ValueError('build image differs')
    with np.load(a.prepared,allow_pickle=False) as saved:
        states=saved['states']; five_states=saved['five_states']; four=saved['four_states']; images=saved['images']
    if sha(states.tobytes())!=build['states_sha256']: raise ValueError('prepared input differs')
    sheet=Image.new('RGB',(1536,416*len(a.frames)),(24,24,24)); draw=ImageDraw.Draw(sheet); rows=[]
    for row,index in enumerate(a.frames):
        actual,record=capture(a.fuse,a.trd,m,index,a.work)
        expected=reference_screen(b''.join(five.expand(five_states[index].tobytes())),index,m['frames'])
        bad=[i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y]
        record.update(compared_bytes=6912,mismatched_bytes=len(bad),mismatch_offsets=bad[:32],
                      source_frame=build['quality'][index]['source_frame'],
                      four_mse=build['quality'][index]['four_mse'],five_mse=build['quality'][index]['five_mse'])
        (a.work/f'frame-{index}.scr').write_bytes(actual)
        native=Image.fromarray(video.base.render_spectrum_screen(actual[:6144],actual[6144:]))
        old=Image.fromarray(video.base.render_spectrum_screen(*video.expand_compact_screen(four[index].tobytes())))
        source=Image.fromarray(images[index]).resize((256,192),Image.Resampling.NEAREST)
        for col,(label,panel) in enumerate(zip(('Scaled source','Four-code reference','Five levels: actual Fuse RAM'),(source,old,native))):
            sheet.paste(panel.resize((512,384),Image.Resampling.NEAREST),(512*col,416*row+24))
            draw.text((512*col+8,416*row+6),f'{index} / source {record["source_frame"]}: {label}',fill='white')
        rows.append(record); print(json.dumps(record),flush=True)
    sheet.save(a.preview)
    report=dict(complete=all(r['mismatched_bytes']==0 for r in rows),release=False,scope=__doc__,
        trd_sha256=build['trd_sha256'],rom_sha256=sha((a.fuse.parent/'roms/trdos.rom').read_bytes()),
        full_screen_captures=rows,preview_sha256=sha(a.preview.read_bytes()),
        metric='MSE of 2x2 averaged sRGB versus scaled source, active 256x144 area; not a perceptual accuracy percentage',
        progress_included=True,timing_claim=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    if not report['complete']: raise SystemExit(1)


if __name__=='__main__': main()
