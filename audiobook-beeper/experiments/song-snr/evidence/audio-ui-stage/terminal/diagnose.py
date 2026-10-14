"""Minimal actual whole-song READY/end checkpoints; no waveform trace."""
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import time


HERE=Path(__file__).resolve().parent
BASE=runpy.run_path(str(HERE.parent/'diagnose.py'))
DISK,META,FUSE=BASE['DISK'],BASE['META'],BASE['FUSE']
LABELS=META['player_labels'];stamp='spectrum:frames*71680+ula:tstates'


def main():
    lines=['base 10',f"br {LABELS['ready']}",'com 1','pr -10','pr '+stamp,'pr ula:mem7ffd',
           f"pr ([{LABELS['stream_remaining']}]+[{LABELS['stream_remaining']+1}]*256)",'co','end',
           f"br {LABELS['stream_finished']}",'com 2','pr -11','pr '+stamp,'pr ula:mem7ffd',
           '[23416]']
    # At completion bank7 remains mapped. Observe all32 finalbar attributes.
    lines[-1]='pr [23416]'
    lines.extend('pr ['+str(address)+']' for address in range(0xDAC0,0xDAE0))
    lines.extend(['ex 77','end'])
    script='\n'.join(lines);(HERE/'debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    command=[str(FUSE),'--no-sound','--no-autosave-settings','--no-confirm-actions',
             '--speed','10000','--machine','pentagon512','--beta128','--debugger-command',script,str(DISK.resolve())]
    start=time.perf_counter();timeout=False
    try:
        result=subprocess.run(command,cwd=FUSE.parent,env=dict(os.environ,SDL_VIDEODRIVER='dummy'),
                              capture_output=True,startupinfo=BASE['hidden_startupinfo'](),timeout=60)
        stdout,stderr,code=result.stdout,result.stderr,result.returncode
    except subprocess.TimeoutExpired as error:
        stdout,stderr,code=error.stdout or b'',error.stderr or b'',None;timeout=True
    elapsed=time.perf_counter()-start
    (HERE/'stdout.txt').write_bytes(stdout);(HERE/'stderr.txt').write_bytes(stderr)
    values=[int(match.group(1),0) for match in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',stdout)]
    ready=terminal=None;cursor=0
    while cursor<len(values):
        tag=values[cursor];cursor+=1
        if tag>=0xffff0000:tag-=2**32
        if tag==-10:
            ready=dict(timestamp=values[cursor],paging=values[cursor+1],remaining=values[cursor+2]);cursor+=3
        elif tag==-11:
            terminal=dict(timestamp=values[cursor],paging=values[cursor+1],bar_counter=values[cursor+2],attributes=values[cursor+3:cursor+35]);cursor+=35
    report=dict(date='2026-10-14',profile='pentagon512',elapsed_seconds=elapsed,returncode=code,
                timed_out=timeout,timeout_seconds=60,trd_sha256=hashlib.sha256(DISK.read_bytes()).hexdigest(),
                ready=ready,terminal=terminal,end_of_audio_reached=terminal is not None,
                ready_to_terminal_seconds=(terminal['timestamp']-ready['timestamp'])/3584000 if ready and terminal else None,
                final_bar_green=bool(terminal and terminal['attributes']==[0x24]*32),command=command,
                scope='Actual whole-song global READY/end path only. No bit/state/relative-pulse-timing orqualityclaim; fulltraceverification stillrequired')
    (HERE/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='command'},indent=2),flush=True)


if __name__=='__main__':main()
