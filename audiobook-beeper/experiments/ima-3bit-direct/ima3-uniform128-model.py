import gzip,json,shutil
import numpy as np
from pathlib import Path
p=Path('.tmp/ima3-direct-uniform128-pilot');o=Path('.tmp/ima3-direct-uniform128-host');o.mkdir(exist_ok=True)
m=json.loads((p/'player.json').read_bytes());t=np.frombuffer(gzip.decompress((p/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
h=np.diff(t[:(m['pcm_samples']-128)*16+1]).reshape(-1,16);h=h[h.max(axis=1)<100]
model=dict(m['model'],holds=np.rint(h.mean(axis=0)*8).astype(int).tolist(),weight_units='eighth T-state; uniform-memory packed IMA3 Fuse means',calibration=str(p/'output-times.u32.gz'))
m['model']=model;m['host_only_model_change']=True
(o/'player.json').write_text(json.dumps(m,indent=2));(o/'model.json').write_text(json.dumps(model,indent=2))
for name in ('soundtrack.ima.gz','source-preview.wav','compensated-pcm.wav','output-times.u32.gz'):shutil.copy2(p/name,o/name)
print(json.dumps(model))
