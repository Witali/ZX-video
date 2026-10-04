import gzip,json
from pathlib import Path
import numpy as np
from verify_direct import sample_positions
p=Path('.tmp/ima3-direct-uniform128-pilot');q=Path('.tmp/ima3-direct-uniform128-disk')
a=json.loads((p/'player.json').read_bytes());b=json.loads((q/'player.json').read_bytes())
x=np.frombuffer(gzip.decompress((p/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
y=np.frombuffer(gzip.decompress((q/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
sx=x[sample_positions(a)];sy=y[sample_positions(b)]
r=dict(source_samples=a['pcm_samples'],sample_min_delta_tstates=int((sy-sx).min()),sample_max_delta_tstates=int((sy-sx).max()),sample_peak_to_peak_microseconds=float(np.ptp(sy-sx)/3.5469),different_payload_and_model=True,scope='Cold initial phase may differ by three T-states; compare complete useful-source sample timelines')
Path('.tmp/ima3-uniform128-timing-delta.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
