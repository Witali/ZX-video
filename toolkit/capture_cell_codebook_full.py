"""Compare every full CB41 screen with read-only Fuse debugger passes.

Windows limits command-line length. Read consecutive 1536-byte slices in
five complete independent runs instead of restarting Fuse for every frame.
The shared native-draw return is sampled without paging, pokes or CPU jumps.
Uninterrupted publication/AY/sector timing remains a separate required test.
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

from build_fap3_trd import sha
from build_five_level_test_trd import save
from disk_progress_z80 import reference_screen
from row_dictionary_video import display_screen
from smoke_test_fuse import hidden_startupinfo


def capture_pass(fuse, trd, metadata, lo, hi, folder, timeout):
    lab = metadata['player_labels']
    draws = [row['address']+3 for row in metadata['cell_codebook']['packet_listing']
             if row['instruction']=='CALL native draw']
    assert len(draws)==1
    base = metadata['cell_codebook']['screen_base']
    nonce = secrets.randbits(30)
    stamp = 'spectrum:frames*70908+ula:tstates'
    lines = ['base 10','set $running 0','set $n 0',
        f'breakpoint {lab["start"]}','commands 1','print 100',f'print {nonce}',
        'set $running 1','continue','end','condition 1 $running==0',
        f'breakpoint {draws[0]}','commands 2','print 200','print $n',f'print {stamp}',
        'print ula:mem7ffd',f'set $s [{base}]*256','print $s']
    for at in range(lo,hi,4):
        lines.append(f'print [$s+{at}]+256*[$s+{at+1}]+65536*[$s+{at+2}]+16777216*[$s+{at+3}]')
    lines += ['set $n $n+1','continue','end','condition 2 $running==1',
        f'breakpoint {lab["finished"]}','commands 3','print 199','print $n',f'print {stamp}',
        'exit 77','end','condition 3 $running==1',
        f'breakpoint {lab["fatal"]}','commands 4','print 198','print $n','exit 78','end',
        'condition 4 $running==1']
    script = '\n'.join(lines)
    command = [str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions',
               '--speed','10000','--machine','128','--beta128','--debugger-command',script,str(trd.resolve())]
    if len(subprocess.list2cmdline(command))>=32760:
        raise ValueError('full-screen slice exceeds Windows command-line limit')
    prefix = folder/f'bytes-{lo}-{hi}'
    prefix.with_suffix('.debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    epoch = time.time()
    result = subprocess.run(command,cwd=fuse.parent,env=dict(os.environ,SDL_VIDEODRIVER='dummy'),
        capture_output=True,timeout=timeout,startupinfo=hidden_startupinfo())
    output = result.stdout.decode(errors='replace')
    fallback = fuse.parent/'stdout.txt'
    if not re.search(r'^\s*\d+\s*$',output,re.M) and fallback.exists() and fallback.stat().st_mtime>=epoch-2:
        output = fallback.read_text(errors='replace')
    prefix.with_suffix('.trace.txt').write_text(output,encoding='utf-8',newline='\n')
    prefix.with_suffix('.stderr.txt').write_bytes(result.stderr)
    numbers = [int(line.strip(),0) for line in output.splitlines()
               if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',line.strip())]
    assert numbers[:2]==[100,nonce], ('trace identity differs',lo)
    at, frames, records = 2, [], []
    width = (hi-lo)//4
    while at<len(numbers) and numbers[at]==200:
        index,stamp,page,screen = numbers[at+1:at+5]
        assert index==len(frames) and page&7==7 and screen==(0xc000 if index%2==0 else 0x4000)
        data = b''.join((value&0xffffffff).to_bytes(4,'little') for value in numbers[at+5:at+5+width])
        assert len(data)==hi-lo
        frames.append(data)
        records.append(dict(frame=index,tstate=stamp,page=page,screen=screen,sha256=sha(data)))
        at += 5+width
    assert numbers[at:at+2]==[199,metadata['frames']] and at+3==len(numbers), ('incomplete frame trace',lo,len(frames))
    assert len(frames)==metadata['frames'] and result.returncode==77
    return frames,dict(start=lo,end=hi,frames=len(frames),nonce=nonce,exit_code=result.returncode,
        trace_sha256=sha(prefix.with_suffix('.trace.txt').read_bytes()),
        debugger_sha256=sha(prefix.with_suffix('.debugger.txt').read_bytes()),records=records)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('fuse','trd','metadata','states','timing','work','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--timeout',type=float,default=180)
    a = p.parse_args()
    a.work.mkdir(parents=True,exist_ok=True)
    metadata = json.loads(a.metadata.read_bytes())
    timing = json.loads(a.timing.read_bytes())
    identity = sha(a.trd.read_bytes())
    assert identity == metadata['trd_sha256'] == timing['trd_sha256']
    assert timing['complete'] and timing['frames']==metadata['frames']
    with np.load(a.states,allow_pickle=False) as cache:
        states = cache['states']
    assert sha(states.tobytes())==metadata['states_sha256']
    expected = [reference_screen(display_screen(states[metadata['frame_start']+i].tobytes(),metadata),i,metadata['frames'])
                for i in range(metadata['frames'])]
    restored = [bytearray() for _ in expected]
    passes = []
    for lo in range(0,6912,1536):
        hi = min(lo+1536,6912)
        frames,report = capture_pass(a.fuse,a.trd,metadata,lo,hi,a.work,a.timeout)
        for i,(data,wanted) in enumerate(zip(frames,expected,strict=True)):
            if data!=wanted[lo:hi]:
                bad = [lo+j for j,(x,y) in enumerate(zip(data,wanted[lo:hi])) if x!=y]
                raise AssertionError(('full Fuse screen differs',i,bad[:32]))
            restored[i].extend(data)
        report['all_bytes_exact'] = True
        passes.append(report)
        save(a.work/'progress.json',dict(complete=False,verified_bytes_per_frame=hi,passes=passes))
        print(f'Volume {metadata["part"]}: all {metadata["frames"]} frames exact through byte {hi}/6912',flush=True)
    assert all(bytes(actual)==wanted for actual,wanted in zip(restored,expected,strict=True))
    screens = [sha(frame) for frame in restored]
    result = dict(complete=True,release=False,scope=__doc__,part=metadata['part'],
        frame_start=metadata['frame_start'],frames=metadata['frames'],trd_sha256=identity,
        full_screens_exact=True,compared_bytes=metadata['frames']*6912,
        pixel_scope='All screen bytes at the common native draw return; publication and AY verified separately on the same TRD.',
        debugger_pokes=0,debugger_paging_changes=0,debugger_cpu_jumps=0,
        passes=passes,screen_sha256=screens,states_sha256=metadata['states_sha256'],
        timing_sha256=sha(a.timing.read_bytes()),
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('capture_cell_codebook_full.py','row_dictionary_video.py','disk_progress_z80.py')})
    save(a.output,result)
    print(json.dumps({k:result[k] for k in ('part','frames','compared_bytes','full_screens_exact')}),flush=True)


if __name__ == '__main__':
    main()
