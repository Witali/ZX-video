"""Isolated wheel check: python -I FILE INSTALLED_PACKAGE_DIR OUTPUT_DIR."""
import importlib,json,runpy,sys
from pathlib import Path

installed=Path(sys.argv[1]).resolve();destination=Path(sys.argv[2]).resolve()
sys.path.insert(0,str(installed));import lzsa
assert Path(lzsa.__file__).is_relative_to(installed)
from lzsa.block import build as block
from lzsa.resumable import build
from lzsa.export import export

profiles={}
for name,builder,options in (
    ('block',block,dict(long_copy=True,near_literals=True)),
    ('coroutine',build,dict(compact_sync=True,long_copy=True,near_literals=True,restore_compare=True)),
    ('guarded-call',build,dict(streaming=True,compact_sync=True,long_copy=True,word_state_init=True)),
    ('guarded-direct',build,dict(streaming=True,direct_header=True,compact_sync=True,long_copy=True,word_state_init=True))):
    regions,labels,metadata=builder(core=0x9103,core_limit=0x9500,fast_jumps=True,nibble_prefill=True,compact_branches=True,**options)
    at=destination/name;export(at,regions,labels,metadata)
    rebuilt=[]
    for line in (at/'decoder.asm').read_text().splitlines():
        if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):rebuilt[-1][1].extend(int(x[1:],16) for x in line[3:].split(','))
    assert [(address,bytes(blob)) for address,blob in rebuilt]==regions
    assert metadata['compact_branches'] and len(metadata['branch_changes'])==1
    profiles[name]=dict(code_and_state_bytes=metadata['code_bytes'],exact_export=True)
argv=['lzsa','build','--profile','fast-block','--compact-branches','--output',str(destination/'cli')]
sys.argv=argv;runpy.run_module('lzsa.__main__',run_name='__main__')
assert json.loads((destination/'cli/metadata.json').read_text())['compact_branches']
for builder in (build,block):
    try:builder(branch_tuned=True,compact_branches=True)
    except ValueError:pass
    else:raise AssertionError('incompatible policies were silently accepted')
assert not any(n.startswith(('toolkit','cv2','numpy')) for n in sys.modules)
report=dict(complete=True,independent_installed_wheel=True,converter_imports=False,profiles=profiles,
    cli_export_exact=True,mutual_exclusion_checked=True)
(destination/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
