import json
from pathlib import Path
from convert_ima3_audio import reuse_pilot
from probe_reconstruction_error import wav8
identity=json.loads(Path('.tmp/ima3-automatic-final/run.json').read_bytes())
source=wav8(Path('.tmp/ima3-automatic-final/source-preview.wav')).copy();source[1000]^=1
try:reuse_pilot(Path('.tmp/ima3-cache-must-not-write'),Path('.tmp/ima3-automatic-full/pilot'),source,identity)
except ValueError as e:
    assert str(e)=='pilot source differs';assert not Path('.tmp/ima3-cache-must-not-write').exists()
    r=dict(complete=True,different_source_rejected=True,no_cached_data_modified=True)
    Path('.tmp/ima3-pilot-cache-check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
else:raise AssertionError('wrong source accepted')
