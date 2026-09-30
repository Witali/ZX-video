"""Fetch pinned libdragon LH5 author tools; build separately with host C compiler."""
import argparse,hashlib,json,subprocess,urllib.request
from pathlib import Path

REVISION='e356bf3f56f7afbf7e5246329562f145965cfdfc'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--vcvars',type=Path,help='Optional MSVC vcvars64.bat; builds the host probe')
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);files=[]
    for name in ('lzh5_compress.c','lzh5_compress.h'):
        url=f'https://raw.githubusercontent.com/DragonMinded/libdragon/{REVISION}/tools/common/{name}'
        data=urllib.request.urlopen(url,timeout=30).read();(a.output/name).write_bytes(data)
        files.append(dict(file=name,url=url,sha256=hashlib.sha256(data).hexdigest()))
    record=dict(revision=REVISION,files=files)
    if a.vcvars:
        root=a.output.resolve();wrapper=Path(__file__).with_name('lzh5_probe.c').resolve()
        original=(root/'lzh5_compress.c').read_bytes()
        before=b'static unsigned short left[], right[];'
        after=b'static unsigned short left[1019], right[1019];'
        if original.count(before)!=1:raise ValueError('upstream declaration changed')
        adapted=original.replace(before,after);(root/'lzh5_compress_host.c').write_bytes(adapted)
        record['host_adaptation']=dict(reason='MSVC needs complete tentative array declarations; 2*NC-1=1019',
            original=before.decode(),replacement=after.decode(),sha256=hashlib.sha256(adapted).hexdigest())
        command=f'cl /nologo /O2 /std:c11 /I"{root}" /Fe"{root / "lzh5_probe.exe"}" /Fo"{root / "lzh5_probe.obj"}" "{wrapper}"'
        batch=root/'build.cmd'
        batch.write_text(f'@echo off\nset VSLANG=1033\ncall "{a.vcvars.resolve()}" >nul\nif errorlevel 1 exit /b 1\n{command}\nexit /b %errorlevel%\n',encoding='ascii')
        result=subprocess.run(['cmd','/d','/c',str(batch)],capture_output=True,text=True,encoding='utf-8',errors='replace')
        (root/'build.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError((result.returncode,(result.stdout+result.stderr)[-4000:]))
        record.update(executable_sha256=hashlib.sha256((root/'lzh5_probe.exe').read_bytes()).hexdigest(),
            wrapper_sha256_lf=hashlib.sha256(wrapper.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),build_command=command)
    (a.output/'source.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(revision=REVISION,files=[r['file'] for r in files])))


if __name__=='__main__':main()
