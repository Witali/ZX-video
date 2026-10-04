import gzip,json
from pathlib import Path
from functools import partial
from ima3_direct_player import build_disk,pack3
from verify_packet import native_check
from verify_direct import reference,intervals
from verify_pcm import save
p=Path('.tmp/ima3-direct-uniform128-host');model=json.loads((p/'model.json').read_bytes())
b=gzip.decompress((p/'soundtrack.ima.gz').read_bytes());capacity=93432
full=b+bytes(capacity//3*4-len(b));o=Path('.tmp/ima3-direct-uniform128-capacity');o.mkdir(exist_ok=True)
d,m=build_disk(full,o/'assembly',model)
assert len(pack3(full))==capacity
save(o/'player.json',m)
r=native_check(d,m,full,partial(reference,model=m['model']),intervals)
r['resident_audio_bytes']=capacity;r['scope']+='; complete RAM capacity with original clip followed by synthetic silence'
save(o/'native.json',r);print(json.dumps(r))
