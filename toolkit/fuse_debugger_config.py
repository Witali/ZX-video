"""Probe an isolated Fuse config as transport for long debugger scripts.

Copy the same executable, DLLs and ROMs into a task output directory. Only
that copy receives fuse.cfg; the installed emulator and user settings are
untouched. The config route has NOT worked in the bundled Fuse 1.9.0:
it times out, while the same probe through argv exits correctly. This is
an unfinished diagnostic experiment, not an available playback runner.
"""
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def prepare(source,directory,commands):
    source=Path(source).resolve();directory=Path(directory).resolve()
    if directory==source.parent:raise ValueError('refuse to change installed Fuse settings')
    directory.mkdir(parents=True,exist_ok=True)
    for path in [source]+list(source.parent.glob('*.dll')):
        target=directory/path.name
        if not target.exists() or path.read_bytes()!=target.read_bytes():shutil.copy2(path,target)
    for name in ('roms','lib','ui'):
        shutil.copytree(source.parent/name,directory/name,dirs_exist_ok=True)
    root=ET.Element('settings');ET.SubElement(root,'debuggercommand').text=commands
    config=directory/'appdata'/'Fuse'/'fuse.cfg';config.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(config,encoding='utf-8',xml_declaration=True)
    return directory/source.name


if __name__=='__main__':
    import argparse
    import hashlib
    import json
    import os
    import re
    import subprocess
    from smoke_test_fuse import hidden_startupinfo
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fuse',type=Path,required=True);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--command-line',action='store_true',help='Compare the same probe supplied via argv')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();exe=prepare(args.fuse,args.directory,'base 10\nprint 314159\nexit 77')
    command=[str(exe),'--no-sound','--no-autosave-settings','--no-confirm-actions']
    if args.command_line:command+=['--debugger-command','base 10\nprint 314159\nexit 77']
    report=dict(mode='argv' if args.command_line else 'config',timeout_seconds=15,
        fuse_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),installation_modified=False)
    try:
        result=subprocess.run(command,cwd=exe.parent,
            env=dict(os.environ,SDL_VIDEODRIVER='dummy',APPDATA=str(exe.parent/'appdata')),
            capture_output=True,startupinfo=hidden_startupinfo(),timeout=15)
        output=result.stdout.decode(errors='replace')
        if not output and (exe.parent/'stdout.txt').exists():output=(exe.parent/'stdout.txt').read_text()
        values=[int(s.strip(),0) for s in output.splitlines() if re.fullmatch(r'(?:\d+|0x[\da-fA-F]+)',s.strip())]
        report.update(timed_out=False,exit_code=result.returncode,values=values,
            verified=result.returncode==77 and values==[314159],stderr=result.stderr.decode(errors='replace'))
    except subprocess.TimeoutExpired:
        report.update(timed_out=True,verified=False,exit_code=None)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report))
