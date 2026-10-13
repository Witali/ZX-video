"""Isolated smoke check: python -I smoke_install.py INSTALLED_DIR PACKAGE OUTPUT [ENCODER]."""
import importlib
import json
from pathlib import Path
import runpy
import sys

installed=Path(sys.argv[1]).resolve();name=sys.argv[2];destination=Path(sys.argv[3]).resolve()
encoder=sys.argv[4] if len(sys.argv)>4 else None
sys.path.insert(0,str(installed))
package=importlib.import_module(name)
assert Path(package.__file__).is_relative_to(installed)
assert not any(n.startswith(('toolkit','cv2','numpy')) for n in sys.modules)
seed=b'Independent project\n';raw=seed*32
payload=(package.encode(raw,[package.Token(0,len(seed)),package.Token(len(seed),len(raw)-len(seed),len(seed))])
         if name=='zx0' else package.encode(raw,[(len(seed),len(raw)-len(seed),len(seed))]))
assert package.decompress(payload,limit=len(raw))==raw
build=importlib.import_module(name+'.resumable').build
export=importlib.import_module(name+'.export').export
kwargs=dict(prefix=0x5000,prefix_limit=0x5400,core=0x6000,core_limit=0x6400,stack=0x4ff0,output_base=0xa000)
regions,labels,metadata=build(**kwargs)
export(destination/'custom',regions,labels,metadata)
assert (destination/'custom/LICENSE').is_file()
sys.argv=[name,'build','--output',str(destination/'cli')]
if name=='lzsa':sys.argv+=['--streaming','--direct-header']
runpy.run_module(name+'.__main__',run_name='__main__')
assert (destination/'cli/decoder.asm').is_file()
if encoder:
    assert package.decompress(package.compress(raw,executable=encoder),limit=len(raw))==raw
report=dict(package=name,independent_wheel=True,custom_layout=True,cli_export=True,
            resources=True,exact_round_trip=True,external_encoder=bool(encoder))
(destination/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
