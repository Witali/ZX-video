"""Reach the real EOF disk prompt and reject the unchanged disk in Fuse."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from smoke_test_fuse import hidden_startupinfo


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('fuse','build','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); result=[]
    for part in (1,2,3):
        stem=f'ZX-video-optimized-preview_part{part:02}'
        meta=json.loads((args.build/(stem+'.json')).read_text()); labels=meta['bootstrap_labels']
        script='\n'.join([
            f'breakpoint {labels["poll_next"]}','ignore 1 2','commands 1','exit 77','end',
            f'breakpoint {labels["next_disk_accepted"]}','commands 2','exit 99','end'])
        r=subprocess.run([str(args.fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions',
            '--speed','10000','--machine','128','--beta128','--debugger-command',script,
            str((args.build/(stem+'.trd')).resolve())],cwd=args.fuse.parent,
            env=dict(os.environ,SDL_VIDEODRIVER='dummy'),capture_output=True,
            startupinfo=hidden_startupinfo(),timeout=60)
        result.append(dict(part=part,eof_prompt_reached=r.returncode==77,unchanged_disk_rejected=r.returncode==77,
            exit_code=r.returncode,actual_disk_replacement_tested=False))
        if r.returncode!=77: raise RuntimeError(result[-1])
    args.output.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result),flush=True)


if __name__=='__main__': main()
