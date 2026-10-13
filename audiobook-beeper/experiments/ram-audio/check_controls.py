"""Reproduce cold boots, real predecessor RAM, and wrong-disk rejection on four models."""
from pathlib import Path
import gzip,json,numpy as np
from ima3_direct_player import build_disk,MEASURED_MODEL
from ram_series import build_volume
from convert_audio import pcm_wav
from verify_ram_series import verify_series
from verify_pcm import save
p=Path('audiobook-beeper/experiments/ram-audio/evidence/ima3-swap');p.mkdir(parents=True,exist_ok=True)
selected=[]
for i in range(2):
 path=p/f'selected-{i}';path.mkdir(exist_ok=True)
 d,m=build_disk(bytes(4096),path/'assembly',MEASURED_MODEL)
 save(path/'player.json',m);pcm_wav(path/'source-preview.wav',np.full(8192,128,'u1'))
 (path/'soundtrack.ima.gz').write_bytes(gzip.compress(bytes(4096),mtime=0));selected.append(path)
volumes=[]
for i in range(2):
 d,m=build_volume([selected[i]],p/f'volume-{i+1}',bytes(range(16)),i+1,2,codec='ima3')
 name=f'audio-{i+1}.trd';(p/name).write_bytes(d);volumes.append(dict(file=name,**m))
save(p/'volumes.json',volumes)
print(json.dumps(verify_series(p,Path('C:/Program Files (x86)/Fuse/fuse.exe'),'ffmpeg')),flush=True)
