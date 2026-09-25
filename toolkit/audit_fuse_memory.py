"""After the real TRD cold boot, check field length and RAM contention.

This destructive diagnostic replaces the frame code and exits without
playing video. Interrupts are disabled. Identical 10000-iteration read loops
execute in fixed bank 2, first reading A800, then 6400. Each loop is exactly
310000 CPU T-states. Independent frame/tstate counters expose an accidental
machine switch; no assumed field length is hidden in the trace.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
from build_zxv_trd import MiniAssembler
from smoke_test_fuse import hidden_startupinfo


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('fuse','trd','output'):p.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args();nonce=secrets.randbits(30)
    a=MiniAssembler(0x8000);a.emit(0xf3);events=[]
    for i,address in enumerate((0xa800,0x6400)*3):
        a.emit(0x21);a.word(address);a.emit(0x01);a.word(10000)
        a.label(f'loop{i}');events.append((a.pc,100+i*2))
        # LD D,(HL) 7; DEC BC 6; LD A,B 4; OR C 4; JP NZ 10.
        a.emit(0x56,0x0b,0x78,0xb1);a.abs16(0xc2,f'loop{i}')
        events.append((a.pc,101+i*2))
    a.emit(0x76);code=a.resolve()
    lines=['base 10','se $r 0','br 0xdf20','com 1',f'pr {nonce}']
    lines += [f'se {0x8000+i} {v}' for i,v in enumerate(code)]
    lines += ['se $r 1','se z80:pc 32768','co','end','cond 1 $r==0']
    for j,(pc,tag) in enumerate(events,2):
        lines += [f'br {pc}',f'com {j}',f'pr {tag}','pr spectrum:frames','pr ula:tstates',
                  'ex 77' if tag==111 else 'co','end',f'cond {j} $r==1'+(' && z80:bc==10000' if tag%2==0 else '')]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    script='\n'.join(lines);args.output.with_suffix('.debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    command=[str(args.fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions',
        '--speed','10000','--machine','128','--beta128','--debugger-command',script,str(args.trd.resolve())]
    epoch=time.time();r=subprocess.run(command,cwd=args.fuse.parent,env=dict(os.environ,SDL_VIDEODRIVER='dummy'),
                                     startupinfo=hidden_startupinfo(),capture_output=True,timeout=90)
    trace=r.stdout.decode(errors='replace');log=args.fuse.parent/'stdout.txt'
    if not re.search(r'^\s*\d+\s*$',trace,re.M) and log.exists() and log.stat().st_mtime>=epoch-2:trace=log.read_text(errors='replace')
    trace=trace.replace('\r\n','\n')
    args.output.with_suffix('.trace.txt').write_text(trace,encoding='utf-8',newline='\n')
    nums=[int(s.strip(),0) for s in trace.splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip())]
    if len(nums)!=37 or nums[0]!=nonce:raise ValueError(('incomplete or stale trace',nums[:10],len(nums)))
    rows=[]
    for i in range(6):
        t0,f0,u0,t1,f1,u1=nums[1+6*i:7+6*i]
        if (t0,t1)!=(100+2*i,101+2*i):raise AssertionError('event order')
        elapsed=(f1-f0)*70908+u1-u0
        rows.append(dict(address=(0xa800,0x6400)[i%2],cpu_tstates=310000,frames=f1-f0,
            start_ula_tstates=u0,end_ula_tstates=u1,elapsed_tstates_70908=elapsed,extra_tstates=elapsed-310000))
    field_ok=all(r['elapsed_tstates_70908']==310000 for r in rows[::2])
    contention=all(r['extra_tstates']>0 for r in rows[1::2])
    result=dict(complete=field_ok and contention,scope=__doc__,nonce_exact=True,exit_code=r.returncode,
        fuse_sha256=hashlib.sha256(args.fuse.read_bytes()).hexdigest(),trd_sha256=hashlib.sha256(args.trd.read_bytes()).hexdigest(),
        actual_70908_tstate_field_verified=field_ok,bank5_contention_verified=contention,loops=rows,
        trace_sha256=hashlib.sha256(args.output.with_suffix('.trace.txt').read_bytes()).hexdigest())
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result),flush=True)
    if not result['complete']:raise SystemExit(1)


if __name__=='__main__':main()
