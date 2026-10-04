import gzip,json
from pathlib import Path
from functools import partial
from ima3_direct_player import build_disk,MEASURED_MODEL,pack3
from verify_packet import native_check
from verify_direct import reference,intervals
from verify_pcm import save
p=Path('audiobook-beeper/experiments/ima-3bit-waveform')
b=gzip.decompress((p/'soundtrack.ima.gz').read_bytes())
capacity=5*16383+9471+2046
full=b+bytes(capacity//3*4-len(b))
o=Path('.tmp/ima3-direct-capacity');o.mkdir(exist_ok=True)
d,m=build_disk(full,o/'assembly',MEASURED_MODEL)
assert len(pack3(full))==capacity
r=native_check(d,m,full,partial(reference,model=m['model']),intervals)
r['resident_audio_bytes']=capacity;r['scope']+='; complete RAM capacity with original clip followed by synthetic silence'
save(o/'native.json',r);save(o/'player.json',m)
print(json.dumps(r))
