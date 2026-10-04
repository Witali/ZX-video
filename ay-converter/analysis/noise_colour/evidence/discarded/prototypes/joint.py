exec(Path('.tmp/ay-noise-colour/probe.py').read_text().split('a=bands(original)')[0])
def plain(audio):
    mag,_=ay.spectra(audio,22050,50,1556,window_size=2048)
    hz=np.fft.rfftfreq(4096,1/22050)
    edges=np.geomspace(150,8000,25)
    return np.array([(mag[:,(hz>=a)&(hz<b)]**2).sum(axis=1) for a,b in zip(edges[:-1],edges[1:])]).T
raw=np.frombuffer(gzip.decompress(Path('.tmp/ay-tracked50-release/registers.gz').read_bytes()),dtype=np.uint8).reshape(-1,11)
ref=spectrogram.features(original)
source=np.concatenate([plain(original),bands(original)],axis=-1)
baseline=np.fromfile('.tmp/noise-benchmark.f32',dtype='<f4')[::2]
gain=np.sqrt(np.mean(original**2)/np.mean(baseline**2))
cost=[]
floor=source.max()*1e-6
for delta in (-2,-1,0):
    directory=OUT/f'delta{delta}'
    directory.mkdir(exist_ok=True)
    if delta:
        subprocess.run(['C:/Program Files/nodejs/node.exe','ay-converter/render_noise_candidates.js','.tmp/ay-tracked50-release/registers.gz',str(directory),str(delta)],check=True)
    else: directory=OUT
    for n in range(1,32):
        audio=np.fromfile(directory/f'noise-{n}.f32',dtype='<f4').astype(float)*gain
        target=np.concatenate([plain(audio),bands(audio)],axis=-1)
        cost.append(np.mean(abs(10*np.log10(np.maximum(source,floor)/np.maximum(target,floor))),axis=-1))
    print('delta',delta,flush=True)
cost=np.array(cost).T
np.save(OUT/'joint-cost.npy',cost)
choice=cost.argmin(axis=1)
delta=choice//31-2
period=choice%31+1
candidate=raw.copy()
mask=raw[:,6]>0
candidate[mask,6]=period[mask]
for i in np.flatnonzero(mask):
    for c in range(3):
        if not raw[i,7] & (1 << (c+3)): candidate[i,8+c]=max(1,int(raw[i,8+c])+int(delta[i]))
out=OUT/'joint'
out.mkdir(exist_ok=True)
(out/'registers.gz').write_bytes(gzip.compress(candidate.tobytes(),mtime=0))
subprocess.run(['C:/Program Files/nodejs/node.exe','ay-converter/render_ym2149.js',str(out/'registers.gz'),str(out/'chip.f32'),'50',str(out/'render.json')],check=True)
down=np.frombuffer(subprocess.run([ff,'-v','error','-f','f32le','-ar','44100','-ac','1','-i',str(out/'chip.f32'),'-ar','22050','-f','f32le','-'],capture_output=True,check=True).stdout,'<f4').astype(float)
result=dict(period_histogram={str(i):int(np.sum(period[mask]==i)) for i in range(1,32)},delta_histogram={str(i):int(np.sum(delta[mask]==i)) for i in (-2,-1,0)},stft=spectrogram.compare(ref,spectrogram.features(down)))
save(out/'result.json',result)
print(json.dumps(result),flush=True)
