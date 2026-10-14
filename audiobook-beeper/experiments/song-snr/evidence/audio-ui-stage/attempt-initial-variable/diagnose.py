"""Bounded cold-boot checkpoint diagnostic; no audio trace or shared edits."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

from ram_cache import PROFILES
from smoke_test_fuse import hidden_startupinfo


HERE=Path(__file__).resolve().parent
DISK=HERE.parent/'audio-ui-delivery/generated/audio.trd'
META=json.loads(DISK.with_name('player.json').read_bytes())
LABELS=META['player_labels']
PROFILE='pentagon512'
FUSE=Path('C:/Program Files (x86)/Fuse/fuse.exe')


def main():
    assert hashlib.sha256(DISK.read_bytes()).hexdigest()=='55216119144fdb4e574bb3525b496d15c528b6f1a826da39c5070c3f57be9e1d'
    field=PROFILES[PROFILE]['field'];stamp=f'spectrum:frames*{field}+ula:tstates'
    lines=['base 10','set $first_rom 0'];events=[]
    def event(address,tag,condition='',after=(),stop=False):
        eid=len(events)+1
        expr=[stamp,'z80:pc','ula:mem7ffd','z80:hl','z80:de','z80:b',
              f"[{LABELS['audio_ui_loading']}]",f"[{LABELS['audio_ui_dots']}]",'[23416]',
              f"([{LABELS['stream_remaining']}]+[{LABELS['stream_remaining']+1}]*256)"]
        lines.extend([f'br {address}',f'com {eid}',f'pr {tag}'])
        lines.extend('pr '+item for item in expr);lines.extend(after)
        lines.extend(['ex 77' if stop else 'co','end'])
        if condition:lines.append(f'cond {eid} {condition}')
        events.append(dict(tag=tag,address=address,fields=['timestamp','pc','7ffd','hl','de','b','loading','dots','bar','remaining']))
    event(LABELS['start'],-10)
    event(LABELS['cover_visible'],-11)
    event(0x3D13,-12,condition='$first_rom==0',after=['se $first_rom 1'])
    event(LABELS['ready'],-13,stop=True)
    event(LABELS['stream_finished'],-14,stop=True)
    script='\n'.join(lines)
    (HERE/'debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    command=[str(FUSE),'--no-sound','--no-autosave-settings','--no-confirm-actions',
             '--speed','10000','--machine',PROFILE,'--beta128','--debugger-command',script,str(DISK.resolve())]
    started=time.perf_counter();timeout=False
    try:
        result=subprocess.run(command,cwd=FUSE.parent,env=dict(os.environ,SDL_VIDEODRIVER='dummy'),
                              capture_output=True,startupinfo=hidden_startupinfo(),timeout=60)
        stdout,stderr,returncode=result.stdout,result.stderr,result.returncode
    except subprocess.TimeoutExpired as error:
        stdout,stderr,returncode=error.stdout or b'',error.stderr or b'',None;timeout=True
    elapsed=time.perf_counter()-started
    (HERE/'stdout.txt').write_bytes(stdout);(HERE/'stderr.txt').write_bytes(stderr)
    values=[int(match.group(1),0) for match in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',stdout)]
    parsed=[];cursor=0;definitions={item['tag']:item for item in events}
    while cursor<len(values):
        tag=values[cursor];cursor+=1
        if tag>=0xffff0000:tag-=2**32
        if tag not in definitions:continue
        definition=definitions[tag];width=len(definition['fields'])
        if cursor+width>len(values):break
        parsed.append(dict(tag=tag,**dict(zip(definition['fields'],values[cursor:cursor+width]))));cursor+=width
    report=dict(date='2026-10-14',profile=PROFILE,trd_sha256=hashlib.sha256(DISK.read_bytes()).hexdigest(),
                elapsed_seconds=elapsed,timeout_seconds=60,timed_out=timeout,returncode=returncode,
                ready_reached=any(item['tag']==-13 for item in parsed),events=parsed,
                checkpoint_definitions=events,command=command,
                scope='Actual independently cold-booted Fuse loader checkpoints only; no complete audio or waveform-quality claim')
    (HERE/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
