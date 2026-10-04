from pathlib import Path
exec(Path('.tmp/ay-noise-colour/probe.py').read_text().split('a=bands(original)')[0])
raw=np.frombuffer(gzip.decompress(Path('.tmp/ay-tracked50-release/registers.gz').read_bytes()),dtype=np.uint8).reshape(-1,11)
mask=raw[:,6]>0
ref=spectrogram.features(original)
cost=np.load(OUT/'joint-cost.npy')
root=np.frombuffer(gzip.decompress((OUT/'root/registers.gz').read_bytes()),dtype=np.uint8).reshape(-1,11)
for name,period,delta in [('level_only',raw[:,6],np.full(1556,-2)),('period_only',cost[:,-31:].argmin(axis=1)+1,np.zeros(1556,int)),('root_level',root[:,6],np.full(1556,-2))]:
    candidate=raw.copy()
    candidate[mask,6]=period[mask]
    for i in np.flatnonzero(mask):
        for c in range(3):
            if not raw[i,7] & (1 << (c+3)): candidate[i,8+c]=max(1,int(raw[i,8+c])+int(delta[i]))
    out=OUT/name
    out.mkdir(exist_ok=True)
    (out/'registers.gz').write_bytes(gzip.compress(candidate.tobytes(),mtime=0))
    subprocess.run(['C:/Program Files/nodejs/node.exe','ay-converter/render_ym2149.js',str(out/'registers.gz'),str(out/'chip.f32'),'50',str(out/'render.json')],check=True)
    down=np.frombuffer(subprocess.run([ff,'-v','error','-f','f32le','-ar','44100','-ac','1','-i',str(out/'chip.f32'),'-ar','22050','-f','f32le','-'],capture_output=True,check=True).stdout,'<f4').astype(float)
    result=dict(stft=spectrogram.compare(ref,spectrogram.features(down)))
    save(out/'result.json',result)
    print(name,json.dumps(result),flush=True)
