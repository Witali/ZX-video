"""Retain the final integrated codec regression results and tested sources."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
AUDIO=HERE.parents[1]
MODULES=('test_native_waveform_select','test_native_waveform_encoder',
         'test_native_waveform_prepare','test_convert_snr_audio')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve existing results')
    if not args.ffmpeg.is_file():raise ValueError('Need the actual FFmpeg executable')
    out.mkdir(parents=True,exist_ok=True)
    environment=dict(os.environ)
    environment['PATH']=str(args.ffmpeg.resolve().parent)+os.pathsep+environment.get('PATH','')
    environment['PYTHONPATH']=os.pathsep.join((str(AUDIO),str(HERE),str(AUDIO.parent/'toolkit'),
                                             environment.get('PYTHONPATH','')))
    command=[sys.executable,'-m','unittest',*MODULES,'-v']
    started=time.perf_counter()
    child=subprocess.run(command,cwd=AUDIO,env=environment,capture_output=True,creationflags=0x08000000 if os.name=='nt' else 0)
    elapsed=time.perf_counter()-started
    raw=child.stdout+child.stderr;(out/'tests.log').write_bytes(raw)
    log=raw.decode('utf-8',errors='replace')
    match=re.search(r'Ran (\d+) tests in ([\d.]+)s',log)
    report=dict(complete=True,exit_code=child.returncode,command=command,
        external_wall_seconds=elapsed,tests=None if match is None else int(match.group(1)),
        skipped_lines=[line for line in log.splitlines() if '... skipped' in line],
        FFmpeg=str(args.ffmpeg.resolve()),FFmpeg_sha256=sha(args.ffmpeg.read_bytes()),
        unittest_success=child.returncode==0 and bool(re.search(r'^OK\s*$',log,re.M)),
        scope='One final suite on integrated native preparation, selector and public converter; includes short full-native/Fuse verification when installed')
    snapshot=out/'producer-source';snapshot.mkdir()
    for name in (*[module+'.py' for module in MODULES],
        'native_waveform_prepare.c','native_waveform_prepare.py','native_waveform_encoder.c',
        'native_waveform_encoder.py','ima_waveform_encoder.py','ima_beam.py','waveform_kernel.py',
        'convert_snr_audio.py','experiments/song-snr/clock_control.py',
        'experiments/song-snr/codec_speed_tests.py'):
        (snapshot/(name.replace('/','__')+'.gz')).write_bytes(gzip.compress((AUDIO/name).read_bytes(),mtime=0))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    manifest=dict(complete=True,files=[dict(path=path.relative_to(out).as_posix(),
        bytes=path.stat().st_size,sha256=sha(path.read_bytes())) for path in sorted(out.rglob('*')) if path.is_file()])
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)
    if not report['unittest_success'] or report['tests']!=28 or report['skipped_lines']:
        raise RuntimeError('Final suite did not pass all28 required tests; preserve evidence')


if __name__=='__main__':main()
