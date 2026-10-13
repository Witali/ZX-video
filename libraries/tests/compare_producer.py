import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'toolkit'))
original=types.ModuleType('original_prefix')
source=subprocess.run(['git','show','0085a116:toolkit/inplace_streaming_core.py'],cwd=root,
                       check=True,capture_output=True,text=True).stdout
exec(compile(source,'original_prefix.py','exec'),original.__dict__)
import inplace_streaming_core as current
from test_streaming_lzsa2 import Harness
from lzsa2_oracle import encode
import struct

results=[]
raw=b'X'*1024;payload=encode(raw,[(1,1023,1)])
stream=struct.pack('<HH',len(raw),len(payload))+payload
for direct in (False,True):
    h=Harness(stream,57,direct_header=direct)
    kwargs=dict(elapsed_fields=h.elapsed_fields,origin=h.layout['prefix_end'],patch_guards=True)
    before=original.input_prefix(h.z,h.d,**kwargs)
    after=current.input_prefix(h.z,h.d,**kwargs)
    assert before==after
    results.append(dict(direct_header=direct,code_labels_and_timing_rows_identical=True,
        regions=[dict(address=at,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()) for at,blob in after[0]]))
(root/'.tmp/library-producer-comparison.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print('Both shared input producer variants retain exact code, labels and timing rows')
