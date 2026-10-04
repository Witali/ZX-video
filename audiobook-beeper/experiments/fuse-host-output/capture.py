"""Compare a real Windows speaker loopback with Fuse's own FMF PCM.

The recording endpoint is explicitly a render-device loopback, never a mic.
Only two execution breakpoints are used: entry and first-part exit.
"""
import argparse,gzip,hashlib,json,os,re,subprocess,sys,time,warnings,wave
from pathlib import Path
import numpy as np
import soundcard as sc
from record_pcm import read_fmf
from smoke_test_fuse import hidden_startupinfo

p=argparse.ArgumentParser();p.add_argument('--fuse',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--frequency',type=int,choices=(44100,48000),default=44100);p.add_argument('--driver');a=p.parse_args()
if a.driver and a.driver.lower()=='dummy':p.error('This experiment requires a real audio output driver')
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
disk=Path(__file__).resolve().parents[3]/'ZX-audiobook-IMA3-overlap-test.trd'
meta=json.loads(Path('audiobook-beeper/experiments/ima-3bit-overlap/disk/part-01/player.json').read_bytes())
labels=meta['player_labels']
script=f"base 10\nbreakpoint {labels['ready']}\ncommands 1\nprint 100\nprint spectrum:frames\nprint ula:tstates\ncontinue\nend\nbreakpoint {labels['chain_exit']}\ncommands 2\nprint 200\nprint spectrum:frames\nprint ula:tstates\nexit 77\nend"
(out/'debugger.txt').write_text(script)
cmd=[str(a.fuse.resolve()),'--sound','--sound-freq',str(a.frequency),'--no-sound-force-8bit',
 '--no-autosave-settings','--no-confirm-actions','--speed','100','--machine','128','--beta128',
 '--movie-start',str(out/'capture.fmf'),'--movie-compr','None','--debugger-command',script,str(disk)]
env=dict(os.environ)
env.pop('SDL_AUDIODRIVER',None);env.pop('SDL_VIDEODRIVER',None)
if a.driver:env['SDL_AUDIODRIVER']=a.driver
# Hide the SDL visual surface only; its audio must use a real output driver.
if 'sdl' in str(a.fuse).lower():env['SDL_VIDEODRIVER']='dummy'
speaker=sc.default_speaker();endpoint=sc.get_microphone(id=speaker.id,include_loopback=True)
assert endpoint.isloopback
blocks=[];block_times=[];started=time.monotonic();process=None;launched_wall=time.time()
try:
 with warnings.catch_warnings(record=True) as caught:
  warnings.simplefilter('always')
  with endpoint.recorder(samplerate=48000,channels=[0,1],blocksize=4800) as recorder:
   with (out/'stdout.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
    process=subprocess.Popen(cmd,cwd=out,stdout=stdout,stderr=stderr,env=env,startupinfo=hidden_startupinfo())
    last_progress=0;exit_at=None
    while True:
     blocks.append(recorder.record(numframes=4800));elapsed=time.monotonic()-started;block_times.append(elapsed)
     if elapsed-last_progress>=10:
      print(json.dumps(dict(recording_seconds=round(elapsed,2),exit_code=process.poll())),flush=True);last_progress=elapsed
     if process.poll() is not None and exit_at is None:exit_at=elapsed
     if exit_at is not None and elapsed-exit_at>1:break
     if elapsed>120:raise TimeoutError('Fuse did not reach first-part exit')
  captured_warnings=[str(item.message) for item in caught]
finally:
 if process is not None and process.poll() is None:
  process.kill();process.wait(timeout=10)
audio=np.concatenate(blocks);(out/'loopback.f32.gz').write_bytes(gzip.compress(audio.astype('<f4').tobytes(),mtime=0))
def wav(path,data,rate):
 with wave.open(str(path),'wb') as w:
  w.setparams((1 if data.ndim==1 else data.shape[1],2,rate,0,'NONE','not compressed'))
  w.writeframes(np.rint(np.clip(data,-1,32767/32768)*32768).astype('<i2').tobytes())
wav(out/'loopback.wav',audio,48000)
assert process.returncode==77,process.returncode
if not (out/'stdout.txt').stat().st_size and 'sdl' in str(a.fuse).lower():
 redirected=a.fuse.parent/'stdout.txt'
 assert redirected.stat().st_mtime>=launched_wall,'Stale SDL debugger log'
 (out/'stdout.txt').write_bytes(redirected.read_bytes())
blob=(out/'capture.fmf').read_bytes()
if a.frequency==44100:raw,chunks,timing=read_fmf(blob)
else:
 import types
 module=types.ModuleType('capture_fmf');source=Path('audiobook-beeper/record_pcm.py').read_text()
 exec(compile(source.replace('rate != 44100',f'rate != {a.frequency}'),'<rate-specific fmf reader>','exec'),module.__dict__)
 raw,chunks,timing=module.read_fmf(blob)
wav(out/'internal.wav',raw.astype(float)/32768,a.frequency)
report=dict(fuse=str(a.fuse.resolve()),fuse_sha256=hashlib.sha256(a.fuse.read_bytes()).hexdigest(),
 disk_sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),speaker_name=speaker.name,loopback=True,
 source_frequency=a.frequency,capture_frequency=48000,capture_channels=2,capture_buffer_frames=4800,
 requested_sdl_driver=a.driver,real_audio_driver=True,frames=len(chunks),timing=timing,
 internal_samples=len(raw),captured_samples=len(audio),elapsed_seconds=time.monotonic()-started,
 exit_code=process.returncode,warnings=captured_warnings,capture_valid=not captured_warnings,block_times=block_times,
 loopback_peak=float(abs(audio).max()),loopback_rms=float(np.sqrt(np.mean(audio**2))))
(out/'capture.fmf.gz').write_bytes(gzip.compress(blob,mtime=0))
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='block_times'}),flush=True)
