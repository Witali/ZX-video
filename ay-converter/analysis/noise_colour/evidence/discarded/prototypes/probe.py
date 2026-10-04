import sys, subprocess, gzip, json
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('ay-converter').resolve()))
import ay_fidelity as ay
import spectrogram
from support import save

OUT=Path('.tmp/ay-noise-colour')
ff='C:/Users/rudol/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe'
original=np.frombuffer(subprocess.run([ff,'-v','error','-i','audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg','-t','31.12','-ac','1','-ar','22050','-f','f32le','-'],capture_output=True,check=True).stdout,'<f4').astype(float)
def bands(audio):
    mag,rms=ay.spectra(audio,22050,50,1556,window_size=2048)
    power=mag**2
    floor=np.median(np.lib.stride_tricks.sliding_window_view(np.pad(power,((0,0),(4,4)),mode='edge'),9,axis=1),axis=-1)/.7
    power=np.minimum(power,floor)
    hz=np.fft.rfftfreq(4096,1/22050)
    edges=np.geomspace(150,8000,25)
    return np.array([power[:,(hz>=a)&(hz<b)].sum(axis=1) for a,b in zip(edges[:-1],edges[1:])]).T
a=bands(original)
b=np.array([bands(np.fromfile(OUT/f'noise-{n}.f32',dtype='<f4')) for n in range(1,32)])
np.savez(OUT/'bands.npz',reference=a,candidates=b)
def norm(x): return x/np.maximum(x.sum(axis=-1,keepdims=True),1e-20)
an,bn=norm(a),norm(b)
losses={'root':1-np.sqrt(an[None]*bn).sum(axis=-1), 'log':np.mean((10*np.log10(np.maximum(an[None],.0001))-10*np.log10(np.maximum(bn,.0001)))**2,axis=-1)}
raw=np.frombuffer(gzip.decompress(Path('.tmp/ay-tracked50-release/registers.gz').read_bytes()),dtype=np.uint8).reshape(-1,11)
ref=spectrogram.features(original)
for name,loss in losses.items():
    selected=loss.argmin(axis=0)+1
    candidate=raw.copy()
    mask=raw[:,6]>0
    candidate[mask,6]=selected[mask]
    out=OUT/name
    out.mkdir(exist_ok=True)
    (out/'registers.gz').write_bytes(gzip.compress(candidate.tobytes(),mtime=0))
    subprocess.run(['C:/Program Files/nodejs/node.exe','ay-converter/render_ym2149.js',str(out/'registers.gz'),str(out/'chip.f32'),'50',str(out/'render.json')],check=True)
    down=np.frombuffer(subprocess.run([ff,'-v','error','-f','f32le','-ar','44100','-ac','1','-i',str(out/'chip.f32'),'-ar','22050','-f','f32le','-'],capture_output=True,check=True).stdout,'<f4').astype(float)
    result=dict(histogram={str(i):int(np.sum(selected[mask]==i)) for i in range(1,32)},stft=spectrogram.compare(ref,spectrogram.features(down)))
    save(out/'result.json',result)
    print(name,json.dumps(result),flush=True)
