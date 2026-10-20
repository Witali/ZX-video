"""Isolated installed-wheel export: python -I FILE PACKAGE_DIR OUTPUT_DIR."""
import json,runpy,sys
from pathlib import Path
installed=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();sys.path.insert(0,str(installed))
import zx0
assert Path(zx0.__file__).is_relative_to(installed)
from zx0.maximum_coroutine import build
from zx0.export import export
profiles={}
for cap in (31,63,127):
    regions,labels,metadata=build(core=0x9103,prefix_cap=cap,irq_code_bytes=13,irq_stack_bytes=6)
    at=out/str(cap);export(at,regions,labels,metadata)
    text=(at/'decoder.asm').read_text();assert 'REQUIRES undocumented CP IXH / CP IXL, 8 T' in text
    rebuilt=[]
    for line in text.splitlines():
        if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):rebuilt[-1][1].extend(int(n[1:],16) for n in line[3:].split(','))
    assert [(address,bytes(blob))for address,blob in rebuilt]==regions
    assert metadata['coroutine_supported'] and metadata['requires_undocumented_ix_halves']
    profiles[str(cap)]=dict(service_bytes=metadata['service_memory_bytes'],relocated_export_exact=True)
sys.argv=['zx0','build','--variant','maximum-coroutine','--output',str(out/'cli')]
runpy.run_module('zx0.__main__',run_name='__main__')
assert json.loads((out/'cli/metadata.json').read_text())['coroutine_supported']
assert not any(name.startswith(('toolkit','cv2','numpy','lzsa'))for name in sys.modules)
report=dict(complete=True,independent_installed_wheel=True,profiles=profiles,cli_export=True,converter_imports=False)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
