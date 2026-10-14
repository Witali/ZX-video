"""Bounded actual first100 source-output diagnostic with minimal hooks."""
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
bit='([z80:pc-1]==81 || ([z80:pc-1]==65 && z80:b==16) || ([z80:pc-1]==254 && z80:a==16))'


def main():
    # Register the terminating condition first: the following counter cannot
    # make the same OUT satisfy it retroactively during breakpoint handling.
    lines=['base 10','set $active 0','set $pulse 0',
           f"br {LABELS['ready']}",'com 1','pr -10','pr '+stamp,'se $active 1','co','end',
           'br port write 254','com 2','pr -11','pr '+stamp,'pr z80:pc','pr '+bit,'pr $pulse',
           'ex 77','end','cond 2 $active==1 && $pulse==99',
           'br port write 254','com 3','pr -12','pr '+stamp,'pr z80:pc','pr '+bit,'pr $pulse',
           'se $pulse $pulse+1','co','end','cond 3 $active==1 && $pulse<99',
           f"br {LABELS['stream_finished']}",'com 4','pr -13','pr '+stamp,'ex 77','end']
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
    (HERE/'stdout.txt').write_bytes(stdout);(HERE/'stderr.txt').write_bytes(stderr)
    values=[int(match.group(1),0) for match in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',stdout)]
    events=[];cursor=0
    while cursor<len(values):
        tag=values[cursor];cursor+=1
        if tag>=0xffff0000:tag-=2**32
        if tag not in (-10,-11,-12,-13):continue
        names=['timestamp'] if tag in (-10,-13) else ['timestamp','pc','bit','pulse_index']
        if cursor+len(names)>len(values):break
        events.append(dict(tag=tag,**dict(zip(names,values[cursor:cursor+len(names)]))));cursor+=len(names)
    source=[item for item in events if item['tag'] in (-11,-12)]
    report=dict(date='2026-10-14',profile='pentagon512',elapsed_seconds=time.perf_counter()-start,
                returncode=code,timed_out=timeout,timeout_seconds=60,
                trd_sha256=hashlib.sha256(DISK.read_bytes()).hexdigest(),events=events,
                source_output_count=len(source),first100_complete=(len(source)==100 and [item['pulse_index'] for item in source]==list(range(100)) and all(a['timestamp']<b['timestamp'] for a,b in zip(source,source[1:]))),
                command=command,scope='Actual first100 source outputs only, no full playback claim')
    (HERE/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key not in ('events','command')},indent=2),flush=True)


if __name__=='__main__':main()
