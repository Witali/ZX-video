from pathlib import Path
exec(Path('.tmp/ay-noise-colour/probe.py').read_text().split('a=bands(original)')[0])
raw=np.frombuffer(gzip.decompress(Path('.tmp/ay-tracked50-release/registers.gz').read_bytes()),dtype=np.uint8).reshape(-1,11)
mask=raw[:,6]>0
active=np.flatnonzero(mask)
baseline=np.fromfile('.tmp/noise-benchmark.f32',dtype='<f4')[::2]
gain=np.sqrt(np.mean(original**2)/np.mean(baseline**2))
def spectral(audio,size):
    win=np.hanning(size)
    centres=np.rint((active+.5)*441).astype(int)
    padded=np.pad(audio,(size//2,size//2))
    frames=padded[centres[:,None]+np.arange(size)]
    hz=np.fft.rfftfreq(size*2,1/22050)
    return abs(np.fft.rfft(frames*win,n=size*2,axis=1))[:,(hz>=50)&(hz<=8000)]/(win.sum()/2)
sizes=(512,2048,8192)
sources=[spectral(original,size) for size in sizes]
cost=[]
for delta in (-2,-1,0):
    directory=OUT/f'delta{delta}' if delta else OUT
    for n in range(1,32):
        audio=np.fromfile(directory/f'noise-{n}.f32',dtype='<f4').astype(float)*gain
        errors=[]
        for size,a in zip(sizes,sources):
            b=spectral(audio,size)
            floor=a.max()*.001
            support=(a>floor)|(b>floor)
            err=abs(20*np.log10(np.maximum(a,floor)/np.maximum(b,floor)))
            errors.append((err*support).sum(axis=1)/np.maximum(support.sum(axis=1),1))
        cost.append(np.mean(errors,axis=0))
    print('delta',delta,flush=True)
cost=np.array(cost).T
np.save(OUT/'fullbin-cost.npy',cost)
periods=np.tile(np.arange(1,32),3)
deltas=np.repeat([-2,-1,0],31)
transition=.15*abs(np.log2(periods[:,None]/periods[None,:]))+.15*abs(deltas[:,None]-deltas[None,:])
choice=np.zeros(len(active),int)
start=0
while start<len(active):
    end=start+1
    while end<len(active) and active[end]==active[end-1]+1: end+=1
    previous=cost[start].copy()
    history=[]
    for t in range(start+1,end):
        edges=previous[:,None]+transition
        best=edges.argmin(axis=0)
        history.append(best)
        previous=cost[t]+edges[best,np.arange(len(periods))]
    choice[end-1]=previous.argmin()
    for t in range(end-2,start-1,-1): choice[t]=history[t-start][choice[t+1]]
    start=end
candidate=raw.copy()
candidate[mask,6]=periods[choice]
for j,i in enumerate(active):
    for c in range(3):
        if not raw[i,7] & (1 << (c+3)): candidate[i,8+c]=max(1,int(raw[i,8+c])+int(deltas[choice[j]]))
out=OUT/'fullbins'
out.mkdir(exist_ok=True)
(out/'registers.gz').write_bytes(gzip.compress(candidate.tobytes(),mtime=0))
subprocess.run(['C:/Program Files/nodejs/node.exe','ay-converter/render_ym2149.js',str(out/'registers.gz'),str(out/'chip.f32'),'50',str(out/'render.json')],check=True)
down=np.frombuffer(subprocess.run([ff,'-v','error','-f','f32le','-ar','44100','-ac','1','-i',str(out/'chip.f32'),'-ar','22050','-f','f32le','-'],capture_output=True,check=True).stdout,'<f4').astype(float)
result=dict(period_histogram={str(i):int(np.sum(periods[choice]==i)) for i in range(1,32)},delta_histogram={str(i):int(np.sum(deltas[choice]==i)) for i in (-2,-1,0)},stft=spectrogram.compare(spectrogram.features(original),spectrogram.features(down)))
save(out/'result.json',result)
print(json.dumps(result),flush=True)
