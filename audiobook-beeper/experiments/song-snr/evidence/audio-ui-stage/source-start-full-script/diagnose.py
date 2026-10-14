"""Exact full UI debugger script, bounded at its first eligible source OUT."""
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
ORIGINAL=HERE.parent.parent/'audio-ui-emulator/pentagon512/debugger.txt'


def main():
    original=ORIGINAL.read_bytes();text=original.decode('utf-8')
    pattern=r'(br port write 254\ncom \d+\n.*?\n)co(\nend)'
    transformed,count=re.subn(pattern,lambda match:match[1]+'ex 77'+match[2],text,count=1,flags=re.S)
    assert count==1
    (HERE/'original-debugger.txt').write_bytes(original)
    (HERE/'debugger.txt').write_text(transformed,encoding='utf-8',newline='\n')
    command=[str(FUSE),'--no-sound','--no-autosave-settings','--no-confirm-actions',
             '--speed','10000','--machine','pentagon512','--beta128','--debugger-command',transformed,str(DISK.resolve())]
    start=time.perf_counter();timeout=False
    try:
        result=subprocess.run(command,cwd=FUSE.parent,env=dict(os.environ,SDL_VIDEODRIVER='dummy'),
                              capture_output=True,startupinfo=BASE['hidden_startupinfo'](),timeout=60)
        stdout,stderr,code=result.stdout,result.stderr,result.returncode
    except subprocess.TimeoutExpired as error:
        stdout,stderr,code=error.stdout or b'',error.stderr or b'',None;timeout=True
    elapsed=time.perf_counter()-start
    (HERE/'stdout.txt').write_bytes(stdout);(HERE/'stderr.txt').write_bytes(stderr)
    # Preserve the complete numeric stream; the original full verifier owns
    # all variable-width event parsing. Report only unambiguous stage tags.
    values=[int(match.group(1),0) for match in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',stdout)]
    tags=[value-2**32 if value>=0xffff0000 else value for value in values if value<0 or value>=0xffff0000]
    report=dict(date='2026-10-14',profile='pentagon512',elapsed_seconds=elapsed,
                returncode=code,timed_out=timeout,timeout_seconds=60,stdout_bytes=len(stdout),stderr_bytes=len(stderr),
                trd_sha256=hashlib.sha256(DISK.read_bytes()).hexdigest(),
                original_script_bytes=len(original),original_script_sha256=hashlib.sha256(original).hexdigest(),
                transformed_script_sha256=hashlib.sha256(transformed.encode()).hexdigest(),
                exactly_one_change='First source OUT command final co replaced by ex77; all UI/loading/state breakpoint definitions retained',
                ready_tag_observed=-100 in tags,observed_stage_tags=tags,command=command,
                scope='Bounded diagnostic of the exact detailed script through first source OUT; timeout preserves partial stdout, not a complete playback claim')
    (HERE/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key not in ('command','observed_stage_tags')},indent=2),flush=True)


if __name__=='__main__':main()
